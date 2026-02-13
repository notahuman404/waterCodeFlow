"""
Tests for revert logic.

Tests cover:
- File reconstruction from diffs
- Cursor movement to reverted tick
- Error handling (tick not on current branch)
- Recording continues after revert
- Multiple reverts and branches
"""

import time
from pathlib import Path

import pytest

from codevovle.engine import RecordingEngine, RecordingError
from codevovle.storage import BranchManager, StateManager, DiffManager
import storage_utility as su


class TestRevertLogic:
    """Tests for revert functionality."""
    
    def test_revert_to_previous_tick(self, codevovle_root: Path, sample_file: Path):
        """Test reverting to a previous tick."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create two versions
        su.write_text(str(sample_file), "version 1\n")
        tick1 = engine.sample()
        time.sleep(0.06)
        
        su.write_text(str(sample_file), "version 2\n")
        tick2 = engine.sample()
        
        # Revert to tick1
        content = engine.revert_to_tick(tick1)
        
        assert "version 1" in content
        file_content = su.read_text(str(sample_file))
        assert "version 1" in file_content
    
    def test_revert_updates_cursor(self, codevovle_root: Path, sample_file: Path):
        """Test that revert updates cursor."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        su.write_text(str(sample_file), "v1\n")
        tick1 = engine.sample()
        time.sleep(0.06)
        
        su.write_text(str(sample_file), "v2\n")
        tick2 = engine.sample()
        
        # Revert to tick1
        engine.revert_to_tick(tick1)
        
        cursor = StateManager.get_cursor(engine.normalized_path)
        assert cursor["current_tick"] == tick1
    
    def test_revert_nonexistent_tick(self, codevovle_root: Path, sample_file: Path):
        """Test reverting to non-existent tick raises error."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        su.write_text(str(sample_file), "v1\n")
        engine.sample()
        
        with pytest.raises(RecordingError):
            engine.revert_to_tick(999)
    
    def test_revert_tick_not_on_branch(self, codevovle_root: Path, sample_file: Path):
        """Test reverting to tick not on current branch."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create tick on main
        su.write_text(str(sample_file), "v1\n")
        tick1 = engine.sample()
        
        # Create develop branch
        time.sleep(0.06)
        BranchManager.create("develop", parent="main", forked_at_tick=tick1)
        StateManager.set_cursor(engine.normalized_path, "develop", tick1)
        
        # Try to revert to tick that's only on main
        with pytest.raises(RecordingError) as exc_info:
            engine.revert_to_tick(tick1)
        
        assert "not on branch" in str(exc_info.value).lower()
    
    def test_revert_and_continue_recording(self, codevovle_root: Path, sample_file: Path):
        """Test that recording continues after revert."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create two ticks
        su.write_text(str(sample_file), "v1\n")
        tick1 = engine.sample()
        time.sleep(0.06)
        
        su.write_text(str(sample_file), "v2\n")
        tick2 = engine.sample()
        
        # Revert to tick1
        engine.revert_to_tick(tick1)
        time.sleep(0.06)
        
        # Record new change
        su.write_text(str(sample_file), "v3\n")
        tick3 = engine.sample()
        
        # New tick should be created
        assert tick3 is not None
        assert tick3 == 3
        
        status = engine.get_status()
        assert status["cursor_tick"] == tick3


class TestBranchIntegration:
    """Integration tests for branching with revert."""
    
    def test_revert_creates_branch_condition(self, codevovle_root: Path, sample_file: Path):
        """Test scenario where revert + edit creates branch."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Create main branch timeline: tick 1 -> 2 -> 3
        for i in range(3):
            su.write_text(str(sample_file), f"v{i+1}\n")
            engine.sample()
            time.sleep(0.06)
        
        # Revert to tick 1
        engine.revert_to_tick(1)
        
        # Make different edit (this would normally create branch)
        time.sleep(0.06)
        su.write_text(str(sample_file), "alternate\n")
        new_tick = engine.sample()
        
        # Should be able to continue
        assert new_tick is not None
        
        status = engine.get_status()
        assert status["cursor_tick"] == new_tick
