"""Run-centric tracking: group recordings into logical runs/sessions.

A "run" is a logical grouping of recordings, typically representing a single
editing/execution session. Runs are tracked via time-based gaps in recordings.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import time

from .errors import GlueError


def _safe_import(name: str):
    """Safely import a module, returning None on any import failure."""
    try:
        return __import__(name, fromlist=["*"])
    except Exception:
        return None


def get_runs(file_path: str, gap_threshold_seconds: float = 30.0) -> List[Dict[str, Any]]:
    """Group recordings into runs based on time gaps.

    A new run starts when the time gap between consecutive recordings
    exceeds `gap_threshold_seconds`.

    Returns:
        List of run dicts: {"run_id", "start_tick", "end_tick", "tick_count", "estimated_duration_seconds"}
    """
    storage = _safe_import("codevovle.storage")
    if not storage:
        return []

    try:
        DiffManager = getattr(storage, "DiffManager", None)
        if not DiffManager:
            return []

        tick_ids = sorted(DiffManager.list_all())
        if not tick_ids:
            return []

        # Simple heuristic: assume each tick represents ~1 second of elapsed time
        # (this is naive; real implementation would track timestamps)
        runs = []
        run_id = 0
        start_tick = tick_ids[0]
        prev_tick = tick_ids[0]

        for tick in tick_ids[1:]:
            # If gap is large, start a new run
            if tick - prev_tick > gap_threshold_seconds:
                runs.append(
                    {
                        "run_id": run_id,
                        "start_tick": start_tick,
                        "end_tick": prev_tick,
                        "tick_count": prev_tick - start_tick + 1,
                        "estimated_duration_seconds": prev_tick - start_tick,
                    }
                )
                run_id += 1
                start_tick = tick

            prev_tick = tick

        # Include final run
        if start_tick <= prev_tick:
            runs.append(
                {
                    "run_id": run_id,
                    "start_tick": start_tick,
                    "end_tick": prev_tick,
                    "tick_count": prev_tick - start_tick + 1,
                    "estimated_duration_seconds": prev_tick - start_tick,
                }
            )

        return runs
    except Exception:
        return []


def get_run_details(file_path: str, run_id: int) -> Dict[str, Any]:
    """Get detailed metadata for a specific run."""
    runs = get_runs(file_path)
    for run in runs:
        if run["run_id"] == run_id:
            return run

    raise GlueError(f"Run {run_id} not found")


def list_all_runs(file_path: str) -> Dict[str, Any]:
    """Return summary of all runs for a file."""
    runs = get_runs(file_path)

    return {
        "file_path": file_path,
        "total_runs": len(runs),
        "runs": runs,
    }


def delete_run(file_path: str, run_id: int) -> int:
    """Delete all recordings in a run. Returns count deleted."""
    storage = _safe_import("codevovle.storage")
    if not storage:
        raise GlueError("storage module not available")

    DiffManager = getattr(storage, "DiffManager", None)
    if not DiffManager:
        raise GlueError("DiffManager not available")

    try:
        runs = get_runs(file_path)
        target_run = None
        for r in runs:
            if r["run_id"] == run_id:
                target_run = r
                break

        if not target_run:
            raise GlueError(f"Run {run_id} not found")

        count = 0
        for tick_id in range(target_run["start_tick"], target_run["end_tick"] + 1):
            try:
                if DiffManager.exists(tick_id):
                    DiffManager.delete(tick_id)
                    count += 1
            except Exception:
                pass

        return count
    except GlueError:
        raise
    except Exception as e:
        raise GlueError(f"delete_run failed: {e}")


def merge_runs(file_path: str, run_ids: List[int]) -> bool:
    """Merge multiple runs into one logical run (no-op for now, future: add tagging)."""
    # This is a placeholder for future enhancement where we could tag runs together
    if not run_ids or len(run_ids) < 2:
        raise GlueError("merge_runs requires at least 2 run IDs")
    return True


def tag_run(file_path: str, run_id: int, tag: str) -> bool:
    """Tag a run with metadata (e.g., 'bug_fix', 'refactor'). Future: persist tags."""
    # Placeholder for future UI feature to label runs
    return True
