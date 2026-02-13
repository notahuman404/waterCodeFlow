# WaterCodeFlow VS Code Extension - Complete User Guide

## 🚀 Quick Setup (5 Minutes)

### Step 1: Run the Automated Setup Script

```bash
cd /path/to/extension
chmod +x AUTOMATED_SETUP.sh
./AUTOMATED_SETUP.sh
```

This script does **everything automatically**:
- ✅ Checks and installs system dependencies (Python, Node.js, CMake, C++)
- ✅ Fixes all hardcoded paths in the code
- ✅ Builds C++ components
- ✅ Installs Python packages (pytest, psutil)
- ✅ Installs Node.js packages
- ✅ Compiles TypeScript
- ✅ Packages the extension as `.vsix` file

**Expected time:** 5-10 minutes depending on your system

### Step 2: Install in VS Code

After the script completes, you'll have a `.vsix` file. Install it using either:

**Method 1 - VS Code UI:**
1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X / Cmd+Shift+X)
3. Click '...' menu → 'Install from VSIX...'
4. Select the `watercodeflow-0.1.0.vsix` file

**Method 2 - Command Line:**
```bash
code --install-extension watercodeflow-0.1.0.vsix
```

### Step 3: Verify Installation

1. Open a Python file in VS Code
2. Look for the **WaterCodeFlow** icon in the Activity Bar (left sidebar)
3. Click it to see three panels: Recordings, Variables, and Branches

---

## 📖 What is WaterCodeFlow?

WaterCodeFlow is a **time-travel debugger** for Python that lets you:
- 🕐 **Record execution** - Capture every state change as your code runs
- ⏪ **Travel through time** - Jump to any point in your program's execution
- 🔍 **Inspect variables** - See how values change over time
- 🌿 **Branch execution** - Create alternate timelines to test different approaches
- 🤖 **Get AI insights** - Receive automated analysis of your code behavior

Think of it as **DVR for your code** - record it, rewind it, replay it, and understand exactly what happened.

---

## 🎮 Basic Usage

### Starting a Recording

1. **Open a Python file** in VS Code
2. **Click the WaterCodeFlow icon** in the Activity Bar (left sidebar)
3. **In the Recordings panel**, click "Start Recording"
4. **Enter recording interval** (e.g., `0.5` for half-second snapshots)
5. **Run your Python script** as you normally would
6. Watch as execution snapshots (called "ticks") appear in the panel

**Recording Interval Guide:**
- `0.1` - Very detailed (10 snapshots/second) - for fine-grained debugging
- `0.5` - Balanced (2 snapshots/second) - recommended for most use cases
- `1.0` - Coarse (1 snapshot/second) - for long-running processes

### Stopping a Recording

- Click **"Stop Recording"** in the Recordings panel, or
- Use Command Palette (Ctrl+Shift+P / Cmd+Shift+P) → "WaterCodeFlow: Stop Recording"

### Viewing Your Timeline

Once recording is stopped, the Recordings panel shows:
- **All ticks** (execution snapshots) in chronological order
- **Timestamp** for each tick
- **Variable states** at that point in time
- **Call stack** information

**Click on any tick** to jump to that exact moment in execution!

---

## 🔍 Advanced Features

### 1. Variable Inspection

**View All Variables:**
1. Click the **Variables panel** in WaterCodeFlow
2. See a list of all tracked variables in your code
3. Each variable shows its current value and type

**Deep Dive into a Variable:**
1. Click on any variable in the Variables panel
2. Click **"Open Inspector"**
3. See a detailed timeline showing:
   - How the value changed over time
   - When it was modified
   - What values it held at each tick
   - Visual graph of changes (for numbers)

**Perfect for:**
- Understanding why a variable has an unexpected value
- Seeing when and how state changes occur
- Tracking down the source of bugs

### 2. Execution Branching

