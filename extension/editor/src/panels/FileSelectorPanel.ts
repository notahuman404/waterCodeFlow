import * as vscode from 'vscode';
import * as path from 'path';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

const STORAGE_KEY = 'watercodeflow.trackedFiles';

export class FileSelectorPanel implements vscode.WebviewViewProvider {
    public static currentPanel: FileSelectorPanel | undefined;
    private _view?: vscode.WebviewView;
    private _disposables: vscode.Disposable[] = [];
    private _selectedFiles: Set<string>;
    private _outputChannel: vscode.OutputChannel;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private bridge: GlueBridge,
        private context: vscode.ExtensionContext
    ) {
        this._outputChannel = vscode.window.createOutputChannel('WaterCodeFlow: Daemon');
        const saved: string[] = context.globalState.get<string[]>(STORAGE_KEY, []) ?? [];
        this._selectedFiles = new Set(saved);
        FileSelectorPanel.currentPanel = this;
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
        webviewView.webview.html = this._getHtml(webviewView.webview, this._extensionUri);

        webviewView.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'ready':
                    await this._pushFiles();
                    break;

                case 'toggleFile': {
                    const fp = msg.filePath as string;
                    const fileName = path.basename(fp);
                    
                    if (this._selectedFiles.has(fp)) {
                        this._outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] STOP tracking: ${fp}`);
                        this._selectedFiles.delete(fp);
                        try {
                            const result = await this.bridge.send('stopRecording', { filePath: fp });
                            this._outputChannel.appendLine(`  → Result: ${JSON.stringify(result)}`);
                            vscode.window.showInformationMessage(`✓ Stopped tracking: ${fileName}`);
                        } catch (e: any) {
                            this._outputChannel.appendLine(`  ✗ ERROR: ${e.message}`);
                            vscode.window.showErrorMessage(`Failed to stop tracking: ${e.message}`);
                        }
                    } else {
                        this._outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] START tracking: ${fp}`);
                        this._outputChannel.show(true);
                        
                        this._selectedFiles.add(fp);
                        const cfg = vscode.workspace.getConfiguration('watercodeflow');
                        const interval = cfg.get('samplingInterval', 0.5);
                        const threads = cfg.get('daemonThreads', 4);
                        
                        this._outputChannel.appendLine(`  Config: interval=${interval}s, threads=${threads}`);
                        
                        try {
                            const result = await this.bridge.send('startRecording', {
                                filePath: fp,
                                interval: interval,
                                numThreads: threads,
                            });
                            
                            const pid: number | null =
                                typeof result === 'number' ? result
                                : (result?.pid ?? result?.daemon_pid ?? null);

                            if (pid) {
                                this._outputChannel.appendLine(`  ✓ Daemon started with PID: ${pid}`);
                                vscode.window.showInformationMessage(
                                    `✓ Started tracking: ${fileName}  |  Daemon PID: ${pid}`
                                );
                            } else {
                                this._outputChannel.appendLine(`  ⚠ No PID returned`);
                                vscode.window.showWarningMessage(`Started tracking ${fileName} but no PID returned.`);
                            }
                        } catch (e: any) {
                            this._outputChannel.appendLine(`  ✗ ERROR: ${e.message}`);
                            this._selectedFiles.delete(fp);
                            vscode.window.showErrorMessage(`Failed to start tracking: ${e.message}`);
                        }
                    }
                    
                    await this.context.globalState.update(STORAGE_KEY, Array.from(this._selectedFiles));
                    this._view?.webview.postMessage({
                        command: 'updateSelected',
                        selected: Array.from(this._selectedFiles)
                    });
                    break;
                }

                case 'clearAll': {
                    const failures: string[] = [];
                    for (const fp of this._selectedFiles) {
                        try {
                            await this.bridge.send('stopRecording', { filePath: fp });
                        } catch (e: any) {
                            failures.push(path.basename(fp));
                        }
                    }
                    this._selectedFiles.clear();
                    await this.context.globalState.update(STORAGE_KEY, []);
                    this._view?.webview.postMessage({ command: 'updateSelected', selected: [] });
                    break;
                }
            }
        });
    }

    private async _pushFiles() {
        if (!this._view) return;
        const folders = vscode.workspace.workspaceFolders;
        let files: Array<{ name: string; path: string; displayPath: string; branch: string; selected: boolean }> = [];

        if (folders && folders.length > 0) {
            const rootPath = folders[0].uri.fsPath;
            try {
                const found = await vscode.workspace.findFiles(
                    '**/*.{py,js,ts,json,yaml,yml,sh,cpp,c,java,rb,go}',
                    '{**/node_modules/**,**/.git/**,**/__pycache__/**,**/build/**}',
                    200
                );
                files = found.map(uri => ({
                    name: path.basename(uri.fsPath),
                    path: uri.fsPath,
                    displayPath: path.relative(rootPath, uri.fsPath),
                    branch: 'main',
                    selected: this._selectedFiles.has(uri.fsPath)
                }));
            } catch (_) {}
        }

        this._view.webview.postMessage({ command: 'setFiles', files });
    }

    public dispose() {
        FileSelectorPanel.currentPanel = undefined;
        this._outputChannel.dispose();
        while (this._disposables.length) { this._disposables.pop()?.dispose(); }
    }

    private _getHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'fileSelector.js'));
        const styleUri  = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'fileSelector.css'));
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
      <input type="text" id="file-filter" class="file-filter" placeholder="Filter by name or path..." />
    </div>
    <div class="fs-toolbar">
      <p class="hint-text">Select files for daemon tracking. Changes appear in the sidebar scrubber.</p>
      <button id="clear-all-btn" class="clear-btn">Clear All</button>
    </div>
    <div class="file-list" id="file-list"><div class="loading">Loading...</div></div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
