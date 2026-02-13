"""
Event Enrichment Pipeline

Takes fast-path events and enriches them with detailed information:
- Byte-level deltas (what bytes changed)
- Symbol resolution (function name, file, line)
- Context information (SQL context, thread data)
"""

import struct
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import OrderedDict


@dataclass
class EnrichedEvent:
    """Fully enriched event ready for persistence"""
    event_id: str
    timestamp_ns: int
    variable_id: str
    variable_name: str

    # Symbol information
    function_name: str
    file_path: str
    line_number: int

    # Mutation details
    deltas: List[Dict[str, Any]]  # [{offset, before, after}, ...]

    # Context
    thread_id: Optional[int] = None
    sql_context: Optional[Dict[str, str]] = None

    # Variable scope (from config)
    scope: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'event_id': self.event_id,
            'timestamp_ns': self.timestamp_ns,
            'variable_id': self.variable_id,
            'variable_name': self.variable_name,
            'function': self.function_name,
            'file': self.file_path,
            'line': self.line_number,
            'deltas': self.deltas,
            'thread_id': self.thread_id,
            'sql_context': self.sql_context,
            'scope': self.scope,
        }


class DeltaComputer:
    """Computes byte-level deltas between two snapshots"""

    @staticmethod
    def compute_deltas(before: bytes, after: bytes) -> List[Dict[str, Any]]:
        """
        Compute byte-level differences between before and after snapshots.

        Returns list of {offset: int, before: hex_str, after: hex_str}
        """
        deltas = []

        # Ensure same length
        min_len = min(len(before), len(after))

        for i in range(min_len):
            if before[i] != after[i]:
                deltas.append({
                    'offset': i,
                    'before': hex(before[i]),
                    'after': hex(after[i]),
                })

        # Handle size changes
        if len(before) != len(after):
            deltas.append({
                'size_change': f"{len(before)} -> {len(after)}"
            })

        return deltas


class SymbolCache:
    """LRU cache for IP -> symbol resolution with TTL"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Dict[str, str], float]] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, ip_str: str) -> Optional[Dict[str, str]]:
        """Get cached symbol, return None if expired or missing"""
        with self.lock:
            if ip_str not in self.cache:
                return None

            symbol_info, timestamp = self.cache[ip_str]

            # Check TTL
            if time.time() - timestamp > self.ttl_seconds:
                del self.cache[ip_str]
                return None

            # Move to end (LRU)
            self.cache.move_to_end(ip_str)
            return symbol_info

    def set(self, ip_str: str, symbol_info: Dict[str, str]):
        """Cache a symbol resolution"""
        with self.lock:
            if ip_str in self.cache:
                self.cache.move_to_end(ip_str)

            self.cache[ip_str] = (symbol_info, time.time())

            # Evict LRU if over capacity
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)


class SymbolResolver:
    """Resolves instruction pointers to function:file:line"""

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or "/proc/self/exe"
        self.cache = SymbolCache()

    def resolve(self, ip: int) -> Dict[str, str]:
        """
        Resolve IP address to symbol information.

        Returns:
            {
                'function': 'function_name',
                'file': 'path/to/file.py',
                'line': 42
            }
        """
        ip_str = hex(ip)

        # Check cache first
        cached = self.cache.get(ip_str)
        if cached is not None:
            return cached

        # Resolve via subprocess
        try:
            result = subprocess.run(
                ['addr2line', '-e', self.binary_path, ip_str],
                capture_output=True,
                text=True,
                timeout=1.0  # 1 second timeout
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                # Format: "function at file:line"
                parts = output.split(' at ')

                if len(parts) == 2:
                    function_name = parts[0]
                    file_line = parts[1]  # "file.py:42"

                    file_parts = file_line.rsplit(':', 1)
                    if len(file_parts) == 2:
                        file_path = file_parts[0]
                        line_num = int(file_parts[1]) if file_parts[1].isdigit() else 0

                        symbol_info = {
                            'function': function_name,
                            'file': file_path,
                            'line': line_num
                        }
                        self.cache.set(ip_str, symbol_info)
                        return symbol_info
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass

        # Fallback
        fallback = {
            'function': '??',
            'file': '??',
            'line': 0
        }
        self.cache.set(ip_str, fallback)
        return fallback


class EventEnricher:
    """Enriches fast-path events with detailed information"""

    def __init__(self, binary_path: Optional[str] = None):
        self.symbol_resolver = SymbolResolver(binary_path)
        self.delta_computer = DeltaComputer()

    def enrich(
        self,
        event_id: str,
        timestamp_ns: int,
        ip: int,
        tid: Optional[int],
        variable_id: str,
        variable_name: str,
        before_snapshot: bytes,
        after_snapshot: bytes,
        sql_context: Optional[Dict[str, str]] = None,
        scope: Optional[str] = None,
    ) -> EnrichedEvent:
        """
        Enrich a fast-path event with full details.

        Args:
            event_id: Unique event identifier
            timestamp_ns: Event timestamp in nanoseconds
            ip: Instruction pointer address
            tid: Thread ID (optional)
            variable_id: ID of watched variable
            variable_name: Name of variable
            before_snapshot: Memory snapshot before mutation
            after_snapshot: Memory snapshot after mutation
            sql_context: SQL context if tracking SQL
            scope: Variable scope (local/global/both/unknown)

        Returns:
            EnrichedEvent with all details populated
        """
        # Resolve symbol
        symbol_info = self.symbol_resolver.resolve(ip)

        # Compute deltas
        deltas = self.delta_computer.compute_deltas(before_snapshot, after_snapshot)

        # Build enriched event
        return EnrichedEvent(
            event_id=event_id,
            timestamp_ns=timestamp_ns,
            variable_id=variable_id,
            variable_name=variable_name,
            function_name=symbol_info['function'],
            file_path=symbol_info['file'],
            line_number=symbol_info['line'],
            deltas=deltas,
            thread_id=tid,
            sql_context=sql_context,
            scope=scope,
        )
