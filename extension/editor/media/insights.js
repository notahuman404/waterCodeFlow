(function(){
'use strict';
const vscode = acquireVsCodeApi();
const canvas  = document.getElementById('insight-canvas');
const ctx     = canvas.getContext('2d');
const getInsightsBtn = document.getElementById('get-insights-btn');
const insightsResult = document.getElementById('insights-result');

let nodeStates    = {};   // nodeId -> 'first' | 'second'
let selectionOrder = [];  // [firstId, secondId]
let nodes         = [];   // built by buildNodes()
let diskRecordings = [];  // from built/recordings/*.json (real runs)
let branches      = [];   // from glue getBranches

// ── Color palette (spec: cyan=main, yellow=selected, gray=branch) ────────────
const COLOR_MAIN_DEFAULT   = '#4ec9b0'; // cyan — main branch nodes
const COLOR_BRANCH_DEFAULT = '#555555'; // gray — branch nodes
const COLOR_SELECTED       = '#f5c518'; // yellow — ANY selected node
const COLOR_SELECTED_FROM  = '#ff4444'; // red — first selected node (original design)
const COLOR_LINE_MAIN      = 'rgba(255,255,255,0.55)';
const COLOR_LINE_BRANCH    = 'rgba(120,120,120,0.5)';

// ── Build the node graph from real data ──────────────────────────────────────
function buildNodes() {
  const W = canvas.width, H = canvas.height;
  if (W < 10 || H < 10) return [];
  const midY = H * 0.48;
  const result = [];

  const recCount = diskRecordings.length;
  if (recCount === 0) {
    // Draw a single placeholder node so the canvas isn't blank
    result.push({ id: 'placeholder', x: W * 0.5, y: midY, rx: 18, ry: 11,
      type: 'main', branchName: 'main', recIndex: -1, runId: null,
      label: '?', timestamp: null });
    return result;
  }

  // ── Main-line nodes (one per real run, left→right = oldest→newest) ─────────
  const mainRecs = diskRecordings.slice(); // already sorted newest-first from panel, reverse for display
  mainRecs.reverse(); // oldest first
  const mainCount = Math.min(mainRecs.length, 12);
  const xPad = 0.07;
  const mainXs = mainCount === 1
    ? [W * 0.5]
    : Array.from({ length: mainCount }, (_, i) => (xPad + i * ((1 - 2 * xPad) / (mainCount - 1))) * W);

  mainXs.forEach((x, i) => {
    const rec = mainRecs[i];
    const runLabel = '#' + (i + 1);
    result.push({
      id:         'main-' + i,
      x, y:       midY,
      rx: 20, ry: 12,
      type:       'main',
      branchName: 'main',
      recIndex:   i,
      runId:      rec.runId || rec.run_id || null,
      label:      runLabel,
      timestamp:  rec.timestamp,
      exitCode:   rec.exitCode,
    });
  });

  // ── Branch nodes (one cluster per branch from the bridge) ─────────────────
  if (branches.length > 0) {
    const mainNodes = result.filter(n => n.type === 'main');
    branches.forEach((branch, bi) => {
      // Attach each branch off an evenly-spaced main node
      const srcIdx = Math.min(bi + 1, mainNodes.length - 1);
      const src = mainNodes[srcIdx];
      if (!src) return;

      // Branch node sits to the upper-right of its source
      const bx = src.x + 50;
      const by = midY - 60 - bi * 30;
      result.push({
        id:         'branch-' + bi + '-0',
        x:          bx,
        y:          by,
        rx:         13, ry: 8,
        type:       'branch',
        branchName: branch.name || ('branch-' + bi),
        recIndex:   -1,
        runId:      null,
        label:      (branch.name || '').slice(0, 8),
        srcX:       src.x,
        srcY:       src.y,
        timestamp:  null,
      });
    });
  }

  return result;
}

// ── Canvas draw ──────────────────────────────────────────────────────────────
function draw() {
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#1e1e1e';
  ctx.fillRect(0, 0, W, H);

  if (W < 10 || H < 10) return;

  nodes = buildNodes();
  const mainNodes   = nodes.filter(n => n.type === 'main');
  const branchNodes = nodes.filter(n => n.type === 'branch');
  const midY = H * 0.48;

  // Draw main timeline spine
  if (mainNodes.length > 1) {
    ctx.strokeStyle = COLOR_LINE_MAIN;
    ctx.lineWidth   = 2;
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(mainNodes[0].x, midY);
    for (let i = 1; i < mainNodes.length; i++) {
      ctx.lineTo(mainNodes[i].x, midY);
    }
    ctx.stroke();
  }

  // Draw branch connectors (L-shaped lines to branch node)
  branchNodes.forEach(n => {
    ctx.strokeStyle = COLOR_LINE_BRANCH;
    ctx.lineWidth   = 1;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(n.srcX, n.srcY);
    ctx.lineTo(n.srcX, n.y);
    ctx.lineTo(n.x - n.rx - 2, n.y);
    ctx.stroke();
    ctx.setLineDash([]);
  });

  // Draw nodes
  nodes.forEach(n => {
    const state = nodeStates[n.id];
    let fill = n.type === 'main' ? COLOR_MAIN_DEFAULT : COLOR_BRANCH_DEFAULT;
    if (state === 'first')  { fill = COLOR_SELECTED_FROM; }
    if (state === 'second') { fill = COLOR_SELECTED; }

    // Drop shadow for selected nodes
    if (state) {
      ctx.shadowColor = fill;
      ctx.shadowBlur  = 8;
    }

    ctx.beginPath();
    ctx.ellipse(n.x, n.y, n.rx, n.ry, 0, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();

    if (state) {
      ctx.strokeStyle = '#fff';
      ctx.lineWidth   = 2;
      ctx.stroke();
      ctx.shadowBlur  = 0;
    }
    ctx.shadowBlur = 0;

    // Label (run number or branch name) — below main nodes, inside branch nodes
    ctx.fillStyle = n.type === 'main' ? '#1e1e1e' : '#ccc';
    ctx.font = n.type === 'main'
      ? 'bold 10px "Segoe UI", sans-serif'
      : '9px "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(n.label || '', n.x, n.y);

    // Run timestamp hint below main nodes
    if (n.type === 'main' && n.timestamp) {
      const ts = new Date(n.timestamp).toLocaleTimeString(undefined,
        { hour: '2-digit', minute: '2-digit' });
      ctx.fillStyle = 'rgba(180,180,180,0.6)';
      ctx.font = '9px "Segoe UI", sans-serif';
      ctx.fillText(ts, n.x, n.y + n.ry + 12);
    }

    // Branch name label above branch nodes
    if (n.type === 'branch' && n.branchName) {
      ctx.fillStyle = 'rgba(180,180,180,0.7)';
      ctx.font = '9px "Segoe UI", sans-serif';
      ctx.fillText(n.branchName, n.x, n.y - n.ry - 7);
    }
  });

  ctx.textAlign = 'left';
  ctx.textBaseline = 'alphabetic';

  // Empty state label
  if (diskRecordings.length === 0) {
    ctx.fillStyle = 'rgba(150,150,150,0.6)';
    ctx.font = '13px "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No runs yet — press ▶ to record', W * 0.5, H * 0.5 + 40);
    ctx.textAlign = 'left';
  }

  // Legend
  drawLegend(W, H);
}

function drawLegend(W, H) {
  const items = [
    { color: COLOR_MAIN_DEFAULT, label: 'Run (main)' },
    { color: COLOR_BRANCH_DEFAULT, label: 'Branch node' },
    { color: COLOR_SELECTED_FROM, label: 'From (first click)' },
    { color: COLOR_SELECTED, label: 'To (second click)' },
  ];
  const legendX = 12, legendY = H - 14 - items.length * 18;
  ctx.font = '10px "Segoe UI", sans-serif';
  items.forEach((item, i) => {
    const y = legendY + i * 18;
    ctx.beginPath();
    ctx.ellipse(legendX + 6, y, 6, 4, 0, 0, Math.PI * 2);
    ctx.fillStyle = item.color;
    ctx.fill();
    ctx.fillStyle = 'rgba(180,180,180,0.7)';
    ctx.fillText(item.label, legendX + 16, y + 4);
  });
}

// ── Hit detection (ellipse math) ─────────────────────────────────────────────
function getNodeAt(mx, my) {
  // Check in reverse order (top nodes first)
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i];
    // Ellipse equation: (dx/rx)² + (dy/ry)² <= 1
    const dx = mx - n.x, dy = my - n.y;
    if ((dx * dx) / (n.rx * n.rx) + (dy * dy) / (n.ry * n.ry) <= 1.3) {
      return n;
    }
  }
  return null;
}

