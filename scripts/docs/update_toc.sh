#!/bin/bash
# Markdown Table of Contents Generator
# Uses markdown-toc to automatically generate/update TOCs in markdown files

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== Markdown TOC Generator ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if markdown-toc is installed
if ! command -v markdown-toc >/dev/null 2>&1; then
    echo "markdown-toc not found. Installing globally..."
    npm install -g markdown-toc
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install markdown-toc"
        echo "Install manually: npm install -g markdown-toc"
        exit 1
    fi
fi

# Documents to update (add more as needed)
DOCS=(
    "$PROJECT_ROOT/PYTHON_STYLE_GUIDE.md"
    "$PROJECT_ROOT/BASH_STYLE_GUIDE.md"
    "$PROJECT_ROOT/docs/GIT_WORKFLOW.md"
    "$PROJECT_ROOT/docs/AUTOMATED_GIT_WORKFLOW.md"
)

echo "Updating TOCs in ${#DOCS[@]} documents..."
echo ""

UPDATED_COUNT=0
SKIPPED_COUNT=0

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo "Processing: $doc"
        
        # markdown-toc -i updates in-place
        if markdown-toc -i "$doc" 2>/dev/null; then
            UPDATED_COUNT=$((UPDATED_COUNT + 1))
            echo "  ✓ Updated"
        else
            echo "  ⚠ No TOC markers found (add <!-- toc --> and <!-- tocstop -->)"
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        fi
    else
        echo "Skipping (not found): $doc"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    fi
    echo ""
done

echo "========================================="
echo "Summary:"
echo "  Updated: $UPDATED_COUNT"
echo "  Skipped: $SKIPPED_COUNT"
echo "========================================="

exit 0
