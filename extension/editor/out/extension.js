"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const GlueBridge_1 = require("./GlueBridge");
const VariablesViewProvider_1 = require("./providers/VariablesViewProvider");
const RecordingViewerProvider_1 = require("./providers/RecordingViewerProvider");
const SettingsPanel_1 = require("./panels/SettingsPanel");
const FileSelectorPanel_1 = require("./panels/FileSelectorPanel");
const RecordingsPanel_1 = require("./panels/RecordingsPanel");
const InsightsPanel_1 = require("./panels/InsightsPanel");
const VariableInspectorPanel_1 = require("./panels/VariableInspectorPanel");
const RunInspectorPanel_1 = require("./panels/RunInspectorPanel");
let bridge;
/** File extensions that get watcher-based variable recording. */
const WATCHER_EXTS = new Set(['.py', '.js', '.mjs']);
/** File extensions that get plain-terminal execution (no variable tracking). */
const PLAIN_EXTS = {
    '.c': f => { const o = f.replace(/\.[^/.]+$/, ''); return `gcc -O1 -o "${o}" "${f}" && "${o}"`; },
    '.cpp': f => { const o = f.replace(/\.[^/.]+$/, ''); return `g++ -O1 -o "${o}" "${f}" && "${o}"`; },
    '.cc': f => { const o = f.replace(/\.[^/.]+$/, ''); return `g++ -O1 -o "${o}" "${f}" && "${o}"`; },
    '.cxx': f => { const o = f.replace(/\.[^/.]+$/, ''); return `g++ -O1 -o "${o}" "${f}" && "${o}"`; },
    '.go': f => `go run "${f}"`,
    '.rb': f => `ruby "${f}"`,
    '.sh': f => `bash "${f}"`,
    '.java': f => { const d = path.dirname(f); const b = path.basename(f, '.java'); return `cd "${d}" && javac "${b}.java" && java "${b}"`; },
    '.rs': f => { const o = f.replace(/\.[^/.]+$/, ''); return `rustc -o "${o}" "${f}" && "${o}"`; },
};
function activate(context) {
    const extPath = context.extensionPath;
    bridge = new GlueBridge_1.GlueBridge(extPath);
    const variablesProvider = new VariablesViewProvider_1.VariablesViewProvider(context.extensionUri, bridge, context);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('watercodeflow.variables', variablesProvider));
    const recordingViewerProvider = new RecordingViewerProvider_1.RecordingViewerProvider(context.extensionUri, bridge);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('watercodeflow.recordingViewer', recordingViewerProvider));
    context.subscriptions.push(vscode.commands.registerCommand('watercodeflow.openSettings', () => SettingsPanel_1.SettingsPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openFileSelector', () => FileSelectorPanel_1.FileSelectorPanel.createOrShow(context.extensionUri, bridge, context)), vscode.commands.registerCommand('watercodeflow.openRecordings', () => RecordingsPanel_1.RecordingsPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openInsights', () => InsightsPanel_1.InsightsPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openInspector', () => VariableInspectorPanel_1.VariableInspectorPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openRunInspector', () => RunInspectorPanel_1.RunInspectorPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openVariables', () => vscode.commands.executeCommand('watercodeflow.variables.focus')), vscode.commands.registerCommand('watercodeflow.runFile', async () => {
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
            if (!RecordingsPanel_1.RecordingsPanel.currentPanel) {
                RecordingsPanel_1.RecordingsPanel.createOrShow(context.extensionUri, bridge);
            }
            const panel = RecordingsPanel_1.RecordingsPanel.currentPanel;
            const notifyPanel = (type, data) => {
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
            }
            catch (err) {
                notifyPanel('run.error', err.message ?? String(err));
                vscode.window.showErrorMessage(`WaterCodeFlow run failed: ${err.message}`);
            }
        }
        else if (PLAIN_EXTS[ext]) {
            // ── Plain terminal execution — no variable tracking ─────────────
            const terminal = vscode.window.createTerminal('WaterCodeFlow: Run');
            terminal.show();
            terminal.sendText(PLAIN_EXTS[ext](filePath));
        }
        else {
            vscode.window.showWarningMessage(`WaterCodeFlow: No runner configured for ${ext} files.`);
        }
    }));
    context.subscriptions.push({ dispose: () => bridge.dispose() });
}
function deactivate() {
    bridge?.dispose();
}
//# sourceMappingURL=extension.js.map