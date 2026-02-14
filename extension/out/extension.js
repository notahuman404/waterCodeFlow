"use strict";var M=Object.create;var b=Object.defineProperty;var I=Object.getOwnPropertyDescriptor;var S=Object.getOwnPropertyNames;var $=Object.getPrototypeOf,E=Object.prototype.hasOwnProperty;var V=(o,e)=>{for(var i in e)b(o,i,{get:e[i],enumerable:!0})},U=(o,e,i,t)=>{if(e&&typeof e=="object"||typeof e=="function")for(let s of S(e))!E.call(o,s)&&s!==i&&b(o,s,{get:()=>e[s],enumerable:!(t=I(e,s))||t.enumerable});return o};var h=(o,e,i)=>(i=o!=null?M($(o)):{},U(e||!o||!o.__esModule?b(i,"default",{value:o,enumerable:!0}):i,o)),j=o=>U(b({},"__esModule",{value:!0}),o);var O={};V(O,{activate:()=>G,deactivate:()=>D,getActiveFilePath:()=>H,getNonce:()=>N});module.exports=j(O);var n=h(require("vscode")),x=require("crypto");var T=require("child_process"),F=require("crypto"),W=h(require("path")),_=class{constructor(){this.subprocess=null;this.pendingRequests=new Map;this.readyResolve=null;this.lines=[];this.ready=new Promise(e=>{this.readyResolve=e})}async spawn(e){return new Promise((i,t)=>{try{let s=W.join(e,"glue","adapter.py");this.subprocess=(0,T.spawn)("python3",["-m","glue.adapter"],{cwd:e,stdio:["pipe","pipe","pipe"],env:{...process.env}}),this.subprocess.on("error",r=>{console.error("[GlueClient] subprocess error:",r),t(r)}),this.subprocess.stdout.on("data",r=>{this.handleData(r.toString())}),this.subprocess.stderr.on("data",r=>{console.error("[GlueClient] stderr:",r.toString())}),setTimeout(()=>{this.readyResolve&&this.readyResolve(),i()},500)}catch(s){t(s)}})}async send(e){if(await this.ready,!this.subprocess||!this.subprocess.stdin)throw new Error("GlueClient not initialized. Call spawn() first.");let i=(0,F.v4)(),t={...e,id:i};return new Promise((s,r)=>{this.pendingRequests.set(i,g=>{g.success?s(g.result):r(new Error(`[${g.errorType||"GlueError"}] ${g.error}`))});let v=JSON.stringify(t)+`
`;this.subprocess.stdin.write(v)})}handleData(e){let i=(this.lines.join("")+e).split(`
`);this.lines=[i[i.length-1]];for(let t=0;t<i.length-1;t++){let s=i[t].trim();if(s)try{let r=JSON.parse(s),v=this.pendingRequests.get(r.id);v?(this.pendingRequests.delete(r.id),v(r)):console.warn("[GlueClient] received response for unknown request:",r.id)}catch(r){console.error("[GlueClient] failed to parse JSON:",s,r)}}}kill(){this.subprocess&&!this.subprocess.killed&&(this.subprocess.kill(),this.subprocess=null)}isAlive(){return this.subprocess!==null&&!this.subprocess.killed}},R=null;function a(){return R||(R=new _),R}var p=h(require("vscode"));var f=class{constructor(e,i){this.context=e;this.nonce=i;this._activeFile="";this.statusRefreshInterval=null}static{this.viewType="watercodeflow.recordings"}resolveWebviewView(e,i,t){this._view=e,e.webview.options={enableScripts:!0,localResourceRoots:[p.Uri.joinPath(this.context.extensionUri,"media")]},e.webview.html=this.getHtmlForWebview(e.webview),e.webview.onDidReceiveMessage(async s=>{await this.handleMessage(s)}),this.statusRefreshInterval=setInterval(()=>{this.refreshStatus()},2e3)}setActiveFile(e){this._activeFile=e,this.refreshRecordings(),this.refreshStatus()}async refreshStatus(){if(!(!this._view||!this._activeFile))try{let i=await a().send({command:"getStatus",filePath:this._activeFile});this._view.webview.postMessage({type:"statusUpdate",status:i})}catch(e){console.log("Status refresh error (expected if not recording):",e)}}async refreshRecordings(){if(!(!this._view||!this._activeFile))try{let i=await a().send({command:"listRuns",filePath:this._activeFile});this._view.webview.postMessage({type:"recordingsUpdate",recordings:i})}catch(e){console.log("Recordings refresh error:",e)}}async handleMessage(e){let i=a();switch(e.command){case"startRecording":{try{let t=await i.send({command:"startRecording",filePath:e.filePath,interval:e.interval||.5});this._view?.webview.postMessage({type:"recordingStarted",pid:t}),this.refreshStatus()}catch(t){this._view?.webview.postMessage({type:"error",message:`Failed to start recording: ${t}`})}break}case"stopRecording":{try{await i.send({command:"stopRecording",filePath:e.filePath}),this._view?.webview.postMessage({type:"recordingStopped"}),this.refreshStatus()}catch(t){this._view?.webview.postMessage({type:"error",message:`Failed to stop recording: ${t}`})}break}case"jumpToTick":{try{await i.send({command:"jumpToTick",filePath:e.filePath,tickId:e.tickId}),this._view?.webview.postMessage({type:"cursorUpdate",tick:e.tickId})}catch(t){this._view?.webview.postMessage({type:"error",message:`Failed to jump to tick: ${t}`})}break}case"openRun":{p.commands.executeCommand("watercodeflow.openInspector",e.runId);break}case"deleteRun":{try{await i.send({command:"deleteRun",filePath:e.filePath,runId:e.runId}),this.refreshRecordings(),this.refreshStatus()}catch(t){this._view?.webview.postMessage({type:"error",message:`Failed to delete run: ${t}`})}break}}}getHtmlForWebview(e){let i=e.asWebviewUri(p.Uri.joinPath(this.context.extensionUri,"media","recordings.js"));return`<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="${e.asWebviewUri(p.Uri.joinPath(this.context.extensionUri,"media","recordings.css"))}">
    <title>Recordings</title>
</head>
<body>
    <div id="recordings-container">
        <div id="controls">
            <button id="btn-start">Start Recording</button>
            <button id="btn-stop">Stop Recording</button>
            <div id="status">Ready</div>
        </div>
        <div id="recordings-list"></div>
    </div>
    <script nonce="${this.nonce}" src="${i}"></script>
</body>
</html>`}dispose(){this.statusRefreshInterval&&clearInterval(this.statusRefreshInterval)}};var w=h(require("vscode"));var y=class{constructor(e,i){this.context=e;this.nonce=i;this._activeFile=""}static{this.viewType="watercodeflow.variables"}resolveWebviewView(e,i,t){this._view=e,e.webview.options={enableScripts:!0,localResourceRoots:[w.Uri.joinPath(this.context.extensionUri,"media")]},e.webview.html=this.getHtmlForWebview(e.webview),e.webview.onDidReceiveMessage(async s=>{await this.handleMessage(s)})}setActiveFile(e){this._activeFile=e,this.refreshVariables()}async refreshVariables(){if(!(!this._view||!this._activeFile))try{let i=await a().send({command:"listTrackedVariables",filePath:this._activeFile});this._view.webview.postMessage({type:"variablesUpdate",variables:i})}catch(e){console.log("Variables refresh error:",e)}}async handleMessage(e){let i=a();switch(e.command){case"inspectVariable":{w.commands.executeCommand("watercodeflow.openInspector",e.varName);break}case"inferVariables":{try{let t=await i.send({command:"listTrackedVariables",filePath:e.filePath||this._activeFile});this._view?.webview.postMessage({type:"variables",variables:t})}catch(t){this._view?.webview.postMessage({type:"error",message:`Failed to infer variables: ${t}`})}break}}}getHtmlForWebview(e){let i=e.asWebviewUri(w.Uri.joinPath(this.context.extensionUri,"media","variables.js"));return`<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="${e.asWebviewUri(w.Uri.joinPath(this.context.extensionUri,"media","variables.css"))}">
    <title>Variables</title>
</head>
<body>
    <div id="variables-container">
        <div id="controls">
            <button id="btn-infer">Infer Variables</button>
        </div>
        <ul id="variables-list"></ul>
    </div>
    <script nonce="${this.nonce}" src="${i}"></script>
</body>
</html>`}dispose(){}};var c=h(require("vscode"));var P=class{constructor(e,i,t,s){this.filePath=t;this.varName=s;this._disposed=!1;this._panel=c.window.createWebviewPanel("watercodeflow.inspector",`Inspector: ${s}`,c.ViewColumn.Beside,{enableScripts:!0,localResourceRoots:[c.Uri.joinPath(e.extensionUri,"media")]}),this._panel.webview.html=this.getHtmlForWebview(this._panel.webview,e,i),this._panel.webview.onDidReceiveMessage(async r=>{await this.handleMessage(r)}),this._panel.onDidDispose(()=>{this._disposed=!0}),this.loadTimeline()}async loadTimeline(){if(!this._disposed)try{let i=await a().send({command:"getVariableTimeline",filePath:this.filePath,variableName:this.varName,maxTicks:200});this._panel.webview.postMessage({type:"timelineLoaded",timeline:i,varName:this.varName})}catch(e){this._panel.webview.postMessage({type:"error",message:`Failed to load timeline: ${e}`})}}async handleMessage(e){let i=a();switch(e.command){case"scrub":{try{await i.send({command:"jumpToTick",filePath:this.filePath,tickId:e.tick}),this._panel.webview.postMessage({type:"scrubbed",tick:e.tick})}catch(t){this._panel.webview.postMessage({type:"error",message:`Failed to scrub: ${t}`})}break}case"scrollToLine":{let t=c.window.activeTextEditor;if(t){let s=Math.max(0,(e.lineNo||1)-1);t.selection=new c.Selection(s,0,s,0),t.revealRange(new c.Range(s,0,s,100),c.TextEditorRevealType.InCenter)}break}}}getHtmlForWebview(e,i,t){let s=e.asWebviewUri(c.Uri.joinPath(i.extensionUri,"media","inspector.js"));return`<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="${e.asWebviewUri(c.Uri.joinPath(i.extensionUri,"media","inspector.css"))}">
    <title>Variable Inspector</title>
</head>
<body>
    <div id="inspector-container">
        <div id="header">
            <h2 id="var-name"></h2>
            <button id="btn-close">\xD7</button>
        </div>
        <div id="timeline-view">
            <div id="timeline-list"></div>
            <div id="timeline-metadata"></div>
        </div>
    </div>
    <script nonce="${t}" src="${s}"></script>
</body>
</html>`}dispose(){this._panel.dispose(),this._disposed=!0}[Symbol.dispose](){this.dispose()}};var d=h(require("vscode"));var C=class{constructor(e,i,t,s,r){this.filePath=t;this.fromTick=s;this.toTick=r;this._disposed=!1;this._panel=d.window.createWebviewPanel("watercodeflow.insights",`Insights: ${s} \u2192 ${r}`,d.ViewColumn.Beside,{enableScripts:!0,localResourceRoots:[d.Uri.joinPath(e.extensionUri,"media")]}),this._panel.webview.html=this.getHtmlForWebview(this._panel.webview,e,i),this._panel.webview.onDidReceiveMessage(async v=>{await this.handleMessage(v)}),this._panel.onDidDispose(()=>{this._disposed=!0}),this.loadInsights()}async loadInsights(){if(!this._disposed)try{let i=await a().send({command:"getInsights",filePath:this.filePath,fromTick:this.fromTick.toString(),toTick:this.toTick.toString(),model:"gemini"});this._panel.webview.postMessage({type:"insightsLoaded",insights:i})}catch(e){this._panel.webview.postMessage({type:"error",message:`Failed to load insights: ${e}`})}}async handleMessage(e){let i=a();switch(e.command){case"scrubToTick":{try{await i.send({command:"jumpToTick",filePath:this.filePath,tickId:e.tick}),this._panel.webview.postMessage({type:"scrubbedToTick",tick:e.tick})}catch(t){this._panel.webview.postMessage({type:"error",message:`Failed to scrub to tick: ${t}`})}break}case"highlightLine":{let t=d.window.activeTextEditor;if(t){let s=Math.max(0,(e.lineNo||1)-1);t.selection=new d.Selection(s,0,s,0),t.revealRange(new d.Range(s,0,s,100),d.TextEditorRevealType.InCenter)}break}}}getHtmlForWebview(e,i,t){let s=e.asWebviewUri(d.Uri.joinPath(i.extensionUri,"media","insights.js"));return`<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="${e.asWebviewUri(d.Uri.joinPath(i.extensionUri,"media","insights.css"))}">
    <title>Insights</title>
</head>
<body>
    <div id="insights-container">
        <div id="header">
            <h2>Insights</h2>
            <button id="btn-close">\xD7</button>
        </div>
        <div id="insights-content">
            <div id="insights-summary"></div>
            <div id="affected-lines"></div>
        </div>
    </div>
    <script nonce="${t}" src="${s}"></script>
</body>
</html>`}dispose(){this._panel.dispose(),this._disposed=!0}[Symbol.dispose](){this.dispose()}};var m,l="",u=null,k=null;async function G(o){console.log("[WaterCodeFlow] Activating..."),m=(0,x.randomUUID)();let e=a();try{await e.spawn(o.extensionPath),console.log("[WaterCodeFlow] Glue client initialized")}catch(i){console.error("[WaterCodeFlow] Failed to spawn glue adapter:",i),n.window.showErrorMessage("WaterCodeFlow: Failed to start glue adapter. Is Python installed?");return}o.subscriptions.push(n.window.onDidChangeActiveTextEditor(i=>{i&&i.document.languageId==="python"&&(l=i.document.uri.fsPath,u?.setActiveFile(l),k?.setActiveFile(l))})),u=new f(o,m),k=new y(o,m),o.subscriptions.push(n.window.registerWebviewViewProvider("watercodeflow.recordings",u,{webviewOptions:{retainContextWhenHidden:!0}})),o.subscriptions.push(n.window.registerWebviewViewProvider("watercodeflow.variables",k,{webviewOptions:{retainContextWhenHidden:!0}})),o.subscriptions.push(n.commands.registerCommand("watercodeflow.startRecording",async()=>{if(!l){n.window.showWarningMessage("No Python file is currently active");return}let i=await n.window.showInputBox({prompt:"Recording interval (seconds)",value:"0.5"});if(i!==void 0)try{let t=await e.send({command:"startRecording",filePath:l,interval:parseFloat(i)});n.window.showInformationMessage(`Recording started (PID: ${t})`),u?.refreshStatus()}catch(t){n.window.showErrorMessage(`Failed to start recording: ${t}`)}})),o.subscriptions.push(n.commands.registerCommand("watercodeflow.stopRecording",async()=>{if(!l){n.window.showWarningMessage("No Python file is currently active");return}try{await e.send({command:"stopRecording",filePath:l}),n.window.showInformationMessage("Recording stopped"),u?.refreshStatus()}catch(i){n.window.showErrorMessage(`Failed to stop recording: ${i}`)}})),o.subscriptions.push(n.commands.registerCommand("watercodeflow.openInspector",async i=>{if(!l){n.window.showWarningMessage("No Python file is currently active");return}let t=new P(o,m,l,i);o.subscriptions.push(t)})),o.subscriptions.push(n.commands.registerCommand("watercodeflow.openInsights",async(i,t)=>{if(!l){n.window.showWarningMessage("No Python file is currently active");return}let s=new C(o,m,l,i,t);o.subscriptions.push(s)})),console.log("[WaterCodeFlow] Extension fully activated")}function D(){console.log("[WaterCodeFlow] Deactivating..."),a().kill()}function N(){return m}function H(){return l}0&&(module.exports={activate,deactivate,getActiveFilePath,getNonce});
