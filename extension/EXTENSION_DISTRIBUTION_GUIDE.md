# WaterCodeFlow - Extension Distribution & Usage

## Overview

WaterCodeFlow is a complete **VS Code extension package** contained in the `editor/` subdirectory. This document explains how to install, configure, and use the extension when the entire project is exported/distributed as an extension.

---

## Project Structure (Root Level)

```
WaterCodeFlow/              [Project Root - Exported as Extension]
├── editor/                 [Extension Code - Main deliverable]
│   ├── src/                [TypeScript source files]
│   ├── media/              [Webview assets]
│   ├── out/                [Compiled extension.js]
│   ├── package.json        [Extension manifest]
│   ├── tsconfig.json       [Build config]
│   └── README.md           [Developer guide]
│
├── glue/                   [Integration layer - Python]
│   ├── adapter.py          [JSON bridge for extension]
│   ├── api.py              [Glue API implementation]
│   ├── variables.py        [Variable tracking]
│   ├── runs.py             [Run grouping]
│   └── ...                 [Other glue modules]
│
├── CodeVovle/              [Core recording engine - Python]
│   ├── codevovle/          [Engine implementation]
│   ├── tests/              [Engine tests]
│   └── ...
│
├── EXTENSION_USAGE.md      [User guide for end users]
├── INTEGRATION_VERIFICATION_REPORT.md  [Build verification report]
├── .codevovle/             [Runtime storage - created on first use]
├── .gitignore
├── README.md               [Main project README]
└── ...                     [Other project files]
```

---

## Installation Methods

### Method 1: Install from VS Code Extensions Marketplace (Future)

When published to the VS Code Marketplace:

1. Open VS Code
2. Go to **Extensions** (Ctrl+Shift+X)
3. Search for "WaterCodeFlow"
4. Click **Install**
5. Reload VS Code
6. Done! Extension is ready to use

### Method 2: Install from .vsix File

If distributed as a `.vsix` package:

1. Obtain the `.vsix` file
2. In VS Code: **Extensions → ... → Install from VSIX**
3. Select the file
4. Reload VS Code

### Method 3: Clone & Build from Source

If installing from the GitHub repository:

```bash
# Clone the repository
git clone https://github.com/specifiedone/WaterCodeFlow.git
cd WaterCodeFlow

# Install extension dependencies
cd editor
npm install

# Build the extension
npm run esbuild

# Now open the root folder in VS Code
cd ..
code .

# Press F5 to launch extension in debug mode
# Or install locally:
code --install-extension ./editor --force
```

### Method 4: Manual Installation

Copy to VS Code extensions folder:

**Windows**:
```powershell
Copy-Item .\editor -Destination "$env:USERPROFILE\.vscode\extensions\watercodeflow-0.1.0"
```

**macOS/Linux**:
```bash
cp -r editor ~/.vscode/extensions/watercodeflow-0.1.0
```

Then reload VS Code.

---

## Configuration & Setup

### Prerequisites

1. **VS Code 1.85.0+**
   - Install from https://code.visualstudio.com/

2. **Python 3.8+**
   ```bash
   # Verify Python
   python3 --version
   
   # Should show: Python 3.x.x or higher
   ```

3. **Ensure Python is in PATH**
   - Windows: Check Environment Variables
   - macOS/Linux: `which python3` should return a path

### First Run Setup

1. **Open any Python file** in a workspace
   - VS Code activates the extension
   - WaterCodeFlow icon appears in activity bar

2. **Grant workspace permissions** (if prompted)
   - VS Code may ask to trust the workspace
   - Click "Trust"

3. **Verify extension started**
   - Open **Output** panel (Ctrl+Shift+U)
   - Select "WaterCodeFlow" from dropdown
   - Should see: `[WaterCodeFlow] Activating...`
   - Should see: `[WaterCodeFlow] Glue client initialized`

### Optional Configuration

Extension stores records in `.codevovle/` at the project root:

