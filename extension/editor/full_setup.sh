#!/bin/bash
# ============================================================================
# WATERCODEFLOW — COMPLETE AUTOMATED SETUP v2
# ============================================================================
set -e

BOLD='\033[1m'; GREEN='\033[92m'; RED='\033[91m'; YELLOW='\033[93m'; CYAN='\033[96m'; RESET='\033[0m'
EXTENSION_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$EXTENSION_ROOT"
LOG_FILE="$EXTENSION_ROOT/setup.log"
echo "Setup started at $(date)" > "$LOG_FILE"

info()    { echo -e "${CYAN}i $1${RESET}"; }
success() { echo -e "${GREEN}+ $1${RESET}"; }
warn()    { echo -e "${YELLOW}! $1${RESET}"; }
fail()    { echo -e "${RED}FAIL: $1${RESET}"; exit 1; }
step()    { echo -e "\n${BOLD}> $1${RESET}"; }

echo -e "${BOLD}WaterCodeFlow — Automated Setup v2${RESET}"

# Step 1: System checks
step "System checks"
command -v python3 >/dev/null || fail "python3 required"
success "python3: $(python3 --version 2>&1)"
command -v node >/dev/null || fail "node required"
success "node: $(node --version)"

# Step 2: Python deps
step "Python dependencies"
python3 -c "import psutil" 2>/dev/null && success "psutil ok" || {
  python3 -m pip install psutil --break-system-packages >>"$LOG_FILE" 2>&1 && success "psutil installed" || warn "psutil unavailable"
}

# Verify glue adapter
if echo '{"id":"v","command":"getStatus","filePath":"test.py"}' | \
   PYTHONPATH="$EXTENSION_ROOT:$EXTENSION_ROOT/CodeVovle" python3 glue/adapter.py 2>/dev/null | \
   grep -q '"success": true'; then
  success "Glue adapter working"
else
  warn "Glue adapter check inconclusive (ok if CodeVovle not yet built)"
fi

# Step 3: Type stubs
step "TypeScript type stubs"
mkdir -p node_modules/@types/vscode node_modules/@types/node

# Find @types/node from existing npm packages
for candidate in \
  "$HOME/.npm-global/lib/node_modules/pptxgenjs/node_modules/@types/node" \
  "$(npm root -g 2>/dev/null)/@types/node" \
  "/usr/lib/node_modules/@types/node"; do
  if [ -d "$candidate" ]; then
    cp -r "$candidate/"* node_modules/@types/node/ 2>/dev/null || true
    success "@types/node from $candidate"
    break
  fi
done

