# WaterCodeFlow VS Code Extension (editor/)

This directory contains the VS Code extension code for the WaterCodeFlow time-travel debugger.

## Directory Structure

```
editor/
├── src/
│   ├── extension.ts                  # Entry point: activate() & deactivate()
│   ├── glueClient.ts                 # Python subprocess bridge (JSON RPC)
│   ├── types.ts                      # TypeScript interfaces
│   ├── providers/
│   │   ├── RecordingsViewProvider.ts # Sidebar: recordings list & controls
│   │   └── VariablesViewProvider.ts  # Sidebar: variable tracking
│   └── panels/
│       ├── VariableInspectionPanel.ts # Modal: variable timeline inspector
│       └── InsightsPanel.ts          # Modal: AI-powered change analysis
│
├── media/
│   ├── recordings.html/js/css        # Recordings webview
│   ├── variables.html/js/css         # Variables webview
│   ├── inspector.html/js/css         # Inspector modal webview
│   └── insights.html/js/css          # Insights modal webview
│
├── out/                              # Compiled JavaScript (auto-generated)
│   └── extension.js                  # Bundled extension entry point
│
├── package.json                      # Extension manifest & dependencies
├── tsconfig.json                     # TypeScript compiler config
└── README.md                         # This file
```

## Development Setup

### Prerequisites
- **Node.js 20+** and **npm**
- **TypeScript 5.3+**
- **VS Code 1.85+** (for testing)
- **Python 3.8+** (glue backend, at project root)

### Installation

```bash
cd editor
npm install
```

### Compilation

**Watch mode** (recompile on file change):
```bash
npm run esbuild-watch
```

**One-time build**:
```bash
npm run esbuild
```

**Production build** (minified):
```bash
npm run vscode:prepublish
```

## Running the Extension

### In VS Code IDE

1. Open the project **root** (WaterCodeFlow/) in VS Code
2. Navigate to `editor/` subdirectory
3. Press **F5** to launch extension in debug mode
   - A new VS Code window opens with the extension active
   - Open any `.py` file to activate
   - **WaterCodeFlow** panel appears in activity bar

### From Command Line

```bash
# One terminal: watch for changes
npm run esbuild-watch

# Another terminal: launch extension host
code --extensionDevelopmentPath=. ..

# Or use the debug config
code --extensionDevelopmentPath=/path/to/editor /path/to/root
```

## Code Organization

### Extension Entry Point (`src/extension.ts`)

- **`activate(context)`**: Called when extension activates
  - Spawns Python subprocess (`glue/adapter.py`)
  - Registers webview providers & commands
  - Sets up file tracking & subscriptions
- **`deactivate()`**: Called on extension unload
  - Kills Python subprocess
  - Disposes all webviews

### GlueClient (`src/glueClient.ts`)

Manages communication with Python backend:
- **`async spawn(extensionPath)`**: Start Python subprocess
  - Runs `python3 -m glue.adapter` in project root
  - Parses JSON responses from Python
- **`async send<T>(command)`**: Send command and wait for response
  - Uses UUID for message correlation
  - Returns typed result or throws error

**Important**: The `extensionPath` parameter is the `editor/` directory. The client subtracts one level to find the project root where `glue/` is located.

### Providers

#### RecordingsViewProvider (`src/providers/RecordingsViewProvider.ts`)

Manages the **Recordings** sidebar view:
- Displays list of recorded runs
- Provides start/stop recording buttons
- Refreshes status every 2 seconds
- Handles webview ↔ extension messaging

#### VariablesViewProvider (`src/providers/VariablesViewProvider.ts`)

Manages the **Variables** sidebar view:
- Lists tracked variables
- Provides "Infer Variables" button
- Launches Variable Inspector on click

### Panels

#### VariableInspectionPanel (`src/panels/VariableInspectionPanel.ts`)

Modal webview for inspecting a single variable:
- Fetches variable timeline from glue
- Displays mutation points with code snippets
- Supports scrubbing to specific ticks
- Auto-scrolls editor to relevant line on click

