import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

export interface GlueResponse {
    id: string;
    success: boolean;
    result?: any;
    error?: string;
}

/**
 * GlueBridge: Persistent child process bridge to the Python glue adapter.
 * Sends JSON commands to stdin, reads JSON responses from stdout.
 */
export class GlueBridge {
    private _proc: cp.ChildProcess | null = null;
    private _pending = new Map<string, (res: GlueResponse) => void>();
    private _buf = '';
    private _extensionPath: string;
    private _restarting = false;

    constructor(extensionPath: string) {
        this._extensionPath = extensionPath;
    }

    private _spawn() {
        if (this._proc) return;
        const adapterPath = path.join(this._extensionPath, 'glue', 'adapter.py');
        const pythonPath = [
            this._extensionPath,
            path.join(this._extensionPath, 'CodeVovle')
        ].join(path.delimiter);

        this._proc = cp.spawn('python3', [adapterPath], {
            cwd: this._extensionPath,
            env: { ...process.env, PYTHONPATH: pythonPath }
        });

        this._proc.stdout?.on('data', (chunk: Buffer) => {
            this._buf += chunk.toString();
            let nl: number;
            while ((nl = this._buf.indexOf('\n')) !== -1) {
                const line = this._buf.slice(0, nl).trim();
                this._buf = this._buf.slice(nl + 1);
                if (!line) continue;
                try {
                    const res: GlueResponse = JSON.parse(line);
                    const cb = this._pending.get(res.id);
                    if (cb) {
                        this._pending.delete(res.id);
                        cb(res);
                    }
                } catch (_) {}
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

        this._proc.stderr?.on('data', (_chunk: Buffer) => {
            // swallow stderr — python tracebacks are debug-only
        });
    }

    send(command: string, args: Record<string, any> = {}): Promise<any> {
        return new Promise((resolve, reject) => {
            this._spawn();
            const id = Math.random().toString(36).slice(2);
            const msg = JSON.stringify({ id, command, ...args }) + '\n';

            this._pending.set(id, (res) => {
                if (res.success) resolve(res.result);
                else reject(new Error(res.error || 'Glue error'));
            });

            try {
                this._proc?.stdin?.write(msg);
            } catch (e) {
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