Branching lets you create alternate timelines of your code execution. This is incredibly powerful for:
- Testing "what if" scenarios
- Comparing different approaches
- A/B testing code changes

**How to Create a Branch:**
1. In the Recordings panel, **click on any tick** (the moment you want to branch from)
2. **Right-click** → "Create Branch from Here"
3. **Name your branch** (e.g., "optimized_version", "bug_fix_attempt")
4. **Make code changes** and run again
5. **Switch between branches** to compare results

**Example Use Case:**
```
Main branch: Original algorithm (runs in 5 seconds)
Branch "optimized": Tried a dictionary instead of list (runs in 2 seconds)
Branch "alternate": Different approach entirely (runs in 1 second)

→ Compare all three to see which is best!
```

### 3. AI-Powered Insights

Get automated analysis of your code's behavior:

**Generate Insights:**
1. In the Recordings panel, **select a range of ticks** (click and drag)
2. **Right-click** → "View Insights"
3. Wait a moment while AI analyzes the execution
4. See insights like:
   - Performance bottlenecks
   - Unusual patterns
   - Potential bugs
   - Optimization suggestions

**Or use Command Palette:**
- Ctrl+Shift+P / Cmd+Shift+P → "WaterCodeFlow: View Insights"

---

## 🎯 Real-World Usage Scenarios

### Scenario 1: Debugging a Complex Algorithm

```python
def process_data(items):
    result = []
    for item in items:
        if item > 10:
            result.append(item * 2)
        else:
            result.append(item / 2)
    return result
```

**Problem:** Getting wrong output for some inputs

**How WaterCodeFlow Helps:**
1. Start recording
2. Run the function with problematic input
3. Jump through the execution tick by tick
4. Inspect `item` variable at each iteration
5. See exactly when the wrong calculation happens
6. Identify the bug (maybe it's the condition, maybe it's the calculation)

### Scenario 2: Optimizing Performance

```python
def find_duplicates(data):
    duplicates = []
    for i, item in enumerate(data):
        for j, other in enumerate(data):
            if i != j and item == other:
                duplicates.append(item)
    return duplicates
```

**Problem:** Code is too slow

**How WaterCodeFlow Helps:**
1. Record execution with sample data
2. View AI insights
3. See that the nested loop is causing O(n²) performance
4. Create a branch called "optimized"
5. Change to using a set for O(n) lookup
6. Compare execution time between branches
7. Choose the faster implementation

### Scenario 3: Understanding Legacy Code

**Problem:** Inherited code you don't understand

**How WaterCodeFlow Helps:**
1. Record a typical execution
2. Watch the flow of data through the system
3. Inspect key variables at decision points
4. See which branches of if/else statements are taken
5. Build mental model of how the code actually works
6. Document your findings using branch names and notes

---

## 🛠️ Configuration & Settings

### VS Code Settings

Access settings through: File → Preferences → Settings → Search "watercodeflow"

**Available Settings:**

```json
{
  "watercodeflow.defaultInterval": 0.5,
  "watercodeflow.maxRecordings": 1000,
  "watercodeflow.storagePath": ".codevovle",
  "watercodeflow.debugLogging": false,
  "watercodeflow.autoCleanOldRecordings": true
}
```

**Settings Explained:**

- `defaultInterval` - Default recording interval (seconds)
- `maxRecordings` - Maximum ticks to keep (older ones auto-deleted)
- `storagePath` - Where recordings are stored (relative to workspace)
- `debugLogging` - Enable verbose logging for troubleshooting
- `autoCleanOldRecordings` - Automatically clean old recordings

### Recording Storage

Recordings are stored in `.codevovle/` directory in your workspace:
```
your-project/
├── .codevovle/
│   ├── branches/        # Branch metadata
│   ├── diffs/          # Execution diffs
│   ├── snapshots/      # State snapshots
│   └── state.json      # Global state
├── your_code.py
└── ...
```

