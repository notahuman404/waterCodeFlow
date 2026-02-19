"""
Public API facade — calls the real codevovle and watcher storage layers.

PYTHONPATH (set by GlueBridge._spawn) is:
  [extPath/CodeVovle, extPath]

This means:
  - `codevovle.*`    imports from extPath/CodeVovle/codevovle/
  - `storage_utility` resolves to extPath/CodeVovle/storage_utility.py (the pure-Python one)
  - `watcher.*`      imports from extPath/watcher/

codevovle stores its data in .codevovle/ relative to CWD.
CWD is extPath (set in GlueBridge._spawn).
The validate_cwd() check in codevovle/__main__.py only applies when using the CLI entry point,
NOT when importing codevovle.storage directly — so direct imports are fine.

For recordings (built/recordings/*.json) written by GlueBridge.spawnRun:
we read them directly from the filesystem.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .errors import GlueError


# ── helpers ────────────────────────────────────────────────────────────────────

def _recordings_dir() -> Path:
    """built/recordings/ relative to CWD (= extPath)."""
    return Path(os.getcwd()) / "built" / "recordings"


def _codevovle_storage():
    """
    Import codevovle.storage.  Returns the module or raises GlueError.
    This works because PYTHONPATH puts CodeVovle/ first, giving us the right
    storage_utility.py.
    """
    try:
        from codevovle import storage
        return storage
    except ImportError as e:
        raise GlueError(f"codevovle.storage not available: {e}")


def _read_recording_files(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read spawnRun recording JSONs, optionally filtered to file_path."""
    rdir = _recordings_dir()
    if not rdir.exists():
        return []
    recordings = []
    for p in sorted(rdir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            if file_path:
                if rec.get("filePath") != file_path and rec.get("file_path") != file_path:
                    continue
            recordings.append(rec)
        except Exception:
            pass
    return recordings


# ── recordings (spawnRun output) ──────────────────────────────────────────────


def list_recordings(file_path: str) -> List[Dict[str, Any]]:
    """Return all spawnRun recordings for file_path, newest-first."""
    return _read_recording_files(file_path)


def save_recording(
    run_id: str,
    recording_path: str,
    file_path: str,
    timestamp: str,
    duration_ms: int,
    exit_code: int,
    variables: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """Merge extra metadata into a recording JSON (called by adapter saveRecording)."""
    rdir = _recordings_dir()
    rdir.mkdir(parents=True, exist_ok=True)
    target = rdir / f"{run_id}.json"
    existing: Dict[str, Any] = {}
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            pass
    existing.update({
        "runId": run_id,
        "filePath": file_path,
        "recordingPath": recording_path,
        "timestamp": timestamp,
        "durationMs": duration_ms,
        "exitCode": exit_code,
    })
    if variables is not None:
        existing["variables"] = variables
    target.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return True


def get_recording(run_id: str) -> Dict[str, Any]:
    """Return a recording by runId."""
    rdir = _recordings_dir()
    candidate = rdir / f"{run_id}.json"
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    for rec in _read_recording_files():
        if rec.get("runId") == run_id:
            return rec
    raise GlueError(f"Recording {run_id!r} not found")


def delete_recording(run_id: str) -> bool:
    """Delete a spawnRun recording JSON.  Returns True if deleted."""
    rdir = _recordings_dir()
    candidate = rdir / f"{run_id}.json"
    if candidate.exists():
        candidate.unlink()
        return True
    for p in rdir.glob("*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            if rec.get("runId") == run_id:
                p.unlink()
                return True
        except Exception:
            pass
    return False


def delete_all_recordings(file_path: str) -> int:
    """Delete all recordings for file_path. Returns count deleted."""
    deleted = 0
    for rec in _read_recording_files(file_path):
        if delete_recording(rec.get("runId", "")):
            deleted += 1
    return deleted


# ── codevovle status / cursor ─────────────────────────────────────────────────


def get_status(file_path: str) -> Dict[str, Any]:
    """
    Return tracking status for file_path using real codevovle state.
    Falls back gracefully if .codevovle/ does not exist yet.
    """
    result: Dict[str, Any] = {
        "ready": False,
        "recordings_count": len(_read_recording_files(file_path)),
        "branches": [],
        "tick_counter": 0,
    }
    try:
        storage = _codevovle_storage()
        state = storage.StateManager.read_all()
        result["tick_counter"] = state.get("global_tick_counter", 0)
        result["ready"] = True
        result["branches"] = get_branches(file_path)
    except Exception:
        pass
    return result


def get_cursor(file_path: str) -> Dict[str, Any]:
    """Get codevovle cursor (active branch + current tick) for file_path."""
    try:
        storage = _codevovle_storage()
        cursor = storage.StateManager.get_cursor(file_path)
        if cursor:
            return {
                "branch": cursor.get("active_branch", "main"),
                "tick": cursor.get("current_tick"),
            }
    except Exception:
        pass
    return {"branch": "main", "tick": None}


def set_cursor(file_path: str, branch: str, tick: Optional[int]) -> bool:
    """Set codevovle cursor for file_path."""
    try:
        storage = _codevovle_storage()
        storage.StateManager.set_cursor(file_path, branch, tick)
        return True
    except Exception as e:
        raise GlueError(f"set_cursor failed: {e}")


def jump_to_tick(file_path: str, tick_id: int) -> bool:
    """Revert file to a specific codevovle tick using the engine."""
    try:
        from codevovle.engine import RecordingEngine
        from codevovle.storage import ThreadConfigManager
        num_threads = ThreadConfigManager.get_thread_count()
        engine = RecordingEngine(file_path, 1.0, num_threads=num_threads)
        engine.revert_to_tick(tick_id)
        return True
    except Exception as e:
        raise GlueError(f"jump_to_tick failed: {e}")


# ── codevovle branches ────────────────────────────────────────────────────────


def get_branches(file_path: str) -> List[Dict[str, Any]]:
    """List all codevovle branches from .codevovle/branches/."""
    try:
        storage = _codevovle_storage()
        branch_names = storage.BranchManager.list_all()
        branches = []
        for name in branch_names:
            try:
                meta = storage.BranchManager.read(name)
                branches.append({
                    "name": name,
                    "label": meta.get("label", name.split("/")[-1]),
                    "parent": meta.get("parent"),
                    "head_tick": meta.get("head_tick"),
                    "forked_at_tick": meta.get("forked_at_tick"),
                })
            except Exception:
                pass
        return branches
    except Exception:
        return [{"name": "main", "label": "main", "parent": None, "head_tick": None, "forked_at_tick": None}]


def create_branch(name: str, parent: Optional[str] = None, forked_at_tick: Optional[int] = None) -> bool:
    """Create a codevovle branch."""
    try:
        storage = _codevovle_storage()
        storage.BranchManager.create(name, parent=parent, forked_at_tick=forked_at_tick)
        return True
    except Exception as e:
        raise GlueError(f"create_branch failed: {e}")


def rename_branch(old_name: str, new_short_name: str) -> bool:
    """Rename a codevovle branch."""
    try:
        from codevovle.engine import RecordingEngine
        from codevovle.storage import ThreadConfigManager
        num_threads = ThreadConfigManager.get_thread_count()
        # RecordingEngine.rename_branch takes (old_path, new_short_name)
        engine = RecordingEngine(".", 1.0, num_threads=num_threads)
        engine.rename_branch(old_name, new_short_name)
        return True
    except Exception as e:
        raise GlueError(f"rename_branch failed: {e}")


def delete_branch(name: str) -> bool:
    """Delete a codevovle branch and its children."""
    try:
        storage = _codevovle_storage()
        storage.BranchManager.delete(name)
        return True
    except Exception as e:
        raise GlueError(f"delete_branch failed: {e}")


# ── codevovle daemon recording ────────────────────────────────────────────────


def start_recording(file_path: str, interval: float = 1.0, num_threads: Optional[int] = None) -> int:
    """
    Start a codevovle background recording daemon for file_path.
    Returns the daemon PID.
    """
    try:
        from codevovle.daemon import DaemonManager
        pid = DaemonManager.start(file_path, interval, num_threads=num_threads)
        return pid
    except Exception as e:
        raise GlueError(f"start_recording failed: {e}")


def stop_recording(file_path: str) -> bool:
    """Stop the codevovle daemon recording file_path."""
    try:
        from codevovle.daemon import DaemonManager
        return DaemonManager.stop(file_path)
    except Exception as e:
        raise GlueError(f"stop_recording failed: {e}")


def list_daemon_processes() -> List[Dict[str, Any]]:
    """List all active codevovle daemon processes."""
    try:
        from codevovle.daemon import DaemonManager
        return DaemonManager.list_all()
    except Exception:
        return []


# ── codevovle insights ────────────────────────────────────────────────────────


def get_insights(
    file_path: str,
    from_spec: str,
    to_spec: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate AI insights via codevovle InsightsEngine.
    Requires API keys in CodeVovle/.env.
    """
    try:
        from codevovle.insights import InsightsEngine
        engine = InsightsEngine(file_path, model=model or "gemini")
        return engine.generate_insights(from_spec, to_spec)
    except Exception as e:
        raise GlueError(f"get_insights failed: {e}")
