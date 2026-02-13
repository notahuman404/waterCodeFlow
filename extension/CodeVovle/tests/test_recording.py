"""
Tests for recording engine.

Tests cover:
- Initialization and setup
- Interval-based sampling
- Diff computation and persistence
- Tick ID assignment (monotonic, only on non-empty diffs)
- Cursor tracking
- Status reporting
"""

import time
from pathlib import Path

import pytest

from codevovle.engine import RecordingEngine, TickCursor, RecordingError
from codevovle.storage import (
    StateManager,
    ConfigManager,
    BranchManager,
    DiffManager,
    SnapshotManager,
)
import storage_utility as su


class TestRecordingEngineInit:
    """Tests for RecordingEngine initialization."""
    
    def test_engine_creation(self, codevovle_root: Path, sample_file: Path):
        """Test creating a recording engine."""
        engine = RecordingEngine(str(sample_file), 5.0)
        
        assert engine.file_path == str(sample_file)
        assert engine.interval_seconds == 5.0
    
    def test_initialize_tracking(self, codevovle_root: Path, sample_file: Path):
        """Test initialization of tracking."""
        engine = RecordingEngine(str(sample_file), 5.0)
        
        engine.initialize_tracking()
        
        # Check that structure is created
        assert (codevovle_root / ".codevovle").exists()
        assert SnapshotManager.exists()
        assert BranchManager.exists("main")
        
        # Check that cursor is initialized
        cursor = StateManager.get_cursor(engine.normalized_path)
        assert cursor is not None
        assert cursor["active_branch"] == "main"
    
    def test_initialize_creates_config(self, codevovle_root: Path, sample_file: Path):
        """Test that initialization creates config."""
        engine = RecordingEngine(str(sample_file), 7.5)
        
        engine.initialize_tracking()
        
        config = ConfigManager.get_file_config(engine.normalized_path)
        
        assert config is not None
        assert config["interval"] == 7.5
        assert config["file_path"] == engine.normalized_path
    
    def test_initialize_preserves_existing_branch(self, codevovle_root: Path, sample_file: Path):
        """Test that re-initialization preserves existing branches."""
        engine = RecordingEngine(str(sample_file), 5.0)
        
        engine.initialize_tracking()
        BranchManager.create("develop", parent="main")
        
        # Re-initialize
        engine.initialize_tracking()
        
        # develop branch should still exist
        assert BranchManager.exists("develop")
    
    def test_negative_interval_raises(self, codevovle_root: Path, sample_file: Path):
        """Test that negative interval raises error."""
        with pytest.raises(RecordingError):
            RecordingEngine(str(sample_file), -5.0)
    
    def test_zero_interval_raises(self, codevovle_root: Path, sample_file: Path):
        """Test that zero interval raises error."""
        with pytest.raises(RecordingError):
            RecordingEngine(str(sample_file), 0.0)


class TestRecordingEngineSampling:
    """Tests for sampling and diff persistence."""
    
    def test_first_sample_no_change(self, codevovle_root: Path, sample_file: Path):
        """Test that first sample with no change returns None."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        # First sample immediately
        tick = engine.sample()
        
        assert tick is None
    
    def test_sample_creates_tick_on_change(self, codevovle_root: Path, sample_file: Path):
        """Test that sampling creates tick on file change."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        # Make a change
        su.write_text(str(sample_file), "modified content\n")
        
        # First sample
        tick = engine.sample()
        
        assert tick is not None
        assert tick == 1
        assert DiffManager.exists(1)
    
    def test_multiple_samples_within_interval(self, codevovle_root: Path, sample_file: Path):
        """Test that samples within interval are ignored."""
        engine = RecordingEngine(str(sample_file), 10.0)  # Long interval
        engine.initialize_tracking()
        
        # Make change and sample
        su.write_text(str(sample_file), "change1\n")
        tick1 = engine.sample()
        
        # Make another change (still within interval)
        su.write_text(str(sample_file), "change2\n")
        tick2 = engine.sample()
        
        # Second sample should be skipped
        assert tick1 == 1
        assert tick2 is None
    
    def test_sample_after_interval_elapsed(self, codevovle_root: Path, sample_file: Path):
        """Test that sample is taken after interval elapses."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        # First change
        su.write_text(str(sample_file), "change1\n")
        tick1 = engine.sample()
        
        # Wait for interval and make second change
        time.sleep(0.15)
        su.write_text(str(sample_file), "change2\n")
        tick2 = engine.sample()
        
        assert tick1 == 1
        assert tick2 == 2
    
    def test_empty_diff_not_persisted(self, codevovle_root: Path, sample_file: Path):
        """Test that empty diffs don't create ticks."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        # First sample (change)
        su.write_text(str(sample_file), "change\n")
        tick1 = engine.sample()
        
        # Wait and sample without changes
        time.sleep(0.15)
        tick2 = engine.sample()
        
        assert tick1 == 1
        assert tick2 is None
        assert not DiffManager.exists(2)
    
    def test_tick_monotonicity(self, codevovle_root: Path, sample_file: Path):
        """Test that tick IDs are monotonically increasing."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        ticks = []
        for i in range(5):
            su.write_text(str(sample_file), f"change {i}\n")
            tick = engine.sample()
            if tick:
                ticks.append(tick)
            time.sleep(0.06)
        
        # All ticks should be unique and increasing
        assert ticks == sorted(ticks)
        assert len(ticks) == len(set(ticks))
    
    def test_snapshot_updated_after_sample(self, codevovle_root: Path, sample_file: Path):
        """Test that snapshot is updated after sampling."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        original_snapshot = SnapshotManager.read()
        
        # Make change
        new_content = "new content\n"
        su.write_text(str(sample_file), new_content)
        engine.sample()
        
        # Snapshot should be updated
        updated_snapshot = SnapshotManager.read()
        
        assert updated_snapshot == new_content
        assert updated_snapshot != original_snapshot


