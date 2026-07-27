#!/usr/bin/env bash
# profile_search_latency.sh — Search-latency phase profiling (measure-only).
#
# Wraps profile_search_latency.py with venv-aware Python resolution.
#
# Usage:
#   ./scripts/benchmark/profiling/profile_search_latency.sh
#   ./scripts/benchmark/profiling/profile_search_latency.sh --runs 8
#   ./scripts/benchmark/profiling/profile_search_latency.sh --project /path/to/other/repo
#   ./scripts/benchmark/profiling/profile_search_latency.sh --queries "auth flow" "embedding cache"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [[ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    echo "[ERROR] Virtual environment not found at $PROJECT_ROOT/.venv" >&2
    echo "Run: python -m venv .venv && .venv/Scripts/pip install -e .[dev]" >&2
    exit 1
fi

PROFILE_SCRIPT="$SCRIPT_DIR/profile_search_latency.py"
if [[ ! -f "$PROFILE_SCRIPT" ]]; then
    echo "[ERROR] profile_search_latency.py not found: $PROFILE_SCRIPT" >&2
    exit 1
fi

cd "$PROJECT_ROOT" || exit 1

# Suppress noisy PyTorch/TorchDynamo tracing logs
export TORCHDYNAMO_VERBOSE=0
unset TORCH_LOGS

echo "[INFO] Using Python: $PYTHON"
echo "[INFO] Running: profile_search_latency.py $*"
exec "$PYTHON" "$PROFILE_SCRIPT" "$@"
