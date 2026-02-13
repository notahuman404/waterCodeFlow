"""
Progress tracking utility for CodeVovle.

Updates CODEVOVLE_PROGRESS.md with test results.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import storage_utility as su


PROGRESS_FILE = Path(__file__).parent.parent / "CODEVOVLE_PROGRESS.md"


def update_progress(feature_name: str, implemented: bool, tests_path: str, passed: bool, timestamp: str = None) -> None:
    """
    Update progress file with feature status.
    
    Args:
        feature_name: Name of feature/step
        implemented: Whether feature is fully implemented
        tests_path: Path to test file
        passed: Whether tests passed
        timestamp: ISO8601 timestamp (auto-generated if None)
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Read existing progress or create new
    try:
        progress_content = su.read_text(str(PROGRESS_FILE))
    except FileNotFoundError:
        progress_content = "# CodeVovle Implementation Progress\n\n"
    
    # Add or update entry
    entry = f"- **{feature_name}**: implemented={implemented}, tests={tests_path}, passed={passed}, {timestamp}\n"
    
    progress_content += entry
    
    # Write back
    su.write_text(str(PROGRESS_FILE), progress_content)


def main():
    """Main entry point for progress updates."""
    if len(sys.argv) < 5:
        print("Usage: python update_progress.py <feature> <implemented> <tests_path> <passed>")
        sys.exit(1)
    
    feature_name = sys.argv[1]
    implemented = sys.argv[2].lower() == "true"
    tests_path = sys.argv[3]
    passed = sys.argv[4].lower() == "true"
    
    update_progress(feature_name, implemented, tests_path, passed)
    print(f"Updated progress: {feature_name}")


if __name__ == "__main__":
    main()
