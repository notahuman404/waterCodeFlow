"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.RecordingsPanel = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const utils_1 = require("../utils");
/** Parse watcher JSONL events and merge variables into an existing recording object. */
function enrichRecordingWithVars(rec, extPath) {
    const runId = rec.runId || rec.run_id;
    if (!runId || rec.vars) {
        return rec;
    }
    // extPath IS the extension root (no need to go up one level)
    const projectRoot = extPath;
    const watcherDir = path.join(projectRoot, 'built', 'watcher_events', runId);
    if (!fs.existsSync(watcherDir)) {
        return rec;
    }
    const varMap = {};
    try {
        fs.readdirSync(watcherDir).filter(f => f.endsWith('.jsonl')).forEach(file => {
            fs.readFileSync(path.join(watcherDir, file), 'utf8')
                .split('\n').filter(Boolean).forEach(line => {
                try {
                    const evt = JSON.parse(line);
                    const name = evt.variable || evt.name;
                    if (name) {
                        varMap[name] = {
                            name,
                            value: evt.value ?? evt.new_value ?? null,
                            scope: evt.scope || 'global',
                            type: evt.type || typeof evt.value,
                            line_no: evt.line_no || evt.lineno || 0,
                            evolutions: (varMap[name]?.evolutions ?? 0) + 1,
                        };
                    }
                }
                catch (_) { }
            });
        });
    }
    catch (_) { }
    return Object.keys(varMap).length > 0 ? { ...rec, vars: Object.values(varMap) } : rec;
}
class RecordingsPanel {
    static createOrShow(extensionUri, bridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (RecordingsPanel.currentPanel) {
            RecordingsPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('watercodeflow.recordings', 'Recordings', column, { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] });
        RecordingsPanel.currentPanel = new RecordingsPanel(panel, extensionUri, bridge);
    }
    /** Forward a run lifecycle event (stdout, stderr, done, error) into the webview. */
    postRunEvent(type, data) {
        // Make sure the panel is visible so the user can see live output
        if (!this._panel.visible) {
            this._panel.reveal(vscode.ViewColumn.Beside, true);
        }
        this._panel.webview.postMessage({ command: 'run.event', type, data });
    }
    constructor(panel, extensionUri, bridge) {
        this.bridge = bridge;
        this._disposables = [];
        this._lastPushedFilePath = '';
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'ready':
                    await this._pushData();
                    break;
                case 'openRunInspector':
                    vscode.commands.executeCommand('watercodeflow.openRunInspector');
                    break;
                case 'openVariableInspector':
                    vscode.commands.executeCommand('watercodeflow.openInspector');
                    break;
                case 'deleteRun': {
                    const fp = vscode.window.activeTextEditor?.document.fileName || '';
                    if (fp) {
                        try {
                            await this.bridge.send('deleteRun', { filePath: fp, runId: msg.runId });
                            await this._pushData();
                        }
                        catch (e) {
                            vscode.window.showErrorMessage('Delete run failed: ' + e.message);
                        }
                    }
                    break;
                }
                case 'deleteRecording': {
                    const extPath = this._extensionUri.fsPath;
                    // extPath IS the extension root (no need to go up one level)
                    const projectRoot = extPath;
                    const recordingsDir = path.join(projectRoot, 'built', 'recordings');
                    try {
                        if (fs.existsSync(recordingsDir)) {
                            const files = fs.readdirSync(recordingsDir);
                            const match = files.find(f => f.startsWith(msg.runId) || f === `${msg.runId}.json`);
                            if (match) {
                                fs.unlinkSync(path.join(recordingsDir, match));
                            }
                        }
                    }
                    catch (_) { }
                    // Also tell glue to remove it (non-fatal)
                    this.bridge.send('deleteRecording', { runId: msg.runId }).catch((e) => {
                        console.warn('deleteRecording glue call failed:', e.message);
                        // Non-fatal: disk deletion already happened
                    });
                    this._panel.webview.postMessage({ command: 'recordingDeleted', runId: msg.runId });
                    await this._pushData();
                    break;
                }
                case 'exportRecording': {
                    const rec = msg.recording;
                    if (!rec) {
                        break;
                    }
                    const uri = await vscode.window.showSaveDialog({
                        defaultUri: vscode.Uri.file(`recording-${rec.runId || 'export'}.json`),
                        filters: { 'JSON': ['json'] }
                    });
                    if (uri) {
                        fs.writeFileSync(uri.fsPath, JSON.stringify(rec, null, 2));
                        vscode.window.showInformationMessage(`Recording exported to ${uri.fsPath}`);
                    }
                    break;
                }
            }
        });
    }
    async _pushData() {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        const extPath = this._extensionUri.fsPath;
        // extPath IS the extension root — no need to go up one level
        const projectRoot = extPath;
        // ── 1. spawnRun recordings from built/recordings/*.json ──────────────
        let recordings = [];
        const recordingsDir = path.join(projectRoot, 'built', 'recordings');
        try {
            if (fs.existsSync(recordingsDir)) {
                const files = fs.readdirSync(recordingsDir)
                    .filter(f => f.endsWith('.json'))
                    .sort()
                    .reverse(); // newest first
                recordings = files.map(f => {
                    try {
                        const rec = JSON.parse(fs.readFileSync(path.join(recordingsDir, f), 'utf8'));
                        return enrichRecordingWithVars(rec, extPath);
                    }
                    catch (_) {
                        return null;
                    }
                }).filter(Boolean);
            }
        }
        catch (_) { }
        // ── 2. Daemon-based runs from .codevovle/ (via glue listRuns) ────────
        // These are created by the background recording daemon (track file button).
        // Merge them with spawnRun recordings so both show up in the panel.
        if (fp) {
            try {
                const daemonRuns = await this.bridge.send('listRuns', { filePath: fp });
                if (Array.isArray(daemonRuns) && daemonRuns.length > 0) {
                    // Avoid duplicating runs already in the JSON recordings list
                    const existingIds = new Set(recordings.map((r) => r.runId || r.run_id));
                    for (const run of daemonRuns) {
                        if (!existingIds.has(run.runId) && !existingIds.has(run.run_id)) {
                            recordings.push(run);
                        }
                    }
                }
            }
            catch (_) { }
        }
        // ── 3. Tracked files — derived from all recordings ───────────────────
        const seen = new Set();
        const trackedFiles = [];
        recordings.forEach(r => {
            const p = r.filePath || r.file_path || '';
            if (p && !seen.has(p)) {
                seen.add(p);
                trackedFiles.push({ name: path.basename(p), path: p });
            }
        });
        // Also include the active file even if it has no recordings yet
        if (fp && !seen.has(fp)) {
            try {
                const recs = await this.bridge.send('listRecordings', { filePath: fp });
                if (recs && recs.length > 0) {
                    trackedFiles.unshift({ name: path.basename(fp), path: fp });
                }
            }
            catch (_) { }
        }
        // ── 4. Variable evolutions from glue ─────────────────────────────────
        let vars = [];
        if (fp) {
            try {
                vars = await this.bridge.send('listTrackedVariables', { filePath: fp });
                if (!Array.isArray(vars)) {
                    vars = [];
                }
            }
            catch (_) { }
        }
        const resetFilter = this._lastPushedFilePath !== fp;
        this._lastPushedFilePath = fp;
        this._panel.webview.postMessage({
            command: 'setData',
            trackedFiles,
            vars,
            runs: [],
            recordings,
            filePath: fp,
            _resetFilter: resetFilter,
        });
    }
    dispose() {
        RecordingsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            this._disposables.pop()?.dispose();
        }
    }
    _getHtml(webview, extensionUri) {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'recordings.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'recordings.css'));
        const nonce = (0, utils_1.getNonce)();
        return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="${styleUri}" rel="stylesheet">
</head>
<body>
  <div class="recordings-container" id="recordings-container"><div class="loading">Loading…</div></div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.RecordingsPanel = RecordingsPanel;
//# sourceMappingURL=RecordingsPanel.js.map