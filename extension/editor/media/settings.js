(function(){
const vscode=acquireVsCodeApi();

document.getElementById('saveBtn').addEventListener('click',()=>{
  vscode.postMessage({
    command:'saveSettings',
    trackThreads:document.getElementById('trackThreads').checked,
    trackLocals:document.getElementById('trackLocals').checked,
    trackSql:document.getElementById('trackSql').checked,
    trackAll:document.getElementById('trackAll').checked,
    samplingInterval:parseFloat(document.getElementById('samplingInterval').value)||0.5,
    daemonThreads:parseInt(document.getElementById('daemonThreads').value)||4,
    aiModel:document.getElementById('aiModel').value,
    logLevel:document.getElementById('logLevel').value,
  });
});

document.getElementById('browseBtn').addEventListener('click',()=>{
  // Signal extension to open file picker
  vscode.postMessage({command:'browseProcessor'});
});

document.getElementById('resetBtn').addEventListener('click',()=>{
  vscode.postMessage({command:'resetRecording'});
});

document.getElementById('bgBtn').addEventListener('click',()=>{
  vscode.postMessage({command:'backgroundRecording'});
});

window.addEventListener('message',evt=>{
  const msg=evt.data;
  if(msg.command==='loadSettings' && msg.settings){
    const s=msg.settings;
    document.getElementById('trackThreads').checked=!!s.trackThreads;
    document.getElementById('trackLocals').checked=!!s.trackLocals;
    document.getElementById('trackSql').checked=!!s.trackSql;
    document.getElementById('trackAll').checked=!!s.trackAll;
    document.getElementById('samplingInterval').value=s.samplingInterval||0.5;
    document.getElementById('daemonThreads').value=s.daemonThreads||4;
    document.getElementById('aiModel').value=s.aiModel||'Gemini';
    document.getElementById('logLevel').value=s.logLevel||'INFO';
  }
});
})();
