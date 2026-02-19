(function () {
'use strict';
const vscode = acquireVsCodeApi();
const container = document.getElementById('recordings-container');

// ── Helpers ──────────────────────────────────────────────────────────────────

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) { e.className = cls; }
  if (html !== undefined) { e.innerHTML = html; }
  return e;
}

function fmtDuration(ms) {
  if (ms == null || ms === 0) { return '—'; }
  if (ms < 1000) { return ms + 'ms'; }
  return (ms / 1000).toFixed(2) + 's';
}

function fmtTime(iso) {
  if (!iso) { return '—'; }
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      + '  ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (_) { return iso; }
}

function fmtExit(code) {
  if (code == null) { return ''; }
  return code === 0 ? 'exit 0' : 'exit ' + code;
}

// ── Run log panel ─────────────────────────────────────────────────────────────

let runLogEl = null;

function ensureRunLog() {
  if (runLogEl) { return runLogEl; }
  runLogEl = el('div', 'run-log');
  runLogEl.appendChild(el('div', 'run-log-title', '⟳ Run output'));
  const pre = el('pre', 'run-log-pre', '');
  pre.id = 'run-log-pre';
  runLogEl.appendChild(pre);
  container.insertBefore(runLogEl, container.firstChild);
  return runLogEl;
}

function appendRunLog(text) {
  ensureRunLog();
  const pre = document.getElementById('run-log-pre');
  if (pre) { pre.textContent += text; pre.scrollTop = pre.scrollHeight; }
}

function clearRunLog() {
  if (runLogEl) { runLogEl.remove(); runLogEl = null; }
}

// ── Recording card ────────────────────────────────────────────────────────────

