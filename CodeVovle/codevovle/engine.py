"""
Recording engine for CodeVovle.

Provides:
- Interval-based recording of file changes
- Automatic diff computation and persistence
- Tick ID assignment and management
- Cursor tracking across branches
- Performance profiling (optional)

The engine samples file state at regular intervals, computes diffs,
persists non-empty diffs, and assigns tick IDs.
"""

import os
import time
from pathlib import Path
from typing import Optional

from codevovle.storage import (
    ConfigManager,
    BranchManager,
    DiffManager,
    SnapshotManager,
    StateManager,
)
from codevovle.diffs import compute_unified_diff, is_empty_diff
from codevovle.profiler import Profiler
import storage_utility as su


class RecordingError(Exception):
    """Recording engine error."""
    pass


from concurrent.futures import ThreadPoolExecutor


class RecordingEngine:
    """
    Manages interval-based recording of file changes.
    
    Responsibilities:
    - Create and manage base snapshots
    - Sample file state at intervals
    - Compute unified diffs
    - Persist diffs and assign tick IDs
    - Manage branch and cursor state
    """
    
    def __init__(self, file_path: str, interval_seconds: float, profiler: Optional[Profiler] = None, num_threads: Optional[int] = None):
        """
        Initialize recording engine for a file.
        
        Args:
            file_path: Absolute path to file being recorded
            interval_seconds: Sampling interval in seconds
            profiler: Optional performance profiler
            
        Raises:
            RecordingError: If file path is invalid or setup fails
        """
        if interval_seconds <= 0:
            raise RecordingError("Interval must be positive")
        
        self.file_path = file_path
        self.interval_seconds = interval_seconds
        self.last_sample_time = None
        self.profiler = profiler or Profiler(enable=False)
        
        # Normalize path
        self.normalized_path = str(Path(file_path).resolve())
        # Thread pool for offloading diff computation/persistence
        from codevovle.storage import ThreadConfigManager

        if num_threads is None:
            num_threads = ThreadConfigManager.get_thread_count()

        # Cap threads to reasonable limits
        try:
            self.num_threads = int(num_threads)
        except Exception:
            self.num_threads = 10

        if self.num_threads < 1:
            self.num_threads = 1

        self._executor = ThreadPoolExecutor(max_workers=self.num_threads)
    
    def initialize_tracking(self) -> None:
        """
        Initialize tracking for this file.
        
        Creates:
        - .codevovle/ directory structure if missing
        - Base snapshot from current file content
        - Main branch
        - Initial config and state
        
        Raises:
            RecordingError: If initialization fails
        """
        ConfigManager.ensure_initialized()
        
        try:
            # Read current file content
            if not su.exists(self.normalized_path):
                raise RecordingError(f"File does not exist: {self.normalized_path}")
            
            current_content = su.read_text(self.normalized_path)
            
            # Create base snapshot if not exists
            if not SnapshotManager.exists():
                SnapshotManager.write(current_content)
            
            # Create main branch if not exists
            if not BranchManager.exists("main"):
                BranchManager.create(
                    "main",
                    parent=None,
                    forked_at_tick=None
                )
            
            # Initialize state for this file
            if StateManager.get_cursor(self.normalized_path) is None:
                StateManager.set_cursor(self.normalized_path, "main", None)
            
            # Set config for this file
            config = ConfigManager.get_file_config(self.normalized_path)
            if config is None:
                ConfigManager.set_file_config(
                    self.normalized_path,
                    {
                        "file_path": self.normalized_path,
                        "interval": self.interval_seconds,
                        "active_branch": "main",
                        "last_tick": None
                    }
                )
            else:
                # Update interval if provided
                config["interval"] = self.interval_seconds
                ConfigManager.set_file_config(self.normalized_path, config)
        
        except Exception as e:
            raise RecordingError(f"Failed to initialize tracking: {e}") from e
    
    def sample(self) -> Optional[int]:
        """
        Sample current file state and persist diff if it changed.
        
        If sufficient time has passed since last sample and file has changed,
        computes diff, persists it, assigns next tick ID, and updates state.
        
        Returns:
            Tick ID if a diff was persisted, None if no change or interval not elapsed
            
        Raises:
            RecordingError: If sampling fails
        """
        try:
            sample_start = self.profiler.start_sample()
            now = time.time()
            
            # Check if interval has elapsed
            if self.last_sample_time is not None:
                elapsed = now - self.last_sample_time
                if elapsed < self.interval_seconds:
                    return None
            
            # Update last sample time
            self.last_sample_time = now
            
            # Read current file content
            if not su.exists(self.normalized_path):
                raise RecordingError(f"File disappeared: {self.normalized_path}")
            
            current_content = su.read_text(self.normalized_path)
            
            # Capture base snapshot
            base_content = SnapshotManager.read()
            # Compute diff synchronously (cheap CPU), but persist asynchronously
            diff = compute_unified_diff(base_content, current_content)
            if is_empty_diff(diff):
                if sample_start:
                    self.profiler.record_sample(sample_start, self.normalized_path, False, False)
                return None

            # Reserve tick id immediately to keep ordering consistent
            tick_id = StateManager.increment_tick_counter()
            diff_computed = True

            # Offload writing diff to thread pool so disk I/O doesn't block sampling
            def _persist_diff(tid, content):
                try:
                    DiffManager.write(tid, content)
                except Exception:
                    # Best-effort: ignore write failures here (metadata will indicate missing diffs)
                    pass

            # Submit write and don't wait
            try:
                self._executor.submit(_persist_diff, tick_id, diff)
            except Exception:
                # If executor shutdown or unavailable, fallback to synchronous write
                DiffManager.write(tick_id, diff)
            
            # Update branch metadata only if a tick was produced
            if tick_id is not None:
                cursor = StateManager.get_cursor(self.normalized_path)
                if cursor:
                    active_branch = cursor["active_branch"]
                    branch = BranchManager.read(active_branch)

                    # Add tick to diff chain
                    if "diff_chain" not in branch:
                        branch["diff_chain"] = []
                    branch["diff_chain"].append(tick_id)
                    branch["head_tick"] = tick_id

                    BranchManager.update(active_branch, branch)

                    # Update cursor
                    StateManager.set_cursor(self.normalized_path, active_branch, tick_id)
            
            # Update base snapshot to current state
            SnapshotManager.write(current_content)
            
            if sample_start:
                self.profiler.record_sample(sample_start, self.normalized_path, diff_computed, True)
            
            return tick_id
        
        except Exception as e:
            raise RecordingError(f"Sampling failed: {e}") from e
    
    def get_status(self) -> dict:
        """
        Get current recording status for this file.
        
        Returns:
            Dictionary with status information:
            - active_branch: Current branch name
            - cursor_tick: Current tick position
            - branch_head_tick: Last tick on active branch
            - last_tick_id: Last assigned tick ID globally
            - interval: Recording interval in seconds
        """
        cursor = StateManager.get_cursor(self.normalized_path)
        config = ConfigManager.get_file_config(self.normalized_path)
        
        active_branch = cursor["active_branch"] if cursor else "main"
        cursor_tick = cursor["current_tick"] if cursor else None
        
        branch = BranchManager.read(active_branch)
        branch_head_tick = branch.get("head_tick") if branch else None
        branch_tick_count = len(branch.get("diff_chain", [])) if branch else 0
        
        last_tick_id = StateManager.get_tick_counter()
        interval = config["interval"] if config else self.interval_seconds
        
        return {
            "active_branch": active_branch,
            "cursor_tick": cursor_tick,
            "branch_head_tick": branch_head_tick,
            "last_tick_id": last_tick_id,
            "interval": interval,
            "branch_tick_count": branch_tick_count
        }


    def revert_to_tick(self, tick_id: int) -> str:
        """
        Reconstruct file to a specific tick and revert on disk.
        
        Validates that tick exists on current branch, reconstructs file state,
        overwrites file on disk, and updates cursor.
        
        Args:
            tick_id: Tick ID to revert to
            
        Returns:
            Reconstructed file content
            
        Raises:
            RecordingError: If tick not on current branch or revert fails
        """
        try:
            cursor = StateManager.get_cursor(self.normalized_path)
            if not cursor:
                raise RecordingError("No tracking initialized for file")
            
            current_branch = cursor["active_branch"]
            branch = BranchManager.read(current_branch)
            
            if not branch or tick_id not in branch.get("diff_chain", []):
                raise RecordingError(
                    f"Tick {tick_id} not on branch '{current_branch}'\n"
                    f"Use 'branch jump' to switch branches"
                )
            
            # Reconstruct content from base + diffs up to tick
            base_content = SnapshotManager.read()
            
            # Get all diffs up to this tick
            diff_chain = branch["diff_chain"]
            tick_index = diff_chain.index(tick_id)
            diffs_to_apply = diff_chain[:tick_index + 1]
            
            # Apply diffs
            from codevovle.diffs import apply_patch_chain
            reconstructed = apply_patch_chain(
                base_content,
                [DiffManager.read(t) for t in diffs_to_apply]
            )
            
            # Overwrite file on disk
            su.write_text(self.normalized_path, reconstructed)
            
            # Update cursor
            StateManager.set_cursor(self.normalized_path, current_branch, tick_id)
            
            return reconstructed
        
        except Exception as e:
            if "not on branch" in str(e):
                raise
            raise RecordingError(f"Failed to revert to tick {tick_id}: {e}") from e
    
    def list_branches(self) -> list:
        """
        List all branches with metadata.
        
        Returns:
            List of branch names
        """
        return BranchManager.list_all()
    
    def rename_branch(self, old_name: str, new_short_name: str) -> None:
        """
        Rename a branch (change the final component of the path).
        
        Args:
            old_name: Current branch full path (e.g., "main/feature")
            new_short_name: New short name (e.g., "feature2")
            
        Raises:
            RecordingError: If branch operation fails
        """
        try:
            BranchManager.rename(old_name, new_short_name)
            
            # Update cursor if current branch was renamed
            cursor = StateManager.get_cursor(self.normalized_path)
            if cursor and cursor["active_branch"] == old_name:
                # Reconstruct new name from path
                if "/" in old_name:
                    parent_path = "/".join(old_name.split("/")[:-1])
                    new_name = f"{parent_path}/{new_short_name}"
                else:
                    new_name = new_short_name
                
                StateManager.set_cursor(
                    self.normalized_path,
                    new_name,
                    cursor["current_tick"]
                )
        except Exception as e:
            raise RecordingError(f"Failed to rename branch: {e}") from e
    
    def jump_to_branch(self, branch_name: str) -> None:
        """
        Switch to a different branch and reconstruct file to branch head.
        
        Validates branch exists, reconstructs file state to branch head,
        and updates cursor. No diffs are written during jump.
        
        Args:
            branch_name: Branch to switch to
            
        Raises:
            RecordingError: If branch doesn't exist or jump fails
        """
        try:
            if not BranchManager.exists(branch_name):
                raise RecordingError(f"Branch does not exist: {branch_name}")
            
            branch = BranchManager.read(branch_name)
            head_tick = branch.get("head_tick")
            
            if head_tick is None:
                # Branch has no ticks yet, just switch cursor
                StateManager.set_cursor(self.normalized_path, branch_name, None)
            else:
                # Reconstruct file to branch head
                base_content = SnapshotManager.read()
                diff_chain = branch.get("diff_chain", [])
                
                from codevovle.diffs import apply_patch_chain
                reconstructed = apply_patch_chain(
                    base_content,
                    [DiffManager.read(t) for t in diff_chain if DiffManager.exists(t)]
                )
                
                # Overwrite file
                su.write_text(self.normalized_path, reconstructed)
                
                # Update cursor
                StateManager.set_cursor(self.normalized_path, branch_name, head_tick)
        
        except RecordingError:
            raise
        except Exception as e:
            raise RecordingError(f"Failed to jump to branch: {e}") from e

    def shutdown(self) -> None:
        """Cleanly shutdown background resources (thread pool)."""
        try:
            if hasattr(self, "_executor") and self._executor is not None:
                self._executor.shutdown(wait=True)
        except Exception:
            pass


