#!/bin/bash
# Flaky Test Detection Script
#
# Two modes:
#
#   1. Repeat mode (default) — pytest-repeat runs each test N times *adjacently, in
#      place*. This surfaces within-test nondeterminism (a stateful mock, a leaked
#      side_effect iterator) but CANNOT surface ordering dependencies: every
#      repetition of a test runs immediately next to itself, never interleaved with
#      the rest of the suite.
#
#   2. Suite-loop mode (--suite-loop) — re-runs the ENTIRE suite N times as N separate
#      pytest invocations, so pytest-randomly picks a fresh random order (and prints a
#      fresh "Using --randomly-seed=<N>") each run. This is the mode that can actually
#      surface an ordering dependency — a test that only fails when some other test
#      ran before it and left state behind. Any failing run's seed is captured so the
#      failure can be reproduced directly with `pytest <path> --randomly-seed=<N>`.
#
# Usage:
#   ./scripts/test/detect_flaky_tests.sh [REPEAT] [TEST_PATH]
#   ./scripts/test/detect_flaky_tests.sh --suite-loop [LOOPS] [TEST_PATH]

# Detect Python and pytest from virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ -f "$PROJECT_ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
    PYTEST="$PROJECT_ROOT/.venv/Scripts/pytest.exe"
elif [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
    PYTEST="$PROJECT_ROOT/.venv/bin/pytest"
else
    PYTHON="python"
    PYTEST="pytest"
fi

if [[ "$1" == "--suite-loop" || "$1" == "-s" ]]; then
    LOOPS=${2:-20}
    TEST_PATH=${3:-"tests/unit/"}

    echo "=== Flaky Test Detection (suite-loop mode) ==="
    echo "Re-running the FULL suite ${LOOPS} times (fresh random order/seed each run) for: ${TEST_PATH}"
    echo "Unlike repeat mode, this can surface ordering dependencies, not just within-test nondeterminism."
    echo ""

    FAILED_SEEDS=()
    for i in $(seq 1 "$LOOPS"); do
        echo "--- Run ${i}/${LOOPS} ---"
        RUN_LOG="$(mktemp)"
        "$PYTEST" "$TEST_PATH" -q --tb=short 2>&1 | tee "$RUN_LOG"
        RUN_EXIT=${PIPESTATUS[0]}
        SEED=$(grep -m1 -- "--randomly-seed=" "$RUN_LOG" | sed -E 's/.*--randomly-seed=([0-9]+).*/\1/')
        if [[ $RUN_EXIT -ne 0 ]]; then
            echo "FAIL run ${i} -- seed=${SEED}"
            FAILED_SEEDS+=("$SEED")
        fi
        rm -f "$RUN_LOG"
    done

    echo ""
    if [[ ${#FAILED_SEEDS[@]} -eq 0 ]]; then
        echo "All ${LOOPS} full-suite runs passed - no ordering dependency detected"
        exit 0
    else
        echo "${#FAILED_SEEDS[@]}/${LOOPS} runs failed."
        echo "Reproduce with: ${PYTEST} ${TEST_PATH} --randomly-seed=<N>, using one of:"
        printf '  %s\n' "${FAILED_SEEDS[@]}"
        exit 1
    fi
fi

# --- Repeat mode (original behavior) ---
REPEAT=${1:-5}
TEST_PATH=${2:-"tests/unit/"}

echo "=== Flaky Test Detection (repeat mode) ==="
echo "Repeating tests ${REPEAT} times for: ${TEST_PATH}"
echo "Note: pytest-repeat runs each test adjacently in place -- this surfaces within-test"
echo "nondeterminism only. Use --suite-loop to surface ordering dependencies instead."
echo ""

# Check if pytest-repeat is installed
if ! "$PYTHON" -c "import pytest_repeat" 2>/dev/null; then
    echo "ERROR: pytest-repeat not installed" >&2
    echo "Install with: pip install pytest-repeat" >&2
    exit 1
fi

# Run tests with repetition
echo "Starting test runs..."
"$PYTEST" "$TEST_PATH" --count="$REPEAT" --tb=line -q

EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    echo ""
    echo "✓ All tests passed across ${REPEAT} runs - no flaky tests detected"
else
    echo ""
    echo "✗ Tests failed - potential flaky tests or genuine failures detected"
    echo "Review output above to identify intermittent failures"
fi

exit $EXIT_CODE
