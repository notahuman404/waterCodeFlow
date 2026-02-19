#!/bin/bash
# ============================================================================
# WATERCODEFLOW EXTENSION - COMPLETE AUTOMATED SETUP
# ============================================================================
# This script does EVERYTHING to set up the extension:
#   1.  Checks and installs system dependencies
#   2.  Fixes hardcoded paths in watcher test files
#   3.  Builds C++ components (storage, watcher core, adapters, processor)
#   4.  Copies built libraries to their expected locations
#   5.  Installs Python dependencies (CodeVovle + glue)
#   6.  Installs Node.js dependencies inside editor/
#   7.  Compiles TypeScript inside editor/
#   8.  Packages the extension as a .vsix file
#   9.  Prints installation instructions
#
# Usage:
#   chmod +x full_setup.sh
#   ./full_setup.sh
# ============================================================================

set -e

# ── Colours ──────────────────────────────────────────────────────────────────

BOLD='\033[1m'
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BLUE='\033[94m'
CYAN='\033[96m'
RESET='\033[0m'

# ── Paths ─────────────────────────────────────────────────────────────────────

EXTENSION_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EDITOR_DIR="$EXTENSION_ROOT/editor"
LOG_FILE="$EXTENSION_ROOT/setup.log"

cd "$EXTENSION_ROOT"
echo "Setup started at $(date)" > "$LOG_FILE"

# ── Helper functions ──────────────────────────────────────────────────────────

print_header() {
    echo -e "\n${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${CYAN}║  $1${RESET}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${RESET}\n"
}

print_step()    { echo -e "${BOLD}${BLUE}▶ $1${RESET}"; }
print_success() { echo -e "${GREEN}✓ $1${RESET}"; }
print_error()   { echo -e "${RED}✗ $1${RESET}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${RESET}"; }
print_info()    { echo -e "${CYAN}ℹ $1${RESET}"; }

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_command() {
    command -v "$1" &>/dev/null
}

# Detect OS and package manager
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="mac"
        PKG_MANAGER="brew"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if check_command apt-get; then
            PKG_MANAGER="apt"
        elif check_command dnf; then
            PKG_MANAGER="dnf"
        elif check_command yum; then
            PKG_MANAGER="yum"
        else
            PKG_MANAGER="unknown"
        fi
    else
        OS="unknown"
        PKG_MANAGER="unknown"
    fi
}

# Install a package via the detected package manager
install_pkg() {
    local pkg_apt="$1"
    local pkg_brew="${2:-$1}"
    local pkg_label="${3:-$1}"

    print_info "Installing $pkg_label..."
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        sudo apt-get update -qq > /dev/null 2>&1
        sudo apt-get install -y "$pkg_apt" >> "$LOG_FILE" 2>&1
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        brew install "$pkg_brew" >> "$LOG_FILE" 2>&1
    elif [[ "$PKG_MANAGER" == "dnf" || "$PKG_MANAGER" == "yum" ]]; then
        sudo "$PKG_MANAGER" install -y "$pkg_apt" >> "$LOG_FILE" 2>&1
    else
        print_error "Cannot install $pkg_label automatically — please install it manually then re-run."
        exit 1
    fi
    print_success "$pkg_label installed"
}

# ── Banner ────────────────────────────────────────────────────────────────────

print_header "WATERCODEFLOW EXTENSION — AUTOMATED SETUP"

echo -e "${BOLD}This script will:${RESET}"
echo "  1.  Check and install system dependencies"
echo "  2.  Fix hardcoded paths in watcher test files"
echo "  3.  Build C++ components"
echo "  4.  Copy libraries to their expected locations"
echo "  5.  Install Python dependencies"
echo "  6.  Install Node.js dependencies (inside editor/)"
echo "  7.  Compile TypeScript (inside editor/)"
echo "  8.  Package the extension as a .vsix file"
echo ""
echo -e "${YELLOW}This may take 5–10 minutes depending on your system.${RESET}"
echo ""

