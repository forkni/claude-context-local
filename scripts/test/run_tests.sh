#!/usr/bin/env bash
# run_tests.sh - Run pytest using project virtual environment
# Usage: ./scripts/test/run_tests.sh [pytest args...]
# Example: ./scripts/test/run_tests.sh tests/ -v --tb=short

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Detect venv pytest (Windows/Linux/macOS)
if [ -f "$PROJECT_ROOT/.venv/Scripts/pytest.exe" ]; then
    PYTEST="$PROJECT_ROOT/.venv/Scripts/pytest.exe"
elif [ -f "$PROJECT_ROOT/.venv/bin/pytest" ]; then
    PYTEST="$PROJECT_ROOT/.venv/bin/pytest"
else
    echo "[ERROR] Virtual environment not found at $PROJECT_ROOT/.venv" >&2
    echo "Run: python -m venv .venv && .venv/Scripts/pip install -e .[dev]" >&2
    exit 1
fi

cd "$PROJECT_ROOT" || exit 1
echo "[INFO] Using pytest: $PYTEST"
exec "$PYTEST" "$@"
