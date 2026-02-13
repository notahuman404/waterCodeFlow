"""
Example Custom Processor for Watcher

This processor demonstrates how to filter, annotate, and enrich events.
Use with: --custom-processor examples/processor_example.py
"""

import json
from typing import Any, Dict

def main(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a Watcher event.
    
    Args:
        event: Enriched event dict containing:
            - event_id: str (UUID)
            - ts_ns: int (timestamp in nanoseconds)
            - page_base: str (hex address)
            - fault_addr: str (hex address)
            - tid: int (thread ID)
            - ip: str (hex instruction pointer)
            - symbol: str (function name)
            - file: str (source file path)
            - line: int (line number)
            - deltas: list of (offset, old_bytes, new_bytes)
            - variable_ids: list of str
            - sql_context_id: optional str
    
    Returns:
        Action dict with one of:
        {
            "action": "pass"      # Pass through unchanged
        }
        {
            "action": "drop"      # Drop event from persistence
        }
        {
            "action": "annotate",
            "annotations": {...}  # Add fields to event
        }
        {
            "action": "enrich",
            "extra": {...}        # Add nested structure
        }
    """
    
    # Example 1: Filter out high-frequency mutations
    if len(event.get("deltas", [])) > 100:
        print(f"[FILTER] Dropping event {event['event_id']}: too many deltas ({len(event['deltas'])})")
        return {"action": "drop"}
    
    # Example 2: Annotate events from specific files
    if "user_code" in event.get("file", ""):
        return {
            "action": "annotate",
            "annotations": {
                "priority": "high",
                "needs_review": True,
                "domain": "user_logic"
            }
        }
    
    # Example 3: Annotate SQL-related mutations
    if event.get("sql_context_id"):
        return {
            "action": "annotate",
            "annotations": {
                "has_sql_context": True,
                "query_related": True
            }
        }
    
    # Example 4: Enrich with computed fields
    deltas = event.get("deltas", [])
    if deltas:
        total_bytes_changed = sum(d[1] for d in deltas)  # Sum of lengths
        
        return {
            "action": "enrich",
            "extra": {
                "mutation_analysis": {
                    "total_deltas": len(deltas),
                    "total_bytes_changed": total_bytes_changed,
                    "average_delta_size": total_bytes_changed / len(deltas) if deltas else 0
                }
            }
        }
    
    # Example 5: Default - pass through
    return {"action": "pass"}


# ============================================================================
# Advanced Example: Stateful Processor
# ============================================================================

class StatefulProcessor:
    """
    Example of a stateful processor that tracks patterns across events.
    """
    
    def __init__(self):
        self.event_count = 0
        self.mutations_per_var = {}
        self.high_frequency_vars = set()
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process with state tracking"""
        self.event_count += 1
        
        # Track mutations per variable
        for var_id in event.get("variable_ids", []):
            if var_id not in self.mutations_per_var:
                self.mutations_per_var[var_id] = 0
            self.mutations_per_var[var_id] += 1
            
            # Detect high-frequency mutations
            if self.mutations_per_var[var_id] > 1000:
                self.high_frequency_vars.add(var_id)
        
        # Annotate high-frequency mutations
        for var_id in event.get("variable_ids", []):
            if var_id in self.high_frequency_vars:
                return {
                    "action": "annotate",
                    "annotations": {
                        "high_frequency": True,
                        "mutation_count": self.mutations_per_var[var_id]
                    }
                }
        
        return {"action": "pass"}


# ============================================================================
# Example: Filter by Pattern
# ============================================================================

PATTERNS_TO_IGNORE = [
    "/usr/lib",          # System library mutations
    "/virtual/",         # Virtual environment
    "<string>",          # Dynamic code
]

def main_with_patterns(event: Dict[str, Any]) -> Dict[str, Any]:
    """Filter based on file path patterns"""
    file_path = event.get("file", "")
    
    for pattern in PATTERNS_TO_IGNORE:
        if pattern in file_path:
            return {"action": "drop"}
    
    return {"action": "pass"}


# ============================================================================
# Example: Rate Limiting
# ============================================================================

import time

class RateLimiter:
    """Limit events from same location"""
    
    def __init__(self, max_per_second: int = 10):
        self.max_per_second = max_per_second
        self.location_times = {}
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Rate limit by file:line location"""
        location = f"{event['file']}:{event['line']}"
        now = time.time()
        
        if location not in self.location_times:
            self.location_times[location] = []
        
        # Remove old timestamps (> 1 second ago)
        self.location_times[location] = [
            t for t in self.location_times[location]
            if now - t < 1.0
        ]
        
        # Check if rate exceeded
        if len(self.location_times[location]) >= self.max_per_second:
            return {"action": "drop"}
        
        self.location_times[location].append(now)
        return {"action": "pass"}
