"""
Pytest configuration and shared fixtures for CodeVovle tests.

All tests run in a temporary sandbox directory structure
that mimics a CodeVovle project layout.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def codevovle_root(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary CodeVovle project directory and change into it.
    
    Yields the path to the temporary CodeVovle directory.
    Cleans up and restores original cwd after test.
    
    Usage:
        def test_something(codevovle_root):
            # You are now in <tmp>/CodeVovle
            assert os.getcwd().endswith("CodeVovle")
    """
    # Create CodeVovle directory inside tmp_path
    codevovle_dir = tmp_path / "CodeVovle"
    codevovle_dir.mkdir(parents=True, exist_ok=True)
    
    # Create .codevovle subdirectories structure
    (codevovle_dir / ".codevovle").mkdir(exist_ok=True)
    (codevovle_dir / ".codevovle" / "branches").mkdir(exist_ok=True)
    (codevovle_dir / ".codevovle" / "diffs").mkdir(exist_ok=True)
    (codevovle_dir / ".codevovle" / "snapshots").mkdir(exist_ok=True)
    
    # Save original cwd
    original_cwd = os.getcwd()
    
    try:
        # Change to CodeVovle directory
        os.chdir(str(codevovle_dir))
        
        # Add parent directory to sys.path so we can import storage_utility
        parent_dir = str(codevovle_dir.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        yield codevovle_dir
    finally:
        # Restore original cwd
        os.chdir(original_cwd)
        
        # Remove from sys.path if we added it
        if parent_dir in sys.path:
            sys.path.remove(parent_dir)


@pytest.fixture
def sample_file(codevovle_root: Path) -> Path:
    """
    Create a sample file for testing within the CodeVovle sandbox.
    
    Usage:
        def test_something(sample_file):
            # sample_file is a Path object pointing to a temp file inside CodeVovle
    """
    sample = codevovle_root / "sample.txt"
    sample.write_text("initial content\n")
    return sample
