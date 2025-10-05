#!/usr/bin/env bash
# Branch validation script for Git Bash / Linux / macOS
# Windows cmd.exe users: use validate_branches.bat instead

set -e  # Exit on first error

echo "=== Branch Validation ==="
echo ""

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

# Check if on development or main
if [[ "$CURRENT_BRANCH" != "development" && "$CURRENT_BRANCH" != "main" ]]; then
    echo "❌ Must be on 'development' or 'main' branch"
    echo "   Current: $CURRENT_BRANCH"
    exit 1
fi
echo "✓ On valid branch: $CURRENT_BRANCH"

echo ""
echo "Checking for uncommitted changes..."
if ! git diff-index --quiet HEAD --; then
    echo "❌ Uncommitted changes detected:"
    git status --short
    exit 1
fi
echo "✓ No uncommitted changes"

echo ""
echo "Checking branch relationship (development vs main)..."
# Check if development is ahead of main
DEV_AHEAD=$(git rev-list --count main..development 2>/dev/null || echo "0")
MAIN_AHEAD=$(git rev-list --count development..main 2>/dev/null || echo "0")

echo "  Development ahead of main: $DEV_AHEAD commits"
echo "  Main ahead of development: $MAIN_AHEAD commits"

if [ "$DEV_AHEAD" -eq 0 ] && [ "$CURRENT_BRANCH" = "development" ]; then
    echo "⚠️  Warning: Development branch has no new commits vs main"
fi

if [ "$MAIN_AHEAD" -gt 0 ] && [ "$CURRENT_BRANCH" = "development" ]; then
    echo "⚠️  Warning: Main branch is ahead - consider merging main into development"
fi

echo ""
echo "✅ Branch validation passed"
exit 0
