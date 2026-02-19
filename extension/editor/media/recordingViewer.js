(function(){
const vscode=acquireVsCodeApi();
let recordings=[];
let branches=[];
let activeDot=0;
let branchesOpen=false;
let renamingBranch=null;

const dotsTrack=document.getElementById('dots-track');
const btnBack=document.getElementById('btn-back');
const btnFwd=document.getElementById('btn-fwd');
const btnBranches=document.getElementById('btn-branches');
const btnInsights=document.getElementById('btn-insights');
const branchesDropdown=document.getElementById('branches-dropdown');
const renameContainer=document.getElementById('rename-container');
const renameBranchLabel=document.getElementById('rename-branch-label');
const renameInput=document.getElementById('rename-input');
const renameConfirm=document.getElementById('rename-confirm-btn');
const renameCancel=document.getElementById('rename-cancel-btn');
const changeCount=document.getElementById('change-count');

function renderDots(){
  dotsTrack.innerHTML='';
  const total = recordings.length;
  if (total === 0) {
    dotsTrack.innerHTML = '<span style="color:rgba(150,150,150,0.5);font-size:11px">No tracked changes yet</span>';
    changeCount.textContent = 'no ticks';
    return;
  }
  changeCount.textContent = (total === 0 ? 'no' : total) + ' tick' + (total !== 1 ? 's' : '');
  for(let i=0;i<total;i++){
    const d=document.createElement('div');
    d.className='dot cyan'+(i===activeDot?' active':'');
    d.title = recordings[i] ? 'Tick #'+(recordings[i].tick_id || (i+1)) : '—';
    d.addEventListener('click',()=>{
      activeDot=i;
      renderDots();
      if(recordings[i] && recordings[i].tick_id != null){
        vscode.postMessage({command:'jumpToTick', tickId:recordings[i].tick_id});
      }
    });
    dotsTrack.appendChild(d);
  }
}

function renderBranches(){
  branchesDropdown.innerHTML='';
  const list=branches;
  if (list.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:8px 12px;color:var(--vscode-descriptionForeground);font-size:11px;font-style:italic';
    empty.textContent = 'No branches yet.';
    branchesDropdown.appendChild(empty);
    return;
  }
  list.forEach(b=>{
    const item=document.createElement('div');item.className='branch-item';
    const nameEl=document.createElement('span');nameEl.className='branch-name';nameEl.textContent=b.name||b;
    const rBtn=document.createElement('button');rBtn.className='rename-btn';rBtn.textContent='rename';
    rBtn.addEventListener('click',e=>{
      e.stopPropagation();
      renamingBranch=b;
      renameBranchLabel.textContent=b.name||b;
      renameInput.value=b.name||b;
      renameContainer.classList.remove('hidden');
      branchesDropdown.classList.add('hidden');
      branchesOpen=false;
    });
    nameEl.addEventListener('click',e=>{
      e.stopPropagation();
      vscode.postMessage({command:'switchBranch',branchName:b.name||b});
      activeDot=Math.max(0,recordings.length-1);
      renderDots();
      branchesDropdown.classList.add('hidden');
      branchesOpen=false;
    });
    item.appendChild(nameEl);item.appendChild(rBtn);
    branchesDropdown.appendChild(item);
  });
}

btnBack.addEventListener('click',()=>{
  if(activeDot>0){activeDot--;renderDots();
    if(recordings[activeDot] && recordings[activeDot].tick_id != null) vscode.postMessage({command:'jumpToTick',tickId:recordings[activeDot].tick_id});}
});
btnFwd.addEventListener('click',()=>{
  const total=Math.max(recordings.length,1);
  if(activeDot<total-1){activeDot++;renderDots();
    if(recordings[activeDot] && recordings[activeDot].tick_id != null) vscode.postMessage({command:'jumpToTick',tickId:recordings[activeDot].tick_id});}
});
btnBranches.addEventListener('click',e=>{
  e.stopPropagation();
  branchesOpen=!branchesOpen;
  renameContainer.classList.add('hidden');
  if(branchesOpen){renderBranches();branchesDropdown.classList.remove('hidden');}
  else branchesDropdown.classList.add('hidden');
});
btnInsights.addEventListener('click',()=>vscode.postMessage({command:'openInsights'}));

const btnRefresh=document.getElementById('btn-refresh');
if(btnRefresh){
  btnRefresh.addEventListener('click',()=>vscode.postMessage({command:'refresh'}));
}
renameConfirm.addEventListener('click',()=>{
  if(renamingBranch&&renameInput.value.trim()){
    vscode.postMessage({command:'renameBranch',oldName:renamingBranch.name||renamingBranch,newName:renameInput.value.trim()});
    renamingBranch=null;renameContainer.classList.add('hidden');
  }
});
renameCancel.addEventListener('click',()=>{renamingBranch=null;renameContainer.classList.add('hidden');});
document.addEventListener('click',()=>{branchesDropdown.classList.add('hidden');branchesOpen=false;});

window.addEventListener('message',evt=>{
  const msg=evt.data;
  if(msg.command==='setData'){
    recordings=msg.recordings||[];
  
  // Update status bar if status data present
  if(msg.status && statusBar){
    const ready = msg.status.ready ? '✓' : '✗';
    const count = msg.status.recordings_count || 0;
    const tick = msg.status.tick_counter !== undefined ? msg.status.tick_counter : '?';
    statusBar.textContent = `Status: ${ready} Ready | Tick: ${tick} | Recordings: ${count}`;
    statusBar.style.display = 'block';
  }else if(statusBar){
    statusBar.style.display = 'none';
  }
    branches=msg.branches||[];
    activeDot=Math.max(0,recordings.length-1);
    renderDots();
  }
});

// Pause button: placeholder — auto-playback is not yet implemented
const btnPause = document.getElementById('btn-pause');
if (btnPause) {
  btnPause.title = 'Auto-playback (coming soon)';
  btnPause.style.opacity = '0.4';
  btnPause.style.cursor = 'not-allowed';
}

vscode.postMessage({command:'ready'});
renderDots();
})();
