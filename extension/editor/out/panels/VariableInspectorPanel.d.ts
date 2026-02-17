import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class VariableInspectorPanel {
    private bridge;
    static currentPanel: VariableInspectorPanel | undefined;
    private readonly _panel;
    private _disposables;
    static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge): void;
    private constructor();
    private _pushVarData;
    dispose(): void;
    private _getHtml;
}
//# sourceMappingURL=VariableInspectorPanel.d.ts.map