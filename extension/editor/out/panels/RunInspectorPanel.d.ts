import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class RunInspectorPanel {
    private bridge;
    static currentPanel: RunInspectorPanel | undefined;
    private readonly _panel;
    private _disposables;
    static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge): void;
    private constructor();
    private _pushRunData;
    dispose(): void;
    private _getHtml;
}
//# sourceMappingURL=RunInspectorPanel.d.ts.map