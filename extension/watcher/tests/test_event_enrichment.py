"""
Integration tests for Event Enrichment Pipeline, Persistence, and Processor Framework
"""

import pytest
import tempfile
import json
import os
from pathlib import Path

from watcher.core.event_enricher import (
    DeltaComputer,
    SymbolCache,
    SymbolResolver,
    EventEnricher,
    EnrichedEvent,
)
from watcher.core.event_writer import EventWriter, BatchEventWriter
from watcher.cli.processor_runner import (
    PythonProcessorRunner,
    ProcessorResponse,
    ProcessorAction,
    ProcessorFactory,
)


class TestDeltaComputer:
    """Test byte-level delta computation"""

    def test_simple_delta(self):
        """Test computing deltas for simple byte changes"""
        before = bytes([0x01, 0x02, 0x03, 0x04])
        after = bytes([0x01, 0x22, 0x03, 0x44])

        deltas = DeltaComputer.compute_deltas(before, after)

        assert len(deltas) == 2
        assert deltas[0]['offset'] == 1
        assert deltas[1]['offset'] == 3

    def test_no_delta(self):
        """Test when data doesn't change"""
        data = bytes([0x01, 0x02, 0x03])
        deltas = DeltaComputer.compute_deltas(data, data)
        assert len(deltas) == 0

    def test_size_change(self):
        """Test size changes"""
        before = bytes([0x01, 0x02])
        after = bytes([0x01, 0x02, 0x03, 0x04])

        deltas = DeltaComputer.compute_deltas(before, after)

        # Should have one size_change delta
        assert any('size_change' in d for d in deltas)


class TestSymbolCache:
    """Test symbol caching with LRU and TTL"""

    def test_cache_hit(self):
        """Test getting cached symbol"""
        cache = SymbolCache(max_size=10, ttl_seconds=3600)

        symbol_info = {'function': 'test_func', 'file': 'test.py', 'line': 42}
        cache.set('0x1234', symbol_info)

        assert cache.get('0x1234') == symbol_info

    def test_cache_miss(self):
        """Test cache miss for uncached IP"""
        cache = SymbolCache()
        assert cache.get('0x9999') is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = SymbolCache(max_size=2)

        cache.set('0x0001', {'function': 'f1', 'file': 'f1.py', 'line': 1})
        cache.set('0x0002', {'function': 'f2', 'file': 'f2.py', 'line': 2})
        cache.set('0x0003', {'function': 'f3', 'file': 'f3.py', 'line': 3})

        # First entry should be evicted
        assert cache.get('0x0001') is None
        assert cache.get('0x0002') is not None
        assert cache.get('0x0003') is not None


class TestSymbolResolver:
    """Test symbol resolution"""

    def test_resolver_fallback(self):
        """Test fallback when resolution fails"""
        resolver = SymbolResolver(binary_path='/nonexistent/binary')

        result = resolver.resolve(0x1234)

        # Should return fallback
        assert result['function'] == '??'
        assert result['file'] == '??'
        assert result['line'] == 0

    def test_cache_reuse(self):
        """Test that resolver caches results"""
        resolver = SymbolResolver(binary_path='/nonexistent/binary')

        result1 = resolver.resolve(0x1234)
        result2 = resolver.resolve(0x1234)

        # Same object (from cache)
        assert result1 == result2


class TestEnrichedEvent:
    """Test enriched event structure"""

    def test_to_dict(self):
        """Test conversion to dictionary"""
        event = EnrichedEvent(
            event_id='evt-123',
            timestamp_ns=1000000,
            variable_id='var-456',
            variable_name='counter',
            function_name='increment',
            file_path='app.py',
            line_number=42,
            deltas=[{'offset': 0, 'before': '0x00', 'after': '0x01'}],
            thread_id=1001,
            sql_context={'query': 'SELECT 1'},
            scope='global',
        )

        event_dict = event.to_dict()

        assert event_dict['event_id'] == 'evt-123'
        assert event_dict['variable_name'] == 'counter'
        assert event_dict['function'] == 'increment'
        assert event_dict['scope'] == 'global'