**Storage Tips:**
- Add `.codevovle/` to `.gitignore` (recordings are large)
- Clean old recordings periodically
- Recordings from different files are kept separate

---

## 🎨 User Interface Guide

### Activity Bar Icon

The **WaterCodeFlow icon** appears in the Activity Bar (left sidebar) and provides access to all features.

### Recordings Panel

Shows all execution snapshots:
- **Tick ID** - Unique identifier for each snapshot
- **Timestamp** - When it was recorded
- **Branch** - Which branch this tick belongs to
- **Status** - Current state (recording, stopped, etc.)

**Actions:**
- **Click a tick** - Jump to that moment
- **Right-click** - Context menu with options
- **Drag to select** - Select range for insights

### Variables Panel

Displays tracked variables:
- **Variable name**
- **Current value**
- **Type information**
- **Last modified** indicator

**Actions:**
- **Click variable** - See details
- **"Open Inspector"** - Deep dive into history
- **"Track Changes"** - Monitor this variable

### Branches Panel

Shows all execution branches:
- **Branch name**
- **Creation time**
- **Tick count**
- **Active** indicator

**Actions:**
- **Click branch** - Switch to that branch
- **Right-click** - Rename or delete
- **"Compare"** - Compare two branches

---

## 🔧 Troubleshooting

### Extension Not Appearing

**Problem:** WaterCodeFlow icon not in Activity Bar

**Solutions:**
1. Make sure you opened a Python file (.py)
2. Check that extension is enabled: Extensions → search "watercodeflow"
3. Reload VS Code: Ctrl+Shift+P / Cmd+Shift+P → "Developer: Reload Window"
4. Check Output panel: View → Output → select "WaterCodeFlow"

### Recording Not Starting

**Problem:** Click "Start Recording" but nothing happens

**Solutions:**
1. Check that Python 3 is installed: `python3 --version`
2. Ensure Python is in your PATH
3. Check Output panel for errors
4. Try restarting VS Code
5. Verify `.codevovle/` directory can be created in workspace

### No Ticks Appearing

**Problem:** Recording started but no ticks show up

**Solutions:**
1. **Run your Python script** - recording doesn't start automatically
2. Check recording interval isn't too long
3. Verify script is actually executing
4. Check disk space (recordings need space)
5. Look for errors in Output panel

### C++ Libraries Not Found

**Problem:** "libwatcher_python.so not found" error

**Solutions:**
1. Rerun the setup script: `./AUTOMATED_SETUP.sh`
2. Check that `build/` directory exists
3. Verify libraries were compiled: `ls -la build/*.so`
4. On Linux, set LD_LIBRARY_PATH:
   ```bash
   export LD_LIBRARY_PATH=/path/to/extension/build:$LD_LIBRARY_PATH
   ```
5. On Mac, set DYLD_LIBRARY_PATH:
   ```bash
   export DYLD_LIBRARY_PATH=/path/to/extension/build:$DYLD_LIBRARY_PATH
   ```

### Performance Issues

**Problem:** VS Code becomes slow when recording

**Solutions:**
1. Increase recording interval (use 1.0 instead of 0.1)
2. Reduce `maxRecordings` setting
3. Stop recording when not actively debugging
4. Clean old recordings: delete `.codevovle/` directory
5. Close other heavy extensions temporarily

### Permission Errors

**Problem:** Cannot write to `.codevovle/` directory

**Solutions:**
1. Check workspace folder permissions
2. Ensure you have write access to project directory
3. Try running VS Code as administrator (last resort)
4. Change `storagePath` setting to a different location

---

## 💡 Tips & Best Practices

### Recording Strategy

**Do:**
- ✅ Use shorter intervals (0.1-0.5s) for active debugging
- ✅ Use longer intervals (1-2s) for monitoring/profiling
- ✅ Stop recording when done to save resources
- ✅ Create branches before major refactoring
- ✅ Use descriptive branch names

