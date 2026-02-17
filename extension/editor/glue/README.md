# glue — Complete UI Integration Layer

A production-ready Python package providing a stable, JSON-friendly facade over CodeVovle and watcher modules. Designed to reduce friction when building UIs by exposing comprehensive APIs for recording management, variable tracking, run grouping, branch control, and more.

## Features

### Recording Management
- **List & inspect recordings**: `list_recordings(file_path)` → metadata with metrics
- **Fetch full diffs**: `get_recording(tick_id)` → diff + size
- **Delete operations**: `delete_recording(tick_id)`, `delete_all_recordings(file_path)`

### Cursor Navigation
- **Get/set cursor**: `get_cursor(file_path)`, `set_cursor(file_path, branch, tick)`
- **Jump to tick**: `jump_to_tick(file_path, tick_id)` for timeline navigation

### Status & Monitoring
- **File status**: `get_status(file_path)` → ready flag, recording count, branches, tick counter
- **Daemon management**: `start_recording()`, `stop_recording()`, `list_daemon_processes()`

### Branch Management
- **List branches**: `get_branches(file_path)` with metadata (name, parent, head_tick, forked_at_tick)
- **Create/rename/delete**: `create_branch()`, `rename_branch()`, `delete_branch()`

### AI Insights
- **Generate insights**: `get_insights(file_path, from_spec, to_spec, model=None)`

### Variable Tracking
- **Timeline**: `get_variable_timeline(file_path, variable_name)` → line numbers, context, match counts
- **Variable values**: `get_variable_value_at_tick(file_path, variable_name)`
- **Tracked variables**: `list_tracked_variables(file_path)` from config
- **Inference**: `infer_variables_from_file(file_path)` → parameters, assignments, returns
- **Change tracking**: `track_variable_changes()` (future: per-tick reconstruction)

### Run Tracking
- **Group recordings**: `get_runs(file_path)` groups ticks into logical runs/sessions
- **Run metadata**: `get_run_details()`, `list_all_runs(file_path)`
- **Delete runs**: `delete_run(file_path, run_id)` → removes all ticks in a run
- **Tagging**: `tag_run()`, `merge_runs()` (placeholders for future UI features)

### Watch / Variable Monitoring
- **Watch proxy**: `watch(value, name, scope, file_path)` → `WatchProxy` with UUID + metadata
- **Registry**: In-process tracking with best-effort native watcher integration
- **Safe**: No-op fallback when native watcher unavailable

## API Organization

```
glue/
├── api.py              # Recording, cursor, branch, daemon, insights
├── variables.py        # Variable extraction, timeline, inference
├── runs.py             # Run grouping, deletion, tagging
├── watch.py            # WatchProxy, registry, integration
├── errors.py           # GlueError, NotFoundError
├── __init__.py         # Public exports
├── README.md           # This file
├── PROGRESS.md         # Dev tracking
├── examples/
│   └── demo_api.py     # Comprehensive usage examples
└── tests/
    ├── test_api_basic.py       # 9 tests: recordings, cursor, daemon, branches
    ├── test_variables.py       # 7 tests: watch, timeline, inference
    └── test_runs.py            # 6 tests: run grouping, deletion, tagging
```

## Quick Start

### Import

```python
from glue import (
    # Recordings
    list_recordings, get_recording, delete_recording,
    # Cursor
    get_cursor, set_cursor, jump_to_tick,
    # Status
    get_status,
    # Daemon
    start_recording, stop_recording, list_daemon_processes,
    # Branches
    get_branches, create_branch, rename_branch, delete_branch,
    # Insights
    get_insights,
    # Variables
    get_variable_timeline, list_tracked_variables,
    # Runs
    runs,
    # Watch
    watch, WatchProxy,
)
```

### Basic Usage

```python
# Check recording status
status = get_status("my_file.py")
print(f"Recordings: {status['recordings_count']}")
print(f"Branches: {status['branches']}")

# List all recordings
recordings = list_recordings("my_file.py")
for rec in recordings:
    print(f"Tick {rec['tick_id']}: +{rec['lines_added']} -{rec['lines_removed']}")

# Get variable occurrences
timeline = get_variable_timeline("my_file.py", "x")
for entry in timeline:
    print(f"Line {entry['line_no']}: {entry['snippet']}")

# Group by runs
all_runs = runs.list_all_runs("my_file.py")
print(f"Total runs: {all_runs['total_runs']}")

# Watch a variable
proxy = watch(x, name="x", scope="local", file_path="my_file.py")
print(proxy.to_dict())
```

### Complete Examples

See [glue/examples/demo_api.py](examples/demo_api.py) for comprehensive usage patterns covering all modules.

Run it:
```bash
python3 glue/examples/demo_api.py
```

## Testing

All 22 tests pass:

```bash
PYTHONPATH=. pytest glue/tests -v
```

- **test_api_basic.py**: 9 tests for recording, cursor, daemon, branches
- **test_variables.py**: 7 tests for watch, timeline, variable inference
- **test_runs.py**: 6 tests for run grouping, deletion, tagging

No external dependencies required beyond CodeVovle/watcher modules already in the repo.

## Design Philosophy

- **Conservative**: Safe fallbacks when underlying modules unavailable
- **JSON-friendly**: All responses are serializable (dicts/lists)
- **Best-effort**: Variable timeline, run inference use heuristics initially
- **Future-proof**: Placeholder methods (`tag_run`, `merge_runs`) ready for UI features
- **No magic**: Thin wrappers over existing CodeVovle APIs

## Future Enhancements

- Tick-by-tick state reconstruction for variable changes
- Native watcher integration for real-time variable tracking
- Run tagging and metadata persistence
- Batch operations and transactions
- Event streaming for live UI updates

## Contributing

When adding features:
1. Implement in corresponding module (`api.py`, `variables.py`, etc.)
2. Add tests in `tests/test_*.py`
3. Update `__init__.py` if exposing new public API
4. Update `PROGRESS.md` with changes
5. Keep backwards compatible with existing exports

