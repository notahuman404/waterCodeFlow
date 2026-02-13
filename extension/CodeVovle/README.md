# CodeVovle: Multi-file Code Timeline Tracking CLI

A production-grade Python CLI tool for tracking code evolution across multiple files with branching, reverting, and AI-powered insights.

## Features

- **Recording**: Interval-based code change tracking with unified diff storage
- **Reverting**: Reconstruct any version of a tracked file at any recorded tick
- **Hierarchical Branching**: Create, rename, delete, and switch between recursive branches at any nesting level (e.g., `main/feature/auth/jwt`)
- **Full Branch Management**: Create branches in any branch recursively with complete functionality for renaming, deleting, and managing deep hierarchies
- **Insights**: AI-powered code analysis using Gemini, ChatGPT, or Claude with support for hierarchical branch paths
- **Status**: Real-time tracking metadata and recording state

## Installation

CodeVovle requires Python 3.12+ and has no external dependencies for core functionality.

```bash
cd CodeVovle
```

## Usage

All CodeVovle commands enforce that the current working directory is named `CodeVovle` (for safety/containment). All file operations are confined to the project directory.

**⚠️ IMPORTANT: Record command runs continuously and blocks the terminal.** Run it in a background terminal or with `&` for live development.

### Recording Code Changes

Start continuous monitoring of a file:
```bash
python -m codevovle record --file path/to/file.py --interval 5
```

This **continuously monitors** the file at 5-second intervals. Each time a diff is detected, a tick is recorded. **The command keeps running until you press Ctrl+C or kill the process.**

**To run in background:**
```bash
python -m codevovle record --file path/to/file.py --interval 5 &
```

**In a separate terminal:**
```bash
# Terminal 1: Keep recording running
python -m codevovle record --file path/to/file.py --interval 5

# Terminal 2: Check status while still recording
python -m codevovle status --file path/to/file.py
python -m codevovle branch list --file path/to/file.py
```

The command outputs:
- **🔄 Tick X recorded** - When a change is persisted
- **[HH:MM:SS] 📊 Sampled (no changes)** - When sampling happens but file hasn't changed
- Graceful shutdown on Ctrl+C or SIGTERM

## Practical Usage Examples

### Development Workflow

```bash
# Terminal 1: Start recording your main file
$ cd CodeVovle
$ python -m codevovle record --file main.py --interval 2
📝 Recording file: main.py
⏱️  Interval: 2s
💾 Data dir: .codevovle/
✅ Recording initialized
📍 Base snapshot created
🌿 Main branch created
🔄 Starting sampling loop (Ctrl+C to stop)...

[14:32:15] Sampled (no changes)
[14:32:17] Sampled (no changes)
[14:32:19] ✨ Tick 1 recorded (-5 bytes)
[14:32:21] Sampled (no changes)
[14:32:23] ✨ Tick 2 recorded (+45 bytes)
```

```bash
# Terminal 2: While recording runs, check status
$ python -m codevovle status --file main.py
📊 CodeVovle Status: main.py
==================================================
🌿 Active Branch:    main
📍 Current Tick:     2
🔝 Branch Head:      2
📈 Last Tick ID:     2
⏱️  Interval:         2.0s
==================================================
```

```bash
# Terminal 2: Revert to a previous version
$ python -m codevovle revert --file main.py --at 1
⏮️  Reverting to tick: 1
✅ File reverted to tick 1
📄 File: main.py
📊 Bytes changed: -45

# File now contains the state from tick 1
```

### Creating Branches and Comparing Changes

```bash
# Create an experimental branch by editing before the current head
# (Automatically creates a new branch on first edit)
$ python -m codevovle branch jump --file main.py --to feature/experiment

# View the branch timeline
$ python -m codevovle branch list --file main.py
📋 Branches for main.py:
Branch                         Head Tick    Diff Chain Len  Status    
===================================================================
feature/experiment                      5               5  ✓ ACTIVE
main                                    2               2            

# Get AI insights on what changed
$ python -m codevovle insights --file main.py --from main@1 --to feature/experiment@5
🤖 Generating insights for main.py
   From: main@1
   To: feature/experiment@5
   Calling Gemini API (default)...

✅ Insights generated
==================================================
📋 Summary:
Refactored database connection logic to use async/await pattern...

🔍 Key Changes:
  1. Added async def get_connection() function
  2. Removed synchronous database pooling
```

### Reverting

Revert a file to any recorded tick:
```bash
python -m codevovle revert --file path/to/file.py --tick 5
```

This reconstructs the file by applying diffs up to the specified tick, then writes the result to disk.

