#!/bin/bash
# Flaky Test Detection Script
# Run tests multiple times to detect intermittent failures

REPEAT=${1:-5}
TEST_PATH=${2:-"tests/unit/"}

echo "=== Flaky Test Detection ==="
echo "Repeating tests ${REPEAT} times for: ${TEST_PATH}"
echo ""

# Detect Python and pytest from virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then
    PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
    PYTEST="$PROJECT_ROOT/.venv/Scripts/pytest.exe"
elif [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
    PYTEST="$PROJECT_ROOT/.venv/bin/pytest"
else
    PYTHON="python"
    PYTEST="pytest"
fi

# Check if pytest-repeat is installed
if ! "$PYTHON" -c "import pytest_repeat" 2>/dev/null; then
    echo "ERROR: pytest-repeat not installed"
    echo "Install with: pip install pytest-repeat"
    exit 1
fi

# Run tests with repetition
echo "Starting test runs..."
"$PYTEST" "$TEST_PATH" --count="$REPEAT" --tb=line -q

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ All tests passed across ${REPEAT} runs - no flaky tests detected"
else
    echo ""
    echo "✗ Tests failed - potential flaky tests or genuine failures detected"
    echo "Review output above to identify intermittent failures"
fi

exit $EXIT_CODE