python3 - << 'PYEOF'
stub = '''interface Thenable<T> extends PromiseLike<T> {}
declare module "vscode" {
  export enum ViewColumn{One=1,Two=2,Three=3,Active=-1,Beside=-2}
  export enum ConfigurationTarget{Global=1,Workspace=2,WorkspaceFolder=3}
  export interface Disposable{dispose():any}
  export interface CancellationToken{isCancellationRequested:boolean}
  export interface Uri{scheme:string;path:string;fsPath:string;toString():string;with(c:any):Uri}
  export namespace Uri{function file(p:string):Uri;function joinPath(b:Uri,...s:string[]):Uri;function parse(v:string,x?:boolean):Uri}
  export interface WorkspaceFolder{uri:Uri;name:string}
  export interface WorkspaceConfiguration{get<T>(s:string,d:T):T;update(s:string,v:any,t?:ConfigurationTarget):Thenable<void>}
  export namespace workspace{let workspaceFolders:WorkspaceFolder[]|undefined;function getConfiguration(s?:string):WorkspaceConfiguration;function findFiles(i:string,e?:string,m?:number):Thenable<Uri[]>}
  export interface WebviewOptions{enableScripts?:boolean;localResourceRoots?:Uri[]}
  export interface Webview{options:WebviewOptions;html:string;cspSource:string;onDidReceiveMessage:Event<any>;postMessage(m:any):Thenable<boolean>;asWebviewUri(r:Uri):Uri}
  export interface WebviewView{webview:Webview;onDidDispose:Event<void>;show(p?:boolean):void}
  export interface WebviewViewResolveContext<T=unknown>{state:T|undefined}
  export interface WebviewViewProvider{resolveWebviewView(v:WebviewView,c:WebviewViewResolveContext,t:CancellationToken):Thenable<void>|void}
  export interface WebviewPanel{webview:Webview;onDidDispose:Event<void>;reveal(v?:ViewColumn,p?:boolean):void;dispose():any;viewColumn:ViewColumn|undefined}
  export interface Event<T>{(l:(e:T)=>any,t?:any,d?:Disposable[]):Disposable}
  export interface TextDocument{fileName:string}
  export interface TextEditor{document:TextDocument;viewColumn:ViewColumn|undefined}
  export interface Terminal{show(p?:boolean):void;sendText(t:string,n?:boolean):void}
  export namespace window{let activeTextEditor:TextEditor|undefined;const onDidChangeActiveTextEditor:Event<TextEditor|undefined>;function createWebviewPanel(t:string,ti:string,s:any,o?:WebviewOptions):WebviewPanel;function registerWebviewViewProvider(t:string,p:WebviewViewProvider,o?:any):Disposable;function createTerminal(n?:string):Terminal;function showInformationMessage(m:string,...i:string[]):Thenable<string|undefined>;function showWarningMessage(m:string,...i:string[]):Thenable<string|undefined>;function showErrorMessage(m:string,...i:string[]):Thenable<string|undefined>}
  export namespace commands{function registerCommand(c:string,cb:(...a:any[])=>any):Disposable;function executeCommand<T=unknown>(c:string,...r:any[]):Thenable<T>}
  export interface ExtensionContext{subscriptions:Disposable[];extensionUri:Uri;extensionPath:string;globalState:{get<T>(k:string):T|undefined;update(k:string,v:any):Thenable<void>}}
}'''
with open('node_modules/@types/vscode/index.d.ts','w') as f:
    f.write(stub)
print("vscode stub written")
PYEOF
success "Type stubs ready"

# Step 3.5: Bundle backend dependencies into extension directory
step "Bundling backend dependencies"
PARENT_DIR="$(dirname "$EXTENSION_ROOT")"

# Copy CodeVovle (codevovle Python package) if it's not already here
if [ -d "$PARENT_DIR/CodeVovle" ] && [ ! -d "$EXTENSION_ROOT/CodeVovle" ]; then
  cp -r "$PARENT_DIR/CodeVovle" "$EXTENSION_ROOT/CodeVovle"
  success "Copied CodeVovle -> $EXTENSION_ROOT/CodeVovle"
elif [ -d "$EXTENSION_ROOT/CodeVovle" ]; then
  success "CodeVovle already present"
else
  warn "CodeVovle not found in parent directory — codevovle features will be limited"
fi

