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
const utils_1 = require("../utils");
class RunInspectorPanel {
    static createOrShow(extensionUri, bridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (RunInspectorPanel.currentPanel) {
            RunInspectorPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('watercodeflow.runInspector', 'Run Recording Inspection', column, { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] });
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
                await this._pushRunData();
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
        });
    }
    async _pushRunData() {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        let runs = [];
        let recordings = [];
        if (fp) {
            try {
                runs = await this.bridge.send('listRuns', { filePath: fp });
            }
            catch (_) { }
            try {
                recordings = await this.bridge.send('listRecordings', { filePath: fp });
            }
            catch (_) { }
        }
        this._panel.webview.postMessage({ command: 'setData', runs, recordings, filePath: fp });
    }
    dispose() {
        RunInspectorPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length)
            this._disposables.pop()?.dispose();
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
    <button class="ri-back-btn" id="ri-back">&#8592; Back</button>
    <span class="ri-title" id="ri-run-title">Run Recording Inspection</span>
    <span class="ri-status" id="ri-status">Status: Ready</span>
  </div>
  <hr class="ri-divider" />
  <div class="ri-context-bar">
    <span class="ri-line-no" id="ri-lineno">Line no.: —</span>
    <span class="ri-code-icon">&#x1f4c4;</span>
    <span class="ri-code-line" id="ri-codeline">—</span>
    <span class="ri-file-path" id="ri-filepath">—</span>
    <span class="ri-pinned">PINNED CONTEXT HEAD</span>
  </div>
  <hr class="ri-divider" />
  <div class="ri-body">
    <div class="ri-left" id="ri-left"><div class="loading">Loading...</div></div>
    <div class="ri-right">
      <div class="ri-meta-header">Variable Metadata</div>
      <div id="ri-meta-blocks"></div>
    </div>
  </div>
  <div class="ri-timeline">
    <div class="ri-step-badge" id="ri-step-badge">Step —</div>
    <div class="ri-dots" id="ri-dots"></div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.RunInspectorPanel = RunInspectorPanel;
//# sourceMappingURL=RunInspectorPanel.js.map