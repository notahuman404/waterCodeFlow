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
  const v = vars.find(v => (v.name || v) === varName);
  if (!v) return null;
  // If we have mutations array, use it
  if (v.mutations) return v.mutations[v.mutations.length - 1];
  return v;
}

function getMutations(varName) {
    const all = [];
    recordings.forEach(rec => {
        const vars = rec.vars || rec.variables || [];
        const v = vars.find(x => (x.name || x) === varName);
        if (v && v.mutations) {
            v.mutations.forEach(m => all.push({ ...m, timestamp: rec.timestamp }));
        } else if (v) {
            all.push({ ...v, timestamp: rec.timestamp });
        }
    });
    return all.sort((a, b) => (a.ts_ns || 0) - (b.ts_ns || 0));
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
  const el = document.getElementById('vi-dots'); el.innerHTML = '';
  const timeEl = document.getElementById('vi-time');

  if (!currentVar) {
      timeEl.textContent = '—';
      return;
  }

  const mutations = getMutations(currentVar);
  if (mutations.length === 0) {
    timeEl.textContent = '—';
    return;
  }

  mutations.forEach((mut, i) => {
    const d = document.createElement('div'); d.className = 'vi-dot' + (i === activeDot ? ' active' : '');
    const ts = mut.timestamp ? new Date(mut.timestamp).toLocaleTimeString() : '';
    d.title = 'Mutation #' + (i + 1) + (ts ? ' — ' + ts : '');
    d.style.background = i === activeDot ? '' : '#f5a623';
    d.addEventListener('click', () => {
      activeDot = i;
      renderDots();

      // Update display with this mutation's data
      const codeEl = document.getElementById('vi-code');
      const val = mut.value;
      if (val !== null) {
        try {
          codeEl.innerHTML = highlightJson(JSON.stringify(val, null, 2));
        } catch(_) {
          codeEl.textContent = String(val);
        }
      }

      // Update metadata
      const metaEl = document.getElementById('vi-meta-list');
      metaEl.innerHTML = '';
      const metaRows = [
        { label: 'Variable name', value: currentVar || '—' },
        { label: 'Scope',         value: mut.scope || 'global' },
        { label: 'Type',          value: mut.type || (mut.value !== undefined ? typeof mut.value : '—') },
        { label: 'File Path',     value: mut.file || filePath || '—' },
        { label: 'Line no.',      value: mut.line_no != null ? String(mut.line_no) : '—' },
        { label: 'Timestamp',     value: mut.timestamp ? new Date(mut.timestamp).toLocaleString() : '—' },
        { label: 'Mutation ID',   value: String(i + 1) },
      ];
      metaRows.forEach(m => {
        const row = document.createElement('div'); row.className = 'vi-meta-row';
        const lbl = document.createElement('div'); lbl.className = 'vi-meta-label'; lbl.textContent = m.label;
        const val = document.createElement('div'); val.className = 'vi-meta-value'; val.textContent = m.value;
        row.appendChild(lbl); row.appendChild(val); metaEl.appendChild(row);
      });

      timeEl.textContent = mut.timestamp ? new Date(mut.timestamp).toLocaleTimeString() : '—';
    });
    el.appendChild(d);
  });

  const activeMut = mutations[activeDot];
  if (activeMut) {
    timeEl.textContent = activeMut.timestamp ? new Date(activeMut.timestamp).toLocaleTimeString() : '—';
  }
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
