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
const utils_1 = require("../utils");
class VariableInspectorPanel {
    static createOrShow(extensionUri, bridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (VariableInspectorPanel.currentPanel) {
            VariableInspectorPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('watercodeflow.variableInspector', 'Single Variable Inspection', column, { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] });
        VariableInspectorPanel.currentPanel = new VariableInspectorPanel(panel, extensionUri, bridge);
    }
    constructor(panel, extensionUri, bridge) {
        this.bridge = bridge;
        this._disposables = [];
        this._panel = panel;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'ready') {
                await this._pushVarData();
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
    async _pushVarData() {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        let timeline = [];
        let recordings = [];
        if (fp) {
            try {
                recordings = await this.bridge.send('listRecordings', { filePath: fp });
            }
            catch (_) { }
        }
        this._panel.webview.postMessage({ command: 'setData', filePath: fp, timeline, recordings });
    }
    dispose() {
        VariableInspectorPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length)
            this._disposables.pop()?.dispose();
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
  <div class="vi-topbar">
    <span class="vi-watcher">Watcher</span>
    <span class="vi-title">Variable Inspector</span>
  </div>
  <hr class="vi-divider" />
  <div class="vi-body">
    <div class="vi-left">
      <div class="vi-section-label">VALUE DISPLAY</div>
      <pre class="vi-code" id="vi-code"></pre>
      <div class="vi-btns">
        <button class="vi-btn" id="btn-download">Download .pkl</button>
        <button class="vi-btn" id="btn-print">Print Value</button>
      </div>
      <pre class="vi-snippet" id="vi-snippet">from some_import_name import s
s.inspect(variable_name="user_data", runs=5)</pre>
    </div>
    <div class="vi-right">
      <div class="vi-meta-header">Metadata</div>
      <div class="vi-meta-list" id="vi-meta-list"></div>
    </div>
  </div>
  <div class="vi-timeline">
    <div class="vi-time-label">Time: <span id="vi-time">14:30:00.005</span></div>
    <div class="vi-dots" id="vi-dots"></div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.VariableInspectorPanel = VariableInspectorPanel;
//# sourceMappingURL=VariableInspectorPanel.js.map