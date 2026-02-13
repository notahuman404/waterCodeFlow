"""
Tests for storage layer (ConfigManager, BranchManager, DiffManager, etc.).

Tests cover:
- Atomic writes and reads
- JSON metadata operations
- Directory structure creation
- CRUD operations for branches, diffs, snapshots
- State and cursor tracking
"""

from pathlib import Path

import pytest

from codevovle.storage import (
    ConfigManager,
    BranchManager,
    DiffManager,
    SnapshotManager,
    StateManager,
    StorageError,
    CODEVOVLE_DIR,
    BRANCHES_DIR,
    DIFFS_DIR,
    SNAPSHOTS_DIR,
    CONFIG_FILE,
    STATE_FILE,
)


class TestConfigManager:
    """Tests for ConfigManager."""
    
    def test_ensure_initialized(self, codevovle_root: Path):
        """Test that initialization creates required directories."""
        ConfigManager.ensure_initialized()
        
        assert (codevovle_root / CODEVOVLE_DIR).exists()
        assert (codevovle_root / BRANCHES_DIR).exists()
        assert (codevovle_root / DIFFS_DIR).exists()
        assert (codevovle_root / SNAPSHOTS_DIR).exists()
        assert (codevovle_root / CONFIG_FILE).exists()
    
    def test_read_empty_config(self, codevovle_root: Path):
        """Test reading empty config."""
        ConfigManager.ensure_initialized()
        
        config = ConfigManager.read_all()
        
        assert config == {}
    
    def test_set_get_file_config(self, codevovle_root: Path):
        """Test setting and getting file configuration."""
        ConfigManager.ensure_initialized()
        
        file_config = {
            "file_path": "main.py",
            "interval": 5.0,
            "active_branch": "main",
            "last_tick": None
        }
        
        ConfigManager.set_file_config("main.py", file_config)
        
        retrieved = ConfigManager.get_file_config("main.py")
        
        assert retrieved == file_config
    
    def test_set_multiple_files(self, codevovle_root: Path):
        """Test setting config for multiple files."""
        ConfigManager.ensure_initialized()
        
        config1 = {"file_path": "file1.py", "interval": 5.0}
        config2 = {"file_path": "file2.py", "interval": 10.0}
        
        ConfigManager.set_file_config("file1.py", config1)
        ConfigManager.set_file_config("file2.py", config2)
        
        all_config = ConfigManager.read_all()
        
        assert "file1.py" in all_config
        assert "file2.py" in all_config
        assert all_config["file1.py"] == config1
        assert all_config["file2.py"] == config2
    
    def test_delete_file_config(self, codevovle_root: Path):
        """Test deleting file configuration."""
        ConfigManager.ensure_initialized()
        
        ConfigManager.set_file_config("main.py", {"interval": 5.0})
        ConfigManager.delete_file_config("main.py")
        
        config = ConfigManager.read_all()
        
        assert "main.py" not in config
    
    def test_delete_nonexistent_config(self, codevovle_root: Path):
        """Test deleting nonexistent config (should not raise)."""
        ConfigManager.ensure_initialized()
        
        # Should not raise
        ConfigManager.delete_file_config("nonexistent.py")


