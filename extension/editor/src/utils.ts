export function getNonce(): string {
    let text = '';
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return text;
}

export interface VarEntry {
    name: string;
    file: string;
    scope: 'local' | 'global' | 'parameter' | 'return' | 'assignment';
    tracked: boolean;
    trackMode: 'single' | 'multi';
    trackRuns: number;
}
