import * as vscode from 'vscode';
import { GlueBridge } from '../GlueBridge';
export declare class VariablesViewProvider implements vscode.WebviewViewProvider {
    private readonly _extensionUri;
    private readonly _bridge;
    private _view?;
    private _trackState;
    constructor(_extensionUri: vscode.Uri, _bridge: GlueBridge);
    resolveWebviewView(webviewView: vscode.WebviewView, _context: vscode.WebviewViewResolveContext, _token: vscode.CancellationToken): void;
    private _pushVars;
    private _getHtml;
}
//# sourceMappingURL=VariablesViewProvider.d.ts.map