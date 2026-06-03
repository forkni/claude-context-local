#!/usr/bin/env bash
# run_caller_recall.sh — Direct-caller recall benchmark driver.
#
# Wraps run_caller_recall.py with venv-aware Python resolution.
#
# Usage:
#   ./scripts/benchmark/run_caller_recall.sh --project-path F:/path/to/project
#   ./scripts/benchmark/run_caller_recall.sh --project-path /path --output results/baseline.json
#   ./scripts/benchmark/run_caller_recall.sh --compare results/before.json results/after.json
#   ./scripts/benchmark/run_caller_recall.sh --project-path /path --target C001 --target C002

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    echo "[ERROR] Virtual environment not found at $PROJECT_ROOT/.venv" >&2
    echo "Run: python -m venv .venv && .venv/Scripts/pip install -e .[dev]" >&2
    exit 1
fi

RECALL_SCRIPT="$SCRIPT_DIR/run_caller_recall.py"
if [[ ! -f "$RECALL_SCRIPT" ]]; then
    echo "[ERROR] run_caller_recall.py not found: $RECALL_SCRIPT" >&2
    exit 1
fi

cd "$PROJECT_ROOT" || exit 1

# Suppress noisy PyTorch/TorchDynamo tracing logs
export TORCHDYNAMO_VERBOSE=0
unset TORCH_LOGS

echo "[INFO] Using Python: $PYTHON"
echo "[INFO] Running: run_caller_recall.py $*"
exec "$PYTHON" "$RECALL_SCRIPT" "$@"
