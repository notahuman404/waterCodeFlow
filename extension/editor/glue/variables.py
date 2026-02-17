"""Variable-focused helpers for UI: naive timeline reconstruction and listing.

Provides variable-centric queries like fetching value changes across ticks,
listing tracked variables, and reconstructing variable timelines.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Pattern
import re

from .errors import GlueError


def _safe_import(name: str):
    """Safely import a module, returning None on any import failure."""
    try:
        return __import__(name, fromlist=["*"])
    except Exception:
        return None


def _extract_variable_pattern(variable_name: str) -> Pattern:
    """Create a regex pattern to find variable assignments and usage.

    Matches patterns like:
    - name = ...
    - name: ...
    - return name
    - print(name)
    """
    # Escape special regex chars in the variable name
    escaped = re.escape(variable_name)
    # Match word boundaries to avoid partial matches
    return re.compile(rf"\b{escaped}\b")


def get_variable_timeline(
    file_path: str, variable_name: str, max_ticks: int = 200
) -> List[Dict[str, Any]]:
    """Return a best-effort timeline for `variable_name` in `file_path`.

    Reconstruction approach:
    1. Read current file content
    2. Search for the variable name and return matching lines
    3. (Future) iterate over ticks using DiffManager to build true timeline

    Returns:
        List of timeline entries: {"tick": str, "line_no": int, "snippet": str, "context": str}
    """
    # Try to read the file to get current state
    timeline = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        # If file not readable, return empty timeline
        return []

    pattern = _extract_variable_pattern(variable_name)
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        if pattern.search(line):
            # Found a match
            context_start = max(0, idx - 3)
            context_end = min(len(lines), idx + 2)
            context = "\n".join(lines[context_start:context_end])

            timeline.append(
                {
                    "tick": "HEAD",
                    "line_no": idx,
                    "snippet": line.strip(),
                    "context": context,
                    "match_count": len(pattern.findall(line)),
                }
            )

            if len(timeline) >= max_ticks:
                break

    return timeline


def get_variable_value_at_tick(
    file_path: str, variable_name: str, tick_id: Optional[int] = None
) -> Optional[str]:
    """Extract the value of a variable at a specific tick (best-effort).

    This is a naive implementation that tries to find simple assignments.
    Future: integrate with proper AST parsing or reconstructed state.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    # Simple pattern: look for "name = value" or "name: type = value"
    patterns = [
        rf"{re.escape(variable_name)}\s*=\s*(.+?)(?:\n|#|$)",
        rf"{re.escape(variable_name)}\s*:\s*\w+\s*=\s*(.+?)(?:\n|#|$)",
    ]

    for pattern_str in patterns:
        match = re.search(pattern_str, content)
        if match:
            return match.group(1).strip()

    return None


def list_tracked_variables(file_path: str) -> List[Dict[str, Any]]:
    """Return variables configured for tracking in a file's config if present.

    Current implementation:
    - Checks CodeVovle config for "tracked_variables" setting
    - Falls back to empty list

    Future: can be enhanced to infer tracked variables from config or AST analysis.
    """
    storage = _safe_import("codevovle.storage")
    if not storage:
        return []

    try:
        ConfigManager = getattr(storage, "ConfigManager", None)
        if not ConfigManager:
            return []

        config = ConfigManager.get_file_config(file_path)
        if config and "tracked_variables" in config:
            tracked = config["tracked_variables"]
            if isinstance(tracked, list):
                return [{"name": v, "scope": "global"} for v in tracked]

        return []
    except Exception:
        return []


def infer_variables_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Infer interesting variables from a file using simple heuristics.

    Looks for:
    - Function parameters
    - Top-level assignments
    - Return statements

    Returns:
        List of {"name": str, "scope": str, "line_no": int}
    """
    variables = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    # Regex patterns for common variable declarations
    patterns = [
        (r"def\s+\w+\s*\(\s*([^)]+)\s*\)", "parameter"),  # Function parameters
        (r"^\s*(\w+)\s*=\s*", "assignment"),  # Top-level assignments
        (r"return\s+(\w+)", "return"),  # Return statements
    ]

    seen = set()

    for line_no, line in enumerate(lines, start=1):
        for pattern, scope in patterns:
            match = re.search(pattern, line)
            if match:
                # Extract variable name(s)
                if scope == "parameter":
                    # Parse comma-separated parameters
                    params_str = match.group(1)
                    for param in params_str.split(","):
                        var_name = param.split("=")[0].strip()
                        if var_name and var_name not in seen:
                            variables.append(
                                {"name": var_name, "scope": scope, "line_no": line_no}
                            )
                            seen.add(var_name)
                else:
                    var_name = match.group(1).strip()
                    if var_name and var_name not in seen:
                        variables.append(
                            {"name": var_name, "scope": scope, "line_no": line_no}
                        )
                        seen.add(var_name)

    return variables


def track_variable_changes(
    file_path: str, variable_name: str, tick_start: int, tick_end: int
) -> List[Dict[str, Any]]:
    """Track changes to a variable across a range of ticks (future implementation).

    For now, returns empty list. Real implementation would:
    1. Fetch diffs for ticks in range
    2. Parse each diff to find lines mentioning the variable
    3. Build a timeline of changes

    Returns:
        List of changes: {"tick": int, "change_type": str, "before": str, "after": str}
    """
    # Placeholder for future feature requiring diff parsing and state reconstruction
    return []