function buildRecordingCard(r, runNumber) {
  const card = el('div', 'rec-card');
  const runId = r.runId || r.run_id || '';
  card.dataset.runId = runId;
  card.dataset.expanded = 'false';

  // Header
  const header = el('div', 'rec-card-header');
  header.setAttribute('role', 'button');
  header.setAttribute('tabindex', '0');
  header.setAttribute('aria-expanded', 'false');

  const chevron = el('span', 'rec-chevron', '▶');

  // Show "Run #N" with actual run number, not the runId string
  const title = el('span', 'rec-card-title');
  title.textContent = 'Run #' + runNumber;

  // Also show filename as secondary info
  const fname = (r.filePath || r.file_path || '').split(/[\\/]/).pop() || '';
  const subtitle = el('span', 'rec-card-subtitle');
  subtitle.textContent = fname;

  const meta = el('span', 'rec-card-meta');
  const parts = [
    r.language || '',
    fmtDuration(r.durationMs),
    fmtTime(r.timestamp),
    fmtExit(r.exitCode),
  ].filter(Boolean);
  meta.textContent = parts.join('  ·  ');

  const exitOk = (r.exitCode === 0 || r.exitCode == null);
  const badge = el('span', 'rec-status-badge ' + (exitOk ? 'badge-ok' : 'badge-err'));
  badge.textContent = exitOk ? '✓' : '✗';

  const actions = el('div', 'rec-card-actions');
  actions.addEventListener('click', e => e.stopPropagation());

  const exportBtn = el('button', 'rec-action-btn', '⬆ Export');
  exportBtn.title = 'Export recording as JSON';
  const deleteBtn = el('button', 'rec-action-btn rec-action-delete', '✕');
  deleteBtn.title = 'Delete this recording';

  actions.appendChild(exportBtn);
  actions.appendChild(deleteBtn);

  header.appendChild(chevron);
  header.appendChild(title);
  header.appendChild(subtitle);
  header.appendChild(meta);
  header.appendChild(badge);
  header.appendChild(actions);

  // Detail section
  const detail = el('div', 'rec-detail');
  detail.setAttribute('aria-hidden', 'true');
  detail.hidden = true;

  // Run metadata table
  const metaTable = el('table', 'rec-meta-table');
  const rows = [
    ['Run #',     String(runNumber)],
    ['Run ID',    runId || '—'],
    ['File',      r.filePath || r.file_path || '—'],
    ['Language',  r.language || '—'],
    ['Exit code', r.exitCode != null ? String(r.exitCode) : '—'],
    ['Duration',  fmtDuration(r.durationMs)],
    ['Timestamp', r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'],
  ];
  rows.forEach(([k, v]) => {
    const tr = el('tr', '');
    tr.innerHTML = '<td class="rec-meta-key">' + k + '</td><td class="rec-meta-val">' + v + '</td>';
    metaTable.appendChild(tr);
  });
  detail.appendChild(metaTable);

  // Variables captured by watcher
  const vars = r.vars || r.variables || [];
  if (vars.length > 0) {
    detail.appendChild(el('div', 'rec-detail-section-title', 'Captured variables'));
    const table = el('table', 'rec-var-table');
    table.innerHTML = '<thead><tr><th>Name</th><th>Value</th><th>Evolutions</th></tr></thead>';
    const tbody = el('tbody', '');
    vars.forEach(v => {
      const tr = el('tr', '');
      const name = v.name || v;
      const val  = v.value != null ? v.value : '—';
      const evo  = v.evolutions != null ? v.evolutions : 0;
      tr.innerHTML = '<td class="rec-var-name-cell">' + name + '</td><td class="rec-var-val" data-varname="' + name + '">' + val + '</td><td>' + evo + '</td>';
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    detail.appendChild(table);
  }

  // stdout
  const stdout = (r.stdout || '').trim();
  if (stdout) {
    detail.appendChild(el('div', 'rec-detail-section-title', 'Output (stdout)'));
    const pre = el('pre', 'rec-detail-pre', '');
    pre.textContent = stdout.length > 4000 ? stdout.slice(0, 4000) + '\n…(truncated)' : stdout;
    detail.appendChild(pre);
  }

  // stderr
  const stderr = (r.stderr || '').trim();
  if (stderr) {
    detail.appendChild(el('div', 'rec-detail-section-title rec-section-err', 'Errors (stderr)'));
    const pre = el('pre', 'rec-detail-pre rec-detail-err', '');
    pre.textContent = stderr.length > 2000 ? stderr.slice(0, 2000) + '\n…(truncated)' : stderr;
    detail.appendChild(pre);
  }

  if (!stdout && !stderr && vars.length === 0) {
    detail.appendChild(el('p', 'rec-hint', 'No output captured.'));
  }

  card.appendChild(header);
  card.appendChild(detail);

  // Expand / collapse inline — does NOT open any separate panel
  function toggle() {
    const expanded = card.dataset.expanded === 'true';
    card.dataset.expanded = expanded ? 'false' : 'true';
    header.setAttribute('aria-expanded', String(!expanded));
    chevron.textContent = expanded ? '▶' : '▼';
    detail.hidden = expanded;
    detail.setAttribute('aria-hidden', String(expanded));
  }
  header.addEventListener('click', toggle);
  header.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
  });

  exportBtn.addEventListener('click', () => {
    vscode.postMessage({ command: 'exportRecording', runId: card.dataset.runId, recording: r });
  });

  deleteBtn.addEventListener('click', () => {
    vscode.postMessage({ command: 'deleteRecording', runId: card.dataset.runId });
    // Remove immediately from DOM for instant feedback; server will confirm via recordingDeleted
    card.style.transition = 'opacity 0.2s';
    card.style.opacity = '0';
    setTimeout(() => { if (card.parentNode) { card.parentNode.removeChild(card); } }, 220);
  });

  return card;
}

// ── Main render ───────────────────────────────────────────────────────────────

let _allData = null;
let _filterFile = null;  // currently filtered file path (null = show all)

function render(data) {
  if (data) { _allData = data; }
  const { trackedFiles = [], vars = [], recordings = [] } = _allData || {};

  container.innerHTML = '';

  // ── SECTION 1: Files — Tracked ────────────────────────────────────────────
  const s1 = el('div', 'rec-section');
  const s1hdr = el('div', 'rec-section-header');
  s1hdr.innerHTML = '<strong>Files</strong><span class="header-normal"> — Tracked</span>';
  s1.appendChild(s1hdr);

  if (trackedFiles.length === 0) {
    s1.appendChild(el('p', 'rec-hint', 'No tracked files yet. Use "Select Files to Track" or press ▶ to run a Python or JS file.'));
  } else {
    trackedFiles.forEach(f => {
      const fpath = f.path || '';
      const name  = f.name || fpath.split(/[\\/]/).pop() || fpath;
      const isActive = _filterFile === fpath;

      const row = el('div', 'rec-row' + (isActive ? ' rec-row-active' : ''));
      row.style.cursor = 'pointer';
      row.title = 'Click to filter recordings for this file';
      const fileRecCount = recordings.filter(r => (r.filePath || r.file_path || '') === fpath).length;
      row.innerHTML = '<span class="teal-check">&#10003;</span>' +
        '<span class="rec-filename">' + name + '</span>' +
        '<span class="rec-filepath"> ' + fpath + '</span>' +
        (fileRecCount > 0 ? '<span class="rec-run-badge">' + fileRecCount + ' run' + (fileRecCount > 1 ? 's' : '') + '</span>' : '');

      row.addEventListener('click', () => {
        // Toggle filter: clicking same file again clears filter
        _filterFile = (isActive ? null : fpath);
        render(null);
      });
      s1.appendChild(row);
    });
    s1.appendChild(el('p', 'rec-hint', 'Click a file to filter its recordings below.'));
  }
  container.appendChild(s1);

  // ── SECTION 2: Variables — Evolution ─────────────────────────────────────
  // Aggregate actual variable evolution counts from real recording data on disk.
  // Don't rely on listTrackedVariables which returns config-only objects without evolutions.
  const varEvoMap = {};
  recordings.forEach(rec => {
    (rec.vars || rec.variables || []).forEach(v => {
      const name = v.name || String(v);
      if (!varEvoMap[name]) { varEvoMap[name] = { name, evolutions: 0, scope: v.scope || 'global' }; }
      varEvoMap[name].evolutions += (v.evolutions || 1);
    });
  });
  const aggVars = Object.values(varEvoMap);
  // Also include any bridge-provided vars that aren't already accounted for
  vars.forEach(v => {
    const name = typeof v === 'string' ? v : (v.name || String(v));
    if (!varEvoMap[name]) { aggVars.push({ name, evolutions: 0, scope: v.scope || 'global' }); }
  });

  const s2 = el('div', 'rec-section');
  const s2hdr = el('div', 'rec-section-header');
  s2hdr.innerHTML = '<strong>Variables</strong><span class="header-normal"> — Evolution</span>';
  s2.appendChild(s2hdr);

  if (aggVars.length === 0) {
    s2.appendChild(el('p', 'rec-hint', 'Open a Python or JS file and run it to see variable evolution data.'));
  } else {
    aggVars.forEach(v => {
      const row = el('div', 'rec-row');
      row.style.cursor = 'pointer';
      row.title = 'Click to open Variable Inspector for this variable';
      const scope = v.scope ? '<span class="rec-var-scope"> ' + v.scope + '</span>' : '';
      row.innerHTML = '<span class="rec-var-name">' + v.name + '</span>' + scope +
        '<span class="rec-count">evolutions: ' + v.evolutions + '</span>';
      row.addEventListener('click', () => vscode.postMessage({ command: 'openVariableInspector', varName: v.name }));
      s2.appendChild(row);
    });
    s2.appendChild(el('p', 'rec-hint', 'Updates when variables change across runs.'));
  }
  container.appendChild(s2);

  // ── SECTION 3: Runs — Recordings ─────────────────────────────────────────
  const s3 = el('div', 'rec-section');
  const s3hdr = el('div', 'rec-section-header');
  const filterLabel = _filterFile ? ' for <em>' + (_filterFile.split(/[\\/]/).pop() || _filterFile) + '</em>' : '';
  s3hdr.innerHTML = '<strong>Runs</strong><span class="header-normal"> — Recordings' + filterLabel + '</span>';
  if (_filterFile) {
    const clearBtn = el('button', 'rec-clear-filter-btn', '✕ Clear filter');
    clearBtn.addEventListener('click', () => { _filterFile = null; render(null); });
    s3hdr.appendChild(clearBtn);
  }
  s3.appendChild(s3hdr);

  // Filter recordings by selected file if active
  const visibleRecs = _filterFile
    ? recordings.filter(r => (r.filePath || r.file_path || '') === _filterFile)
    : recordings;

  if (visibleRecs.length === 0) {
    if (_filterFile) {
      s3.appendChild(el('p', 'rec-hint', 'No recordings for this file yet. Press ▶ to run it.'));
    } else {
      s3.appendChild(el('p', 'rec-hint', 'No runs recorded yet. Press ▶ to start.'));
    }
  } else {
    // Display newest first, numbered from most recent (Run #1 = most recent)
    visibleRecs.forEach((r, idx) => {
      const runNumber = visibleRecs.length - idx; // ascending run numbers oldest→newest
      s3.appendChild(buildRecordingCard(r, runNumber));
    });
  }
  container.appendChild(s3);
}

// ── Message handler ───────────────────────────────────────────────────────────

window.addEventListener('message', evt => {
  const msg = evt.data;

  if (msg.command === 'setData') {
    clearRunLog();
    // Only reset the file filter if the file context changed.
    // This preserves the filter across run.done → ready → setData refresh cycles.
    if (msg._resetFilter || (msg.filePath && msg.filePath !== (_allData && _allData.filePath))) {
      _filterFile = null;
    }
    render(msg);
    return;
  }

  if (msg.command === 'run.event') {
    if (msg.type === 'run.start') {
      clearRunLog();
      ensureRunLog();
      appendRunLog('▶ Starting: ' + msg.data + '\n');
    } else if (msg.type === 'run.stdout') {
      appendRunLog(msg.data);
    } else if (msg.type === 'run.stderr') {
      appendRunLog('[stderr] ' + msg.data);
    } else if (msg.type === 'run.done') {
      appendRunLog('\n✓ Run complete\n');
      vscode.postMessage({ command: 'ready' }); // refresh list
    } else if (msg.type === 'run.error') {
      appendRunLog('\n✗ Error: ' + msg.data + '\n');
    }
    return;
  }

  if (msg.command === 'recordingDeleted') {
    vscode.postMessage({ command: 'ready' });
    return;
  }
});

vscode.postMessage({ command: 'ready' });
render(null);
})();
