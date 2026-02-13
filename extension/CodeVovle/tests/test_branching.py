"""
Tests for branch operations (list, rename, jump).

Tests cover:
- Listing branches
- Renaming branches
- Jumping to branches
- File reconstruction on branch jump
- Cursor updates on branch operations
"""

import time
from pathlib import Path

import pytest

from codevovle.engine import RecordingEngine, RecordingError
from codevovle.storage import BranchManager, StateManager
import storage_utility as su


class TestBranchOperations:
    """Tests for branch commands."""
    
    def test_list_branches(self, codevovle_root: Path, sample_file: Path):
        """Test listing branches."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create some branches
        BranchManager.create("develop")
        BranchManager.create("feature")
        
        branches = engine.list_branches()
        
        assert "main" in branches
        assert "develop" in branches
        assert "feature" in branches
        assert len(branches) == 3
    
    def test_list_branches_empty(self, codevovle_root: Path, sample_file: Path):
        """Test listing when only main exists."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        branches = engine.list_branches()
        
        assert branches == ["main"]
    
    def test_rename_branch(self, codevovle_root: Path, sample_file: Path):
        """Test renaming a branch."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        BranchManager.create("develop")
        
        engine.rename_branch("develop", "dev")
        
        branches = engine.list_branches()
        
        assert "dev" in branches
        assert "develop" not in branches
    
    def test_rename_nonexistent_branch(self, codevovle_root: Path, sample_file: Path):
        """Test renaming non-existent branch raises error."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        with pytest.raises(RecordingError):
            engine.rename_branch("nonexistent", "other")
    
    def test_rename_to_existing_raises(self, codevovle_root: Path, sample_file: Path):
        """Test rename to existing branch raises error."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        BranchManager.create("develop")
        
        with pytest.raises(RecordingError):
            engine.rename_branch("develop", "main")
    
    def test_rename_updates_cursor(self, codevovle_root: Path, sample_file: Path):
        """Test that renaming active branch updates cursor."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Switch to a branch
        BranchManager.create("develop")
        StateManager.set_cursor(engine.normalized_path, "develop", 1)
        
        engine.rename_branch("develop", "dev")
        
        cursor = StateManager.get_cursor(engine.normalized_path)
        assert cursor["active_branch"] == "dev"
    
    def test_jump_to_branch(self, codevovle_root: Path, sample_file: Path):
        """Test jumping to a branch."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create content on main
        su.write_text(str(sample_file), "main content\n")
        tick1 = engine.sample()
        
        # Create and switch to develop
        BranchManager.create("develop", parent="main", forked_at_tick=tick1)
        
        engine.jump_to_branch("develop")
        
        cursor = StateManager.get_cursor(engine.normalized_path)
        assert cursor["active_branch"] == "develop"
    
    def test_jump_nonexistent_branch(self, codevovle_root: Path, sample_file: Path):
        """Test jumping to non-existent branch raises error."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        with pytest.raises(RecordingError):
            engine.jump_to_branch("nonexistent")
    
    def test_jump_reconstructs_file(self, codevovle_root: Path, sample_file: Path):
        """Test that jump reconstructs file to branch head."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create main timeline
        su.write_text(str(sample_file), "main v1\n")
        tick1 = engine.sample()
        time.sleep(0.06)
        
        su.write_text(str(sample_file), "main v2\n")
        tick2 = engine.sample()
        
        # Create develop from tick1
        develop_branch = BranchManager.create("develop", parent="main", forked_at_tick=tick1)
        
        # Manually create a diff for develop
        from codevovle.diffs import compute_unified_diff
        from codevovle.storage import DiffManager
        
        # Revert to tick1 state
        tick3 = engine.revert_to_tick(tick1)
        time.sleep(0.06)
        
        # Switch to develop and make a different change
        StateManager.set_cursor(engine.normalized_path, "develop", tick1)
        su.write_text(str(sample_file), "develop change\n")
        tick_dev = engine.sample()
        
        # Now jump back to main
        engine.jump_to_branch("main")
        
        cursor = StateManager.get_cursor(engine.normalized_path)
        assert cursor["active_branch"] == "main"
        
        # File should be reconstructed to main's head
        file_content = su.read_text(str(sample_file))
        assert "main" in file_content


class TestBranchJumpAdvanced:
    """Advanced tests for branch jumping."""
    
    def test_jump_empty_branch(self, codevovle_root: Path, sample_file: Path):
        """Test jumping to branch with no ticks."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create a branch but don't add ticks to it
        BranchManager.create("empty_branch")
        
        # Should be able to jump
        engine.jump_to_branch("empty_branch")
        
        cursor = StateManager.get_cursor(engine.normalized_path)
        assert cursor["active_branch"] == "empty_branch"
        assert cursor["current_tick"] is None
