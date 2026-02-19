(function(){
'use strict';
const vscode = acquireVsCodeApi();
let recordings = [];
let runs = [];
let filePath = '';
let activeDot = 0;
let selectedCard = null;

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

function buildVarCards(recs) {
  // Collect unique variables across all recordings
  const varMap = {};
  recs.forEach((rec, recIdx) => {
    const vars = rec.vars || rec.variables || [];
    vars.forEach(v => {
      const name = v.name || String(v);
      if (!varMap[name]) {
        varMap[name] = { id: name, label: name, versions: [], total: 0 };
      }
      varMap[name].versions.push({ recIdx, value: v.value, timestamp: rec.timestamp });
      varMap[name].total = varMap[name].versions.length;
    });
  });
  return Object.values(varMap);
}

function buildMetaBlocks(recs) {
  const varMap = {};
  recs.forEach(rec => {
    const vars = rec.vars || rec.variables || [];
    vars.forEach(v => {
      const name = v.name || String(v);
      if (!varMap[name]) {
        varMap[name] = {
          title: name,
          rows: [
            { label: 'Variable name:', value: name },
            { label: 'Scope:',         value: v.scope || 'global' },
            { label: 'Type:',          value: v.type || typeof v.value || '—' },
            { label: 'File Path:',     value: rec.filePath || rec.file_path || filePath || '—' },
            { label: 'Line no.:',      value: v.line_no != null ? String(v.line_no) : '—' },
            { label: 'Total versions:', value: String(recs.filter(r =>
              (r.vars || r.variables || []).some(x => (x.name || x) === name)
            ).length) },
          ]
        };
      }
    });
  });
  return Object.values(varMap);
}

function renderCards(cards) {
  const left = document.getElementById('ri-left');
  left.innerHTML = '';

  if (cards.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:16px;color:var(--vscode-descriptionForeground);font-style:italic;font-size:12px';
    empty.textContent = 'No variable data captured yet. Run a Python or JS file with ▶ to start recording.';
    left.appendChild(empty);
    return;
  }

  const cardEls = {};
  cards.forEach(card => {
    const cardEl = document.createElement('div'); cardEl.className = 'var-card'; cardEl.id = 'card-' + card.id;
    const hdr = document.createElement('div'); hdr.className = 'var-card-header'; hdr.textContent = card.label;
    const body = document.createElement('div'); body.className = 'var-card-body';

    // Show latest value
    const latestVer = card.versions[card.versions.length - 1];
    const displayVal = latestVer ? latestVer.value : null;
    try {
      body.innerHTML = highlightJson(JSON.stringify(displayVal !== undefined && displayVal !== null ? displayVal : '(no value)', null, 2));
    } catch(_) {
      body.textContent = String(displayVal);
    }

    const footer = document.createElement('div'); footer.className = 'var-card-footer';
    footer.textContent = 'Version ' + card.total + ' of ' + card.total;
    const bar = document.createElement('div'); bar.className = 'var-progress-bar';
    const fill = document.createElement('div'); fill.className = 'var-progress-fill';
    fill.style.width = '100%';
    bar.appendChild(fill);
    cardEl.appendChild(hdr); cardEl.appendChild(body); cardEl.appendChild(footer); cardEl.appendChild(bar);
    cardEl.addEventListener('click', () => {
      selectedCard = selectedCard === card.id ? null : card.id;
      Object.keys(cardEls).forEach(id => cardEls[id].classList.toggle('selected', id === selectedCard));
      if (selectedCard) {
        const b = document.getElementById('meta-block-' + card.id);
        if (b) { b.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      }
    });
    left.appendChild(cardEl); cardEls[card.id] = cardEl;
  });
}

function renderMetaBlocks(blocks) {
  const el = document.getElementById('ri-meta-blocks'); el.innerHTML = '';
  if (blocks.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:12px;color:var(--vscode-descriptionForeground);font-size:12px;font-style:italic';
    empty.textContent = 'No metadata available.';
    el.appendChild(empty); return;
  }
  blocks.forEach(block => {
    const blockEl = document.createElement('div'); blockEl.className = 'ri-meta-block'; blockEl.id = 'meta-block-' + block.title;
    const title = document.createElement('div'); title.className = 'ri-meta-block-title'; title.textContent = block.title;
    blockEl.appendChild(title);
    block.rows.forEach(r => {
      const row = document.createElement('div'); row.className = 'ri-meta-row';
      const lbl = document.createElement('div'); lbl.className = 'ri-meta-label'; lbl.textContent = r.label;
      const val = document.createElement('div'); val.className = 'ri-meta-value'; val.textContent = r.value;
      row.appendChild(lbl); row.appendChild(val); blockEl.appendChild(row);
    });
    el.appendChild(blockEl);
  });
}

function renderDots() {
  const total = recordings.length;
  const el = document.getElementById('ri-dots'); el.innerHTML = '';
  const badge = document.getElementById('ri-step-badge');
  if (total === 0) {
    badge.textContent = 'No runs yet';
    return;
  }
  recordings.forEach((rec, i) => {
    const d = document.createElement('div'); d.className = 'ri-dot' + (i === activeDot ? ' active' : '');
    const ts = rec.timestamp ? new Date(rec.timestamp).toLocaleTimeString() : String(i + 1);
    d.title = 'Run #' + (i + 1) + ' — ' + ts;
    d.addEventListener('click', () => {
      activeDot = i; renderDots();
      refreshForDot(i);
    });
    el.appendChild(d);
  });
  badge.textContent = 'Run #' + (activeDot + 1) + ' of ' + total;
}

function refreshForDot(idx) {
  const rec = recordings[idx];
  if (!rec) { return; }
  document.getElementById('ri-step-badge').textContent = 'Run #' + (idx + 1) + ' of ' + recordings.length;
  const titleEl = document.getElementById('ri-run-title');
  titleEl.textContent = 'Run #' + (idx + 1) + ' — ' + (rec.filePath || rec.file_path || filePath || '').split(/[\\/]/).pop();
  document.getElementById('ri-status').textContent = 'Exit: ' + (rec.exitCode != null ? rec.exitCode : '?') + '  Duration: ' + fmtMs(rec.durationMs);
  document.getElementById('ri-filepath').textContent = rec.filePath || rec.file_path || filePath || '—';

  const cards = buildVarCards([rec]);
  renderCards(cards);
  renderMetaBlocks(buildMetaBlocks([rec]));
}

function fmtMs(ms) {
  if (!ms) { return '—'; }
  return ms < 1000 ? ms + 'ms' : (ms / 1000).toFixed(2) + 's';
}

function renderRun(recData) {
  const titleEl = document.getElementById('ri-run-title');
  const statusEl = document.getElementById('ri-status');
  const fpEl = document.getElementById('ri-filepath');
  if (recData) {
    const runNum = recordings.indexOf(recData) + 1 || 1;
    titleEl.textContent = 'Run #' + runNum + ' — ' + (recData.filePath || recData.file_path || '').split(/[\\/]/).pop();
    statusEl.textContent = 'Exit: ' + (recData.exitCode != null ? recData.exitCode : '?') + '  Duration: ' + fmtMs(recData.durationMs);
    fpEl.textContent = recData.filePath || recData.file_path || filePath || '—';
  } else {
    titleEl.textContent = 'Run Recording Inspection';
    statusEl.textContent = 'Open a file and press ▶ to record';
    fpEl.textContent = filePath || '—';
  }
  document.getElementById('ri-lineno').innerHTML = 'File: <strong style="color:var(--wcf-teal)">—</strong>';
}

// Initial empty state
renderCards([]);
renderMetaBlocks([]);
renderDots();
renderRun(null);

document.getElementById('ri-back').addEventListener('click', () => {
  vscode.postMessage({ command: 'close' });
});

window.addEventListener('message', evt => {
  const msg = evt.data;
  if (msg.command === 'setData') {
    filePath = msg.filePath || '';
    recordings = msg.recordings || [];
    runs = msg.runs || [];

    // Merge run metadata into recordings if available
    if (runs.length > 0 && recordings.length === 0) {
      // Runs from glue adapter — display them
      recordings = runs.map(r => ({
        runId: r.run_id || r.runId,
        filePath: r.file_path || r.filePath || filePath,
        exitCode: r.exit_code != null ? r.exit_code : r.exitCode,
        durationMs: r.duration_ms || r.durationMs,
        timestamp: r.timestamp || r.started_at,
        vars: r.vars || r.variables || [],
      }));
    }

    activeDot = Math.max(0, recordings.length - 1);
    renderDots();
    if (recordings.length > 0) {
      refreshForDot(activeDot);
    } else {
      renderRun(null);
      renderCards([]);
      renderMetaBlocks([]);
    }
    document.getElementById('ri-filepath').textContent = filePath || '—';
  }
});

// Open Variable Inspector button
const openViBtn = document.getElementById('ri-open-vi');
if (openViBtn) {
  openViBtn.addEventListener('click', () => {
    vscode.postMessage({ command: 'openVariableInspector' });
  });
}

vscode.postMessage({ command: 'ready' });
})();
