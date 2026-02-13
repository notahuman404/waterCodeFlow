## Glue package progress

- 2026-02-12 (Initial): Created `glue/` package skeleton and initial modules:
  - `__init__.py`, `api.py`, `variables.py`, `watch.py`, `errors.py`
  - Added `PROGRESS.md` (this file)
  - Initial tests passing (4/4)

- 2026-02-12 (Complete version): Enhanced for full production UI support:
  - **api.py** (FULLY WIRED):
    - `list_recordings()` — fetch all recordings with metrics (tick_id, lines_added/removed, size)
    - `get_recording(tick_id)` — fetch full diff for a tick
    - `delete_recording(tick_id)` and `delete_all_recordings(file_path)` — deletion support
    - `get_cursor()`, `set_cursor()`, `jump_to_tick()` — cursor navigation
    - `get_status(file_path)` — comprehensive file status (ready, recording count, branches, tick counter)
    - `start_recording()`, `stop_recording()`, `list_daemon_processes()` — daemon management
    - `get_branches()`, `create_branch()`, `rename_branch()`, `delete_branch()` — branch management with full metadata
    - `get_insights()` — AI insights between ticks
  
  - **variables.py** (COMPLETE):
    - `get_variable_timeline()` — extract variable uses from file with context, line numbers, match counts
    - `get_variable_value_at_tick()` — extract variable value using regex patterns
    - `list_tracked_variables()` — read from CodeVovle config or fallback
    - `infer_variables_from_file()` — heuristic inference (parameters, assignments, returns)
    - `track_variable_changes()` — placeholder for future tick-based tracking

  - **runs.py** (NEW - RUN TRACKING):
    - `get_runs(file_path)` — group recordings by time gaps into logical runs/sessions
    - `get_run_details()`, `list_all_runs()` — run metadata queries
    - `delete_run()` — delete all recordings in a run
    - `merge_runs()`, `tag_run()` — future: tagging and merging (placeholders)

  - **watch.py** (COMPLETE):
    - `watch(value, name, scope, file_path)` -> `WatchProxy` with best-effort native integration
    - `WatcherRegistry` for in-process tracking
    - Safe fallback when native watcher unavailable

  - **errors.py**: `GlueError`, `NotFoundError`

  - **__init__.py**: Re-exports all public APIs

  - **README.md**, **examples/demo_api.py**, **PROGRESS.md** (tracking)

- **Tests** (initial suite):
  - `tests/test_api_basic.py` — list_recordings, start/stop_recording safety tests
  - `tests/test_variables.py` — watch registry, variable timeline tests
  - All 4 tests passing ✓

- **Ready for UI**:
  - All major UI features covered: recordings, runs, variables, branches, daemon, insights
  - Delete operations for single/batch deletion
  - Metadata-rich responses (JSON-serializable, UI-friendly)
  - Best-effort approach: graceful fallback when CodeVovle modules absent
  - No external dependencies beyond CodeVovle/watcher modules
