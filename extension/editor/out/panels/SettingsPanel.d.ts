import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class SettingsPanel {
    private bridge;
    static currentPanel: SettingsPanel | undefined;
    private readonly _panel;
    private _disposables;
    static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge): void;
    private constructor();
    dispose(): void;
    private _getHtml;
}
//# sourceMappingURL=SettingsPanel.d.ts.map