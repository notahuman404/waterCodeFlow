import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class RecordingsPanel {
    private bridge;
    static currentPanel: RecordingsPanel | undefined;
    private readonly _panel;
    private _disposables;
    static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge): void;
    private constructor();
    private _pushData;
    dispose(): void;
    private _getHtml;
}
//# sourceMappingURL=RecordingsPanel.d.ts.map