#### InsightsPanel (`src/panels/InsightsPanel.ts`)

Modal webview for AI-generated insights:
- Fetches insights from glue API
- Shows diff summary & affected lines
- Clickable line references

## Webview Architecture

### Message Flow

```
User Click in Webview
  ↓
Webview JS: vscode.postMessage({command: '...'})
  ↓
Extension: webview.onDidReceiveMessage(message) → router
  ↓
Extension: glueClient.send({command: '...', ...args})
  ↓
Python: adapter.py receives JSON, calls glue functions
  ↓
Python: Returns result as JSON to stdout
  ↓
Extension: Parse response, resolve promise
  ↓
Extension: webview.postMessage({type: 'update', ...result})
  ↓
Webview JS: window.addEventListener('message') → DOM update
```

### Security (CSP)

- Nonce generated on extension activate: `randomUUID()`
- All webview scripts wrapped in `<script nonce="${nonce}">`
- CSP header: `script-src 'nonce-XXX'`
- No inline event handlers; all listeners bound in JS
- Resources loaded from `media/` only

## Glue API Integration

The extension consumes these glue functions via the Python adapter:

| Function | Purpose |
|----------|---------|
| `start_recording(filePath, interval)` | Launch daemon |
| `stop_recording(filePath)` | Stop daemon |
| `listRuns(filePath)` | Get recorded runs |
| `jumpToTick(filePath, tickId)` | Navigate to tick |
| `getStatus(filePath)` | Fetch recording status |
| `getVariableTimeline(filePath, varName)` | Get var mutations |
| `listTrackedVariables(filePath)` | List variables |
| `getInsights(filePath, fromTick, toTick)` | Get AI analysis |
| Additional: all 22 glue exports via `glue/adapter.py` |

See `glue/__init__.py` for full API reference.

## Building for Production

```bash
npm run vscode:prepublish
```

Output: `out/extension.js` (minified, ready for distribution)

## Debugging

### VS Code Extension Debugger
- Press **F5** to launch with debugger attached
- Set breakpoints in TypeScript files
- Uses source maps for debugging compiled JS

### Python Subprocess
- Check stderr output in **Debug Console**
- Test adapter directly:
  ```bash
  cd /path/to/WaterCodeFlow
  echo '{"command":"listDaemons","id":"1"}' | python3 -m glue.adapter
  ```

### Webview DevTools
- In extension host, right-click webview → **Inspect Element**
- Browser DevTools open for that webview
- Debug JS, inspect DOM, check network

## Dependencies

**Runtime** (bundled):
- None (vscode polyfills provided)

**Development**:
- `@types/vscode`: VS Code API types
- `@types/node`: Node.js types
- `typescript`: TS compiler
- `esbuild`: Fast bundler

## Troubleshooting

### "Cannot find module 'vscode'"
- Run `npm install` in editor/

### Extension not activating
- Check activation events in `package.json`
- Ensure `.codevovle/` exists or Python file is open
- Review **Output** panel (Ctrl+Shift+U) for logs

### Webviews not appearing
- Check that `media/` files exist & are referenced correctly
- Verify `localResourceRoots` in webview options
- Check browser console in webview DevTools

### Python adapter not responding
- Test adapter: `echo '{"command":"listDaemons","id":"1"}' | python3 -m glue.adapter`
- Check Python is in PATH
- Review extension log output

## Contributing

When adding new features:

1. **Add command** in `package.json` under `contributes.commands`
2. **Implement handler** in `extension.ts`
3. **Add glue function** call in provider/panel
4. **Create webview** if needed in `media/`
5. **Update types** in `src/types.ts`
6. **Test** with F5 in VS Code

## Release Checklist

- [ ] Update version in `package.json`
- [ ] Update `CHANGELOG.md` (root)
- [ ] Run `npm run vscode:prepublish` for production build
- [ ] Test with clean VS Code installation
- [ ] Package: `vsce package`
- [ ] Publish: `vsce publish` (if using VS Code registry)

---

**Last Updated**: February 2026  
**Status**: Beta
