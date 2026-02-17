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
export declare class GlueBridge {
    private _proc;
    private _pending;
    private _buf;
    private _extensionPath;
    private _restarting;
    constructor(extensionPath: string);
    private _spawn;
    send(command: string, args?: Record<string, any>): Promise<any>;
    dispose(): void;
}
//# sourceMappingURL=GlueBridge.d.ts.map