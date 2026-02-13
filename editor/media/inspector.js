/**
 * Variable Inspector panel webview script.
 */
(function () {
  const vscode = acquireVsCodeApi();
  const varNameH2 = document.getElementById("var-name");
  const closeBtn = document.getElementById("btn-close");
  const timelineList = document.getElementById("timeline-list");
  const timelineMetadata = document.getElementById("timeline-metadata");

  let currentTimeline = [];
  let currentVarName = "";

  window.addEventListener("message", (event) => {
    const message = event.data;

    if (message.type === "timelineLoaded") {
      currentTimeline = message.timeline || [];
      currentVarName = message.varName;
      varNameH2.textContent = currentVarName;
      renderTimeline();
    } else if (message.type === "scrubbed") {
      updateMetadata(`Scrubbed to tick ${message.tick}`);
    } else if (message.type === "error") {
      timelineList.innerHTML = `<p style="color: var(--vscode-terminal-ansiRed);">Error: ${message.message}</p>`;
    }
  });

  closeBtn.addEventListener("click", () => {
    vscode.postMessage({ command: "close" });
  });

  function renderTimeline() {
    timelineList.innerHTML = "";

    if (!currentTimeline || currentTimeline.length === 0) {
      timelineList.innerHTML =
        '<p style="color: var(--vscode-descriptionForeground);">No timeline data</p>';
      return;
    }

    currentTimeline.forEach((entry, idx) => {
      const div = document.createElement("div");
      div.className = "timeline-entry";
      div.style.marginBottom = "12px";
      div.style.paddingBottom = "12px";
      div.style.borderBottom = "1px solid var(--vscode-editor-lineHighlightBackground)";
      div.style.cursor = "pointer";

      div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;">
          <strong>Line ${entry.line_no}</strong>
          <span style="font-size: 10px; color: var(--vscode-descriptionForeground);">Tick: ${entry.tick}</span>
        </div>
        <code style="display: block; background-color: var(--vscode-editor-background); padding: 8px; border-radius: 4px; font-size: 11px; overflow-x: auto; white-space: pre-wrap; word-break: break-all;">
          ${escapeHtml(entry.snippet)}
        </code>
        <p style="margin: 6px 0 0 0; font-size: 11px; color: var(--vscode-descriptionForeground);">
          Matches: ${entry.match_count}
        </p>
      `;

      div.addEventListener("click", () => {
        vscode.postMessage({
          command: "scrollToLine",
          lineNo: entry.line_no,
        });
      });

      timelineList.appendChild(div);
    });
  }

  function updateMetadata(text) {
    timelineMetadata.innerHTML = `<p style="padding: 8px; background-color: var(--vscode-editor-lineHighlightBackground); border-radius: 4px; font-size: 11px;">${text}</p>`;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  vscode.postMessage({ command: "webviewReady" });
})();
