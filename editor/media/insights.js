/**
 * Insights panel webview script.
 */
(function () {
  const vscode = acquireVsCodeApi();
  const closeBtn = document.getElementById("btn-close");
  const summaryDiv = document.getElementById("insights-summary");
  const affectedLinesDiv = document.getElementById("affected-lines");

  let currentInsights = null;

  window.addEventListener("message", (event) => {
    const message = event.data;

    if (message.type === "insightsLoaded") {
      currentInsights = message.insights;
      renderInsights();
    } else if (message.type === "scrubbedToTick") {
      const msg = document.createElement("p");
      msg.textContent = `Scrubbed to tick ${message.tick}`;
      msg.style.fontSize = "11px";
      msg.style.color = "var(--vscode-descriptionForeground)";
      affectedLinesDiv.insertBefore(msg, affectedLinesDiv.firstChild);
    } else if (message.type === "error") {
      summaryDiv.innerHTML = `<p style="color: var(--vscode-terminal-ansiRed);">Error: ${message.message}</p>`;
    }
  });

  closeBtn.addEventListener("click", () => {
    vscode.postMessage({ command: "close" });
  });

  function renderInsights() {
    if (!currentInsights) {
      summaryDiv.innerHTML = "<p>No insights available</p>";
      return;
    }

    const insights = currentInsights;

    // Render summary
    summaryDiv.innerHTML = `
      <div style="margin-bottom: 16px;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px;">AI Analysis</h3>
        <p style="margin: 0; font-size: 12px; line-height: 1.5;">
          ${escapeHtml(insights.diff_summary || "No summary available")}
        </p>
        <div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;">
          <span style="font-size: 10px; background-color: var(--vscode-editor-background); padding: 4px 8px; border-radius: 3px;">
            Model: ${escapeHtml(insights.model || "unknown")}
          </span>
          <span style="font-size: 10px; background-color: var(--vscode-editor-background); padding: 4px 8px; border-radius: 3px;">
            Type: ${escapeHtml(insights.change_type || "unknown")}
          </span>
          <span style="font-size: 10px; background-color: var(--vscode-editor-background); padding: 4px 8px; border-radius: 3px;">
            Severity: ${escapeHtml(insights.severity || "medium")}
          </span>
        </div>
      </div>
    `;

    // Render affected lines
    affectedLinesDiv.innerHTML = "<h3 style='margin: 0 0 8px 0; font-size: 14px;'>Affected Lines</h3>";

    if (!insights.affected_lines || insights.affected_lines.length === 0) {
      affectedLinesDiv.innerHTML += "<p>No specific lines affected</p>";
      return;
    }

    const list = document.createElement("ul");
    list.style.listStyle = "none";
    list.style.padding = "0";
    list.style.margin = "0";

    insights.affected_lines.forEach((lineNo) => {
      const li = document.createElement("li");
      li.style.padding = "8px";
      li.style.marginBottom = "4px";
      li.style.backgroundColor = "var(--vscode-list-hoverBackground)";
      li.style.borderRadius = "4px";
      li.style.cursor = "pointer";
      li.textContent = `Line ${lineNo}`;

      li.addEventListener("click", () => {
        vscode.postMessage({
          command: "highlightLine",
          lineNo: lineNo,
        });
      });

      li.addEventListener("mouseenter", () => {
        li.style.backgroundColor = "var(--vscode-list-activeSelectionBackground)";
      });

      li.addEventListener("mouseleave", () => {
        li.style.backgroundColor = "var(--vscode-list-hoverBackground)";
      });

      list.appendChild(li);
    });

    affectedLinesDiv.appendChild(list);
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  vscode.postMessage({ command: "webviewReady" });
})();
