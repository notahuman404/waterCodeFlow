(function(){
const vscode=acquireVsCodeApi();
let files=[];
let filterText='';

const listEl=document.getElementById('file-list');
const filterEl=document.getElementById('file-filter');

filterEl.addEventListener('input',function(){filterText=this.value.toLowerCase();render();});

function render(){
  listEl.innerHTML='';
  const visible=files.filter(f=>{
    if(!filterText)return true;
    return(f.name+' '+f.path).toLowerCase().includes(filterText);
  });
  if(visible.length===0){
    const e=document.createElement('div');
    e.style.cssText='padding:12px;color:var(--vscode-descriptionForeground);font-size:12px;font-style:italic';
    e.textContent=filterText?'No files match.':'No files found in workspace.';
    listEl.appendChild(e);return;
  }
  visible.forEach(f=>{
    const row=document.createElement('div');
    row.className='file-row'+(f.selected?' selected':'');
    const cb=document.createElement('div');
    cb.className='file-checkbox';
    cb.innerHTML=f.selected?'&#10003;':'';
    const nm=document.createElement('span');nm.className='file-name';nm.textContent=f.name;
    const pt=document.createElement('span');pt.className='file-path';pt.textContent=f.path||'';
    const bg=document.createElement('span');bg.className='branch-badge';bg.textContent=f.branch||'main';
    row.appendChild(cb);row.appendChild(nm);row.appendChild(pt);row.appendChild(bg);
    row.addEventListener('click',()=>{
      f.selected=!f.selected;
      vscode.postMessage({command:'toggleFile',filePath:f.path});
      render();
    });
    listEl.appendChild(row);
  });
}

window.addEventListener('message',evt=>{
  const msg=evt.data;
  if(msg.command==='setFiles'){files=msg.files||[];render();}
  else if(msg.command==='updateSelected'){
    const sel=new Set(msg.selected||[]);
    files.forEach(f=>f.selected=sel.has(f.path));
    render();
  }
});

vscode.postMessage({command:'ready'});
})();
