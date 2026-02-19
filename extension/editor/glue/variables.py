"""
Variable analysis — uses real watcher JSONL events and codevovle diffs,
with AST-based fallback for source files with no recorded data yet.

Priority:
1. Watcher JSONL events in built/watcher_events/<runId>/*.jsonl
   (produced by watcher CLI when C++ core is available)
2. Codevovle diffs in .codevovle/diffs/*.diff
   (parse diff hunks to count per-variable appearances)
3. Python/JS AST analysis of the source file
   (pure static analysis, no runtime data needed)
"""
from __future__ import annotations

import ast
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .errors import GlueError


# ── Watcher JSONL events ──────────────────────────────────────────────────────

def _watcher_events_root() -> Path:
    return Path(os.getcwd()) / "built" / "watcher_events"


def _read_watcher_events_for_file(file_path: str) -> List[Dict[str, Any]]:
    """Read all watcher JSONL events that mention file_path."""
    root = _watcher_events_root()
    if not root.exists():
        return []
    events = []
    for run_dir in root.iterdir():
        if not run_dir.is_dir():
            continue
        for jl in run_dir.glob("*.jsonl"):
            try:
                for line in jl.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        ev_file = ev.get("file", "")
                        if not file_path or ev_file == file_path:
                            events.append(ev)
                    except Exception:
                        pass
            except Exception:
                pass
    return events


def _variables_from_watcher_events(file_path: str) -> List[Dict[str, Any]]:
    events = _read_watcher_events_for_file(file_path)
    if not events:
        return []
    counts: Dict[str, int] = defaultdict(int)
    for ev in events:
        for var_id in ev.get("variable_ids", []):
            counts[var_id] += 1
    if not counts:
        return []
    return [
        {"name": name, "evolutions": count, "scope": "tracked"}
        for name, count in sorted(counts.items(), key=lambda x: -x[1])
    ]


# ── Codevovle diff analysis ───────────────────────────────────────────────────

