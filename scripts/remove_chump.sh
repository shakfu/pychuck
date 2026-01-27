#!/bin/bash
#
# Script to remove chump package manager integration from numchuck
#
# This removes:
# - C++ bindings (_chump.cpp)
# - Python modules (packages.py, _chump.py, cli/packages.py)
# - Tests (test_packages.py)
# - thirdparty/chump directory
# - CMake configuration for chump
# - CLI integration in main.py
#
# Usage: ./scripts/remove_chump.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Removing chump integration from numchuck..."
echo "Project root: $PROJECT_ROOT"
echo ""

# ============================================================================
# Remove files
# ============================================================================

echo "Removing chump-related files..."

# C++ binding
if [ -f "src/_chump.cpp" ]; then
    rm -v "src/_chump.cpp"
fi

# Python modules
if [ -f "src/numchuck/_chump.py" ]; then
    rm -v "src/numchuck/_chump.py"
fi

if [ -f "src/numchuck/packages.py" ]; then
    rm -v "src/numchuck/packages.py"
fi

if [ -f "src/numchuck/cli/packages.py" ]; then
    rm -v "src/numchuck/cli/packages.py"
fi

# Tests
if [ -f "tests/test_packages.py" ]; then
    rm -v "tests/test_packages.py"
fi

# Cached files
rm -f "src/numchuck/__pycache__/_chump.cpython-*.pyc"
rm -rf ".mypy_cache/3.13/numchuck/_chump.*"

# thirdparty/chump directory (if not a submodule)
if [ -d "thirdparty/chump" ]; then
    # Check if it's a git submodule
    if [ -f ".gitmodules" ] && grep -q "thirdparty/chump" .gitmodules 2>/dev/null; then
        echo "thirdparty/chump is a git submodule, removing with git..."
        git submodule deinit -f thirdparty/chump || true
        git rm -f thirdparty/chump || true
        rm -rf ".git/modules/thirdparty/chump" || true
    else
        echo "Removing thirdparty/chump directory..."
        rm -rf "thirdparty/chump"
    fi
fi

echo ""

# ============================================================================
# Use Python for all file modifications (cross-platform compatible)
# ============================================================================

python3 << 'PYTHON_SCRIPT'
import re
import os

# ============================================================================
# Modify CMakeLists.txt (root)
# ============================================================================

print("Modifying CMakeLists.txt...")

cmake_file = "CMakeLists.txt"
if os.path.exists(cmake_file):
    with open(cmake_file, "r") as f:
        content = f.read()

    # Create backup
    with open(cmake_file + ".bak", "w") as f:
        f.write(content)

    # Remove chump-related lines
    content = re.sub(r'^# Optional chump package manager support\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'^option\(NUMCHUCK_ENABLE_CHUMP.*?\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'if\(NUMCHUCK_ENABLE_CHUMP\).*?endif\(\)\n', '', content, flags=re.DOTALL)

    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(cmake_file, "w") as f:
        f.write(content)

    print("  Modified CMakeLists.txt (backup: CMakeLists.txt.bak)")

# ============================================================================
# Modify src/CMakeLists.txt
# ============================================================================

print("Modifying src/CMakeLists.txt...")

src_cmake_file = "src/CMakeLists.txt"
if os.path.exists(src_cmake_file):
    with open(src_cmake_file, "r") as f:
        content = f.read()

    # Create backup
    with open(src_cmake_file + ".bak", "w") as f:
        f.write(content)

    # Remove the entire _chump section (from the separator comment to endif)
    # Pattern: separator + _chump comment + separator + if block + endif
    pattern = r'\n# =+\n# _chump module.*?endif\(\)\n'
    content = re.sub(pattern, '\n', content, flags=re.DOTALL)

    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(src_cmake_file, "w") as f:
        f.write(content)

    print("  Modified src/CMakeLists.txt (backup: src/CMakeLists.txt.bak)")

# ============================================================================
# Modify src/numchuck/cli/main.py
# ============================================================================

print("Modifying src/numchuck/cli/main.py...")

main_file = "src/numchuck/cli/main.py"
if os.path.exists(main_file):
    with open(main_file, "r") as f:
        content = f.read()

    # Create backup
    with open(main_file + ".bak", "w") as f:
        f.write(content)

    # Remove _chump_available function
    content = re.sub(
        r'\ndef _chump_available\(\).*?return False\n',
        '\n',
        content,
        flags=re.DOTALL
    )

    # Remove pkg subcommand parser section
    content = re.sub(
        r'\n    # pkg subcommand - package management.*?pkg_subparsers\.add_parser\("path".*?\)\n',
        '\n',
        content,
        flags=re.DOTALL
    )

    # Remove cmd_pkg function
    content = re.sub(
        r'\ndef cmd_pkg\(args: argparse\.Namespace\).*?cmd_pkg_list\(\)\n',
        '\n',
        content,
        flags=re.DOTALL
    )

    # Remove pkg handler registration
    content = re.sub(
        r'\n    # Add pkg handler only if _chump is available\n.*?command_handlers\["pkg"\] = cmd_pkg\n',
        '\n',
        content,
        flags=re.DOTALL
    )

    # Clean up any double blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    with open(main_file, "w") as f:
        f.write(content)

    print("  Modified src/numchuck/cli/main.py (backup: src/numchuck/cli/main.py.bak)")

print("")
PYTHON_SCRIPT

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "============================================================================"
echo "Chump integration removed successfully!"
echo "============================================================================"
echo ""
echo "Files removed:"
echo "  - src/_chump.cpp"
echo "  - src/numchuck/_chump.py"
echo "  - src/numchuck/packages.py"
echo "  - src/numchuck/cli/packages.py"
echo "  - tests/test_packages.py"
echo "  - thirdparty/chump/"
echo ""
echo "Files modified (backups created with .bak extension):"
echo "  - CMakeLists.txt"
echo "  - src/CMakeLists.txt"
echo "  - src/numchuck/cli/main.py"
echo ""
echo "Manual steps remaining:"
echo "  1. Update CHANGELOG.md to note the removal"
echo "  2. Update README.md to remove chump documentation"
echo "  3. Run 'make build' to verify the build works"
echo "  4. Run 'make test' to verify tests pass"
echo "  5. Remove backup files: rm -f CMakeLists.txt.bak src/CMakeLists.txt.bak src/numchuck/cli/main.py.bak"
echo ""