### Branching

List all branches:
```bash
python -m codevovle branch list --file path/to/file.py
```

Create hierarchical branches (nested at any level):
```bash
# Create a first-level branch
python -m codevovle branch create --file path/to/file.py main/feature-auth

# Create nested branches
python -m codevovle branch create --file path/to/file.py main/feature-auth/jwt
python -m codevovle branch create --file path/to/file.py main/feature-auth/oauth
```

Rename a branch (updates the short name, children updated automatically):
```bash
python -m codevovle branch rename --file path/to/file.py main/old-name new-name
# Results in: main/new-name
```

Delete a branch and all children recursively:
```bash
python -m codevovle branch delete --file path/to/file.py main/feature-old
```

Jump to a branch (reconstruct file to branch head):
```bash
python -m codevovle branch jump --file path/to/file.py main/feature-auth/jwt
```

List children of a specific branch:
```bash
python -m codevovle branch list --file path/to/file.py --parent main/feature-auth
```

**See [RECURSIVE_BRANCHING.md](RECURSIVE_BRANCHING.md) for comprehensive hierarchical branching documentation.**

Branches use path-like naming (e.g., `main/feature/auth`) and support unlimited nesting depth with full management capabilities.

### Insights

Generate AI analysis comparing two points in time:
```bash
# Analyze changes on main branch
python -m codevovle insights --file path/to/file.py --from main@0 --to main@10

# Analyze changes on nested branches
python -m codevovle insights --file path/to/file.py --from main/feature@1 --to main/feature@15

# Mix branches in analysis
python -m codevovle insights --file path/to/file.py --from main@5 --to main/experimental@12
```

Format: `branch/path@tick` or `tick` (defaults to current branch).

Supports all hierarchical branch paths with the same syntax as branch commands.

Requires API key for the selected model:
- Gemini (default): `GEMINI_API_KEY`
- ChatGPT: `CHATGPT_API_KEY`
- Claude: `CLAUDE_API_KEY`

## CLI Grammar

```
codevovle COMMAND [OPTIONS]

Commands:
  record      Start interval-based change tracking
    --file PATH         (required) File path to track
    --interval FLOAT    (required) Sampling interval in seconds

  revert      Restore file to recorded tick
    --file PATH         (required) File path
    --at INT            (required) Tick ID

  branch      Create, delete, rename, list, or switch branches (hierarchical)
    list                List all branches (hierarchical view)
      --file PATH         (required) File path
      --parent BRANCH     (optional) Show children of specific branch
    create              Create a new branch at any nesting level
      --file PATH         (required) File path
      BRANCH              (required) Branch path (e.g., main/feature/auth)
    delete              Delete branch and all children recursively
      --file PATH         (required) File path
      BRANCH              (required) Branch path to delete
    rename              Rename a branch (short name only)
      --file PATH         (required) File path
      BRANCH              (required) Current branch path
      NEW_NAME            (required) New short name
    jump                Switch to a branch
      --file PATH         (required) File path
      BRANCH              (required) Target branch path

  status      Show tracking state
    --file PATH         (required) File path

  insights    Generate AI-powered code analysis
    --file PATH         (required) File path
    --from SPEC         (required) Starting tick (format: branch/path@tick or tick)
    --to SPEC           (required) Ending tick (format: branch/path@tick or tick)
    --model MODEL       (optional) AI model (gemini, chatgpt, claude)

Note: All branch paths use hierarchical naming with "/" separators:
  - main                         (root branch)
  - main/feature                 (feature branch under main)
  - main/feature/auth            (nested branch)
  - main/feature/auth/jwt        (deeply nested branch)
```

## Storage Structure

CodeVovle stores all metadata and diffs in `.codevovle/` directory with hierarchical branch structure:

```
.codevovle/
├── config.json              # Per-file tracking config and intervals
├── state.json               # Global tick counter and per-file cursors
├── branches.json            # Branch metadata and diff chains
├── snapshots/
│   └── base.txt             # Original file snapshot
└── diffs/
    ├── 1.diff               # Unified diff for tick 1
    ├── 2.diff               # Unified diff for tick 2
    └── ...
```

### Key Concepts

- **Tick**: Monotonic integer ID assigned only when a non-empty diff is persisted
- **Branch**: Independent change timeline with parent tick reference and diff chain
- **Diff Chain**: Ordered list of tick IDs representing evolution on a branch
- **Cursor**: Current tick position within active branch per file

## Testing

Run all tests:
```bash
make test           # Quiet mode summary
make test-verbose   # Detailed test output
make coverage       # Coverage report
```

