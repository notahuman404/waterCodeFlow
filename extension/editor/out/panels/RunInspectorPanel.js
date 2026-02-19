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
exports.RunInspectorPanel = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const utils_1 = require("../utils");
class RunInspectorPanel {
    static createOrShow(extensionUri, bridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (RunInspectorPanel.currentPanel) {
            RunInspectorPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('watercodeflow.runInspector', 'Run Inspector', column, { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] });
        RunInspectorPanel.currentPanel = new RunInspectorPanel(panel, extensionUri, bridge);
    }
    constructor(panel, extensionUri, bridge) {
        this.bridge = bridge;
        this._disposables = [];
        this._panel = panel;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'ready') {
                await this._pushRunData(extensionUri);
            }
            else if (msg.command === 'close') {
                this.dispose();
            }
            else if (msg.command === 'jumpToTick') {
                const fp = vscode.window.activeTextEditor?.document.fileName || '';
                if (fp && msg.tickId !== undefined) {
                    try {
                        await this.bridge.send('jumpToTick', { filePath: fp, tickId: msg.tickId });
                    }
                    catch (e) {
                        vscode.window.showErrorMessage('Jump failed: ' + e.message);
                    }
                }
            }
            else if (msg.command === 'openVariableInspector') {
                vscode.commands.executeCommand('watercodeflow.openInspector');
            }
        });
    }
    async _pushRunData(extensionUri) {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        const extPath = extensionUri.fsPath;
        // extPath IS the extension root
        const projectRoot = extPath;
        let recordings = [];
        // Load disk recordings as the primary source
        const recordingsDir = path.join(projectRoot, 'built', 'recordings');
        try {
            if (fs.existsSync(recordingsDir)) {
                const files = fs.readdirSync(recordingsDir)
                    .filter(f => f.endsWith('.json'))
                    .sort()
                    .reverse();
                recordings = files.map(f => {
                    try {
                        return JSON.parse(fs.readFileSync(path.join(recordingsDir, f), 'utf8'));
                    }
                    catch (_) {
                        return null;
                    }
                }).filter(Boolean);
                if (fp) {
                    const forFile = recordings.filter(r => (r.filePath || r.file_path || '') === fp);
                    if (forFile.length > 0) {
                        recordings = forFile;
                    }
                }
            }
        }
        catch (_) { }
        // Enrich with watcher event variable data
        recordings = recordings.map(rec => enrichRecording(rec, extPath));
        this._panel.webview.postMessage({ command: 'setData', recordings, filePath: fp });
    }
    dispose() {
        RunInspectorPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            this._disposables.pop()?.dispose();
        }
    }
    _getHtml(webview, extensionUri) {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'runInspector.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'runInspector.css'));
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
  <div class="ri-header">
    <button class="ri-back-btn" id="ri-back">✕ Close</button>
    <span class="ri-title" id="ri-run-title">Run Inspector</span>
    <span class="ri-status" id="ri-status"></span>
  </div>
  <hr class="ri-divider" />
  <div class="ri-context-bar">
    <span class="ri-line-no" id="ri-lineno">File:</span>
    <span class="ri-file-path" id="ri-filepath">—</span>
    <button class="ri-open-vi-btn" id="ri-open-vi">Open Variable Inspector</button>
  </div>
  <hr class="ri-divider" />
  <div class="ri-body">
    <div class="ri-left" id="ri-left"><div class="loading">Loading…</div></div>
    <div class="ri-right">
      <div class="ri-meta-header">Variable Metadata</div>
      <div id="ri-meta-blocks"></div>
    </div>
  </div>
  <div class="ri-timeline">
    <div class="ri-step-badge" id="ri-step-badge">No runs yet</div>
    <div class="ri-dots" id="ri-dots"></div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.RunInspectorPanel = RunInspectorPanel;
function enrichRecording(rec, extPath) {
    const runId = rec.runId || rec.run_id;
    if (!runId || rec.vars) {
        return rec;
    }
    // extPath IS the extension root
    const projectRoot = extPath;
    const watcherDir = path.join(projectRoot, 'built', 'watcher_events', runId);
    if (!fs.existsSync(watcherDir)) {
        return rec;
    }
    const varMap = {};
    try {
        fs.readdirSync(watcherDir).filter(f => f.endsWith('.jsonl')).forEach(file => {
            fs.readFileSync(path.join(watcherDir, file), 'utf8')
                .split('\n').filter(Boolean)
                .forEach(line => {
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
//# sourceMappingURL=RunInspectorPanel.js.map