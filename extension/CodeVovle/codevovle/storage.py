"""
Storage layer for CodeVovle metadata and snapshots.

Manages:
- Configuration (per-file tracking settings)
- Branches (branch metadata and history)
- Diffs (individual change diffs)
- Snapshots (base file state)
- State (global cursor and tick tracking)

All operations use storage_utility for atomic file I/O.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any

import storage_utility as su


# Directory structure constants
CODEVOVLE_DIR = ".codevovle"
BRANCHES_DIR = f"{CODEVOVLE_DIR}/branches"
DIFFS_DIR = f"{CODEVOVLE_DIR}/diffs"
SNAPSHOTS_DIR = f"{CODEVOVLE_DIR}/snapshots"
CONFIG_FILE = f"{CODEVOVLE_DIR}/config.json"
STATE_FILE = f"{CODEVOVLE_DIR}/state.json"


class StorageError(Exception):
    """Storage operation error."""
    pass


class ConfigManager:
    """
    Manages per-file configuration in .codevovle/config.json.
    
    Config structure:
    {
        "<file_path>": {
            "file_path": str,
            "interval": float,
            "active_branch": str,
            "last_tick": int or null
        }
    }
    """
    
    @staticmethod
    def ensure_initialized() -> None:
        """Ensure .codevovle/ directory and config.json exist."""
        su.ensure_dir(CODEVOVLE_DIR)
        su.ensure_dir(BRANCHES_DIR)
        su.ensure_dir(DIFFS_DIR)
        su.ensure_dir(SNAPSHOTS_DIR)
        
        if not su.exists(CONFIG_FILE):
            su.write_json(CONFIG_FILE, {})
    
    @staticmethod
    def read_all() -> Dict[str, Dict[str, Any]]:
        """Read entire config."""
        ConfigManager.ensure_initialized()
        return su.read_json_safe(CONFIG_FILE, {})
    
    @staticmethod
    def get_file_config(file_path: str) -> Optional[Dict[str, Any]]:
        """Get config for a specific file."""
        config = ConfigManager.read_all()
        return config.get(file_path)
    
    @staticmethod
    def set_file_config(file_path: str, config_data: Dict[str, Any]) -> None:
        """Set config for a specific file."""
        ConfigManager.ensure_initialized()
        config = ConfigManager.read_all()
        config[file_path] = config_data
        su.write_json(CONFIG_FILE, config)
    
    @staticmethod
    def delete_file_config(file_path: str) -> None:
        """Delete config for a specific file."""
        config = ConfigManager.read_all()
        if file_path in config:
            del config[file_path]
            su.write_json(CONFIG_FILE, config)


class BranchManager:
    """
    Manages hierarchical branch metadata in .codevovle/branches/<path>/meta.json.
    
    Supports recursive branching with hierarchical naming:
    - "main" (root branch)
    - "main/feature1" (branch of main)
    - "main/feature1/sub-branch" (branch of feature1)
    
    Branch structure:
    {
        "id": str (unique identifier/full path),
        "label": str (short name, last component of path),
        "parent": str or null (parent branch full path),
        "forked_at_tick": int or null,
        "diff_chain": [tick_id, tick_id, ...],
        "head_tick": int or null
    }
    """
    
    @staticmethod
    def _get_branch_dir(branch_name: str) -> str:
        """Get the directory path for a branch (hierarchical)."""
        return f"{BRANCHES_DIR}/{branch_name}"
    
    @staticmethod
    def _get_branch_meta_path(branch_name: str) -> str:
        """Get the metadata file path for a branch."""
        return f"{BranchManager._get_branch_dir(branch_name)}/meta.json"
    
    @staticmethod
    def _validate_branch_name(branch_name: str) -> None:
        """Validate branch name format."""
        if not branch_name or "/" in branch_name.strip("/"):
            return  # "/" separators are valid for hierarchy
        if branch_name.startswith("/") or branch_name.endswith("/"):
            raise StorageError(f"Invalid branch name: {branch_name}")
    
    @staticmethod
    def exists(branch_name: str) -> bool:
        """Check if a branch exists."""
        return su.exists(BranchManager._get_branch_meta_path(branch_name))
    
    @staticmethod
    def create(
        branch_name: str,
        parent: Optional[str] = None,
        forked_at_tick: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new branch at any level of hierarchy.
        
        Args:
            branch_name: Full hierarchical path (e.g., "main/feature/sub")
            parent: Parent branch path (auto-detected from branch_name if not provided)
            forked_at_tick: Tick where branch forked from parent
        """
        ConfigManager.ensure_initialized()
        
        if BranchManager.exists(branch_name):
            raise StorageError(f"Branch already exists: {branch_name}")
        
        # Auto-detect parent if not provided
        if parent is None and "/" in branch_name:
            parent = "/".join(branch_name.split("/")[:-1])
        
        # Validate parent exists (except for root)
        if parent and not BranchManager.exists(parent):
            raise StorageError(f"Parent branch does not exist: {parent}")
        
        branch_data = {
            "id": branch_name,
            "label": branch_name.split("/")[-1],  # Last component
            "parent": parent,
            "forked_at_tick": forked_at_tick,
            "diff_chain": [],
            "head_tick": None
        }
        
        # Create directory and metadata
        su.ensure_dir(BranchManager._get_branch_dir(branch_name))
        su.write_json(BranchManager._get_branch_meta_path(branch_name), branch_data)
        return branch_data
    
    @staticmethod
    def read(branch_name: str) -> Dict[str, Any]:
        """Read branch metadata."""
        path = BranchManager._get_branch_meta_path(branch_name)
        return su.read_json_safe(path, {})
    
    @staticmethod
    def update(branch_name: str, data: Dict[str, Any]) -> None:
        """Update branch metadata."""
        su.write_json(BranchManager._get_branch_meta_path(branch_name), data)
    
    @staticmethod
    def delete(branch_name: str) -> bool:
        """
        Delete a branch and all its children recursively.
        Cannot delete 'main' branch.
        
        Returns:
            True if deleted, False if it's the main branch
        """
        if branch_name == "main":
            raise StorageError("Cannot delete main branch")
        
        # Get all child branches
        children = BranchManager.get_children(branch_name)
        
        # Recursively delete children first
        for child in children:
            BranchManager.delete(child)
        
        # Delete this branch
        path = BranchManager._get_branch_meta_path(branch_name)
        if su.exists(path):
            os.unlink(path)
        
        # Remove empty directory
        branch_dir = BranchManager._get_branch_dir(branch_name)
        try:
            os.rmdir(branch_dir)
        except OSError:
            pass  # Directory not empty, that's ok
        
        return True
    
    @staticmethod
    def get_children(branch_name: str) -> List[str]:
        """
        Get all direct children of a branch.
        
        Args:
            branch_name: Parent branch path
            
        Returns:
            List of child branch full paths
        """
        ConfigManager.ensure_initialized()
        all_branches = BranchManager.list_all()
        prefix = branch_name + "/"
        
        children = []
        for branch in all_branches:
            if branch.startswith(prefix):
                # Check if this is a direct child (no more "/" after prefix)
                remainder = branch[len(prefix):]
                if "/" not in remainder:
                    children.append(branch)
        
        return children
    
    @staticmethod
    def get_descendants(branch_name: str) -> List[str]:
        """
        Get all descendants of a branch (children, grandchildren, etc).
        
        Args:
            branch_name: Parent branch path
            
        Returns:
            List of all descendant branch full paths
        """
        ConfigManager.ensure_initialized()
        all_branches = BranchManager.list_all()
        prefix = branch_name + "/"
        
        descendants = []
        for branch in all_branches:
            if branch.startswith(prefix):
                descendants.append(branch)
        
        return descendants
    
    @staticmethod
    def list_all() -> List[str]:
        """
        List all branch paths in hierarchical order.
        
        Returns:
            Sorted list of all branch full paths
        """
        ConfigManager.ensure_initialized()
        
        branch_dir = Path(BRANCHES_DIR)
        if not branch_dir.exists():
            return []
        
        def find_branches(base_path: Path, prefix: str = "") -> List[str]:
            """Recursively find all branches."""
            branches = []
            try:
                for item in base_path.iterdir():
                    if item.is_dir():
                        meta_file = item / "meta.json"
                        if meta_file.exists():
                            # This is a branch
                            branch_path = prefix + item.name if prefix else item.name
                            branches.append(branch_path)
                            # Recursively find children
                            branches.extend(find_branches(item, branch_path + "/"))
            except OSError:
                pass
            return branches
        
        return sorted(find_branches(branch_dir))
    
    @staticmethod
    def list_children(parent_branch: Optional[str] = None) -> List[str]:
        """
        List direct children of a branch.
        If parent_branch is None, returns root branches (direct children of "main").
        
        Args:
            parent_branch: Parent branch path, or None for roots
            
        Returns:
            List of child branch full paths
        """
        all_branches = BranchManager.list_all()
        
        if parent_branch is None:
            # Return only root branches
            return [b for b in all_branches if "/" not in b]
        
        return BranchManager.get_children(parent_branch)
    
    @staticmethod
    def rename(old_name: str, new_short_name: str) -> None:
        """
        Rename a branch (affects only the final component of the path).
        
        Example: rename "main/feature1" to "main/feature" (new_short_name="feature")
        
        Args:
            old_name: Full path of branch to rename
            new_short_name: New short name (final component)
        """
        if not BranchManager.exists(old_name):
            raise StorageError(f"Branch does not exist: {old_name}")
        
        # Build new full path
        if "/" in old_name:
            parent_path = "/".join(old_name.split("/")[:-1])
            new_name = f"{parent_path}/{new_short_name}"
        else:
            new_name = new_short_name
        
        if BranchManager.exists(new_name):
            raise StorageError(f"Branch already exists: {new_name}")
        
        # Read data
        data = BranchManager.read(old_name)
        data["id"] = new_name
        data["label"] = new_short_name
        
        # Create new directory
        su.ensure_dir(BranchManager._get_branch_dir(new_name))
        su.write_json(BranchManager._get_branch_meta_path(new_name), data)
        
        # Delete old
        old_path = BranchManager._get_branch_meta_path(old_name)
        if su.exists(old_path):
            os.unlink(old_path)
        
        # Update children's parent reference
        children = BranchManager.get_children(old_name)
        for child in children:
            child_data = BranchManager.read(child)
            child_data["parent"] = new_name
            BranchManager.update(child, child_data)
            
            # Move child directory
            new_child_path = child.replace(old_name, new_name)
            old_child_dir = BranchManager._get_branch_dir(child)
            new_child_dir = BranchManager._get_branch_dir(new_child_path)
            su.ensure_dir(new_child_dir.rsplit("/", 1)[0])
            try:
                os.rename(old_child_dir, new_child_dir)
            except OSError:
                pass
    
    @staticmethod
    def get_parent(branch_name: str) -> Optional[str]:
        """Get the parent branch of a given branch."""
        data = BranchManager.read(branch_name)
        return data.get("parent")


