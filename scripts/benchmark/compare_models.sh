#!/usr/bin/env bash
# compare_models.sh - Differential model benchmark using project virtual environment
# Usage: ./scripts/benchmark/compare_models.sh [options]
#
# Options (passed through to compare_models.py):
#   --project-path PATH       Path to indexed project (required)
#   --model-a KEY             First model key (default: bge_code)
#   --model-b KEY             Second model key (default: qwen3)
#   --golden-dataset PATH     Optional golden dataset JSON for MRR/Recall scoring
#   --queries PATH            Optional custom query list JSON [{id, query}]
#   --k INT                   Results to retrieve per query (default: 5)
#   --output PATH             Where to save results JSON
#   --compare FILE1 FILE2     Compare two saved benchmark result JSONs
#   --quiet                   Suppress per-query output
#   --no-side-by-side         Skip side-by-side chunk comparison
#
# Examples:
#   # Qualitative comparison (no golden labels)
#   ./scripts/benchmark/compare_models.sh \
#       --project-path D:/dev/SD_3_0_1/test_Install_dev/StreamDiffusion
#
#   # Rigorous MRR scoring
#   ./scripts/benchmark/compare_models.sh \
#       --project-path D:/dev/SD_3_0_1/test_Install_dev/StreamDiffusion \
#       --golden-dataset evaluation/streamdiffusion_golden.json
#
#   # Compare saved results
#   ./scripts/benchmark/compare_models.sh \
#       --compare results/bge.json results/qwen.json

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

BENCHMARK_SCRIPT="$SCRIPT_DIR/compare_models.py"

if [[ ! -f "$BENCHMARK_SCRIPT" ]]; then
    echo "[ERROR] Benchmark script not found: $BENCHMARK_SCRIPT" >&2
    exit 1
fi

cd "$PROJECT_ROOT" || exit 1

# Suppress noisy PyTorch/TorchDynamo tracing logs
export TORCHDYNAMO_VERBOSE=0
unset TORCH_LOGS

echo "[INFO] Using Python: $PYTHON"
echo "[INFO] Running: compare_models.py $*"
exec "$PYTHON" "$BENCHMARK_SCRIPT" "$@"
