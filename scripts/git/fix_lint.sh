#!/usr/bin/env bash
# Auto-fix lint issues for Git Bash / Linux / macOS
# Windows cmd.exe users: use fix_lint.bat instead

set -e  # Exit on first error

echo "=== Auto-Fixing Lint Issues ==="
echo ""

echo "[1/3] Running ruff --fix..."
.venv/Scripts/ruff.exe check . --fix
echo "✓ Ruff auto-fixes applied"

echo ""
echo "[2/3] Running black..."
.venv/Scripts/black.exe .
echo "✓ Black formatting applied"

echo ""
echo "[3/3] Running isort..."
.venv/Scripts/isort.exe .
echo "✓ Isort fixes applied"

echo ""
echo "✅ All lint fixes applied!"
echo ""
echo "Run ./scripts/git/check_lint.sh to verify all issues are resolved."
exit 0
