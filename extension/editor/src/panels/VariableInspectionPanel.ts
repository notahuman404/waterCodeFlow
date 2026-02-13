/**
 * VariableInspectionPanel: Modal webview for inspecting variable mutations.
 */
import * as vscode from "vscode";
import { getGlueClient } from "../glueClient";
import { VariableTimelineEntry } from "../types";

export class VariableInspectionPanel {
  private readonly _panel: vscode.WebviewPanel;
  private _disposed = false;

  constructor(
    context: vscode.ExtensionContext,
    nonce: string,
    private filePath: string,
    private varName: string
  ) {
    this._panel = vscode.window.createWebviewPanel(
      "watercodeflow.inspector",
      `Inspector: ${varName}`,
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        localResourceRoots: [
          vscode.Uri.joinPath(context.extensionUri, "media"),
        ],
      }
    );

    this._panel.webview.html = this.getHtmlForWebview(
      this._panel.webview,
      context,
      nonce
    );

    this._panel.webview.onDidReceiveMessage(async (message) => {
      await this.handleMessage(message);
    });

    this._panel.onDidDispose(() => {
      this._disposed = true;
    });

    // Load timeline data
    this.loadTimeline();
  }

  private async loadTimeline(): Promise<void> {
    if (this._disposed) return;

    try {
      const glueClient = getGlueClient();
      const timeline = await glueClient.send<VariableTimelineEntry[]>({
        command: "getVariableTimeline",
        filePath: this.filePath,
        variableName: this.varName,
        maxTicks: 200,
      });

      this._panel.webview.postMessage({
        type: "timelineLoaded",
        timeline,
        varName: this.varName,
      });
    } catch (err) {
      this._panel.webview.postMessage({
        type: "error",
        message: `Failed to load timeline: ${err}`,
      });
    }
  }

  private async handleMessage(message: any): Promise<void> {
    const glueClient = getGlueClient();

    switch (message.command) {
      case "scrub": {
        try {
          await glueClient.send({
            command: "jumpToTick",
            filePath: this.filePath,
            tickId: message.tick,
          });

          this._panel.webview.postMessage({
            type: "scrubbed",
            tick: message.tick,
          });
        } catch (err) {
          this._panel.webview.postMessage({
            type: "error",
            message: `Failed to scrub: ${err}`,
          });
        }
        break;
      }

      case "scrollToLine": {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
          const line = Math.max(0, (message.lineNo || 1) - 1);
          editor.selection = new vscode.Selection(line, 0, line, 0);
          editor.revealRange(
            new vscode.Range(line, 0, line, 100),
            vscode.TextEditorRevealType.InCenter
          );
        }
        break;
      }
    }
  }

  private getHtmlForWebview(
    webview: vscode.Webview,
    context: vscode.ExtensionContext,
    nonce: string
  ): string {
    const inspectorUri = webview.asWebviewUri(
      vscode.Uri.joinPath(context.extensionUri, "media", "inspector.js")
    );

    const inspectorCssUri = webview.asWebviewUri(
      vscode.Uri.joinPath(context.extensionUri, "media", "inspector.css")
    );

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="${inspectorCssUri}">
    <title>Variable Inspector</title>
</head>
<body>
    <div id="inspector-container">
        <div id="header">
            <h2 id="var-name"></h2>
            <button id="btn-close">×</button>
        </div>
        <div id="timeline-view">
            <div id="timeline-list"></div>
            <div id="timeline-metadata"></div>
        </div>
    </div>
    <script nonce="${nonce}" src="${inspectorUri}"></script>
</body>
</html>`;
  }

  dispose(): void {
    this._panel.dispose();
    this._disposed = true;
  }

  [Symbol.dispose](): void {
    this.dispose();
  }
}