class DiffManager:
    """
    Manages individual diffs in .codevovle/diffs/<tick_id>.diff.
    
    Stores unified diff format as plain text.
    """
    
    @staticmethod
    def _get_diff_path(tick_id: int) -> str:
        """Get the file path for a diff."""
        return f"{DIFFS_DIR}/{tick_id}.diff"
    
    @staticmethod
    def exists(tick_id: int) -> bool:
        """Check if a diff exists."""
        return su.exists(DiffManager._get_diff_path(tick_id))
    
    @staticmethod
    def write(tick_id: int, diff_content: str) -> None:
        """Write a diff file."""
        ConfigManager.ensure_initialized()
        su.write_text(DiffManager._get_diff_path(tick_id), diff_content)
    
    @staticmethod
    def read(tick_id: int) -> str:
        """Read a diff file."""
        try:
            return su.read_text(DiffManager._get_diff_path(tick_id))
        except FileNotFoundError:
            raise StorageError(f"Diff not found: {tick_id}")
    
    @staticmethod
    def delete(tick_id: int) -> None:
        """Delete a diff file."""
        path = DiffManager._get_diff_path(tick_id)
        if su.exists(path):
            os.unlink(path)
    
    @staticmethod
    def list_all() -> List[int]:
        """List all tick IDs (from diff files)."""
        ConfigManager.ensure_initialized()
        
        diff_dir = Path(DIFFS_DIR)
        if not diff_dir.exists():
            return []
        
        tick_ids = []
        for file_path in diff_dir.glob("*.diff"):
            try:
                tick_id = int(file_path.stem)
                tick_ids.append(tick_id)
            except ValueError:
                # Skip non-numeric filenames
                pass
        
        return sorted(tick_ids)


