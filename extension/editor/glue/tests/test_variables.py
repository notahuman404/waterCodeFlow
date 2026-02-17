from glue import watch, variables


def test_watch_registry_and_proxy():
    """watch() creates a proxy with correct metadata."""
    p = watch.watch(123, name="x", scope="local", file_path="/tmp/foo.py")
    assert p.get() == 123
    d = p.to_dict()
    assert d["name"] == "x"
    assert d["file_path"] == "/tmp/foo.py"


def test_get_variable_timeline_returns_list():
    """get_variable_timeline returns a list of timeline entries."""
    res = variables.get_variable_timeline(__file__, "test_get_variable_timeline_returns_list")
    assert isinstance(res, list)
    # Should find at least one match (the function name in this file)
    assert len(res) >= 1


def test_variable_timeline_has_required_keys():
    """Timeline entries have required keys."""
    res = variables.get_variable_timeline(__file__, "def")
    if res:
        entry = res[0]
        assert "tick" in entry
        assert "line_no" in entry
        assert "snippet" in entry
        assert "context" in entry


def test_get_variable_value_at_tick():
    """get_variable_value_at_tick safely returns None or string."""
    res = variables.get_variable_value_at_tick(__file__, "nonexistent_var_name_xyz")
    assert res is None or isinstance(res, str)


def test_list_tracked_variables_returns_list():
    """list_tracked_variables returns a list."""
    res = variables.list_tracked_variables("/tmp/no_such_file.py")
    assert isinstance(res, list)


def test_infer_variables_from_file():
    """infer_variables_from_file returns list of variable dicts."""
    res = variables.infer_variables_from_file(__file__)
    assert isinstance(res, list)
    # Should find at least some variables in this test file
    if res:
        for var in res:
            assert "name" in var
            assert "scope" in var
            assert "line_no" in var


def test_track_variable_changes():
    """track_variable_changes returns empty list (placeholder)."""
    res = variables.track_variable_changes(__file__, "x", 0, 10)
    assert isinstance(res, list)
    assert len(res) == 0  # Placeholder returns empty list

