/**
 * InsightsPanel: Modal webview for AI insights between ticks.
 */
import * as vscode from "vscode";
import { getGlueClient } from "../glueClient";
import { Insights } from "../types";

export class InsightsPanel {
  private readonly _panel: vscode.WebviewPanel;
  private _disposed = false;

  constructor(
    context: vscode.ExtensionContext,
    nonce: string,
    private filePath: string,
    private fromTick: number,
    private toTick: number
  ) {
    this._panel = vscode.window.createWebviewPanel(
      "watercodeflow.insights",
      `Insights: ${fromTick} → ${toTick}`,
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

    // Load insights data
    this.loadInsights();
  }

  private async loadInsights(): Promise<void> {
    if (this._disposed) return;

    try {
      const glueClient = getGlueClient();
      const insights = await glueClient.send<Insights>({
        command: "getInsights",
        filePath: this.filePath,
        fromTick: this.fromTick.toString(),
        toTick: this.toTick.toString(),
        model: "gemini",
      });

      this._panel.webview.postMessage({
        type: "insightsLoaded",
        insights,
      });
    } catch (err) {
      this._panel.webview.postMessage({
        type: "error",
        message: `Failed to load insights: ${err}`,
      });
    }
  }

  private async handleMessage(message: any): Promise<void> {
    const glueClient = getGlueClient();

    switch (message.command) {
      case "scrubToTick": {
        try {
          await glueClient.send({
            command: "jumpToTick",
            filePath: this.filePath,
            tickId: message.tick,
          });

          this._panel.webview.postMessage({
            type: "scrubbedToTick",
            tick: message.tick,
          });
        } catch (err) {
          this._panel.webview.postMessage({
            type: "error",
            message: `Failed to scrub to tick: ${err}`,
          });
        }
        break;
      }

      case "highlightLine": {
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
    const insightsUri = webview.asWebviewUri(
      vscode.Uri.joinPath(context.extensionUri, "media", "insights.js")
    );

    const insightsCssUri = webview.asWebviewUri(
      vscode.Uri.joinPath(context.extensionUri, "media", "insights.css")
    );

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="${insightsCssUri}">
    <title>Insights</title>
</head>
<body>
    <div id="insights-container">
        <div id="header">
            <h2>Insights</h2>
            <button id="btn-close">×</button>
        </div>
        <div id="insights-content">
            <div id="insights-summary"></div>
            <div id="affected-lines"></div>
        </div>
    </div>
    <script nonce="${nonce}" src="${insightsUri}"></script>
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
