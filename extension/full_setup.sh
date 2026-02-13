#!/bin/bash
# ============================================================================
# WATERCODEFLOW EXTENSION - COMPLETE AUTOMATED SETUP
# ============================================================================
# This script does EVERYTHING to set up the extension:
# 1. Checks and installs system dependencies
# 2. Fixes all hardcoded paths automatically
# 3. Builds C++ components
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
        sudo apt-get install -y python3 python3-pip >> "$LOG_FILE" 2>&1
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

# Fix setup.sh
if [ -f "setup.sh" ]; then
    print_info "Fixing setup.sh..."
    sed -i.bak 's|PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE\[0\]}")/\.\./\.\." && pwd)"|PROJECT_ROOT="$(cd "$(dirname \"${BASH_SOURCE[0]}\")\" \&\& pwd)"|g' setup.sh
    print_success "Fixed setup.sh"
fi

# Fix tests/test_real_mutations.py
if [ -f "tests/test_real_mutations.py" ]; then
    print_info "Fixing tests/test_real_mutations.py..."
    sed -i.bak "20s|sys.path.insert(0, '/workspaces/WaterCodeFlow')|# Get the extension root directory\nEXTENSION_ROOT = Path(__file__).parent.parent\nsys.path.insert(0, str(EXTENSION_ROOT))|" tests/test_real_mutations.py
    sed -i.bak "27s|lib_path = Path('/workspaces/WaterCodeFlow/build/libwatcher_python.so')|lib_path = EXTENSION_ROOT / 'build' / 'libwatcher_python.so'|" tests/test_real_mutations.py
    print_success "Fixed tests/test_real_mutations.py"
fi

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
    "tests/test_functionality.py"
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
        """# Get the extension root directory (2 levels up from tests/)
EXTENSION_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(EXTENSION_ROOT))""",
        content
    )
    
    content = re.sub(
        r"os\.environ\['LD_LIBRARY_PATH'\] = '/workspaces/WaterCodeFlow/build:' \+ os\.environ\.get\('LD_LIBRARY_PATH', ''\)",
        "os.environ['LD_LIBRARY_PATH'] = str(EXTENSION_ROOT / 'build') + ':' + os.environ.get('LD_LIBRARY_PATH', '')",
        content
    )
    
    with open(full_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed: {file_path}")

# Fix test_recursive_branching.py
recursive_test = extension_root / "test_recursive_branching.py"
if recursive_test.exists():
    with open(recursive_test, 'r') as f:
        content = f.read()
    
    content = re.sub(
        r'sys\.path\.insert\(0, "/workspaces/WaterCodeFlow/CodeVovle"\)',
        """# Get the extension root directory
EXTENSION_ROOT = Path(__file__).parent
sys.path.insert(0, str(EXTENSION_ROOT / 'codevovle'))""",
        content
    )
    
    with open(recursive_test, 'w') as f:
        f.write(content)
    
    print(f"Fixed: test_recursive_branching.py")

print("All hardcoded paths fixed!")
PYEOF

python3 /tmp/fix_paths.py
print_success "All hardcoded paths fixed!"
rm /tmp/fix_paths.py

# ============================================================================
# Step 3: Build C++ Components
# ============================================================================

print_header "STEP 3: BUILDING C++ COMPONENTS"

print_step "Creating build directory..."
mkdir -p build
cd build

print_step "Running CMake configuration..."
cmake .. -DCMAKE_BUILD_TYPE=Release >> "$LOG_FILE" 2>&1
print_success "CMake configured"

print_step "Compiling C++ libraries..."
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2) >> "$LOG_FILE" 2>&1
print_success "C++ libraries compiled"

# List built libraries
print_info "Built libraries:"
for lib in *.so *.dylib 2>/dev/null; do
    if [ -f "$lib" ]; then
        SIZE=$(du -h "$lib" | cut -f1)
        echo "  ${GREEN}✓${RESET} $lib ($SIZE)"
    fi
done

cd "$EXTENSION_ROOT"

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
echo "  • HOW_TO_USE_EXTENSION.md - Complete usage guide"
echo "  • HARDCODED_PATHS_TO_FIX.md - Technical details on path fixes"
echo "  • QUICK_START.md - Quick reference"
echo ""

echo -e "${YELLOW}Setup log saved to: $LOG_FILE${RESET}"
echo ""

echo -e "${BOLD}${GREEN}🎉 You're ready to go! Install the extension and start debugging!${RESET}\n"