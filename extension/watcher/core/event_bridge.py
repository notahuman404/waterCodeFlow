"""
Event Bridge - Connects C++ core event queue to Python enrichment pipeline

Retrieves fast-path events from C++ core and enriches them using the Phase 2
enrichment pipeline before persisting to JSONL.
"""

import json
import ctypes
import threading
import time
from typing import Optional, Dict, Any, Callable
from queue import Queue


class EventBridge:
    """Bridges C++ event queue to Python enrichment pipeline"""

    def __init__(self, watcher_core, enricher, writer, poll_interval_ms: float = 10):
        """
        Initialize the event bridge.

        Args:
            watcher_core: WatcherCore instance (has access to FFI lib)
            enricher: EventEnricher instance from Phase 2
            writer: EventWriter instance from Phase 2
            poll_interval_ms: Polling interval in milliseconds
        """
        self.watcher_core = watcher_core
        self.enricher = enricher
        self.writer = writer
        self.poll_interval = poll_interval_ms / 1000.0  # Convert to seconds

        self.lib = watcher_core.lib
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None

        # Statistics
        self.events_from_cpp = 0
        self.events_enriched = 0
        self.events_persisted = 0
        self.events_failed = 0

    def start(self):
        """Start background worker thread to drain C++ queue"""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self, timeout_seconds: int = 10):
        """Stop worker thread and drain queue"""
        self.running = False

        # Wait for worker to finish
        if self.worker_thread:
            self.worker_thread.join(timeout=timeout_seconds)

    def process_events(self, max_events: int = 100) -> int:
        """
        Process events from C++ queue (non-blocking).

        Args:
            max_events: Maximum number of events to process

        Returns:
            Number of events processed
        """
        processed = 0

        for _ in range(max_events):
            # Call C++ dequeue function
            try:
                # The FFI lib should have watcher_dequeue_fast_path_event function
                self.lib.watcher_dequeue_fast_path_event.restype = ctypes.c_char_p
                json_bytes = self.lib.watcher_dequeue_fast_path_event()

                if not json_bytes:
                    # Queue is empty
                    break

                # Parse JSON event from C++
                json_str = json_bytes.decode('utf-8')
                if not json_str:
                    continue

                event_dict = json.loads(json_str)
                self.events_from_cpp += 1

                # Enrich using Phase 2 pipeline
                try:
                    enriched = self._enrich_event(event_dict)
                    enriched_dict = enriched.to_dict()

                    # Persist to JSONL
                    success = self.writer.write_event(enriched_dict)
                    if success:
                        self.events_persisted += 1
                    else:
                        self.events_failed += 1

                    self.events_enriched += 1
                    processed += 1

                except Exception as e:
                    self.events_failed += 1
                    print(f"Error enriching event: {e}", flush=True)

            except Exception as e:
                print(f"Error dequeuing event from C++: {e}", flush=True)
                break

        return processed

    def _enrich_event(self, event_dict: Dict[str, Any]):
        """
        Enrich a fast-path event from C++.

        Args:
            event_dict: Event from C++ queue

        Returns:
            EnrichedEvent from Phase 2 enrichment pipeline
        """
        # Extract fields from C++ event
        event_id = event_dict.get('event_id', 'unknown')
        timestamp_ns = event_dict.get('timestamp_ns', 0)
        ip = event_dict.get('ip', 0)
        tid = event_dict.get('tid')
        page_base_str = event_dict.get('page_base', '0x0')

        # Parse page_base (hex string like "0x7f0000")
        try:
            page_base = int(page_base_str, 16)
        except (ValueError, TypeError):
            page_base = 0

        # Look up variable info from registry
        variable_id, variable_name, scope = self._lookup_variable(page_base)

        # Read snapshots from C++ core
        before_snapshot = self.watcher_core.lib.watcher_read_snapshot(
            variable_id.encode() if variable_id else b"unknown"
        ) or b""

        after_snapshot = before_snapshot  # In this simplified version, we approximate

        # Use Phase 2 enricher
        enriched = self.enricher.enrich(
            event_id=event_id,
            timestamp_ns=timestamp_ns,
            ip=ip,
            tid=tid,
            variable_id=variable_id or "unknown",
            variable_name=variable_name or "unknown_var",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            scope=scope,
        )

        return enriched

    def _lookup_variable(self, page_base: int) -> tuple:
        """
        Look up variable info by page base address.

        Args:
            page_base: Memory address of page

        Returns:
            (variable_id, variable_name, scope) tuple
        """
        # For now, simplified lookup from watcher_core.variables
        if hasattr(self.watcher_core, 'variables'):
            for var_id, (shadow, proxy) in self.watcher_core.variables.items():
                if shadow.page_base == page_base or id(shadow.mmap_obj) == page_base:
                    return var_id, proxy._name, None

        return None, None, None

    def _worker_loop(self):
        """Background worker thread continuously drains C++ queue"""
        while self.running:
            try:
                self.process_events(max_events=50)
                time.sleep(self.poll_interval)
            except Exception as e:
                print(f"Error in event bridge worker: {e}", flush=True)

    def get_stats(self) -> dict:
        """Get bridge statistics"""
        return {
            'events_from_cpp': self.events_from_cpp,
            'events_enriched': self.events_enriched,
            'events_persisted': self.events_persisted,
            'events_failed': self.events_failed,
        }


class SyncEventBridge:
    """Synchronous version of event bridge for blocking integration"""

    def __init__(self, watcher_core, enricher, writer):
        """
        Initialize sync event bridge.

        Args:
            watcher_core: WatcherCore instance
            enricher: EventEnricher instance
            writer: EventWriter instance
        """
        self.watcher_core = watcher_core
        self.enricher = enricher
        self.writer = writer
        self.bridge = EventBridge(watcher_core, enricher, writer)

    def process_until_empty(self, timeout_seconds: float = 5):
        """Process all events from C++ queue until empty"""
        start_time = time.time()
        consecutive_empty = 0

        while time.time() - start_time < timeout_seconds:
            processed = self.bridge.process_events(max_events=100)

            if processed == 0:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    # Queue has been empty for 3 polls, assume drained
                    break
                time.sleep(0.01)
            else:
                consecutive_empty = 0

    def get_stats(self) -> dict:
        """Get statistics from bridge"""
        return self.bridge.get_stats()
