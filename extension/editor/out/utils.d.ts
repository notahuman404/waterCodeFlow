export declare function getNonce(): string;
export interface VarEntry {
    name: string;
    file: string;
    scope: 'local' | 'global' | 'parameter' | 'return' | 'assignment';
    tracked: boolean;
    trackMode: 'single' | 'multi';
    trackRuns: number;
}
//# sourceMappingURL=utils.d.ts.map