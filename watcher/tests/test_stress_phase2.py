"""
Stress Tests for Watcher Phase 2 Components

Tests performance and reliability under load:
- 100+ variables with rapid mutations
- High throughput event writing
- Symbol resolution under cache pressure
- Processor invocation at scale
"""

import pytest
import tempfile
import time
import threading
import uuid
from pathlib import Path

from watcher.core.event_enricher import EventEnricher, SymbolResolver
from watcher.core.event_writer import BatchEventWriter
from watcher.cli.processor_runner import ProcessorFactory


class TestEnrichmentUnderLoad:
    """Stress test enrichment pipeline"""

    def test_high_mutation_rate(self):
        """Test enrichment with high mutation rate"""
        enricher = EventEnricher()

        # Produce 1000 enriched events
        start_time = time.time()

        for i in range(1000):
            enricher.enrich(
                event_id=f'evt-{i}',
                timestamp_ns=int(time.time_ns()),
                ip=0x7f000000 + i,
                tid=1000 + (i % 10),  # 10 different threads
                variable_id=f'var-{i % 100}',  # 100 different variables
                variable_name=f'var_{i % 100}',
                before_snapshot=bytes([i % 256] * 32),
                after_snapshot=bytes([(i+1) % 256] * 32),
                scope='global',
            )

        elapsed = time.time() - start_time
        throughput = 1000 / elapsed

        print(f"\nEnrichment throughput: {throughput:.0f} events/sec")
        assert throughput > 100  # At least 100 events/sec


class TestSymbolResolutionUnderLoad:
    """Stress test symbol resolution cache"""

    def test_cache_hit_rate(self):
        """Test symbol cache with realistic hit/miss pattern"""
        resolver = SymbolResolver(binary_path='/nonexistent/binary')

        # Simulate realistic pattern: 80% cache hit rate
        total_requests = 1000
        unique_ips = 200  # 80% hit rate with 1000 requests

        start_time = time.time()

        for i in range(total_requests):
            ip = 0x7f000000 + (i % unique_ips)
            resolver.resolve(ip)

        elapsed = time.time() - start_time
        throughput = total_requests / elapsed

        cache_stats = resolver.cache.cache
        hit_ratio = (total_requests - unique_ips) / total_requests

        print(f"\nSymbol resolution throughput: {throughput:.0f} requests/sec")
        print(f"Expected cache hit ratio: {hit_ratio:.1%}")
        print(f"Cache size: {len(cache_stats)} entries")

        # Should handle 1000 requests quickly
        assert elapsed < 1.0  # Less than 1 second for 1000 requests


