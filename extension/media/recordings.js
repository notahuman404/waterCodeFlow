/**
 * Recordings view webview script.
 */
(function () {
  const vscode = acquireVsCodeApi();
  const startBtn = document.getElementById("btn-start");
  const stopBtn = document.getElementById("btn-stop");
  const statusDiv = document.getElementById("status");
  const recordingsListDiv = document.getElementById("recordings-list");
  
  let currentStatus = null;
  let currentRecordings = [];
  let activeFile = "";

  // Handle messages from extension
  window.addEventListener("message", (event) => {
    const message = event.data;

    if (message.type === "statusUpdate") {
      currentStatus = message.status;
      updateStatusDisplay();
    } else if (message.type === "recordingsUpdate") {
      currentRecordings = message.recordings || [];
      renderRecordings();
    } else if (message.type === "recordingStarted") {
      statusDiv.textContent = `Recording (PID: ${message.pid})`;
    } else if (message.type === "recordingStopped") {
      statusDiv.textContent = "Stopped";
    } else if (message.type === "cursorUpdate") {
      statusDiv.textContent = `At tick ${message.tick}`;
    } else if (message.type === "error") {
      statusDiv.textContent = `Error: ${message.message}`;
      statusDiv.style.color = "var(--vscode-terminal-ansiRed)";
    }
  });

  startBtn.addEventListener("click", () => {
    vscode.postMessage({
      command: "startRecording",
      filePath: activeFile || "",
      interval: 0.5,
    });
  });

  stopBtn.addEventListener("click", () => {
    vscode.postMessage({
      command: "stopRecording",
      filePath: activeFile || "",
    });
  });

  function updateStatusDisplay() {
    if (!currentStatus) {
      statusDiv.textContent = "Ready";
      return;
    }

    const tick = currentStatus.tick_counter || 0;
    const count = currentStatus.recordings_count || 0;
    statusDiv.textContent = `${count} recordings, tick ${tick}`;
  }

  function renderRecordings() {
    recordingsListDiv.innerHTML = "";

    if (!currentRecordings || currentRecordings.length === 0) {
      recordingsListDiv.innerHTML =
        '<p style="color: var(--vscode-foreground);">No recordings</p>';
      return;
    }

    const list = document.createElement("ul");
    list.style.listStyle = "none";
    list.style.padding = "0";
    list.style.margin = "0";

    currentRecordings.forEach((run) => {
      const li = document.createElement("li");
      li.style.padding = "8px";
      li.style.marginBottom = "4px";
      li.style.backgroundColor = "var(--vscode-editor-background)";
      li.style.borderLeft = "3px solid var(--vscode-terminal-ansiBlue)";
      li.style.cursor = "pointer";

      li.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>Run ${run.run_id}: ticks ${run.start_tick}-${run.end_tick}</span>
          <button class="delete-btn" data-run-id="${run.run_id}">×</button>
        </div>
        <small style="color: var(--vscode-descriptionForeground);">
          ${run.tick_count} ticks, ~${run.estimated_duration_seconds}s
        </small>
      `;

      li.addEventListener("click", () => {
        vscode.postMessage({
          command: "jumpToTick",
          filePath: activeFile || "",
          tickId: run.start_tick,
        });
      });

      const deleteBtn = li.querySelector(".delete-btn");
      if (deleteBtn) {
        deleteBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          vscode.postMessage({
            command: "deleteRun",
            filePath: activeFile || "",
            runId: run.run_id,
          });
        });
      }

      list.appendChild(li);
    });

    recordingsListDiv.appendChild(list);
  }

  // Notify extension that webview is ready
  vscode.postMessage({ command: "webviewReady" });
})();
