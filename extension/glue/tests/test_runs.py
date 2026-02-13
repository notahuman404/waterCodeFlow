"""Tests for glue.runs module (run tracking and grouping)."""
from glue import runs
from glue.errors import GlueError


def test_get_runs_returns_list():
    """get_runs returns a list of run dicts."""
    res = runs.get_runs("/tmp/no_such_file.py")
    assert isinstance(res, list)


def test_list_all_runs_returns_dict():
    """list_all_runs returns a dict with runs summary."""
    res = runs.list_all_runs("/tmp/no_such_file.py")
    assert isinstance(res, dict)
    assert "file_path" in res
    assert "total_runs" in res
    assert "runs" in res


def test_get_run_details_raises_when_not_found():
    """get_run_details raises GlueError for nonexistent run."""
    try:
        runs.get_run_details("/tmp/no_such_file.py", run_id=9999)
        # If storage unavailable, get_runs returns [], so this raises GlueError
        assert False, "Should have raised GlueError"
    except GlueError:
        pass


def test_delete_run_raises_safely():
    """delete_run raises GlueError or returns int."""
    try:
        count = runs.delete_run("/tmp/no_such_file.py", run_id=9999)
        # If storage available but run not found, raises GlueError
        assert False, "Should have raised GlueError"
    except GlueError:
        pass


def test_merge_runs_requires_multiple():
    """merge_runs requires at least 2 run IDs."""
    try:
        runs.merge_runs("/tmp/no_such_file.py", [1])
        assert False, "Should have raised GlueError"
    except GlueError:
        pass


def test_tag_run_returns_bool():
    """tag_run returns True (placeholder)."""
    result = runs.tag_run("/tmp/no_such_file.py", run_id=0, tag="test")
    assert result is True
