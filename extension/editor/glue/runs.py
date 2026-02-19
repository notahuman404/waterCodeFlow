"""
Run-centric queries — reads both:
  1. built/recordings/*.json  (spawnRun output: stdout/stderr/exitCode/durationMs)
  2. .codevovle/              (codevovle diff-based tick data)

A "run" in the recordings UI is one spawnRun session.
Each recording JSON is surfaced as one run.

Codevovle ticks are a separate concept (continuous background recording
triggered by `codevovle daemon start`), exposed via listRuns with the
legacy tick grouping logic when recordings are absent.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .errors import GlueError
from .api import _read_recording_files, delete_recording


# ── spawnRun-based runs ───────────────────────────────────────────────────────


def get_runs(file_path: str, gap_threshold_seconds: float = 30.0) -> List[Dict[str, Any]]:
    """
    Return all runs for file_path.

    Priority:
    1. spawnRun recording JSONs (built/recordings/*.json)
    2. codevovle diff ticks (.codevovle/diffs/) if no JSON recordings exist

    Each run exposes both new-style fields (runId, timestamp, stdout, …)
    and legacy fields (run_id, tick_count) for backwards compat.
    """
    recordings = _read_recording_files(file_path)
    if recordings:
        return [_recording_to_run(rec, i) for i, rec in enumerate(recordings)]

    # Fallback: codevovle tick-based grouping
    return _codevovle_tick_runs(file_path, gap_threshold_seconds)


def _recording_to_run(rec: Dict[str, Any], index: int) -> Dict[str, Any]:
    run_id = rec.get("runId", f"run-{index}")
    stdout = rec.get("stdout", "")
    stderr = rec.get("stderr", "")
    output_lines = len([l for l in (stdout + stderr).splitlines() if l.strip()])
    return {
        # Legacy fields
        "run_id": run_id,
        "tick_count": output_lines,
        # Full recording fields
        "runId": run_id,
        "filePath": rec.get("filePath", ""),
        "language": rec.get("language", "python"),
        "exitCode": rec.get("exitCode", 0),
        "timestamp": rec.get("timestamp", ""),
        "durationMs": rec.get("durationMs", 0),
        "stdout": stdout,
        "stderr": stderr,
        "useWatcher": rec.get("useWatcher", False),
        "variables": rec.get("variables", []),
    }


def _codevovle_tick_runs(file_path: str, gap_threshold_seconds: float) -> List[Dict[str, Any]]:
    """Group codevovle diff ticks into logical runs by time gap."""
    try:
        from codevovle.storage import DiffManager, BranchManager, StateManager
    except ImportError:
        return []

    try:
        tick_ids = sorted(DiffManager.list_all())
    except Exception:
        return []

    if not tick_ids:
        return []

    runs = []
    run_idx = 0
    start_tick = tick_ids[0]
    prev_tick = tick_ids[0]

    for tick in tick_ids[1:]:
        if tick - prev_tick > gap_threshold_seconds:
            runs.append(_make_tick_run(run_idx, start_tick, prev_tick))
            run_idx += 1
            start_tick = tick
        prev_tick = tick

    runs.append(_make_tick_run(run_idx, start_tick, prev_tick))
    return runs


def _make_tick_run(run_idx: int, start_tick: int, end_tick: int) -> Dict[str, Any]:
    run_id = f"codevovle-run-{run_idx}"
    return {
        "run_id": run_id,
        "tick_count": end_tick - start_tick + 1,
        "runId": run_id,
        "filePath": "",
        "language": "python",
        "exitCode": 0,
        "timestamp": "",
        "durationMs": 0,
        "stdout": "",
        "stderr": "",
        "useWatcher": False,
        "variables": [],
        # codevovle-specific
        "start_tick": start_tick,
        "end_tick": end_tick,
        "estimated_duration_seconds": end_tick - start_tick,
    }


def get_run_details(file_path: str, run_id: str) -> Dict[str, Any]:
    for run in get_runs(file_path):
        if run.get("runId") == run_id or run.get("run_id") == run_id:
            return run
    raise GlueError(f"Run {run_id!r} not found for {file_path!r}")


def delete_run(file_path: str, run_id: str) -> int:
    """Delete a spawnRun recording. Returns 1 if deleted, 0 otherwise."""
    if delete_recording(run_id):
        return 1
    # Try codevovle tick deletion
    try:
        from codevovle.storage import DiffManager
        run = get_run_details(file_path, run_id)
        start_tick = run.get("start_tick")
        end_tick = run.get("end_tick")
        if start_tick is not None and end_tick is not None:
            count = 0
            for tick in range(start_tick, end_tick + 1):
                if DiffManager.exists(tick):
                    DiffManager.delete(tick)
                    count += 1
            return count
    except Exception:
        pass
    return 0