// ── Canvas events ─────────────────────────────────────────────────────────────
canvas.addEventListener('mousemove', e => {
  const r = canvas.getBoundingClientRect();
  const n = getNodeAt(e.clientX - r.left, e.clientY - r.top);
  canvas.style.cursor = n ? 'pointer' : 'default';
  if (n) {
    // Show tooltip
    canvas.title = n.type === 'main'
      ? 'Run ' + (n.label || '') + (n.timestamp ? '\n' + new Date(n.timestamp).toLocaleString() : '')
      + (n.exitCode != null ? '\nExit: ' + n.exitCode : '')
      : 'Branch: ' + (n.branchName || n.label || '');
  } else {
    canvas.title = '';
  }
});

canvas.addEventListener('click', e => {
  const r  = canvas.getBoundingClientRect();
  const n  = getNodeAt(e.clientX - r.left, e.clientY - r.top);
  if (!n) { return; }

  const cur    = nodeStates[n.id];
  const active = selectionOrder.filter(id => nodeStates[id]);

  if (cur) {
    // Deselect
    delete nodeStates[n.id];
    selectionOrder = selectionOrder.filter(id => id !== n.id);
    // Re-label remaining
    if (selectionOrder.length === 1) { nodeStates[selectionOrder[0]] = 'first'; }
  } else if (active.length === 0) {
    nodeStates[n.id] = 'first';
    selectionOrder.push(n.id);
  } else if (active.length === 1) {
    nodeStates[n.id] = 'second';
    selectionOrder.push(n.id);
  } else {
    // Already 2 selected — replace the oldest one
    delete nodeStates[selectionOrder[0]];
    selectionOrder.shift();
    nodeStates[n.id] = 'second';
    selectionOrder.push(n.id);
  }
  draw();
  updateSelectionHint();
});