class TestBranchManager:
    """Tests for BranchManager."""
    
    def test_create_branch(self, codevovle_root: Path):
        """Test creating a new branch."""
        ConfigManager.ensure_initialized()
        
        branch = BranchManager.create("main", parent=None, forked_at_tick=None)
        
        assert branch["label"] == "main"
        assert branch["parent"] is None
        assert branch["diff_chain"] == []
        assert branch["head_tick"] is None
        assert BranchManager.exists("main")
    
    def test_create_duplicate_branch_raises(self, codevovle_root: Path):
        """Test that creating duplicate branch raises error."""
        ConfigManager.ensure_initialized()
        
        BranchManager.create("main")
        
        with pytest.raises(StorageError):
            BranchManager.create("main")
    
    def test_read_branch(self, codevovle_root: Path):
        """Test reading branch metadata."""
        ConfigManager.ensure_initialized()
        
        # Create parent branch first (hierarchical validation)
        BranchManager.create("main", parent=None, forked_at_tick=None)
        BranchManager.create("main/develop", parent="main", forked_at_tick=5)
        
        branch = BranchManager.read("main/develop")
        
        assert branch["label"] == "develop"
        assert branch["parent"] == "main"
        assert branch["forked_at_tick"] == 5
    
    def test_read_nonexistent_branch(self, codevovle_root: Path):
        """Test reading nonexistent branch returns empty dict."""
        ConfigManager.ensure_initialized()
        
        branch = BranchManager.read("nonexistent")
        
        assert branch == {}
    
    def test_update_branch(self, codevovle_root: Path):
        """Test updating branch metadata."""
        ConfigManager.ensure_initialized()
        
        BranchManager.create("main")
        
        updated_data = {
            "id": "main",
            "label": "main",
            "parent": None,
            "forked_at_tick": None,
            "diff_chain": [1, 2, 3],
            "head_tick": 3
        }
        
        BranchManager.update("main", updated_data)
        
        branch = BranchManager.read("main")
        
        assert branch["diff_chain"] == [1, 2, 3]
        assert branch["head_tick"] == 3
    
    def test_delete_branch(self, codevovle_root: Path):
        """Test deleting a branch."""
        ConfigManager.ensure_initialized()
        
        BranchManager.create("feature")
        assert BranchManager.exists("feature")
        
        BranchManager.delete("feature")
        
        assert not BranchManager.exists("feature")
    
    def test_list_all_branches(self, codevovle_root: Path):
        """Test listing all branches."""
        ConfigManager.ensure_initialized()
        
        BranchManager.create("main")
        BranchManager.create("develop")
        BranchManager.create("feature")
        
        branches = BranchManager.list_all()
        
        assert len(branches) == 3
        assert "main" in branches
        assert "develop" in branches
        assert "feature" in branches
        assert branches == sorted(branches)
    
    def test_rename_branch(self, codevovle_root: Path):
        """Test renaming a branch."""
        ConfigManager.ensure_initialized()
        
        BranchManager.create("old_name")
        
        BranchManager.rename("old_name", "new_name")
        
        assert not BranchManager.exists("old_name")
        assert BranchManager.exists("new_name")
        
        branch = BranchManager.read("new_name")
        assert branch["label"] == "new_name"
    
    def test_rename_to_existing_raises(self, codevovle_root: Path):
        """Test that renaming to existing name raises error."""
        ConfigManager.ensure_initialized()
        
        BranchManager.create("branch1")
        BranchManager.create("branch2")
        
        with pytest.raises(StorageError):
            BranchManager.rename("branch1", "branch2")


class TestDiffManager:
    """Tests for DiffManager."""
    
    def test_write_read_diff(self, codevovle_root: Path):
        """Test writing and reading a diff."""
        ConfigManager.ensure_initialized()
        
        diff_content = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
 def hello():
