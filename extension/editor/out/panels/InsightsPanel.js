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
exports.InsightsPanel = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const utils_1 = require("../utils");
class InsightsPanel {
    static createOrShow(extensionUri, bridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (InsightsPanel.currentPanel) {
            InsightsPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('watercodeflow.insights', 'Insights', column, { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] });
        InsightsPanel.currentPanel = new InsightsPanel(panel, extensionUri, bridge);
    }
    constructor(panel, extensionUri, bridge) {
        this.bridge = bridge;
        this._disposables = [];
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'ready') {
                await this._pushBranchData(extensionUri);
            }
            else if (msg.command === 'getInsights') {
                const fp = vscode.window.activeTextEditor?.document.fileName || '';
                if (!fp) {
                    vscode.window.showWarningMessage('No active file');
                    return;
                }
                try {
                    const result = await this.bridge.send('getInsights', {
                        filePath: fp,
                        fromTick: msg.fromRunIdx,
                        toTick: msg.toRunIdx,
                        model: 'default'
                    });
                    this._panel.webview.postMessage({
                        command: 'insightsResult',
                        fromRunIdx: msg.fromRunIdx,
                        toRunIdx: msg.toRunIdx,
                        insights: result
                    });
                }
                catch (e) {
                    vscode.window.showErrorMessage('Get insights failed: ' + e.message);
                }
            }
        });
    }
    async _pushBranchData(extensionUri) {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        const extPath = extensionUri.fsPath;
        // extPath IS the extension root
        const projectRoot = extPath;
        let recordings = [];
        let branches = [];
        // Load disk recordings
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
            }
        }
        catch (_) { }
        // Try to get branches from glue
        if (fp) {
            try {
                branches = await this.bridge.send('getBranches', { filePath: fp });
            }
            catch (_) { }
        }
        this._panel.webview.postMessage({
            command: 'setData',
            recordings,
            branches
        });
    }
    dispose() {
        InsightsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            this._disposables.pop()?.dispose();
        }
    }
    _getHtml(webview, extensionUri) {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'insights.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'insights.css'));
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
  <div class="insights-container">
    <div class="insights-header">
      <span class="insights-title">Code Insights</span>
      <button class="insights-btn" id="btn-refresh">Refresh</button>
    </div>
    <div class="tree-container" id="tree-container">
      <svg id="tree-svg" width="100%" height="600"></svg>
    </div>
    <div class="legend" id="legend"></div>
    <div class="insights-output" id="insights-output">
      <div class="output-placeholder">Select two runs to generate insights</div>
    </div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.InsightsPanel = InsightsPanel;
//# sourceMappingURL=InsightsPanel.js.map