"""Small demo script that exercises the glue API and shows usage patterns.

Run as: python3 glue/examples/demo_api.py
"""
import json
import sys
from pathlib import Path

# Add workspace root to path to import glue
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from glue import api, variables, runs, watch


def demo_recordings():
    """Demo: list and inspect recordings."""
    print("\n=== Recording Operations ===")
    sample_file = "test_sample.py"

    recordings = api.list_recordings(sample_file)
    print(f"Recordings for {sample_file}:")
    print(json.dumps(recordings, indent=2))


def demo_status():
    """Demo: get status of a recording file."""
    print("\n=== Status Check ===")
    sample_file = "test_sample.py"

    status = api.get_status(sample_file)
    print(f"Status for {sample_file}:")
    print(json.dumps(status, indent=2))


def demo_branches():
    """Demo: list and manage branches."""
    print("\n=== Branch Operations ===")
    sample_file = "test_sample.py"

    branches = api.get_branches(sample_file)
    print(f"Branches for {sample_file}:")
    print(json.dumps(branches, indent=2))


def demo_variables():
    """Demo: variable tracking and timeline."""
    print("\n=== Variable Operations ===")
    sample_file = __file__

    # List tracked variables (from config)
    tracked = variables.list_tracked_variables(sample_file)
    print(f"Tracked variables: {tracked}")

    # Infer variables from file
    inferred = variables.infer_variables_from_file(sample_file)
    print(f"Inferred variables (first 3):")
    print(json.dumps(inferred[:3], indent=2))

    # Get timeline for a specific variable
    timeline = variables.get_variable_timeline(sample_file, "sample_file")
    print(f"Timeline for 'sample_file' variable (first 2 matches):")
    print(json.dumps(timeline[:2], indent=2))


def demo_runs():
    """Demo: run tracking and grouping."""
    print("\n=== Run Operations ===")
    sample_file = "test_sample.py"

    run_summary = runs.list_all_runs(sample_file)
    print(f"Runs for {sample_file}:")
    print(json.dumps(run_summary, indent=2))


def demo_watch():
    """Demo: watch() and WatchProxy."""
    print("\n=== Watch Operations ===")

    # Create watched variables
    x = watch.watch(42, name="x", scope="local", file_path="demo.py")
    y = watch.watch([1, 2, 3], name="list_data", scope="local")

    print("Watched variables:")
    print(json.dumps({"x": x.to_dict(), "y": y.to_dict()}, indent=2))


def demo_cursor():
    """Demo: cursor navigation."""
    print("\n=== Cursor Navigation ===")
    sample_file = "test_sample.py"

    cursor = api.get_cursor(sample_file)
    print(f"Current cursor for {sample_file}:")
    print(json.dumps(cursor, indent=2))


def demo_daemon():
    """Demo: daemon process listing."""
    print("\n=== Daemon Processes ===")

    processes = api.list_daemon_processes()
    print(f"Active daemon processes:")
    print(json.dumps(processes, indent=2))


def main():
    """Run all demos."""
    print("=" * 60)
    print("Glue API Demo - showing all major features")
    print("=" * 60)

    try:
        demo_status()
    except Exception as e:
        print(f"Status demo skipped: {e}")

    try:
        demo_recordings()
    except Exception as e:
        print(f"Recordings demo skipped: {e}")

    try:
        demo_branches()
    except Exception as e:
        print(f"Branches demo skipped: {e}")

    try:
        demo_cursor()
    except Exception as e:
        print(f"Cursor demo skipped: {e}")

    try:
        demo_daemon()
    except Exception as e:
        print(f"Daemon demo skipped: {e}")

    try:
        demo_runs()
    except Exception as e:
        print(f"Runs demo skipped: {e}")

    try:
        demo_variables()
    except Exception as e:
        print(f"Variables demo skipped: {e}")

    try:
        demo_watch()
    except Exception as e:
        print(f"Watch demo skipped: {e}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