class TestRecordingEngineStatus:
    """Tests for status reporting."""
    
    def test_status_initial(self, codevovle_root: Path, sample_file: Path):
        """Test initial status."""
        engine = RecordingEngine(str(sample_file), 5.0)
        engine.initialize_tracking()
        
        status = engine.get_status()
        
        assert status["active_branch"] == "main"
        assert status["cursor_tick"] is None
        assert status["branch_head_tick"] is None
        assert status["interval"] == 5.0
    
    def test_status_after_sample(self, codevovle_root: Path, sample_file: Path):
        """Test status after sampling."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        su.write_text(str(sample_file), "change\n")
        tick = engine.sample()
        
        status = engine.get_status()
        
        assert status["active_branch"] == "main"
        assert status["cursor_tick"] == tick
        assert status["branch_head_tick"] == tick
        assert status["last_tick_id"] == 1
    
    def test_status_multiple_branches(self, codevovle_root: Path, sample_file: Path):
        """Test status with multiple branches."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        # Create samples on main
        su.write_text(str(sample_file), "change1\n")
        tick1 = engine.sample()
        
        # Create branch and sample
        BranchManager.create("develop", parent="main", forked_at_tick=tick1)
        StateManager.set_cursor(engine.normalized_path, "develop", tick1)
        
        status = engine.get_status()
        
        assert status["active_branch"] == "develop"
        assert status["cursor_tick"] == tick1


class TestTickCursor:
    """Tests for TickCursor."""
    
    def test_cursor_set_and_get(self, codevovle_root: Path, sample_file: Path):
        """Test setting and getting cursor position."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        cursor = TickCursor(sample_file)
        
        cursor.set_position("main", 5)
        
        branch, tick = cursor.get_position()
        
        assert branch == "main"
        assert tick == 5
    
    def test_cursor_get_branch_head(self, codevovle_root: Path, sample_file: Path):
        """Test getting branch head."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        su.write_text(str(sample_file), "change\n")
        tick = engine.sample()
        
        cursor = TickCursor(sample_file)
        head = cursor.get_branch_head("main")
        
        assert head == tick
    
    def test_cursor_is_at_head(self, codevovle_root: Path, sample_file: Path):
        """Test checking if cursor is at head."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        su.write_text(str(sample_file), "change\n")
        tick = engine.sample()
        
        cursor = TickCursor(sample_file)
        
        assert cursor.is_at_head() is True
    
    def test_cursor_not_at_head(self, codevovle_root: Path, sample_file: Path):
        """Test when cursor is not at head."""
        engine = RecordingEngine(str(sample_file), 0.1)
        engine.initialize_tracking()
        
        su.write_text(str(sample_file), "change\n")
        tick = engine.sample()
        
        # Move cursor back
        cursor = TickCursor(sample_file)
        cursor.set_position("main", tick - 1)
        
        assert cursor.is_at_head() is False


class TestRecordingIntegration:
    """Integration tests for recording."""
    
    def test_continuous_recording(self, codevovle_root: Path, sample_file: Path):
        """Test continuous recording workflow."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Simulate editing and sampling
        ticks = []
        for i in range(3):
            # Edit file
            content = f"version {i}\nmore content\n"
            su.write_text(str(sample_file), content)
            
            # Sample
            tick = engine.sample()
            if tick:
                ticks.append(tick)
            
            # Wait for interval
            time.sleep(0.06)
        
        # Verify ticks were created
        assert len(ticks) > 0
        assert all(DiffManager.exists(t) for t in ticks)
        
        # Verify branch state
        branch = BranchManager.read("main")
        assert len(branch["diff_chain"]) == len(ticks)
        assert branch["head_tick"] == ticks[-1]
    
    def test_file_lifecycle(self, codevovle_root: Path, sample_file: Path):
        """Test complete file lifecycle from empty to complex."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        states = [
            "def hello():\n    pass\n",
            "def hello():\n    print('hello')\n",
            "def hello():\n    print('hello')\ndef world():\n    pass\n"
        ]
        
        tick_count = 0
        for state in states:
            su.write_text(str(sample_file), state)
            tick = engine.sample()
            if tick:
                tick_count += 1
            time.sleep(0.06)
        
        status = engine.get_status()
        assert status["branch_head_tick"] == tick_count
        assert status["last_tick_id"] == tick_count
