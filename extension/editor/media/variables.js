/**
 * Variables view webview script.
 */
(function () {
  const vscode = acquireVsCodeApi();
  const inferBtn = document.getElementById("btn-infer");
  const variablesListUl = document.getElementById("variables-list");

  let currentVariables = [];
  let activeFile = "";

  window.addEventListener("message", (event) => {
    const message = event.data;

    if (message.type === "variablesUpdate") {
      currentVariables = message.variables || [];
      renderVariables();
    } else if (message.type === "error") {
      const errorMsg = document.createElement("li");
      errorMsg.style.color = "var(--vscode-terminal-ansiRed)";
      errorMsg.textContent = `Error: ${message.message}`;
      variablesListUl.appendChild(errorMsg);
    }
  });

  inferBtn.addEventListener("click", () => {
    vscode.postMessage({
      command: "inferVariables",
      filePath: activeFile || "",
    });
  });

  function renderVariables() {
    variablesListUl.innerHTML = "";

    if (!currentVariables || currentVariables.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No variables tracked";
      li.style.color = "var(--vscode-descriptionForeground)";
      variablesListUl.appendChild(li);
      return;
    }

    currentVariables.forEach((variable) => {
      const li = document.createElement("li");
      li.style.padding = "8px";
      li.style.marginBottom = "4px";
      li.style.backgroundColor = "var(--vscode-list-hoverBackground)";
      li.style.borderRadius = "4px";
      li.style.cursor = "pointer";
      li.style.transition = "all 0.2s ease";

      li.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span title="${variable.name}">${variable.name}</span>
          <span style="font-size: 10px; color: var(--vscode-descriptionForeground); background-color: var(--vscode-editor-background); padding: 2px 6px; border-radius: 3px;">
            ${variable.scope || "unknown"}
          </span>
        </div>
      `;

      li.addEventListener("click", () => {
        vscode.postMessage({
          command: "inspectVariable",
          varName: variable.name,
          filePath: activeFile || "",
        });
      });

      li.addEventListener("mouseenter", () => {
        li.style.backgroundColor = "var(--vscode-list-activeSelectionBackground)";
      });

      li.addEventListener("mouseleave", () => {
        li.style.backgroundColor = "var(--vscode-list-hoverBackground)";
      });

      variablesListUl.appendChild(li);
    });
  }

  vscode.postMessage({ command: "webviewReady" });
})();
