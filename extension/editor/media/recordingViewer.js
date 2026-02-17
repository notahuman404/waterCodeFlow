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
  const total=Math.max(recordings.length,1);
  changeCount.textContent=(total-1)+' changes';
  for(let i=0;i<total;i++){
    const d=document.createElement('div');
    d.className='dot'+(i===activeDot?' active':'');
    d.title=recordings[i]?'Tick '+recordings[i].tick_id:'—';
    d.addEventListener('click',()=>{
      activeDot=i;
      renderDots();
      if(recordings[i]){
        vscode.postMessage({command:'jumpToTick',tickId:recordings[i].tick_id});
      }
    });
    dotsTrack.appendChild(d);
  }
}

function renderBranches(){
  branchesDropdown.innerHTML='';
  const list=branches.length>0?branches:[{name:'main'},{name:'feature-a'},{name:'dev'}];
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
    if(recordings[activeDot]) vscode.postMessage({command:'jumpToTick',tickId:recordings[activeDot].tick_id});}
});
btnFwd.addEventListener('click',()=>{
  const total=Math.max(recordings.length,1);
  if(activeDot<total-1){activeDot++;renderDots();
    if(recordings[activeDot]) vscode.postMessage({command:'jumpToTick',tickId:recordings[activeDot].tick_id});}
});
btnBranches.addEventListener('click',e=>{
  e.stopPropagation();
  branchesOpen=!branchesOpen;
  renameContainer.classList.add('hidden');
  if(branchesOpen){renderBranches();branchesDropdown.classList.remove('hidden');}
  else branchesDropdown.classList.add('hidden');
});
btnInsights.addEventListener('click',()=>vscode.postMessage({command:'openInsights'}));
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
    branches=msg.branches||[];
    activeDot=Math.max(0,recordings.length-1);
    renderDots();
  }
});

vscode.postMessage({command:'ready'});
renderDots();
})();
