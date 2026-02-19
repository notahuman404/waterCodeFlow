import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class InsightsPanel {
    private bridge;
    static currentPanel: InsightsPanel | undefined;
    private readonly _panel;
    private _disposables;
    private _extensionUri;
    static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge): void;
    private constructor();
    private _pushBranchData;
    dispose(): void;
    private _getHtml;
}
//# sourceMappingURL=InsightsPanel.d.ts.map