class TestEventWriter:
    """Test event persistence"""

    def test_write_single_event(self):
        """Test writing a single event"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)

            event_dict = {
                'event_id': 'evt-1',
                'variable_name': 'x',
                'function': 'test',
            }

            result = writer.write_event(event_dict)
            assert result is True

            writer.flush()
            writer.close()

            # Check file was created
            events_file = Path(tmpdir) / 'events.jsonl'
            assert events_file.exists()

            # Read and verify
            with open(events_file) as f:
                line = f.readline()
                data = json.loads(line)
                assert data['event_id'] == 'evt-1'

    def test_write_multiple_events(self):
        """Test writing multiple events"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir, max_buffer_events=10)

            for i in range(5):
                event_dict = {'event_id': f'evt-{i}', 'data': i}
                writer.write_event(event_dict)

            writer.flush()
            writer.close()

            # Verify all events written
            events_file = Path(tmpdir) / 'events.jsonl'
            with open(events_file) as f:
                lines = f.readlines()
                assert len(lines) == 5

    def test_get_stats(self):
        """Test statistics tracking"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)

            writer.write_event({'event_id': 'evt-1'})
            writer.write_event({'event_id': 'evt-2'})

            stats = writer.get_stats()

            assert stats['events_written'] == 2
            assert stats['events_lost'] == 0
            assert stats['buffered'] == 2

            writer.close()


class TestBatchEventWriter:
    """Test async batch event writer"""

    def test_batch_writing(self):
        """Test batch event writing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = BatchEventWriter(tmpdir, batch_size=5)
            writer.start()

            # Enqueue events
            for i in range(10):
                success = writer.enqueue_event({'event_id': f'evt-{i}'})
                assert success

            # Stop and flush
            writer.stop(timeout_seconds=5)

            # Verify all events written
            events_file = Path(tmpdir) / 'events.jsonl'
            with open(events_file) as f:
                lines = f.readlines()
                # At least some should be written
                assert len(lines) > 0


class TestProcessorResponse:
    """Test processor response parsing"""

    def test_from_dict_pass(self):
        """Test parsing pass action"""
        response = ProcessorResponse.from_dict({'action': 'pass'})
        assert response.action == ProcessorAction.PASS

    def test_from_dict_annotate(self):
        """Test parsing annotate action"""
        response = ProcessorResponse.from_dict({
            'action': 'annotate',
            'annotations': {'tag': 'important'},
        })
        assert response.action == ProcessorAction.ANNOTATE
        assert response.annotations['tag'] == 'important'

    def test_from_dict_drop(self):
        """Test parsing drop action"""
        response = ProcessorResponse.from_dict({'action': 'drop'})
        assert response.action == ProcessorAction.DROP


class TestPythonProcessorRunner:
    """Test Python processor invocation"""

    def test_processor_not_found(self):
        """Test processor with nonexistent file"""
        runner = PythonProcessorRunner('/nonexistent/processor.py')
        result = runner.invoke({'event_id': 'evt-1'})
        assert result is None

    def test_processor_timeout(self):
        """Test processor timeout"""
        # Create a processor that times out
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import time
def main(event):
    time.sleep(10)  # Will timeout
    return {'action': 'pass'}
""")
            f.flush()
            processor_path = f.name

        try:
            runner = PythonProcessorRunner(processor_path, timeout_seconds=0.1)
            result = runner.invoke({'event_id': 'evt-1'})
            # Should timeout and return None
            assert result is None
        finally:
            os.unlink(processor_path)


class TestProcessorFactory:
    """Test processor factory"""

    def test_create_python_runner(self):
        """Test creating Python processor runner"""
        runner = ProcessorFactory.create_runner('/tmp/proc.py')
        assert isinstance(runner, PythonProcessorRunner)

    def test_create_javascript_runner(self):
        """Test creating JavaScript processor runner"""
        from watcher.cli.processor_runner import JavaScriptProcessorRunner
        runner = ProcessorFactory.create_runner('/tmp/proc.js')
        assert isinstance(runner, JavaScriptProcessorRunner)

    def test_invalid_processor_type(self):
        """Test error for invalid processor type"""
        with pytest.raises(ValueError):
            ProcessorFactory.create_runner('/tmp/proc.rb')


class TestIntegrationPipeline:
    """End-to-end integration tests"""

    def test_enrichment_to_persistence(self):
        """Test full pipeline: enrich → write"""
        with tempfile.TemporaryDirectory() as tmpdir:
            enricher = EventEnricher()
            writer = EventWriter(tmpdir)

            # Create a mutation
            before = bytes([0x00, 0x00, 0x00, 0x00])
            after = bytes([0x00, 0x00, 0x00, 0x05])

            # Enrich event
            enriched = enricher.enrich(
                event_id='evt-1',
                timestamp_ns=1000000000,
                ip=0x7f0000,
                tid=1001,
                variable_id='var-x',
                variable_name='counter',
                before_snapshot=before,
                after_snapshot=after,
                sql_context=None,
                scope='global',
            )

            # Write event
            event_dict = enriched.to_dict()
            writer.write_event(event_dict)
            writer.flush()
            writer.close()

            # Verify
            events_file = Path(tmpdir) / 'events.jsonl'
            with open(events_file) as f:
                line = f.readline()
                data = json.loads(line)
                assert data['variable_name'] == 'counter'
                assert data['scope'] == 'global'
                assert len(data['deltas']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
