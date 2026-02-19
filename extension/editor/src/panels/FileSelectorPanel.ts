import * as vscode from 'vscode';
import * as path from 'path';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

const STORAGE_KEY = 'watercodeflow.trackedFiles';

export class FileSelectorPanel {
    public static currentPanel: FileSelectorPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];
    private _selectedFiles: Set<string>;
    private _outputChannel: vscode.OutputChannel;

    public static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge, context?: vscode.ExtensionContext) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (FileSelectorPanel.currentPanel) {
            FileSelectorPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'watercodeflow.fileSelector', 'Select Files to Track', column,
            { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] }
        );
        FileSelectorPanel.currentPanel = new FileSelectorPanel(panel, extensionUri, bridge, context);
    }

    private constructor(
        panel: vscode.WebviewPanel,
        extensionUri: vscode.Uri,
        private bridge: GlueBridge,
        private context?: vscode.ExtensionContext
    ) {
        this._panel = panel;
        this._outputChannel = vscode.window.createOutputChannel('WaterCodeFlow: Daemon');
        
        // Restore persisted selections
        const saved: string[] = context?.globalState.get<string[]>(STORAGE_KEY, []) ?? [];
        this._selectedFiles = new Set(saved);

        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'ready':
                    await this._pushFiles();
                    break;

                case 'toggleFile': {
                    const fp = msg.filePath as string;
                    const fileName = path.basename(fp);
                    
                    if (this._selectedFiles.has(fp)) {
                        // Stop tracking
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
                        // Start tracking
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
                            
                            this._outputChannel.appendLine(`  → Result: ${JSON.stringify(result, null, 2)}`);
                            
                            // start_recording returns a plain integer PID — the old check
                            // for result.pid / result.daemon_pid silently failed because
                            // accessing .pid on a number gives undefined.
                            const pid: number | null =
                                typeof result === 'number' ? result
                                : (result?.pid ?? result?.daemon_pid ?? null);

                            if (pid) {
                                this._outputChannel.appendLine(`  ✓ Daemon started with PID: ${pid}`);
                                vscode.window.showInformationMessage(
                                    `✓ Started tracking: ${fileName}  |  Daemon PID: ${pid}`
                                );
                            } else {
                                this._outputChannel.appendLine(`  ⚠ No PID returned — daemon may not have started`);
                                vscode.window.showWarningMessage(
                                    `Started tracking ${fileName} but no daemon PID was returned. ` +
                                    `Check Output › WaterCodeFlow: Daemon for details.`
                                );
                            }
                        } catch (e: any) {
                            this._outputChannel.appendLine(`  ✗ ERROR: ${e.message}`);
                            this._outputChannel.appendLine(`  Stack: ${e.stack || 'no stack'}`);
                            
                            this._selectedFiles.delete(fp); // rollback on failure
                            vscode.window.showErrorMessage(
                                `Failed to start tracking: ${e.message}\n\n` +
                                `Possible causes:\n` +
                                `• CodeVovle core not installed\n` +
                                `• Python dependencies missing\n` +
                                `• File permissions issue\n\n` +
                                `Check: Output > WaterCodeFlow: Daemon`
                            );
                        }
                    }
                    
                    // Persist selection immediately
                    await this.context?.globalState.update(STORAGE_KEY, Array.from(this._selectedFiles));
                    this._panel.webview.postMessage({
                        command: 'updateSelected',
                        selected: Array.from(this._selectedFiles)
                    });
                    break;
                }

                case 'clearAll': {
                    this._outputChannel.appendLine(`\n[${new Date().toLocaleTimeString()}] CLEAR ALL tracking`);
                    const failures: string[] = [];
                    for (const fp of this._selectedFiles) {
                        try {
                            await this.bridge.send('stopRecording', { filePath: fp });
                            this._outputChannel.appendLine(`  ✓ Stopped: ${path.basename(fp)}`);
                        } catch (e: any) {
                            this._outputChannel.appendLine(`  ✗ Failed: ${path.basename(fp)} - ${e.message}`);
                            failures.push(path.basename(fp));
                        }
                    }
                    this._selectedFiles.clear();
                    await this.context?.globalState.update(STORAGE_KEY, []);
                    this._panel.webview.postMessage({ command: 'updateSelected', selected: [] });
                    
                    if (failures.length > 0) {
                        vscode.window.showWarningMessage(
                            `Cleared all selections. Failed to stop: ${failures.join(', ')}`
                        );
                    } else {
                        vscode.window.showInformationMessage('✓ Cleared all file tracking');
                    }
                    break;
                }
            }
        });
    }

    private async _pushFiles() {
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

        this._panel.webview.postMessage({ command: 'setFiles', files });
    }

    public dispose() {
        FileSelectorPanel.currentPanel = undefined;
        this._outputChannel.dispose();
        this._panel.dispose();
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
      <p class="hint-text">Select files for daemon tracking. Changes appear in the sidebar scrubber. Check Output > WaterCodeFlow: Daemon for logs.</p>
      <button id="clear-all-btn" class="clear-btn">Clear All</button>
    </div>
    <div class="file-list" id="file-list"><div class="loading">Loading...</div></div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