class SnapshotManager:
    """
    Manages file snapshots in .codevovle/snapshots/base.txt.
    
    Stores the initial ("base") state of a file.
    """
    
    @staticmethod
    def _get_snapshot_path() -> str:
        """Get the base snapshot file path."""
        return f"{SNAPSHOTS_DIR}/base.txt"
    
    @staticmethod
    def exists() -> bool:
        """Check if base snapshot exists."""
        return su.exists(SnapshotManager._get_snapshot_path())
    
    @staticmethod
    def write(content: str) -> None:
        """Write the base snapshot."""
        ConfigManager.ensure_initialized()
        su.write_text(SnapshotManager._get_snapshot_path(), content)
    
    @staticmethod
    def read() -> str:
        """Read the base snapshot."""
        try:
            return su.read_text(SnapshotManager._get_snapshot_path())
        except FileNotFoundError:
            raise StorageError("Base snapshot not found")
    
    @staticmethod
    def delete() -> None:
        """Delete the base snapshot."""
        path = SnapshotManager._get_snapshot_path()
        if su.exists(path):
            os.unlink(path)


class StateManager:
    """
    Manages global state in .codevovle/state.json.
    
    State structure:
    {
        "global_tick_counter": int,
        "cursor": {
            "<file_path>": {
                "active_branch": str,
                "current_tick": int or null
            }
        }
    }
    """
    
    @staticmethod
    def ensure_initialized() -> None:
        """Ensure state.json exists with default values."""
        ConfigManager.ensure_initialized()
        
        if not su.exists(STATE_FILE):
            initial_state = {
                "global_tick_counter": 0,
                "cursor": {}
            }
            su.write_json(STATE_FILE, initial_state)
    
    @staticmethod
    def read_all() -> Dict[str, Any]:
        """Read entire state."""
        StateManager.ensure_initialized()
        return su.read_json_safe(STATE_FILE, {"global_tick_counter": 0, "cursor": {}})
    
    @staticmethod
    def get_tick_counter() -> int:
        """Get current global tick counter."""
        state = StateManager.read_all()
        return state.get("global_tick_counter", 0)
    
    @staticmethod
    def increment_tick_counter() -> int:
        """Increment and return the next tick ID."""
        state = StateManager.read_all()
        next_tick = state.get("global_tick_counter", 0) + 1
        state["global_tick_counter"] = next_tick
        su.write_json(STATE_FILE, state)
        return next_tick
    
    @staticmethod
    def set_cursor(file_path: str, branch: str, tick: Optional[int]) -> None:
        """Set cursor position for a file."""
        state = StateManager.read_all()
        if "cursor" not in state:
            state["cursor"] = {}
        
        state["cursor"][file_path] = {
            "active_branch": branch,
            "current_tick": tick
        }
        su.write_json(STATE_FILE, state)
    
    @staticmethod
    def get_cursor(file_path: str) -> Optional[Dict[str, Any]]:
        """Get cursor position for a file."""
        state = StateManager.read_all()
        return state.get("cursor", {}).get(file_path)
    
    @staticmethod
    def delete_cursor(file_path: str) -> None:
        """Delete cursor for a file."""
        state = StateManager.read_all()
        if file_path in state.get("cursor", {}):
            del state["cursor"][file_path]
            su.write_json(STATE_FILE, state)

class ThreadConfigManager:
    """
    Manages daemon thread configuration in .codevovle/state.json.
    
    Thread config structure in state.json:
    {
        "thread_config": {
            "daemon_threads": int (default: 10)
        }
    }
    """
    
    DEFAULT_THREADS = 10
    
    @staticmethod
    def get_thread_count() -> int:
        """Get configured number of daemon threads."""
        state = StateManager.read_all()
        return state.get("thread_config", {}).get("daemon_threads", ThreadConfigManager.DEFAULT_THREADS)
    
    @staticmethod
    def set_thread_count(num_threads: int) -> None:
        """
        Set number of daemon threads.
        
        Args:
            num_threads: Number of threads (must be 1-32)
            
        Raises:
            ValueError: If thread count is invalid
        """
        if not isinstance(num_threads, int) or num_threads < 1 or num_threads > 32:
            raise ValueError(f"Thread count must be between 1 and 32, got {num_threads}")
        
        StateManager.ensure_initialized()
        state = StateManager.read_all()
        
        if "thread_config" not in state:
            state["thread_config"] = {}
        
        state["thread_config"]["daemon_threads"] = num_threads
        su.write_json(STATE_FILE, state)