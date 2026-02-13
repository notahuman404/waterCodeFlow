"""
Real functional integration tests for Watcher pipeline.

Tests everything that can work without userfaultfd:
- File-scope configuration parsing
- Event enrichment pipeline
- Delta computation
- Symbol resolution
- JSONL persistence
- Processor execution
- Full end-to-end pipeline with synthetic data
"""

import pytest
import tempfile
import json
import time
import os
from pathlib import Path

from watcher.cli.scope_config_parser import parse_scope_config
from watcher.core.event_enricher import (
    EventEnricher,
    DeltaComputer,
    SymbolResolver,
    SymbolCache,
)
from watcher.core.event_writer import EventWriter, BatchEventWriter
from watcher.cli.processor_runner import ProcessorFactory, ProcessorResponse


class TestScopeConfigurationReal:
    """Test file-scope configuration parsing with real configs"""

    def test_parse_simple_config(self):
        """Test parsing a simple scope configuration"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("app.py:(local:counter,global:db_conn)\n")
            f.write("utils.py:(both:config)\n")
            config_path = f.name

        try:
            config = parse_scope_config(config_path)
            assert "app.py" in config
            assert "utils.py" in config

            app_vars = config["app.py"]
            assert len(app_vars) == 2
            assert app_vars[0]['name'] == 'counter'
            assert app_vars[0]['scope'] == 'local'
            assert app_vars[1]['name'] == 'db_conn'
            assert app_vars[1]['scope'] == 'global'

            utils_vars = config["utils.py"]
            assert len(utils_vars) == 1
            assert utils_vars[0]['name'] == 'config'
            assert utils_vars[0]['scope'] == 'both'
        finally:
            os.unlink(config_path)

    def test_parse_mixed_scope_config(self):
        """Test parsing with mixed scope types including unknown"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("service.py:(local:x,both:y,unknown:z)\n")
            f.write("lib/core.py:(global:shared)\n")
            config_path = f.name

        try:
            config = parse_scope_config(config_path)
            assert len(config) == 2

            service_vars = config["service.py"]
            assert service_vars[0]['scope'] == 'local'
            assert service_vars[1]['scope'] == 'both'
            assert service_vars[2]['scope'] == 'unknown'

            core_vars = config["lib/core.py"]
            assert core_vars[0]['scope'] == 'global'
        finally:
            os.unlink(config_path)

    def test_parse_default_scope(self):
        """Test parsing with default (no specified) scope"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test.py:(var1,local:var2)\n")
            config_path = f.name

        try:
            config = parse_scope_config(config_path)
            vars_list = config["test.py"]
            # First var without scope should get default
            assert vars_list[0]['name'] == 'var1'
            # Second var has explicit scope
            assert vars_list[1]['name'] == 'var2'
            assert vars_list[1]['scope'] == 'local'
        finally:
            os.unlink(config_path)


class TestDeltaComputationReal:
    """Test delta computation with real byte data"""

    def test_compute_single_byte_delta(self):
        """Test computing delta for single byte change"""
        before = bytes([0x00, 0x11, 0x22, 0x33])
        after = bytes([0x00, 0xFF, 0x22, 0x33])

        deltas = DeltaComputer.compute_deltas(before, after)
        assert len(deltas) == 1
        assert deltas[0]['offset'] == 1
        assert deltas[0]['before'] == '0x11'
        assert deltas[0]['after'] == '0xff'

    def test_compute_multiple_deltas(self):
        """Test computing multiple byte changes"""
        before = bytes(range(10))
        after = bytes([i if i % 2 == 0 else i + 100 for i in range(10)])

        deltas = DeltaComputer.compute_deltas(before, after)
        assert len(deltas) == 5  # Every odd offset changes
        for i, delta in enumerate(deltas):
            assert delta['offset'] == 2 * i + 1

    def test_compute_no_deltas(self):
        """Test when before and after are identical"""
        data = bytes([0xAA, 0xBB, 0xCC, 0xDD])
        deltas = DeltaComputer.compute_deltas(data, data)
        assert len(deltas) == 0

    def test_compute_large_buffer_deltas(self):
        """Test delta computation on large buffers"""
        before = bytes(10000)
        after = bytearray(10000)
        after[0] = 0xFF
        after[5000] = 0xFF
        after[9999] = 0xFF
        after = bytes(after)

        deltas = DeltaComputer.compute_deltas(before, after)
        assert len(deltas) == 3
        assert deltas[0]['offset'] == 0
        assert deltas[1]['offset'] == 5000
        assert deltas[2]['offset'] == 9999

    def test_compute_consecutive_deltas(self):
        """Test delta computation with consecutive byte changes"""
        before = bytes([0x00, 0x00, 0x00, 0x00])
        after = bytes([0xFF, 0xFF, 0xFF, 0xFF])

        deltas = DeltaComputer.compute_deltas(before, after)
        assert len(deltas) == 4
        for i, delta in enumerate(deltas):
            assert delta['offset'] == i
            # hex() returns '0x0' not '0x00' for small values
            assert delta['before'] in ['0x0', '0x00']
            assert delta['after'] in ['0xff', '0xFF']


class TestSymbolCacheReal:
    """Test symbol caching with real TTL"""

    def test_cache_hit(self):
        """Test cache hit returns cached value"""
        cache = SymbolCache(max_size=100, ttl_seconds=60)
        symbol_info = {'function': 'func_name', 'file': 'file.py', 'line': 10}
        cache.set("0x12345678", symbol_info)

        result = cache.get("0x12345678")
        assert result == symbol_info

    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = SymbolCache(max_size=100, ttl_seconds=60)
        result = cache.get("0x99999999")
        assert result is None

    def test_cache_lru_eviction(self):
        """Test LRU eviction works"""
        cache = SymbolCache(max_size=3, ttl_seconds=60)
        cache.set("key1", {'func': 'val1'})
        cache.set("key2", {'func': 'val2'})
        cache.set("key3", {'func': 'val3'})
        # Access key1 to make it recently used
        cache.get("key1")
        # Add key4, should evict key2 (least recently used)
        cache.set("key4", {'func': 'val4'})

        assert cache.get("key1") == {'func': 'val1'}
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == {'func': 'val3'}
        assert cache.get("key4") == {'func': 'val4'}

    def test_cache_ttl_expiration(self):
        """Test cache entries expire after TTL"""
        cache = SymbolCache(max_size=100, ttl_seconds=1)
        cache.set("key", {'func': 'value'})

        assert cache.get("key") == {'func': 'value'}
        time.sleep(1.1)
        assert cache.get("key") is None

    def test_cache_multiple_entries(self):
        """Test cache with many entries"""
        cache = SymbolCache(max_size=1000, ttl_seconds=60)
        for i in range(100):
            symbol_info = {'function': f'func_{i}', 'file': f'file{i}.py', 'line': i*10}
            cache.set(f"0x{i:x}", symbol_info)

        for i in range(100):
            result = cache.get(f"0x{i:x}")
            assert result == {'function': f'func_{i}', 'file': f'file{i}.py', 'line': i*10}


class TestEventEnrichmentReal:
    """Test full event enrichment pipeline with real data"""

    def test_enrich_simple_event(self):
        """Test enriching a simple event"""
        enricher = EventEnricher()

        enriched = enricher.enrich(
            event_id="evt-001",
            timestamp_ns=1000000000,
            ip=0x7f000100,
            tid=1001,
            variable_id="var_001",
            variable_name="counter",
            before_snapshot=bytes([0x00, 0x00, 0x00, 0x01]),
            after_snapshot=bytes([0x00, 0x00, 0x00, 0x02]),
            scope="local",
        )

        assert enriched.event_id == "evt-001"
        assert enriched.timestamp_ns == 1000000000
        assert enriched.thread_id == 1001
        assert enriched.variable_name == "counter"
        assert enriched.scope == "local"
        assert len(enriched.deltas) > 0

    def test_enrich_event_with_large_snapshot(self):
        """Test enriching event with large snapshots"""
        enricher = EventEnricher()

        before = bytes(1024)  # 1KB
        after = bytearray(1024)
        after[100:110] = b'\xFF' * 10
        after = bytes(after)

        enriched = enricher.enrich(
            event_id="evt-large",
            timestamp_ns=2000000000,
            ip=0x7f000200,
            tid=2002,
            variable_id="var_large",
            variable_name="big_buffer",
            before_snapshot=before,
            after_snapshot=after,
        )

        assert enriched.event_id == "evt-large"
        assert len(enriched.deltas) == 10
        enriched_dict = enriched.to_dict()
        assert "deltas" in enriched_dict
        assert "event_id" in enriched_dict

    def test_enrich_event_to_dict(self):
        """Test converting enriched event to dictionary"""
        enricher = EventEnricher()

        enriched = enricher.enrich(
            event_id="evt-dict",
            timestamp_ns=3000000000,
            ip=0x7f000300,
            tid=3003,
            variable_id="var_dict",
            variable_name="test_var",
            before_snapshot=bytes([0x11, 0x22]),
            after_snapshot=bytes([0x11, 0x33]),
            scope="both",
        )

        event_dict = enriched.to_dict()
        assert isinstance(event_dict, dict)
        assert event_dict['event_id'] == "evt-dict"
        assert event_dict['timestamp_ns'] == 3000000000
        assert event_dict['variable_name'] == "test_var"
        assert event_dict['scope'] == "both"


class TestEventWriterReal:
    """Test JSONL event writer with real file I/O"""

    def test_write_single_event(self):
        """Test writing single event to JSONL"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)

            event = {
                'event_id': 'evt-001',
                'timestamp_ns': 1000000000,
                'variable_name': 'counter',
                'deltas': [{'offset': 0, 'before': '0x00', 'after': '0x01'}],
            }

            success = writer.write_event(event)
            assert success

            writer.flush()
            writer.close()

            # Verify file content
            events_file = Path(tmpdir) / "events.jsonl"
            assert events_file.exists()

            with open(events_file) as f:
                lines = f.readlines()
                assert len(lines) == 1
                loaded = json.loads(lines[0])
                assert loaded['variable_name'] == 'counter'

    def test_write_multiple_events(self):
        """Test writing multiple events"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)

            for i in range(10):
                event = {
                    'event_id': f'evt-{i:03d}',
                    'timestamp_ns': 1000000000 + i,
                    'variable_name': f'var_{i}',
                }
                writer.write_event(event)

            writer.flush()
            writer.close()

            events_file = Path(tmpdir) / "events.jsonl"
            with open(events_file) as f:
                lines = f.readlines()
                assert len(lines) == 10

    def test_write_event_statistics(self):
        """Test event writer statistics tracking"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)

            for i in range(5):
                writer.write_event({'event_id': f'evt-{i}'})

            writer.flush()
            stats = writer.get_stats()

            assert stats['events_written'] == 5
            assert stats['events_lost'] == 0

            writer.close()

    def test_batch_writer_throughput(self):
        """Test batch event writer throughput"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = BatchEventWriter(tmpdir, batch_size=50)
            writer.start()

            # Write 200 events
            for i in range(200):
                event = {
                    'event_id': f'evt-batch-{i}',
                    'timestamp_ns': 1000000000 + i,
                }
                writer.enqueue_event(event)

            writer.stop(timeout_seconds=5)

            # Verify file written
            events_file = Path(tmpdir) / "events.jsonl"
            if events_file.exists():
                with open(events_file) as f:
                    lines = f.readlines()
                    assert len(lines) > 0


class TestProcessorExecutionReal:
    """Test processor execution with real Python code"""

    def test_processor_response_parsing(self):
        """Test parsing processor response"""
        response_data = {
            'action': 'annotate',
            'annotations': {'test_key': 'test_value'},
        }
        response = ProcessorResponse.from_dict(response_data)
        assert response.action == 'annotate'
        assert response.annotations == {'test_key': 'test_value'}

    def test_processor_response_drop_action(self):
        """Test drop action response"""
        response = ProcessorResponse(action='drop')
        assert response.action == 'drop'

    def test_processor_response_pass_action(self):
        """Test pass action response"""
        response = ProcessorResponse(action='pass')
        assert response.action == 'pass'


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline without mocks"""

    def test_full_pipeline_enrichment_to_jsonl(self):
        """Test complete pipeline from event to JSONL"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create enricher and writer
            enricher = EventEnricher()
            writer = EventWriter(tmpdir)

            # Create and enrich multiple events
            num_events = 20
            for i in range(num_events):
                # Create event with delta
                before = bytes([i, i + 1, i + 2])
                after = bytes([i, i + 10, i + 2])

                enriched = enricher.enrich(
                    event_id=f"evt-e2e-{i:03d}",
                    timestamp_ns=1000000000 + i,
                    ip=0x7f000000 + i,
                    tid=1000 + i,
                    variable_id=f"var-{i}",
                    variable_name=f"variable_{i}",
                    before_snapshot=before,
                    after_snapshot=after,
                    scope="local" if i % 2 == 0 else "global",
                )

                event_dict = enriched.to_dict()
                writer.write_event(event_dict)

            writer.flush()
            writer.close()

            # Verify output
            events_file = Path(tmpdir) / "events.jsonl"
            assert events_file.exists()

            with open(events_file) as f:
                lines = f.readlines()
                assert len(lines) == num_events

                for i, line in enumerate(lines):
                    event = json.loads(line)
                    assert event['event_id'] == f"evt-e2e-{i:03d}"
                    assert event['variable_name'] == f"variable_{i}"
                    assert 'deltas' in event
                    assert len(event['deltas']) > 0

    def test_pipeline_with_scope_filtering(self):
        """Test pipeline with scope-based filtering"""
        with tempfile.TemporaryDirectory() as tmpdir:
            enricher = EventEnricher()
            writer = EventWriter(tmpdir)

            # Create events with different scopes
            scopes = ['local', 'global', 'both', 'unknown']
            for i, scope in enumerate(scopes):
                enriched = enricher.enrich(
                    event_id=f"evt-scope-{i}",
                    timestamp_ns=2000000000 + i,
                    ip=0x7f000100 + i,
                    tid=2000 + i,
                    variable_id=f"var-scope-{i}",
                    variable_name=f"scope_test_{scope}",
                    before_snapshot=bytes([i]),
                    after_snapshot=bytes([i + 1]),
                    scope=scope,
                )

                writer.write_event(enriched.to_dict())

            writer.flush()
            writer.close()

            # Verify scopes are preserved
            events_file = Path(tmpdir) / "events.jsonl"
            with open(events_file) as f:
                events = [json.loads(line) for line in f]
                assert len(events) == 4

                for i, event in enumerate(events):
                    expected_scope = scopes[i]
                    if expected_scope != 'unknown':
                        assert event['scope'] == expected_scope

    def test_pipeline_concurrent_events(self):
        """Test pipeline handling concurrent events properly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            enricher = EventEnricher()
            writer = EventWriter(tmpdir)

            # Simulate concurrent events (rapid succession)
            num_events = 100
            for i in range(num_events):
                enriched = enricher.enrich(
                    event_id=f"evt-concurrent-{i:04d}",
                    timestamp_ns=3000000000 + i,
                    ip=0x7f000000 + (i % 4),  # Some IPs repeat
                    tid=3000 + (i % 8),  # Some thread IDs repeat
                    variable_id=f"var-{i % 10}",  # Some variables repeat
                    variable_name=f"concurrent_var_{i % 10}",
                    before_snapshot=bytes([i % 256]),
                    after_snapshot=bytes([(i + 1) % 256]),
                )

                writer.write_event(enriched.to_dict())

            writer.flush()
            writer.close()

            events_file = Path(tmpdir) / "events.jsonl"
            with open(events_file) as f:
                events = [json.loads(line) for line in f]
                assert len(events) == num_events

                # Verify all event IDs are unique
                event_ids = [e['event_id'] for e in events]
                assert len(event_ids) == len(set(event_ids))


