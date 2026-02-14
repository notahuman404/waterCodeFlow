#!/bin/bash
# ============================================================================
# WATERCODEFLOW EXTENSION - COMPLETE AUTOMATED SETUP (FIXED)
# ============================================================================
# This script does EVERYTHING to set up the extension:
# 1. Checks and installs system dependencies
# 2. Fixes all hardcoded paths automatically
# 3. Builds C++ components (FIXED: now uses root CMakeLists.txt)
# 4. Installs Python dependencies
# 5. Installs Node.js dependencies
# 6. Compiles TypeScript
# 7. Packages extension as .vsix file
# 8. Provides installation instructions
# ============================================================================

set -e  # Exit on any error

# Colors for output
BOLD='\033[1m'
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BLUE='\033[94m'
CYAN='\033[96m'
RESET='\033[0m'

# Get the directory where this script is located (extension root)
EXTENSION_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$EXTENSION_ROOT"

# Log file
LOG_FILE="$EXTENSION_ROOT/setup.log"
echo "Setup started at $(date)" > "$LOG_FILE"

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "\n${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${CYAN}║  $1${RESET}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${RESET}\n"
}

print_step() {
    echo -e "${BOLD}${BLUE}▶ $1${RESET}"
}

print_success() {
    echo -e "${GREEN}✓ $1${RESET}"
}