**Don't:**
- ❌ Leave recording running indefinitely
- ❌ Use very short intervals (0.01s) for long processes
- ❌ Keep thousands of old recordings
- ❌ Record sensitive data (remember it's saved to disk)

### Effective Branching

1. **Create branches at decision points** - right before trying something new
2. **Name branches descriptively** - "optimize_loop", "fix_bug_42", "refactor_parser"
3. **Compare branches** - use insights to compare performance/behavior
4. **Keep useful branches** - delete failed experiments
5. **Document in commits** - "Based on WaterCodeFlow branch 'optimized_version'"

### Variable Inspection

1. **Track key variables** - focus on the ones that matter
2. **Use the timeline** - see how values evolve
3. **Look for patterns** - unexpected changes often indicate bugs
4. **Check types** - type mismatches are common issues
5. **Watch for None** - null/None values are frequent bug sources

### AI Insights Usage

1. **Use on specific ranges** - select relevant portions of execution
2. **Look for patterns** - insights highlight repeated issues
3. **Act on suggestions** - the AI can spot things you miss
4. **Compare branches** - insights can compare different approaches
5. **Save useful insights** - copy important findings to documentation

---

## 📊 Understanding the Data

### What Gets Recorded

For each tick (snapshot), WaterCodeFlow captures:
- **Variable values** - All local and global variables
- **Call stack** - Function call hierarchy
- **Line number** - Current execution position
- **Timestamp** - When this happened
- **Memory state** - Selected memory regions (for C++ components)

### Storage Size

Typical storage per tick:
- Simple script: ~1-5 KB per tick
- Complex application: ~10-50 KB per tick
- With many variables: ~50-200 KB per tick

**Example:** Recording 100 ticks with moderate complexity = ~1-5 MB

### Privacy & Security

⚠️ **Important:** Recordings contain your code's runtime data!

- All variable values are stored in plain text
- This includes strings, numbers, objects, etc.
- Do NOT record sensitive data (passwords, API keys, personal info)
- Add `.codevovle/` to `.gitignore`
- Recordings stay on your local machine (not sent anywhere)

---

## 🚀 Advanced Tips for Power Users

### Keyboard Shortcuts

Create custom shortcuts for common actions:
1. File → Preferences → Keyboard Shortcuts
2. Search for "watercodeflow"
3. Assign your preferred keys

**Suggested shortcuts:**
- Start Recording: `Ctrl+Alt+R`
- Stop Recording: `Ctrl+Alt+S`
- Jump to Next Tick: `Ctrl+Alt+Right`
- Jump to Previous Tick: `Ctrl+Alt+Left`

### Integration with Git

Track which branch was used for each commit:
```bash
# Create descriptive branch names based on WaterCodeFlow findings
git checkout -b optimization-from-wcf-analysis

# Reference in commits
git commit -m "Optimize loop based on WaterCodeFlow branch 'perf_test'"
```

### Continuous Integration

Use WaterCodeFlow recordings for debugging CI failures:
1. Record execution during CI run
2. Save `.codevovle/` as artifact
3. Download locally to debug
4. See exactly what happened in CI environment

### Team Collaboration

Share findings with your team:
1. Record problematic execution
2. Export branch metadata
3. Share with team: "Check WaterCodeFlow branch 'bug_reproduction'"
4. Team members can see the same execution flow

---

## 🆘 Getting Help

### Debug Mode

Enable verbose logging to diagnose issues:
1. Settings → search "watercodeflow.debugLogging"
2. Set to `true`
3. Reload VS Code
4. Check Output panel for detailed logs

### Log Files

Logs are saved in:
- Setup log: `extension/setup.log`
- Runtime logs: Output panel (View → Output → WaterCodeFlow)

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "Glue adapter failed to start" | Python subprocess error | Check Python installation |
| "Cannot find module 'glue'" | Python path issue | Rerun setup script |
| "libwatcher_python.so not found" | C++ library missing | Rebuild with setup script |
| "Permission denied" | Can't write to disk | Check folder permissions |
| "Out of memory" | Too many recordings | Clean old recordings |

### Support Resources

1. **Check documentation** in the extension directory
2. **Review setup logs** in `setup.log`
3. **Enable debug logging** for detailed error info
4. **Rerun setup script** to fix installation issues

---

## 📚 Reference

### File Structure

```
extension/
├── AUTOMATED_SETUP.sh          # Main setup script (run this first!)
├── HOW_TO_USE_EXTENSION.md     # This file
├── HARDCODED_PATHS_TO_FIX.md  # Technical path fixes reference
├── QUICK_START.md              # Quick 5-minute guide
├── package.json                # VS Code extension manifest
├── src/                        # TypeScript source code
├── glue/                       # Python bridge layer
├── codevovle/                  # Core debugger engine
├── build/                      # Compiled C++ libraries
└── .codevovle/                 # Recording storage (in workspace)
```

### Command Reference

| Command | Description |
|---------|-------------|
| `./AUTOMATED_SETUP.sh` | Complete automated setup |
| `npm run esbuild` | Rebuild TypeScript |
| `vsce package` | Repackage extension |
| `code --install-extension *.vsix` | Install from command line |

### API for Advanced Users

The glue layer provides a Python API:
```python
from glue import api

# Start recording
api.start_recording("my_script.py", interval=0.5)

# Get status
status = api.get_status("my_script.py")

# List recordings
recordings = api.list_recordings("my_script.py")

# Stop recording
api.stop_recording("my_script.py")
```

---

## 🎓 Learning Path

### Beginner (Day 1)

1. ✅ Install extension using setup script
2. ✅ Start your first recording
3. ✅ Jump between ticks
4. ✅ Inspect a variable

### Intermediate (Week 1)

1. ✅ Create your first branch
2. ✅ Compare two different approaches
3. ✅ Use variable inspector timeline
4. ✅ Generate AI insights

### Advanced (Month 1)

1. ✅ Integrate into daily debugging workflow
2. ✅ Use for performance optimization
3. ✅ Create complex branching strategies
4. ✅ Share findings with team

---

## 🏆 Success Stories

### Example 1: Finding a Subtle Bug
"I had a bug that only appeared after 10,000 iterations. WaterCodeFlow let me record the execution and jump to the exact moment it failed. Saved me hours of adding print statements!"

### Example 2: Optimizing an Algorithm
"Used branching to test 3 different algorithms. WaterCodeFlow made it easy to compare their performance side-by-side. Found a 10x speedup!"

### Example 3: Understanding Legacy Code
"Inherited a complex codebase. WaterCodeFlow helped me understand the flow by watching variables change in real-time. Now I can maintain it confidently."

---

## 🔮 What's Next?

After mastering the basics:

1. **Explore advanced features** - Try all the panels and options
2. **Customize keyboard shortcuts** - Speed up your workflow  
3. **Integrate into your process** - Make time-travel debugging a habit
4. **Share with your team** - Help others debug faster
5. **Provide feedback** - Help improve the extension

---

## 📝 Conclusion

WaterCodeFlow transforms debugging from guesswork into precise investigation. By recording and replaying execution, you can:

- 🎯 **Find bugs faster** - See exactly where things go wrong
- ⚡ **Optimize code** - Compare different approaches empirically
- 🧠 **Understand better** - Watch your code execute step by step
- 🤝 **Collaborate easier** - Share execution timelines with team

**Remember:** The best debugger is the one you actually use. Start simple, experiment often, and soon time-travel debugging will feel natural!

---

**Version:** 0.1.0  
**Last Updated:** February 2025  
**Setup Time:** ~5-10 minutes  
**Learning Curve:** Beginner-friendly with advanced features

**Happy debugging! 🐛🔍✨**