(function(){
'use strict';
const vscode = acquireVsCodeApi();
let recordings = [];
let filePath = '';
let activeDot = 0;
let currentVar = null; // name of variable currently inspected

function highlightJson(json){
  return json
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/(\"(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*\"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, match => {
      let cls = 'json-number';
      if (/^"/.test(match)) { cls = /:$/.test(match) ? 'json-key' : 'json-string'; }
      else if (/true|false/.test(match)) { cls = 'json-bool'; }
      else if (/null/.test(match)) { cls = 'json-null'; }
      return '<span class="' + cls + '">' + match + '</span>';
    });
}

function getVarData(varName, recIdx) {
  const rec = recordings[recIdx];
  if (!rec) { return null; }
  const vars = rec.vars || rec.variables || [];
  return vars.find(v => (v.name || v) === varName) || null;
}

function getAllVarNames() {
  const names = new Set();
  recordings.forEach(rec => {
    (rec.vars || rec.variables || []).forEach(v => names.add(v.name || String(v)));
  });
  return Array.from(names);
}

function renderCode(varName, recIdx) {
  const codeEl = document.getElementById('vi-code');
  const vd = getVarData(varName, recIdx);
  const val = vd ? (vd.value !== undefined ? vd.value : null) : null;
  if (val !== null) {
    try {
      codeEl.innerHTML = highlightJson(JSON.stringify(val, null, 2));
    } catch(_) {
      codeEl.textContent = String(val);
    }
  } else {
    codeEl.textContent = varName ? 'No data for "' + varName + '" in this run.' : 'Select a variable to inspect.';
  }
}

function renderMeta(varName, recIdx) {
  const el = document.getElementById('vi-meta-list');
  el.innerHTML = '';
  const rec = recordings[recIdx];
  const vd = rec ? getVarData(varName, recIdx) : null;

  const metaRows = [
    { label: 'Variable name', value: varName || '—' },
    { label: 'Scope',         value: vd ? (vd.scope || 'global') : '—' },
    { label: 'Type',          value: vd ? (vd.type || (vd.value !== undefined ? typeof vd.value : '—')) : '—' },
    { label: 'File Path',     value: rec ? (rec.filePath || rec.file_path || filePath || '—') : (filePath || '—') },
    { label: 'Line no.',      value: vd && vd.line_no != null ? String(vd.line_no) : '—' },
    { label: 'First seen',    value: recordings.length > 0 ? (recordings[0].timestamp || '—') : '—' },
    { label: 'Last seen',     value: rec ? (rec.timestamp || '—') : '—' },
    { label: 'Total runs',    value: String(recordings.length) },
    { label: 'Run index',     value: recordings.length > 0 ? String(recIdx + 1) + ' of ' + recordings.length : '—' },
  ];

  metaRows.forEach(m => {
    const row = document.createElement('div'); row.className = 'vi-meta-row';
    const lbl = document.createElement('div'); lbl.className = 'vi-meta-label'; lbl.textContent = m.label;
    const val = document.createElement('div'); val.className = 'vi-meta-value'; val.textContent = m.value;
    row.appendChild(lbl); row.appendChild(val); el.appendChild(row);
  });
}

function renderVarSelector() {
  // Build a small selector row at the top for choosing which variable to inspect
  let sel = document.getElementById('vi-var-selector');
  if (!sel) {
    sel = document.createElement('select');
    sel.id = 'vi-var-selector';
    sel.style.cssText = 'margin:4px 8px 8px;padding:3px 6px;font-size:12px;background:var(--vscode-dropdown-background);color:var(--vscode-dropdown-foreground);border:1px solid var(--vscode-dropdown-border);border-radius:3px;width:calc(100% - 16px)';
    const codeEl = document.getElementById('vi-code');
    codeEl.parentNode.insertBefore(sel, codeEl);
    sel.addEventListener('change', () => {
      currentVar = sel.value || null;
      renderCode(currentVar, activeDot);
      renderMeta(currentVar, activeDot);
      renderDots();
    });
  }
  const names = getAllVarNames();
  sel.innerHTML = '';
  if (names.length === 0) {
    const opt = document.createElement('option'); opt.value = ''; opt.textContent = '(no variables captured)';
    sel.appendChild(opt);
    currentVar = null;
  } else {
    const placeholder = document.createElement('option'); placeholder.value = ''; placeholder.textContent = 'Select variable…';
    sel.appendChild(placeholder);
    names.forEach(n => {
      const opt = document.createElement('option'); opt.value = n; opt.textContent = n;
      if (n === currentVar) { opt.selected = true; }
      sel.appendChild(opt);
    });
    if (!currentVar && names.length > 0) {
      currentVar = names[0];
      sel.value = currentVar;
    }
  }
}

function renderDots() {
  const total = recordings.length;
  const el = document.getElementById('vi-dots'); el.innerHTML = '';
  const timeEl = document.getElementById('vi-time');
  if (total === 0) {
    timeEl.textContent = '—';
    return;
  }
  recordings.forEach((rec, i) => {
    const d = document.createElement('div'); d.className = 'vi-dot' + (i === activeDot ? ' active' : '');
    const ts = rec.timestamp ? new Date(rec.timestamp).toLocaleTimeString() : String(i + 1);
    d.title = 'Run #' + (i + 1) + ' — ' + ts;
    d.style.background = i === activeDot ? '' : '#f5a623';
    d.addEventListener('click', () => {
      activeDot = i;
      renderDots();
      renderCode(currentVar, activeDot);
      renderMeta(currentVar, activeDot);
      const rec = recordings[i];
      if (rec) {
        timeEl.textContent = rec.timestamp ? new Date(rec.timestamp).toLocaleTimeString() : String(i);
      }
    });
    el.appendChild(d);
  });
  const activeRec = recordings[activeDot];
  timeEl.textContent = activeRec && activeRec.timestamp
    ? new Date(activeRec.timestamp).toLocaleTimeString()
    : '—';
}

function renderSnippet() {
  const snippetEl = document.getElementById('vi-snippet');
  if (!snippetEl) { return; }
  if (!currentVar) {
    snippetEl.textContent = '# Select a variable above to see its value history';
    return;
  }
  // Show a summary of how many runs captured this variable
  const runsWithVar = recordings.filter(rec =>
    (rec.vars || rec.variables || []).some(v => (v.name || v) === currentVar)
  ).length;
  const totalRuns = recordings.length;
  snippetEl.textContent =
    '# Variable: ' + currentVar + '\n' +
    '# Captured in ' + runsWithVar + ' of ' + totalRuns + ' run' + (totalRuns !== 1 ? 's' : '') + '\n' +
    '# Use the timeline dots below to step through runs';
}

// Initial empty state
document.getElementById('vi-code').textContent = 'Open a Python or JS file and press ▶ to capture variable data.';
renderMeta(null, 0);
renderDots();

document.getElementById('btn-download').addEventListener('click', () => {
  if (!currentVar) {
    alert('Select a variable first.');
    return;
  }
  const data = recordings.map((rec, i) => ({
    run: i + 1,
    timestamp: rec.timestamp,
    filePath: rec.filePath || rec.file_path || filePath,
    value: getVarData(currentVar, i)?.value
  }));
  // In VS Code webviews, URL.createObjectURL is not available.
  // Ask extension host to save the file via file dialog.
  vscode.postMessage({ command: 'exportTimeline', varName: currentVar, data });
});

document.getElementById('btn-print').addEventListener('click', () => {
  const code = document.getElementById('vi-code').textContent;
  console.log('[WaterCodeFlow] Variable "' + (currentVar || '?') + '":\n' + code);
});

window.addEventListener('message', evt => {
  const msg = evt.data;
  if (msg.command === 'setData') {
    filePath = msg.filePath || '';
    recordings = msg.recordings || [];
    activeDot = Math.max(0, recordings.length - 1);

    renderVarSelector();
    renderCode(currentVar, activeDot);
    renderMeta(currentVar, activeDot);
    renderDots();
    renderSnippet();

    // Update file path
  
  }
});

vscode.postMessage({ command: 'ready' });
})();