Test suite includes:
- **197 unit and integration tests** across 9 test modules
- **Atomic file I/O tests** ensuring race-free writes
- **Diff engine tests** with patch application and chaining
- **Recording and branching logic tests**
- **End-to-end workflow tests** with complete lifecycles
- **API mocking tests** for Claude integration

All tests pass with zero failures.

## Architecture

CodeVovle is modularized into:

- `cli.py`: Argument parsing and CWD validation
- `storage.py`: Metadata persistence (ConfigManager, BranchManager, DiffManager, SnapshotManager, StateManager)
- `storage_utility.py`: Atomic file I/O primitives
- `engine.py`: Recording loop, revert logic, branch operations (RecordingEngine)
- `diffs.py`: Unified diff computation and patch application
- `insights.py`: Multi-model AI integration (Gemini, ChatGPT, Claude) for code analysis
- `__main__.py`: Entry point with CWD enforcement

## Python Version and Dependencies

- **Minimum**: Python 3.12
- **Core dependencies**: None (stdlib only)
- **Test dependencies**: pytest >= 7.0.0

# CodeVovle — Practical README

This README describes how to use and operate the CodeVovle CLI (recording, branching, reverting and generating insights). It's focused on practical usage, configuration, and behavior you need to understand to run CodeVovle reliably.

Summary
-------
- Purpose: track file evolution over time by sampling file contents and storing unified diffs (ticks), with support for branches and reverts.
- Storage: all metadata and diffs are stored under `.codevovle/` inside your project directory.
- Runtime: `record` runs a sampling loop (foreground or daemon). Daemons run as separate processes; each process has a thread pool used for background writes.

Quickstart
----------
Requirements: Python 3.12+ (standard library only for core features).

