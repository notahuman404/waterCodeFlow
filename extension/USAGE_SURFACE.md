# System Usage Surface

**Last Updated:** February 10, 2026  
**Status:** Core fixes applied - see [CRITICAL_FIXES.md](CRITICAL_FIXES.md) for safety improvements

⚠️ **Note on Core Stability:** Recent critical fixes have been applied to the userfaultfd integration layer to improve safety and correctness. All 271 testable scenarios pass with zero regressions. 
---

Grouped by user intent. Each capability lists the required fields exactly.

**Record & Sampling**
- Capability name: Record file changes (foreground)
  - How it is invoked: CLI command `codevovle record` (entrypoint via `python -m codevovle` / `codevovle`) with subcommand `record`
  - Required inputs: `--file` (path to file), `--interval` (sampling interval in seconds)
  - Optional inputs: `--out` (output directory for diffs), `--profile` (enable profiling flag), `--threads` (thread count), `--daemonized` (internal flag suppressed in help)
  - Preconditions: Current working directory must be named `CodeVovle`; target file must exist inside the `CodeVovle` working directory
  - What the capability does (observable effects only): Starts a continuous sampling loop; on detected changes computes diffs; persists diffs; updates timeline metadata; prints progress and tick logs to stdout/stderr; responds to Ctrl+C for graceful shutdown
  - State read: Reads the target file content and existing `.codevovle` snapshot/state/branch/diff files
  - State written or mutated: Writes/updates `.codevovle/state.json`, `.codevovle/config.json` (per-file config), `.codevovle/snapshots/base.txt` (base snapshot), `.codevovle/diffs/<tick>.diff`, `.codevovle/branches/<branch>.json`
  - User-visible outputs (files created, logs emitted, state changes): Console logs (sampling ticks, summaries); `.codevovle/` directory and files as above; updated cursor/state
  - Failure modes (errors, no-ops, partial execution): Invalid interval or missing file errors; sampling exceptions emit warnings and continue or sleep; I/O failures may drop diffs (best-effort persistence); KeyboardInterrupt triggers graceful shutdown with summary

**Record (background via daemon manager)**
- Capability name: Start background recording (daemon start)
  - How it is invoked: CLI command `codevovle daemon start` or programmatic call to `DaemonManager.start()`
  - Required inputs: `--file` (path to file), `--interval` (seconds)
  - Optional inputs: `num_threads` (via stored config or explicit `--threads` when launching record)
  - Preconditions: File exists; `.codevovle/` directory writable
  - What the capability does (observable effects only): Launches a background process executing the `record` command; registers daemon metadata on disk
  - State read: Reads thread configuration from `.codevovle/state.json` (daemon thread config)
  - State written or mutated: Writes `.codevovle/daemons/<safe-file>.daemon` (metadata including PID, interval, start_time)
  - User-visible outputs: Console output when starting; daemon metadata file in `.codevovle/daemons/`; background process PID
  - Failure modes: If a daemon is already running for the file, start raises an error; process spawn failures cause DaemonError; malformed daemon metadata may be cleaned up

- Capability name: Stop background recording (daemon stop)
  - How it is invoked: CLI command `codevovle daemon stop --file <file>` or `DaemonManager.stop(file_path)`
  - Required inputs: `--file` (path to file)
  - Optional inputs: none
  - Preconditions: Corresponding daemon metadata file exists and PID refers to a running process
  - What the capability does (observable effects only): Attempts to terminate the daemon process group (SIGTERM), removes daemon metadata file
  - State read: Reads `.codevovle/daemons/<safe-file>.daemon`
  - State written or mutated: Deletes the daemon metadata file on success
  - User-visible outputs: Console logs indicating stop or "no daemon running"; daemon metadata file removal
  - Failure modes: If metadata file missing returns no-op; process termination may fail silently; exceptions propagate as DaemonError

- Capability name: Query daemon status / list daemons
  - How it is invoked: `codevovle daemon status --file <file>` or `codevovle daemon status` (no file) / `codevovle daemon list`
  - Required inputs: `--file` optional (none required to list all)
  - Optional inputs: none
  - Preconditions: None (reads existing metadata)
  - What the capability does (observable effects only): Reads daemon metadata files and reports running daemons and per-file PID/interval/elapsed time
  - State read: `.codevovle/daemons/*.daemon`
  - State written or mutated: May remove stale metadata files if referenced PIDs are dead
  - User-visible outputs: Console listing of daemons or per-file status
  - Failure modes: Corrupt JSON daemon files are removed; absence of daemons yields informational message

- Capability name: Stop all daemons
  - How it is invoked: `codevovle daemon stop-all` or `DaemonManager.stop_all()`
  - Required inputs: none
  - Optional inputs: none
  - Preconditions: None
  - What the capability does (observable effects only): Iterates discovered daemon metadata and attempts to stop each daemon; removes metadata files
  - State read: `.codevovle/daemons/*.daemon`
  - State written or mutated: Removes daemon metadata files; may change process state (terminate PIDs)
  - User-visible outputs: Console logs including count stopped
  - Failure modes: Individual daemon stop operations may fail silently; count returned reflects successes only

