import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

export class VariablesViewProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    private _trackState: Record<string, { tracked: boolean; mode: 'single'|'multi'; runs: number }> = {};

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
                    if (runs !== undefined) s.runs = runs;
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

    private async _pushVars() {
        if (!this._view) return;
        const editor = vscode.window.activeTextEditor;
        const filePath = editor?.document.fileName || '';
        let vars: any[] = [];

        if (filePath) {
            try {
                const inferred: any[] = await this._bridge.send('getVariableTimeline', {
                    filePath,
                    variableName: '_all_vars_',
                    maxTicks: 1
                });
                // inferred may be empty — fall through to infer_from_file
            } catch (_) {}

            // Use Python-side infer_variables_from_file via a separate call
            try {
                // We call listTrackedVariables which gives us config-tracked vars
                const tracked: any[] = await this._bridge.send('listTrackedVariables', { filePath });
                vars = tracked.map((v: any) => ({
                    name: typeof v === 'string' ? v : v.name,
                    file: filePath,
                    scope: (typeof v === 'object' && v.scope) ? v.scope : 'global',
                    line_no: v.line_no || 0
                }));
            } catch (_) {}
        }

        // Always send something — if no real data, show placeholder sections
        this._view.webview.postMessage({
            command: 'setVars',
            filePath,
            vars,
            trackState: this._trackState
        });
    }

    private _getHtml(webview: vscode.Webview): string {
        const scriptUri = webview.asWebviewUri(
            vscode.Uri.joinPath(this._extensionUri, 'media', 'variables.js')
        );
        const styleUri = webview.asWebviewUri(
            vscode.Uri.joinPath(this._extensionUri, 'media', 'variables.css')
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
