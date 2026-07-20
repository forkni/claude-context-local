#!/usr/bin/env bash
# measure_parse_once.sh — Parse-once feasibility measurement (Candidate B exploration).
#
# Wraps measure_parse_once.py with venv-aware Python resolution.
#
# Usage:
#   ./scripts/benchmark/measure_parse_once.sh
#   ./scripts/benchmark/measure_parse_once.sh --project /path/to/other/repo
#   ./scripts/benchmark/measure_parse_once.sh --workers 8 --runs 5

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

MEASURE_SCRIPT="$SCRIPT_DIR/measure_parse_once.py"
if [[ ! -f "$MEASURE_SCRIPT" ]]; then
    echo "[ERROR] measure_parse_once.py not found: $MEASURE_SCRIPT" >&2
    exit 1
fi

cd "$PROJECT_ROOT" || exit 1

# Suppress noisy PyTorch/TorchDynamo tracing logs
export TORCHDYNAMO_VERBOSE=0
unset TORCH_LOGS

echo "[INFO] Using Python: $PYTHON"
echo "[INFO] Running: measure_parse_once.py $*"
exec "$PYTHON" "$MEASURE_SCRIPT" "$@"
