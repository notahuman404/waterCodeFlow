import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
import { getNonce } from '../utils';

export class SettingsPanel {
    public static currentPanel: SettingsPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge) {
        const column = vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One;
        if (SettingsPanel.currentPanel) {
            SettingsPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'watercodeflow.settings', 'Watcher Settings', column,
            { enableScripts: true, localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')] }
        );
        SettingsPanel.currentPanel = new SettingsPanel(panel, extensionUri, bridge);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, private bridge: GlueBridge) {
        this._panel = panel;
        this._panel.webview.html = this._getHtml(panel.webview, extensionUri);
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(async (msg) => {
            if (msg.command === 'saveSettings') {
                // Persist settings via extension configuration
                const cfg = vscode.workspace.getConfiguration('watercodeflow');
                await cfg.update('trackThreads', msg.trackThreads, vscode.ConfigurationTarget.Global);
                await cfg.update('trackLocals', msg.trackLocals, vscode.ConfigurationTarget.Global);
                await cfg.update('trackSql', msg.trackSql, vscode.ConfigurationTarget.Global);
                await cfg.update('trackAll', msg.trackAll, vscode.ConfigurationTarget.Global);
                await cfg.update('samplingInterval', msg.samplingInterval, vscode.ConfigurationTarget.Global);
                await cfg.update('daemonThreads', msg.daemonThreads, vscode.ConfigurationTarget.Global);
                await cfg.update('aiModel', msg.aiModel, vscode.ConfigurationTarget.Global);
                await cfg.update('logLevel', msg.logLevel, vscode.ConfigurationTarget.Global);
                vscode.window.showInformationMessage('WaterCodeFlow: Settings saved.');
            }
        });

        // Push saved settings to webview
        const cfg = vscode.workspace.getConfiguration('watercodeflow');
        this._panel.webview.postMessage({
            command: 'loadSettings',
            settings: {
                trackThreads: cfg.get('trackThreads', true),
                trackLocals: cfg.get('trackLocals', false),
                trackSql: cfg.get('trackSql', true),
                trackAll: cfg.get('trackAll', true),
                samplingInterval: cfg.get('samplingInterval', 0.5),
                daemonThreads: cfg.get('daemonThreads', 4),
                aiModel: cfg.get('aiModel', 'Gemini'),
                logLevel: cfg.get('logLevel', 'INFO')
            }
        });
    }

    public dispose() {
        SettingsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) this._disposables.pop()?.dispose();
    }

    private _getHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'settings.js'));
        const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'media', 'settings.css'));
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
  <div class="settings-container">
    <h1 class="settings-title">Watcher Settings</h1>
    <div class="settings-section">
      <div class="toggle-row"><span class="toggle-label">Track Threads</span><label class="toggle"><input type="checkbox" id="trackThreads" checked><span class="slider"></span></label></div>
      <div class="toggle-row"><span class="toggle-label">Track Locals</span><label class="toggle"><input type="checkbox" id="trackLocals"><span class="slider"></span></label></div>
      <div class="toggle-row"><span class="toggle-label">Track SQL</span><label class="toggle"><input type="checkbox" id="trackSql" checked><span class="slider"></span></label></div>
      <div class="toggle-row"><span class="toggle-label">Track All</span><label class="toggle"><input type="checkbox" id="trackAll" checked><span class="slider"></span></label></div>
      <div class="control-row"><label class="control-label">Mutation Depth</label><select class="control-input" id="mutationDepth"><option>Custom &amp; Full</option><option>Custom</option><option>Full</option><option>Shallow</option></select></div>
      <div class="control-row"><label class="control-label">Files Scope</label><input type="text" class="control-input" id="filesScope" value="List of Files" /></div>
      <div class="control-row"><label class="control-label">Max Queue Size</label><input type="number" class="control-input" id="maxQueueSize" value="1000" min="1" /></div>
      <div class="control-row"><label class="control-label">Log Level</label><select class="control-input" id="logLevel"><option>INFO</option><option>DEBUG</option></select></div>
      <div class="control-row"><label class="control-label">Custom Processor</label><div class="input-with-btn"><input type="text" class="control-input flex1" id="customProcessor" placeholder="Attach..." /><button class="folder-btn" id="browseBtn">&#128193;</button></div></div>
    </div>
    <h2 class="section-header">Code Volvo (Recording) Settings</h2>
    <div class="settings-section">
      <div class="control-row"><label class="control-label">Sampling Interval</label><div class="input-hint-row"><input type="number" class="control-input control-input-sm" id="samplingInterval" value="0.5" step="0.1" min="0.01" /><span class="hint-text">hint timing</span><span class="unit-text">s</span></div></div>
      <div class="control-row"><label class="control-label">Daemon Threads</label><input type="number" class="control-input" id="daemonThreads" value="4" min="1" max="32" /></div>
      <div class="control-row"><label class="control-label">AI Model</label><select class="control-input" id="aiModel"><option>Gemini</option><option>ChatGPT</option><option>Claude</option></select></div>
      <div class="control-row"><label class="control-label">Recording Mode</label><div class="btn-group"><button class="mode-btn mode-btn-outline" id="resetBtn">Reset</button><button class="mode-btn mode-btn-filled" id="bgBtn">Background</button></div></div>
    </div>
    <div class="save-row"><button class="save-btn" id="saveBtn">Save Settings</button></div>
  </div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
    }
}
