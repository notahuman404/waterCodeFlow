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
function activate(context) {
    const extPath = context.extensionPath;
    bridge = new GlueBridge_1.GlueBridge(extPath);
    const variablesProvider = new VariablesViewProvider_1.VariablesViewProvider(context.extensionUri, bridge);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('watercodeflow.variables', variablesProvider));
    const recordingViewerProvider = new RecordingViewerProvider_1.RecordingViewerProvider(context.extensionUri, bridge);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider('watercodeflow.recordingViewer', recordingViewerProvider));
    context.subscriptions.push(vscode.commands.registerCommand('watercodeflow.openSettings', () => SettingsPanel_1.SettingsPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openFileSelector', () => FileSelectorPanel_1.FileSelectorPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openRecordings', () => RecordingsPanel_1.RecordingsPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openInsights', () => InsightsPanel_1.InsightsPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openInspector', () => VariableInspectorPanel_1.VariableInspectorPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openRunInspector', () => RunInspectorPanel_1.RunInspectorPanel.createOrShow(context.extensionUri, bridge)), vscode.commands.registerCommand('watercodeflow.openVariables', () => vscode.commands.executeCommand('watercodeflow.variables.focus')), vscode.commands.registerCommand('watercodeflow.runFile', () => {
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
            terminal.sendText(`cd "${extPath}" && PYTHONPATH="${extPath}:${extPath}/CodeVovle" python3 -m codevovle run "${filePath}" 2>/dev/null || python3 "${filePath}"`);
        }
        else if (['.js', '.mjs', '.ts'].includes(ext)) {
            // JS: use the watcher JS adapter if available, else node
            const watcherAdapterPath = path.join(extPath, 'watcher', 'adapters', 'javascript', 'index.js');
            terminal.sendText(`node "${watcherAdapterPath}" "${filePath}" 2>/dev/null || node "${filePath}"`);
        }
        else if (['.c', '.cpp', '.cc', '.cxx'].includes(ext)) {
            const compiler = ext === '.c' ? 'gcc' : 'g++';
            const outFile = filePath.replace(/\.[^/.]+$/, '');
            terminal.sendText(`${compiler} -O1 -o "${outFile}" "${filePath}" && "${outFile}"`);
        }
        else if (ext === '.go') {
            terminal.sendText(`go run "${filePath}"`);
        }
        else if (ext === '.rb') {
            terminal.sendText(`ruby "${filePath}"`);
        }
        else if (ext === '.sh') {
            terminal.sendText(`bash "${filePath}"`);
        }
        else if (ext === '.java') {
            const dir = path.dirname(filePath);
            const base = path.basename(filePath, '.java');
            terminal.sendText(`cd "${dir}" && javac "${base}.java" && java "${base}"`);
        }
        else if (ext === '.rs') {
            const outFile = filePath.replace(/\.[^/.]+$/, '');
            terminal.sendText(`rustc -o "${outFile}" "${filePath}" && "${outFile}"`);
        }
        else {
            terminal.sendText(`"${filePath}"`);
        }
    }));
    context.subscriptions.push({ dispose: () => bridge.dispose() });
}
function deactivate() {
    bridge?.dispose();
}
//# sourceMappingURL=extension.js.map