function updateSelectionHint() {
  const active = selectionOrder.filter(id => nodeStates[id]);
  if (active.length === 0) {
    showResult('Click two run nodes to compare them for insights.', 'info');
  } else if (active.length === 1) {
    const n = nodes.find(x => x.id === active[0]);
    showResult('Selected: Run ' + (n?.label || '?') + ' — now click a second node.', 'info');
  } else {
    const n1 = nodes.find(x => x.id === active[0]);
    const n2 = nodes.find(x => x.id === active[1]);
    showResult(
      'Compare Run ' + (n1?.label || '?') + ' → Run ' + (n2?.label || '?') +
      '\nClick "Get Insights" to analyze.', 'ready'
    );
  }
}

function showResult(text, type) {
  insightsResult.textContent = text;
  insightsResult.style.cssText = [
    'position:absolute;left:50%;transform:translateX(-50%);',
    'padding:10px 18px;border-radius:4px;font-size:12px;',
    'max-width:70%;text-align:center;white-space:pre-wrap;',
    type === 'error'  ? 'background:#2a1e1e;border:1px solid #f48771;color:#f48771;top:60%' :
    type === 'ready'  ? 'background:#1e2a1e;border:1px solid #4ec9b0;color:#ccc;top:60%' :
    type === 'loading'? 'background:#252525;border:1px solid #555;color:#9cdcfe;top:60%' :
                        'background:#252525;border:1px solid #555;color:#888;top:60%'
  ].join('');
  insightsResult.classList.remove('hidden');
}

// ── Get insights button ───────────────────────────────────────────────────────
getInsightsBtn.addEventListener('click', () => {
  const active = selectionOrder.filter(id => nodeStates[id]);
  if (active.length < 2) {
    showResult('Select two run nodes (click on them) to get insights.', 'info');
    return;
  }
  const n1 = nodes.find(n => n.id === active[0]);
  const n2 = nodes.find(n => n.id === active[1]);

  // Use runId if available, otherwise use recIndex as tick substitute
  const fromId = n1?.runId || n1?.recIndex;
  const toId   = n2?.runId || n2?.recIndex;

  showResult('Generating insights…', 'loading');
  vscode.postMessage({ command: 'getInsights', fromTick: fromId, toTick: toId,
    fromRunId: n1?.runId, toRunId: n2?.runId });
});

// ── Responsive resize using ResizeObserver ────────────────────────────────────
function resize() {
  const wrap = canvas.parentElement;
  if (!wrap) return;
  canvas.width  = wrap.clientWidth;
  canvas.height = wrap.clientHeight;
  draw();
}

const ro = new ResizeObserver(() => resize());
ro.observe(canvas.parentElement || document.body);

// ── Messages from extension ───────────────────────────────────────────────────
window.addEventListener('message', evt => {
  const msg = evt.data;
  if (msg.command === 'setBranchData') {
    diskRecordings = msg.recordings || [];
    branches       = msg.branches   || [];
    nodeStates     = {};
    selectionOrder = [];
    resize();
    updateSelectionHint();
  } else if (msg.command === 'insightsResult') {
    const text = typeof msg.result === 'object'
      ? JSON.stringify(msg.result, null, 2)
      : String(msg.result);
    showResult(text, 'ready');
  } else if (msg.command === 'insightsError') {
    showResult('Error: ' + msg.error, 'error');
  }
});

window.addEventListener('resize', resize);
vscode.postMessage({ command: 'ready' });
setTimeout(resize, 80);
})();
