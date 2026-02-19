export interface GlueResponse {
    id: string;
    success: boolean;
    result?: any;
    error?: string;
}
export interface SpawnRunOptions {
    filePath: string;
    extPath: string;
    language: 'python' | 'javascript';
    onStdout?: (chunk: string) => void;
    onStderr?: (chunk: string) => void;
}
export interface RunResult {
    runId: string;
    filePath: string;
    language: string;
    exitCode: number;
    recordingPath: string;
    timestamp: string;
    durationMs: number;
    useWatcher: boolean;
}
export declare class GlueBridge {
    private _proc;
    private _pending;
    private _buf;
    private _extensionPath;
    private _projectRoot;
    private _spawnError;
    private _outputChannel;
    constructor(extensionPath: string);
    private _spawn;
    send(command: string, args?: Record<string, any>): Promise<any>;
    spawnRun(opts: SpawnRunOptions): Promise<RunResult>;
    dispose(): void;
}
//# sourceMappingURL=GlueBridge.d.ts.map