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
exports.GlueBridge = void 0;
const vscode = __importStar(require("vscode"));
const cp = __importStar(require("child_process"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
/** Request timeout: reject pending requests after 30s to prevent hangs. */
const REQUEST_TIMEOUT_MS = 30000;
class GlueBridge {
    constructor(extensionPath) {
        this._proc = null;
        this._pending = new Map();
        this._buf = '';
        this._spawnError = null;
        this._extensionPath = extensionPath;
        // PROJECT ROOT: glue/, watcher/, CodeVovle/ are siblings of editor/ in
        // the source tree. When the extension loads from the workspace (dev/codespace),
        // extensionPath = .../editor/ and the backends are one level up.
        // If they were ever bundled inside the extension dir instead, that takes priority.
        const parentDir = path.join(extensionPath, '..');
        if (fs.existsSync(path.join(extensionPath, 'CodeVovle'))) {
            // Bundled inside extension dir (e.g. production VSIX with backends included)
            this._projectRoot = extensionPath;
        }
        else if (fs.existsSync(path.join(parentDir, 'CodeVovle'))) {
            // Sibling of editor/ — dev/codespace install (the normal case)
            this._projectRoot = parentDir;
        }
        else {
            // Fallback: assume extensionPath and surface a clear log message
            this._projectRoot = extensionPath;
        }
        // Create output channel once so bridge restarts don't create duplicates
        this._outputChannel = vscode.window.createOutputChannel('WaterCodeFlow');
        this._outputChannel.appendLine(`Extension path: ${this._extensionPath}`);
        this._outputChannel.appendLine(`Project root: ${this._projectRoot}`);
        this._outputChannel.appendLine(`Glue at: ${path.join(this._projectRoot, 'glue')}`);
        this._outputChannel.appendLine(`Watcher at: ${path.join(this._projectRoot, 'watcher')}`);
        this._outputChannel.appendLine(`CodeVovle at: ${path.join(this._projectRoot, 'CodeVovle')}`);
    }
    _spawn() {
        if (this._proc) {
            return;
        }
        this._spawnError = null;
        const adapterPath = path.join(this._projectRoot, 'glue', 'adapter.py');
        const pythonPath = [
            path.join(this._projectRoot, 'CodeVovle'),
            this._projectRoot,
        ].join(path.delimiter);
        // Include watcher/build/ in LD_LIBRARY_PATH so libwatcher_core.so is found
        const watcherBuildDir = path.join(this._projectRoot, 'watcher', 'build');
        const ldLibPath = [watcherBuildDir, process.env.LD_LIBRARY_PATH || '']
            .filter(Boolean).join(path.delimiter);
        this._proc = cp.spawn('python3', [adapterPath], {
            cwd: this._projectRoot,
            env: { ...process.env, PYTHONPATH: pythonPath, LD_LIBRARY_PATH: ldLibPath },
        });
        // ── Handle spawn failure (python3 not found, adapter missing, etc.) ──
        this._proc.on('error', (err) => {
            this._spawnError = err.message;
            this._proc = null;
            for (const [, { cb, timer }] of this._pending) {
                clearTimeout(timer);
                cb({ id: '', success: false, error: 'Bridge failed to start: ' + err.message });
            }
            this._pending.clear();
            // Notify user once so they know what's wrong
            if (err.code === 'ENOENT') {
                vscode.window.showErrorMessage('WaterCodeFlow: python3 not found. Please install Python 3 and ensure it is on PATH.');
            }
        });
        this._proc.stdout?.on('data', (chunk) => {
            this._buf += chunk.toString();
            let nl;
            while ((nl = this._buf.indexOf('\n')) !== -1) {
                const line = this._buf.slice(0, nl).trim();
                this._buf = this._buf.slice(nl + 1);
                if (!line) {
                    continue;
                }
                try {
                    const res = JSON.parse(line);
                    const entry = this._pending.get(res.id);
                    if (entry) {
                        clearTimeout(entry.timer);
                        this._pending.delete(res.id);
                        entry.cb(res);
                    }
                }
                catch (_) { }
            }
        });
        this._proc.on('exit', (code) => {
            this._proc = null;
            const msg = code != null ? `Bridge process exited (code ${code})` : 'Bridge process exited';
            for (const [, { cb, timer }] of this._pending) {
                clearTimeout(timer);
                cb({ id: '', success: false, error: msg });
            }
            this._pending.clear();
        });
        // Log stderr to the shared output channel (created once in constructor)
        this._proc.stderr?.on('data', (chunk) => {
            this._outputChannel.append(chunk.toString());
        });
    }
    send(command, args = {}) {
        return new Promise((resolve, reject) => {
            this._spawn();
            // If spawn failed immediately, reject right away
            if (this._spawnError) {
                reject(new Error('Bridge unavailable: ' + this._spawnError));
                return;
            }
            const id = Math.random().toString(36).slice(2);
            const msg = JSON.stringify({ id, command, ...args }) + '\n';
            // Timeout guard — prevents requests hanging forever
            const timer = setTimeout(() => {
                this._pending.delete(id);
                reject(new Error(`Bridge request timed out: ${command}`));
            }, REQUEST_TIMEOUT_MS);
            this._pending.set(id, {
                cb: (res) => {
                    if (res.success) {
                        resolve(res.result);
                    }
                    else {
                        reject(new Error(res.error || 'Glue error'));
                    }
                },
                timer,
            });
            // Guard stdin access in case process died between _spawn() and now
            if (!this._proc?.stdin?.writable) {
                clearTimeout(timer);
                this._pending.delete(id);
                this._proc = null; // force re-spawn next call
                reject(new Error('Bridge stdin not writable'));
                return;
            }
            try {
                this._proc.stdin.write(msg);
            }
            catch (e) {
                clearTimeout(timer);
                this._pending.delete(id);
                reject(e);
            }
        });
    }
    async spawnRun(opts) {
        const { filePath, extPath, language, onStdout, onStderr } = opts;
        // Use project root for all backend paths
        const projectRoot = this._projectRoot;
        const runId = `run-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
        const timestamp = new Date().toISOString();
        const startMs = Date.now();
        const recordingsDir = path.join(projectRoot, 'built', 'recordings');
        fs.mkdirSync(recordingsDir, { recursive: true });
        const recordingPath = path.join(recordingsDir, `${runId}.json`);
        const pythonPath = [
            path.join(projectRoot, 'CodeVovle'),
            projectRoot,
        ].join(path.delimiter);
        const watcherCliScript = path.join(projectRoot, 'watcher', 'cli', 'main.py');
        const watcherOutputDir = path.join(projectRoot, 'built', 'watcher_events', runId);
        // LD_LIBRARY_PATH so watcher's C++ shared libs are resolved at runtime
        const watcherBuildDir = path.join(projectRoot, 'watcher', 'build');
        const ldLibPath = [watcherBuildDir, process.env.LD_LIBRARY_PATH || '']
            .filter(Boolean).join(path.delimiter);
        const spawnEnv = { ...process.env, PYTHONPATH: pythonPath, LD_LIBRARY_PATH: ldLibPath };
        let proc;
        let usedWatcher = false;
        if (language === 'python') {
            if (fs.existsSync(watcherCliScript)) {
                proc = cp.spawn('python3', [
                    watcherCliScript,
                    '--user-script', filePath,
                    '--output', watcherOutputDir,
                    '--log-level', 'WARNING',
                ], {
                    cwd: projectRoot,
                    env: spawnEnv,
                });
                usedWatcher = true;
            }
            else {
                proc = cp.spawn('python3', [filePath], {
                    cwd: path.dirname(filePath),
                    env: spawnEnv,
                });
            }
        }
        else {
            const jsAdapterPath = path.join(projectRoot, 'watcher', 'adapters', 'javascript', 'index.js');
            if (fs.existsSync(jsAdapterPath)) {
                proc = cp.spawn('node', [jsAdapterPath, filePath], { cwd: projectRoot, env: spawnEnv });
                usedWatcher = true;
            }
            else {
                proc = cp.spawn('node', [filePath], { cwd: path.dirname(filePath) });
            }
        }
        const stdoutParts = [];
        const stderrParts = [];
        proc.stdout?.on('data', (chunk) => {
            const s = chunk.toString();
            stdoutParts.push(s);
            onStdout?.(s);
        });
        proc.stderr?.on('data', (chunk) => {
            const s = chunk.toString();
            stderrParts.push(s);
            onStderr?.(s);
        });
        let exitCode = await new Promise((resolve) => {
            proc.on('close', (code) => resolve(code ?? 0));
            proc.on('error', (err) => {
                // Provide a meaningful error message when python3/node is not found
                const msg = err.code === 'ENOENT'
                    ? `Command not found: ${language === 'python' ? 'python3' : 'node'}`
                    : err.message;
                onStderr?.(msg + '\n');
                resolve(1);
            });
        });
        // Fallback: if watcher exited with validation error, retry as plain python3
        if (usedWatcher && language === 'python' && exitCode === 2) {
            const retryProc = cp.spawn('python3', [filePath], {
                cwd: path.dirname(filePath),
                env: { ...process.env, PYTHONPATH: pythonPath },
            });
            const retryStdout = [];
            const retryStderr = [];
            retryProc.stdout?.on('data', (chunk) => {
                const s = chunk.toString();
                retryStdout.push(s);
                onStdout?.(s);
            });
            retryProc.stderr?.on('data', (chunk) => {
                const s = chunk.toString();
                retryStderr.push(s);
                onStderr?.(s);
            });
            exitCode = await new Promise((resolve) => {
                retryProc.on('close', (code) => resolve(code ?? 0));
                retryProc.on('error', () => resolve(1));
            });
            stdoutParts.push(...retryStdout);
            stderrParts.push(...retryStderr);
            usedWatcher = false;
        }
        const durationMs = Date.now() - startMs;
        const stdoutStr = stdoutParts.join('');
        const stderrStr = stderrParts.join('');
        // Parse watcher JSONL event files for variable mutations
        let watcherEventFiles = [];
        try {
            if (fs.existsSync(watcherOutputDir)) {
                watcherEventFiles = fs.readdirSync(watcherOutputDir)
                    .filter(f => f.endsWith('.jsonl'))
                    .map(f => path.join(watcherOutputDir, f));
            }
        }
        catch (_) { }
        let capturedVars = [];
        if (watcherEventFiles.length > 0) {
            const varMap = {};
            for (const jsonlFile of watcherEventFiles) {
                try {
                    const lines = fs.readFileSync(jsonlFile, 'utf8').split('\n').filter(Boolean);
                    for (const line of lines) {
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
                        }
                        catch (_) { }
                    }
                }
                catch (_) { }
            }
            capturedVars = Object.values(varMap);
        }
        const recording = {
            runId, filePath, language, exitCode,
            recordingPath, timestamp, durationMs,
            useWatcher: usedWatcher,
            stdout: stdoutStr,
            stderr: stderrStr,
            ...(watcherEventFiles.length > 0 ? { watcherEvents: watcherEventFiles } : {}),
            ...(capturedVars.length > 0 ? { vars: capturedVars } : {}),
        };
        fs.writeFileSync(recordingPath, JSON.stringify(recording, null, 2));
        // Notify glue adapter (non-fatal)
        this.send('saveRecording', {
            runId, recordingPath, filePath, timestamp, durationMs, exitCode,
        }).catch(() => { });
        return recording;
    }
    dispose() {
        // Cancel all pending requests cleanly
        for (const [, { cb, timer }] of this._pending) {
            clearTimeout(timer);
            cb({ id: '', success: false, error: 'Bridge disposed' });
        }
        this._pending.clear();
        this._proc?.kill();
        this._proc = null;
        this._outputChannel.dispose();
    }
}
exports.GlueBridge = GlueBridge;
//# sourceMappingURL=GlueBridge.js.map