**Thread Configuration**
- Capability name: Set daemon thread count
  - How it is invoked: CLI command `codevovle daemon set-threads --count <num>` or `ThreadConfigManager.set_thread_count(num)`
  - Required inputs: `--count` (integer 1..32)
  - Optional inputs: none
  - Preconditions: none (value validated 1..32)
  - What the capability does (observable effects only): Stores thread count used by daemons and recording engine
  - State read: `.codevovle/state.json` (existing state)
  - State written or mutated: Writes `thread_config.daemon_threads` in `.codevovle/state.json`
  - User-visible outputs: Console confirmation message
  - Failure modes: Invalid counts raise ValueError and error message; write failures may raise exceptions

- Capability name: Get daemon thread configuration
  - How it is invoked: `codevovle daemon get-threads` or `ThreadConfigManager.get_thread_count()`
  - Required inputs: none
  - Optional inputs: none
  - Preconditions: none
  - What the capability does (observable effects only): Reads and prints current configured thread count
  - State read: `.codevovle/state.json`
  - State written or mutated: none
  - User-visible outputs: Console prints the thread count
  - Failure modes: Read errors emit an error message

**Timeline Navigation & Manipulation**
- Capability name: Revert file to a tick
  - How it is invoked: CLI command `codevovle revert --file <file> --at <tick>` or `RecordingEngine.revert_to_tick(tick)`
  - Required inputs: `--file`, `--at` (integer tick)
  - Optional inputs: none
  - Preconditions: Tracking initialized for the file; specified tick must exist on the current active branch
  - What the capability does (observable effects only): Reconstructs file content at the tick and overwrites the working file; updates cursor position
  - State read: `.codevovle/snapshots/base.txt`, `.codevovle/diffs/<tick>.diff`, `.codevovle/branches/<branch>.json`, `.codevovle/state.json`
  - State written or mutated: Overwrites target file on disk; updates `.codevovle/state.json` cursor for the file
  - User-visible outputs: Console confirmation, bytes-changed summary, file content replaced on disk
  - Failure modes: If tick not on branch raises error; file write errors propagate; malformed diffs cause Reconstruction/RecordingError

- Capability name: Show status for a file
  - How it is invoked: `codevovle status --file <file>` or `RecordingEngine.get_status()`
  - Required inputs: `--file`
  - Optional inputs: none
  - Preconditions: None (will report best-effort info)
  - What the capability does (observable effects only): Reads stored state/config and prints active branch, current tick, branch head, last tick ID, interval, and counts
  - State read: `.codevovle/state.json`, `.codevovle/config.json`, `.codevovle/branches/*.json`
  - State written or mutated: none
  - User-visible outputs: Console-formatted status
  - Failure modes: Read errors reported as status error

**Branch Management**
- Capability name: List branches
  - How it is invoked: `codevovle branch list --file <file>` or `RecordingEngine.list_branches()`
  - Required inputs: `--file`
  - Optional inputs: none
  - Preconditions: Tracking initialized (branches directory exists or empty)
  - What the capability does (observable effects only): Reads branch metadata and displays branch names, head tick, diff chain length, and active branch indicator
  - State read: `.codevovle/branches/*.json`, `.codevovle/state.json`
  - State written or mutated: none
  - User-visible outputs: Console table of branches
  - Failure modes: Missing branch files yields "No branches" message; corrupt branch JSON skipped

- Capability name: Rename branch
  - How it is invoked: `codevovle branch rename --file <file> <branch> <new_name>` or `RecordingEngine.rename_branch(old, new)`
  - Required inputs: `--file`, positional `branch`, positional `new_name`
  - Optional inputs: none
  - Preconditions: `branch` exists; `new_name` does not already exist
  - What the capability does (observable effects only): Moves branch metadata to a new filename and updates branch label; updates cursor if the active branch was renamed
  - State read: `.codevovle/branches/<old>.json`, `.codevovle/state.json`
  - State written or mutated: Writes `.codevovle/branches/<new>.json` and deletes `.codevovle/branches/<old>.json`; updates `.codevovle/state.json` cursor if needed
  - User-visible outputs: Console confirmation of rename
  - Failure modes: StorageError if preconditions fail; file operations may raise exceptions

- Capability name: Jump to branch (switch active branch)
  - How it is invoked: `codevovle branch jump --file <file> <branch>` or `RecordingEngine.jump_to_branch(branch)`
  - Required inputs: `--file`, positional `branch`
  - Optional inputs: none
  - Preconditions: Branch exists
  - What the capability does (observable effects only): Reconstructs file content to branch head and overwrites the working file; updates cursor active branch and tick
  - State read: `.codevovle/snapshots/base.txt`, `.codevovle/diffs/*.diff`, `.codevovle/branches/<branch>.json`, `.codevovle/state.json`
  - State written or mutated: Overwrites target file on disk; updates `.codevovle/state.json` cursor
  - User-visible outputs: Console confirmation and reconstructed tick ID printed
  - Failure modes: Missing branch raises error; reconstruction may be partial if diffs missing; file write errors

