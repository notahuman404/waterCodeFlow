(function(){
const vscode=acquireVsCodeApi();
let recordings=[];
let runs=[];
let filePath='';
let activeDot=0;
let selectedCard=null;

const CARDS_DEMO=[
  {id:'user_data',label:'user_data',data:{"id":1045,"username":"jdoe","email":"jdoe@example.com","metadata":{"last_login":"2023-10-27T09:41:00Z","role":"admin","permissions":["read","write","execute"]}},version:4,total:8},
  {id:'userMeta',label:'userMeta',data:{"role":"admin","permissions":["read","write","execute"],"session_token":"A1B2C3D4E5F6"},version:2,total:3}
];
const META_BLOCKS_DEMO=[
  {title:'user_data',rows:[
    {label:'Variable name:',value:'user_data'},{label:'Scope:',value:'local'},
    {label:'Type:',value:'dict'},{label:'SQL',value:''},
    {label:'First seen:',value:'2023-10-27T14:00:00Z'},{label:'Last seen:',value:'2023-10-27T14:35:00Z'},
    {label:'File Path:',value:'/src/client_handler.py'},{label:'Line no.:',value:'46'},
    {label:'Code Line:',value:'user_data.update(userMeta)'},{label:'Total versions:',value:'4G'}
  ]},
  {title:'counter',rows:[
    {label:'Variable name:',value:'counter'},{label:'Scope:',value:'local'},
    {label:'Type:',value:'int'},{label:'sql',value:'False',special:'false'},
    {label:'Threads id:',value:'2001'},{label:'First seen:',value:'2023-10-26T18:45:00Z'},
    {label:'Last seen:',value:'2023-10-26T20:28:00Z'},{label:'File Path:',value:'/src/server.py'},
    {label:'Line no.:',value:'87'},{label:'Code Line:',value:'counter += 1'},{label:'Total versions:',value:'16'}
  ]}
];

function highlightJson(json){
  return json
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,match=>{
      let cls='json-number';
      if(/^"/.test(match))cls=/:$/.test(match)?'json-key':'json-string';
      else if(/true|false/.test(match))cls='json-bool';
      else if(/null/.test(match))cls='json-null';
      return`<span class="${cls}">${match}</span>`;
    });
}

function renderCards(cards){
  const left=document.getElementById('ri-left');left.innerHTML='';
  const cardEls={};
  cards.forEach(card=>{
    const cardEl=document.createElement('div');cardEl.className='var-card';cardEl.id='card-'+card.id;
    const hdr=document.createElement('div');hdr.className='var-card-header';hdr.textContent=card.label;
    const body=document.createElement('div');body.className='var-card-body';
    body.innerHTML=highlightJson(JSON.stringify(card.data,null,2));
    const footer=document.createElement('div');footer.className='var-card-footer';
    footer.textContent='Version '+(card.version||1)+' of '+(card.total||1);
    const bar=document.createElement('div');bar.className='var-progress-bar';
    const fill=document.createElement('div');fill.className='var-progress-fill';
    fill.style.width=((card.version||1)/(card.total||1)*100)+'%';
    bar.appendChild(fill);
    cardEl.appendChild(hdr);cardEl.appendChild(body);cardEl.appendChild(footer);cardEl.appendChild(bar);
    cardEl.addEventListener('click',()=>{
      selectedCard=selectedCard===card.id?null:card.id;
      Object.keys(cardEls).forEach(id=>cardEls[id].classList.toggle('selected',id===selectedCard));
      if(selectedCard){const b=document.getElementById('meta-block-'+card.id);if(b)b.scrollIntoView({behavior:'smooth',block:'start'});}
    });
    left.appendChild(cardEl);cardEls[card.id]=cardEl;
  });
}

function renderMetaBlocks(blocks){
  const el=document.getElementById('ri-meta-blocks');el.innerHTML='';
  blocks.forEach(block=>{
    const blockEl=document.createElement('div');blockEl.className='ri-meta-block';blockEl.id='meta-block-'+block.title;
    const title=document.createElement('div');title.className='ri-meta-block-title';title.textContent=block.title;
    blockEl.appendChild(title);
    block.rows.forEach(r=>{
      const row=document.createElement('div');row.className='ri-meta-row';
      const lbl=document.createElement('div');lbl.className='ri-meta-label';lbl.textContent=r.label;
      const val=document.createElement('div');val.className='ri-meta-value'+(r.special==='false'?' false-val':'');val.textContent=r.value;
      row.appendChild(lbl);row.appendChild(val);blockEl.appendChild(row);
    });
    el.appendChild(blockEl);
  });
}

function renderDots(){
  const total=Math.max(recordings.length,20);
  const el=document.getElementById('ri-dots');el.innerHTML='';
  const badge=document.getElementById('ri-step-badge');
  for(let i=0;i<total;i++){
    const d=document.createElement('div');d.className='ri-dot'+(i===activeDot?' active':'');
    d.title=recordings[i]?'Tick '+recordings[i].tick_id:String(i);
    d.addEventListener('click',()=>{
      activeDot=i;renderDots();
      if(recordings[i]) vscode.postMessage({command:'jumpToTick',tickId:recordings[i].tick_id});
      badge.textContent='Step '+(activeDot+1)+': Line 87';
    });
    el.appendChild(d);
  }
  if(recordings[activeDot]) badge.textContent='Tick '+recordings[activeDot].tick_id+': Line 87';
}

function renderRun(runData){
  const titleEl=document.getElementById('ri-run-title');
  const statusEl=document.getElementById('ri-status');
  const lineEl=document.getElementById('ri-lineno');
  const codeEl=document.getElementById('ri-codeline');
  const fpEl=document.getElementById('ri-filepath');
  if(runData){
    titleEl.textContent='Run #'+(runData.run_id!==undefined?runData.run_id:'?')+' — Variable Recordings';
    statusEl.textContent='Status: Completed | '+(runData.tick_count||0)+' ticks';
  }
  lineEl.innerHTML='Line no.: <strong>87</strong>';
  codeEl.textContent='user_data.update(userMeta)';
  fpEl.textContent=filePath||'/src/client_handler.py';
}

// Initial render with demo data
renderCards(CARDS_DEMO);
renderMetaBlocks(META_BLOCKS_DEMO);
renderDots();
renderRun(null);

document.getElementById('ri-back').addEventListener('click',()=>{window.history.back();});

window.addEventListener('message',evt=>{
  const msg=evt.data;
  if(msg.command==='setData'){
    filePath=msg.filePath||'';
    recordings=msg.recordings||[];
    runs=msg.runs||[];
    activeDot=Math.max(0,recordings.length-1);
    renderRun(runs[0]||null);
    renderDots();
    // Update file path in context bar
    document.getElementById('ri-filepath').textContent=filePath||'/src/client_handler.py';
  }
});

vscode.postMessage({command:'ready'});
})();
