import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class FileSelectorPanel {
    private bridge;
    private context?;
    static currentPanel: FileSelectorPanel | undefined;
    private readonly _panel;
    private _disposables;
    private _selectedFiles;
    private _outputChannel;
    static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge, context?: vscode.ExtensionContext): void;
    private constructor();
    private _pushFiles;
    dispose(): void;
    private _getHtml;
}
//# sourceMappingURL=FileSelectorPanel.d.ts.map