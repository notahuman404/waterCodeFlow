import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

export class RecordingViewerProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly _bridge: GlueBridge
    ) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
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
                    break;
                case 'openInsights':
                    vscode.commands.executeCommand('watercodeflow.openInsights');
                    break;
                case 'jumpToTick': {
                    const filePath = vscode.window.activeTextEditor?.document.fileName || '';
                    if (filePath && msg.tickId !== undefined) {
                        try {
                            await this._bridge.send('jumpToTick', { filePath, tickId: msg.tickId });
                        } catch (e: any) {
                            vscode.window.showErrorMessage('Jump to tick failed: ' + e.message);
                        }
                    }
                    break;
                }
                case 'renameBranch': {
                    try {
                        await this._bridge.send('renameBranch', {
                            oldName: msg.oldName,
                            newName: msg.newName
                        });
                        await this._pushData();
                    } catch (e: any) {
                        vscode.window.showErrorMessage('Rename branch failed: ' + e.message);
                    }
                    break;
                }
                case 'switchBranch': {
                    const fp = vscode.window.activeTextEditor?.document.fileName || '';
                    if (fp) {
                        try {
                            // Get the branch head tick
                            const branches: any[] = await this._bridge.send('getBranches', { filePath: fp });
                            const b = branches.find((x: any) => x.name === msg.branchName);
                            if (b && b.head_tick !== null) {
                                await this._bridge.send('jumpToTick', { filePath: fp, tickId: b.head_tick });
                            }
                        } catch (_) {}
                    }
                    break;
                }
            }
        });

        vscode.window.onDidChangeActiveTextEditor(() => this._pushData());
    }

    private async _pushData() {
        if (!this._view) return;
        const filePath = vscode.window.activeTextEditor?.document.fileName || '';
        let recordings: any[] = [];
        let branches: any[] = [];

        if (filePath) {
            try {
                recordings = await this._bridge.send('listRecordings', { filePath });
            } catch (_) {}
            try {
                branches = await this._bridge.send('getBranches', { filePath });
            } catch (_) {}
        }

        this._view.webview.postMessage({
            command: 'setData',
            recordings,
            branches,
            filePath
        });
    }

    private _getHtml(webview: vscode.Webview): string {
        const scriptUri = webview.asWebviewUri(
            vscode.Uri.joinPath(this._extensionUri, 'media', 'recordingViewer.js')
        );
        const styleUri = webview.asWebviewUri(
            vscode.Uri.joinPath(this._extensionUri, 'media', 'recordingViewer.css')
        );
        const nonce = getNonce();
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
    <div class="scrubber-row">
      <button class="nav-btn" id="btn-back">&#9664;</button>
      <button class="nav-btn pause-btn" id="btn-pause">&#9646;&#9646;</button>
      <div class="dots-track" id="dots-track"></div>
      <button class="nav-btn" id="btn-fwd">&#9654;</button>
    </div>
    <div class="scrubber-labels">
      <span>Diff Points</span>
      <span id="change-count">0 changes</span>
    </div>
    <div class="actions-row">
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
