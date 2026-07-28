#!/usr/bin/env bash
# profile_full_index.sh — Full-reindex phase profiling (measure-only).
#
# Wraps profile_full_index.py with venv-aware Python resolution.
#
# Usage:
#   ./scripts/benchmark/profiling/profile_full_index.sh
#   ./scripts/benchmark/profiling/profile_full_index.sh --runs 3
#   ./scripts/benchmark/profiling/profile_full_index.sh --runs 1 --no-profile
#   ./scripts/benchmark/profiling/profile_full_index.sh --project /path/to/other/repo

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

PROFILE_SCRIPT="$SCRIPT_DIR/profile_full_index.py"
if [[ ! -f "$PROFILE_SCRIPT" ]]; then
    echo "[ERROR] profile_full_index.py not found: $PROFILE_SCRIPT" >&2
    exit 1
fi

cd "$PROJECT_ROOT" || exit 1

# Suppress noisy PyTorch/TorchDynamo tracing logs
export TORCHDYNAMO_VERBOSE=0
unset TORCH_LOGS

echo "[INFO] Using Python: $PYTHON"
echo "[INFO] Running: profile_full_index.py $*"
exec "$PYTHON" "$PROFILE_SCRIPT" "$@"
