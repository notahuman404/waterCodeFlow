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
const utils_1 = require("../utils");
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
    constructor(panel, extensionUri, bridge) {
        this.bridge = bridge;
        this._disposables = [];
        this._panel = panel;
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
            }
        });
    }
    async _pushData() {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        let trackedFiles = [];
        let vars = [];
        let runs = [];
        if (fp) {
            try {
                const recs = await this.bridge.send('listRecordings', { filePath: fp });
                trackedFiles = recs.length > 0 ? [{ name: fp.split('/').pop() || fp, path: fp }] : [];
            }
            catch (_) { }
            try {
                vars = await this.bridge.send('listTrackedVariables', { filePath: fp });
            }
            catch (_) { }
            try {
                runs = await this.bridge.send('listRuns', { filePath: fp });
            }
            catch (_) { }
        }
        // Fallback demo data if nothing from glue
        if (trackedFiles.length === 0) {
            trackedFiles = [
                { name: 'main.py', path: './src/main.py' },
                { name: 'utils.py', path: './src/utils.py' },
                { name: 'data_proc.py', path: './src/data_proc.py' }
            ];
        }
        if (vars.length === 0) {
            vars = [
                { name: 'counter', evolutions: 5 },
                { name: 'total_sum', evolutions: 8 },
                { name: 'status', evolutions: 3 },
                { name: 'data_buffer', evolutions: 6 }
            ];
        }
        if (runs.length === 0) {
            runs = [
                { run_id: 4, tick_count: 7 },
                { run_id: 3, tick_count: 3 },
                { run_id: 2, tick_count: 2 }
            ];
        }
        this._panel.webview.postMessage({ command: 'setData', trackedFiles, vars, runs });
    }
    dispose() {
        RecordingsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length)
            this._disposables.pop()?.dispose();
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
  <div class="recordings-container" id="recordings-container"><div class="loading">Loading...</div></div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.RecordingsPanel = RecordingsPanel;
//# sourceMappingURL=RecordingsPanel.js.map