# Copy pre-built watcher .so files if available
WATCHER_BUILD="$PARENT_DIR/watcher/build"
if [ -d "$WATCHER_BUILD" ]; then
  mkdir -p "$EXTENSION_ROOT/watcher/build"
  cp "$WATCHER_BUILD"/*.so "$EXTENSION_ROOT/watcher/build/" 2>/dev/null || true
  success "Copied watcher shared libs"
fi

# Copy watcher CLI and adapters for Python tracking
WATCHER_SRC="$PARENT_DIR/watcher"
if [ -d "$WATCHER_SRC" ] && [ ! -d "$EXTENSION_ROOT/watcher/cli" ]; then
  mkdir -p "$EXTENSION_ROOT/watcher"
  cp -r "$WATCHER_SRC/cli" "$EXTENSION_ROOT/watcher/cli" 2>/dev/null || true
  cp -r "$WATCHER_SRC/adapters" "$EXTENSION_ROOT/watcher/adapters" 2>/dev/null || true
  cp -r "$WATCHER_SRC/core" "$EXTENSION_ROOT/watcher/core" 2>/dev/null || true
  success "Copied watcher CLI and adapters"
fi

# Step 4: Compile TypeScript
step "Compiling TypeScript"
TSC_BIN=""
for t in tsc ./node_modules/.bin/tsc "$HOME/.npm-global/bin/tsc"; do
  "$t" --version >/dev/null 2>&1 && TSC_BIN="$t" && break
done
[ -z "$TSC_BIN" ] && fail "tsc not found"
"$TSC_BIN" -p ./ 2>>"$LOG_FILE" && success "TypeScript compiled" || {
  tail -20 "$LOG_FILE"; fail "TypeScript compilation failed"; }

# Step 5: Package VSIX
step "Packaging VSIX"
python3 - << 'PYEOF'
import zipfile, os, sys

base = os.getcwd()
vsix_path = os.path.join(base, 'watercodeflow-0.2.0.vsix')

ct = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension=".json" ContentType="application/json"/>
  <Default Extension=".js" ContentType="application/javascript"/>
  <Default Extension=".ts" ContentType="text/plain"/>
  <Default Extension=".css" ContentType="text/css"/>
  <Default Extension=".svg" ContentType="image/svg+xml"/>
  <Default Extension=".map" ContentType="application/json"/>
  <Default Extension=".vsixmanifest" ContentType="text/xml"/>
  <Default Extension=".py" ContentType="text/plain"/>
  <Default Extension=".sh" ContentType="text/plain"/>
  <Default Extension=".md" ContentType="text/plain"/>
  <Default Extension=".so" ContentType="application/octet-stream"/>
  <Default Extension=".txt" ContentType="text/plain"/>
</Types>'''
mf = '''<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="watercodeflow" Version="0.2.0" Publisher="watercodeflow"/>
    <DisplayName>WaterCodeFlow</DisplayName>
    <Description xml:space="preserve">Time-travel debugger for Python</Description>
    <Tags>debugger,python,time-travel</Tags>
    <Categories>Debuggers</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.89.0"/></Properties>
  </Metadata>
  <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation>
  <Dependencies/>
  <Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets>
</PackageManifest>'''

INCLUDE_DIRS=['out','media','glue','CodeVovle','storage_utility','watcher']
INCLUDE_FILES=['package.json','tsconfig.json']
EXCLUDE_DIRS={'node_modules','__pycache__','.git','tests','idea_images','editor','.vscode-test','.codevovle','.vscode'}
EXCLUDE_EXTS={'.pyc','.o','.bin'}

with zipfile.ZipFile(vsix_path,'w',zipfile.ZIP_DEFLATED) as zf:
    zf.writestr('[Content_Types].xml',ct)
    zf.writestr('extension.vsixmanifest',mf)
    for fn in INCLUDE_FILES:
        fp=os.path.join(base,fn)
        if os.path.exists(fp): zf.write(fp,'extension/'+fn)
    for d in INCLUDE_DIRS:
        dp=os.path.join(base,d)
        if not os.path.isdir(dp): continue
        for root,dirs,files in os.walk(dp):
            dirs[:]=[x for x in dirs if x not in EXCLUDE_DIRS]
            for fn in files:
                _,ext=os.path.splitext(fn)
                if ext in EXCLUDE_EXTS: continue
                fp=os.path.join(root,fn)
                zf.write(fp,'extension/'+os.path.relpath(fp,base))

sz=os.path.getsize(vsix_path)
print(f"VSIX: {vsix_path} ({sz//1024}KB)")
sys.exit(0)
PYEOF

VSIX_FILE=$(ls -t *.vsix 2>/dev/null | head -1)
[ -z "$VSIX_FILE" ] && fail "VSIX not created"
success "VSIX: $VSIX_FILE"

echo ""
echo -e "${BOLD}${GREEN}Setup complete!${RESET}"
echo -e "Install: code --install-extension $EXTENSION_ROOT/$VSIX_FILE"
