#!/usr/bin/env bash
# bm25_tokenizer_ab.sh — BM25 tokenizer A/B recall harness driver (Round 6).
#
# Wraps bm25_tokenizer_ab.py with venv-aware Python resolution.
#
# Usage:
#   ./scripts/benchmark/bm25_tokenizer_ab.sh --project-path D:/claude-context-local
#   ./scripts/benchmark/bm25_tokenizer_ab.sh --project-path D:/claude-context-local --emit-raw-results

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

AB_SCRIPT="$SCRIPT_DIR/bm25_tokenizer_ab.py"
if [[ ! -f "$AB_SCRIPT" ]]; then
    echo "[ERROR] bm25_tokenizer_ab.py not found: $AB_SCRIPT" >&2
    exit 1
fi

cd "$PROJECT_ROOT" || exit 1

# Suppress noisy PyTorch/TorchDynamo tracing logs
export TORCHDYNAMO_VERBOSE=0
unset TORCH_LOGS

echo "[INFO] Using Python: $PYTHON"
echo "[INFO] Running: bm25_tokenizer_ab.py $*"
exec "$PYTHON" "$AB_SCRIPT" "$@"
