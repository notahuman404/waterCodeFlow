(function(){
const vscode=acquireVsCodeApi();
const container=document.getElementById('recordings-container');

function el(tag,cls,html){const e=document.createElement(tag);if(cls)e.className=cls;if(html)e.innerHTML=html;return e;}

function render(data){
  container.innerHTML='';
  const {trackedFiles=[],vars=[],runs=[]}=data||{};

  // SECTION 1: Files — Tracked
  const s1=el('div','rec-section');
  const h1=el('div','rec-section-header');h1.innerHTML='<strong>Files</strong><span class="header-normal"> — Tracked</span>';
  s1.appendChild(h1);
  if(trackedFiles.length===0){s1.appendChild(el('p','rec-hint','No tracked files yet. Use Run to start recording.'));}
  trackedFiles.forEach(f=>{
    const row=el('div','rec-row');row.style.cursor='pointer';
    row.appendChild(el('span','teal-check','&#10003;'));
    row.appendChild(el('span','rec-filename',f.name||(f.path||'').split('/').pop()));
    row.appendChild(el('span','rec-filepath',' ('+f.path+')'));
    row.addEventListener('click',()=>vscode.postMessage({command:'openRunInspector'}));
    s1.appendChild(row);
  });
  s1.appendChild(el('p','rec-hint','Persisted in Vovle (.codevovle)'));
  container.appendChild(s1);

  // SECTION 2: Variables — Evolution
  const s2=el('div','rec-section');
  const h2=el('div','rec-section-header');h2.innerHTML='<strong>Variables</strong><span class="header-normal"> — Evolution</span>';
  s2.appendChild(h2);
  vars.forEach(v=>{
    const row=el('div','rec-row');row.style.cursor='pointer';
    row.appendChild(el('span','rec-var-name',typeof v==='string'?v:(v.name||v)));
    const count=v.evolutions||v.match_count||0;
    row.appendChild(el('span','rec-count','evolutions: '+count));
    row.addEventListener('click',()=>vscode.postMessage({command:'openVariableInspector'}));
    s2.appendChild(row);
  });
  if(vars.length===0) s2.appendChild(el('p','rec-hint','No variable evolutions recorded.'));
  s2.appendChild(el('p','rec-hint','Updates when variables change across runs'));
  container.appendChild(s2);

  // SECTION 3: Runs — Variable Changes
  const s3=el('div','rec-section');
  const h3=el('div','rec-section-header');h3.innerHTML='<strong>Runs</strong><span class="header-normal"> — Variable Changes</span>';
  s3.appendChild(h3);
  runs.forEach(r=>{
    const row=el('div','rec-row clickable');
    const id=r.run_id!==undefined?r.run_id:r.run;
    const changes=r.tick_count||r.varChanges||r.changes||0;
    row.appendChild(el('span','rec-run-label','Run #'+id));
    row.appendChild(el('span','rec-run-count',changes+' var changed'));
    row.addEventListener('click',()=>vscode.postMessage({command:'openRunInspector',runId:id}));
    s3.appendChild(row);
  });
  if(runs.length===0) s3.appendChild(el('p','rec-hint','No runs recorded yet.'));
  container.appendChild(s3);
}

window.addEventListener('message',evt=>{
  const msg=evt.data;
  if(msg.command==='setData') render(msg);
});

vscode.postMessage({command:'ready'});
// Show loading state until data arrives
render(null);
})();