read -rp "Continue? (Y/n): " confirm
if [[ "$confirm" == "n" || "$confirm" == "N" ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Preflight: editor/ must exist with its package.json
if [ ! -f "$EDITOR_DIR/package.json" ]; then
    echo ""
    print_error "editor/package.json not found."
    print_info  "Place the watercodeflow editor directory at:"
    print_info  "  $EDITOR_DIR"
    print_info  "It must contain: src/, media/, package.json, tsconfig.json, glue/"
    exit 1
fi

detect_os
log "OS: $OS  PKG_MANAGER: $PKG_MANAGER  ROOT: $EXTENSION_ROOT"
print_info "Detected OS: $OS"
echo ""

# ============================================================================
# STEP 1: System dependencies
# ============================================================================

print_header "STEP 1: SYSTEM DEPENDENCIES"

# ── Python 3 ──
print_step "Checking Python 3..."
if check_command python3; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python 3 found: $PY_VERSION"
    log "Python3: $PY_VERSION"
else
    print_warning "Python 3 not found — installing..."
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        install_pkg "python3 python3-pip python3-dev" "" "Python 3"
    else
        install_pkg "python3" "python3" "Python 3"
    fi
fi

# Version gate: need 3.8+
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    print_error "Python $(python3 --version 2>&1 | awk '{print $2}') is too old — Python 3.8+ required."
    exit 1
fi

# ── pip ──
print_step "Checking pip..."
if python3 -m pip --version > /dev/null 2>&1; then
    print_success "pip available"
else
    print_warning "pip not found — installing..."
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        install_pkg "python3-pip" "" "pip"
    else
        python3 -m ensurepip --upgrade >> "$LOG_FILE" 2>&1
        print_success "pip installed"
    fi
fi

# ── Node.js ──
print_step "Checking Node.js..."
if check_command node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
    log "Node.js: $NODE_VERSION"
else
    print_warning "Node.js not found — installing..."
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        print_info "Fetching Node.js 20.x setup script..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - >> "$LOG_FILE" 2>&1
        install_pkg "nodejs" "" "Node.js 20"
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        install_pkg "" "node" "Node.js"
    else
        print_error "Cannot install Node.js automatically. Install from https://nodejs.org then re-run."
        exit 1
    fi
fi

# Node version gate: need 16+
NODE_MAJOR=$(node --version | tr -d 'v' | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 16 ]; then
    print_error "Node.js $(node --version) is too old — Node 16+ required."
    exit 1
fi

# ── npm ──
print_step "Checking npm..."
if check_command npm; then
    print_success "npm found: $(npm --version)"
else
    print_error "npm not found (should ship with Node.js). Check your installation."
    exit 1
fi

# ── C++ compiler ──
print_step "Checking C++ compiler..."
if check_command g++; then
    print_success "g++ found: $(g++ --version | head -1)"
    log "g++: $(g++ --version | head -1)"
elif check_command clang++; then
    print_success "clang++ found: $(clang++ --version | head -1)"
    log "clang++: $(clang++ --version | head -1)"
else
    print_warning "C++ compiler not found — installing..."
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        install_pkg "build-essential" "" "build-essential"
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        print_info "Installing Xcode Command Line Tools..."
        xcode-select --install >> "$LOG_FILE" 2>&1 || true
        print_success "Xcode tools installed"
    else
        print_error "Cannot install a C++ compiler automatically — please install one manually."
        exit 1
    fi
fi

# ── CMake ──
print_step "Checking CMake..."
if check_command cmake; then
    print_success "CMake found: $(cmake --version | head -1)"
    log "CMake: $(cmake --version | head -1)"
else
    print_warning "CMake not found — installing..."
    if [[ "$PKG_MANAGER" == "brew" ]]; then
        install_pkg "" "cmake" "CMake"
    else
        install_pkg "cmake" "cmake" "CMake"
    fi
fi

print_success "All system dependencies satisfied"

# ============================================================================
# STEP 2: Fix hardcoded paths in watcher test files
# ============================================================================

print_header "STEP 2: FIXING HARDCODED PATHS"

print_step "Scanning watcher test files for hardcoded /workspaces/WaterCodeFlow paths..."

python3 - "$EXTENSION_ROOT" << 'PYEOF'
import re, sys
from pathlib import Path

root = Path(sys.argv[1])
tests_dir = root / "watcher" / "tests"

fixed = []
skipped = []

if not tests_dir.exists():
    print(f"  watcher/tests/ not found — nothing to fix")
    sys.exit(0)

for py_file in sorted(tests_dir.glob("*.py")):
    content = py_file.read_text(encoding="utf-8")
    original = content

    HARDCODED = "/workspaces/WaterCodeFlow"

    # sys.path.insert(0, '/workspaces/WaterCodeFlow')
    content = re.sub(
        r"sys\.path\.insert\(0,\s*[\"']" + re.escape(HARDCODED) + r"[\"']\)",
        "sys.path.insert(0, str(Path(__file__).parent.parent.parent))",
        content,
    )

    # os.environ['LD_LIBRARY_PATH'] = '/workspaces/WaterCodeFlow/build:' + ...
    content = re.sub(
        r"os\.environ\[[\"']LD_LIBRARY_PATH[\"']\]\s*=\s*[\"']"
        + re.escape(HARDCODED)
        + r"/build:[\"']\s*\+\s*os\.environ\.get\([\"']LD_LIBRARY_PATH[\"'],\s*[\"'][\"']\)",
        "os.environ['LD_LIBRARY_PATH'] = str(Path(__file__).parent.parent.parent / 'build') + ':' + os.environ.get('LD_LIBRARY_PATH', '')",
        content,
    )

    # lib_path = Path('/workspaces/WaterCodeFlow/build/libwatcher_python.so')
    content = re.sub(
        r"lib_path\s*=\s*Path\([\"']" + re.escape(HARDCODED) + r"/build/libwatcher_python\.so[\"']\)",
        "lib_path = Path(__file__).parent.parent.parent / 'build' / 'libwatcher_python.so'",
        content,
    )

    if content != original:
        py_file.write_text(content, encoding="utf-8")
        fixed.append(py_file.name)
    else:
        skipped.append(py_file.name)

if fixed:
    for f in fixed:
        print(f"  \033[92m✓\033[0m Fixed: {f}")
else:
    print("  All test files already have portable paths — nothing to change")
PYEOF

print_success "Path check complete"

# ============================================================================
# STEP 3: Build C++ components
# ============================================================================

print_header "STEP 3: BUILDING C++ COMPONENTS"

if [ ! -f "$EXTENSION_ROOT/CMakeLists.txt" ]; then
    print_error "CMakeLists.txt not found in extension root ($EXTENSION_ROOT)"
    print_info  "Expected components:"
    print_info  "  storage_utility/faststorage.c"
    print_info  "  watcher/core/src/watcher_core.cpp"
    print_info  "  watcher/adapters/python/adapter.cpp"
    print_info  "  watcher/processor/processor.cpp"
    exit 1
fi
print_success "CMakeLists.txt found"

print_step "Creating build directory..."
mkdir -p "$EXTENSION_ROOT/build"

print_step "Running CMake configuration..."
cd "$EXTENSION_ROOT/build"
log "cmake $EXTENSION_ROOT -DCMAKE_BUILD_TYPE=Release"
if cmake "$EXTENSION_ROOT" -DCMAKE_BUILD_TYPE=Release >> "$LOG_FILE" 2>&1; then
    print_success "CMake configured"
else
    print_error "CMake configuration failed — see $LOG_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi

print_step "Compiling..."
NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)
log "make -j$NPROC"
if make -j"$NPROC" >> "$LOG_FILE" 2>&1; then
    print_success "Compilation succeeded ($NPROC parallel jobs)"
else
    print_error "Compilation failed — see $LOG_FILE"
    tail -30 "$LOG_FILE"
    exit 1
fi

cd "$EXTENSION_ROOT"

echo ""
print_info "Libraries in build/:"
for lib in build/*.so build/*.dylib; do
    [ -f "$lib" ] && echo -e "  ${GREEN}✓${RESET} $(basename "$lib")  ($(du -h "$lib" | cut -f1))"
done

# ============================================================================
# STEP 4: Copy libraries to expected locations
# ============================================================================

print_header "STEP 4: PLACING LIBRARIES"

# faststorage_c.so → storage_utility/  (used by CodeVovle and glue)
print_step "Placing faststorage_c.so..."
if [ -f "build/faststorage_c.so" ]; then
    cp "build/faststorage_c.so" "storage_utility/"
    print_success "faststorage_c.so → storage_utility/"
    # Also into watcher/storage_utility/ if it exists
    if [ -d "watcher/storage_utility" ]; then
        cp "build/faststorage_c.so" "watcher/storage_utility/"
        print_success "faststorage_c.so → watcher/storage_utility/"
    fi
elif [ -f "storage_utility/faststorage_c.so" ]; then
    print_success "faststorage_c.so already in storage_utility/"
else
    print_error "faststorage_c.so not found in build/ or storage_utility/"
    exit 1
fi

# Watcher shared libraries — must live in build/ (extension.ts resolves them there)
print_step "Verifying watcher libraries..."
MISSING=0
for lib in libwatcher_python.so libwatcher_core.so libwatcher_processor.so; do
    if [ -f "build/$lib" ]; then
        print_success "$lib  ($(du -h "build/$lib" | cut -f1))"
    else
        print_error "build/$lib not found"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -gt 0 ]; then
    print_error "$MISSING critical librar$([ $MISSING -eq 1 ] && echo y || echo ies) missing — check $LOG_FILE"
    exit 1
fi

# ============================================================================
# STEP 5: Python dependencies
# ============================================================================

print_header "STEP 5: PYTHON DEPENDENCIES"

print_step "Upgrading pip..."
python3 -m pip install --upgrade pip >> "$LOG_FILE" 2>&1
print_success "pip up to date"

# CodeVovle requirements
print_step "Installing CodeVovle requirements..."
if [ -f "$EXTENSION_ROOT/CodeVovle/requirements.txt" ]; then
    python3 -m pip install -r "$EXTENSION_ROOT/CodeVovle/requirements.txt" >> "$LOG_FILE" 2>&1
    print_success "CodeVovle/requirements.txt installed"
else
    print_warning "CodeVovle/requirements.txt not found — skipping"
fi

# Common test + runtime deps
print_step "Installing shared Python packages..."
python3 -m pip install pytest psutil >> "$LOG_FILE" 2>&1
print_success "pytest, psutil installed"

# Verify the glue package loads cleanly
print_step "Verifying glue package..."
if python3 - << PYCHECK >> "$LOG_FILE" 2>&1
import sys
sys.path.insert(0, '$EXTENSION_ROOT')
from glue import api, runs, variables, watch
from glue.errors import GlueError
print("glue ok")
PYCHECK
then
    print_success "glue package imports cleanly"
else
    print_warning "glue import had warnings — see $LOG_FILE (non-fatal, CodeVovle not yet installed)"
fi

# ============================================================================
# STEP 6: Node.js dependencies
# ============================================================================

print_header "STEP 6: NODE.JS DEPENDENCIES"

print_step "Running npm install in editor/..."
cd "$EDITOR_DIR"
if npm install >> "$LOG_FILE" 2>&1; then
    PKGS=$(ls node_modules | wc -l | tr -d ' ')
    print_success "node_modules installed ($PKGS packages)"
else
    print_error "npm install failed — see $LOG_FILE"
    exit 1
fi
cd "$EXTENSION_ROOT"

# ============================================================================
# STEP 7: Compile TypeScript
# ============================================================================

print_header "STEP 7: COMPILING TYPESCRIPT"

print_step "Building editor/src → editor/out..."
cd "$EDITOR_DIR"
if npm run esbuild >> "$LOG_FILE" 2>&1; then
    print_success "TypeScript compiled → editor/out/"
else
    print_error "TypeScript compilation failed — see $LOG_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi
cd "$EXTENSION_ROOT"

# Verify key output files
print_step "Verifying compiled output..."
OK=0
for f in out/extension.js out/GlueBridge.js out/utils.js \
          out/panels/RecordingsPanel.js out/panels/SettingsPanel.js \
          out/panels/RunInspectorPanel.js out/panels/VariableInspectorPanel.js \
          out/providers/RecordingViewerProvider.js; do
    if [ -f "$EDITOR_DIR/$f" ]; then
        OK=$((OK + 1))
    else
        print_warning "editor/$f missing after compilation"
    fi
done
print_success "$OK compiled output files verified"

# ============================================================================
# STEP 8: Package extension
# ============================================================================

print_header "STEP 8: PACKAGING EXTENSION"

cd "$EDITOR_DIR"

print_step "Checking for vsce..."
if check_command vsce; then
    print_success "vsce found: $(vsce --version 2>/dev/null)"
else
    print_info "Installing @vscode/vsce globally..."
    npm install -g @vscode/vsce >> "$LOG_FILE" 2>&1
    if check_command vsce; then
        print_success "vsce installed: $(vsce --version 2>/dev/null)"
    else
        print_error "vsce installation failed — see $LOG_FILE"
        exit 1
    fi
fi

print_step "Packaging as .vsix..."
if vsce package \
    --allow-missing-repository \
    --no-dependencies \
    --allow-star-activation \
    --allow-missing-repository \
    --allow-package-env-file \
    >> "$LOG_FILE" 2>&1; then
    print_success "Extension packaged"
else
    print_error "vsce package failed — see $LOG_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi

VSIX_FILE=$(ls -t "$EDITOR_DIR"/*.vsix 2>/dev/null | head -1)
if [ -z "$VSIX_FILE" ]; then
    print_error "No .vsix file found after packaging"
    exit 1
fi

VSIX_SIZE=$(du -h "$VSIX_FILE" | cut -f1)
print_success "Created: $(basename "$VSIX_FILE")  ($VSIX_SIZE)"

cd "$EXTENSION_ROOT"

# ============================================================================
# Done
# ============================================================================

print_header "SETUP COMPLETE!"

echo -e "${BOLD}${GREEN}✓ All 8 steps completed successfully!${RESET}\n"

echo -e "${BOLD}📦 Extension package:${RESET}"
echo -e "   ${CYAN}$VSIX_FILE${RESET}"
echo ""

echo -e "${BOLD}📥 Install in VS Code:${RESET}"
echo -e "   ${YELLOW}Method 1 — Command line:${RESET}"
echo -e "     code --install-extension \"$VSIX_FILE\""
echo ""
echo -e "   ${YELLOW}Method 2 — VS Code UI:${RESET}"
echo "     Extensions (Ctrl+Shift+X) → ⋯ → Install from VSIX…"
echo "     Select: $VSIX_FILE"
echo ""

echo -e "${BOLD}📚 Quick start:${RESET}"
echo "   1. Open a Python file in VS Code"
echo "   2. Click the WaterCodeFlow icon in the Activity Bar"
echo "   3. Press ▶ to run and start recording"
echo "   4. Inspect variables with the 👁 watcher button"
echo ""

echo -e "${BOLD}📄 Docs:${RESET}"
echo "   • README.md          — project overview"
echo "   • QUICK_REFERENCE.md — quick-start commands"
echo ""

echo -e "${YELLOW}Setup log: $LOG_FILE${RESET}"
echo ""
echo -e "${BOLD}${GREEN}🎉 You're ready to go!${RESET}\n"