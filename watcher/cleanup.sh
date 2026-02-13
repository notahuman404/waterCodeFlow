#!/bin/bash
# ============================================================================
# WATCHER FRAMEWORK CLEANUP SCRIPT
# ============================================================================
#
# This script removes all build artifacts and temporary files:
# - Deletes build directory
# - Removes compiled libraries
# - Cleans cmake cache
# - Removes compiled test binaries
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

BOLD='\033[1m'
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
RESET='\033[0m'

echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║          WATCHER FRAMEWORK CLEANUP                             ║${RESET}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════════╝${RESET}\n"

ITEMS_DELETED=0

# ============================================================================
# Remove Build Directory
# ============================================================================

echo -e "${BOLD}Removing build artifacts...${RESET}\n"

if [ -d "build" ]; then
    echo -e "${YELLOW}Deleting${RESET} build/ directory..."
    rm -rf build
    echo -e "${GREEN}✅${RESET} build/ deleted"
    ITEMS_DELETED=$((ITEMS_DELETED + 1))
else
    echo -e "${YELLOW}⚠️${RESET} build/ directory not found"
fi

# ============================================================================
# Remove CMake Cache Files
# ============================================================================

echo -e "\n${BOLD}Removing CMake files...${RESET}\n"

if [ -f "CMakeCache.txt" ]; then
    rm -f CMakeCache.txt
    echo -e "${GREEN}✅${RESET} CMakeCache.txt deleted"
    ITEMS_DELETED=$((ITEMS_DELETED + 1))
fi

if [ -d "CMakeFiles" ]; then
    rm -rf CMakeFiles
    echo -e "${GREEN}✅${RESET} CMakeFiles/ deleted"
    ITEMS_DELETED=$((ITEMS_DELETED + 1))
fi

if [ -f "cmake_install.cmake" ]; then
    rm -f cmake_install.cmake
    echo -e "${GREEN}✅${RESET} cmake_install.cmake deleted"
    ITEMS_DELETED=$((ITEMS_DELETED + 1))
fi

if [ -f "Makefile" ]; then
    rm -f Makefile
    echo -e "${GREEN}✅${RESET} Makefile deleted"
    ITEMS_DELETED=$((ITEMS_DELETED + 1))
fi

# ============================================================================
# Remove Python Cache
# ============================================================================

echo -e "\n${BOLD}Removing Python cache...${RESET}\n"

PYCACHE_DIRS=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
if [ $PYCACHE_DIRS -gt 0 ]; then
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}✅${RESET} Removed $PYCACHE_DIRS __pycache__ directories"
    ITEMS_DELETED=$((ITEMS_DELETED + PYCACHE_DIRS))
fi

PYFILES=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l)
if [ $PYFILES -gt 0 ]; then
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo -e "${GREEN}✅${RESET} Removed $PYFILES .pyc files"
    ITEMS_DELETED=$((ITEMS_DELETED + PYFILES))
fi

EGGINFO=$(find . -type d -name "*.egg-info" 2>/dev/null | wc -l)
if [ $EGGINFO -gt 0 ]; then
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}✅${RESET} Removed $EGGINFO .egg-info directories"
    ITEMS_DELETED=$((ITEMS_DELETED + EGGINFO))
fi

# ============================================================================
# Remove Generated Files
# ============================================================================

echo -e "\n${BOLD}Removing generated files...${RESET}\n"

find . -type f \( -name "*.o" -o -name "*.a" -o -name "*.so" \) -delete 2>/dev/null || true
echo -e "${GREEN}✅${RESET} Removed object/library files"
ITEMS_DELETED=$((ITEMS_DELETED + 1))

# ============================================================================
# Summary
# ============================================================================

echo -e "\n${BOLD}${GREEN}╔════════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║               CLEANUP COMPLETE!${RESET}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════════╝${RESET}\n"

echo -e "${BOLD}Items deleted/cleaned: $ITEMS_DELETED${RESET}\n"

echo -e "${BOLD}Next steps:${RESET}"
echo -e "  1. Rebuild:  ${BOLD}./setup.sh${RESET}"
echo -e "  2. Run tests: ${BOLD}python3 watcher/tests/test_real.py${RESET}\n"

echo -e "${GREEN}✅ Project cleaned${RESET}\n"
