import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

export class FileSelectorPanel {
    public static currentPanel: FileSelectorPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];
    private _selectedFiles = new Set<string>();

    public static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (FileSelectorPanel.currentPanel) {
            FileSelectorPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'watercodeflow.fileSelector', 'Select Files', column,
            { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] }
        );
        FileSelectorPanel.currentPanel = new FileSelectorPanel(panel, extensionUri, bridge);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, private bridge: GlueBridge) {
        this._panel = panel;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'ready':
                    await this._pushFiles();
                    break;
                case 'toggleFile':
                    if (this._selectedFiles.has(msg.filePath)) {
                        this._selectedFiles.delete(msg.filePath);
                    } else {
                        this._selectedFiles.add(msg.filePath);
                    }
                    this._panel.webview.postMessage({ command: 'updateSelected', selected: Array.from(this._selectedFiles) });
                    break;
            }
        });
    }

    private async _pushFiles() {
        const folders = vscode.workspace.workspaceFolders;
        let files: Array<{ name: string; path: string; branch: string; selected: boolean }> = [];

        if (folders && folders.length > 0) {
            // Scan workspace for Python/JS files
            const rootPath = folders[0].uri.fsPath;
            try {
                const found = await vscode.workspace.findFiles(
                    '**/*.{py,js,ts,json,yaml,yml,sh,cpp,c,java,rb,go}',
                    '{**/node_modules/**,**/.git/**,**/__pycache__/**,**/build/**}',
                    100
                );
                files = found.map(uri => ({
                    name: path.basename(uri.fsPath),
                    path: path.relative(rootPath, uri.fsPath),
                    branch: 'main',
                    selected: this._selectedFiles.has(uri.fsPath)
                }));
            } catch (_) {}
        }

        // Fallback to demo data if no workspace
        if (files.length === 0) {
            files = [
                { name: 'app.py',       path: 'src/app.py',       branch: 'main',      selected: false },
                { name: 'src/app.py',   path: 'src/app.py',       branch: 'feather',   selected: true  },
                { name: 'data.py',      path: 'db/data.py',       branch: 'feature-a', selected: false },
                { name: 'utils.js',     path: 'utils.js',         branch: 'master',    selected: true  },
                { name: 'tests.py',     path: 'tests/tests.py',   branch: 'fix-bug',   selected: false },
                { name: 'config.json',  path: 'config.json',      branch: 'dev',       selected: false },
                { name: 'index.html',   path: 'index.html',       branch: 'release',   selected: false },
            ];
        }

        this._panel.webview.postMessage({ command: 'setFiles', files });
    }

    public dispose() {
        FileSelectorPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) this._disposables.pop()?.dispose();
    }

    private _getHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'fileSelector.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'fileSelector.css'));
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
  <div class="fs-container">
    <div class="search-wrap">
      <span class="search-icon">&#x1f50d;</span>
      <input type="text" id="file-filter" class="file-filter" placeholder="Enter file path..." />
    </div>
    <p class="hint-text">Type to filter files by name or path.</p>
    <div class="file-list" id="file-list"><div class="loading">Loading...</div></div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
