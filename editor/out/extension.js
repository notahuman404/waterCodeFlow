"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/extension.ts
var extension_exports = {};
__export(extension_exports, {
  activate: () => activate,
  deactivate: () => deactivate,
  getActiveFilePath: () => getActiveFilePath,
  getNonce: () => getNonce
});
module.exports = __toCommonJS(extension_exports);
var vscode5 = __toESM(require("vscode"));
var import_crypto2 = require("crypto");

// src/glueClient.ts
var import_child_process = require("child_process");
var import_crypto = require("crypto");
var path = __toESM(require("path"));
var GlueClient = class {
  constructor() {
    this.subprocess = null;
    this.pendingRequests = /* @__PURE__ */ new Map();
    this.readyResolve = null;
    this.lines = [];
    this.ready = new Promise((resolve) => {
      this.readyResolve = resolve;
    });
  }
  /**
   * Spawn Python subprocess running glue adapter.
   * extensionPath is the editor/ directory.
   * We need to traverse up one level to reach the project root where glue/ is located.
   */
  async spawn(extensionPath) {
    return new Promise((resolve, reject) => {
      try {
        const projectRoot = path.dirname(extensionPath);
        this.subprocess = (0, import_child_process.spawn)("python3", ["-m", "glue.adapter"], {
          cwd: projectRoot,
          stdio: ["pipe", "pipe", "pipe"],
          env: { ...process.env }
        });
        this.subprocess.on("error", (err) => {
          console.error("[GlueClient] subprocess error:", err);
          reject(err);
        });
        this.subprocess.stdout.on("data", (data) => {
          this.handleData(data.toString());
        });
        this.subprocess.stderr.on("data", (data) => {
          console.error("[GlueClient] stderr:", data.toString());
        });
        setTimeout(() => {
          if (this.readyResolve) {
            this.readyResolve();
          }
          resolve();
        }, 500);
      } catch (err) {
        reject(err);
      }
    });
  }
  /**
   * Send a command to glue and wait for response.
   */
  async send(command) {
    await this.ready;
    if (!this.subprocess || !this.subprocess.stdin) {
      throw new Error("GlueClient not initialized. Call spawn() first.");
    }
    const id = (0, import_crypto.randomUUID)();
    const fullCommand = { ...command, id };
    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, (response) => {
        if (response.success) {
          resolve(response.result);
        } else {
          reject(
            new Error(
              `[${response.errorType || "GlueError"}] ${response.error}`
            )
          );
        }
      });
      const cmdJson = JSON.stringify(fullCommand) + "\n";
      this.subprocess.stdin.write(cmdJson);
    });
  }
  /**
   * Handle incoming data from subprocess.
   * Accumulates lines and processes complete JSON objects.
   */
  handleData(chunk) {
    const allLines = (this.lines.join("") + chunk).split("\n");
    this.lines = [allLines[allLines.length - 1]];
    for (let i = 0; i < allLines.length - 1; i++) {
      const line = allLines[i].trim();
      if (!line)
        continue;
      try {
        const response = JSON.parse(line);
        const callback = this.pendingRequests.get(response.id);
        if (callback) {
          this.pendingRequests.delete(response.id);
          callback(response);
        } else {
          console.warn(
            "[GlueClient] received response for unknown request:",
            response.id
          );
        }
      } catch (err) {
        console.error("[GlueClient] failed to parse JSON:", line, err);
      }
    }
  }
  /**
   * Kill subprocess.
   */
  kill() {
    if (this.subprocess && !this.subprocess.killed) {
      this.subprocess.kill();
      this.subprocess = null;
    }
  }
  /**
   * Check if subprocess is alive.
   */
  isAlive() {
    return this.subprocess !== null && !this.subprocess.killed;
  }
};
var instance = null;
function getGlueClient() {
  if (!instance) {
    instance = new GlueClient();
  }
  return instance;
}

