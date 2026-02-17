"""Public API facade used by UI code to query recordings, branches, daemon and insights.

Fully wired to CodeVovle storage managers for complete recording/metadata access.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import os
from .errors import GlueError


def _safe_import(name: str):
    """Safely import a module, returning None on any import failure."""
    try:
        return __import__(name, fromlist=["*"])
    except Exception:
        return None


def list_recordings(file_path: str) -> List[Dict[str, Any]]:
    """Return a list of all recording metadata for `file_path`.

    Each recording includes tick ID, diff summary, and estimated size.
    Sorted chronologically by tick ID.
    """
    storage = _safe_import("codevovle.storage")
    if not storage:
        return []

    try:
        DiffManager = getattr(storage, "DiffManager", None)
        if not DiffManager:
            return []

        # Get all tick IDs from DiffManager
        tick_ids = DiffManager.list_all()
        recordings = []

        for tick_id in tick_ids:
            try:
                diff = DiffManager.read(tick_id)
                # Compute simple metrics on the diff
                lines = diff.split("\n")
                added = sum(1 for l in lines if l.startswith("+"))
                removed = sum(1 for l in lines if l.startswith("-"))

                recordings.append(
                    {
                        "tick_id": tick_id,
                        "lines_added": added,
                        "lines_removed": removed,
                        "size_bytes": len(diff.encode("utf-8")),
                    }
                )
            except Exception:
                pass

        return recordings
    except Exception:
        return []


def get_recording(tick_id: int) -> Dict[str, Any]:
    """Return full recording details for `tick_id`.

    Includes the full unified diff and metadata.
    """
    storage = _safe_import("codevovle.storage")
    if not storage:
        raise GlueError("storage module not available")

    DiffManager = getattr(storage, "DiffManager", None)
    if not DiffManager:
        raise GlueError("DiffManager not available")

    try:
        if not DiffManager.exists(tick_id):
            raise GlueError(f"Recording {tick_id} not found")

        diff_content = DiffManager.read(tick_id)
        return {
            "tick_id": tick_id,
            "diff": diff_content,
            "size_bytes": len(diff_content.encode("utf-8")),
        }
    except GlueError:
        raise
    except Exception as e:
        raise GlueError(f"get_recording failed: {e}")


def delete_recording(tick_id: int) -> bool:
    """Delete a single recording by tick ID. Returns True if deleted."""
    storage = _safe_import("codevovle.storage")
    if not storage:
        raise GlueError("storage module not available")

    DiffManager = getattr(storage, "DiffManager", None)
    if not DiffManager:
        raise GlueError("DiffManager not available")

    try:
        if DiffManager.exists(tick_id):
            DiffManager.delete(tick_id)
            return True
        return False
    except Exception as e:
        raise GlueError(f"delete_recording failed: {e}")


def delete_all_recordings(file_path: str) -> int:
    """Delete all recordings for a file. Returns count deleted."""
    storage = _safe_import("codevovle.storage")
    if not storage:
        raise GlueError("storage module not available")

    DiffManager = getattr(storage, "DiffManager", None)
    if not DiffManager:
        raise GlueError("DiffManager not available")

    try:
        tick_ids = DiffManager.list_all()
        count = 0
        for tid in tick_ids:
            try:
                if DiffManager.exists(tid):
                    DiffManager.delete(tid)
                    count += 1
            except Exception:
                pass
        return count
    except Exception as e:
        raise GlueError(f"delete_all_recordings failed: {e}")


def get_cursor(file_path: str) -> Dict[str, Any]:
    """Get current cursor position (active branch and tick) for file_path."""
    storage = _safe_import("codevovle.storage")
    if not storage:
        return {"branch": "main", "tick": None}

    StateManager = getattr(storage, "StateManager", None)
    if not StateManager:
        return {"branch": "main", "tick": None}

    try:
        cursor = StateManager.get_cursor(file_path)
        if cursor:
            return cursor
        return {"branch": "main", "tick": None}
    except Exception:
        return {"branch": "main", "tick": None}


def set_cursor(file_path: str, branch: str, tick: Optional[int]) -> bool:
    """Set cursor position for file_path."""
    storage = _safe_import("codevovle.storage")
    if not storage:
        raise GlueError("storage module not available")

    StateManager = getattr(storage, "StateManager", None)
    if not StateManager:
        raise GlueError("StateManager not available")

    try:
        StateManager.set_cursor(file_path, branch, tick)
        return True
    except Exception as e:
        raise GlueError(f"set_cursor failed: {e}")


def jump_to_tick(file_path: str, tick_id: int) -> bool:
    """Jump to a specific tick (set cursor and file content)."""
    storage = _safe_import("codevovle.storage")
    if not storage:
        raise GlueError("storage module not available")

    try:
        from codevovle.engine import TickCursor

        tc = TickCursor(file_path)
        tc.set_position("main", tick_id)
        return True
    except Exception as e:
        raise GlueError(f"jump_to_tick failed: {e}")


def get_status(file_path: str) -> Dict[str, Any]:
    """Return comprehensive status info for a recording file."""
    storage = _safe_import("codevovle.storage")
    engine_mod = _safe_import("codevovle.engine")

    result: Dict[str, Any] = {"ready": False, "recordings_count": 0, "branches": []}

    try:
        if storage and hasattr(storage, "StateManager"):
            tick_counter = storage.StateManager.get_tick_counter()
            result["tick_counter"] = tick_counter
            result["ready"] = True
    except Exception:
        pass

    try:
        if storage and hasattr(storage, "DiffManager"):
            tick_ids = storage.DiffManager.list_all()
            result["recordings_count"] = len(tick_ids)
    except Exception:
        pass

    try:
        branches = get_branches(file_path)
        result["branches"] = branches
    except Exception:
        pass

    return result


def start_recording(
    file_path: str, interval: float = 1.0, num_threads: Optional[int] = None
) -> int:
    """Start background recording daemon for file_path.

    Returns the PID of the daemon process.
    """
    daemon = _safe_import("codevovle.daemon")
    if not daemon or not hasattr(daemon, "DaemonManager"):
        raise GlueError("daemon manager not available")

    try:
        return daemon.DaemonManager.start(
            file_path, interval, num_threads=num_threads or 1
        )
    except Exception as e:
        raise GlueError(f"start_recording failed: {e}")


def stop_recording(file_path: str) -> bool:
    """Stop background recording daemon for file_path."""
    daemon = _safe_import("codevovle.daemon")
    if not daemon or not hasattr(daemon, "DaemonManager"):
        raise GlueError("daemon manager not available")

    try:
        return daemon.DaemonManager.stop(file_path)
    except Exception as e:
        raise GlueError(f"stop_recording failed: {e}")


def list_daemon_processes() -> List[Dict[str, Any]]:
    """List all active daemon recording processes."""
    daemon = _safe_import("codevovle.daemon")
    if not daemon or not hasattr(daemon, "DaemonManager"):
        return []

    try:
        return daemon.DaemonManager.list_all()
    except Exception:
        return []


def get_branches(file_path: str) -> List[Dict[str, Any]]:
    """List all branches with metadata."""
    storage = _safe_import("codevovle.storage")
    if not storage or not hasattr(storage, "BranchManager"):
        return []

    try:
        BranchManager = storage.BranchManager
        branch_names = BranchManager.list_all()
        branches = []

        for name in branch_names:
            try:
                meta = BranchManager.read(name)
                branches.append(
                    {
                        "name": name,
                        "label": meta.get("label", name.split("/")[-1]),
                        "parent": meta.get("parent"),
                        "head_tick": meta.get("head_tick"),
                        "forked_at_tick": meta.get("forked_at_tick"),
                    }
                )
            except Exception:
                pass

        return branches
    except Exception:
        return []


def create_branch(
    name: str, parent: Optional[str] = None, forked_at_tick: Optional[int] = None
) -> bool:
    """Create a new branch."""
    storage = _safe_import("codevovle.storage")
    if not storage or not hasattr(storage, "BranchManager"):
        raise GlueError("BranchManager not available")

    try:
        storage.BranchManager.create(name, parent=parent, forked_at_tick=forked_at_tick)
        return True
    except Exception as e:
        raise GlueError(f"create_branch failed: {e}")


def rename_branch(old_name: str, new_short_name: str) -> bool:
    """Rename a branch (only the final component)."""
    storage = _safe_import("codevovle.storage")
    if not storage or not hasattr(storage, "BranchManager"):
        raise GlueError("BranchManager not available")

    try:
        storage.BranchManager.rename(old_name, new_short_name)
        return True
    except Exception as e:
        raise GlueError(f"rename_branch failed: {e}")


def delete_branch(name: str) -> bool:
    """Delete a branch and all its descendants."""
    storage = _safe_import("codevovle.storage")
    if not storage or not hasattr(storage, "BranchManager"):
        raise GlueError("BranchManager not available")

    try:
        storage.BranchManager.delete(name)
        return True
    except Exception as e:
        raise GlueError(f"delete_branch failed: {e}")


def get_insights(
    file_path: str,
    from_spec: str,
    to_spec: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate AI insights between two recording points."""
    insights = _safe_import("codevovle.insights")
    if not insights or not hasattr(insights, "InsightsEngine"):
        raise GlueError("Insights engine not available")

    try:
        ie = insights.InsightsEngine(file_path, model=model)
        return ie.generate_insights(from_spec, to_spec)
    except Exception as e:
        raise GlueError(f"get_insights failed: {e}")