def _variables_from_codevovle_diffs(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse .codevovle/diffs/*.diff files to count how many diffs mention
    each variable name from the source file.
    """
    try:
        from codevovle.storage import DiffManager
        tick_ids = DiffManager.list_all()
    except Exception:
        return []

    if not tick_ids:
        return []

    # Get variable names from AST to know what to count
    ast_vars = {v["name"] for v in _extract_variables_ast(file_path)}
    if not ast_vars:
        return []

    # Count how many diffs mention each variable
    counts: Dict[str, int] = defaultdict(int)
    for tick_id in tick_ids:
        try:
            from codevovle.storage import DiffManager
            diff = DiffManager.read(tick_id)
            for name in ast_vars:
                if re.search(rf"\b{re.escape(name)}\b", diff):
                    counts[name] += 1
        except Exception:
            pass

    if not counts:
        return []

    return [
        {"name": name, "evolutions": count, "scope": "codevovle"}
        for name, count in sorted(counts.items(), key=lambda x: -x[1])
    ]


# ── AST analysis ──────────────────────────────────────────────────────────────

def _name_of(node) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    return None


def _names_in_target(node) -> List[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names = []
        for elt in node.elts:
            names.extend(_names_in_target(elt))
        return names
    return []


def _extract_variables_ast(file_path: str) -> List[Dict[str, Any]]:
    """Parse a Python file and return interesting variable names with assignment counts."""
    try:
        src = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    try:
        tree = ast.parse(src, filename=file_path)
    except SyntaxError:
        return []

    assignment_counts: Dict[str, int] = defaultdict(int)
    first_line: Dict[str, int] = {}
    scope_map: Dict[str, str] = {}

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self._scope = "global"

        def visit_FunctionDef(self, node):
            old = self._scope
            self._scope = "local"
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                name = arg.arg
                if name in ("self", "cls"):
                    continue
                assignment_counts[name] += 1
                first_line.setdefault(name, node.lineno)
                scope_map.setdefault(name, "parameter")
            self.generic_visit(node)
            self._scope = old

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Assign(self, node):
            for target in node.targets:
                for name in _names_in_target(target):
                    assignment_counts[name] += 1
                    first_line.setdefault(name, node.lineno)
                    scope_map.setdefault(name, self._scope)
            self.generic_visit(node)

        def visit_AugAssign(self, node):
            name = _name_of(node.target)
            if name:
                assignment_counts[name] += 1
                first_line.setdefault(name, node.lineno)
                scope_map.setdefault(name, self._scope)
            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            name = _name_of(node.target)
            if name:
                assignment_counts[name] += 1
                first_line.setdefault(name, node.lineno)
                scope_map.setdefault(name, self._scope)
            self.generic_visit(node)

        def visit_For(self, node):
            name = _name_of(node.target)
            if name:
                assignment_counts[name] += 1
                first_line.setdefault(name, node.lineno)
                scope_map.setdefault(name, self._scope)
            self.generic_visit(node)

    Visitor().visit(tree)

    # Skip: bare '_', bare '__', dunder names (__xxx__), and pure digit strings.
    # Single-letter variables like x, y, i and _private-style names are kept.
    SKIP = re.compile(r"^(_$|__$|__\w+__|^\d+$)")
    results = []
    for name, count in sorted(assignment_counts.items(), key=lambda x: -x[1]):
        if SKIP.match(name):
            continue
        results.append({
            "name": name,
            "evolutions": count,
            "scope": scope_map.get(name, "global"),
            "line_no": first_line.get(name, 0),
        })
    return results[:40]


# ── Public API ────────────────────────────────────────────────────────────────


def list_tracked_variables(file_path: str) -> List[Dict[str, Any]]:
    """
    Return variables for file_path, using the richest available data source.

    1. Watcher JSONL events (runtime mutation data, most accurate)
    2. Codevovle diff mentions (which variables changed across recordings)
    3. AST assignment counts (static analysis, always available)
    """
    # Try watcher events first (richest data)
    result = _variables_from_watcher_events(file_path)
    if result:
        return result

    # Try codevovle diff analysis
    result = _variables_from_codevovle_diffs(file_path)
    if result:
        return result

    # Always fall back to AST — works even with no recorded data
    return _extract_variables_ast(file_path)


def get_variable_timeline(
    file_path: str, variable_name: str, max_ticks: int = 200
) -> List[Dict[str, Any]]:
    """
    Return a timeline for variable_name.

    1. Watcher JSONL events (exact mutation events with timestamps)
    2. Codevovle diffs that mention the variable (approximate)
    3. Source line occurrences (static)
    """
    # Try watcher events
    events = _read_watcher_events_for_file(file_path)
    if events:
        timeline = []
        for i, ev in enumerate(events):
            if variable_name in ev.get("variable_ids", []):
                timeline.append({
                    "tick": ev.get("event_id", str(i)),
                    "ts_ns": ev.get("ts_ns", 0),
                    "symbol": ev.get("symbol", "?"),
                    "file": ev.get("file", file_path),
                    "line": ev.get("line", 0),
                })
                if len(timeline) >= max_ticks:
                    break
        if timeline:
            return timeline

    # Try codevovle diffs
    try:
        from codevovle.storage import DiffManager
        tick_ids = DiffManager.list_all()
        pattern = re.compile(rf"\b{re.escape(variable_name)}\b")
        timeline = []
        for tick_id in tick_ids:
            try:
                diff = DiffManager.read(tick_id)
                if pattern.search(diff):
                    # Find the changed lines that mention the variable
                    for line in diff.splitlines():
                        if (line.startswith('+') or line.startswith('-')) and pattern.search(line):
                            timeline.append({
                                "tick": tick_id,
                                "change_type": "added" if line.startswith('+') else "removed",
                                "snippet": line[1:].strip(),
                            })
                            break
                if len(timeline) >= max_ticks:
                    break
            except Exception:
                pass
        if timeline:
            return timeline
    except Exception:
        pass

    # Fallback: source file occurrences
    try:
        src = Path(file_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    pattern = re.compile(rf"\b{re.escape(variable_name)}\b")
    lines = src.splitlines()
    timeline = []
    for idx, line in enumerate(lines, start=1):
        if pattern.search(line):
            ctx_start = max(0, idx - 3)
            ctx_end = min(len(lines), idx + 2)
            timeline.append({
                "tick": "HEAD",
                "line_no": idx,
                "snippet": line.strip(),
                "context": "\n".join(lines[ctx_start:ctx_end]),
            })
            if len(timeline) >= max_ticks:
                break
    return timeline