-    print("old")
+    print("new")
"""
        
        DiffManager.write(1, diff_content)
        
        read_content = DiffManager.read(1)
        
        assert read_content == diff_content
    
    def test_exists_diff(self, codevovle_root: Path):
        """Test checking if diff exists."""
        ConfigManager.ensure_initialized()
        
        assert not DiffManager.exists(1)
        
        DiffManager.write(1, "diff content")
        
        assert DiffManager.exists(1)
    
    def test_read_nonexistent_diff(self, codevovle_root: Path):
        """Test reading nonexistent diff raises error."""
        ConfigManager.ensure_initialized()
        
        with pytest.raises(StorageError):
            DiffManager.read(999)
    
    def test_delete_diff(self, codevovle_root: Path):
        """Test deleting a diff."""
        ConfigManager.ensure_initialized()
        
        DiffManager.write(1, "content")
        assert DiffManager.exists(1)
        
        DiffManager.delete(1)
        
        assert not DiffManager.exists(1)
    
    def test_list_all_diffs(self, codevovle_root: Path):
        """Test listing all diffs."""
        ConfigManager.ensure_initialized()
        
        DiffManager.write(1, "diff 1")
        DiffManager.write(2, "diff 2")
        DiffManager.write(5, "diff 5")
        
        tick_ids = DiffManager.list_all()
        
        assert tick_ids == [1, 2, 5]
    
    def test_overwrite_diff(self, codevovle_root: Path):
        """Test overwriting an existing diff."""
        ConfigManager.ensure_initialized()
        
        DiffManager.write(1, "original")
        DiffManager.write(1, "updated")
        
        read_content = DiffManager.read(1)
        
        assert read_content == "updated"


class TestSnapshotManager:
    """Tests for SnapshotManager."""
    
    def test_write_read_snapshot(self, codevovle_root: Path):
        """Test writing and reading a snapshot."""
        ConfigManager.ensure_initialized()
        
        snapshot_content = "line 1\nline 2\nline 3\n"
        
        SnapshotManager.write(snapshot_content)
        
        read_content = SnapshotManager.read()
        
        assert read_content == snapshot_content
    
    def test_exists_snapshot(self, codevovle_root: Path):
        """Test checking if snapshot exists."""
        ConfigManager.ensure_initialized()
        
        assert not SnapshotManager.exists()
        
        SnapshotManager.write("content")
        
        assert SnapshotManager.exists()
    
    def test_read_nonexistent_snapshot(self, codevovle_root: Path):
        """Test reading nonexistent snapshot raises error."""
        ConfigManager.ensure_initialized()
        
        with pytest.raises(StorageError):
            SnapshotManager.read()
    
    def test_delete_snapshot(self, codevovle_root: Path):
        """Test deleting a snapshot."""
        ConfigManager.ensure_initialized()
        
        SnapshotManager.write("content")
        assert SnapshotManager.exists()
        
        SnapshotManager.delete()
        
        assert not SnapshotManager.exists()
    
    def test_overwrite_snapshot(self, codevovle_root: Path):
        """Test overwriting a snapshot."""
        ConfigManager.ensure_initialized()
        
        SnapshotManager.write("original")
        SnapshotManager.write("updated")
        
        read_content = SnapshotManager.read()
        
        assert read_content == "updated"


class TestStateManager:
    """Tests for StateManager."""
    
    def test_ensure_initialized(self, codevovle_root: Path):
        """Test that state initialization works."""
        StateManager.ensure_initialized()
        
        assert (codevovle_root / STATE_FILE).exists()
        
        state = StateManager.read_all()
        
        assert "global_tick_counter" in state
        assert "cursor" in state
        assert state["global_tick_counter"] == 0
    
    def test_get_tick_counter(self, codevovle_root: Path):
        """Test getting tick counter."""
        StateManager.ensure_initialized()
        
        counter = StateManager.get_tick_counter()
        
        assert counter == 0
    
    def test_increment_tick_counter(self, codevovle_root: Path):
        """Test incrementing tick counter."""
        StateManager.ensure_initialized()
        
        tick1 = StateManager.increment_tick_counter()
        tick2 = StateManager.increment_tick_counter()
        tick3 = StateManager.increment_tick_counter()
        
        assert tick1 == 1
        assert tick2 == 2
        assert tick3 == 3
        
        # Verify persistence
        counter = StateManager.get_tick_counter()
        assert counter == 3
    
    def test_set_cursor(self, codevovle_root: Path):
        """Test setting cursor position."""
        StateManager.ensure_initialized()
        
        StateManager.set_cursor("main.py", "main", 5)
        
        cursor = StateManager.get_cursor("main.py")
        
        assert cursor["active_branch"] == "main"
        assert cursor["current_tick"] == 5
    
    def test_set_cursor_multiple_files(self, codevovle_root: Path):
        """Test setting cursor for multiple files."""
        StateManager.ensure_initialized()
        
        StateManager.set_cursor("file1.py", "main", 3)
        StateManager.set_cursor("file2.py", "develop", 7)
        
        cursor1 = StateManager.get_cursor("file1.py")
        cursor2 = StateManager.get_cursor("file2.py")
        
        assert cursor1["active_branch"] == "main"
        assert cursor1["current_tick"] == 3
        assert cursor2["active_branch"] == "develop"
        assert cursor2["current_tick"] == 7
    
    def test_get_nonexistent_cursor(self, codevovle_root: Path):
        """Test getting cursor for nonexistent file returns None."""
        StateManager.ensure_initialized()
        
        cursor = StateManager.get_cursor("nonexistent.py")
        
        assert cursor is None
    
    def test_set_cursor_null_tick(self, codevovle_root: Path):
        """Test setting cursor with null tick."""
        StateManager.ensure_initialized()
        
        StateManager.set_cursor("main.py", "main", None)
        
        cursor = StateManager.get_cursor("main.py")
        
        assert cursor["current_tick"] is None
    
    def test_delete_cursor(self, codevovle_root: Path):
        """Test deleting cursor."""
        StateManager.ensure_initialized()
        
        StateManager.set_cursor("main.py", "main", 5)
        StateManager.delete_cursor("main.py")
        
        cursor = StateManager.get_cursor("main.py")
        
        assert cursor is None


class TestStorageIntegration:
    """Integration tests for storage layer."""
    
    def test_full_workflow(self, codevovle_root: Path):
        """Test a complete workflow using all managers."""
        ConfigManager.ensure_initialized()
        
        # Create main branch
        BranchManager.create("main", parent=None)
        
        # Write snapshot
        SnapshotManager.write("original code\n")
        
        # Write diffs
        DiffManager.write(1, "diff 1 content")
        DiffManager.write(2, "diff 2 content")
        
        # Update branch with diffs
        main_branch = BranchManager.read("main")
        main_branch["diff_chain"] = [1, 2]
        main_branch["head_tick"] = 2
        BranchManager.update("main", main_branch)
        
        # Set cursor
        StateManager.set_cursor("main.py", "main", 2)
        
        # Verify everything
        assert SnapshotManager.read() == "original code\n"
        assert DiffManager.read(1) == "diff 1 content"
        assert DiffManager.read(2) == "diff 2 content"
        
        branch = BranchManager.read("main")
        assert branch["diff_chain"] == [1, 2]
        assert branch["head_tick"] == 2
        
        cursor = StateManager.get_cursor("main.py")
        assert cursor["active_branch"] == "main"
        assert cursor["current_tick"] == 2
    
    def test_atomic_writes(self, codevovle_root: Path):
        """Test that writes are atomic."""
        ConfigManager.ensure_initialized()
        
        # Write config
        ConfigManager.set_file_config("file.py", {"interval": 5})
        
        # Overwrite config
        ConfigManager.set_file_config("file.py", {"interval": 10})
        
        # Verify new value is persisted
        config = ConfigManager.get_file_config("file.py")
        assert config["interval"] == 10
        
        # No partial writes should be visible
        all_config = ConfigManager.read_all()
        assert len(all_config) == 1
    
    def test_concurrent_file_independence(self, codevovle_root: Path):
        """Test that operations on different files don't interfere."""
        ConfigManager.ensure_initialized()
        
        ConfigManager.set_file_config("file1.py", {"interval": 5})
        ConfigManager.set_file_config("file2.py", {"interval": 10})
        
        BranchManager.create("main_file1")
        BranchManager.create("main_file2")
        
        DiffManager.write(1, "diff for file1")
        DiffManager.write(2, "diff for file2")
        
        # Verify independence
        config1 = ConfigManager.get_file_config("file1.py")
        config2 = ConfigManager.get_file_config("file2.py")
        
        assert config1["interval"] == 5
        assert config2["interval"] == 10
        
        branch1 = BranchManager.read("main_file1")
        branch2 = BranchManager.read("main_file2")
        
        assert branch1["label"] == "main_file1"
        assert branch2["label"] == "main_file2"