**AI Insights (read-only analysis)**
- Capability name: Generate insights from change range
  - How it is invoked: CLI command `codevovle insights --file <file> --from <spec> --to <spec> [--model <model>]` or `InsightsEngine.generate_insights(from_spec,to_spec)`
  - Required inputs: `--file`, `--from` (tick or branch@tick), `--to` (tick or branch@tick)
  - Optional inputs: `--model` (`gemini`, `chatgpt`, `claude`; default `gemini`)
  - Preconditions: `.codevovle` tracking data exists (base snapshot and diffs for requested ticks); API key configured for the chosen model in `.env` or environment
  - What the capability does (observable effects only): Reconstructs two code states, computes unified diff, sends diff/payload to external AI model endpoint, and prints returned analysis to console
  - State read: `.codevovle/snapshots/base.txt`, `.codevovle/diffs/*.diff`, `.codevovle/branches/*.json`, `.env` or environment variables for API keys
  - State written or mutated: none (read-only)
  - User-visible outputs: Console printed analysis, list of key changes and risks returned by the model
  - Failure modes: Missing API key raises InsightsError with guidance; invalid tick specs raise InsightsError; network/API errors raise InsightsError; partial diffs cause reconstruction errors

- Capability name: List available AI models
  - How it is invoked: `InsightsEngine.get_available_models()` (used by handlers before calling insights)
  - Required inputs: none
  - Optional inputs: none
  - Preconditions: None
  - What the capability does (observable effects only): Reads `.env` and environment to list configured models
  - State read: `.env` file and environment variables
  - State written or mutated: none
  - User-visible outputs: None directly (used by CLI to error/print available models)
  - Failure modes: none (returns empty list if no keys)

**Configuration (API keys & .env)**
- Capability name: Configure AI API keys via `.env` or environment variables
  - How it is invoked: Create/modify `.env` file in project root or set environment variables like `GEMINI_API_KEY`, `CHATGPT_API_KEY`, `CLAUDE_API_KEY` (or lowercase keys in `.env` such as `gemini`, `chatgpt`, `claude`)
  - Required inputs: API key value for chosen model
  - Optional inputs: none
  - Preconditions: Project root writable (to write `.env`)
  - What the capability does (observable effects only): Makes API keys discoverable to `EnvManager.get_api_key()`; enables `insights` capability for that model
  - State read: existing `.env` and environment variables
  - State written or mutated: `.env` when user writes it manually (code only reads `.env`)
  - User-visible outputs: None from code; CLI prints errors prompting `.env` usage when keys absent
  - Failure modes: Malformed `.env` lines ignored; missing keys cause insights to fail

**Watcher Framework — Job & Tracing Runtime**
- Capability name: Run Watcher CLI (execute a user script under tracing)
  - How it is invoked: CLI `watcher --user-script <script> [--output <dir>] [--track-threads] [--track-locals] [--track-all] [--track-sql] [--files-scope <path|globs>] [--mutation-depth <FULL|bytes>] [--custom-processor <path>] [--log-level <LEVEL>] [--max-queue-size <n>]` (entrypoint `watcher/cli/main.py`)
  - Required inputs: `--user-script` (path to a `.py` or `.js` script that defines `main()`)
  - Optional inputs: `--output`, `--track-threads`, `--track-locals`, `--track-all`, `--track-sql`, `--files-scope`, `--mutation-depth`, `--custom-processor`, `--log-level`, `--max-queue-size`
  - Preconditions: `--user-script` exists and is `.py` or `.js`; output directory writable; if `--custom-processor` provided it must exist and match language
  - What the capability does (observable effects only): Validates configuration, injects `watch()` into user script, initializes WatcherCore, optionally loads a custom processor, starts C++ core via FFI, executes user `main()` function under tracing, and persists enriched events to output
  - State read: User script file; optional scope config file; custom processor file; environment and filesystem
  - State written or mutated: Writes events to `--output` directory (default `./watcher_output/events.jsonl`), may create output directory; may write temporary runtime state in memory; may patch SQL execution at runtime
  - User-visible outputs: Console logs about init and execution; `events.jsonl` in `--output` containing enriched events; processor debug logs
  - Failure modes: Validation errors (missing script, wrong file extension, incompatible processor) cause CLI to exit with error; runtime exceptions during `main()` cause CLI to return runtime error; missing C++ library or initialization failure raises runtime error

