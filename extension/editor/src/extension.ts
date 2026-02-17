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

export function activate(context: vscode.ExtensionContext) {
    const extPath = context.extensionPath;
    bridge = new GlueBridge(extPath);

    const variablesProvider = new VariablesViewProvider(context.extensionUri, bridge);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('watercodeflow.variables', variablesProvider)
    );

    const recordingViewerProvider = new RecordingViewerProvider(context.extensionUri, bridge);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('watercodeflow.recordingViewer', recordingViewerProvider)
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('watercodeflow.openSettings', () =>
            SettingsPanel.createOrShow(context.extensionUri, bridge)),

        vscode.commands.registerCommand('watercodeflow.openFileSelector', () =>
            FileSelectorPanel.createOrShow(context.extensionUri, bridge)),

        vscode.commands.registerCommand('watercodeflow.openRecordings', () =>
            RecordingsPanel.createOrShow(context.extensionUri, bridge)),

        vscode.commands.registerCommand('watercodeflow.openInsights', () =>
            InsightsPanel.createOrShow(context.extensionUri, bridge)),

        vscode.commands.registerCommand('watercodeflow.openInspector', () =>
            VariableInspectorPanel.createOrShow(context.extensionUri, bridge)),

        vscode.commands.registerCommand('watercodeflow.openRunInspector', () =>
            RunInspectorPanel.createOrShow(context.extensionUri, bridge)),

        vscode.commands.registerCommand('watercodeflow.openVariables', () =>
            vscode.commands.executeCommand('watercodeflow.variables.focus')),

        vscode.commands.registerCommand('watercodeflow.runFile', () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('WaterCodeFlow: No active file to run.');
                return;
            }
            const filePath = editor.document.fileName;
            const ext = path.extname(filePath).toLowerCase();
            const terminal = vscode.window.createTerminal('WaterCodeFlow: Run');
            terminal.show();

            // Python and JS: use watcher CLI for variable tracking
            if (ext === '.py') {
                terminal.sendText(
                    `cd "${extPath}" && PYTHONPATH="${extPath}:${extPath}/CodeVovle" python3 -m codevovle run "${filePath}" 2>/dev/null || python3 "${filePath}"`
                );
            } else if (['.js', '.mjs', '.ts'].includes(ext)) {
                // JS: use the watcher JS adapter if available, else node
                const watcherAdapterPath = path.join(extPath, 'watcher', 'adapters', 'javascript', 'index.js');
                terminal.sendText(`node "${watcherAdapterPath}" "${filePath}" 2>/dev/null || node "${filePath}"`);
            } else if (['.c', '.cpp', '.cc', '.cxx'].includes(ext)) {
                const compiler = ext === '.c' ? 'gcc' : 'g++';
                const outFile = filePath.replace(/\.[^/.]+$/, '');
                terminal.sendText(`${compiler} -O1 -o "${outFile}" "${filePath}" && "${outFile}"`);
            } else if (ext === '.go') {
                terminal.sendText(`go run "${filePath}"`);
            } else if (ext === '.rb') {
                terminal.sendText(`ruby "${filePath}"`);
            } else if (ext === '.sh') {
                terminal.sendText(`bash "${filePath}"`);
            } else if (ext === '.java') {
                const dir = path.dirname(filePath);
                const base = path.basename(filePath, '.java');
                terminal.sendText(`cd "${dir}" && javac "${base}.java" && java "${base}"`);
            } else if (ext === '.rs') {
                const outFile = filePath.replace(/\.[^/.]+$/, '');
                terminal.sendText(`rustc -o "${outFile}" "${filePath}" && "${outFile}"`);
            } else {
                terminal.sendText(`"${filePath}"`);
            }
        })
    );

    context.subscriptions.push({ dispose: () => bridge.dispose() });
}

export function deactivate() {
    bridge?.dispose();
}
