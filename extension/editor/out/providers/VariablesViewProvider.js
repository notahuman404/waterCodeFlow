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
exports.VariablesViewProvider = void 0;
const vscode = __importStar(require("vscode"));
const utils_1 = require("../utils");
class VariablesViewProvider {
    constructor(_extensionUri, _bridge) {
        this._extensionUri = _extensionUri;
        this._bridge = _bridge;
        this._trackState = {};
    }
    resolveWebviewView(webviewView, _context, _token) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [vscode.Uri.joinPath(this._extensionUri, 'media')]
        };
        webviewView.webview.html = this._getHtml(webviewView.webview);
        webviewView.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'ready':
                    await this._pushVars();
                    break;
                case 'toggleTrack': {
                    const { name } = msg;
                    const s = this._trackState[name] || { tracked: false, mode: 'multi', runs: 5 };
                    s.tracked = !s.tracked;
                    this._trackState[name] = s;
                    webviewView.webview.postMessage({ command: 'trackState', name, state: s });
                    break;
                }
                case 'setTrackMode': {
                    const { name, mode, runs } = msg;
                    const s = this._trackState[name] || { tracked: true, mode: 'multi', runs: 5 };
                    s.mode = mode;
                    if (runs !== undefined)
                        s.runs = runs;
                    this._trackState[name] = s;
                    break;
                }
                case 'refresh':
                    await this._pushVars();
                    break;
            }
        });
        // Refresh when active editor changes
        vscode.window.onDidChangeActiveTextEditor(() => this._pushVars());
    }
    async _pushVars() {
        if (!this._view)
            return;
        const editor = vscode.window.activeTextEditor;
        const filePath = editor?.document.fileName || '';
        let vars = [];
        if (filePath) {
            try {
                const inferred = await this._bridge.send('getVariableTimeline', {
                    filePath,
                    variableName: '_all_vars_',
                    maxTicks: 1
                });
                // inferred may be empty — fall through to infer_from_file
            }
            catch (_) { }
            // Use Python-side infer_variables_from_file via a separate call
            try {
                // We call listTrackedVariables which gives us config-tracked vars
                const tracked = await this._bridge.send('listTrackedVariables', { filePath });
                vars = tracked.map((v) => ({
                    name: typeof v === 'string' ? v : v.name,
                    file: filePath,
                    scope: (typeof v === 'object' && v.scope) ? v.scope : 'global',
                    line_no: v.line_no || 0
                }));
            }
            catch (_) { }
        }
        // Always send something — if no real data, show placeholder sections
        this._view.webview.postMessage({
            command: 'setVars',
            filePath,
            vars,
            trackState: this._trackState
        });
    }
    _getHtml(webview) {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'media', 'variables.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'media', 'variables.css'));
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
  <div class="header-row">
    <span class="header-label">VARIABLES</span>
    <button class="refresh-btn" id="refresh-btn" title="Refresh">&#8635;</button>
  </div>
  <div class="search-wrap">
    <input type="text" id="filter-input" class="filter-input" placeholder="Filter variables..." />
  </div>
  <div id="sections-container"></div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.VariablesViewProvider = VariablesViewProvider;
//# sourceMappingURL=VariablesViewProvider.js.map