import * as vscode from 'vscode';
import * as path from 'path';
import { GlueBridge } from './GlueBridge';
import { VariablesViewProvider } from './providers/VariablesViewProvider';
import { RecordingViewerProvider } from './providers/RecordingViewerProvider';
import { SettingsPanel } from './panels/SettingsPanel';
import { FileSelectorPanel } from './panels/FileSelectorPanel';
import { RecordingsPanel } from './panels/RecordingsPanel';
import { InsightsPanel } from './panels/InsightsPanel';
import { VariableInspectorPanel } from './panels/VariableInspectorPanel';
import { RunInspectorPanel } from './panels/RunInspectorPanel';

let bridge: GlueBridge;

/** File extensions that get watcher-based variable recording. */
const WATCHER_EXTS = new Set(['.py', '.js', '.mjs']);

/** File extensions that get plain-terminal execution (no variable tracking). */
const PLAIN_EXTS: Record<string, (f: string) => string> = {
    '.c':    f => { const o = f.replace(/\.[^/.]+$/, ''); return `gcc -O1 -o "${o}" "${f}" && "${o}"`; },
    '.cpp':  f => { const o = f.replace(/\.[^/.]+$/, ''); return `g++ -O1 -o "${o}" "${f}" && "${o}"`; },
    '.cc':   f => { const o = f.replace(/\.[^/.]+$/, ''); return `g++ -O1 -o "${o}" "${f}" && "${o}"`; },
    '.cxx':  f => { const o = f.replace(/\.[^/.]+$/, ''); return `g++ -O1 -o "${o}" "${f}" && "${o}"`; },
    '.go':   f => `go run "${f}"`,
    '.rb':   f => `ruby "${f}"`,
    '.sh':   f => `bash "${f}"`,
    '.java': f => { const d = path.dirname(f); const b = path.basename(f, '.java'); return `cd "${d}" && javac "${b}.java" && java "${b}"`; },
    '.rs':   f => { const o = f.replace(/\.[^/.]+$/, ''); return `rustc -o "${o}" "${f}" && "${o}"`; },
};

export function activate(context: vscode.ExtensionContext) {
    const extPath = context.extensionPath;
    bridge = new GlueBridge(extPath);

    const variablesProvider = new VariablesViewProvider(context.extensionUri, bridge, context);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('watercodeflow.variables', variablesProvider)
    );

    const recordingViewerProvider = new RecordingViewerProvider(context.extensionUri, bridge);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('watercodeflow.recordingViewer', recordingViewerProvider)
    );

    const recordingsProvider = new RecordingsPanel(context.extensionUri, bridge, context);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('watercodeflow.recordings', recordingsProvider)
    );

    const settingsProvider = new SettingsPanel(context.extensionUri, bridge);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('watercodeflow.settings', settingsProvider)
    );

    const fileSelectorProvider = new FileSelectorPanel(context.extensionUri, bridge, context);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('watercodeflow.fileSelector', fileSelectorProvider)
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('watercodeflow.openSettings', () =>
            vscode.commands.executeCommand('watercodeflow.settings.focus')),

        vscode.commands.registerCommand('watercodeflow.openFileSelector', () =>
            vscode.commands.executeCommand('watercodeflow.fileSelector.focus')),

        vscode.commands.registerCommand('watercodeflow.openRecordings', () =>
            vscode.commands.executeCommand('watercodeflow.recordings.focus')),

        vscode.commands.registerCommand('watercodeflow.openInsights', () =>
            InsightsPanel.createOrShow(context.extensionUri, bridge)),

        vscode.commands.registerCommand('watercodeflow.openInspector', () =>
            VariableInspectorPanel.createOrShow(context.extensionUri, bridge)),

        vscode.commands.registerCommand('watercodeflow.openRunInspector', () =>
            RunInspectorPanel.createOrShow(context.extensionUri, bridge)),

        vscode.commands.registerCommand('watercodeflow.openVariables', () =>
            vscode.commands.executeCommand('watercodeflow.variables.focus')),

        vscode.commands.registerCommand('watercodeflow.runFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('WaterCodeFlow: No active file to run.');
                return;
            }
            const filePath = editor.document.fileName;
            const ext = path.extname(filePath).toLowerCase();

            if (WATCHER_EXTS.has(ext)) {
                // ── Watcher-tracked run — goes through GlueBridge ──────────────
                // Spawn watcher CLI via glue so stdout/stderr stream to the
                // webview and a recording JSON is saved automatically.
                // Open RecordingsPanel if not already open so user sees live output
                if (!RecordingsPanel.currentPanel) {
                    RecordingsPanel.createOrShow(context.extensionUri, bridge);
                }
                const panel = RecordingsPanel.currentPanel;

                const notifyPanel = (type: string, data: string) => {
                    panel?.postRunEvent(type, data);
                };

                notifyPanel('run.start', filePath);

                try {
                    const result = await bridge.spawnRun({
                        filePath,
                        extPath,
                        language: ext === '.py' ? 'python' : 'javascript',
                        onStdout: chunk => notifyPanel('run.stdout', chunk),
                        onStderr: chunk => notifyPanel('run.stderr', chunk),
                    });
                    notifyPanel('run.done', JSON.stringify(result));
                } catch (err: any) {
                    notifyPanel('run.error', err.message ?? String(err));
                    vscode.window.showErrorMessage(`WaterCodeFlow run failed: ${err.message}`);
                }

            } else if (PLAIN_EXTS[ext]) {
                // ── Plain terminal execution — no variable tracking ─────────────
                const terminal = vscode.window.createTerminal('WaterCodeFlow: Run');
                terminal.show();
                terminal.sendText(PLAIN_EXTS[ext](filePath));

            } else {
                vscode.window.showWarningMessage(
                    `WaterCodeFlow: No runner configured for ${ext} files.`
                );
            }
        })
    );

    context.subscriptions.push({ dispose: () => bridge.dispose() });
}

export function deactivate() {
    bridge?.dispose();
}