- Capability name: Inject global `watch` API into user scripts (Python)
  - How it is invoked: Automatically by `WatcherCLI` when loading a Python `--user-script` (the loader injects `watch` wrapper into the module namespace)
  - Required inputs: User script executed via Watcher CLI
  - Optional inputs: Call-site kwargs when calling `watch()` (see below)
  - Preconditions: Watcher initialized; `WatcherCore.initialize()` called; user script defines `main()` and calls `watch()` as needed
  - What the capability does (observable effects only): Provides `watch(value, name=..., ...)` function that returns a `WatchProxy` object; registering the watched variable with the C++ core; further mutations to the proxy produce C++ fast-path events
  - State read: Reads in-process Python value and current WatcherCore config (track flags, scope config)
  - State written or mutated: Registers variable with C++ core (via FFI); creates in-memory `ShadowMemory` and `WatchProxy` entries; may cause C++ core to track variable state and emit events
  - User-visible outputs: None directly; later enriched events persist to output and console logs from Watcher
  - Failure modes: Registration can raise RuntimeError if C++ FFI returns an error; value too large for page allocation raises ValueError

- Capability name: `watch()` function call options (Python adapter)
  - How it is invoked: Call from user code: `watch(value, name="var", track_threads=None, track_locals=None, track_sql=None, mutation_depth="FULL", scope=None, file_path=None)`
  - Required inputs: `value` (object to watch)
  - Optional inputs: `name`, `track_threads`, `track_locals`, `track_sql`, `mutation_depth`, `scope`, `file_path`
  - Preconditions: `WatcherCore` initialized and C++ core loaded
  - What the capability does (observable effects only): Allocates shadow memory for value; registers page with C++ core; returns `WatchProxy` that intercepts mutations and updates shadow memory, which can trigger event emission
  - State read: Value content in Python process; WatcherCore runtime flags
  - State written or mutated: In-memory shadow page, registration with C++ core (internal state), subsequent events emitted to the watcher event queue
  - User-visible outputs: None direct; mutations result in events persisted to `events.jsonl`
  - Failure modes: Value too large, missing FFI library, or registration errors raise exceptions

**Watcher Scope Configuration**
- Capability name: Files-scope configuration parser
  - How it is invoked: Pass `--files-scope <path>` to `watcher` CLI pointing at a config file; internally `parse_scope_config(path)` parses file
  - Required inputs: Path to scope configuration file (text file with lines like `src/app.py:(local:counter,global:total)`)
  - Optional inputs: none (format-specific)
  - Preconditions: File exists and readable
  - What the capability does (observable effects only): Produces structured mapping of file paths to variable specifications (name + scope) used by injected `watch()` wrapper to provide `scope` and `file_path` when registering watches
  - State read: The scope configuration text file
  - State written or mutated: none
  - User-visible outputs: CLI logs on successful load; applied scope information affects event attributes persisted
  - Failure modes: Malformed lines raise ValueError and cause validation failure; empty/invalid config yields CLI validation error

**Watcher Custom Processor**
- Capability name: Load and run custom processor(s)
  - How it is invoked: `watcher` CLI with `--custom-processor <path>` or `ProcessorRunner` invoked by the watcher runtime
  - Required inputs: `--custom-processor` path to `.py` or `.js` processor implementing `main(event)`
  - Optional inputs: `timeout_seconds` (internal runner default ~0.1s)
  - Preconditions: Processor file exists and exposes `main(event)` function in the correct language
  - What the capability does (observable effects only): For each enriched event, runs processor(s) (in subprocess), applies actions: `pass`, `drop`, `annotate`, `enrich` per processor response; processor may modify or drop events before persistence
  - State read: Event dictionary passed to processor; processor code reads arbitrary local context in its process
  - State written or mutated: Event dictionary may be annotated/enriched in-memory before being written; no persisted storage by the runner itself
  - User-visible outputs: Modified events written into `events.jsonl`; processor exceptions/timeouts are skipped (silent failure), CLI logs may show errors
  - Failure modes: Processor timeouts or crashes cause that processor invocation to be skipped; invalid JSON responses are ignored; processors longer than timeout are treated as failures and skipped

**Event Persistence & Enrichment (Watcher Phase 2)**
- Capability name: Persist enriched events to JSONL
  - How it is invoked: Internal writer triggered by enrichment pipeline; configured via `--output` when launching `watcher`
  - Required inputs: Enriched event dictionaries produced by pipeline
  - Optional inputs: Buffering and batch parameters (default values in code)
  - Preconditions: Output directory writable
  - What the capability does (observable effects only): Appends one JSON object per line to `events.jsonl`; supports buffering and batch background writer
  - State read: None beyond in-memory event data
  - State written or mutated: Writes `events.jsonl` lines and flushes/archives as configured
  - User-visible outputs: `events.jsonl` file under `--output`; `EventWriter.get_stats()` returns counts
  - Failure modes: Disk write failures increase `events_lost` statistic and drop events from buffer; buffer overflow may drop events; writer prints warnings

