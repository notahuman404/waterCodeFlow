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
exports.RecordingViewerProvider = void 0;
const vscode = __importStar(require("vscode"));
const utils_1 = require("../utils");
class RecordingViewerProvider {
    constructor(_extensionUri, _bridge) {
        this._extensionUri = _extensionUri;
        this._bridge = _bridge;
        this._disposables = [];
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
                    await this._pushData();
                    // Start auto-refresh when daemon is active
                    this._startAutoRefresh();
                    break;
                case 'refresh':
                    await this._pushData();
                    break;
                case 'openInsights':
                    vscode.commands.executeCommand('watercodeflow.openInsights');
                    break;
                case 'jumpToTick': {
                    const filePath = vscode.window.activeTextEditor?.document.fileName || '';
                    if (filePath && msg.tickId !== undefined && msg.tickId !== null) {
                        try {
                            await this._bridge.send('jumpToTick', { filePath, tickId: msg.tickId });
                            vscode.window.showInformationMessage(`✓ Jumped to tick ${msg.tickId}`);
                        }
                        catch (e) {
                            vscode.window.showErrorMessage(`Jump to tick failed: ${e.message}\n\n` +
                                `This requires the CodeVovle core to be installed and a daemon to be running.`);
                        }
                    }
                    else {
                        vscode.window.showWarningMessage('No tick ID available for this recording');
                    }
                    break;
                }
                case 'renameBranch': {
                    try {
                        await this._bridge.send('renameBranch', {
                            oldName: msg.oldName,
                            newName: msg.newName
                        });
                        vscode.window.showInformationMessage(`✓ Branch renamed to "${msg.newName}"`);
                        await this._pushData();
                    }
                    catch (e) {
                        vscode.window.showErrorMessage(`Rename branch failed: ${e.message}`);
                    }
                    break;
                }
                case 'switchBranch': {
                    const fp = vscode.window.activeTextEditor?.document.fileName || '';
                    if (fp) {
                        try {
                            const branches = await this._bridge.send('getBranches', { filePath: fp });
                            const b = branches.find((x) => x.name === msg.branchName);
                            if (b && b.head_tick !== null) {
                                await this._bridge.send('jumpToTick', { filePath: fp, tickId: b.head_tick });
                                vscode.window.showInformationMessage(`✓ Switched to branch "${msg.branchName}"`);
                            }
                        }
                        catch (e) {
                            vscode.window.showErrorMessage(`Switch branch failed: ${e.message}`);
                        }
                    }
                    break;
                }
            }
        }, null, this._disposables);
        // Refresh scrubber when active editor changes
        this._disposables.push(vscode.window.onDidChangeActiveTextEditor(() => {
            this._pushData();
            this._startAutoRefresh();
        }));
        // Refresh when panel becomes visible
        webviewView.onDidChangeVisibility(() => {
            if (webviewView.visible) {
                this._pushData();
                this._startAutoRefresh();
            }
            else {
                this._stopAutoRefresh();
            }
        }, null, this._disposables);
    }
    _startAutoRefresh() {
        // Clear any existing timer
        this._stopAutoRefresh();
        // Refresh every 2 seconds while panel is visible and file is open
        if (this._view?.visible && vscode.window.activeTextEditor) {
            this._refreshTimer = setInterval(() => {
                this._pushData();
            }, 2000);
        }
    }
    _stopAutoRefresh() {
        if (this._refreshTimer) {
            clearInterval(this._refreshTimer);
            this._refreshTimer = undefined;
        }
    }
    async _pushData() {
        if (!this._view) {
            return;
        }
        const filePath = vscode.window.activeTextEditor?.document.fileName || '';
        // ── Read CodeVovle daemon recordings (tick timeline) ─────────────────
        // These are real-time diffs captured by the daemon, not run snapshots.
        let recordings = [];
        let branches = [];
        let status = null;
        if (filePath) {
            // Get daemon status
            try {
                status = await this._bridge.send('getStatus', { filePath });
            }
            catch (e) {
                console.warn('getStatus failed:', e.message);
            }
            // Get recordings (ticks)
            try {
                recordings = await this._bridge.send('listRecordings', { filePath });
            }
            catch (e) {
                console.warn('listRecordings failed:', e.message);
            }
            // Get branches
            try {
                branches = await this._bridge.send('getBranches', { filePath });
            }
            catch (e) {
                console.warn('getBranches failed:', e.message);
            }
        }
        this._view.webview.postMessage({
            command: 'setData',
            recordings,
            branches,
            filePath,
            status
        });
    }
    dispose() {
        this._stopAutoRefresh();
        while (this._disposables.length) {
            this._disposables.pop()?.dispose();
        }
    }
    _getHtml(webview) {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'media', 'recordingViewer.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'media', 'recordingViewer.css'));
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
  <div class="viewer-container">
    <div class="status-bar" id="status-bar" style="display:none;padding:4px 8px;background:rgba(100,100,100,0.1);font-size:10px;color:var(--vscode-descriptionForeground);border-bottom:1px solid var(--vscode-panel-border)"></div>
    <div class="scrubber-row">
      <button class="nav-btn" id="btn-back">&#9664;</button>
      <button class="nav-btn pause-btn" id="btn-pause">&#9646;&#9646;</button>
      <div class="dots-track" id="dots-track"></div>
      <button class="nav-btn" id="btn-fwd">&#9654;</button>
    </div>
    <div class="scrubber-labels">
      <span>Diff Timeline</span>
      <span id="change-count">— ticks</span>
    </div>
    <div class="actions-row">
      <button class="action-btn" id="btn-refresh" title="Refresh timeline">&#8635;</button>
      <button class="action-btn" id="btn-branches">&#x1f500; Branches &#x25be;</button>
      <button class="action-btn" id="btn-insights">&#x1f4ca; Insights</button>
    </div>
    <div class="branches-dropdown hidden" id="branches-dropdown"></div>
    <div class="rename-container hidden" id="rename-container">
      <span class="rename-label" id="rename-branch-label"></span>
      <input type="text" id="rename-input" placeholder="New branch name..." />
      <button id="rename-confirm-btn">Rename</button>
      <button id="rename-cancel-btn">Cancel</button>
    </div>
  </div>
  <span class="star-icon">&#10022;</span>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
exports.RecordingViewerProvider = RecordingViewerProvider;
//# sourceMappingURL=RecordingViewerProvider.js.map