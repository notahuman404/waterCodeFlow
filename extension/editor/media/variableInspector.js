(function(){
const vscode=acquireVsCodeApi();
let recordings=[];
let filePath='';
let activeDot=0;

const JSON_DEMO={
  "user_id":"u_1234567898abcdef","username":"jdoe_dev","active":true,
  "profile":{"first_name":"John","last_name":"Doe","email":"john.doe@example.com",
    "settings":{"theme":"dark","notifications":{"email":true,"push":false,"sms":true}}},
  "access_level":3,"last_login":"2023-10-27T15:30:00Z",
  "recent_activities":[
    {"type":"commit","repo":"backend-service","hash":"a1b2c3d4","timestamp":"2023-10-27T14:15:00Z"},
    {"type":"deploy","environment":"staging","status":"success","timestamp":"2023-10-26T18:45:00Z"}
  ],
  "metrics":{"daily_requests":1600,"average_response_time":"115ms","error_rate":0.005},
  "flags":{"experimental_feature_x":false,"beta_access":true}
};

const META_DEMO=[
  {label:'Variable name',value:'user_data'},{label:'Scope',value:'local'},
  {label:'Type',value:'dict'},{label:'SQL',value:'True'},{label:'Threads id',value:'None'},
  {label:'First seen',value:'2023-10-27T14:00:00Z'},{label:'Last seen',value:'2023-10-27T14:35:00Z'},
  {label:'File Path',value:'/src/client_handler.py'},{label:'Line no.',value:'46'},
  {label:'Code Line',value:'c_data.update(userMeta)'},{label:'Total versions',value:'18'}
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

function renderMeta(meta){
  const el=document.getElementById('vi-meta-list');el.innerHTML='';
  meta.forEach(m=>{
    const row=document.createElement('div');row.className='vi-meta-row';
    const lbl=document.createElement('div');lbl.className='vi-meta-label';lbl.textContent=m.label;
    const val=document.createElement('div');val.className='vi-meta-value';val.textContent=m.value;
    row.appendChild(lbl);row.appendChild(val);el.appendChild(row);
  });
}

function renderDots(){
  const total=Math.max(recordings.length,15);
  const el=document.getElementById('vi-dots');el.innerHTML='';
  for(let i=0;i<total;i++){
    const d=document.createElement('div');d.className='vi-dot'+(i===activeDot?' active':'');
    if(i===total-1&&i!==activeDot)d.style.background='#333';
    else if(i!==activeDot)d.style.background='#f5a623';
    d.title=recordings[i]?'Tick '+recordings[i].tick_id:String(i);
    d.addEventListener('click',()=>{
      activeDot=i;renderDots();
      if(recordings[i]) vscode.postMessage({command:'jumpToTick',tickId:recordings[i].tick_id});
    });
    el.appendChild(d);
  }
}

// Render demo content initially
document.getElementById('vi-code').innerHTML=highlightJson(JSON.stringify(JSON_DEMO,null,2));
renderMeta(META_DEMO);
renderDots();

document.getElementById('btn-print').addEventListener('click',()=>{
  const code=document.getElementById('vi-code').textContent;
  console.log('[WaterCodeFlow] Variable value:\n'+code);
});

window.addEventListener('message',evt=>{
  const msg=evt.data;
  if(msg.command==='setData'){
    filePath=msg.filePath||'';
    recordings=msg.recordings||[];
    activeDot=Math.max(0,recordings.length-1);
    // Update file path in snippet
    document.getElementById('vi-snippet').textContent=
      'from some_import_name import s\ns.inspect(variable_name="user_data", runs=5)';
    // Update metadata file path
    if(filePath){
      const metaCopy=JSON.parse(JSON.stringify(META_DEMO));
      const fp=metaCopy.find(m=>m.label==='File Path');
      if(fp) fp.value=filePath;
      renderMeta(metaCopy);
    }
    renderDots();
  }
});

vscode.postMessage({command:'ready'});
})();