**Processor Invocation (subprocess wrappers)**
- Capability name: Run Python/JS processor in isolated subprocess
  - How it is invoked: `ProcessorFactory.create_runner()` used by watcher runtime; `PythonProcessorRunner.invoke(event)` / `JavaScriptProcessorRunner.invoke(event)`
  - Required inputs: `processor_path`, event JSON on stdin
  - Optional inputs: `timeout_seconds` (defaults in code)
  - Preconditions: Interpreter (`python` or `node`) available in PATH; processor file exports `main(event)`
  - What the capability does (observable effects only): Executes processor in subprocess with event JSON on stdin and expects JSON response on stdout; returns structured `ProcessorResponse`
  - State read: Processor file on disk
  - State written or mutated: None persisted by runner
  - User-visible outputs: Processor-annotated event written to `events.jsonl`; timeouts or errors silently result in pass/drop behavior
  - Failure modes: Subprocess timeouts, missing interpreter, invalid JSON responses, or processor errors cause invocation to return None (treated as no-op)

**Page Address Resolution (Clarified)**
- Capability name: Page-address resolution and variable lookup (Python adapter)
  - How it is invoked: Internal mechanism used by `EventBridge._lookup_variable()` to map C++ event page_base to registered variables
  - Technical detail (Python): Creates mmap page with `segment = mmap.mmap(-1, PAGE_SIZE)`; stores `id(mmap_obj)` as page_base in registration; passes this address to C++ FFI via `watcher_register_page(page_base, ...)`; C++ core embeds the page_base in each event as a hex string; EventBridge parses hex string back to integer and looks up in `WatcherCore.variables` dict by iterating through registered (shadow, proxy) tuples and matching `shadow.page_base`
  - Resolution guarantee: Works reliably within a single Python process in CPython because `id()` returns the stable memory address of the mmap object; address remains valid for the lifetime of the mmap allocation
  - Required inputs: N/A for user
  - Optional inputs: N/A
  - Preconditions: N/A
  - What the capability does (observable effects only): Maps event page_base addresses to variable metadata; if lookup fails, events contain `variable_id: "unknown"` and `variable_name: "unknown_var"`
  - State read: In-memory `WatcherCore.variables` registry, JSON page_base from C++ events
  - State written or mutated: none
  - User-visible outputs: Events in `events.jsonl` contain resolved `variable_id` and `variable_name` fields; if lookup failed, those fields contain `"unknown"`
  - Failure modes: (Rare) If C++ core reports invalid/misaligned page_base or if `WatcherCore.variables` is corrupted, lookup returns None and triggers unknown fields; cross-process communication would fail (process-local only)

**JavaScript Support (Fully Implemented)**
- Capability name: JavaScript support in Watcher (runtime adapter and CLI routing)
  - How it is invoked: Two paths: (1) Direct use of `watcher/adapters/javascript/index.js` Node.js module; (2) via `watcher` CLI with `--user-script` or `--custom-processor` pointing to `.js` files
  - User script loading in CLI (.js scripts): FULLY IMPLEMENTED
    - Invocation: `watcher --user-script app.js` when script is JavaScript
    - Status: Properly implemented in `WatcherCLI._load_javascript_script()`
    - Current behavior: Validates script exists and contains `main` function; stores script path for execution; creates Node.js wrapper at runtime that injects `watch` function and executes the script via subprocess
    - Execution: Created temporary wrapper script that requires the user script module and calls `main()` with watch injected into global scope
  - JavaScript processor execution in CLI (.js processors): FULLY WORKING (subprocess execution)
    - Invocation: `watcher --custom-processor processor.js` when processor is JavaScript
    - Status: `ProcessorFactory.create_runner()` creates `JavaScriptProcessorRunner` that spawns `node -e <wrapper>` subprocess
    - Current behavior: For each event, forks subprocess to execute processor; processor must export `main(event)` function returning action response; subject to 100ms timeout per invocation
    - Requires: Node.js available in PATH
  - JavaScript adapter module (native Node.js binding): FULLY IMPLEMENTED
    - File: `watcher/adapters/javascript/index.js` (standalone Node.js module)
    - Exports: `watch(buffer, options)` function (mirrors Python API)
    - Capabilities: Watches TypedArray/ArrayBuffer (not arbitrary JS objects); SQL context monkey-patching (pg, mysql2, sqlite3); thread/locals/SQL tracking flags
    - Limitation: `pageBase` implementation passes ArrayBuffer object reference directly to C++ core (intended to be V8 backing store address; simplified but functional)
    - Direct usage (bypasses CLI): Can be imported directly in Node.js: `const { watch } = require('./watcher/adapters/javascript/index.js')`
  - Required inputs: `.js` file path; Node.js in PATH
  - Optional inputs: none
  - Preconditions: For CLI execution, Node.js required in PATH; for user scripts, `main()` must be exported
  - What the capability does (observable effects only): Routes JavaScript execution to subprocess; injects watch function; executes user code and persists events
  - State read: Script/processor file, environment PATH
  - State written or mutated: Temporary wrapper script created during execution and cleaned up
  - User-visible outputs: Console logs from user script; processed events written to `events.jsonl`; script output printed to console
  - Failure modes: Missing Node.js causes subprocess creation to fail (error message); invalid script syntax causes execution error; processor timeouts (>100ms) skipped; missing `main()` function detected at load time and reported

