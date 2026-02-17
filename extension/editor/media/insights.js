(function(){
const vscode=acquireVsCodeApi();
const canvas=document.getElementById('insight-canvas');
const ctx=canvas.getContext('2d');
const getInsightsBtn=document.getElementById('get-insights-btn');
const insightsResult=document.getElementById('insights-result');

let nodeStates={};
let selectionOrder=[];
let nodes=[];
let recordings=[];
let branches=[];

function resize(){
  canvas.width=canvas.offsetWidth;
  canvas.height=canvas.offsetHeight;
  draw();
}

function buildNodes(){
  const W=canvas.width,H=canvas.height;
  const midY=H*0.5;
  const result=[];

  // Build main timeline from recordings count
  const total=Math.max(recordings.length,5);
  const mainCount=Math.min(total,8);
  const mainXs=Array.from({length:mainCount},(_,i)=>(0.07+(i*(0.86/(mainCount-1))))*W);

  mainXs.forEach((x,i)=>{
    result.push({id:'main-'+i,x,y:midY,rx:18,ry:11,type:'main',color:'#4ec9b0',tickId:recordings[i]?.tick_id});
  });

  // Branch nodes from middle main nodes
  const branchSrcs=[1,2,Math.floor(mainCount/2)].filter((v,i,a)=>a.indexOf(v)===i&&v<mainCount);
  branchSrcs.forEach((srcIdx,si)=>{
    const srcX=mainXs[srcIdx];
    const branchX=srcX+44;
    for(let k=0;k<4;k++){
      const dy=(k+1)*40;
      const isYellow=(si===0&&k===1)||(si===0&&k===0&&si===0);
      result.push({id:`b${si}u${k}`,x:branchX,y:midY-dy,rx:11,ry:7,type:'branch',color:isYellow?'#f5c518':'#666',srcX,srcY:midY});
      result.push({id:`b${si}d${k}`,x:branchX,y:midY+dy,rx:11,ry:7,type:'branch',color:isYellow&&k===0?'#f5c518':'#666',srcX,srcY:midY});
    }
  });
  return result;
}

function draw(){
  const W=canvas.width,H=canvas.height;
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle='#1e1e1e';ctx.fillRect(0,0,W,H);
  nodes=buildNodes();
  const main=nodes.filter(n=>n.type==='main');
  const midY=H*0.5;

  // Main line
  ctx.strokeStyle='#fff';ctx.lineWidth=1.5;
  for(let i=0;i<main.length-1;i++){
    ctx.beginPath();ctx.moveTo(main[i].x,midY);ctx.lineTo(main[i+1].x,midY);ctx.stroke();
  }
  // Branch connectors
  nodes.filter(n=>n.type==='branch').forEach(n=>{
    ctx.strokeStyle='#888';ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(n.srcX,n.srcY);ctx.lineTo(n.x-n.rx-4,n.srcY);ctx.lineTo(n.x-n.rx-4,n.y);ctx.lineTo(n.x-n.rx,n.y);ctx.stroke();
  });
  // Nodes
  nodes.forEach(n=>{
    const st=nodeStates[n.id];
    let fill=n.color;
    if(st==='first')fill='#ff4444';
    else if(st==='second')fill='#f5c518';
    ctx.beginPath();ctx.ellipse(n.x,n.y,n.rx,n.ry,0,0,Math.PI*2);
    ctx.fillStyle=fill;ctx.fill();
    if(st){ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke();}
  });

  // Branch name labels
  if(branches.length>0){
    ctx.fillStyle='#aaa';ctx.font='11px "Segoe UI",sans-serif';
    branches.forEach((b,i)=>{
      if(main[i]) ctx.fillText(b.name||b,main[i].x-14,midY-main[i].ry-8);
    });
  }
}

function getNodeAt(mx,my){return nodes.find(n=>{const dx=mx-n.x,dy=my-n.y;return Math.sqrt(dx*dx+dy*dy)<14;});}

canvas.addEventListener('mousemove',e=>{
  const r=canvas.getBoundingClientRect();
  canvas.style.cursor=getNodeAt(e.clientX-r.left,e.clientY-r.top)?'pointer':'default';
});

canvas.addEventListener('click',e=>{
  const r=canvas.getBoundingClientRect();
  const n=getNodeAt(e.clientX-r.left,e.clientY-r.top);
  if(!n)return;
  const cur=nodeStates[n.id];
  const active=selectionOrder.filter(id=>nodeStates[id]);
  if(cur){
    delete nodeStates[n.id];
    selectionOrder=selectionOrder.filter(id=>id!==n.id);
  } else if(active.length===0){
    nodeStates[n.id]='first';selectionOrder.push(n.id);
  } else if(active.length===1){
    nodeStates[n.id]='second';selectionOrder.push(n.id);
  } else {
    delete nodeStates[selectionOrder[0]];selectionOrder.shift();
    nodeStates[n.id]='second';selectionOrder.push(n.id);
  }
  draw();
});

getInsightsBtn.addEventListener('click',()=>{
  const selected=selectionOrder.filter(id=>nodeStates[id]);
  if(selected.length<2){
    insightsResult.className='';
    insightsResult.style.cssText='position:absolute;left:50%;transform:translateX(-50%);top:55%;background:#252525;border:1px solid #555;color:#ccc;padding:10px 18px;border-radius:4px;font-size:12px';
    insightsResult.textContent='Select two nodes (before & after) to get insights.';
    return;
  }
  const n1=nodes.find(n=>n.id===selected[0]);
  const n2=nodes.find(n=>n.id===selected[1]);
  vscode.postMessage({command:'getInsights',fromTick:n1?.tickId,toTick:n2?.tickId});
  insightsResult.className='';
  insightsResult.style.cssText='position:absolute;left:50%;transform:translateX(-50%);top:55%;background:#252525;border:1px solid #555;color:#9cdcfe;padding:10px 18px;border-radius:4px;font-size:12px';
  insightsResult.textContent='Generating insights...';
});

window.addEventListener('message',evt=>{
  const msg=evt.data;
  if(msg.command==='setBranchData'){
    recordings=msg.recordings||[];
    branches=msg.branches||[];
    resize();
  } else if(msg.command==='insightsResult'){
    insightsResult.className='';
    insightsResult.style.cssText='position:absolute;left:50%;transform:translateX(-50%);top:55%;max-width:60%;background:#1e2a1e;border:1px solid #4ec9b0;color:#ccc;padding:14px 18px;border-radius:4px;font-size:12px;white-space:pre-wrap;overflow:auto;max-height:200px';
    insightsResult.textContent=typeof msg.result==='object'?JSON.stringify(msg.result,null,2):String(msg.result);
  } else if(msg.command==='insightsError'){
    insightsResult.className='';
    insightsResult.style.cssText='position:absolute;left:50%;transform:translateX(-50%);top:55%;background:#2a1e1e;border:1px solid #f48771;color:#f48771;padding:10px 18px;border-radius:4px;font-size:12px';
    insightsResult.textContent='Insights error: '+msg.error;
  }
});

window.addEventListener('resize',resize);
vscode.postMessage({command:'ready'});
setTimeout(resize,50);
})();
