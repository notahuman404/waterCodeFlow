(function(){
'use strict';
const vscode = acquireVsCodeApi();

function getVal(id) {
  const el = document.getElementById(id);
  if (!el) return undefined;
  if (el.type === 'checkbox') return el.checked;
  if (el.type === 'number') return parseFloat(el.value) || 0;
  return el.value;
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  if (el.type === 'checkbox') { el.checked = !!val; }
  else if (el.tagName === 'SELECT') {
    // Match by value or text
    const opts = Array.from(el.options);
    const match = opts.find(o => o.value === String(val) || o.text === String(val));
    if (match) el.value = match.value;
  }
  else { el.value = val !== undefined && val !== null ? val : ''; }
}

document.getElementById('saveBtn').addEventListener('click', () => {
  vscode.postMessage({
    command: 'saveSettings',
    trackThreads:    getVal('trackThreads'),
    trackLocals:     getVal('trackLocals'),
    trackSql:        getVal('trackSql'),
    trackAll:        getVal('trackAll'),
    samplingInterval:getVal('samplingInterval'),
    daemonThreads:   parseInt(document.getElementById('daemonThreads').value) || 4,
    aiModel:         getVal('aiModel'),
    logLevel:        getVal('logLevel'),
    mutationDepth:   getVal('mutationDepth'),
    filesScope:      getVal('filesScope'),
    maxQueueSize:    parseInt(document.getElementById('maxQueueSize').value) || 1000,
    customProcessor: getVal('customProcessor'),
  });
});

document.getElementById('browseBtn').addEventListener('click', () => {
  vscode.postMessage({ command: 'browseProcessor' });
});

document.getElementById('resetBtn').addEventListener('click', () => {
  if (confirm('Reset all recordings for the current file? This cannot be undone.')) {
    vscode.postMessage({ command: 'resetRecording' });
  }
});

document.getElementById('bgBtn').addEventListener('click', () => {
  vscode.postMessage({ command: 'backgroundRecording' });
});

window.addEventListener('message', evt => {
  const msg = evt.data;
  if (msg.command === 'loadSettings' && msg.settings) {
    const s = msg.settings;
    setVal('trackThreads',    s.trackThreads);
    setVal('trackLocals',     s.trackLocals);
    setVal('trackSql',        s.trackSql);
    setVal('trackAll',        s.trackAll);
    setVal('samplingInterval',s.samplingInterval);
    setVal('daemonThreads',   s.daemonThreads);
    setVal('aiModel',         s.aiModel);
    setVal('logLevel',        s.logLevel);
    setVal('mutationDepth',   s.mutationDepth);
    setVal('filesScope',      s.filesScope);
    setVal('maxQueueSize',    s.maxQueueSize);
    setVal('customProcessor', s.customProcessor);
  } else if (msg.command === 'setProcessor' && msg.path) {
    setVal('customProcessor', msg.path);
  }
});

// Tell extension the webview is ready to receive settings
vscode.postMessage({ command: 'ready' });
})();
