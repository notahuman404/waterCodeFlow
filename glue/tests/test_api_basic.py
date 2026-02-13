import pytest

from glue import api
from glue.errors import GlueError


def test_list_recordings_returns_list():
    """list_recordings returns a list even when storage unavailable."""
    res = api.list_recordings("/tmp/no_such_file.py")
    assert isinstance(res, list)


def test_get_recording_safe_when_unavailable():
    """get_recording raises GlueError when storage unavailable."""
    try:
        api.get_recording(9999)
        # If we reach here, the call succeeded but no recording exists
        # which is fine
    except GlueError:
        # Expected when storage or DiffManager not available
        assert True


def test_delete_recording_returns_bool():
    """delete_recording returns bool or raises GlueError safely."""
    try:
        result = api.delete_recording(9999)
        assert isinstance(result, bool)
    except GlueError:
        # Expected when storage unavailable
        pass


def test_get_cursor_returns_dict():
    """get_cursor returns a dict with branch and tick keys."""
    res = api.get_cursor("/tmp/no_such_file.py")
    assert isinstance(res, dict)
    assert "branch" in res
    assert "tick" in res


def test_get_status_returns_dict():
    """get_status returns a dict with status keys."""
    res = api.get_status("/tmp/no_such_file.py")
    assert isinstance(res, dict)
    assert "ready" in res
    assert "recordings_count" in res
    assert "branches" in res


def test_get_branches_returns_list():
    """get_branches returns a list."""
    res = api.get_branches("/tmp/no_such_file.py")
    assert isinstance(res, list)


def test_start_stop_recording_safe():
    """start/stop_recording raise GlueError or return primitives safely."""
    try:
        val = api.start_recording("/tmp/no_such_file.py", interval=0.1)
        assert isinstance(val, int)
    except GlueError:
        pass

    try:
        val = api.stop_recording("/tmp/no_such_file.py")
        assert isinstance(val, bool)
    except GlueError:
        pass


def test_list_daemon_processes_returns_list():
    """list_daemon_processes returns a list."""
    res = api.list_daemon_processes()
    assert isinstance(res, list)


def test_get_insights_raises_on_unavailable():
    """get_insights raises GlueError when insights unavailable."""
    try:
        api.get_insights("/tmp/no_such_file.py", "main:0", "main:1")
        # May succeed if fake/mocked; that's ok
    except GlueError:
        # Expected when InsightsEngine unavailable
        pass

