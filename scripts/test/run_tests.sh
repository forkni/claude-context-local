#!/usr/bin/env bash
# run_tests.sh - Run pytest using project virtual environment
# Usage: ./scripts/test/run_tests.sh [--parallel] [--no-sync-check] [pytest args...]
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
SYNC_CHECK=1
for arg in "$@"; do
    if [[ "$arg" == "--parallel" ]]; then
        PARALLEL_ARGS=("-n" "auto" "--dist" "loadfile")
    elif [[ "$arg" == "--no-sync-check" ]]; then
        SYNC_CHECK=0
    else
        ARGS+=("$arg")
    fi
done

cd "$PROJECT_ROOT" || exit 1

# Fail fast when the venv has drifted from uv.lock: a stale venv silently
# skips optional tiers (e.g. pyan) and lets local results diverge from CI.
# --inexact ignores extraneous packages; extras mirror what the suite imports
# (override via RUN_TESTS_SYNC_EXTRAS). Skip with --no-sync-check.
if [[ "$SYNC_CHECK" == "1" ]] && command -v uv &>/dev/null; then
    SYNC_EXTRAS="${RUN_TESTS_SYNC_EXTRAS---extra test --extra callgraph}"
    # shellcheck disable=SC2086
    if ! uv sync --locked --check --inexact $SYNC_EXTRAS >/dev/null 2>&1; then
        echo "[ERROR] venv out of sync with uv.lock -- run: uv sync --locked $SYNC_EXTRAS" >&2
        echo "        (stop the MCP server first -- it locks .pyd files -- or pass --no-sync-check to run anyway)" >&2
        exit 1
    fi
fi

echo "[INFO] Using pytest: $PYTEST"
exec "$PYTEST" "${PARALLEL_ARGS[@]}" "${ARGS[@]}"