---

## How to Create and Use a Custom Processor

A **custom processor** filters or enriches events AFTER they're recorded but BEFORE they're written to disk.

### Python Custom Processor

**File: `processor.py`**
```python
def main(event):
    """
    Process an enriched event.
    
    Args:
        event: Dict with fields:
            - event_id, timestamp_ns, variable_name
            - function, file, line, thread_id
            - deltas (list of byte changes)
            - sql_context (optional)
            - scope, annotations (optional)
    
    Returns:
        Dict with action:
        - {"action": "pass"}              # Let event through
        - {"action": "drop"}              # Remove event
        - {"action": "annotate", "annotations": {...}}  # Add metadata
    """
    
    # Example 1: Drop large mutations (noise filtering)
    if len(event['deltas']) > 100:
        return {"action": "drop"}
    
    # Example 2: Annotate SQL-related events
    if event.get('sql_context'):
        return {
            "action": "annotate",
            "annotations": {"db_op": True, "risk": "high"}
        }
    
    # Example 3: Filter by variable name
    if event['variable_name'].startswith('_'):  # Skip private vars
        return {"action": "drop"}
    
    # Default: pass through
    return {"action": "pass"}
```

**Usage:**
```bash
python -m watcher.cli.main \
  --user-script ./app.py \
  --custom-processor ./processor.py \
  --output ./events
```

---

### JavaScript Custom Processor

**File: `processor.js`**
```javascript
function main(event) {
    /**
     * Process an enriched event.
     * 
     * Args:
     *   event: Object with fields:
     *     - event_id, timestamp_ns, variable_name
     *     - function, file, line, thread_id
     *     - deltas (array of byte changes)
     *     - sql_context (optional)
     *   
     * Returns:
     *   Object with action:
     *   - {action: "pass"}                // Let event through
     *   - {action: "drop"}                // Remove event
     *   - {action: "annotate", annotations: {...}}  // Add metadata
     */
    
    // Example 1: Drop small mutations (noise)
    if (event.deltas.length < 3) {
        return { action: "drop" };
    }
    
    // Example 2: Flag high-mutation events
    if (event.deltas.length > 50) {
        return {
            action: "annotate",
            annotations: { severity: "high", review_needed: true }
        };
    }
    
    // Example 3: Track SQL events separately
    if (event.sql_context) {
        return {
            action: "annotate",
            annotations: { category: "database" }
        };
    }
    
    // Default: pass through
    return { action: "pass" };
}

module.exports = { main };
```

**Usage:**
```bash
python -m watcher.cli.main \
  --user-script ./app.js \
  --custom-processor ./processor.js \
  --output ./events
```

---

### Common Processor Patterns

| Pattern | Code | Use Case |
|---------|------|----------|
| **Drop noise** | `if (event.deltas.length < 3) return {action: "drop"}` | Ignore tiny mutations |
| **Flag high-value** | `if (event.deltas.length > 50) return {action: "annotate", annotations: {risk: "high"}}` | Mark important changes |
| **Track by source** | `if (event.function === "main") return {action: "annotate", annotations: {source: "main"}}` | Categorize by location |
| **SQL tracking** | `if (event.sql_context) return {action: "annotate", annotations: {type: "db"}}` | Tag database operations |
| **Private var skip** | `if (event.variable_name.startsWith("_")) return {action: "drop"}` | Hide internal variables |

---

### Running User Script + Processor Together

```bash
# Simple app
cat > app.py << 'EOF'
counter = watch(0, name="counter")
for i in range(100):
    counter = counter + 1
EOF

# Custom processor to filter
cat > filter.py << 'EOF'
def main(event):
    # Only keep events with specific deltas
    if len(event['deltas']) > 5:
        return {"action": "drop"}
    return {"action": "pass"}
EOF

# Run both
python -m watcher.cli.main \
  --user-script ./app.py \
  --custom-processor ./filter.py \
  --output ./events

# View results
cat events/events.jsonl | wc -l  # See how many events passed through
```

---

# Data Storage Formats and Structures

## CodeVovle Storage

All CodeVovle data is stored in the `.codevovle/` directory within the tracked project.

### File Structure
```
.codevovle/
  ├── config.json              # Per-file tracking configuration
  ├── state.json               # Global state and cursor positions
  ├── snapshots/               # Base file snapshots
  │   └── base.txt
  ├── diffs/                   # Individual changesets
  │   ├── 1.diff
  │   ├── 2.diff
  │   └── ...
  └── branches/                # Branch metadata
      ├── main.json
      ├── feature.json
      └── ...
```

