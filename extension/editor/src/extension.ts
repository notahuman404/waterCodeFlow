/**
 * WaterCodeFlow Extension Entry Point
 * Activates glue client, manages webview providers, routes commands.
 */
import * as vscode from "vscode";
import { randomUUID } from "crypto";
import { getGlueClient } from "./glueClient";
import { RecordingsViewProvider } from "./providers/RecordingsViewProvider";
import { VariablesViewProvider } from "./providers/VariablesViewProvider";
import { VariableInspectionPanel } from "./panels/VariableInspectionPanel";
import { InsightsPanel } from "./panels/InsightsPanel";

let nonce: string;
let activeFilePath: string = "";
let recordingsProvider: RecordingsViewProvider | null = null;
let variablesProvider: VariablesViewProvider | null = null;

export async function activate(context: vscode.ExtensionContext) {
  console.log("[WaterCodeFlow] Activating...");

  nonce = randomUUID();

  // Spawn glue subprocess
  const glueClient = getGlueClient();
  try {
    // extensionPath is the editor/ directory
    await glueClient.spawn(context.extensionPath);
    console.log("[WaterCodeFlow] Glue client initialized");
  } catch (err) {
    console.error("[WaterCodeFlow] Failed to spawn glue adapter:", err);
    vscode.window.showErrorMessage(
      "WaterCodeFlow: Failed to start glue adapter. Is Python installed?"
    );
    return;
  }

  // Track active file
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor && editor.document.languageId === "python") {
        activeFilePath = editor.document.uri.fsPath;
        recordingsProvider?.setActiveFile(activeFilePath);
        variablesProvider?.setActiveFile(activeFilePath);
      }
    })
  );

  // Register webview view providers
  recordingsProvider = new RecordingsViewProvider(context, nonce);
  variablesProvider = new VariablesViewProvider(context, nonce);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "watercodeflow.recordings",
      recordingsProvider,
      { webviewOptions: { retainContextWhenHidden: true } }
    )
  );

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "watercodeflow.variables",
      variablesProvider,
      { webviewOptions: { retainContextWhenHidden: true } }
    )
  );

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "watercodeflow.startRecording",
      async () => {
        if (!activeFilePath) {
          vscode.window.showWarningMessage(
            "No Python file is currently active"
          );
          return;
        }

        const interval = await vscode.window.showInputBox({
          prompt: "Recording interval (seconds)",
          value: "0.5",
        });

        if (interval === undefined) return;

        try {
          const pid = await glueClient.send({
            command: "startRecording",
            filePath: activeFilePath,
            interval: parseFloat(interval),
          });

          vscode.window.showInformationMessage(
            `Recording started (PID: ${pid})`
          );
          recordingsProvider?.refreshStatus();
        } catch (err) {
          vscode.window.showErrorMessage(`Failed to start recording: ${err}`);
        }
      }
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("watercodeflow.stopRecording", async () => {
      if (!activeFilePath) {
        vscode.window.showWarningMessage(
          "No Python file is currently active"
        );
        return;
      }

      try {
        await glueClient.send({
          command: "stopRecording",
          filePath: activeFilePath,
        });

        vscode.window.showInformationMessage("Recording stopped");
        recordingsProvider?.refreshStatus();
      } catch (err) {
        vscode.window.showErrorMessage(`Failed to stop recording: ${err}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "watercodeflow.openInspector",
      async (varName: string) => {
        if (!activeFilePath) {
          vscode.window.showWarningMessage(
            "No Python file is currently active"
          );
          return;
        }

        const inspectorPanel = new VariableInspectionPanel(
          context,
          nonce,
          activeFilePath,
          varName
        );
        context.subscriptions.push(inspectorPanel);
      }
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "watercodeflow.openInsights",
      async (fromTick: number, toTick: number) => {
        if (!activeFilePath) {
          vscode.window.showWarningMessage(
            "No Python file is currently active"
          );
          return;
        }

        const insightsPanel = new InsightsPanel(
          context,
          nonce,
          activeFilePath,
          fromTick,
          toTick
        );
        context.subscriptions.push(insightsPanel);
      }
    )
  );

  console.log("[WaterCodeFlow] Extension fully activated");
}

export function deactivate() {
  console.log("[WaterCodeFlow] Deactivating...");

  const glueClient = getGlueClient();
  glueClient.kill();
}

export function getNonce(): string {
  return nonce;
}

export function getActiveFilePath(): string {
  return activeFilePath;
}
