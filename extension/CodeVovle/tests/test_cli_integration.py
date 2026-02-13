"""
Integration tests for CLI command handlers.

Tests that CLI commands actually execute and produce working behavior.
"""

import subprocess
import json
import os
import sys
import time
import threading
from pathlib import Path
import tempfile
import shutil


def test_cli_record_command_actually_samples():
    """Test that 'record' command continuously samples and creates ticks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a CodeVovle directory
        codevovle_dir = Path(tmpdir) / "CodeVovle"
        codevovle_dir.mkdir()
        
        # Create a test file
        test_file = codevovle_dir / "test.py"
        test_file.write_text("x = 1\n")
        
        # Get CodeVovle directory for PYTHONPATH
        codevovle_root = str(Path(__file__).parent.parent)
        
        # Run record command in background with short interval
        env = os.environ.copy()
        env["PYTHONPATH"] = codevovle_root + ":" + env.get("PYTHONPATH", "")
        
        # Start recording in background with 0.5s interval
        process = subprocess.Popen(
            [sys.executable, "-m", "codevovle", "record", "--file", "test.py", "--interval", "0.5"],
            cwd=str(codevovle_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        try:
            # Give it time to initialize
            time.sleep(0.5)
            
            # Verify initialization worked
            assert (codevovle_dir / ".codevovle").exists(), "Tracking dir not created"
            assert (codevovle_dir / ".codevovle" / "state.json").exists(), "State file not created"
            
            # Make a file change
            test_file.write_text("x = 1\ny = 2\n")
            
            # Wait for sampling to detect change
            time.sleep(1.0)
            
            # Check that a tick was actually created
            diffs_dir = codevovle_dir / ".codevovle" / "diffs"
            tick_files = list(diffs_dir.glob("*.diff")) if diffs_dir.exists() else []
            
            assert len(tick_files) > 0, f"No ticks recorded! Diffs dir: {diffs_dir}, exists: {diffs_dir.exists() if diffs_dir else False}"
            
            # Make another change
            test_file.write_text("x = 1\ny = 2\nz = 3\n")
            time.sleep(1.0)
            
            # Should have 2 ticks now
            tick_files = list(diffs_dir.glob("*.diff"))
            assert len(tick_files) >= 2, f"Expected at least 2 ticks, got {len(tick_files)}"
            
        finally:
            # Gracefully stop recording
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            
            # Process should exit after terminate
            assert process.poll() is not None, "Process didn't terminate properly"


def test_cli_status_command_shows_ticks():
    """Test that 'status' command displays recorded ticks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a CodeVovle directory
        codevovle_dir = Path(tmpdir) / "CodeVovle"
        codevovle_dir.mkdir()
        
        # Create a test file
        test_file = codevovle_dir / "test.py"
        test_file.write_text("x = 1\n")
        
        # Get CodeVovle directory for PYTHONPATH
        codevovle_root = str(Path(__file__).parent.parent)
        env = os.environ.copy()
        env["PYTHONPATH"] = codevovle_root + ":" + env.get("PYTHONPATH", "")
        
        # Start recording in background
        process = subprocess.Popen(
            [sys.executable, "-m", "codevovle", "record", "--file", "test.py", "--interval", "0.3"],
            cwd=str(codevovle_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        try:
            # Wait for initialization
            time.sleep(0.5)
            
            # Make changes to create ticks
            for i in range(3):
                test_file.write_text(f"x = {i}\n")
                time.sleep(0.4)
            
            # Now check status
            result = subprocess.run(
                [sys.executable, "-m", "codevovle", "status", "--file", "test.py"],
                cwd=str(codevovle_dir),
                capture_output=True,
                text=True,
                env=env
            )
            
            # Check exit code
            assert result.returncode == 0, f"Exit code {result.returncode}, stderr: {result.stderr}"
            
            # Check output contains status information
            assert "Active Branch:" in result.stdout, f"stdout: {result.stdout}"
            assert "Current Tick:" in result.stdout
            assert "main" in result.stdout
            
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


def test_cli_branch_list_command_shows_branches():
    """Test that 'branch list' command shows tracked branches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a CodeVovle directory
        codevovle_dir = Path(tmpdir) / "CodeVovle"
        codevovle_dir.mkdir()
        
        # Create a test file
        test_file = codevovle_dir / "test.py"
        test_file.write_text("x = 1\n")
        
        # Get CodeVovle directory for PYTHONPATH
        codevovle_root = str(Path(__file__).parent.parent)
        env = os.environ.copy()
        env["PYTHONPATH"] = codevovle_root + ":" + env.get("PYTHONPATH", "")
        
        # Start recording in background (don't use timeout)
        process = subprocess.Popen(
            [sys.executable, "-m", "codevovle", "record", "--file", "test.py", "--interval", "0.5"],
            cwd=str(codevovle_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        try:
            # Wait for init
            time.sleep(0.5)
            
            # Run branch list command
            result = subprocess.run(
                [sys.executable, "-m", "codevovle", "branch", "list", "--file", "test.py"],
                cwd=str(codevovle_dir),
                capture_output=True,
                text=True,
                env=env
            )
            
            # Check exit code
            assert result.returncode == 0, f"Exit code {result.returncode}, stderr: {result.stderr}"
            
            # Check output contains branch information
            assert "Branch" in result.stdout or "main" in result.stdout, f"stdout: {result.stdout}"
            
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


def test_cli_cwd_validation():
    """Test that CWD validation works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a non-CodeVovle directory
        other_dir = Path(tmpdir) / "NotCodeVovle"
        other_dir.mkdir()
        
        # Get CodeVovle directory for PYTHONPATH
        codevovle_root = str(Path(__file__).parent.parent)
        env = os.environ.copy()
        env["PYTHONPATH"] = codevovle_root + ":" + env.get("PYTHONPATH", "")
        
        # Try to run a command from wrong directory
        result = subprocess.run(
            [sys.executable, "-m", "codevovle", "status", "--file", "test.py"],
            cwd=str(other_dir),
            capture_output=True,
            text=True,
            env=env,
        )
        
        # Check that it fails
        assert result.returncode != 0, "Should fail with wrong CWD"
        assert "CodeVovle" in result.stderr, f"stderr: {result.stderr}"


def test_cli_revert_command_restores_file():
    """Test that 'revert' command actually restores file to a tick."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a CodeVovle directory
        codevovle_dir = Path(tmpdir) / "CodeVovle"
        codevovle_dir.mkdir()
        
        # Create a test file
        test_file = codevovle_dir / "test.py"
        test_file.write_text("version 0\n")
        
        # Get CodeVovle directory for PYTHONPATH
        codevovle_root = str(Path(__file__).parent.parent)
        env = os.environ.copy()
        env["PYTHONPATH"] = codevovle_root + ":" + env.get("PYTHONPATH", "")
        
        # Start recording in background
        process = subprocess.Popen(
            [sys.executable, "-m", "codevovle", "record", "--file", "test.py", "--interval", "0.3"],
            cwd=str(codevovle_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        try:
            # Wait for initialization
            time.sleep(0.5)
            
            # Create tick 1
            test_file.write_text("version 1\n")
            time.sleep(0.4)
            
            # Create tick 2
            test_file.write_text("version 2\n")
            time.sleep(0.4)
            
            # Verify we have ticks
            diffs_dir = codevovle_dir / ".codevovle" / "diffs"
            tick_files_before = list(diffs_dir.glob("*.diff"))
            assert len(tick_files_before) >= 2, f"Not enough ticks created: {len(tick_files_before)}"
            
            # Get first tick ID
            tick_ids = sorted([int(f.stem) for f in tick_files_before])
            first_tick = tick_ids[0]
            
            # Revert to first tick
            result = subprocess.run(
                [sys.executable, "-m", "codevovle", "revert", "--file", "test.py", "--at", str(first_tick)],
                cwd=str(codevovle_dir),
                capture_output=True,
                text=True,
                env=env
            )
            
            assert result.returncode == 0, f"Exit code {result.returncode}, stderr: {result.stderr}"
            
            # Verify file was actually reverted
            current_content = test_file.read_text()
            assert "version 1" in current_content, f"File not reverted! Content: {current_content}"
            
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


def test_cli_complete_workflow():
    """Test complete workflow: record, create ticks, check status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a CodeVovle directory
        codevovle_dir = Path(tmpdir) / "CodeVovle"
        codevovle_dir.mkdir()
        
        # Create a test file
        test_file = codevovle_dir / "main.py"
        test_file.write_text("def main():\n    pass\n")
        
        # Get CodeVovle directory for PYTHONPATH
        codevovle_root = str(Path(__file__).parent.parent)
        env = os.environ.copy()
        env["PYTHONPATH"] = codevovle_root + ":" + env.get("PYTHONPATH", "")
        
        # Start recording in background with fast interval
        process = subprocess.Popen(
            [sys.executable, "-m", "codevovle", "record", "--file", "main.py", "--interval", "0.3"],
            cwd=str(codevovle_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        try:
            time.sleep(0.5)  # Wait for init
            
            # Make multiple changes
            versions = [
                "def main():\n    print('v1')\n",
                "def main():\n    print('v2')\n",
                "def main():\n    print('v3')\n"
            ]
            
            for version in versions:
                test_file.write_text(version)
                time.sleep(0.4)
            
            # Check status
            result = subprocess.run(
                [sys.executable, "-m", "codevovle", "status", "--file", "main.py"],
                cwd=str(codevovle_dir),
                capture_output=True,
                text=True,
                env=env
            )
            
            assert result.returncode == 0, f"Status failed: {result.stderr}"
            assert "main" in result.stdout
            
            # List branches
            result = subprocess.run(
                [sys.executable, "-m", "codevovle", "branch", "list", "--file", "main.py"],
                cwd=str(codevovle_dir),
                capture_output=True,
                text=True,
                env=env
            )
            
            assert result.returncode == 0, f"Branch list failed: {result.stderr}"
            assert "main" in result.stdout
            
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    print("Running CLI integration tests...")
    print("=" * 60)
    
    tests = [
        ("record: continuous sampling", test_cli_record_command_actually_samples),
        ("status: shows tracking state", test_cli_status_command_shows_ticks),
        ("branch: lists branches", test_cli_branch_list_command_shows_branches),
        ("revert: restores file", test_cli_revert_command_restores_file),
        ("complete: full workflow", test_cli_complete_workflow),
        ("CWD: validation", test_cli_cwd_validation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
