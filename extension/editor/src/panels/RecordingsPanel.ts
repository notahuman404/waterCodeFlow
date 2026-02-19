import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

/** Parse watcher JSONL events and merge variables into an existing recording object. */
function enrichRecordingWithVars(rec: any, extPath: string): any {
    const runId = rec.runId || rec.run_id;
    if (!runId || rec.vars) { return rec; }
    const projectRoot = extPath;
    const watcherDir = path.join(projectRoot, 'built', 'watcher_events', runId);
    if (!fs.existsSync(watcherDir)) { return rec; }
    const varMap: Record<string, any> = {};
    try {
        fs.readdirSync(watcherDir).filter(f => f.endsWith('.jsonl')).forEach(file => {
            fs.readFileSync(path.join(watcherDir, file), 'utf8')
                .split('\n').filter(Boolean).forEach(line => {
                    try {
                        const evt = JSON.parse(line);
                        const name = evt.variable || evt.name;
                        if (name) {
                            varMap[name] = {
                                name,
                                value: evt.value ?? evt.new_value ?? null,
                                scope: evt.scope || 'global',
                                type: evt.type || typeof evt.value,
                                line_no: evt.line_no || evt.lineno || 0,
                                evolutions: (varMap[name]?.evolutions ?? 0) + 1,
                            };
                        }
                    } catch (_) {}
                });
        });
    } catch (_) {}
    return Object.keys(varMap).length > 0 ? { ...rec, vars: Object.values(varMap) } : rec;
}

export class RecordingsPanel implements vscode.WebviewViewProvider {
    public static currentPanel: RecordingsPanel | undefined;
    private _view?: vscode.WebviewView;
    private _disposables: vscode.Disposable[] = [];
    private _extensionUri: vscode.Uri;
    private _lastPushedFilePath: string = '';

    constructor(extensionUri: vscode.Uri, private bridge: GlueBridge, private context: vscode.ExtensionContext) {
        this._extensionUri = extensionUri;
        RecordingsPanel.currentPanel = this;
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

        webviewView.webview.onDidReceiveMessage(async (msg: any) => {
            switch (msg.command) {
                case 'ready':
                    await this._pushData();
                    break;

                case 'openRunInspector':
                    vscode.commands.executeCommand('watercodeflow.openRunInspector', { runId: msg.runId });
                    break;

                case 'openVariableInspector':
                    vscode.commands.executeCommand('watercodeflow.openInspector', { varName: msg.varName });
                    break;

                case 'openFileRecording':
                    vscode.commands.executeCommand('watercodeflow.recordingViewer.focus');
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

                case 'deleteRecording': {
                    const extPath = this._extensionUri.fsPath;
                    const projectRoot = extPath;
                    const recordingsDir = path.join(projectRoot, 'built', 'recordings');
                    try {
                        if (fs.existsSync(recordingsDir)) {
                            const files = fs.readdirSync(recordingsDir);
                            const match = files.find(f => f.startsWith(msg.runId) || f === `${msg.runId}.json`);
                            if (match) {
                                fs.unlinkSync(path.join(recordingsDir, match));
                            }
                        }
                    } catch (_) {}
                    this.bridge.send('deleteRecording', { runId: msg.runId }).catch((e: any) => {
                        console.warn('deleteRecording glue call failed:', e.message);
                    });
                    await this._pushData();
                    break;
                }

                case 'exportRecording': {
                    const rec = msg.recording;
                    if (!rec) { break; }
                    const uri = await vscode.window.showSaveDialog({
                        defaultUri: vscode.Uri.file(`recording-${rec.runId || 'export'}.json`),
                        filters: { 'JSON': ['json'] }
                    });
                    if (uri) {
                        fs.writeFileSync(uri.fsPath, JSON.stringify(rec, null, 2));
                        vscode.window.showInformationMessage(`Recording exported to ${uri.fsPath}`);
                    }
                    break;
                }
            }
        });
    }

    public postRunEvent(type: string, data: string) {
        this._view?.webview.postMessage({ command: 'run.event', type, data });
    }

    private async _pushData() {
        if (!this._view) { return; }
        const fp = vscode.window.activeTextEditor?.document.fileName || '';
        const extPath = this._extensionUri.fsPath;
        const projectRoot = extPath;

        let recordings: any[] = [];
        const recordingsDir = path.join(projectRoot, 'built', 'recordings');
        try {
            if (fs.existsSync(recordingsDir)) {
                const files = fs.readdirSync(recordingsDir)
                    .filter(f => f.endsWith('.json'))
                    .sort()
                    .reverse();
                recordings = files.map(f => {
                    try {
                        const rec = JSON.parse(fs.readFileSync(path.join(recordingsDir, f), 'utf8'));
                        return enrichRecordingWithVars(rec, extPath);
                    } catch (_) { return null; }
                }).filter(Boolean);
            }
        } catch (_) {}

        if (fp) {
            try {
                const daemonRuns = await this.bridge.send('listRuns', { filePath: fp }) as any[];
                if (Array.isArray(daemonRuns) && daemonRuns.length > 0) {
                    const existingIds = new Set(recordings.map((r: any) => r.runId || r.run_id));
                    for (const run of daemonRuns) {
                        if (!existingIds.has(run.runId) && !existingIds.has(run.run_id)) {
                            recordings.push(run);
                        }
                    }
                }
            } catch (_) {}
        }

        const seen = new Set<string>();
        const trackedFiles: any[] = [];
        recordings.forEach(r => {
            const p = r.filePath || r.file_path || '';
            if (p && !seen.has(p)) {
                seen.add(p);
                trackedFiles.push({ name: path.basename(p), path: p });
            }
        });

        if (fp && !seen.has(fp)) {
            try {
                const recs = await this.bridge.send('listRecordings', { filePath: fp }) as any[];
                if (recs && recs.length > 0) {
                    trackedFiles.unshift({ name: path.basename(fp), path: fp });
                }
            } catch (_) {}
        }

        let vars: any[] = [];
        if (fp) {
            try {
                vars = await this.bridge.send('listTrackedVariables', { filePath: fp }) as any[];
                if (!Array.isArray(vars)) { vars = []; }
            } catch (_) {}
        }

        const resetFilter = this._lastPushedFilePath !== fp;
        this._lastPushedFilePath = fp;

        this._view.webview.postMessage({
            command: 'setData',
            trackedFiles,
            vars,
            runs: [],
            recordings,
            filePath: fp,
            _resetFilter: resetFilter,
        });
    }

    public dispose() {
        RecordingsPanel.currentPanel = undefined;
        while (this._disposables.length) { this._disposables.pop()?.dispose(); }
    }

    private _getHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'recordings.js'));
        const styleUri  = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'recordings.css'));
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
  <div class="recordings-container" id="recordings-container"><div class="loading">Loading…</div></div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