class TickCursor:
    """
    Manages cursor position within the tick timeline.
    
    Tracks:
    - Active branch
    - Current tick position
    - Branch head position
    """
    
    def __init__(self, file_path: str):
        """
        Initialize cursor for a file.
        
        Args:
            file_path: File path to track
        """
        self.file_path = str(Path(file_path).resolve())
    
    def set_position(self, branch: str, tick: Optional[int]) -> None:
        """
        Set cursor to a specific branch and tick.
        
        Args:
            branch: Branch name
            tick: Tick ID or None
        """
        StateManager.set_cursor(self.file_path, branch, tick)
    
    def get_position(self) -> tuple[Optional[str], Optional[int]]:
        """
        Get current cursor position.
        
        Returns:
            Tuple of (branch, tick)
        """
        cursor = StateManager.get_cursor(self.file_path)
        if cursor:
            return cursor["active_branch"], cursor["current_tick"]
        return None, None
    
    def get_branch_head(self, branch: str) -> Optional[int]:
        """
        Get the head tick of a branch.
        
        Args:
            branch: Branch name
            
        Returns:
            Tick ID of branch head or None
        """
        branch_data = BranchManager.read(branch)
        return branch_data.get("head_tick") if branch_data else None
    
    def is_at_head(self) -> bool:
        """
        Check if cursor is at the head of current branch.
        
        Returns:
            True if cursor is at branch head
        """
        current_branch, current_tick = self.get_position()
        if current_branch is None or current_tick is None:
            return False
        
        head_tick = self.get_branch_head(current_branch)
        return current_tick == head_tick