**Storage Location:** [CodeVovle/codevovle/storage.py](CodeVovle/codevovle/storage.py) (lines 15-30)

### config.json - Per-File Configuration

**Location:** `.codevovle/config.json`  
**Format:** JSON object mapping file paths to configs  
**Persistence:** [storage.py:ConfigManager](CodeVovle/codevovle/storage.py#L36-L80)

**Data Type:**
```json
{
  "<file_path>": {
    "file_path": "string",        // Path being tracked (str)
    "interval": 0.5,              // Sampling interval in seconds (float)
    "active_branch": "main",      // Current branch name (str)
    "last_tick": 42               // Last recorded tick ID (int or null)
  }
}
```

**Fields Explained:**
| Field | Type | Purpose | Updated |
|-------|------|---------|---------|
| `file_path` | str | File being watched | On config creation |
| `interval` | float | Sampling frequency in seconds | User configurable |
| `active_branch` | str | Current branch context | On branch switch |
| `last_tick` | int\|null | Last recorded mutation tick | Each mutation |

### state.json - Global State and Cursors

**Location:** `.codevovle/state.json`  
**Format:** JSON object with global counter and per-file cursors  
**Persistence:** [storage.py:StateManager](CodeVovle/codevovle/storage.py#L295-L365)

**Data Type:**
```json
{
  "global_tick_counter": 1234,     // Global mutation counter (int)
  "cursor": {
    "<file_path>": {
      "active_branch": "develop",  // (str)
      "current_tick": 789          // (int or null)
    }
  }
}
```

**Fields Explained:**
| Field | Type | Purpose |
|-------|------|---------|
| `global_tick_counter` | int | Incremented for every mutation across all files |
| `cursor.<file_path>.active_branch` | str | Which branch cursor is on |
| `cursor.<file_path>.current_tick` | int\|null | Position in diff chain for each file |

### branch.json - Branch Metadata

**Location:** `.codevovle/branches/<branch_name>.json`  
**Format:** JSON object per branch  
**Persistence:** [storage.py:BranchManager](CodeVovle/codevovle/storage.py#L92-L175)

**Data Type:**
```json
{
  "id": "branch-uuid",                // Unique identifier (str UUID)
  "label": "feature-x",               // Branch display name (str)
  "parent": "main",                   // Parent branch name (str or null)
  "forked_at_tick": 500,              // Tick when forked (int or null)
  "diff_chain": [1, 2, 5, 8, 12],    // Ordered list of diff tick IDs (int[])
  "created_at": "2024-01-15T10:30:00Z",  // ISO timestamp (str)
  "description": "..."                // Optional user notes (str)
}
```

**Fields Explained:**
| Field | Type | Purpose | Line Ref |
|-------|------|---------|----------|
| `id` | str | UUID for branch identity | [storage.py:97](CodeVovle/codevovle/storage.py#L97) |
| `label` | str | User-friendly branch name | [storage.py:98](CodeVovle/codevovle/storage.py#L98) |
| `parent` | str\|null | Parent branch for branching history | [storage.py:99](CodeVovle/codevovle/storage.py#L99) |
| `forked_at_tick` | int\|null | Tick ID where fork occurred | [storage.py:100](CodeVovle/codevovle/storage.py#L100) |
| `diff_chain` | int[] | List of diff file tick IDs in order | [storage.py:101](CodeVovle/codevovle/storage.py#L101) |

### Snapshots - Base File State

**Location:** `.codevovle/snapshots/base.txt`  
**Format:** Plain text file  
**Persistence:** [storage.py:SnapshotManager](CodeVovle/codevovle/storage.py#L178-L220)

**Data Type:**
```
Plain text file content or binary data
```

**Purpose:** Starting point for diff computation; used to reconstruct full file from diffs.

### Diffs - Individual Changesets

**Location:** `.codevovle/diffs/<tick_id>.diff`  
**Format:** Unified diff format (standard `diff -u`)  
**Persistence:** [storage.py:DiffManager](CodeVovle/codevovle/storage.py#L223-L290)

**Data Type:**
```
--- a/.codevovle/snapshots/base.txt
+++ b/.codevovle/diffs/1.diff
@@ -10,5 +10,6 @@
 line 9
-line 10 old
+line 10 new
 line 11
```

**Sample File:** [examples/sample.diff](examples/sample.diff)

---

## Watcher Storage

Watcher records variable mutations as enriched events persisted in JSONL format.

### File Structure
```
<output_dir>/
  └── events.jsonl             # All recorded events, one JSON per line
```

**Storage Location:** [watcher/core/event_writer.py](watcher/core/event_writer.py#L31)

### events.jsonl - Enriched Variable Events

**Location:** `<output_dir>/events.jsonl` (specified via `--output`)  
**Format:** JSON Lines (newline-delimited JSON)  
**Persistence:** [event_writer.py:EventWriter.write_event()](watcher/core/event_writer.py#L54-L75)

**Data Type (One Line Per Event):**
```json
{
  "event_id": "evt-001",            // Unique event identifier (str)
  "timestamp_ns": 1707916400000000000,  // Nanosecond timestamp (int)
  "variable_id": "var_counter",     // Variable identifier (str)
  "variable_name": "counter",       // User variable name (str)
  "function": "main",               // Function where mutation occurred (str)
  "file": "app.py",                 // File path (str)
  "line": 42,                       // Line number in source (int)
  "deltas": [
    {
      "offset": 0,                  // Byte offset in memory (int)
      "before": "0x00",             // Hex value before (str)
      "after": "0x01"               // Hex value after (str)
    },
    {
      "offset": 1,
      "before": "0x00",
      "after": "0x00"
    }
  ],
  "thread_id": 1001,                // OS thread ID (int or null)
  "sql_context": {                  // Database operation context (dict or null)
    "operation": "INSERT",
    "table": "users",
    "query_hash": "0x1a2b3c"
  },
  "scope": "local"                  // Variable scope: "local", "global", "both" (str or null)
}
```

**Fields Explained:**

| Field | Type | Purpose | Source | Line Ref |
|-------|------|---------|--------|----------|
| `event_id` | str | Unique event identifier from C++ core | WatcherCore | [event_enricher.py:20](watcher/core/event_enricher.py#L20) |
| `timestamp_ns` | int | Nanosecond-precision timestamp when mutation occurred | WatcherCore | [event_enricher.py:21](watcher/core/event_enricher.py#L21) |
| `variable_id` | str | Variable identifier from C++ core | WatcherCore | [event_enricher.py:22](watcher/core/event_enricher.py#L22) |
| `variable_name` | str | Human-readable variable name (from phase 2 enrichment) | Phase 2 Enricher | [event_enricher.py:23](watcher/core/event_enricher.py#L23) |
| `function` | str | Function name where mutation occurred (symbol resolution) | Phase 2 Enricher | [event_enricher.py:26](watcher/core/event_enricher.py#L26) |
| `file` | str | Source file path | Phase 2 Enricher | [event_enricher.py:27](watcher/core/event_enricher.py#L27) |
| `line` | int | Line number in source file | Phase 2 Enricher | [event_enricher.py:28](watcher/core/event_enricher.py#L28) |
| `deltas` | dict[] | Byte-level changes (offset, before, after) | DeltaComputer | [event_enricher.py:30](watcher/core/event_enricher.py#L30) |
| `thread_id` | int\|null | OS thread ID where mutation occurred | Phase 2 Enricher | [event_enricher.py:33](watcher/core/event_enricher.py#L33) |
| `sql_context` | dict\|null | SQL operation details if applicable | Phase 2 Enricher | [event_enricher.py:34](watcher/core/event_enricher.py#L34) |
| `scope` | str\|null | Variable scope classification | Phase 2 Enricher | [event_enricher.py:36](watcher/core/event_enricher.py#L36) |

### Delta Structure - Byte-Level Changes

Each event contains a `deltas` array with byte-level mutations:

**Data Type (Per Delta):**
```json
{
  "offset": 0,          // Byte position in variable's memory (int)
  "before": "0x00",     // Previous byte value in hex (str)
  "after": "0xff"       // New byte value in hex (str)
}
```

**Compute Function:** [event_enricher.py:DeltaComputer.compute_deltas()](watcher/core/event_enricher.py#L61-L91) (lines 61-91)

### Reading events.jsonl

**Python:**
```python
import json

with open('events.jsonl') as f:
    for line in f:
        event = json.loads(line)
        print(f"Var: {event['variable_name']}, Deltas: {len(event['deltas'])}")
```

**Bash:**
```bash
# Count total events
wc -l events.jsonl

# Pretty-print first event
head -1 events.jsonl | python -m json.tool

# Filter events by variable name
jq 'select(.variable_name == "counter")' events.jsonl
```

---

## Data Flow Summary

**CodeVovle Pipeline:**
1. User runs `codevovle record --file app.py --interval 0.5`
2. File content sampled every 0.5s
3. Diffs computed and stored in `.codevovle/diffs/<tick>.diff`
4. Branch metadata updated in `.codevovle/branches/<active>.json`
5. Global state updated in `.codevovle/state.json`
6. Cursor position saved for resumption

**Watcher Pipeline:**
1. User script calls `watch(buffer, name="var")`
2. C++ core intercepts page faults (if userfaultfd enabled)
3. Event emitted with `event_id`, `timestamp_ns`, byte snapshots
4. Phase 2 enricher resolves symbols (function, file, line)
5. Byte deltas computed
6. Enriched event written to `events.jsonl` (one JSON per line)
7. Processor (if specified) filters/annotates event before write

---

# End of file