1. Open a shell inside your project folder and ensure it is named `CodeVovle` (CodeVovle's CLI enforces this for safety):

```bash
cd /path/to/CodeVovle
```

2. Start recording a file (foreground):

```bash
python -m codevovle record --file src/main.py --interval 5
```

3. Run it in background (separate terminal):

```bash
python -m codevovle record --file src/main.py --interval 5 &
```

Daemon & Global Thread Configuration
-----------------------------------
CodeVovle uses a per-process thread pool for background work (diff persistence and IO). To reduce confusion we made the thread setting global and consistent across all CLI commands and modes:

- Default: 10 threads per process.
- This value is used by every command or operation that constructs a `RecordingEngine` (record, revert, branch operations, status, insights reconstruction) so behavior is consistent whether you run in foreground or via the daemon.

Change and view the setting:

```bash
# Set threads (persisted)
codevovle daemon set-threads --count 4

# Show current setting
codevovle daemon get-threads
```

Notes on effect:
- Threads are per-recording process. If you run multiple daemons, total concurrency = (#daemons) × (threads per daemon).
- Threads are used mainly for background writes; sampling still reads and computes diffs synchronously but scheduling writes to threads minimizes blocking.

Status now shows branch tick totals
----------------------------------
The `status` command now prints the total number of ticks recorded on the active branch (Branch Tick Count). Example output:

```
📊 CodeVovle Status: src/main.py
==================================================
🌿 Active Branch:    main
📍 Current Tick:     12
🔝 Branch Head:      15
📈 Last Tick ID:     35
🧾 Branch Tick Count: 15
⏱️  Interval:         5.0s
==================================================
```


Daemon management (recommended for long-running recording)
-------------------------------------------------------
You can run recording as a managed daemon (recommended for background capture):

- Start: `codevovle daemon start --file src/main.py --interval 5`
- Stop:  `codevovle daemon stop --file src/main.py`
- Status: `codevovle daemon status --file src/main.py` (leave `--file` out to list all)
- List: `codevovle daemon list`
- Stop all: `codevovle daemon stop-all`

Thread configuration (per-process)
---------------------------------
- Default per-daemon thread pool size: **10** (chosen as a balance between throughput and local resource usage).
- Persisted setting: stored in `.codevovle/state.json` via `ThreadConfigManager`.
- Commands to manage it:
  - `codevovle daemon set-threads --count N`  (1 <= N <= 32)
  - `codevovle daemon get-threads`

Notes:
- Threads are used to offload disk writes for diffs so the sampling loop blocks as little as possible.
- Each daemon process uses its own thread pool. Global concurrency = (#daemons) × (threads per daemon).

Core commands (concise)
-----------------------
- `record --file <path> --interval <seconds>`: start sampling loop (foreground). The process logs ticks when non-empty diffs are found.
- `revert --file <path> --at <tick>`: reconstruct file at a recorded tick and overwrite disk file with that state.
- `branch list|rename|jump --file <path> ...`: inspect and modify branch metadata.
- `insights --file <path> --from <spec> --to <spec> [--model claude|gemini|chatgpt]`: generate AI insights between two states (requires API key).

Tick & storage model (brief)
----------------------------
- Snapshot: `.codevovle/snapshots/base.txt` stores the base content used to reconstruct states.
- Diffs: `.codevovle/diffs/<tick>.diff` — unified diff text per tick.
- State: `.codevovle/state.json` holds `global_tick_counter` and per-file `cursor` (active branch and current tick).
- Branch metadata: `.codevovle/branches/<branch>.json` contains `diff_chain` (list of tick IDs).

How sampling works (performance-sensitive path)
----------------------------------------------
1. `record` reads the target file and current base snapshot synchronously (cheap reads).
2. It computes a unified diff synchronously (CPU-bound, usually small for typical edits).
3. If the diff is non-empty:
   - Reserve/assign the next `tick` id immediately (atomic increment in `state.json`).
   - Schedule the diff write to disk on a thread pool (background) — so the sampling loop is not blocked by disk latency.
   - Update branch metadata and cursor once a tick exists.

Why this design:
- Keeps ordering and deterministic tick assignment (tick IDs are sequential).
- Minimizes time spent blocking the sampling loop on slow disks by offloading writes.
- Keeps the implementation safe: file I/O remains atomic and writes are best-effort with fallback.

Implications for user machine performance
----------------------------------------
- CPU: Diff computation runs on the recording process main thread; small diffs are cheap. If diffs are very large/complex, CPU usage spikes briefly.
- Disk I/O: Writes happen on worker threads, reducing blocking on the sampling loop. Disk throughput depends on number of threads and disk speed.
- Memory: Thread pools and queued diff writes use memory proportional to queued diffs; under heavy churn the queue may grow (future option: bounded queue).

Recommendations to minimize local impact
--------------------------------------
- Keep per-daemon thread count modest (10 default). Reduce to 2–4 on small machines: `codevovle daemon set-threads --count 4`.
- Increase sampling interval for large files or slow disks (e.g., 5–10s).
- Use `daemon` mode so recording runs in a separate process and does not share the interactive terminal.

Insights (AI)
-------------
- Supported models: `claude`, `gemini`, `chatgpt`.
- API keys may be provided via environment variables or a `.env` file. Env var names accepted:
  - `CLAUDE_API_KEY`, `GEMINI_API_KEY`, `CHATGPT_API_KEY`
  - Or plain `CLAUDE`, `GEMINI`, `CHATGPT` (less common)
- Example: `export CLAUDE_API_KEY="sk-..."` then run:

```bash
python -m codevovle insights --file src/main.py --from main@1 --to main@5
```

If no API keys are present, `InsightsEngine` can be constructed for local operations, but `generate_insights()` will raise a clear error listing expected environment variable names.

Testing
-------
- Run the CodeVovle unit and integration tests:

```bash
cd CodeVovle
pytest -q CodeVovle/tests
```

- The repository uses atomic writes and includes tests that exercise concurrency and IO.

Developer notes (internals)
--------------------------
- `codevovle/cli.py` — argument parsing and command registration.
- `codevovle/handlers.py` — implementations for CLI commands.
- `codevovle/engine.py` — `RecordingEngine` drives sampling, diffs, and tick metadata.
- `codevovle/storage.py` — `ConfigManager`, `StateManager`, `DiffManager`, `SnapshotManager`, `BranchManager`, and `ThreadConfigManager` for persisted settings.
- `codevovle/daemon.py` — manages background daemon processes and writes `.codevovle/daemons/*.daemon` metadata files.
- `codevovle/insights.py` — AI integration with model selection and API-key checks during generation.

Troubleshooting
---------------
- "No daemons running" — check `.codevovle/daemons/` and process list. Use `codevovle daemon list`.
- If ticks are not being created:
  - Increase `--interval` to avoid sampling while disk is busy.
  - Check `.codevovle/diffs/` for `.diff` files.
- If `insights` fails: verify API keys are set and reachable.

Contributing
------------
- Follow the established test suite and add tests for new behavior.
- Keep file I/O atomic and avoid global mutable state.

License & authorship
--------------------
Provided by the CodeVovle development team. See repository top-level files for license terms.

----

If you'd like, I can also:
- Add a small section with example `.env` content and a sample CI snippet that runs tests and lints.
- Add runtime metrics (queue length, average write latency) exposed via a `status` subcommand.

End of README.