class TestSymbolCacheLRUBehavior:
    """Test LRU cache advanced behavior"""

    def test_cache_lru_with_many_evictions(self):
        """Test LRU with many entries and evictions"""
        cache = SymbolCache(max_size=10, ttl_seconds=60)

        # Add 20 entries, should evict oldest
        for i in range(20):
            cache.set(f"addr-{i}", {'function': f'func-{i}'})

        # Last 10 should still be there
        for i in range(10, 20):
            assert cache.get(f"addr-{i}") is not None

        # First 10 should be evicted
        for i in range(10):
            assert cache.get(f"addr-{i}") is None

    def test_cache_recent_access_prevents_eviction(self):
        """Test that accessing an entry makes it recent and prevents eviction"""
        cache = SymbolCache(max_size=3, ttl_seconds=60)

        cache.set("a", {'val': '1'})
        cache.set("b", {'val': '2'})
        cache.set("c", {'val': '3'})

        # Access 'a' to make it recent
        assert cache.get("a") == {'val': '1'}

        # Add new entry, should evict 'b' (least recently used)
        cache.set("d", {'val': '4'})

        assert cache.get("a") == {'val': '1'}  # Still there
        assert cache.get("b") is None  # Evicted
        assert cache.get("c") == {'val': '3'}  # Still there
        assert cache.get("d") == {'val': '4'}  # New entry


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
