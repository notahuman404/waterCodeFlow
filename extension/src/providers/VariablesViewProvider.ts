/**
 * VariablesViewProvider: Manages the Variables webview sidebar panel.
 * Displays tracked variables and allows selection.
 */
import * as vscode from "vscode";
import { getGlueClient } from "../glueClient";
import { Variable } from "../types";
import * as path from "path";

export class VariablesViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "watercodeflow.variables";

  private _view?: vscode.WebviewView;
  private _activeFile: string = "";

  constructor(
    private context: vscode.ExtensionContext,
    private nonce: string
  ) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext<unknown>,
    token: vscode.CancellationToken
  ): void | Thenable<void> {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.joinPath(this.context.extensionUri, "media"),
      ],
    };

    webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

    webviewView.webview.onDidReceiveMessage(async (message) => {
      await this.handleMessage(message);
    });
  }

  setActiveFile(filePath: string): void {
    this._activeFile = filePath;
    this.refreshVariables();
  }

  async refreshVariables(): Promise<void> {
    if (!this._view || !this._activeFile) return;

    try {
      const glueClient = getGlueClient();
      const variables = await glueClient.send<Variable[]>({
        command: "listTrackedVariables",
        filePath: this._activeFile,
      });

      this._view.webview.postMessage({
        type: "variablesUpdate",
        variables,
      });
    } catch (err) {
      console.log("Variables refresh error:", err);
    }
  }

  private async handleMessage(message: any): Promise<void> {
    const glueClient = getGlueClient();

    switch (message.command) {
      case "inspectVariable": {
        vscode.commands.executeCommand(
          "watercodeflow.openInspector",
          message.varName
        );
        break;
      }

      case "inferVariables": {
        try {
          const variables = await glueClient.send<Variable[]>({
            command: "listTrackedVariables",
            filePath: message.filePath || this._activeFile,
          });

          this._view?.webview.postMessage({
            type: "variables",
            variables,
          });
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to infer variables: ${err}`,
          });
        }
        break;
      }
    }
  }

  private getHtmlForWebview(webview: vscode.Webview): string {
    const variablesUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, "media", "variables.js")
    );

    const variablesCssUri = webview.asWebviewUri(
      vscode.Uri.joinPath(
        this.context.extensionUri,
        "media",
        "variables.css"
      )
    );

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="${variablesCssUri}">
    <title>Variables</title>
</head>
<body>
    <div id="variables-container">
        <div id="controls">
            <button id="btn-infer">Infer Variables</button>
        </div>
        <ul id="variables-list"></ul>
    </div>
    <script nonce="${this.nonce}" src="${variablesUri}"></script>
</body>
</html>`;
  }

  dispose(): void {
    // Cleanup if needed
  }
}
