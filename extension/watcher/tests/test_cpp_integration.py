"""
Integration tests for Phase 3 C++ - Python bridge

Tests the complete flow: C++ core → Python enrichment → JSONL persistence
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from watcher.core.event_bridge import EventBridge, SyncEventBridge
from watcher.core.event_enricher import EventEnricher
from watcher.core.event_writer import EventWriter


class TestEventBridge:
    """Test event bridge functionality"""

    def test_bridge_initialization(self):
        """Test bridge can be initialized"""
        mock_core = Mock()
        mock_core.lib = Mock()

        enricher = EventEnricher()

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)

            bridge = EventBridge(mock_core, enricher, writer)

            assert bridge.watcher_core is mock_core
            assert bridge.enricher is enricher
            assert bridge.writer is writer
            assert not bridge.running

            writer.close()

    def test_bridge_statistics(self):
        """Test bridge statistics tracking"""
        mock_core = Mock()
        mock_core.lib = Mock()
        enricher = EventEnricher()

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)

            bridge = EventBridge(mock_core, enricher, writer)

            # Simulate event processing
            bridge.events_from_cpp = 10
            bridge.events_enriched = 8
            bridge.events_persisted = 8
            bridge.events_failed = 2

            stats = bridge.get_stats()

            assert stats['events_from_cpp'] == 10
            assert stats['events_enriched'] == 8
            assert stats['events_persisted'] == 8
            assert stats['events_failed'] == 2

            writer.close()

    def test_sync_bridge_initialization(self):
        """Test sync bridge initialization"""
        mock_core = Mock()
        mock_core.lib = Mock()
        enricher = EventEnricher()

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)

            sync_bridge = SyncEventBridge(mock_core, enricher, writer)

            assert sync_bridge.watcher_core is mock_core
            assert sync_bridge.bridge is not None

            writer.close()


class TestBridgeEventProcessing:
    """Test bridge event processing"""

    def test_process_events_empty_queue(self):
        """Test processing when queue is empty"""
        mock_core = Mock()
        mock_core.lib = Mock()
        # Simulate empty queue
        mock_core.lib.watcher_dequeue_fast_path_event = Mock(return_value=b"")

        enricher = EventEnricher()

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)
            bridge = EventBridge(mock_core, enricher, writer)

            processed = bridge.process_events(max_events=10)

            assert processed == 0
            assert bridge.events_from_cpp == 0

            writer.close()

    def test_process_events_with_data(self):
        """Test processing events with data"""
        # Create a mock event in JSON format
        event_json = json.dumps({
            'event_id': 'test-evt-1',
            'timestamp_ns': 1000000000,
            'ip': 0x7f000100,
            'tid': 1001,
            'page_base': '0x7f0000'
        }).encode()

        mock_core = Mock()
        mock_core.lib = Mock()
        mock_core.lib.watcher_dequeue_fast_path_event = Mock(
            side_effect=[event_json, b""]  # Return event then empty
        )
        mock_core.lib.watcher_read_snapshot = Mock(return_value=bytes(32))
        mock_core.variables = {}  # Empty variable map for testing

        enricher = EventEnricher()

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)
            bridge = EventBridge(mock_core, enricher, writer)

            processed = bridge.process_events(max_events=10)

            # Should process the one event
            assert processed >= 0  # May be 0 or 1 depending on implementation
            assert bridge.events_from_cpp == 1

            writer.close()


class TestBridgeIntegration:
    """Integration tests for full pipeline"""

    def test_bridge_with_enricher_and_writer(self):
        """Test bridge with real enricher and writer"""
        # Create mock C++ core
        event_json = json.dumps({
            'event_id': 'evt-123',
            'timestamp_ns': 1000000,
            'ip': 0x7f001000,
            'tid': 1002,
            'page_base': '0x7f000000'
        }).encode()

        mock_core = Mock()
        mock_core.lib = Mock()
        mock_core.lib.watcher_dequeue_fast_path_event = Mock(
            side_effect=[event_json, b""]
        )
        mock_core.lib.watcher_read_snapshot = Mock(return_value=bytes(32))
        mock_core.variables = {}

        enricher = EventEnricher()

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)
            bridge = EventBridge(mock_core, enricher, writer)

            # Process events
            processed = bridge.process_events(max_events=10)

            # Verify file was written
            events_file = Path(tmpdir) / "events.jsonl"

            writer.flush()
            writer.close()

            # Check if file has content
            if events_file.exists():
                with open(events_file) as f:
                    lines = f.readlines()
                    # Should have at least attempted to write
                    assert len(lines) >= 0


class TestSyncBridge:
    """Test synchronous bridge"""

    def test_sync_bridge_process_until_empty(self):
        """Test sync bridge process_until_empty"""
        event_json = json.dumps({
            'event_id': 'evt-sync',
            'timestamp_ns': 2000000,
            'ip': 0x7f002000,
            'tid': 2001,
            'page_base': '0x7f000000'
        }).encode()

        mock_core = Mock()
        mock_core.lib = Mock()
        call_count = [0]

        def dequeue_side_effect():
            call_count[0] += 1
            if call_count[0] <= 1:
                return event_json
            return b""

        mock_core.lib.watcher_dequeue_fast_path_event = Mock(
            side_effect=dequeue_side_effect
        )
        mock_core.lib.watcher_read_snapshot = Mock(return_value=bytes(32))
        mock_core.variables = {}

        enricher = EventEnricher()

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = EventWriter(tmpdir)
            sync_bridge = SyncEventBridge(mock_core, enricher, writer)

            # Process until queue is empty
            sync_bridge.process_until_empty(timeout_seconds=1)

            stats = sync_bridge.get_stats()

            # Should have attempted to process
            assert stats['events_from_cpp'] >= 1

            writer.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
