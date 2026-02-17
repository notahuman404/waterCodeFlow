import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class FileSelectorPanel {
    private bridge;
    static currentPanel: FileSelectorPanel | undefined;
    private readonly _panel;
    private _disposables;
    private _selectedFiles;
    static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge): void;
    private constructor();
    private _pushFiles;
    dispose(): void;
    private _getHtml;
}
//# sourceMappingURL=FileSelectorPanel.d.ts.map