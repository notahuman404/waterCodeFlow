(function(){
const vscode = acquireVsCodeApi();

// Mock sections used as fallback when no real data
const MOCK_SECTIONS = [
  { title:'Session Scopes', vars:[{name:'user_id',file:'src/arc/session.py',scope:'local'}] },
  { title:'Global Scopes', vars:[{name:'scan_data',file:'src/orc/main.py',scope:'global'},{name:'processor_type',file:'src/hardware/cpu.py',scope:'global'}] },
  { title:'Local Scopes', vars:[{name:'message_content',file:'src/utils/strings.py',scope:'local'},{name:'config_settings',file:'src/config/app.py',scope:'both'},{name:'count_val',file:'src/hardware/cp.py',scope:'global'}] }
];

let sections = JSON.parse(JSON.stringify(MOCK_SECTIONS));
let collapsed = {};
let trackState = {}; // name -> {tracked,mode,runs}
let openDropdown = null;
let filterText = '';

const container = document.getElementById('sections-container');
const filterInput = document.getElementById('filter-input');
const refreshBtn = document.getElementById('refresh-btn');

filterInput.addEventListener('input', function(){ filterText = this.value.toLowerCase(); render(); });
refreshBtn.addEventListener('click', ()=>{ vscode.postMessage({command:'refresh'}); });
document.addEventListener('click',()=>{ if(openDropdown){openDropdown=null;render();} });

function getState(name){ return trackState[name] || {tracked:false,mode:'multi',runs:5}; }

function render(){
  container.innerHTML='';
  let hasVisible=false;
  sections.forEach(sec=>{
    const secEl=document.createElement('div');
    secEl.className='section';
    // Header
    const hdr=document.createElement('div');
    hdr.className='section-header';
    const chv=document.createElement('span');
    chv.className='chevron'+(collapsed[sec.title]?'':' open');
    chv.textContent='›';
    hdr.appendChild(chv);
    hdr.appendChild(document.createTextNode(sec.title));
    hdr.addEventListener('click',()=>{ collapsed[sec.title]=!collapsed[sec.title]; render(); });
    secEl.appendChild(hdr);

    const body=document.createElement('div');
    body.className='section-body'+(collapsed[sec.title]?' collapsed':'');
    let secVisible=false;

    sec.vars.forEach(v=>{
      const q=(v.name+' '+v.file).toLowerCase();
      if(filterText && !q.includes(filterText)) return;
      secVisible=true; hasVisible=true;
      const st=getState(v.name);
      const row=document.createElement('div');
      row.className='var-row';

      const nm=document.createElement('span');
      nm.className='var-name'; nm.textContent=v.name;
      const mt=document.createElement('span');
      mt.className='var-meta'; mt.textContent=v.file+' — '+v.scope;

      const acts=document.createElement('div'); acts.className='var-actions';
      const eye=document.createElement('button');
      eye.className='eye-btn'+(openDropdown===v.name?' active':'');
      eye.innerHTML='&#128065;'; eye.title='Track options';
      eye.addEventListener('click',e=>{ e.stopPropagation();
        openDropdown=(openDropdown===v.name?null:v.name); render(); });

      const cb=document.createElement('div');
      cb.className='check-box'+(st.tracked?' checked':'');
      cb.innerHTML=st.tracked?'&#10003;':'';
      cb.title=st.tracked?'Tracked — click to untrack':'Click to track';
      cb.addEventListener('click',e=>{ e.stopPropagation();
        vscode.postMessage({command:'toggleTrack',name:v.name}); });

      acts.appendChild(eye); acts.appendChild(cb);
      row.appendChild(nm); row.appendChild(mt); row.appendChild(acts);
      body.appendChild(row);

      // Tracking dropdown
      if(openDropdown===v.name){
        const dd=document.createElement('div'); dd.className='tracking-dropdown';
        dd.addEventListener('click',e=>e.stopPropagation());

        const mkRow=(label,mode)=>{
          const r=document.createElement('div'); r.className='radio-row';
          const dot=document.createElement('div'); dot.className='radio-dot'+(st.mode===mode?' active':'');
          const lbl=document.createElement('span'); lbl.className='radio-label'; lbl.textContent=label;
          r.appendChild(dot); r.appendChild(lbl);
          if(mode==='multi'){
            const inp=document.createElement('input'); inp.className='runs-input';
            inp.type='number'; inp.min='1'; inp.value=String(st.runs||5);
            inp.addEventListener('input',()=>{ const runs=parseInt(inp.value)||1;
              trackState[v.name]={...getState(v.name),runs};
              vscode.postMessage({command:'setTrackMode',name:v.name,mode:'multi',runs}); });
            inp.addEventListener('click',e=>e.stopPropagation());
            r.appendChild(inp);
          }
          r.addEventListener('click',()=>{ trackState[v.name]={...getState(v.name),mode};
            vscode.postMessage({command:'setTrackMode',name:v.name,mode}); render(); });
          return r;
        };
        dd.appendChild(mkRow('Track for single run','single'));
        dd.appendChild(mkRow('Track for multiple runs','multi'));
        body.appendChild(dd);
      }
    });

    if(!secVisible && filterText) return;
    secEl.appendChild(body);
    container.appendChild(secEl);
  });
  if(!hasVisible && filterText){
    const e=document.createElement('div'); e.className='empty-state';
    e.textContent='No variables match "'+filterText+'"';
    container.appendChild(e);
  }
}

// Extension messages
window.addEventListener('message',evt=>{
  const msg=evt.data;
  if(msg.command==='setVars'){
    if(msg.vars && msg.vars.length>0){
      // Group real vars into sections
      const byScope={};
      msg.vars.forEach(v=>{
        const sc=v.scope||'global';
        if(!byScope[sc]) byScope[sc]=[];
        byScope[sc].push({name:v.name,file:msg.filePath||v.file||'',scope:sc});
      });
      sections=Object.entries(byScope).map(([s,vars])=>({
        title:s.charAt(0).toUpperCase()+s.slice(1)+' Scope',vars
      }));
    } else {
      sections=JSON.parse(JSON.stringify(MOCK_SECTIONS));
    }
    if(msg.trackState) trackState=msg.trackState;
    render();
  } else if(msg.command==='trackState'){
    if(!trackState[msg.name]) trackState[msg.name]={tracked:false,mode:'multi',runs:5};
    trackState[msg.name].tracked=msg.state.tracked;
    trackState[msg.name].mode=msg.state.mode;
    trackState[msg.name].runs=msg.state.runs;
    render();
  }
});

// Announce ready
vscode.postMessage({command:'ready'});
render();
})();
