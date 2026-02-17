import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

export class InsightsPanel {
    public static currentPanel: InsightsPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (InsightsPanel.currentPanel) {
            InsightsPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'watercodeflow.insights', 'Insight selection', column,
            { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] }
        );
        InsightsPanel.currentPanel = new InsightsPanel(panel, extensionUri, bridge);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, private bridge: GlueBridge) {
        this._panel = panel;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'ready') {
                await this._pushBranchData();
            } else if (msg.command === 'getInsights') {
                const fp = vscode.window.activeTextEditor?.document.fileName || '';
                if (!fp) {
                    vscode.window.showWarningMessage('Open a tracked file first.');
                    return;
                }
                try {
                    const cfg = vscode.workspace.getConfiguration('watercodeflow');
                    const model = cfg.get<string>('aiModel', 'Gemini');
                    const result = await this.bridge.send('getInsights', {
                        filePath: fp,
                        fromTick: msg.fromTick,
                        toTick: msg.toTick,
                        model
                    });
                    this._panel.webview.postMessage({ command: 'insightsResult', result });
                } catch (e: any) {
                    this._panel.webview.postMessage({ command: 'insightsError', error: e.message });
                }
            }
        });
    }

    private async _pushBranchData() {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        let branches: any[] = [];
        let recordings: any[] = [];

        if (fp) {
            try { branches = await this.bridge.send('getBranches', { filePath: fp }); } catch (_) {}
            try { recordings = await this.bridge.send('listRecordings', { filePath: fp }); } catch (_) {}
        }

        this._panel.webview.postMessage({ command: 'setBranchData', branches, recordings });
    }

    public dispose() {
        InsightsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) this._disposables.pop()?.dispose();
    }

    private _getHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'insights.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'insights.css'));
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
