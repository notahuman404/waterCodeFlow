/**
 * RecordingsViewProvider: Manages the Recordings webview sidebar panel.
 * Displays recording list, status, and controls.
 */
import * as vscode from "vscode";
import { getGlueClient } from "../glueClient";
import { getNonce } from "../extension";
import * as path from "path";
import { Run } from "../types";

export class RecordingsViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "watercodeflow.recordings";

  private _view?: vscode.WebviewView;
  private _activeFile: string = "";
  private statusRefreshInterval: any = null;

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

    // Refresh status every 2 seconds
    this.statusRefreshInterval = setInterval(() => {
      this.refreshStatus();
    }, 2000);
  }

  setActiveFile(filePath: string): void {
    this._activeFile = filePath;
    this.refreshRecordings();
    this.refreshStatus();
  }

  async refreshStatus(): Promise<void> {
    if (!this._view || !this._activeFile) return;

    try {
      const glueClient = getGlueClient();
      const status = await glueClient.send({
        command: "getStatus",
        filePath: this._activeFile,
      });

      this._view.webview.postMessage({
        type: "statusUpdate",
        status,
      });
    } catch (err) {
      console.log("Status refresh error (expected if not recording):", err);
    }
  }

  async refreshRecordings(): Promise<void> {
    if (!this._view || !this._activeFile) return;

    try {
      const glueClient = getGlueClient();
      const runs = await glueClient.send<Run[]>({
        command: "listRuns",
        filePath: this._activeFile,
      });

      this._view.webview.postMessage({
        type: "recordingsUpdate",
        recordings: runs,
      });
    } catch (err) {
      console.log("Recordings refresh error:", err);
    }
  }

  private async handleMessage(message: any): Promise<void> {
    const glueClient = getGlueClient();

    switch (message.command) {
      case "startRecording": {
        try {
          const pid = await glueClient.send({
            command: "startRecording",
            filePath: message.filePath,
            interval: message.interval || 0.5,
          });

          this._view?.webview.postMessage({
            type: "recordingStarted",
            pid,
          });

          this.refreshStatus();
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to start recording: ${err}`,
          });
        }
        break;
      }

      case "stopRecording": {
        try {
          await glueClient.send({
            command: "stopRecording",
            filePath: message.filePath,
          });

          this._view?.webview.postMessage({
            type: "recordingStopped",
          });

          this.refreshStatus();
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to stop recording: ${err}`,
          });
        }
        break;
      }

      case "jumpToTick": {
        try {
          await glueClient.send({
            command: "jumpToTick",
            filePath: message.filePath,
            tickId: message.tickId,
          });

          this._view?.webview.postMessage({
            type: "cursorUpdate",
            tick: message.tickId,
          });
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to jump to tick: ${err}`,
          });
        }
        break;
      }

      case "openRun": {
        vscode.commands.executeCommand(
          "watercodeflow.openInspector",
          message.runId
        );
        break;
      }

      case "deleteRun": {
        try {
          await glueClient.send({
            command: "deleteRun",
            filePath: message.filePath,
            runId: message.runId,
          });

          this.refreshRecordings();
          this.refreshStatus();
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to delete run: ${err}`,
          });
        }
        break;
      }
    }
  }

  private getHtmlForWebview(webview: vscode.Webview): string {
    const recordingsUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, "media", "recordings.js")
    );

    const recordingsCssUri = webview.asWebviewUri(
      vscode.Uri.joinPath(
        this.context.extensionUri,
        "media",
        "recordings.css"
      )
    );

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="${recordingsCssUri}">
    <title>Recordings</title>
</head>
<body>
    <div id="recordings-container">
        <div id="controls">
            <button id="btn-start">Start Recording</button>
            <button id="btn-stop">Stop Recording</button>
            <div id="status">Ready</div>
        </div>
        <div id="recordings-list"></div>
    </div>
    <script nonce="${this.nonce}" src="${recordingsUri}"></script>
</body>
</html>`;
  }

  dispose(): void {
    if (this.statusRefreshInterval) {
      clearInterval(this.statusRefreshInterval);
    }
  }
}
