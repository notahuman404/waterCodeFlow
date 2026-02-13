"""
Event Writer - JSONL Persistence

Writes enriched events to JSONL format (one JSON object per line).
Uses fast buffered writes and handles disk pressure gracefully.
"""

import json
import os
import threading
from pathlib import Path
from typing import Optional, List
from queue import Queue
import time


class EventWriter:
    """Writes enriched events to JSONL file"""

    def __init__(self, output_dir: str, max_buffer_events: int = 1000):
        """
        Initialize event writer.

        Args:
            output_dir: Directory to write events to
            max_buffer_events: Max events to buffer before flush
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.events_file = self.output_dir / "events.jsonl"
        self.max_buffer_events = max_buffer_events

        # Write mode: 'w' initially (create), then 'a' (append)
        self.file_handle = None
        self._open_file()

        # Event buffer
        self.buffer: List[str] = []
        self.lock = threading.Lock()

        # Stats
        self.events_written = 0
        self.events_lost = 0

    def _open_file(self):
        """Open the output file for writing"""
        try:
            # Open in append mode to allow resuming
            self.file_handle = open(self.events_file, 'a', buffering=1)  # Line buffered
        except Exception as e:
            raise RuntimeError(f"Failed to open events file: {e}")

    def write_event(self, event_dict: dict) -> bool:
        """
        Write a single enriched event.

        Args:
            event_dict: Event as dictionary (from EnrichedEvent.to_dict())

        Returns:
            True if written successfully, False if lost due to error
        """
        with self.lock:
            try:
                # Serialize to JSON
                json_line = json.dumps(event_dict)

                # Add to buffer
                self.buffer.append(json_line)
                self.events_written += 1

                # Flush if buffer full
                if len(self.buffer) >= self.max_buffer_events:
                    self._flush_internal()

                return True

            except Exception as e:
                self.events_lost += 1
                # Log but don't crash
                print(f"Warning: Failed to write event: {e}", flush=True)
                return False

    def _flush_internal(self):
        """Flush buffer to disk (must hold lock)"""
        if not self.buffer:
            return

        try:
            for json_line in self.buffer:
                self.file_handle.write(json_line + '\n')

            self.file_handle.flush()
            os.fsync(self.file_handle.fileno())  # Force sync to disk
            self.buffer.clear()

        except IOError as e:
            # Disk write failed
            self.events_lost += len(self.buffer)
            self.buffer.clear()
            print(f"Error writing to disk: {e}", flush=True)

    def flush(self):
        """Explicitly flush all buffered events"""
        with self.lock:
            self._flush_internal()

    def close(self):
        """Close the event writer"""
        with self.lock:
            if self.buffer:
                self._flush_internal()

            if self.file_handle:
                try:
                    self.file_handle.close()
                except:
                    pass

                self.file_handle = None

    def get_stats(self) -> dict:
        """Get writer statistics"""
        with self.lock:
            return {
                'events_written': self.events_written,
                'events_lost': self.events_lost,
                'buffered': len(self.buffer),
                'output_file': str(self.events_file),
            }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class BatchEventWriter:
    """Writes events in batches from a queue (thread-safe)"""

    def __init__(self, output_dir: str, batch_size: int = 100):
        """
        Initialize batch writer with background thread.

        Args:
            output_dir: Directory to write events to
            batch_size: Size of batch to process
        """
        self.writer = EventWriter(output_dir)
        self.queue: Queue = Queue(maxsize=10000)
        self.batch_size = batch_size

        self.running = False
        self.worker_thread: Optional[threading.Thread] = None

    def start(self):
        """Start background worker thread"""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self, timeout_seconds: int = 5):
        """Stop background worker and drain queue"""
        self.running = False

        # Send sentinel to wake up worker
        try:
            self.queue.put(None, timeout=1.0)
        except:
            pass

        # Wait for worker to finish
        if self.worker_thread:
            self.worker_thread.join(timeout=timeout_seconds)

        # Flush remaining events
        self.writer.flush()
        self.writer.close()

    def enqueue_event(self, event_dict: dict) -> bool:
        """
        Enqueue an event for writing (non-blocking).

        Args:
            event_dict: Event as dictionary

        Returns:
            True if enqueued, False if queue full
        """
        try:
            self.queue.put(event_dict, block=False)
            return True
        except:
            return False

    def _worker_loop(self):
        """Background worker thread loop"""
        batch = []

        while self.running:
            try:
                # Collect batch
                while len(batch) < self.batch_size and self.running:
                    try:
                        event = self.queue.get(timeout=0.5)

                        # Sentinel to stop
                        if event is None:
                            break

                        batch.append(event)
                    except:
                        # Timeout waiting for event
                        break

                # Write batch
                for event in batch:
                    self.writer.write_event(event)

                batch.clear()

            except Exception as e:
                print(f"Worker thread error: {e}", flush=True)

    def get_stats(self) -> dict:
        """Get writer statistics"""
        stats = self.writer.get_stats()
        stats['queue_size'] = self.queue.qsize()
        return stats
