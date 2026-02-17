import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class RecordingViewerProvider implements vscode.WebviewViewProvider {
    private readonly _extensionUri;
    private readonly _bridge;
    private _view?;
    constructor(_extensionUri: vscode.Uri, _bridge: GlueBridge);
    resolveWebviewView(webviewView: vscode.WebviewView, _context: vscode.WebviewViewResolveContext, _token: vscode.CancellationToken): void;
    private _pushData;
    private _getHtml;
}
//# sourceMappingURL=RecordingViewerProvider.d.ts.map