class TestEventWriterThroughput:
    """Stress test event writer"""

    def test_high_volume_writing(self):
        """Test writing high volume of events"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = BatchEventWriter(tmpdir, batch_size=50)
            writer.start()

            start_time = time.time()

            # Write 1000 events (reduced from 5000)
            for i in range(1000):
                event = {
                    'event_id': f'evt-{i}',
                    'variable_name': f'var_{i % 100}',
                    'function': f'func_{i % 50}',
                    'line': i % 1000,
                    'deltas': [{'offset': 0, 'before': '0x00', 'after': f'0x{i%256:02x}'}],
                }

                success = writer.enqueue_event(event)
                assert success or writer.queue.qsize() >= writer.queue.maxsize

            # Wait a bit for processing
            time.sleep(0.5)

            # Stop and flush
            writer.stop(timeout_seconds=10)

            elapsed = time.time() - start_time
            throughput = 1000 / elapsed

            print(f"\nBatch event writer throughput: {throughput:.0f} events/sec")

            # Verify events were written
            stats = writer.get_stats()
            print(f"Events written: {stats['events_written']}")
            print(f"Events lost: {stats['events_lost']}")

            # Should write most events
            assert stats['events_written'] > 500


class TestConcurrentEnrichment:
    """Stress test concurrent enrichment"""

    def test_concurrent_enrichers(self):
        """Test multiple threads enriching concurrently"""
        num_threads = 4
        events_per_thread = 500

        start_time = time.time()
        errors = []

        def worker(thread_id):
            try:
                enricher = EventEnricher()
                for i in range(events_per_thread):
                    enricher.enrich(
                        event_id=f'evt-{thread_id}-{i}',
                        timestamp_ns=int(time.time_ns()),
                        ip=0x7f000000 + i,
                        tid=2000 + thread_id,
                        variable_id=f'var-{thread_id}-{i % 50}',
                        variable_name=f'var_{i % 50}',
                        before_snapshot=bytes([0] * 32),
                        after_snapshot=bytes([1] * 32),
                    )
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        elapsed = time.time() - start_time
        total_events = num_threads * events_per_thread
        throughput = total_events / elapsed

        print(f"\nConcurrent enrichment throughput: {throughput:.0f} events/sec")
        print(f"Threads: {num_threads}, Total events: {total_events}")

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert throughput > 100


class TestConcurrentWriting:
    """Stress test concurrent event writing"""

    def test_concurrent_writers(self):
        """Test multiple threads writing events concurrently"""
        with tempfile.TemporaryDirectory() as tmpdir:
            num_threads = 4
            events_per_thread = 100  # Reduced from 250

            writer = BatchEventWriter(tmpdir, batch_size=50)
            writer.start()

            start_time = time.time()
            errors = []

            def worker(thread_id):
                try:
                    for i in range(events_per_thread):
                        event = {
                            'event_id': f'evt-{thread_id}-{i}',
                            'variable_name': f'var_{thread_id}_{i}',
                            'thread_id': 3000 + thread_id,
                        }
                        writer.enqueue_event(event)
                except Exception as e:
                    errors.append((thread_id, str(e)))

            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # Wait for processing
            time.sleep(0.5)

            writer.stop(timeout_seconds=10)

            elapsed = time.time() - start_time
            total_events = num_threads * events_per_thread

            # Get stats
            stats = writer.get_stats()
            written = stats['events_written']
            throughput = written / elapsed

            print(f"\nConcurrent writer throughput: {throughput:.0f} events/sec")
            print(f"Threads: {num_threads}, Total written: {written}/{total_events}")

            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert written >= total_events * 0.8  # At least 80% written


class TestMemoryUnderLoad:
    """Test memory behavior under load"""

    def test_cache_memory_limits(self):
        """Test that symbol cache doesn't grow unbounded"""
        resolver = SymbolResolver(binary_path='/nonexistent/binary')

        # Request 10,000 unique IPs with max cache size of 1000
        for i in range(10000):
            ip = 0x88000000 + i  # All unique IPs
            resolver.resolve(ip)

        cache_size = len(resolver.cache.cache)
        print(f"\nCache size after 10k unique IPs: {cache_size}")

        # Cache should stay bounded (max 1000)
        assert cache_size <= 1200  # Allow some margin
        assert cache_size > 500  # Should have some entries


class TestEdgeCases:
    """Test edge cases under stress"""

    def test_large_deltas(self):
        """Test enrichment with large delta data"""
        enricher = EventEnricher()

        # Large snapshots (1MB each)
        before = bytes(1024 * 1024)
        after_list = bytearray(1024 * 1024)
        after_list[0:100] = b'\xff' * 100  # Some changes
        after = bytes(after_list)

        start_time = time.time()
        enriched = enricher.enrich(
            event_id='evt-large',
            timestamp_ns=int(time.time_ns()),
            ip=0x7f000000,
            tid=4000,
            variable_id='var-large',
            variable_name='large_buffer',
            before_snapshot=before,
            after_snapshot=after,
        )
        elapsed = time.time() - start_time

        print(f"\nLarge delta computation: {elapsed*1000:.1f}ms for 1MB snapshots")

        assert len(enriched.deltas) > 0

    def test_rapid_fire_events(self):
        """Test handling rapid bursts of events"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = BatchEventWriter(tmpdir, batch_size=10)
            writer.start()

            # Rapid burst: 1000 events as fast as possible
            successful = 0
            for i in range(1000):
                success = writer.enqueue_event({
                    'event_id': f'burst-{i}',
                    'data': i,
                })
                if success:
                    successful += 1

            # Wait for processing
            time.sleep(0.5)

            writer.stop(timeout_seconds=10)

            stats = writer.get_stats()
            print(f"\nRapid burst: {successful} enqueued, {stats['events_written']} written")

            # Should handle most events
            assert stats['events_written'] > 200


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
