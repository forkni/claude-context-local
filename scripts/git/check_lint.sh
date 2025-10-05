#!/usr/bin/env bash
# Lint validation script for Git Bash / Linux / macOS
# Windows cmd.exe users: use check_lint.bat instead

set -e  # Exit on first error

echo "=== Lint Validation ==="
echo ""

# Track failures
FAILED=0

echo "[1/4] Running ruff..."
if .venv/Scripts/ruff.exe check .; then
    echo "✓ Ruff passed"
else
    echo "❌ Ruff checks failed"
    FAILED=1
fi

echo ""
echo "[2/4] Running black..."
if .venv/Scripts/black.exe --check .; then
    echo "✓ Black passed"
else
    echo "❌ Black formatting checks failed"
    FAILED=1
fi

echo ""
echo "[3/4] Running isort..."
if .venv/Scripts/isort.exe --check-only .; then
    echo "✓ Isort passed"
else
    echo "❌ Isort checks failed"
    FAILED=1
fi

echo ""
echo "[4/4] Running markdownlint..."
if markdownlint-cli2 "**/*.md" "!**/_archive/**" "!**/node_modules/**" "!**/.venv/**" "!**/benchmark_results/**" "!**/logs/**"; then
    echo "✓ Markdownlint passed"
else
    echo "❌ Markdownlint checks failed"
    FAILED=1
fi

echo ""
if [ $FAILED -eq 0 ]; then
    echo "✅ All lint checks passed!"
    exit 0
else
    echo "❌ Some lint checks failed. Run ./scripts/git/fix_lint.sh to auto-fix."
    exit 1
fi
