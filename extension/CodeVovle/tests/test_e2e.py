"""
End-to-end integration tests for CodeVovle.

Tests complete workflows combining all components.
"""

import time
from pathlib import Path

import pytest

from codevovle.engine import RecordingEngine
from codevovle.storage import BranchManager, StateManager
import storage_utility as su


class TestE2EWorkflows:
    """End-to-end workflow tests."""
    
    def test_record_revert_continue(self, codevovle_root: Path, sample_file: Path):
        """Test workflow: record → edit → revert → continue."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Record v1
        su.write_text(str(sample_file), "v1\n")
        t1 = engine.sample()
        time.sleep(0.06)
        
        # Record v2
        su.write_text(str(sample_file), "v2\n")
        t2 = engine.sample()
        time.sleep(0.06)
        
        # Revert to v1
        engine.revert_to_tick(t1)
        
        # Continue recording different change
        time.sleep(0.06)
        su.write_text(str(sample_file), "alternate\n")
        t3 = engine.sample()
        
        assert t3 == 3
        assert "alternate" in su.read_text(str(sample_file))
    
    def test_branch_and_merge_simulation(self, codevovle_root: Path, sample_file: Path):
        """Test branch creation and navigation."""
        engine = RecordingEngine(str(sample_file), 0.05)
        engine.initialize_tracking()
        
        # Main branch work
        su.write_text(str(sample_file), "main v1\n")
        t1 = engine.sample()
        time.sleep(0.06)
        
        su.write_text(str(sample_file), "main v2\n")
        t2 = engine.sample()
        
        # Create develop branch
        BranchManager.create("develop", parent="main", forked_at_tick=t1)
        StateManager.set_cursor(engine.normalized_path, "develop", t1)
        
        # Develop branch work (simulate on a separate timeline)
        time.sleep(0.06)
        su.write_text(str(sample_file), "develop feature\n")
        t3 = engine.sample()
        
        # Switch back to main
        engine.jump_to_branch("main")
        
        status = engine.get_status()
        assert status["active_branch"] == "main"
        assert status["branch_head_tick"] == t2
    
    def test_multiple_files_independent(self, codevovle_root: Path):
        """Test tracking multiple independent files."""
        file1 = codevovle_root / "file1.py"
        file2 = codevovle_root / "file2.py"
        
        file1.write_text("f1_init\n")
        file2.write_text("f2_init\n")
        
        engine1 = RecordingEngine(str(file1), 0.05)
        engine2 = RecordingEngine(str(file2), 0.05)
        
        engine1.initialize_tracking()
        engine2.initialize_tracking()
        
        # Edit file1
        su.write_text(str(file1), "f1_v1\n")
        t1_1 = engine1.sample()
        time.sleep(0.06)
        
        # Edit file2
        su.write_text(str(file2), "f2_v1\n")
        t2_1 = engine2.sample()
        
        # Verify independence
        status1 = engine1.get_status()
        status2 = engine2.get_status()
        
        assert status1["last_tick_id"] >= 1
        assert status2["last_tick_id"] >= 1
    
    def test_complete_lifecycle(self, codevovle_root: Path, sample_file: Path):
        """Test complete file lifecycle: init -> record -> branches -> revert."""
        engine = RecordingEngine(str(sample_file), 0.05)
        
        # Initialize
        engine.initialize_tracking()
        
        # Record timeline
        versions = ["v1", "v2", "v3"]
        ticks = []
        
        for v in versions:
            su.write_text(str(sample_file), f"{v}\n")
            tick = engine.sample()
            ticks.append(tick)
            time.sleep(0.06)
        
        # Verify timeline
        status = engine.get_status()
        assert status["cursor_tick"] == ticks[-1]
        assert status["branch_head_tick"] == ticks[-1]
        
        # Revert to middle
        engine.revert_to_tick(ticks[0])
        
        # Verify revert
        status = engine.get_status()
        assert status["cursor_tick"] == ticks[0]
        
        # Continue from middle
        time.sleep(0.06)
        su.write_text(str(sample_file), "alt_v\n")
        alt_tick = engine.sample()
        
        # Verify continuation
        assert alt_tick is not None
        assert alt_tick > ticks[-1]
