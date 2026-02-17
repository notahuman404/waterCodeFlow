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
const cp = __importStar(require("child_process"));
const path = __importStar(require("path"));
/**
 * GlueBridge: Persistent child process bridge to the Python glue adapter.
 * Sends JSON commands to stdin, reads JSON responses from stdout.
 */
class GlueBridge {
    constructor(extensionPath) {
        this._proc = null;
        this._pending = new Map();
        this._buf = '';
        this._restarting = false;
        this._extensionPath = extensionPath;
    }
    _spawn() {
        if (this._proc)
            return;
        const adapterPath = path.join(this._extensionPath, 'glue', 'adapter.py');
        const pythonPath = [
            this._extensionPath,
            path.join(this._extensionPath, 'CodeVovle')
        ].join(path.delimiter);
        this._proc = cp.spawn('python3', [adapterPath], {
            cwd: this._extensionPath,
            env: { ...process.env, PYTHONPATH: pythonPath }
        });
        this._proc.stdout?.on('data', (chunk) => {
            this._buf += chunk.toString();
            let nl;
            while ((nl = this._buf.indexOf('\n')) !== -1) {
                const line = this._buf.slice(0, nl).trim();
                this._buf = this._buf.slice(nl + 1);
                if (!line)
                    continue;
                try {
                    const res = JSON.parse(line);
                    const cb = this._pending.get(res.id);
                    if (cb) {
                        this._pending.delete(res.id);
                        cb(res);
                    }
                }
                catch (_) { }
            }
        });
        this._proc.on('exit', () => {
            this._proc = null;
            // Reject all pending
            for (const [, cb] of this._pending) {
                cb({ id: '', success: false, error: 'Bridge process exited' });
            }
            this._pending.clear();
        });
        this._proc.stderr?.on('data', (_chunk) => {
            // swallow stderr — python tracebacks are debug-only
        });
    }
    send(command, args = {}) {
        return new Promise((resolve, reject) => {
            this._spawn();
            const id = Math.random().toString(36).slice(2);
            const msg = JSON.stringify({ id, command, ...args }) + '\n';
            this._pending.set(id, (res) => {
                if (res.success)
                    resolve(res.result);
                else
                    reject(new Error(res.error || 'Glue error'));
            });
            try {
                this._proc?.stdin?.write(msg);
            }
            catch (e) {
                this._pending.delete(id);
                reject(e);
            }
        });
    }
    dispose() {
        this._proc?.kill();
        this._proc = null;
    }
}
exports.GlueBridge = GlueBridge;
//# sourceMappingURL=GlueBridge.js.map