```
.codevovle/
├── state.json               [Current state]
├── config.json              [Recording config]
├── diffs/                   [Tick diffs]
├── branches/                [Branch metadata]
└── snapshots/               [Full file snapshots]
```

To customize storage location, edit `.codevovle/config.json` after first recording.

---

## Basic Usage (End-User Perspective)

### 1. Open a Python Project
```bash
# Example project
mkdir my_project
cd my_project
code .
```

### 2. Create a Python File
```python
# example.py
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(5)
print(f"Result: {result}")
```

### 3. Start Recording

**Via UI**:
- Open `example.py`
- Look for **WaterCodeFlow** in left sidebar
- In **Recordings** panel, click **"Start Recording"**
- Enter interval: `0.5` (seconds)
- Click OK

**Status changes to**: `Recording (PID: 12345)`

### 4. Edit & Save the File

Make changes and save:
```python
# Modified fibonacci function
def fibonacci(n):
    if n <= 1:
        return n
    # Optimized: add memoization
    cache = {}
    def fib_memo(x):
        if x in cache:
            return cache[x]
        result = fibonacci(x-1) + fibonacci(x-2)
        cache[x] = result
        return result
    return fib_memo(n)
```

**Recordings list updates** every 2 seconds with new runs.

### 5. Stop Recording

Click **"Stop Recording"** in the Recordings panel.

**Status changes to**: `Ready`

### 6. Inspect Changes

**See all recordings**:
- Recordings panel shows list of runs
- Each run shows: tick range, count, estimated duration

**Jump to a specific point**:
- Click a run in the list
- Editor displays the file at that point in time
- Cursor position updates

**Inspect a variable**:
1. Go to **Variables** panel
2. Click **"Infer Variables"**
3. Click any variable (e.g., `result`)
4. **Inspector** panel opens
5. Shows timeline of that variable's mutations
6. Click any entry to jump editor to that line

### 7. View Insights (Optional)

If recording 2+ ticks:
1. Two or more runs should exist
2. Right-click a run
3. **Insights** panel opens
4. Shows AI-generated summary of changes
5. Click affected lines to highlight them

---

## Troubleshooting

### Issue: "Extension failed to start glue adapter"

**Cause**: Python not found or glue package missing

**Solution**:
```bash
# Check Python
which python3
python3 --version

# Verify glue package
python3 -c "from glue import list_daemon_processes; print('OK')"

# If glue not installed:
cd /path/to/WaterCodeFlow
pip install -e .
```

### Issue: "WaterCodeFlow panel not appearing"

**Cause**: Extension didn't activate

**Solution**:
1. Open a `.py` file (activates on Python file open)
2. Check **Output** panel (Ctrl+Shift+U) for errors
3. If not there, check extension is installed:
   ```
   VS Code → Extensions → search "WaterCodeFlow"
   Should show as installed
   ```

### Issue: "No recordings shown"

**Cause**: Recording didn't start or file not being tracked

**Solution**:
1. Ensure file is saved
2. Try starting recording again with default interval (0.5)
3. Make change to file and save
4. Wait 2 seconds for list to refresh
5. Check `.codevovle/` folder was created

### Issue: "Inspector shows 'No timeline data'"

**Cause**: Variable not used in recorded file

**Solution**:
1. Ensure variable is actually used in the file
2. Record a new session with variable visible
3. Check variable name spelling

### Issue: "Python module not found" error

**Cause**: Module path or environment issue

**Solution**:
```bash
# Verify Python environment
python3 -m site

# If using virtual environment, activate it:
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Then open VS Code from that environment
code .
```

---

## Common Workflows

### Workflow A: Debug a Function

1. Create a test file calling your function
2. Start recording
3. Run the test
4. Stop recording
5. In **Variables**, infer variables
6. Click the output variable
7. Review timeline to see how it changed line-by-line
8. Use this to find logic errors

### Workflow B: Compare Multiple Implementations

1. Record implementation #1
2. Modify code to implementation #2
3. Record again
4. Click each recording to see different code versions
5. Use **Insights** (if available) to see what changed

