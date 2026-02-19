import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

export class RunInspectorPanel {
    public static currentPanel: RunInspectorPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (RunInspectorPanel.currentPanel) {
            RunInspectorPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'watercodeflow.runInspector', 'Run Inspector', column,
            { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] }
        );
        RunInspectorPanel.currentPanel = new RunInspectorPanel(panel, extensionUri, bridge);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, private bridge: GlueBridge) {
        this._panel = panel;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'ready') {
                await this._pushRunData(extensionUri);

            } else if (msg.command === 'close') {
                this.dispose();

            } else if (msg.command === 'jumpToTick') {
                const fp = vscode.window.activeTextEditor?.document.fileName || '';
                if (fp && msg.tickId !== undefined) {
                    try {
                        await this.bridge.send('jumpToTick', { filePath: fp, tickId: msg.tickId });
                    } catch (e: any) {
                        vscode.window.showErrorMessage('Jump failed: ' + e.message);
                    }
                }
            } else if (msg.command === 'openVariableInspector') {
                vscode.commands.executeCommand('watercodeflow.openInspector', { varName: msg.varName });
            }
        });
    }

    private async _pushRunData(extensionUri: vscode.Uri) {
        const fp      = vscode.window.activeTextEditor?.document.fileName || '';
        const extPath = extensionUri.fsPath;
        // extPath IS the extension root
        const projectRoot = extPath;
        let recordings: any[] = [];

        // Load disk recordings as the primary source
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

                if (fp) {
                    const forFile = recordings.filter(r => (r.filePath || r.file_path || '') === fp);
                    if (forFile.length > 0) { recordings = forFile; }
                }
            }
        } catch (_) {}

        // Enrich with watcher event variable data
        recordings = recordings.map(rec => enrichRecording(rec, extPath));

        this._panel.webview.postMessage({ command: 'setData', recordings, filePath: fp });
    }

    public dispose() {
        RunInspectorPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) { this._disposables.pop()?.dispose(); }
    }

    private _getHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'runInspector.js'));
        const styleUri  = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'runInspector.css'));
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
  <div class="ri-header">
    <button class="ri-back-btn" id="ri-back">✕ Close</button>
    <span class="ri-title" id="ri-run-title">Run Inspector</span>
    <span class="ri-status" id="ri-status"></span>
  </div>
  <hr class="ri-divider" />
  <div class="ri-context-bar">
    <span class="ri-line-no" id="ri-lineno">File:</span>
    <span class="ri-file-path" id="ri-filepath">—</span>
    <button class="ri-open-vi-btn" id="ri-open-vi">Open Variable Inspector</button>
  </div>
  <hr class="ri-divider" />
  <div class="ri-body">
    <div class="ri-left" id="ri-left"><div class="loading">Loading…</div></div>
    <div class="ri-right">
      <div class="ri-meta-header">Variable Metadata</div>
      <div id="ri-meta-blocks"></div>
    </div>
  </div>
  <div class="ri-timeline">
    <div class="ri-step-badge" id="ri-step-badge">No runs yet</div>
    <div class="ri-dots" id="ri-dots"></div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}

function enrichRecording(rec: any, extPath: string): any {
    const runId = rec.runId || rec.run_id;
    if (!runId || rec.vars) { return rec; }
    // extPath IS the extension root
    const projectRoot = extPath;
    const watcherDir = path.join(projectRoot, 'built', 'watcher_events', runId);
    if (!fs.existsSync(watcherDir)) { return rec; }

    // varMap stores an array of mutations per variable
    const varMap: Record<string, any[]> = {};
    const allMutations: any[] = []; // for global scrollbar

    try {
        const files = fs.readdirSync(watcherDir).filter(f => f.endsWith('.jsonl'));
        for (const file of files) {
            const content = fs.readFileSync(path.join(watcherDir, file), 'utf8');
            const lines = content.split('\n').filter(Boolean);
            for (const line of lines) {
                try {
                    const evt = JSON.parse(line);
                    const name = evt.variable || evt.name;
                    if (name) {
                        const mutation = {
                            name,
                            value: evt.value ?? evt.new_value ?? null,
                            scope: evt.scope || 'global',
                            type:  evt.type || typeof evt.value,
                            line_no: evt.line_no || evt.lineno || 0,
                            ts_ns: evt.ts_ns || 0,
                            file: evt.file || ''
                        };
                        if (!varMap[name]) varMap[name] = [];
                        varMap[name].push(mutation);
                        allMutations.push(mutation);
                    }
                } catch (_) {}
            }
        }
    } catch (_) {}

    // Sort mutations by timestamp
    allMutations.sort((a, b) => a.ts_ns - b.ts_ns);
    for (const name in varMap) {
        varMap[name].sort((a, b) => a.ts_ns - b.ts_ns);
    }

    const varList = Object.keys(varMap).map(name => ({
        name,
        mutations: varMap[name],
        last_mutation: varMap[name][varMap[name].length - 1]
    }));

    return varList.length > 0 ? { ...rec, vars: varList, all_mutations: allMutations } : rec;
}
