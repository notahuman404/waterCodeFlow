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
exports.VariableInspectorPanel = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const utils_1 = require("../utils");
class VariableInspectorPanel {
    static createOrShow(extensionUri, bridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (VariableInspectorPanel.currentPanel) {
            VariableInspectorPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('watercodeflow.variableInspector', 'Variable Inspector', column, { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] });
        VariableInspectorPanel.currentPanel = new VariableInspectorPanel(panel, extensionUri, bridge);
    }
    constructor(panel, extensionUri, bridge) {
        this.bridge = bridge;
        this._disposables = [];
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'ready':
                    await this._pushVarData(extensionUri);
                    break;
                case 'exportTimeline':
                    const uri = await vscode.window.showSaveDialog({
                        defaultUri: vscode.Uri.file(`${msg.varName}-timeline.json`),
                        filters: { 'JSON': ['json'] }
                    });
                    if (uri) {
                        fs.writeFileSync(uri.fsPath, JSON.stringify(msg.data, null, 2));
                        vscode.window.showInformationMessage(`Timeline exported to ${uri.fsPath}`);
                    }
                    break;
            }
        });
    }
    async _pushVarData(extensionUri) {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        const extPath = extensionUri.fsPath;
        // extPath IS the extension root
        const projectRoot = extPath;
        let recordings = [];
        // Load disk recordings — this is the PRIMARY source of truth
        const recordingsDir = path.join(projectRoot, 'built', 'recordings');
        try {
            if (fs.existsSync(recordingsDir)) {
                const files = fs.readdirSync(recordingsDir)
                    .filter(f => f.endsWith('.json'))
                    .sort()
                    .reverse();
                recordings = files.map(f => {
                    try {
                        const rec = JSON.parse(fs.readFileSync(path.join(recordingsDir, f), 'utf8'));
                        return rec;
                    }
                    catch (_) {
                        return null;
                    }
                }).filter(Boolean);
                // Filter to current file if one is active
                if (fp) {
                    const forFile = recordings.filter(r => (r.filePath || r.file_path || '') === fp);
                    if (forFile.length > 0) {
                        recordings = forFile;
                    }
                }
            }
        }
        catch (_) { }
        // Enrich with watcher events
        recordings = recordings.map(rec => enrichWithWatcherEvents(rec, projectRoot));
        this._panel.webview.postMessage({
            command: 'setData',
            recordings,
            filePath: fp
        });
    }
    dispose() {
        VariableInspectorPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            this._disposables.pop()?.dispose();
        }
    }
    _getHtml(webview, extensionUri) {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'variableInspector.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'variableInspector.css'));
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
  <div class="vi-container">
    <div class="vi-header">
      <span class="vi-title">VARIABLE INSPECTOR</span>
      <div class="vi-actions">
        <button class="vi-btn" id="btn-download" title="Export timeline as JSON">⬇</button>
        <button class="vi-btn" id="btn-print" title="Log to console">🖨</button>
      </div>
    </div>
    <div class="vi-scrubber">
      <div class="vi-dots" id="vi-dots"></div>
      <div class="vi-time" id="vi-time">—</div>
    </div>
    <div class="vi-split">
      <div class="vi-code-pane">
        <div class="vi-code-label">Value at selected run:</div>
        <pre class="vi-code" id="vi-code">Select a variable to inspect its value across runs.</pre>
      </div>
      <div class="vi-meta-pane">
        <div class="vi-meta-label">Variable Metadata:</div>
        <div class="vi-meta-list" id="vi-meta-list"></div>
      </div>
    </div>
    <div class="vi-snippet-pane">
      <div class="vi-snippet-label">Inspection Info:</div>
      <pre class="vi-snippet" id="vi-snippet"># Select a variable above to see its value history</pre>
    </div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.VariableInspectorPanel = VariableInspectorPanel;
function enrichWithWatcherEvents(rec, projectRoot) {
    if (!rec || rec.vars) {
        return rec;
    }
    const runId = rec.runId || rec.run_id;
    if (!runId) {
        return rec;
    }
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
//# sourceMappingURL=VariableInspectorPanel.js.map