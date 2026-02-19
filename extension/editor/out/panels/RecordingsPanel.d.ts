import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class RecordingsPanel {
    private bridge;
    static currentPanel: RecordingsPanel | undefined;
    private readonly _panel;
    private _disposables;
    private _extensionUri;
    private _lastPushedFilePath;
    static createOrShow(extensionUri: vscode.Uri, bridge: GlueBridge): void;
    /** Forward a run lifecycle event (stdout, stderr, done, error) into the webview. */
    postRunEvent(type: string, data: string): void;
    private constructor();
    private _pushData;
    dispose(): void;
    private _getHtml;
}
//# sourceMappingURL=RecordingsPanel.d.ts.map