### Workflow C: Understand a Complex Algorithm

1. Record execution
2. In **Variables**, track important variables (array, accumulator, etc.)
3. Step through timeline
4. Watch how variables change at each iteration
5. Gain intuition for the algorithm

---

## Uninstallation

### From VS Code UI
1. Go to **Extensions** (Ctrl+Shift+X)
2. Search "WaterCodeFlow"
3. Click the gear icon → **Uninstall**
4. Reload

### Manual Removal
```bash
# Remove extension
rm -rf ~/.vscode/extensions/watercodeflow-*

# Remove stored recordings (optional)
rm -rf /path/to/project/.codevovle/
```

---

## Advanced: Configuration Files

### .codevovle/config.json
Controls recording behavior. Example:

```json
{
  "default_interval": 0.5,
  "storage_path": ".codevovle",
  "max_snapshots": 100,
  "enable_tensor_tracking": true
}
```

Edit this to customize recording parameters.

### .vscode/settings.json
Extension-specific settings (future versions):

```json
{
  "watercodeflow.recordingInterval": 0.5,
  "watercodeflow.autoStartOnFileOpen": false,
  "watercodeflow.showInsightsAutomatically": true
}
```

---

## Advanced: Command-Line Usage of Glue

If you want to use the glue API directly (programmatically):

```python
from glue import list_recordings, jump_to_tick, get_variable_timeline
from glue.runs import get_runs

# List recorded runs
runs = get_runs("/path/to/file.py")
for run in runs:
    print(f"Run {run['run_id']}: {run['tick_count']} ticks")

# Get variable timeline
timeline = get_variable_timeline("/path/to/file.py", "my_var", max_ticks=200)
for entry in timeline:
    print(f"Line {entry['line_no']}: {entry['snippet']}")

# Jump to tick
jump_to_tick("/path/to/file.py", tick_id=42)
```

See `EXTENSION_USAGE.md` for more details.

---

## System Requirements Summary

| Component | Requirement | Status |
|-----------|-------------|--------|
| VS Code | 1.85.0+ | ✅ |
| Python | 3.8+ | ✅ |
| Node.js | Required only for building | ✅ |
| RAM | 100MB+ recommended | ✅ |
| Disk | 500MB–1GB for large recordings | ✅ |
| OS | Windows, macOS, Linux | ✅ |

---

## Getting Help

### Documentation
- **EXTENSION_USAGE.md**: Comprehensive user guide
- **editor/README.md**: Developer & architecture guide
- **INTEGRATION_VERIFICATION_REPORT.md**: Build & test report

### Debugging
1. Open **Output** panel: Ctrl+Shift+U
2. Filter: "WaterCodeFlow"
3. Look for `[WaterCodeFlow]` prefixed messages

### Reporting Issues
Include in bug report:
- VS Code version (Help → About)
- Python version (`python3 --version`)
- WaterCodeFlow version (Extensions details)
- Steps to reproduce
- Output panel log (if applicable)

---

## What's Next?

After installing and using WaterCodeFlow:

1. **Explore Features**:
   - Record different files
   - Compare multiple runs
   - Use Inspector on complex variables

2. **Integrate into Workflow**:
   - Use during debugging
   - Use when learning algorithms
   - Use when code reviewing

3. **Provide Feedback**:
   - What features would help most?
   - Any bugs or issues?
   - Performance concerns?

4. **Contribute** (if open source):
   - Suggest improvements
   - Submit pull requests
   - Improve documentation

---

## Version Information

- **Extension Version**: 0.1.0 (Beta)
- **API Version**: glue 0.1.0
- **Engine Version**: CodeVovle 0.1.0
- **Release Date**: February 2026
- **Status**: Beta - Ready for testing

---

## License & Attribution

[Your license info here]

---

**Last Updated**: February 12, 2026  
**Extension Root**: WaterCodeFlow/editor/  
**Project Root**: WaterCodeFlow/
