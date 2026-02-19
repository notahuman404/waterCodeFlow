import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

export class InsightsPanel {
    public static currentPanel: InsightsPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];
    private _extensionUri: vscode.Uri;

    public static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (InsightsPanel.currentPanel) {
            InsightsPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'watercodeflow.insights', 'Insights', column,
            { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] }
        );
        InsightsPanel.currentPanel = new InsightsPanel(panel, extensionUri, bridge);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, private bridge: GlueBridge) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'ready') {
                await this._pushBranchData(extensionUri);
            } else if (msg.command === 'getInsights') {
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
                } catch (e: any) {
                    vscode.window.showErrorMessage('Get insights failed: ' + e.message);
                }
            }
        });
    }

    private async _pushBranchData(extensionUri: vscode.Uri) {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        const extPath = extensionUri.fsPath;
        // extPath IS the extension root
        const projectRoot = extPath;
        
        let recordings: any[] = [];
        let branches: any[] = [];

        // Load disk recordings
        const recordingsDir = path.join(projectRoot, 'built', 'recordings');
        try {
            if (fs.existsSync(recordingsDir)) {
                const files = fs.readdirSync(recordingsDir)
                    .filter(f => f.endsWith('.json'))
                    .sort()
                    .reverse();
                recordings = files.map(f => {
                    try { return JSON.parse(fs.readFileSync(path.join(recordingsDir, f), 'utf8')); }
                    catch (_) { return null; }
                }).filter(Boolean);
            }
        } catch (_) {}

        // Try to get branches from glue
        if (fp) {
            try {
                branches = await this.bridge.send('getBranches', { filePath: fp });
            } catch (_) {}
        }

        this._panel.webview.postMessage({
            command: 'setData',
            recordings,
            branches
        });
    }

    public dispose() {
        InsightsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) { this._disposables.pop()?.dispose(); }
    }

    private _getHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'insights.js'));
        const styleUri  = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'insights.css'));
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
