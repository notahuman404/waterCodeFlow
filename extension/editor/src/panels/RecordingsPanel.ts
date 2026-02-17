import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

export class RecordingsPanel {
    public static currentPanel: RecordingsPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (RecordingsPanel.currentPanel) {
            RecordingsPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'watercodeflow.recordings', 'Recordings', column,
            { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] }
        );
        RecordingsPanel.currentPanel = new RecordingsPanel(panel, extensionUri, bridge);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, private bridge: GlueBridge) {
        this._panel = panel;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'ready':
                    await this._pushData();
                    break;
                case 'openRunInspector':
                    vscode.commands.executeCommand('watercodeflow.openRunInspector');
                    break;
                case 'openVariableInspector':
                    vscode.commands.executeCommand('watercodeflow.openInspector');
                    break;
                case 'deleteRun': {
                    const fp = vscode.window.activeTextEditor?.document.fileName || '';
                    if (fp) {
                        try {
                            await this.bridge.send('deleteRun', { filePath: fp, runId: msg.runId });
                            await this._pushData();
                        } catch (e: any) {
                            vscode.window.showErrorMessage('Delete run failed: ' + e.message);
                        }
                    }
                    break;
                }
            }
        });
    }

    private async _pushData() {
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        let trackedFiles: any[] = [];
        let vars: any[] = [];
        let runs: any[] = [];

        if (fp) {
            try {
                const recs = await this.bridge.send('listRecordings', { filePath: fp }) as any[];
                trackedFiles = recs.length > 0 ? [{ name: fp.split('/').pop() || fp, path: fp }] : [];
            } catch (_) {}

            try {
                vars = await this.bridge.send('listTrackedVariables', { filePath: fp }) as any[];
            } catch (_) {}

            try {
                runs = await this.bridge.send('listRuns', { filePath: fp }) as any[];
            } catch (_) {}
        }

        // Fallback demo data if nothing from glue
        if (trackedFiles.length === 0) {
            trackedFiles = [
                { name: 'main.py', path: './src/main.py' },
                { name: 'utils.py', path: './src/utils.py' },
                { name: 'data_proc.py', path: './src/data_proc.py' }
            ];
        }
        if (vars.length === 0) {
            vars = [
                { name: 'counter', evolutions: 5 },
                { name: 'total_sum', evolutions: 8 },
                { name: 'status', evolutions: 3 },
                { name: 'data_buffer', evolutions: 6 }
            ];
        }
        if (runs.length === 0) {
            runs = [
                { run_id: 4, tick_count: 7 },
                { run_id: 3, tick_count: 3 },
                { run_id: 2, tick_count: 2 }
            ];
        }

        this._panel.webview.postMessage({ command: 'setData', trackedFiles, vars, runs });
    }

    public dispose() {
        RecordingsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) this._disposables.pop()?.dispose();
    }

    private _getHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'recordings.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'recordings.css'));
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
  <div class="recordings-container" id="recordings-container"><div class="loading">Loading...</div></div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
