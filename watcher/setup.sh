#!/bin/bash
# ============================================================================
# WATCHER FRAMEWORK SETUP SCRIPT
# ============================================================================
# 
# This script sets up the entire Watcher framework environment:
# - Checks system dependencies
# - Installs missing tools
# - Builds C++ components
# - Sets up Python environment
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

BOLD='\033[1m'
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
RESET='\033[0m'

echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║          WATCHER FRAMEWORK SETUP                              ║${RESET}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════════╝${RESET}\n"

# ============================================================================
# Helper Functions
# ============================================================================

check_command() {
    local cmd=$1
    local package=$2
    
    if command -v "$cmd" &> /dev/null; then
        local version=$($cmd --version 2>&1 | head -1)
        echo -e "${GREEN}✅${RESET} $cmd installed: $version"
        return 0
    else
        echo -e "${YELLOW}⚠️${RESET} $cmd not found (package: $package)"
        return 1
    fi
}

install_apt() {
    local package=$1
    echo -e "${YELLOW}Installing ${BOLD}$package${RESET}..."
    sudo apt-get update > /dev/null 2>&1 || true
    sudo apt-get install -y "$package" > /dev/null 2>&1
    echo -e "${GREEN}✅${RESET} $package installed"
}

install_pip() {
    local package=$1
    echo -e "${YELLOW}Installing ${BOLD}$package${RESET} via pip..."
    pip3 install "$package" > /dev/null 2>&1
    echo -e "${GREEN}✅${RESET} $package installed"
}

# ============================================================================
# Step 1: System Dependencies
# ============================================================================

echo -e "${BOLD}Step 1: Checking System Dependencies${RESET}\n"

# C++ Compiler
if ! check_command "g++" "build-essential"; then
    install_apt "build-essential"
    check_command "g++" "build-essential"
fi

# CMake
if ! check_command "cmake" "cmake"; then
    install_apt "cmake"
    check_command "cmake" "cmake"
fi

# Python 3
if ! check_command "python3" "python3"; then
    install_apt "python3"
    check_command "python3" "python3"
fi

# # Git
# if ! check_command "git" "git"; then
#     install_apt "git"
#     check_command "git" "git"
# fi

# Node.js (optional but recommended)
if ! check_command "node" "nodejs"; then
    echo -e "${YELLOW}⚠️${RESET} Node.js not found - JavaScript support won't work"
    echo -e "${YELLOW}Install with: sudo apt-get install nodejs npm${RESET}"
else
    node_version=$(node --version)
    echo -e "${GREEN}✅${RESET} Node.js $node_version"
fi

# ============================================================================
# Step 2: Python Dependencies
# ============================================================================

echo -e "\n${BOLD}Step 2: Checking Python Dependencies${RESET}\n"

# Check pip
if ! python3 -m pip --version > /dev/null 2>&1; then
    echo -e "${YELLOW}Installing pip...${RESET}"
    install_apt "python3-pip"
fi

# Required Python packages
PYTHON_PACKAGES=(
    "ctypes"  # Usually built-in
    "pickle"  # Usually built-in
)

for pkg in "${PYTHON_PACKAGES[@]}"; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo -e "${GREEN}✅${RESET} Python module '$pkg' available"
    else
        echo -e "${YELLOW}⚠️${RESET} Python module '$pkg' not found"
    fi
done

# ============================================================================
# Step 3: Create Build Directory
# ============================================================================

echo -e "\n${BOLD}Step 3: Setting Up Build System${RESET}\n"

if [ ! -d "build" ]; then
    echo -e "${YELLOW}Creating build directory...${RESET}"
    mkdir -p build
    echo -e "${GREEN}✅${RESET} Build directory created"
else
    echo -e "${GREEN}✅${RESET} Build directory exists"
fi

# ============================================================================
# Step 4: CMake Configuration
# ============================================================================

echo -e "\n${BOLD}Step 4: Configuring CMake${RESET}\n"

cd build

if [ ! -f "CMakeCache.txt" ]; then
    echo -e "${YELLOW}Running CMake...${RESET}"
    cmake .. -DCMAKE_BUILD_TYPE=Release > /dev/null 2>&1
    echo -e "${GREEN}✅${RESET} CMake configured"
else
    echo -e "${GREEN}✅${RESET} CMake already configured"
fi

# ============================================================================
# Step 5: Build
# ============================================================================

echo -e "\n${BOLD}Step 5: Building Watcher Framework${RESET}\n"

echo -e "${YELLOW}Compiling C++ components...${RESET}"
if make -j$(nproc) > /dev/null 2>&1; then
    echo -e "${GREEN}✅${RESET} Build successful"
    
    # List built libraries
    echo -e "\n${BOLD}Built libraries:${RESET}"
    for lib in *.so; do
        [ -f "$lib" ] && echo -e "  ${GREEN}✅${RESET} $lib ($(du -h "$lib" | cut -f1))"
    done
else
    echo -e "${RED}❌${RESET} Build failed"
    echo -e "${YELLOW}Run ${BOLD}cd build && make${RESET} for details"
    exit 1
fi

cd "$PROJECT_ROOT"

# ============================================================================
# Step 6: Verify Installation
# ============================================================================

echo -e "\n${BOLD}Step 6: Verifying Installation${RESET}\n"

CHECKS_PASSED=0
CHECKS_TOTAL=0

# Check libraries exist
for lib in libwatcher_core.so libwatcher_python.so libwatcher_processor.so; do
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if [ -f "build/$lib" ]; then
        echo -e "${GREEN}✅${RESET} $lib exists"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${RED}❌${RESET} $lib missing"
    fi
done

# Check Python adapter
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ -f "watcher/adapters/python/__init__.py" ]; then
    echo -e "${GREEN}✅${RESET} Python adapter exists"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}❌${RESET} Python adapter missing"
fi

# Check tests
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ -f "watcher/tests/test_real.py" ]; then
    echo -e "${GREEN}✅${RESET} Test suite exists"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}❌${RESET} Test suite missing"
fi

# ============================================================================
# Final Summary
# ============================================================================

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║              SETUP COMPLETE!${RESET}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════════╝${RESET}\n"

echo -e "${BOLD}Verification: $CHECKS_PASSED/$CHECKS_TOTAL checks passed${RESET}"

if [ $CHECKS_PASSED -eq $CHECKS_TOTAL ]; then
    echo -e "\n${GREEN}✅ All components ready!${RESET}\n"
    echo -e "${BOLD}Next steps:${RESET}"
    echo -e "  1. Run tests:   ${BOLD}python3 watcher/tests/test_real.py${RESET}"
    echo -e "  2. Clean build: ${BOLD}./cleanup.sh${RESET}"
    echo -e "  3. Rebuild:     ${BOLD}./setup.sh${RESET}\n"
    exit 0
else
    echo -e "\n${RED}❌ Some checks failed${RESET}"
    echo -e "Review errors above and run ${BOLD}./setup.sh${RESET} again\n"
    exit 1
fi