print_error() {
    echo -e "${RED}✗ $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${RESET}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${RESET}"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_command() {
    local cmd=$1
    if command -v "$cmd" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if command -v apt-get &> /dev/null; then
            PKG_MANAGER="apt"
        elif command -v yum &> /dev/null; then
            PKG_MANAGER="yum"
        elif command -v dnf &> /dev/null; then
            PKG_MANAGER="dnf"
        else
            PKG_MANAGER="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="mac"
        PKG_MANAGER="brew"
    else
        OS="unknown"
        PKG_MANAGER="unknown"
    fi
}

# ============================================================================
# Main Setup Process
# ============================================================================

print_header "WATERCODEFLOW EXTENSION - AUTOMATED SETUP"

echo -e "${BOLD}This script will:${RESET}"
echo "  1. Check and install system dependencies"
echo "  2. Fix all hardcoded paths in the code"
echo "  3. Build C++ components"
echo "  4. Install Python dependencies"
echo "  5. Install Node.js dependencies"
echo "  6. Compile TypeScript code"
echo "  7. Package the extension as .vsix file"
echo ""
echo -e "${YELLOW}This may take 5-10 minutes depending on your system.${RESET}"
echo ""
read -p "Continue? (Y/n): " confirm
if [[ "$confirm" == "n" || "$confirm" == "N" ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Detect OS
detect_os
log "Detected OS: $OS, Package Manager: $PKG_MANAGER"
print_info "Detected OS: $OS"

# ============================================================================
# Step 1: Check and Install System Dependencies
# ============================================================================

print_header "STEP 1: SYSTEM DEPENDENCIES"

# Check Python 3
print_step "Checking Python 3..."
if check_command python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python 3 installed: $PYTHON_VERSION"
    log "Python3 found: $PYTHON_VERSION"
else
    print_error "Python 3 not found"
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        print_info "Installing Python 3..."
        sudo apt-get update > /dev/null 2>&1
        sudo apt-get install -y python3 python3-pip python3-dev >> "$LOG_FILE" 2>&1
        print_success "Python 3 installed"
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        print_info "Installing Python 3..."
        brew install python3 >> "$LOG_FILE" 2>&1
        print_success "Python 3 installed"
    else
        print_error "Cannot install Python 3 automatically. Please install manually."
        exit 1
    fi
fi

# Check pip
print_step "Checking pip..."
if python3 -m pip --version > /dev/null 2>&1; then
    print_success "pip installed"
else
    print_info "Installing pip..."
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        sudo apt-get install -y python3-pip >> "$LOG_FILE" 2>&1
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        python3 -m ensurepip >> "$LOG_FILE" 2>&1
    fi
    print_success "pip installed"
fi

# Check Node.js
print_step "Checking Node.js..."
if check_command node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js installed: $NODE_VERSION"
    log "Node.js found: $NODE_VERSION"
else
    print_error "Node.js not found"
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        print_info "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - >> "$LOG_FILE" 2>&1
        sudo apt-get install -y nodejs >> "$LOG_FILE" 2>&1
        print_success "Node.js installed"
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        print_info "Installing Node.js..."
        brew install node >> "$LOG_FILE" 2>&1
        print_success "Node.js installed"
    else
        print_error "Cannot install Node.js automatically. Please install from https://nodejs.org"
        exit 1
    fi
fi

# Check npm
print_step "Checking npm..."
if check_command npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm installed: $NPM_VERSION"
else
    print_error "npm not found (should come with Node.js)"
    exit 1
fi

# Check C++ compiler
print_step "Checking C++ compiler..."
if check_command g++ || check_command clang++; then
    if check_command g++; then
        CXX_VERSION=$(g++ --version | head -1)
        print_success "g++ installed: $CXX_VERSION"
    else
        CXX_VERSION=$(clang++ --version | head -1)
        print_success "clang++ installed: $CXX_VERSION"
    fi
else
    print_error "C++ compiler not found"
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        print_info "Installing build-essential..."
        sudo apt-get install -y build-essential >> "$LOG_FILE" 2>&1
        print_success "build-essential installed"
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        print_info "Installing Xcode Command Line Tools..."
        xcode-select --install >> "$LOG_FILE" 2>&1 || true
        print_success "Xcode tools installed"
    else
        print_error "Cannot install C++ compiler automatically. Please install manually."
        exit 1
    fi
fi

# Check CMake
print_step "Checking CMake..."
if check_command cmake; then
    CMAKE_VERSION=$(cmake --version | head -1)
    print_success "CMake installed: $CMAKE_VERSION"
else
    print_error "CMake not found"
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        print_info "Installing CMake..."
        sudo apt-get install -y cmake >> "$LOG_FILE" 2>&1
        print_success "CMake installed"
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        print_info "Installing CMake..."
        brew install cmake >> "$LOG_FILE" 2>&1
        print_success "CMake installed"
    else
        print_error "Cannot install CMake automatically. Please install from https://cmake.org"
        exit 1
    fi
fi

# ============================================================================
# Step 2: Fix Hardcoded Paths
# ============================================================================

print_header "STEP 2: FIXING HARDCODED PATHS"

print_step "Fixing hardcoded paths in test files..."

# Create a Python script to fix all test files at once
cat > /tmp/fix_paths.py << 'PYEOF'
#!/usr/bin/env python3
import re
from pathlib import Path

# Files to fix
files_to_fix = [
    "tests/test_mutations.py",
    "tests/test_javascript_loader.py",
    "tests/test_javascript_processor.py",
    "tests/test_functionality.py",
    "tests/test_real_mutations.py"
]

extension_root = Path.cwd()

for file_path in files_to_fix:
    full_path = extension_root / file_path
    if not full_path.exists():
        continue
    
    with open(full_path, 'r') as f:
        content = f.read()
    
    # Replace the hardcoded paths
    content = re.sub(
        r"sys\.path\.insert\(0, '/workspaces/WaterCodeFlow'\)",
        """# Get the extension root directory
EXTENSION_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(EXTENSION_ROOT))""",
        content
    )
    
    content = re.sub(
        r"os\.environ\['LD_LIBRARY_PATH'\] = '/workspaces/WaterCodeFlow/build:' \+ os\.environ\.get\('LD_LIBRARY_PATH', ''\)",
        "os.environ['LD_LIBRARY_PATH'] = str(EXTENSION_ROOT / 'build') + ':' + os.environ.get('LD_LIBRARY_PATH', '')",
        content
    )
    
    content = re.sub(
        r"lib_path = Path\('/workspaces/WaterCodeFlow/build/libwatcher_python\.so'\)",
        "lib_path = EXTENSION_ROOT / 'build' / 'libwatcher_python.so'",
        content
    )
    
    with open(full_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed: {file_path}")

print("All hardcoded paths fixed!")
PYEOF

python3 /tmp/fix_paths.py
print_success "All hardcoded paths fixed!"
rm /tmp/fix_paths.py

# ============================================================================
# Step 3: Build C++ Components (FIXED)
# ============================================================================

print_header "STEP 3: BUILDING C++ COMPONENTS"

print_step "Checking for CMakeLists.txt in extension root..."
if [ ! -f "$EXTENSION_ROOT/CMakeLists.txt" ]; then
    print_error "CMakeLists.txt not found in extension root!"
    print_error "Please place the CMakeLists.txt file in: $EXTENSION_ROOT"
    print_info "The CMakeLists.txt should build all components:"
    print_info "  - storage_utility/faststorage.c"
    print_info "  - watcher/core/src/watcher_core.cpp"
    print_info "  - watcher/adapters/python/adapter.cpp"
    print_info "  - watcher/processor/processor.cpp"
    exit 1
else
    print_success "Found CMakeLists.txt in extension root"
fi

print_step "Creating build directory..."
mkdir -p "$EXTENSION_ROOT/build"
cd "$EXTENSION_ROOT/build"

print_step "Running CMake configuration..."
log "Running: cmake $EXTENSION_ROOT -DCMAKE_BUILD_TYPE=Release"
if cmake "$EXTENSION_ROOT" -DCMAKE_BUILD_TYPE=Release >> "$LOG_FILE" 2>&1; then
    print_success "CMake configured successfully"
else
    print_error "CMake configuration failed!"
    print_error "Check $LOG_FILE for details"
    tail -n 20 "$LOG_FILE"
    exit 1
fi

print_step "Compiling C/C++ libraries..."
NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)
log "Running: make -j$NPROC"
if make -j$NPROC >> "$LOG_FILE" 2>&1; then
    print_success "C/C++ libraries compiled successfully"
else
    print_error "Compilation failed!"
    print_error "Check $LOG_FILE for details"
    tail -n 30 "$LOG_FILE"
    exit 1
fi

# Libraries are auto-copied during build via POST_BUILD commands
# No need for 'make install'
print_info "Libraries auto-copied during build (via CMake POST_BUILD commands)"

# List built libraries
print_info "Built libraries in $EXTENSION_ROOT/build:"
cd "$EXTENSION_ROOT/build"
for lib in *.so *.dylib 2>/dev/null; do
    if [ -f "$lib" ]; then
        SIZE=$(du -h "$lib" | cut -f1)
        echo "  ${GREEN}✓${RESET} $lib ($SIZE)"
    fi
done

cd "$EXTENSION_ROOT"

# Verify critical libraries exist
print_step "Verifying critical libraries..."
MISSING_LIBS=0

if [ -f "$EXTENSION_ROOT/storage_utility/faststorage_c.so" ]; then
    print_success "faststorage_c.so found in storage_utility/"
else
    print_warning "faststorage_c.so not found in storage_utility/ (will look in build/)"
    if [ -f "$EXTENSION_ROOT/build/faststorage_c.so" ]; then
        print_info "Copying from build/ to storage_utility/"
        cp "$EXTENSION_ROOT/build/faststorage_c.so" "$EXTENSION_ROOT/storage_utility/"
        print_success "Copied faststorage_c.so"
    else
        print_error "faststorage_c.so not found anywhere!"
        MISSING_LIBS=1
    fi
fi

if [ -f "$EXTENSION_ROOT/build/libwatcher_python.so" ]; then
    print_success "libwatcher_python.so found in build/"
else
    print_error "libwatcher_python.so not found in build/!"
    MISSING_LIBS=1
fi

if [ $MISSING_LIBS -eq 1 ]; then
    print_error "Some critical libraries are missing!"
    print_error "Build may have failed. Check $LOG_FILE"
    exit 1
fi

# ============================================================================
# Step 4: Install Python Dependencies
# ============================================================================

print_header "STEP 4: PYTHON DEPENDENCIES"

print_step "Installing Python packages..."
python3 -m pip install --upgrade pip >> "$LOG_FILE" 2>&1
python3 -m pip install pytest psutil >> "$LOG_FILE" 2>&1
print_success "Python packages installed (pytest, psutil)"

# ============================================================================
# Step 5: Install Node.js Dependencies
# ============================================================================

print_header "STEP 5: NODE.JS DEPENDENCIES"

print_step "Installing npm packages..."
npm install >> "$LOG_FILE" 2>&1
print_success "npm packages installed"

# ============================================================================
# Step 6: Compile TypeScript
# ============================================================================

print_header "STEP 6: COMPILING TYPESCRIPT"

print_step "Building TypeScript code..."
npm run esbuild >> "$LOG_FILE" 2>&1
print_success "TypeScript compiled to out/extension.js"

# ============================================================================
# Step 7: Package Extension
# ============================================================================

print_header "STEP 7: PACKAGING EXTENSION"

print_step "Installing vsce (VS Code Extension Manager)..."
npm install -g @vscode/vsce >> "$LOG_FILE" 2>&1
print_success "vsce installed"

print_step "Packaging extension as .vsix file..."
vsce package --allow-star-activation >> "$LOG_FILE" 2>&1
print_success "Extension packaged!"

# Find the .vsix file
VSIX_FILE=$(ls -t *.vsix 2>/dev/null | head -1)

if [ -n "$VSIX_FILE" ]; then
    VSIX_SIZE=$(du -h "$VSIX_FILE" | cut -f1)
    print_success "Created: $VSIX_FILE ($VSIX_SIZE)"
else
    print_error "Could not find .vsix file"
    exit 1
fi

# ============================================================================
# Final Success Message
# ============================================================================

print_header "SETUP COMPLETE!"

echo -e "${BOLD}${GREEN}✓ All steps completed successfully!${RESET}\n"

echo -e "${BOLD}📦 Extension Package:${RESET}"
echo -e "  ${CYAN}$VSIX_FILE${RESET}"
echo ""

echo -e "${BOLD}📥 To Install in VS Code:${RESET}"
echo -e "  ${YELLOW}Method 1 - VS Code UI:${RESET}"
echo "    1. Open VS Code"
echo "    2. Go to Extensions (Ctrl+Shift+X or Cmd+Shift+X)"
echo "    3. Click '...' menu → 'Install from VSIX...'"
echo "    4. Select: $EXTENSION_ROOT/$VSIX_FILE"
echo ""
echo -e "  ${YELLOW}Method 2 - Command Line:${RESET}"
echo "    code --install-extension $VSIX_FILE"
echo ""

echo -e "${BOLD}📚 Quick Start:${RESET}"
echo "  1. Install the extension using one of the methods above"
echo "  2. Open a Python file in VS Code"
echo "  3. Click the WaterCodeFlow icon in the Activity Bar"
echo "  4. Start recording and debug with time-travel!"
echo ""

echo -e "${BOLD}📄 Documentation:${RESET}"
echo "  • README.md - Project overview"
echo "  • QUICK_REFERENCE.md - Quick start guide"
echo ""

echo -e "${YELLOW}Setup log saved to: $LOG_FILE${RESET}"
echo ""

echo -e "${BOLD}${GREEN}🎉 You're ready to go! Install the extension and start debugging!${RESET}\n"