#!/usr/bin/env bash
# run_tests.sh - Run pytest using project virtual environment
# Usage: ./scripts/test/run_tests.sh [--parallel] [pytest args...]
# Example: ./scripts/test/run_tests.sh tests/ -v --tb=short
# Example: ./scripts/test/run_tests.sh --parallel tests/unit/ -q

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Detect venv pytest (Windows/Linux/macOS)
if [[ -f "$PROJECT_ROOT/.venv/Scripts/pytest.exe" ]]; then
    PYTEST="$PROJECT_ROOT/.venv/Scripts/pytest.exe"
elif [[ -f "$PROJECT_ROOT/.venv/bin/pytest" ]]; then
    PYTEST="$PROJECT_ROOT/.venv/bin/pytest"
else
    echo "[ERROR] Virtual environment not found at $PROJECT_ROOT/.venv" >&2
    echo "Run: python -m venv .venv && .venv/Scripts/pip install -e .[dev]" >&2
    exit 1
fi

# --parallel is opt-in local/CI parity, not the default -- it strips itself
# out of "$@" and injects the exact xdist flags branch-protection.yml uses
# (-n auto --dist loadfile; loadfile keeps a module on one worker, required
# because of module-scoped otel fixtures + pytest-randomly). Serial stays
# the default so -x/--pdb/per-test output keep working unchanged.
PARALLEL_ARGS=()
ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--parallel" ]]; then
        PARALLEL_ARGS=("-n" "auto" "--dist" "loadfile")
    else
        ARGS+=("$arg")
    fi
done

cd "$PROJECT_ROOT" || exit 1
echo "[INFO] Using pytest: $PYTEST"
exec "$PYTEST" "${PARALLEL_ARGS[@]}" "${ARGS[@]}"