// src/providers/RecordingsViewProvider.ts
var vscode = __toESM(require("vscode"));
var RecordingsViewProvider = class {
  constructor(context, nonce2) {
    this.context = context;
    this.nonce = nonce2;
    this._activeFile = "";
    this.statusRefreshInterval = null;
  }
  static {
    this.viewType = "watercodeflow.recordings";
  }
  resolveWebviewView(webviewView, context, token) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.joinPath(this.context.extensionUri, "media")
      ]
    };
    webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);
    webviewView.webview.onDidReceiveMessage(async (message) => {
      await this.handleMessage(message);
    });
    this.statusRefreshInterval = setInterval(() => {
      this.refreshStatus();
    }, 2e3);
  }
  setActiveFile(filePath) {
    this._activeFile = filePath;
    this.refreshRecordings();
    this.refreshStatus();
  }
  async refreshStatus() {
    if (!this._view || !this._activeFile)
      return;
    try {
      const glueClient = getGlueClient();
      const status = await glueClient.send({
        command: "getStatus",
        filePath: this._activeFile
      });
      this._view.webview.postMessage({
        type: "statusUpdate",
        status
      });
    } catch (err) {
      console.log("Status refresh error (expected if not recording):", err);
    }
  }
  async refreshRecordings() {
    if (!this._view || !this._activeFile)
      return;
    try {
      const glueClient = getGlueClient();
      const runs = await glueClient.send({
        command: "listRuns",
        filePath: this._activeFile
      });
      this._view.webview.postMessage({
        type: "recordingsUpdate",
        recordings: runs
      });
    } catch (err) {
      console.log("Recordings refresh error:", err);
    }
  }
  async handleMessage(message) {
    const glueClient = getGlueClient();
    switch (message.command) {
      case "startRecording": {
        try {
          const pid = await glueClient.send({
            command: "startRecording",
            filePath: message.filePath,
            interval: message.interval || 0.5
          });
          this._view?.webview.postMessage({
            type: "recordingStarted",
            pid
          });
          this.refreshStatus();
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to start recording: ${err}`
          });
        }
        break;
      }
      case "stopRecording": {
        try {
          await glueClient.send({
            command: "stopRecording",
            filePath: message.filePath
          });
          this._view?.webview.postMessage({
            type: "recordingStopped"
          });
          this.refreshStatus();
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to stop recording: ${err}`
          });
        }
        break;
      }
      case "jumpToTick": {
        try {
          await glueClient.send({
            command: "jumpToTick",
            filePath: message.filePath,
            tickId: message.tickId
          });
          this._view?.webview.postMessage({
            type: "cursorUpdate",
            tick: message.tickId
          });
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to jump to tick: ${err}`
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
            runId: message.runId
          });
          this.refreshRecordings();
          this.refreshStatus();
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to delete run: ${err}`
          });
        }
        break;
      }
    }
  }
  getHtmlForWebview(webview) {
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
  dispose() {
    if (this.statusRefreshInterval) {
      clearInterval(this.statusRefreshInterval);
    }
  }
};

