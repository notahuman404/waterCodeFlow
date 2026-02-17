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
const utils_1 = require("../utils");
class InsightsPanel {
    static createOrShow(extensionUri, bridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (InsightsPanel.currentPanel) {
            InsightsPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('watercodeflow.insights', 'Insight selection', column, { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] });
        InsightsPanel.currentPanel = new InsightsPanel(panel, extensionUri, bridge);
    }
    constructor(panel, extensionUri, bridge) {
        this.bridge = bridge;
        this._disposables = [];
        this._panel = panel;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'ready') {
                await this._pushBranchData();
            }
            else if (msg.command === 'getInsights') {
                const fp = vscode.window.activeTextEditor?.document.fileName || '';
                if (!fp) {
                    vscode.window.showWarningMessage('Open a tracked file first.');
                    return;
                }
                try {
                    const cfg = vscode.workspace.getConfiguration('watercodeflow');
                    const model = cfg.get('aiModel', 'Gemini');
                    const result = await this.bridge.send('getInsights', {
                        filePath: fp,
                        fromTick: msg.fromTick,
                        toTick: msg.toTick,
                        model
                    });
                    this._panel.webview.postMessage({ command: 'insightsResult', result });
                }
                catch (e) {
                    this._panel.webview.postMessage({ command: 'insightsError', error: e.message });
                }
            }
        });
    }
    async _pushBranchData() {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        let branches = [];
        let recordings = [];
        if (fp) {
            try {
                branches = await this.bridge.send('getBranches', { filePath: fp });
            }
            catch (_) { }
            try {
                recordings = await this.bridge.send('listRecordings', { filePath: fp });
            }
            catch (_) { }
        }
        this._panel.webview.postMessage({ command: 'setBranchData', branches, recordings });
    }
    dispose() {
        InsightsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length)
            this._disposables.pop()?.dispose();
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
  <div class="canvas-wrap">
    <canvas id="insight-canvas"></canvas>
    <button class="insights-btn" id="get-insights-btn">Get Insights</button>
    <div class="insights-result hidden" id="insights-result"></div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.InsightsPanel = InsightsPanel;
//# sourceMappingURL=InsightsPanel.js.map