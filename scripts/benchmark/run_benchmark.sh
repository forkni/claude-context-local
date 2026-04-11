#!/usr/bin/env bash
# run_benchmark.sh - Run SSCG benchmark using project virtual environment
# Usage: ./scripts/benchmark/run_benchmark.sh [options]
#
# Options (passed through to run_sscg_benchmark.py):
#   --project-path PATH       Path to indexed project (required)
#   --config-name NAME        Label for this run (default: "default")
#   --output PATH             Where to save results JSON
#   --k INT                   Results to retrieve per query (default: 10)
#   --category A|B|C          Filter by query category
#   --bm25-weight FLOAT       Override BM25 weight
#   --dense-weight FLOAT      Override dense weight
#   --search-mode MODE        hybrid|semantic|bm25|auto
#   --sweep                   Run parameter sweep across weight combinations
#   --compare FILE [FILE...]  Compare saved benchmark result JSONs
#   --quiet                   Suppress per-query output
#
# Examples:
#   ./scripts/benchmark/run_benchmark.sh --project-path F:/RD_PROJECTS/COMPONENTS/claude-context-local
#   ./scripts/benchmark/run_benchmark.sh --project-path /path --sweep
#   ./scripts/benchmark/run_benchmark.sh --compare results/run1.json results/run2.json

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Detect venv Python (Windows/Linux/macOS)
if [[ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    echo "[ERROR] Virtual environment not found at $PROJECT_ROOT/.venv" >&2
    echo "Run: python -m venv .venv && .venv/Scripts/pip install -e .[dev]" >&2
    exit 1
fi

BENCHMARK_SCRIPT="$SCRIPT_DIR/run_sscg_benchmark.py"

if [[ ! -f "$BENCHMARK_SCRIPT" ]]; then
    echo "[ERROR] Benchmark script not found: $BENCHMARK_SCRIPT" >&2
    exit 1
fi

cd "$PROJECT_ROOT" || exit 1

# Suppress noisy PyTorch/TorchDynamo tracing logs
export TORCHDYNAMO_VERBOSE=0
unset TORCH_LOGS

echo "[INFO] Using Python: $PYTHON"
echo "[INFO] Running: run_sscg_benchmark.py $*"
exec "$PYTHON" "$BENCHMARK_SCRIPT" "$@"
