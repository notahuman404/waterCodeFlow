import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

const TRACK_STATE_KEY = 'watercodeflow.trackState';

export class VariablesViewProvider implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    private _trackState: Record<string, { tracked: boolean; mode: 'single'|'multi'; runs: number }> = {};

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly _bridge: GlueBridge,
        private readonly _context: vscode.ExtensionContext
    ) {
        // Restore persisted track state
        this._trackState = this._context.globalState.get<typeof this._trackState>(TRACK_STATE_KEY, {});
    }

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
                    // IMPORTANT: Variable tracking is UI-ONLY.
                    // Variables come from RUN RECORDINGS (watcher mutations), not daemon.
                    // This toggle just marks which variables the user wants to see.
                    const { name } = msg;
                    const s = this._trackState[name] || { tracked: false, mode: 'multi', runs: 5 };
                    s.tracked = !s.tracked;
                    this._trackState[name] = s;
                    // Persist trackState for next session
                    await this._context.globalState.update(TRACK_STATE_KEY, this._trackState);
                    webviewView.webview.postMessage({ command: 'trackState', name, state: s });
                    break;
                }

                case 'setTrackMode': {
                    const { name, mode, runs } = msg;
                    const s = this._trackState[name] || { tracked: true, mode: 'multi', runs: 5 };
                    s.mode = mode;
                    if (runs !== undefined) { s.runs = runs; }
                    this._trackState[name] = s;
                    await this._context.globalState.update(TRACK_STATE_KEY, this._trackState);
                    break;
                }

                case 'refresh':
                    await this._pushVars();
                    break;
            }
        }, null, []);

        // Refresh when active editor changes — tracked so it's disposed with the view
        this._context.subscriptions.push(
            vscode.window.onDidChangeActiveTextEditor(() => this._pushVars())
        );

        // Also refresh when the sidebar panel becomes visible after being hidden
        webviewView.onDidChangeVisibility(() => {
            if (webviewView.visible) { this._pushVars(); }
        });
    }

    private async _pushVars() {
        if (!this._view) { return; }
        const editor = vscode.window.activeTextEditor;
        const filePath = editor?.document.fileName || '';
        let vars: any[] = [];

        if (filePath) {
            // 1. Try to get variables from tracked recordings (timeline approach)
            try {
                const inferred: any[] = await this._bridge.send('getVariableTimeline', {
                    filePath,
                    variableName: '_all_vars_',
                    maxTicks: 1
                });
                if (Array.isArray(inferred) && inferred.length > 0) {
                    vars = inferred.map((v: any) => ({
                        name: typeof v === 'string' ? v : (v.name || String(v)),
                        file: filePath,
                        scope: (typeof v === 'object' && v.scope) ? v.scope : 'global',
                        line_no: v.line_no || 0
                    }));
                }
            } catch (e) {
                console.warn('getVariableTimeline failed:', e);
            }

            // 2. If no timeline data, try listTrackedVariables
            if (vars.length === 0) {
                try {
                    const tracked: any[] = await this._bridge.send('listTrackedVariables', { filePath });
                    if (Array.isArray(tracked) && tracked.length > 0) {
                        vars = tracked.map((v: any) => ({
                            name: typeof v === 'string' ? v : v.name,
                            file: filePath,
                            scope: (typeof v === 'object' && v.scope) ? v.scope : 'global',
                            line_no: v.line_no || 0
                        }));
                    }
                } catch (e) {
                    console.warn('listTrackedVariables failed:', e);
                }
            }
        }

        // Send real data (or empty list — no mock fallback)
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