// src/providers/VariablesViewProvider.ts
var vscode2 = __toESM(require("vscode"));
var VariablesViewProvider = class {
  constructor(context, nonce2) {
    this.context = context;
    this.nonce = nonce2;
    this._activeFile = "";
  }
  static {
    this.viewType = "watercodeflow.variables";
  }
  resolveWebviewView(webviewView, context, token) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode2.Uri.joinPath(this.context.extensionUri, "media")
      ]
    };
    webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);
    webviewView.webview.onDidReceiveMessage(async (message) => {
      await this.handleMessage(message);
    });
  }
  setActiveFile(filePath) {
    this._activeFile = filePath;
    this.refreshVariables();
  }
  async refreshVariables() {
    if (!this._view || !this._activeFile)
      return;
    try {
      const glueClient = getGlueClient();
      const variables = await glueClient.send({
        command: "listTrackedVariables",
        filePath: this._activeFile
      });
      this._view.webview.postMessage({
        type: "variablesUpdate",
        variables
      });
    } catch (err) {
      console.log("Variables refresh error:", err);
    }
  }
  async handleMessage(message) {
    const glueClient = getGlueClient();
    switch (message.command) {
      case "inspectVariable": {
        vscode2.commands.executeCommand(
          "watercodeflow.openInspector",
          message.varName
        );
        break;
      }
      case "inferVariables": {
        try {
          const variables = await glueClient.send({
            command: "listTrackedVariables",
            filePath: message.filePath || this._activeFile
          });
          this._view?.webview.postMessage({
            type: "variables",
            variables
          });
        } catch (err) {
          this._view?.webview.postMessage({
            type: "error",
            message: `Failed to infer variables: ${err}`
          });
        }
        break;
      }
    }
  }
  getHtmlForWebview(webview) {
    const variablesUri = webview.asWebviewUri(
      vscode2.Uri.joinPath(this.context.extensionUri, "media", "variables.js")
    );
    const variablesCssUri = webview.asWebviewUri(
      vscode2.Uri.joinPath(
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
  dispose() {
  }
};

// src/panels/VariableInspectionPanel.ts
var vscode3 = __toESM(require("vscode"));
var VariableInspectionPanel = class {
  constructor(context, nonce2, filePath, varName) {
    this.filePath = filePath;
    this.varName = varName;
    this._disposed = false;
    this._panel = vscode3.window.createWebviewPanel(
      "watercodeflow.inspector",
      `Inspector: ${varName}`,
      vscode3.ViewColumn.Beside,
      {
        enableScripts: true,
        localResourceRoots: [
          vscode3.Uri.joinPath(context.extensionUri, "media")
        ]
      }
    );
    this._panel.webview.html = this.getHtmlForWebview(
      this._panel.webview,
      context,
      nonce2
    );
    this._panel.webview.onDidReceiveMessage(async (message) => {
      await this.handleMessage(message);
    });
    this._panel.onDidDispose(() => {
      this._disposed = true;
    });
    this.loadTimeline();
  }
  async loadTimeline() {
    if (this._disposed)
      return;
    try {
      const glueClient = getGlueClient();
      const timeline = await glueClient.send({
        command: "getVariableTimeline",
        filePath: this.filePath,
        variableName: this.varName,
        maxTicks: 200
      });
      this._panel.webview.postMessage({
        type: "timelineLoaded",
        timeline,
        varName: this.varName
      });
    } catch (err) {
      this._panel.webview.postMessage({
        type: "error",
        message: `Failed to load timeline: ${err}`
      });
    }
  }
  async handleMessage(message) {
    const glueClient = getGlueClient();
    switch (message.command) {
      case "scrub": {
        try {
          await glueClient.send({
            command: "jumpToTick",
            filePath: this.filePath,
            tickId: message.tick
          });
          this._panel.webview.postMessage({
            type: "scrubbed",
            tick: message.tick
          });
        } catch (err) {
          this._panel.webview.postMessage({
            type: "error",
            message: `Failed to scrub: ${err}`
          });
        }
        break;
      }
      case "scrollToLine": {
        const editor = vscode3.window.activeTextEditor;
        if (editor) {
          const line = Math.max(0, (message.lineNo || 1) - 1);
          editor.selection = new vscode3.Selection(line, 0, line, 0);
          editor.revealRange(
            new vscode3.Range(line, 0, line, 100),
            vscode3.TextEditorRevealType.InCenter
          );
        }
        break;
      }
    }
  }
  getHtmlForWebview(webview, context, nonce2) {
    const inspectorUri = webview.asWebviewUri(
      vscode3.Uri.joinPath(context.extensionUri, "media", "inspector.js")
    );
    const inspectorCssUri = webview.asWebviewUri(
      vscode3.Uri.joinPath(context.extensionUri, "media", "inspector.css")
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
            <button id="btn-close">\xD7</button>
        </div>
        <div id="timeline-view">
            <div id="timeline-list"></div>
            <div id="timeline-metadata"></div>
        </div>
    </div>
    <script nonce="${nonce2}" src="${inspectorUri}"></script>
</body>
</html>`;
  }
  dispose() {
    this._panel.dispose();
    this._disposed = true;
  }
  [Symbol.dispose]() {
    this.dispose();
  }
};

// src/panels/InsightsPanel.ts
var vscode4 = __toESM(require("vscode"));
var InsightsPanel = class {
  constructor(context, nonce2, filePath, fromTick, toTick) {
    this.filePath = filePath;
    this.fromTick = fromTick;
    this.toTick = toTick;
    this._disposed = false;
    this._panel = vscode4.window.createWebviewPanel(
      "watercodeflow.insights",
      `Insights: ${fromTick} \u2192 ${toTick}`,
      vscode4.ViewColumn.Beside,
      {
        enableScripts: true,
        localResourceRoots: [
          vscode4.Uri.joinPath(context.extensionUri, "media")
        ]
      }
    );
    this._panel.webview.html = this.getHtmlForWebview(
      this._panel.webview,
      context,
      nonce2
    );
    this._panel.webview.onDidReceiveMessage(async (message) => {
      await this.handleMessage(message);
    });
    this._panel.onDidDispose(() => {
      this._disposed = true;
    });
    this.loadInsights();
  }
  async loadInsights() {
    if (this._disposed)
      return;
    try {
      const glueClient = getGlueClient();
      const insights = await glueClient.send({
        command: "getInsights",
        filePath: this.filePath,
        fromTick: this.fromTick.toString(),
        toTick: this.toTick.toString(),
        model: "gemini"
      });
      this._panel.webview.postMessage({
        type: "insightsLoaded",
        insights
      });
    } catch (err) {
      this._panel.webview.postMessage({
        type: "error",
        message: `Failed to load insights: ${err}`
      });
    }
  }
  async handleMessage(message) {
    const glueClient = getGlueClient();
    switch (message.command) {
      case "scrubToTick": {
        try {
          await glueClient.send({
            command: "jumpToTick",
            filePath: this.filePath,
            tickId: message.tick
          });
          this._panel.webview.postMessage({
            type: "scrubbedToTick",
            tick: message.tick
          });
        } catch (err) {
          this._panel.webview.postMessage({
            type: "error",
            message: `Failed to scrub to tick: ${err}`
          });
        }
        break;
      }
      case "highlightLine": {
        const editor = vscode4.window.activeTextEditor;
        if (editor) {
          const line = Math.max(0, (message.lineNo || 1) - 1);
          editor.selection = new vscode4.Selection(line, 0, line, 0);
          editor.revealRange(
            new vscode4.Range(line, 0, line, 100),
            vscode4.TextEditorRevealType.InCenter
          );
        }
        break;
      }
    }
  }
  getHtmlForWebview(webview, context, nonce2) {
    const insightsUri = webview.asWebviewUri(
      vscode4.Uri.joinPath(context.extensionUri, "media", "insights.js")
    );
    const insightsCssUri = webview.asWebviewUri(
      vscode4.Uri.joinPath(context.extensionUri, "media", "insights.css")
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
            <button id="btn-close">\xD7</button>
        </div>
        <div id="insights-content">
            <div id="insights-summary"></div>
            <div id="affected-lines"></div>
        </div>
    </div>
    <script nonce="${nonce2}" src="${insightsUri}"></script>
</body>
</html>`;
  }
  dispose() {
    this._panel.dispose();
    this._disposed = true;
  }
  [Symbol.dispose]() {
    this.dispose();
  }
};

// src/extension.ts
var nonce;
var activeFilePath = "";
var recordingsProvider = null;
var variablesProvider = null;
async function activate(context) {
  console.log("[WaterCodeFlow] Activating...");
  nonce = (0, import_crypto2.randomUUID)();
  const glueClient = getGlueClient();
  try {
    await glueClient.spawn(context.extensionPath);
    console.log("[WaterCodeFlow] Glue client initialized");
  } catch (err) {
    console.error("[WaterCodeFlow] Failed to spawn glue adapter:", err);
    vscode5.window.showErrorMessage(
      "WaterCodeFlow: Failed to start glue adapter. Is Python installed?"
    );
    return;
  }
  context.subscriptions.push(
    vscode5.window.onDidChangeActiveTextEditor((editor) => {
      if (editor && editor.document.languageId === "python") {
        activeFilePath = editor.document.uri.fsPath;
        recordingsProvider?.setActiveFile(activeFilePath);
        variablesProvider?.setActiveFile(activeFilePath);
      }
    })
  );
  recordingsProvider = new RecordingsViewProvider(context, nonce);
  variablesProvider = new VariablesViewProvider(context, nonce);
  context.subscriptions.push(
    vscode5.window.registerWebviewViewProvider(
      "watercodeflow.recordings",
      recordingsProvider,
      { webviewOptions: { retainContextWhenHidden: true } }
    )
  );
  context.subscriptions.push(
    vscode5.window.registerWebviewViewProvider(
      "watercodeflow.variables",
      variablesProvider,
      { webviewOptions: { retainContextWhenHidden: true } }
    )
  );
  context.subscriptions.push(
    vscode5.commands.registerCommand(
      "watercodeflow.startRecording",
      async () => {
        if (!activeFilePath) {
          vscode5.window.showWarningMessage(
            "No Python file is currently active"
          );
          return;
        }
        const interval = await vscode5.window.showInputBox({
          prompt: "Recording interval (seconds)",
          value: "0.5"
        });
        if (interval === void 0)
          return;
        try {
          const pid = await glueClient.send({
            command: "startRecording",
            filePath: activeFilePath,
            interval: parseFloat(interval)
          });
          vscode5.window.showInformationMessage(
            `Recording started (PID: ${pid})`
          );
          recordingsProvider?.refreshStatus();
        } catch (err) {
          vscode5.window.showErrorMessage(`Failed to start recording: ${err}`);
        }
      }
    )
  );
  context.subscriptions.push(
    vscode5.commands.registerCommand("watercodeflow.stopRecording", async () => {
      if (!activeFilePath) {
        vscode5.window.showWarningMessage(
          "No Python file is currently active"
        );
        return;
      }
      try {
        await glueClient.send({
          command: "stopRecording",
          filePath: activeFilePath
        });
        vscode5.window.showInformationMessage("Recording stopped");
        recordingsProvider?.refreshStatus();
      } catch (err) {
        vscode5.window.showErrorMessage(`Failed to stop recording: ${err}`);
      }
    })
  );
  context.subscriptions.push(
    vscode5.commands.registerCommand(
      "watercodeflow.openInspector",
      async (varName) => {
        if (!activeFilePath) {
          vscode5.window.showWarningMessage(
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
    vscode5.commands.registerCommand(
      "watercodeflow.openInsights",
      async (fromTick, toTick) => {
        if (!activeFilePath) {
          vscode5.window.showWarningMessage(
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
function deactivate() {
  console.log("[WaterCodeFlow] Deactivating...");
  const glueClient = getGlueClient();
  glueClient.kill();
}
function getNonce() {
  return nonce;
}
function getActiveFilePath() {
  return activeFilePath;
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  activate,
  deactivate,
  getActiveFilePath,
  getNonce
});
//# sourceMappingURL=extension.js.map
