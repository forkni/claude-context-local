# Testing Guide

## Overview

This comprehensive guide covers the testing infrastructure for the Claude Context MCP semantic
search system. The project maintains a professional test suite with 5,800+ passing tests
organized into clear categories for effective quality assurance.

### Current Test Status

✅ **Full suite green in one process** (re-measured 2026-08-05, nightly CI fix — see "Fixed
(Nightly CI, 2026-08-05)" below):

- **Unit Tests**: **5,800 passed, 1 skipped** (`tests/unit/`), ~97s serial. This is *collected
  test cases*, not distinct test functions: `tests/unit/evaluation/test_golden_set_guard.py`
  contributes 2 `def test_*` functions but 2,219 collected cases (`--collect-only -q` on that
  file alone) — one is a single sanity check (`test_guard_detects_corrupted_id`), the other
  2,218 are one `@pytest.mark.parametrize`d function (`test_golden_chunk_id_exists_in_live_index`)
  run once per golden chunk-id across four `evaluation/*golden*.json` files. That single
  data-driven drift guard is **~39% of the entire `tests/unit/` collected total** (2,218 of
  5,801). The protection is real and worth keeping (see Phase 10.6 note below for why it's
  collection-time live-file-reading, not a fixed count) — but "5,800 unit tests" should not be
  read as 5,800 independent test functions.
  - Chunking (incl. relationships): includes `test_call_edge_resolver.py`,
    `test_call_graph_config.py`, `test_libcst_call_graph.py`,
    `test_lsp_call_graph.py` (1 POSIX skip)
  - Embeddings, Graph, Merkle, Search, MCP Server, Evaluation, Benchmark, Utils, Tools
- **Fast Integration Tests**: **102 passed** (`tests/fast_integration/`), ~26s
- **Integration Tests**: **19 passed** (`tests/integration/`) — the 3 failures previously
  tracked here (`test_full_index_injects_real_call_edges`, `test_index_full_span_via_mcp_handler`,
  `test_search_span_hierarchy_via_mcp_handlers`) are fixed; see "Fixed (Nightly CI, 2026-08-05)"
  below
- **Slow Integration Tests**: **107 passed, 1 skipped** (`tests/slow_integration/`), 2h39m30s
  wall clock — now runs automatically in a weekly CI job (`.github/workflows/weekly.yml`, Phase
  11.1; this tier never ran in any automated job before). The one skip is a runtime
  `pytest.skip()` conditioned on `searcher.embedder is None`, not a decorator-level skip. Two
  tests dominate the runtime (`test_incremental_indexer_class` ~42min,
  `test_multi_hop_reranking` ~61min) — confirmed genuine real-model download/load work, not
  hangs, since `tests/conftest.py`'s session-wide `CODE_SEARCH_STORAGE` redirect forces a fresh,
  empty model cache for every run of this tier.
- **Total**: `tests/ --ignore=tests/slow_integration` in one process — **5,797 passed, 1
  skipped, 0 failed** in 470.16s (2026-08-05). Branch coverage (CI-shaped, same scope) is
  **76.24%** (re-measured 2026-08-05, up from 75.03% on 2026-08-04 — the C2 fix's new
  per-resolver `except` branch in `call_edge_resolver.py` is covered by its regression test, and
  the process-pool resolver path executing for the first time under pytest exercises code that
  was previously dead in every test run) against `fail_under = 73` — see "Measuring and gating
  coverage" below for why the 2026-08-04 figure itself dropped from the prior 83.52%/81 baseline
  (Phase 11.3 honestly added `tools/`'s mostly-untested CLI scripts to the measured source set).
- **Resolved (Phase 10.2)**: the intermittent failure previously tracked here in
  `tests/unit/search/test_index_write_stage.py::TestInjectCallEdgesResolverSelection::test_none_resolvers_falls_back_to_default_pair`
  did not reproduce once across 22+ randomized whole-suite runs during the Phase 10 hardening
  pass, including a dedicated 10-run whole-suite loop (`detect_flaky_tests.sh --suite-loop`).
  Phase 10.4's fix to `_reset_singleton_state()` (unconditional imports, closing the path where
  a renamed symbol would silently degrade the reset to a no-op instead of failing the run) is
  the plausible incidental fix — it matches the singleton-reset root cause this note originally
  suspected. Closed as resolved rather than left open; the seed-replay tooling
  (`detect_flaky_tests.sh --suite-loop`) stays available if it resurfaces.
- **Fixed (Phase 10.5)**: `_no_real_storage_pollution` previously diffed a shared directory
  listing (`~/.claude_code_search/{projects,merkle,graphs}`) before/after each test to catch
  production code that bypasses `get_storage_dir()`'s `CODE_SEARCH_STORAGE` redirection. That
  design had no notion of *which process* wrote a file — a live code-search MCP server was
  found to be concurrently auto-reindexing this repo while the suite ran, and its writes (real
  deployed project-hash + model-slug filenames, mtime-confirmed mid-run) were attributed to
  whichever unrelated test's teardown happened to straddle the write. Replaced with a
  process-local write ledger: a session-scoped fixture wraps `builtins.open` (write modes
  only), `os.replace`, `os.rename`, and `Path.mkdir`, recording any target that resolves under
  the real `~/.claude_code_search` together with its call stack; `_no_real_storage_pollution`
  now asserts on that ledger (cleared per test) instead of the directory diff. Immune to writes
  from other processes on the machine, and a leak now names its own call site instead of a bare
  filename. Also closed a related bypass: `mock_snapshot_manager_for_unit_tests` patched
  `merkle.snapshot_manager.SnapshotManager` at its definition-module attribute while its
  docstring claimed this was "sufficient for all imports" — five eager importers
  (`search/incremental_indexer.py`, `search/index_write_stage.py`,
  `mcp_server/tools/status_handlers.py`, `merkle/change_detector.py`, `merkle/__init__.py`)
  bind the class at import time and never saw the patch. Now patches
  `SnapshotManager.__init__` directly, which every holder shares regardless of import style;
  docstring corrected to state what is actually patched.
  The new ledger immediately surfaced a genuine, previously-invisible production leak:
  `search/search_executor.py`'s `search_dense()` read `Path.home() / ".claude_code_search" /
  "models"` directly instead of going through `get_storage_dir()`. The old diff-based guard
  missed it because `Path.mkdir(parents=True, exist_ok=True)` on an already-existing real
  directory (`~/.claude_code_search/models`, which genuinely exists from real deployment
  usage) produces no new directory-listing entry to diff against — the new ledger records the
  call regardless of whether the target pre-existed. Fixed by routing through
  `get_storage_dir()` with the same try/except fallback pattern already used by
  `SnapshotManager.__init__`, so the cache dir now honors `CODE_SEARCH_STORAGE` under test.
  Verified clean: seeds `1059340664` and `3422619523` (both originally failing with real-storage
  writes) now replay with zero such failures. Wall-clock overhead of wrapping `builtins.open`
  measured directly (seed `777002`, `tests/unit/`, one shared outlier test deselected — see
  below): 111.43s wrapped vs. 114.70s with the wrap disabled — the unwrapped run was not
  faster, and the ~3% spread is inside the same collection-count noise band documented for
  Phase 10.6 (5639 vs. 5643 collected items at nominally the same seed). No measurable
  overhead; `builtins.open` stays wrapped alongside `os.replace`/`os.rename`/`Path.mkdir`.
- **Investigated and closed (Phase 10.6)**: a 5-failure run under `--randomly-seed=811371831`
  (`test_index_sync.py` / `test_hybrid_search.py`, all sharing one signature — an explicit
  attribute set on a `MagicMock` not visible to production code at read time) did not reproduce
  across 4 consecutive full-suite replays under the same nominal seed (5,625 collected / 0
  failed each time, vs. the original run's 5,620 collected / 5 failed — a stable 5-item
  collection-count delta). `pytest-randomly`'s seed controls `random.shuffle()` over the
  *collected* item list; it does not make collection itself stable across runs.
  `tests/unit/evaluation/test_golden_set_guard.py` builds its 2,216-case parametrize list
  (`_all_golden_id_cases()`) by reading four `evaluation/*golden*.json` files live at collection
  time — the same files this repo's benchmark scripts (`scripts/benchmark/merge_h_queries.py`,
  `scripts/benchmark/mine_commit_queries.py`) write to as part of routine golden-set
  maintenance (`git log` shows commits to those exact files, e.g. `988f1f9`, from this same
  session window). A concurrent edit to any of those files between the original run and a
  replay shifts the collected count, desynchronizing the shuffle from that point on even under
  an identical `--randomly-seed`. Same failure class as 10.5: an out-of-band process on the
  machine mutating shared state the suite reads without isolation, misattributed as an in-suite
  ordering bug. `search/index_sync.py` and `search/hybrid_searcher.py` are unmodified and clean
  (behaving per ADR-0025); no production or test-mock change was made. Re-open only if the exact
  signature recurs *and* `evaluation/*golden*.json` is confirmed unchanged across the run pair.
- **Fixed (Phase 10.7)**: gate batch 3/5 hit a new signature —
  `test_resolve_bounded_when_server_hangs` failed with `ExceptionGroup: multiple unraisable
  exception warnings (6 sub-exceptions)` (all `ResourceWarning: unclosed file <_io.FileIO ...>`)
  under `--randomly-seed=1552417537`. Neither an isolated file replay nor a full-suite replay at
  that exact seed reproduced it — confirming the GC-timing-dependent misattribution this repo's
  `pyproject.toml` `filterwarnings` comment already predicted: a leaked handle surfaces on
  whichever unrelated test happens to be running when the interpreter reaps it, not on the test
  that leaked it (`test_name_resolution.py`, the file that comment names as a prior victim,
  contains no subprocess/file-handle code of its own). Root cause:
  `_LspClient.close()` (`chunking/relationships/lsp_call_graph.py`) waited on / killed the
  subprocess and joined the reader thread, but never closed `self._proc.stdin`/`stdout`/`stderr`
  or joined `self._stderr_thread` — `subprocess.Popen` does not close its pipe `FileIO` objects on
  `wait()`/`kill()`, only via an explicit `.close()` or its own `__exit__`. Fixed by closing all
  three streams (`contextlib.suppress`-wrapped) and joining `_stderr_thread` in `close()`.
  Regression: `test_initialize_and_close_leaves_no_process` now asserts `.closed` on all three
  streams after `close()`. Verified with `-W error::ResourceWarning` (escalating the
  normally-ignored warning class back to a hard failure): both LSP test files clean, plus two full
  `tests/unit/` runs (one ordered via `-p no:randomly`, one randomly-ordered) both clean at 5,644
  passed / 1 skipped. No evidence found of the second leak site the same `pyproject.toml` comment
  names (`chunking/languages/glsl.py:745`) — current source at that file has zero `open()`/file-handle
  calls, so that half of the original claim could not be located and may already be stale.
  `ignore::ResourceWarning` stays in `pyproject.toml` as defense-in-depth against a leak elsewhere
  in the dependency tree, not because a known first-party leak remains.
- **Fixed (Phase 10.8)**: a deferred-work note claimed "six `tests/unit/` tests run 6–7s vs a <1s
  budget" and "none are integrity gaps." Diagnosis found the second half wrong: those six
  `tests/unit/search/test_hybrid_search.py::TestHybridSearcher` tests were slow because
  `HybridSearcher` was constructed with no `embedder=`, so `search_dense()`'s lazy-embedder branch
  (`search/search_executor.py`) built a **real** `CodeEmbedder` and a real `jina-reranker-v3`
  cross-encoder on the GPU — live HTTPS to `huggingface.co`, a GPU model load, and (per the
  Phase 10.5 write-ledger) a write into real `~/.claude_code_search` home storage, every run. Fixed
  by constructing `HybridSearcher` with an explicit stub embedder and a test-owned
  `SearchConfig(reranker.enabled=False)` (`_stub_search_deps()` helper, reusing the
  `get_search_config` patch pattern `test_weight_change_takes_effect_without_rebuild`
  already established) instead of the after-the-fact `patch("embeddings.embedder.CodeEmbedder")`
  that never touched the reranker's separate load path.
  `test_search_dense_creates_embedder_lazily_when_none` is untouched — it deliberately exercises
  that branch and still does.
  Added a function-scoped autouse guard in `tests/conftest.py`
  (`_block_network_and_real_model_downloads` et al.) so this class of bug fails fast instead of
  silently degrading a `<1s` unit test into multi-second live network/GPU I/O: sets
  `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` and patches `socket.socket.connect` to raise on any
  non-loopback address, naming the actual call site in the error. `tests/slow_integration/` is
  exempted by path (it legitimately downloads real models); an individual test can opt out with
  `@pytest.mark.allow_network`.
  Separately, escalated `pyproject.toml`'s `filterwarnings` from a blanket ignore-everything list
  to `"error"` first with scoped third-party re-ignores (`torch.*`/`transformers.*`/
  `huggingface_hub.*`/the FAISS SWIG pattern/`ResourceWarning`, the last per Phase 10.7 above) —
  first-party `DeprecationWarning`/`PendingDeprecationWarning`/`UserWarning` now fail the test that
  raises them instead of vanishing. An `-o filterwarnings=always` inventory across the full unit
  tier first confirmed the blast radius was zero pre-existing warnings of those classes (only the
  15 `ResourceWarning`s Phase 10.7 later traced and fixed), so this was a pure policy change with
  no cleanup debt attached.
  Also deleted `tests/conftest.py`'s `pytest_configure` hook: its 9 `addinivalue_line("markers",
  ...)` calls were byte-identical duplicates of `pyproject.toml`'s list (the file `--strict-markers`
  actually reads — `asyncio` was declared there only), and its `warnings.filterwarnings(".*builtin
  type.*")` call duplicated both this file's module-level block and the ini entry above.
  Finally, added an opt-in `--parallel` flag to `scripts/test/run_tests.sh` that injects the same
  `-n auto --dist loadfile` `branch-protection.yml` (`74d0a40`) already uses in CI — serial stays
  the default so `-x`/`--pdb`/per-test output are unaffected; `--parallel tests/unit/` reproduces
  the same 5,644/1-skipped pass count in roughly half the wall-clock.
- **Correction (Phase 5.1):** `test_result_to_dict` in `tests/unit/search/test_incremental_indexer.py`
  originally asserted `IncrementalIndexResult.to_dict()` by exact-equality, including the
  `call_edges_injected` / `call_edge_resolvers` fields added by the in-flight call-graph-injection
  feature. At the time that assertion was written, those fields existed only in an uncommitted
  working tree — checking out that commit alone (e.g. for a `git bisect`) would fail the test. The
  assertion now uses subset validation over the stable fields plus a separate dataclass-field
  completeness check, per "Use subset validation for metadata" below — this passes regardless of
  which in-flight dataclass fields have landed yet.

- **Fixed (Phase 10.9)**: the Phase 10.7/10.8 work above landed in commit `9ed2ed2` untested
  against CI and broke it: the `_LspClient.close()` None-guard gap pyrefly had been silently
  accepting became a real `missing-attribute` error once the `stream.close()` loop was added
  (`Popen.stdin`/`stdout`/`stderr` are typed `IO[bytes] | None`) — fixed with an explicit
  `if stream is None: continue` before the `contextlib.suppress(Exception)` close. Separately,
  the new `_block_real_network` guard (Phase 10.8) converted a pre-existing latent
  machine-dependence into 22 hard test failures: `ModelLoader.load()`
  (`embeddings/model_loader.py`) and `JinaRerankerV3._load_or_fetch()`
  (`search/neural_reranker.py`) both only reach HuggingFace when the on-disk model cache is
  missing/invalid, so 21 tests in `tests/unit/embeddings/test_embedder.py` and 1 in
  `tests/unit/search/test_jina_reranker_v3.py` passed silently on any developer machine with a
  warm cache and failed only on CI's cold one — invisible locally, and CI's own
  `--maxfail=20` run hid the true count (21+1) behind a reported 20. Fixed by adding a
  file-scoped autouse `huggingface_hub.model_info` stub to `test_embedder.py` (42 of its 43
  tests that patch `ModelLoader`'s `SentenceTransformer` were missing it) and the
  already-established-elsewhere-in-the-file `AutoConfig.from_pretrained` patch to
  `test_cleanup_releases_resources`.
  **To reproduce a cold cache locally** (the only way to catch this failure class before
  pushing — a warm dev cache structurally cannot see it), repoint the home dir the loaders
  resolve their cache path from (`Path.home()`; there is no env-var override):

  ```bash
  USERPROFILE='C:\path\to\empty\tmp\dir' HOME='C:\path\to\empty\tmp\dir' \
    ./scripts/test/run_tests.sh tests/unit/ -q -p no:randomly -n auto --dist loadfile
  ```

  Run this before pushing any change that touches model loading or `tests/conftest.py`'s
  network guard.

- **Fixed (Nightly CI, 2026-08-05)**: the 6-test failure in nightly run 30986597353 (job
  `92242674117`, windows-latest) traced to three root causes, all fixed, none a production
  defect:
  - **`tests/conftest.py`'s write-ledger crashed on integer file descriptors.** The session-wide
    autouse `_install_real_storage_write_ledger` wraps `builtins.open`; multiprocessing's Windows
    `spawn` opens the child pipe via `open(wfd, "wb", closefd=True)` where `wfd` is a raw int, and
    `_record_if_real_storage` unconditionally called `Path(target).resolve()` on it, raising
    `TypeError`. This escaped `ProcessPoolExecutor.submit()` in `run_resolvers()`
    (`chunking/relationships/call_edge_resolver.py`) — silently disabling every process-pool call
    graph resolver (pyan, libcst) under pytest, locally and in CI, with zero prior unit coverage
    of that code path (`TestRunResolvers`'s stubs are never `isinstance`-matched into the
    process-pool branch). Fixed with an `isinstance` guard in `_record_if_real_storage`; regression
    test in `tests/unit/test_conftest_guards.py` (new file — the conftest guards had no prior test
    coverage at all). A second, defensive fix wraps the process-pool submit loop in its own
    per-resolver `try/except` so a future submit failure can't take the thread-pool (LSP) resolvers
    down with it; regression test in `TestRunResolvers` using a real `PyanResolver` instance.
  - **Windows 8.3 short paths** (`C:\Users\RUNNER~1\...` vs. the `Path.resolve()`d
    `C:\Users\runneradmin\...` production code actually stores) broke three raw
    `tempfile.mkdtemp()`-based path comparisons (`test_merkle.py` ×2,
    `test_project_switch.py::test_switch_project_shows_correct_index`). Fixed by pinning
    `tempfile.tempdir` to its resolved form at `tests/conftest.py` module load, before any test
    can call `mkdtemp()` — removes the whole failure class rather than patching the three tests.
  - **No Hugging Face cache in `nightly.yml`** blocked the real `BAAI/bge-m3` download the two
    `@pytest.mark.slow` observability tests need (`test_observability_e2e.py`). Added the same
    `actions/cache` step `weekly.yml` already has, and `@pytest.mark.allow_network` (registered
    but, until now, never actually used anywhere in the suite) to both tests.

  Verified: targeted suite green, `test_call_edge_injection_integration.py` confirmed injecting
  real pyan/libcst/LSP edges under pytest for the first time (previously always silently 0), full
  `tests/ --ignore=tests/slow_integration` green in one process — see "Reproducible baseline"
  below for exact counts.

**Note**: Run `uv run pytest tests/ --ignore=tests/slow_integration -q` for the fast CI subset
(excludes GPU-dependent slow tests, ~2 min).

### Reproducible baseline (Phase 12.3, re-measured 2026-08-05)

Every count and percentage quoted above and in the root `CLAUDE.md` Quick Reference is
reproducible from one of these commands, re-run 2026-08-05 after the nightly CI fix above:

| Metric | Value | Command |
| ------ | ----- | ------- |
| Unit collected cases | 5,801 (5,800 passed, 1 skipped) | `bash scripts/test/run_tests.sh tests/unit/ -q` |
| Fast integration | 102 passed | `bash scripts/test/run_tests.sh tests/fast_integration/ -q` |
| Integration | 19 collected, 19 passed, 0 failed | `bash scripts/test/run_tests.sh tests/integration/ -q` |
| Slow integration | 108 collected (107 passed, 1 skipped) | `bash scripts/test/run_tests.sh tests/slow_integration/ -v --tb=short --no-cov` (~2h39m wall clock) |
| Full CI-shaped subset | 5,921 passed, 1 skipped, 0 failed (unit + fast_integration + integration; duration not re-measured at this count) | `bash scripts/test/run_tests.sh tests/ --ignore=tests/slow_integration -q` |
| CI-shaped coverage | 76.24% vs. `fail_under = 73` (up from 75.03% on 2026-08-04) | `bash scripts/test/run_tests.sh tests/ --ignore=tests/slow_integration/ --cov --cov-branch --cov-report=term-missing` |
| Golden-set guard share | 2,218 of 5,801 unit cases (~38%) from one parametrized function | `.venv/Scripts/python.exe -m pytest tests/unit/evaluation/test_golden_set_guard.py --collect-only -q` |

## Recommended Testing Approach

### Why Run Tests by Module? (legacy workaround — being phased out)

Earlier measurements (2026-07-02) documented 11 cross-module contamination failures when running
the full suite in one process, and recommended module-by-module execution as a workaround. The
2026-07-26 re-measurement above shows the full suite now passes cleanly in one process in the
overwhelming majority of runs — the three test-drift bugs behind the originally-documented failures
have been identified and fixed, and only the one intermittent flake noted above remains open. The
module-by-module commands below still work as a mitigation if you hit that flake, but are no longer
required for a clean run.

### Quick Start: Run Tests by Module

```bash
# Recommended: Run all modules sequentially
.venv/Scripts/python.exe -m pytest tests/unit/chunking/ --tb=short
.venv/Scripts/python.exe -m pytest tests/unit/embeddings/ --tb=short
.venv/Scripts/python.exe -m pytest tests/unit/graph/ --tb=short
.venv/Scripts/python.exe -m pytest tests/unit/merkle/ --tb=short
.venv/Scripts/python.exe -m pytest tests/unit/search/ --tb=short
.venv/Scripts/python.exe -m pytest tests/unit/mcp_server/ --tb=short
.venv/Scripts/python.exe -m pytest tests/integration/ --tb=short
```

### Automated Module Testing Script

**Usage:**

```cmd
cd tests
run_all_tests.bat
```

This script is located at `tests/run_all_tests.bat`:

```batch
@echo off
setlocal

echo ========================================
echo Running Claude Context Test Suite
echo ========================================
echo.

set "PYTEST=..env\Scripts\python.exe -m pytest"
set "FAILED=0"

echo [1/7] Testing Chunking module...
%PYTEST% unit/chunking/ --tb=short -q || set "FAILED=1"

echo [2/7] Testing Embeddings module...
%PYTEST% unit/embeddings/ --tb=short -q || set "FAILED=1"

echo [3/7] Testing Graph module...
%PYTEST% unit/graph/ --tb=short -q || set "FAILED=1"

echo [4/7] Testing Merkle module...
%PYTEST% unit/merkle/ --tb=short -q || set "FAILED=1"

echo [5/7] Testing Search module...
%PYTEST% unit/search/ --tb=short -q || set "FAILED=1"

echo [6/7] Testing MCP Server module...
%PYTEST% unit/mcp_server/ --tb=short -q || set "FAILED=1"

echo [7/7] Testing Integration...
%PYTEST% integration/ --tb=short -q || set "FAILED=1"

echo.
if %FAILED%==0 (
    echo ========================================
    echo ALL TESTS PASSED
    echo ========================================
    exit /b 0
) else (
    echo ========================================
    echo SOME TESTS FAILED
    echo ========================================
    exit /b 1
)
```

## Running Tests

### Module-Specific Testing (Recommended)

```bash
# Chunking tests (~9s)
pytest tests/unit/chunking/ -v

# Embeddings tests (~1s)
pytest tests/unit/embeddings/ -v

# Graph tests (~2s)
pytest tests/unit/graph/ -v

# Merkle tests (~1s)
pytest tests/unit/merkle/ -v

# Search tests (~26s)
pytest tests/unit/search/ -v

# MCP Server tests (~2s)
pytest tests/unit/mcp_server/ -v

# Integration tests (~19s)
pytest tests/integration/ -v
```

### Quick Testing Options

```bash
# Run specific module with minimal output
pytest tests/unit/chunking/ -q

# Run specific module and stop on first failure
pytest tests/unit/search/ -x

# Run specific module with detailed failure info
pytest tests/unit/embeddings/ --tb=long

# Run specific test file
pytest tests/unit/chunking/test_smart_dedent.py -v
```

### Coverage Testing by Module

```bash
# Generate coverage for specific module
pytest tests/unit/search/ --cov=search --cov-report=html

# Coverage for multiple modules
pytest tests/unit/chunking/ tests/unit/embeddings/ --cov=chunking --cov=embeddings --cov-report=term-missing

# Combined coverage report (run modules separately, append coverage)
pytest tests/unit/chunking/ --cov=chunking --cov-report=xml
pytest tests/unit/embeddings/ --cov=embeddings --cov-append --cov-report=xml
pytest tests/unit/graph/ --cov=graph --cov-append --cov-report=xml
# ... continue for all modules
```

## Test Organization

### Directory Structure

```
tests/
├── __init__.py               # Package initialization
├── conftest.py               # Global pytest configuration
├── README.md                 # Detailed test documentation (407 lines)
├── TESTING_GUIDE.md          # This comprehensive guide
├── README_TESTING_UTILS.md   # Testing utilities documentation
├── testing_utils.py          # Reusable testing utilities (decorators, context managers)
├── fixtures/                 # Test fixtures and mocks
│   ├── __init__.py
│   ├── installation_mocks.py # Installation testing mocks
│   └── sample_code.py        # Sample code for testing
├── helpers/                  # Shared test helper utilities
│   ├── __init__.py
│   ├── check_auth.py         # Authentication validation
│   └── embeddings.py         # Shared embedding helper functions
├── test_data/                # Test datasets and sample projects
│   ├── glsl_project/         # GLSL shader samples
│   ├── multi_language/       # Multi-language test files
│   └── python_project/       # Python project samples
├── unit/                     # Unit tests (5,644 passed, 1 skipped as of 2026-08-04; see CI for current count)
│   ├── test_bm25_index.py    # BM25 index functionality
│   ├── test_bm25_population.py # BM25 document population
│   ├── test_embedder.py      # Embedding generation
│   ├── test_testing_utils.py # Testing utilities validation (11 tests)
│   ├── test_evaluation.py    # Evaluation framework components
│   ├── test_hybrid_search.py # Hybrid search logic
│   ├── test_import_resolution.py # Import-based call graph resolution (26 tests)
│   ├── test_incremental_indexer.py # Incremental indexing
│   ├── test_mcp_server.py    # MCP server tools
│   ├── test_merkle.py        # Merkle tree functionality
│   ├── test_model_selection.py # Multi-model support (Gemma/BGE-M3)
│   ├── test_multi_language.py # Multi-language parsing
│   ├── test_reranker.py      # RRF reranking algorithm
│   ├── test_search_config.py # Search configuration
│   ├── test_token_efficiency.py # Token efficiency evaluation
│   └── test_tree_sitter.py   # Tree-sitter parsing
├── fast_integration/         # Fast integration tests (< 5s each)
│   ├── test_complete_workflow.py # End-to-end workflow
│   ├── test_cuda_detection.py # GPU/CUDA detection
│   ├── test_encoding_validation.py # Text encoding validation
│   ├── test_glsl_chunking.py # GLSL chunking validation
│   ├── test_import_resolution_integration.py # Import resolution end-to-end (11 tests)
│   ├── test_installation.py  # Installation verification
│   ├── test_installation_flow.py # Installation workflow
│   ├── test_mcp_project_management.py # MCP project management
│   ├── test_model_switching.py # Model switching (Gemma/BGE-M3)
│   ├── test_token_efficiency_workflow.py # Token efficiency workflow
│   └── test_tree_sitter_*.py # Tree-sitter parsing tests
├── slow_integration/         # Slow integration tests (> 10s each; excluded from main CI run)
│   ├── test_auto_reindex.py  # Auto-reindexing functionality
│   ├── test_direct_indexing.py # Direct indexing tests
│   ├── test_full_flow.py     # Complete search workflow
│   ├── test_glsl_advanced.py # Advanced GLSL features
│   ├── test_hybrid_search_integration.py # Hybrid search integration
│   ├── test_incremental_indexing.py # Incremental indexing
│   ├── test_mcp_indexing.py  # MCP indexing workflow
│   ├── test_multi_hop_flow.py # Multi-hop semantic search
│   ├── test_relationship_extraction_integration.py # Code relationship extraction
│   ├── test_semantic_search.py # End-to-end semantic search
│   └── test_system.py        # System integration tests
└── regression/               # Regression tests (1 file, 15 checks)
    └── test_mcp_configuration.ps1 # MCP config validation (PowerShell)
```

### Design Principles

- **Separation of Concerns**: Unit tests focus on individual components, integration tests verify interactions
- **Professional Organization**: Clear categorization improves maintainability and test discovery
- **Comprehensive Coverage**: All major components and workflows have corresponding tests
- **Realistic Test Data**: Sample projects mirror real-world usage patterns

## Running Tests

### Basic Test Execution

```bash
# Run all tests (5,600+ tests; use --ignore=tests/slow_integration/ for CI speed)
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with brief output
pytest tests/ -q

# Stop on first failure
pytest tests/ -x
```

### Category-Specific Testing

```bash
# Unit tests only (< 1s each) - Fast component testing
pytest tests/unit/

# Fast integration tests only (< 5s each) - Quick workflow validation
pytest tests/fast_integration/

# Slow integration tests only (> 10s each) - Comprehensive workflow validation
pytest tests/slow_integration/

# All integration tests
pytest tests/fast_integration/ tests/slow_integration/

# Regression tests (PowerShell, 1 file, 15 checks)
tests\regression\test_mcp_configuration.ps1

# Specific test files
pytest tests/unit/test_bm25_index.py
pytest tests/fast_integration/test_complete_workflow.py
pytest tests/slow_integration/test_full_flow.py
```

### Interactive Menu Testing

```bash
# Launch interactive menu
start_mcp_server.cmd

# Navigate: Advanced Options (6) → Testing Options
# - Option 1: Start Server in Debug Mode
# - Option 2: Run Unit Tests
# - Option 3: Run Integration Tests
# - Option 4: Run Regression Tests
# - Option 5: Back to Main Menu
```

### Pattern-Based Testing

```bash
# Test specific functionality
pytest tests/ -k "bm25"
pytest tests/ -k "hybrid and not slow"
pytest tests/ -k "installation"

# Test specific components
pytest tests/unit/test_hybrid_search.py tests/integration/test_hybrid_search_integration.py
```

### Coverage Testing

```bash
# Run with coverage report
pytest tests/ --cov=. --cov-report=html

# Coverage with specific threshold
pytest tests/ --cov=. --cov-fail-under=80

# Terminal coverage report
pytest tests/ --cov=. --cov-report=term-missing
```

### Performance and Debugging

```bash
# Run last failed tests first
pytest tests/ --lf

# Show detailed failure information
pytest tests/ --tb=long

# Run tests in parallel (if pytest-xdist installed)
pytest tests/ -n auto

# Time the slowest tests
pytest tests/ --durations=10
```

## Test Categories

### Unit Tests

**Purpose**: Test individual components in isolation with mocked dependencies.

**Key Areas**:

- **Search Components**: BM25 indexing, hybrid search algorithms, reranking
- **Language Support**: Tree-sitter parsing, multi-language chunking
- **Model Support**: Multi-model configuration (Gemma/BGE-M3), model selection
- **Core Infrastructure**: Merkle trees, incremental indexing, search configuration
- **Evaluation Framework**: Token efficiency measurement, evaluation components
- **MCP Integration**: Server tools, import validation
- **Call Graph Resolution**: Import-based resolution (`ImportResolver`), type annotations (`TypeResolver`), assignment tracking (`AssignmentTracker`) - v0.5.12-v0.5.16

**Characteristics**:

- Very fast execution (< 1 second per test)
- Isolated from external dependencies
- Extensive use of mocks and fixtures
- High code coverage targets (>90%)

### Fast Integration Tests

**Purpose**: Verify component interactions with quick feedback cycles for CI/CD.

**Key Areas**:

- **Quick Workflows**: End-to-end workflow validation, installation verification
- **System Integration**: CUDA detection, encoding validation
- **MCP Server**: Project management, basic indexing workflows
- **Model Switching**: Embedding generation with Gemma and BGE-M3
- **Language-Specific**: GLSL chunking validation, tree-sitter parsing
- **Performance**: Token efficiency workflows, import resolution integration

**Characteristics**:

- Fast execution (< 5 seconds per test)
- Real component interactions with mocked slow operations
- File system operations (using temporary directories)
- Ideal for CI fast feedback loops

### Slow Integration Tests

**Purpose**: Comprehensive end-to-end validation of complete workflows.

**Key Areas**:

- **Complete Workflows**: Full indexing and search processes with real embeddings
- **Advanced Features**: Multi-hop search, hybrid search integration, auto-reindexing
- **Code Relationships**: Phase 3 relationship extraction and call graph analysis
- **System Tests**: Complete system integration, semantic search end-to-end
- **Performance**: Large codebase performance testing, incremental indexing
- **GLSL Advanced**: Advanced GLSL shader processing features

**Characteristics**:

- Longer execution time (> 10 seconds per test, some minutes)
- Real component interactions without mocking
- File system and potentially network operations
- Comprehensive workflow validation
- Marked with `@pytest.mark.slow` decorator

### Regression Tests (1 file, 15 checks)

**Purpose**: Prevent previously fixed bugs from reoccurring and validate system configuration integrity.

**Key Areas**:

- **MCP Configuration**: Validates `.claude.json` structure and required fields
  - Checks for required 'args' and 'env' fields
  - Validates PYTHONPATH and PYTHONUNBUFFERED environment variables
  - Ensures correct Python executable paths
  - Verifies working directory configuration
- **Configuration Integrity**: Checks environment variables and paths
- **Deployment Validation**: Pre-deployment configuration checks

**Characteristics**:

- Standalone PowerShell scripts
- Fast execution (< 5 seconds)
- No Python dependencies required
- Can be run independently of pytest
- Validates system state and configuration

**When to Add Regression Tests**:

- Critical bug was fixed and you want to prevent it from reoccurring
- System configuration structure has changed
- Need to validate batch/PowerShell scripts work correctly
- Pre-deployment checks for configuration integrity

## Fast vs Slow Test Organization

### 4-Tier Test Organization

The test suite uses a 4-tier system optimized for CI/CD performance:

| Tier | Location | Count | Execution Time | Purpose |
| ------ | ---------- | ------- | ---------------- | --------- |
| **Unit** | `tests/unit/` | 5,644 passed, 1 skipped | < 1s per test (~100s total serial / ~52s with `--parallel`) | Component isolation testing |
| **Fast Integration** | `tests/fast_integration/` | 102 passed | < 5s per test | Quick workflow validation |
| **Integration** | `tests/integration/` | 6 files, 16 passed | up to ~15s per test | Real-component E2E (no model downloads, so still fast enough for CI) |
| **Slow Integration** | `tests/slow_integration/` | 107 passed, 1 skipped | > 10s per test, up to ~61min | Comprehensive end-to-end (real model downloads); weekly CI job, not on every PR |

Kept as a 4th tier rather than folded into `fast_integration/` (Phase 6 decision — see the >5s
durations table below: every `tests/integration/` file has at least one test over the 5s tier
budget).

The unit tier's `<1s` budget is not enforced by a timing assertion — nothing fails a test purely
for running long. It is enforced indirectly by the `tests/conftest.py` network and storage guards
(Phase 10.8's `_block_network_and_real_model_downloads`, Phase 10.5's `_no_real_storage_pollution`
write ledger): the dominant way a unit test silently balloons past the budget is by reaching real
network I/O, a real model load, or real disk storage instead of a mock, and those guards now fail
that test outright rather than letting it pass slowly.

Unit/fast_integration/integration counts above re-measured 2026-08-04 (Phase 10.8);
slow_integration count re-measured the same day (Phase 11, first-ever automated run of that
tier). No combined `pytest tests/` (all tiers, one process) figure is carried here anymore — the
previous "3,592 passed ... 478.55s" measurement predates the Phase 10.5–10.8 fixes and would
understate the current unit-tier count alone; re-measure per-tier as needed rather than trusting
a stale total.

**Tests over 5s** (unit-tier row re-measured 2026-08-04 via `--durations=0`, Phase 10.8;
integration/slow_integration rows carried over from the 2026-07-26 baseline, not re-measured this
pass):

| Duration | Test | Current tier |
| ---------- | ------ | --------------- |
| 66.81s | `test_auto_reindex.py::test_auto_reindex` | slow_integration |
| 60.22s | `test_semantic_search.py::...test_semantic_search_basic` (setup) | slow_integration |
| 14.80s | `test_observability_e2e.py::test_search_span_hierarchy_via_mcp_handlers` | integration |
| 13.26s | `test_hybrid_search_integration.py::...test_hybrid_search_returns_results` | slow_integration |
| 10.32s | `test_hybrid_search_integration.py::...test_index_persistence` | slow_integration |
| 9.26s | `test_multi_hop_flow.py::...test_multi_hop_basic_functionality` | slow_integration |
| 6.87s | `test_mcp_indexing.py::...test_incremental_indexing_mcp_path` | slow_integration |
| 6.62s | `test_auto_reindex_fixes.py::...test_uses_config_default_when_not_specified` | integration |
| 6.54s | `test_retrieval_evaluation.py::...test_bm25_file_hit[RQ01]` | slow_integration |
| 6.05s | `test_observability_e2e.py::test_index_full_span_via_mcp_handler` | integration |
| 5.89s | `test_phase_implementations.py::test_phase2_symbol_hash_cache` | integration |
| 5.16s | `test_logging_setup.py::...test_run_index_directory_configures_logging_before_first_log` | unit |

The seven unit-tier rows previously listed here (`test_mcp_server_can_import_as_first_module` at
8.83s down to `test_multi_hop_uses_batched_search` at 6.31s) are gone: `test_weight_optimization`
no longer exists, and the other six were the `test_hybrid_search.py::TestHybridSearcher` tests
fixed under Phase 10.8 above — their multi-second runtime was the real-model-load bug, not
inherent test cost. Only one unit test now exceeds the 5s mark.

All 6 `tests/integration/` files have at least one sub-15s test — none are candidates for folding
into `tests/fast_integration/` (< 5s) outright; kept as a documented 4th tier per Phase 6 (table
above), rather than merged. `tests/test_mmap_cleanup.py` (repo-root) did not appear in the >5s
durations list, i.e. it runs fast, and exercises a real `FaissVectorIndex` (not a mock) — so
Phase 6 relocated it to `tests/fast_integration/test_mmap_cleanup.py`. Note: this file is listed in
`.gitignore` as a "local development test file" — it is not tracked in git and does not run in CI;
it only appears in local full-suite runs on a machine where it happens to exist on disk. The
relocation preserves that untracked status (the `.gitignore` entry was updated to the new path);
un-ignoring it would be a separate decision.

### Slow Test Marker

All slow integration tests are marked with the `@pytest.mark.slow` decorator:

```python
import pytest


@pytest.mark.slow
def test_full_indexing_workflow(tmp_path):
    """Complete indexing workflow with real embeddings."""
    # Test implementation...


@pytest.mark.slow
class TestComprehensiveSearch:
    """Comprehensive search integration tests."""

    def test_multi_hop_search(self):
        """Test multi-hop semantic search."""
        # Test implementation...
```

**Benefits**:

- Skip slow tests during development: `pytest tests/ -m "not slow"`
- Run only slow tests for comprehensive validation: `pytest tests/ -m slow`
- Separate fast CI pipeline from comprehensive nightly builds

### CI/CD Optimization Strategy

**Fast CI Pipeline** (< 3 minutes):

```bash
# Run unit + fast integration only
pytest tests/unit/ tests/fast_integration/ --cov=. --cov-fail-under=75
```

**Comprehensive CI Pipeline** (10-15 minutes):

```bash
# Run all tests including slow integration
pytest tests/ --cov=. --cov-fail-under=80
```

**Development Workflow**:

```bash
# Quick validation during development (< 3 min)
pytest tests/unit/ tests/fast_integration/ -x

# Pre-commit validation (< 5 min)
pytest tests/ -m "not slow" -v

# Full validation before PR (10-15 min)
pytest tests/ -v
```

### When to Add Tests to Each Tier

**Unit Tests** (`tests/unit/`):

- Testing individual functions, classes, or modules
- All external dependencies mocked
- No file system operations (or using in-memory alternatives)
- No network calls
- Execution time < 1 second

**Fast Integration Tests** (`tests/fast_integration/`):

- Quick end-to-end workflows with mocked slow operations
- File system operations using `tmp_path` fixture
- Mocked model loading (avoid downloading 4GB+ models)
- Basic MCP server operations
- System integration checks (CUDA detection, encoding validation)
- Execution time < 5 seconds

**Slow Integration Tests** (`tests/slow_integration/`):

- Complete workflows with real embeddings and models
- Large codebase indexing and search
- Multi-hop search, hybrid search with real data
- Performance benchmarking
- Comprehensive relationship extraction
- Execution time > 10 seconds (mark with `@pytest.mark.slow`)

### Test Fixtures and Utilities

#### testing_utils.py

**Professional testing utilities** (based on HuggingFace Transformers patterns):

- **Hardware requirement decorators**:
  - `@require_torch` - Skip test if PyTorch not installed
  - `@require_torch_gpu` - Skip test if no CUDA GPU available
- **Output capture utilities**:
  - `CaptureStdout()` - Capture stdout in context manager
  - `CaptureStderr()` - Capture stderr in context manager
  - `CaptureStd()` - Capture both stdout and stderr
  - `CaptureLogger(logger_name, level)` - Capture logging output
- **Environment mocking**:
  - `@mockenv(**kwargs)` - Decorator to temporarily set environment variables
  - `mockenv_context(**kwargs)` - Context manager for environment variables

**Example usage**:

```python
from tests.testing_utils import require_torch_gpu, CaptureLogger, mockenv


@require_torch_gpu
def test_gpu_inference():
    """Test runs only if CUDA GPU is available."""
    # Test GPU-specific code


def test_logging_output():
    """Verify logging output."""
    with CaptureLogger("search.hybrid_searcher") as cl:
        searcher.add_embeddings(results)
    assert "resolved" in cl.out


@mockenv(CUDA_VISIBLE_DEVICES="0", MODEL_NAME="test")
def test_env_dependent():
    """Test with specific environment variables."""
    # Environment automatically restored after test
```

**Documentation**: See `README_TESTING_UTILS.md` for complete guide.

#### fixtures/ directory

**Purpose**: Provide reusable test data and mocks.

**Components**:

- **installation_mocks.py**: Mock components for installation testing
- **sample_code.py**: Comprehensive sample codebase with realistic patterns
- **Shared fixtures**: Common test data and configuration

### Test Data (tests/test_data/)

**Purpose**: Sample projects for realistic testing scenarios.

**Projects**:

- **python_project/**: Python codebase with various architectural patterns
- **multi_language/**: Files in multiple programming languages
- **glsl_project/**: GLSL shader files for graphics programming validation

## Creating New Tests

### Test Naming Convention

```python
# Test files
test_<component>.py

# Test classes
class Test<ComponentName>:

# Test methods
def test_<specific_behavior>(self):
```

### Example Test Structure

```python
"""
tests/unit/test_new_component.py
"""

import pytest
from unittest.mock import Mock, patch

from your_module import NewComponent


class TestNewComponent:
    """Test cases for NewComponent."""

    @pytest.fixture
    def component(self):
        """Create a test instance of NewComponent."""
        return NewComponent(config={"test": True})

    def test_basic_functionality(self, component):
        """Test basic operation."""
        # Arrange
        input_data = "test input"
        expected_output = "expected result"

        # Act
        result = component.process(input_data)

        # Assert
        assert result == expected_output

    def test_error_handling(self, component):
        """Test error conditions."""
        with pytest.raises(ValueError, match="Invalid input"):
            component.process(None)

    def test_edge_cases(self, component):
        """Test boundary conditions."""
        # Test empty input
        assert component.process("") == ""

        # Test large input
        large_input = "x" * 10000
        result = component.process(large_input)
        assert len(result) > 0

    @patch("your_module.external_dependency")
    def test_mocked_dependency(self, mock_dependency, component):
        """Test with mocked external dependency."""
        # Arrange
        mock_dependency.return_value = "mocked result"

        # Act
        result = component.process_with_dependency("input")

        # Assert
        assert result == "mocked result"
        mock_dependency.assert_called_once_with("input")
```

### Integration Test Example

```python
"""
tests/integration/test_new_workflow.py
"""

import pytest
import tempfile
from pathlib import Path

from your_module import WorkflowManager


class TestNewWorkflow:
    """Integration tests for complete workflow."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create sample files
            (project_path / "main.py").write_text("print('hello')")
            (project_path / "config.json").write_text('{"setting": "value"}')

            yield project_path

    def test_complete_workflow(self, temp_project):
        """Test end-to-end workflow."""
        # Arrange
        manager = WorkflowManager()

        # Act
        result = manager.process_project(temp_project)

        # Assert
        assert result.success is True
        assert len(result.processed_files) == 2
        assert result.errors == []
```

### Guidelines for New Tests

1. **Use descriptive test names** that explain the behavior being tested
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **One assertion per concept** - avoid testing multiple unrelated things
4. **Use fixtures** for common setup and teardown
5. **Mock external dependencies** in unit tests
6. **Test both success and failure paths**
7. **Include edge cases and boundary conditions**
8. **Use temporary directories** for file system operations
9. **Assert on counts produced, not on calls made** — when a test's job is to
   catch a regression in an object's *value* (a count, a result, a persisted
   field), assert on that value from a real run, not on whether a mocked
   dependency was called. A `Mock().method.call_args_list` assertion proves
   the call happened; it says nothing about whether the return value was
   ever used. This is exactly the shape that let a call-edge injection bug
   ship silently (`3adc724`): `tests/unit/search/test_index_write_stage.py`
   asserted only `storage.add_call_edge.call_args_list` against a `Mock`
   graph, so the call always looked correct even after the real return value
   started being discarded. Pair fast Mock-based unit tests (for branch
   coverage) with at least one real integration test that drives production
   objects end-to-end and asserts on the resulting count or persisted state
   — see `tests/integration/test_call_edge_injection_integration.py`, which
   indexes `tests/fixtures/mini_repo/` for real and asserts
   `result.call_edges_injected > 0` plus `resolver_source` in the saved
   graph JSON.

### Best Practices from Recent Fixes (2025-01-10)

**Critical lessons learned from recent test fixes:**

1. **Always mock model loading**: Never let tests download 4GB+ models

   ```python
   from unittest.mock import Mock, patch


   @patch("embeddings.embedder.SentenceTransformer")
   def test_with_mocked_model(mock_transformer):
       mock_model = Mock()
       mock_model.encode.return_value = np.random.randn(768).astype("float32")
       mock_transformer.return_value = mock_model
       # Test logic here
   ```

2. **Use subset validation for metadata**: Don't assume exact field matches

   ```python
   # Bad: Exact equality fails when BM25 adds extra fields
   assert meta == expected

   # Good: Subset validation
   for key, value in expected.items():
       assert key in meta, f"Expected key '{key}' not found"
       assert meta[key] == value
   ```

3. **Import Mock explicitly**: Don't rely on it being available

   ```python
   from unittest.mock import Mock, patch  # Always import explicitly
   ```

4. **Verify test data accuracy**: Ensure fixture values match actual behavior

   ```python
   # Update test assertions to match actual implementation
   assert env.disk_space_gb == 0.5  # Not 1.0 for low disk test
   ```

5. **Add public methods for testing**: Don't test private methods directly

   ```python
   # Added public load() method to CodeIndexManager for test access
   def load(self) -> bool:
       """Public method for loading index (used by tests)."""
       if self._index is not None and len(self._chunk_ids) > 0:
           return True
       # Load logic here
   ```

6. **Mock at the right level**: Mock external dependencies, not internal logic

   ```python
   # Mock SentenceTransformer to avoid downloads
   @patch('embeddings.embedder.SentenceTransformer')
   ```

7. **Test error messages flexibly**: Accept reasonable variations

   ```python
   # Allow multiple acceptable error messages
   assert any(
       msg in str(exc.value)
       for msg in ["Project directory not found", "Invalid project path"]
   )
   ```

8. **Create regression tests for bugs**: Prevent fixed issues from reoccurring
   - MCP configuration validation test created after fixing missing 'args'/'env' fields
   - 15 checks ensure configuration integrity

## Test Isolation and Production Directory Protection

### Overview

**CRITICAL**: All tests MUST use isolated temporary directories to prevent production directory pollution. Tests that write to `~/.claude_code_search` in the user's home directory will cause:

- Conflicts with production index data
- Test artifacts persisting after test completion
- Unreliable test results due to shared state
- Data corruption in production usage

### Production Directory Structure

The following directories are production-only and MUST NOT be accessed by tests:

```
~/.claude_code_search/
├── graphs/                  # CodeGraphStorage data
├── merkle/                  # SnapshotManager data
│   └── *_metadata.json     # Merkle tree snapshots
└── projects/               # Project-specific indices
    └── project_name_*/     # Per-project storage
```

### Automatic Safety Net (Phase 8)

Two autouse fixtures in `tests/conftest.py` back up the manual practices below:

- **`_redirect_test_storage`** (session-scoped) points `CODE_SEARCH_STORAGE` at an isolated
  `tmp_path_factory` directory for the whole test session. `get_storage_dir()`
  (`mcp_server/storage_manager.py`) reads that env var, so anything that goes through it —
  including `SnapshotManager()`'s default `storage_dir` — never resolves to the real
  `~/.claude_code_search` while tests are running.
- **`_no_real_storage_pollution`** (autouse, every test) is the backstop for what the redirect
  above cannot reach: `CodeGraphStorage`'s default `storage_dir` reads `Path.home()` directly
  (`graph/graph_storage.py`), bypassing `get_storage_dir()` entirely, so it is **not** covered by
  the redirect. This fixture snapshots `~/.claude_code_search/{projects,merkle,graphs}` before and
  after each test and fails loudly if a new entry appears.

These two fixtures make production-directory pollution fail the test suite instead of silently
corrupting real data — but they are a safety net, not a substitute for the practices below.
`storage_dir=` is still mandatory for `CodeGraphStorage` in particular, since it is the one
component the redirect doesn't cover.

**Known false-positive source: a concurrent live MCP client.** If this repo's `code-search` MCP
server (port 8765) is also being used interactively — e.g. from another Claude Code window working
on a different project — while the test suite runs, that server writes to the *real*
`~/.claude_code_search` independently of pytest, on its own schedule. `_no_real_storage_pollution`
cannot distinguish that from genuine test leakage, since both look like "a new top-level entry
appeared." Observed once during Phase 9 measurement: a teardown error reported a new
`agentic-perf-loop_<hash>_f2llm-v2-0.6b_1024d` project entry, but `~/.claude_code_search/project_selection.json`
showed `last_project_path` pointing at that same unrelated real project, updated minutes after the
directory appeared — confirming a different concurrent session, not this repo's test suite, wrote
it. If this fires, check whether the leaked project name matches something in `tests/` fixtures
(e.g. `test_project`, a `tmp_path` name) before assuming a real regression; if it's an unrelated
real project path, it's this exception, not a bug in the code under test.

### Required Isolation Practices

#### 1. Always Use `tmp_path` Fixture

```python
def test_with_graph_storage(tmp_path):
    """Correct: Use tmp_path for isolated testing."""
    from graph.graph_storage import CodeGraphStorage

    # Create storage in temporary directory
    storage_dir = tmp_path / "graphs"
    graph = CodeGraphStorage("test_project", storage_dir=storage_dir)

    # Test logic here
    # Cleanup is automatic via pytest's tmp_path
```

**Bad Example (Production Pollution)**:

```python
def test_with_graph_storage_bad():
    """WRONG: Creates data in production directory."""
    from graph.graph_storage import CodeGraphStorage

    # ❌ No storage_dir - defaults to ~/.claude_code_search/graphs
    graph = CodeGraphStorage("test_project")
```

#### 2. Use Provided Fixtures

The test suite provides reusable fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def graph_storage(tmp_path: Path):
    """Isolated CodeGraphStorage fixture."""
    # Use this fixture instead of creating CodeGraphStorage manually


@pytest.fixture
def snapshot_manager(tmp_path: Path):
    """Isolated SnapshotManager fixture."""
    # Use this fixture instead of creating SnapshotManager manually
```

**Usage Example**:

```python
def test_with_fixture(graph_storage):
    """Use provided fixtures for automatic isolation."""
    # graph_storage is already configured with tmp_path
    graph_storage.add_node(
        chunk_id="test.py:1-10:function:test",
        name="test",
        chunk_type="function",
        file_path="test.py",
    )
    # Cleanup is automatic
```

#### 3. Mock Production Components in Unit Tests

For unit tests, mock components that would access production directories:

```python
from unittest.mock import Mock, patch


def test_initialization_with_defaults(tmp_path):
    """Mock SnapshotManager to prevent production access."""
    with patch("search.incremental_indexer.SnapshotManager") as mock_snapshot_class:
        # Configure mock to use temp directory
        mock_snapshot_instance = Mock()
        mock_snapshot_instance.storage_dir = tmp_path / "merkle"
        mock_snapshot_class.return_value = mock_snapshot_instance

        # Test logic here - no production pollution
```

#### 4. Provide Explicit Paths for Integration Tests

Integration tests should provide explicit temporary paths:

```python
def test_full_indexing_workflow(tmp_path):
    """Integration test with explicit temporary paths."""
    from search.incremental_indexer import IncrementalIndexer
    from merkle.snapshot_manager import SnapshotManager

    # Create components with temporary storage
    snapshot_manager = SnapshotManager(storage_dir=str(tmp_path / "merkle"))
    indexer = IncrementalIndexer(snapshot_manager=snapshot_manager)

    # Test logic here
```

### Common Violations and Fixes

| Violation | Problem | Fix |
| ----------- | --------- | ----- |
| `CodeGraphStorage("test_project")` | No `storage_dir` → writes to `~/.claude_code_search/graphs` | Add `storage_dir=tmp_path / "graphs"` |
| `SnapshotManager()` | No `storage_dir` → writes to `~/.claude_code_search/merkle` | Add `storage_dir=str(tmp_path / "merkle")` |
| `IncrementalIndexer()` | Creates default SnapshotManager → production pollution | Provide explicit `snapshot_manager` instance or mock |
| Missing `tmp_path` parameter | Can't create isolated directories | Add `tmp_path` to test function signature |

### Validation Checklist

Before committing new tests, verify:

- [ ] Test function has `tmp_path` parameter
- [ ] All storage components use `tmp_path` subdirectories
- [ ] No hardcoded paths to `~/.claude_code_search`
- [ ] Fixtures used instead of manual instantiation
- [ ] Unit tests mock production components
- [ ] Test cleanup is automatic (via `tmp_path` or teardown)

### Verification Command

Run this command to detect production directory access:

```bash
# Run tests and check for production directory artifacts
pytest tests/unit/ tests/fast_integration/ -v
ls -la ~/.claude_code_search/graphs/
ls -la ~/.claude_code_search/merkle/

# Should see: "No such file or directory" (good!)
# If you see test artifacts, tests are polluting production
```

### Related Resources

- **Fixture Definitions**: `tests/conftest.py` lines 261-302
- **Example Fixes**:
  - `tests/fast_integration/test_type_annotation_integration.py` (lines 26, 290)
  - `tests/unit/test_incremental_indexer.py` (line 119)
  - `tests/slow_integration/test_direct_indexing.py` (line 117)

## Automatic Cleanup of Orphaned Test Projects

### Overview

After each pytest session, orphaned test projects — and their merkle trees — are automatically cleaned up via the `pytest_sessionfinish` hook. This prevents test artifacts from accumulating in `~/.claude_code_search/projects/` and `~/.claude_code_search/merkle/`.

**Why This Matters:**

- Tests create project indices and merkle snapshots for incremental indexing
- Test projects point at pytest's temporary directories (`tmp_path`), which are deleted after the test run
- Without automatic cleanup, the resulting orphaned project entries — and their merkle trees — accumulate over time
- Manual cleanup is error-prone and easy to forget

### How It Works

The cleanup system runs automatically after every pytest session:

1. **Automatic trigger**: Runs after every pytest session (unit, integration, or full suite)
2. **Silent operation**: No output on success, only warnings on errors/timeouts
3. **Safe cleanup**: Only removes projects whose `project_path` no longer exists on disk — real projects are left untouched
4. **Timeout protection**: 30-second timeout to prevent blocking test completion

### Implementation Details

| Component | Location | Purpose |
| ----------- | ---------- | --------- |
| **Hook** | `tests/conftest.py` → `pytest_sessionfinish()` | Triggers cleanup after tests |
| **Script** | `tools/cleanup_orphaned_projects.py` | Removes projects whose `project_path` no longer exists, along with their merkle trees |
| **Mode** | `--auto` flag | Silent non-interactive execution |
| **Exit codes** | 0 (passed) or 1 (some failures) | Only runs on test completion |

**Hook Implementation** (`tests/conftest.py` lines 154-197):

```python
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clean up test-created project indices and merkle trees after test session.

    Only runs cleanup_orphaned_projects.py which safely identifies test projects by
    checking if their project_path still exists. Test projects point to temporary
    directories (pytest's tmp_path) that are deleted after tests, so they can be
    safely cleaned up along with their merkle trees.

    NOTE: cleanup_stale_snapshots.py is NOT run automatically because it identifies
    "stale" snapshots by checking for missing indices, not by checking if the original
    project path exists. This could incorrectly delete merkle trees for real projects
    if their indices were temporarily affected by tests.
    """
    if exitstatus in (0, 1):
        orphan_cleanup_script = (
            Path(__file__).parent.parent / "tools" / "cleanup_orphaned_projects.py"
        )
        if orphan_cleanup_script.exists():
            subprocess.run(
                [sys.executable, str(orphan_cleanup_script), "--auto"],
                capture_output=True,
                text=True,
                timeout=30,
            )
```

`tools/cleanup_stale_snapshots.py` (below) is a separate, **manual-only** tool. It is deliberately not run automatically: it judges staleness by missing indices rather than by a missing project path, which could delete a real project's merkle trees if its index was temporarily affected by a test run.

### Manual Cleanup

For manual cleanup or debugging:

```bash
# Interactive mode (shows details, asks for confirmation)
.venv/Scripts/python.exe tools/cleanup_stale_snapshots.py

# Auto mode (silent, for scripts/CI)
.venv/Scripts/python.exe tools/cleanup_stale_snapshots.py --auto
```

**Interactive mode output:**

```
======================================================================
Merkle Snapshot Cleanup Utility
======================================================================

Scanning for stale snapshots...
Found 50 stale snapshot files (49.5 KB)

Stale snapshots by project:
----------------------------------------------------------------------

Project ID: abc123...
  Models: qwen3, bge-m3
  Dimensions: 768d, 1024d
  Files: 4
  ...

Delete all stale snapshots? [y/N]:
```

### Troubleshooting

If cleanup warnings appear after tests:

- **`[Cleanup] Warning: Snapshot cleanup timed out`**
  - Cleanup took >30 seconds
  - Many stale files (run manual cleanup to see count)
  - Solution: Run `python tools/cleanup_stale_snapshots.py` manually

- **`[Cleanup] Warning: Snapshot cleanup failed: <error>`**
  - Script failed to execute
  - Check Python path and permissions
  - Solution: Verify `.venv/Scripts/python.exe` exists

### Verification

To verify cleanup is working correctly:

```bash
# Check stale snapshots before test run
ls ~/.claude_code_search/merkle/

# Run tests (cleanup runs automatically after)
pytest tests/unit/test_merkle.py -v

# Verify stale files were removed
ls ~/.claude_code_search/merkle/
```

**Expected behavior:**

- Before tests: May see orphaned snapshots from previous runs
- After tests: Only snapshots for currently indexed projects remain

### Disabling Automatic Cleanup

If needed for debugging, you can temporarily disable the hook:

1. **Comment out hook** in `tests/conftest.py`:

   ```python
   # def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
   #     """Clean up stale Merkle snapshots after test session completes."""
   #     ...
   ```

2. **Or skip specific tests** that create many snapshots:

   ```bash
   pytest tests/ -k "not merkle" -v
   ```

## Coverage Requirements

### Target Coverage by Component

| Component | Target Coverage | Priority |
| ----------- | ---------------- | ---------- |
| **Core search logic** | >90% | Critical |
| **MCP server tools** | >85% | High |
| **Language parsing** | >85% | High |
| **Evaluation framework** | >80% | Medium |
| **Error handling** | >75% | Medium |
| **Utility functions** | >70% | Low |

### Generating Coverage Reports

```bash
# HTML coverage report (recommended)
pytest tests/ --cov=. --cov-report=html
# View: htmlcov/index.html

# Terminal coverage report
pytest tests/ --cov=. --cov-report=term-missing

# XML coverage report (for CI)
pytest tests/ --cov=. --cov-report=xml

# Fail if coverage below threshold
pytest tests/ --cov=. --cov-fail-under=80
```

### Coverage Analysis

```bash
# Show missing lines
pytest tests/ --cov=. --cov-report=term-missing

# Coverage for specific modules
pytest tests/ --cov=mcp_server --cov=search --cov-report=html

# Branch coverage (more comprehensive)
pytest tests/ --cov=. --cov-branch --cov-report=html
```

## Pre-commit Testing

### Quick Validation Checklist

```bash
# 1. Run fast tests first (unit + fast integration, < 3 min)
pytest tests/unit/ tests/fast_integration/ -q

# 2. Run specific feature tests
pytest tests/unit/test_hybrid_search.py tests/slow_integration/test_hybrid_search_integration.py

# 3. Fast test suite with coverage (skip slow tests)
pytest tests/ -m "not slow" --cov=. --cov-fail-under=75

# 4. Full test suite with coverage (includes slow tests, ~15 min)
pytest tests/ --cov=. --cov-fail-under=75
```

### Automated Pre-commit Hook Example

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit tests..."

# Fast unit tests
echo "1. Running unit tests..."
pytest tests/unit/ -q --tb=no
if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed!"
    exit 1
fi

# Fast integration tests
echo "2. Running fast integration tests..."
pytest tests/fast_integration/ -q --tb=no
if [ $? -ne 0 ]; then
    echo "❌ Fast integration tests failed!"
    exit 1
fi

# Coverage check (excluding slow tests for speed)
echo "3. Checking coverage..."
pytest tests/ -m "not slow" --cov=. --cov-fail-under=75 -q --tb=no
if [ $? -ne 0 ]; then
    echo "❌ Coverage below threshold!"
    exit 1
fi

echo "✅ All pre-commit tests passed (slow tests skipped)!"
echo "💡 Run 'pytest tests/' for full validation including slow tests"
```

## Debugging Failed Tests

### Common Debugging Commands

```bash
# Run with detailed output
pytest tests/failing_test.py -v --tb=long

# Drop into debugger on failure
pytest tests/failing_test.py --pdb

# Show local variables in traceback
pytest tests/failing_test.py --tb=auto -vvv

# Run only failed tests from last run
pytest tests/ --lf

# Show output from print statements
pytest tests/failing_test.py -s
```

### Debugging Strategies

#### 1. Import Errors

```bash
# Test imports specifically
pytest tests/unit/test_imports.py -v

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify module structure
python -c "from mcp_server import server; print('Import successful')"
```

#### 2. CUDA/GPU Issues

```bash
# Test CUDA detection
pytest tests/integration/test_cuda_detection.py -v

# Force CPU mode
pytest tests/ --cpu-only

# Check GPU availability
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

#### 3. File System Issues

```bash
# Check permissions
pytest tests/integration/test_encoding_validation.py -v

# Use temporary directories
pytest tests/ --basetemp=/tmp/pytest_temp
```

#### 4. Mock-related Issues

```bash
# Run without mocks (integration focus)
pytest tests/integration/ -v

# Debug mock calls
pytest tests/unit/test_component.py -v -s
```

#### 5. Regression Test Issues

```powershell
# Run MCP configuration validation
tests\regression\test_mcp_configuration.ps1

# Test specific config file
tests\regression\test_mcp_configuration.ps1 -ConfigPath "C:\path\to\.claude.json"

# Check Claude Code configuration
.venv\Scripts\python.exe scripts\manual_configure.py --validate-only
```

**Common regression test failures:**

- Missing 'args' or 'env' fields in `.claude.json`
- Incorrect PYTHONPATH configuration
- Invalid Python executable paths
- Wrong working directory in MCP config

### Troubleshooting Checklist

- [ ] **Environment**: Virtual environment activated and dependencies installed
- [ ] **Imports**: All required modules can be imported
- [ ] **Permissions**: Read/write access to test directories
- [ ] **GPU**: CUDA drivers and PyTorch compatibility
- [ ] **Memory**: Sufficient RAM for test operations
- [ ] **Network**: Internet access for model downloads (if needed)
- [ ] **MCP Config**: Valid `.claude.json` with required fields (run regression tests)

## Flaky Test Detection

**Flaky tests** are tests that pass or fail inconsistently without any code changes. They can be caused by timing issues, random data, external dependencies, or test ordering problems.

### Detecting Flaky Tests

Use the flaky test detection script to run tests multiple times:

```bash
# Run all unit tests 5 times
./scripts/test/detect_flaky_tests.sh 5 tests/unit/

# Run specific test module 10 times
./scripts/test/detect_flaky_tests.sh 10 tests/unit/chunking/

# Run fast integration tests 3 times
./scripts/test/detect_flaky_tests.sh 3 tests/fast_integration/
```

**Output**:

- ✅ All tests passed across N runs - no flaky tests detected
- ❌ Tests failed - potential flaky tests or genuine failures

### Identifying Flaky Tests

Signs of flaky tests:

- Test passes sometimes, fails other times (no code changes)
- Different results on different machines
- Failures appear random or timing-dependent
- Test fails in CI but passes locally (or vice versa)

### Common Causes and Fixes

| Cause | Example | Fix |
| ------- | --------- | ----- |
| **Random Data** | `random.randint()`, `uuid.uuid4()` | Use fixed seeds or deterministic data |
| **Timing Issues** | `time.sleep()`, async operations | Use explicit waits with timeouts |
| **External Dependencies** | Network calls, file system | Mock external dependencies |
| **Test Ordering** | Tests depend on previous tests | Use isolated fixtures with `tmp_path` |
| **Global State** | Shared class variables | Reset state in fixtures or use `autouse=True` |
| **Resource Cleanup** | File handles, GPU memory | Use context managers and cleanup fixtures |

### Marking Flaky Tests

If a test is legitimately flaky and cannot be easily fixed, mark it with the `@pytest.mark.flaky` decorator:

```python
import pytest


@pytest.mark.flaky(reruns=3, reruns_delay=1)
def test_potentially_unstable():
    """Test that may fail intermittently due to external factors."""
    result = external_api_call()
    assert result is not None
```

**Note**: This requires `pytest-rerunfailures` plugin:

```bash
pip install pytest-rerunfailures
```

### Best Practices

1. **Fix, Don't Mark**: Always try to fix flaky tests before marking them
2. **Document Why**: Add comments explaining why a test is flaky
3. **Use Deterministic Data**: Avoid random values in tests
4. **Mock External Calls**: Don't rely on network, filesystem, or time
5. **Isolate Tests**: Each test should be completely independent
6. **Clean Up Resources**: Always close handles, clear GPU memory

### Example: Fixing a Flaky Test

**Before (Flaky)**:

```python
import random


def test_random_selection():
    data = [1, 2, 3, 4, 5]
    result = random.choice(data)
    assert result == 3  # Flaky: only passes 20% of the time
```

**After (Fixed)**:

```python
import random


def test_random_selection():
    random.seed(42)  # Fixed seed for determinism
    data = [1, 2, 3, 4, 5]
    result = random.choice(data)
    assert result == 4  # Always passes with seed 42
```

## Continuous Integration

### CI-Friendly Test Commands

```bash
# Fast CI pipeline (unit + fast integration, < 3 min)
pytest tests/unit/ tests/fast_integration/ --cov=. --cov-fail-under=75

# Fast test run (skip slow tests using marker)
pytest tests/ -m "not slow" --cov=. --cov-fail-under=75

# Full test suite with XML output (includes slow tests, ~15 min)
pytest tests/ --cov=. --cov-report=xml --junit-xml=test-results.xml

# Parallel execution (fast tests only)
pytest tests/unit/ tests/fast_integration/ -n auto --dist=loadfile

# Parallel execution (all tests)
pytest tests/ -n auto --dist=loadfile
```

### CI Pipeline Strategies

These two illustrative pipelines are hypothetical — actual CI is one workflow,
`branch-protection.yml` (see "Measuring and gating coverage" above and "Codecov integration"
below for what it actually runs and gates).

**Fast Feedback Pipeline** (runs on every commit, < 3 min):

- Unit tests (~5s)
- Fast integration tests (~2 min)
- **Total time**: ~3 minutes
- **Purpose**: Quick feedback for developers

**Comprehensive Pipeline** (runs on PR/nightly, ~15 min):

- All unit tests
- All fast integration tests
- All slow integration tests
- Coverage check with `fail_under = 73` threshold (`[tool.coverage.report]` in
  `pyproject.toml` — the single gate; see "Measuring and gating coverage" above)
- **Total time**: ~15 minutes
- **Purpose**: Complete validation before merge

### CI Configuration Examples

#### Fast Feedback Workflow

```yaml
# .github/workflows/fast-tests.yml
name: Fast Tests

on: [push]

jobs:
  fast-tests:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run unit tests
      run: pytest tests/unit/ --cov=. --cov-report=xml -v

    - name: Run fast integration tests
      run: pytest tests/fast_integration/ --cov=. --cov-append --cov-report=xml -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: fast-tests
```

#### Comprehensive Validation Workflow

```yaml
# .github/workflows/comprehensive-tests.yml
name: Comprehensive Tests

on:
  pull_request:
  schedule:
    - cron: '0 2 * * *'  # Run nightly at 2 AM

jobs:
  comprehensive-tests:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run all tests
      run: pytest tests/ --cov=. --cov-report=xml --junit-xml=test-results.xml -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: comprehensive-tests

    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: test-results.xml
```

### Performance Testing in CI

```bash
# Quick performance validation (fast integration)
pytest tests/fast_integration/test_token_efficiency_workflow.py --benchmark-only

# Comprehensive performance testing (slow integration)
pytest tests/slow_integration/test_full_flow.py::TestFullSearchFlow::test_performance_with_large_codebase -v

# Memory usage testing (all tests)
pytest tests/ --memory-profile

# Time-limited testing (fast tests only)
timeout 180 pytest tests/unit/ tests/fast_integration/

# Time-limited testing (all tests)
timeout 900 pytest tests/
```

## Best Practices Summary

### For Test Writers

1. **Write tests first** (TDD approach when possible)
2. **Use descriptive names** that explain the behavior
3. **Keep tests simple** and focused on one concept
4. **Mock external dependencies** in unit tests (especially model loading)
5. **Use real interactions** in integration tests
6. **Test both success and failure paths**
7. **Include edge cases** and boundary conditions
8. **Use subset validation for metadata** (don't assume exact matches)
9. **Import Mock explicitly** from unittest.mock
10. **Create regression tests for critical bugs**
11. **Use testing utilities**: Leverage `tests/testing_utils.py` for hardware requirements, output capture, and environment mocking
12. **Skip GPU tests gracefully**: Use `@require_torch_gpu` decorator for GPU-dependent tests
13. **Capture and verify logs**: Use `CaptureLogger` to test logging output

### For Test Maintenance

1. **Run tests frequently** during development
2. **Keep test data current** with code changes
3. **Refactor tests** when refactoring production code
4. **Monitor coverage trends** over time
5. **Update fixtures** when APIs change
6. **Document complex test scenarios**
7. **Review recent fixes** for lessons learned
8. **Update regression tests** when configuration changes

### For CI/CD

1. **Run fast tests first** for quick feedback
2. **Use parallel execution** for speed
3. **Generate coverage reports** for analysis
4. **Fail fast** on critical test failures
5. **Archive test results** for historical analysis
6. **Include regression tests** in CI pipeline
7. **Validate configuration** before deployment

### Recent Test Improvements

#### 2026-01-14: Testing Utilities and Phase 2 Call Graph

**All 1,065 tests now passing:**

- ✅ **Professional Testing Utilities** (based on HuggingFace Transformers):
  - `tests/testing_utils.py` - Reusable decorators and context managers
  - Hardware requirement decorators (`@require_torch`, `@require_torch_gpu`)
  - Output capture utilities (`CaptureStdout`, `CaptureLogger`, etc.)
  - Environment mocking (`@mockenv`, `mockenv_context`)
  - 11 comprehensive tests validating all utilities
  - Complete documentation in `README_TESTING_UTILS.md`
- ✅ **Mock Embedding Result Factory Fixture**:
  - New `mock_embedding_result_factory` fixture in `tests/conftest.py`
  - Factory pattern for creating mock `EmbeddingResult` objects without full chunking pipeline
  - Deterministic embeddings based on chunk_id hash
  - Supports call graph testing with `calls` and `relationships` parameters
  - Reduces test boilerplate and ensures consistent mock structure
- ✅ **Phase 2 Call Graph Edge Resolution**:
  - 4 new tests for call target resolution in `test_hybrid_search.py`
  - Tests verify unique function name resolution, ambiguous names, external calls
  - 100% pass rate with no regressions

#### 2025-11-19: Core Test Suite Stabilization

**All 389 tests passing:**

- ✅ Fixed BM25 metadata handling with subset validation
- ✅ Fixed CUDA detection disk space assertions
- ✅ Added proper Mock imports to all test files
- ✅ Added public load() method to CodeIndexManager
- ✅ Added SentenceTransformer mocking to prevent downloads
- ✅ Created comprehensive MCP configuration regression test (15 checks)
- ✅ **Phase 4 Import Resolution Tests** (v0.5.15):
  - `test_import_resolution.py` - 26 unit tests for import extraction and resolution
  - `test_import_resolution_integration.py` - 11 integration tests for end-to-end import resolution

This comprehensive testing guide ensures high-quality, maintainable code through systematic testing practices and clear documentation.

---

## Testing Infrastructure (2026-06 overhaul)

### Summary of changes

| Area | Before | After |
| ------ | -------- | ------- |
| pytest config | `pytest.ini` (legacy) | `[tool.pytest.ini_options]` in `pyproject.toml` |
| Import mode | `prepend` (default) + manual `sys.path.insert` in conftest | `importlib` + `pythonpath = ["."]` |
| New markers | — | `gpu`, `e2e` |
| New test deps | — | `pytest-randomly`, `pytest-xdist`, `syrupy` |
| Coverage config | None | `[tool.coverage.*]` in `pyproject.toml` (branch coverage) |
| CI install | `pip install` | `uv sync --locked` (matches local `uv.lock`) |
| CI lint gate | non-blocking (`continue-on-error: true`) | `ruff` blocking; `pyrefly` blocking (verified green 2026-06-30); `pre-commit` non-blocking |
| CI pre-commit | not enforced | `uvx pre-commit run --all-files` in CI |

### Order-randomization (Phase 2 — pytest-randomly)

`pytest-randomly` is now a declared test dependency. Use it to expose hidden ordering dependencies:

```bash
# Run unit tests with randomised order (different seed each time)
bash scripts/test/run_tests.sh tests/unit -p randomly

# Reproduce a failure with a specific seed
bash scripts/test/run_tests.sh tests/unit -p randomly --randomly-seed=<N>

# Verify order-independence: 20 consecutive randomised runs
for i in $(seq 1 20); do
    bash scripts/test/run_tests.sh tests/unit -p randomly -q || break
done
```

Any test that fails under randomisation is an ordering dependency — fix the root cause (typically
global state not reset between tests). The autouse fixtures `reset_global_state`,
`_redirect_test_storage`, and `_no_real_storage_pollution` protect the main globals and the real
`~/.claude_code_search` storage tree, but new state mutations need function-scoped teardown.

### Measuring and gating coverage

Coverage config lives in `pyproject.toml` `[tool.coverage.*]`. Branch coverage is on.

**Single gate, not two.** Earlier revisions of this guide documented two separate coverage gates
(`pyproject.toml`'s `fail_under` for the full suite, plus a CI-only `--cov-fail-under` CLI flag in
`branch-protection.yml`) that could silently disagree. The CLI flag was removed in `7a751fb` — CI
now runs `pytest tests/ --ignore=tests/slow_integration/ --cov --cov-branch` with no
`--cov-fail-under` override, so pytest-cov falls back to `[tool.coverage.report] fail_under` in
`pyproject.toml`. That one number is the single source of truth, and it is measured against the
**CI-shaped run** (`--ignore=tests/slow_integration/`), not the full suite — `tests/slow_integration/`
runs only in the separate weekly job (`weekly.yml`, Phase 11) and is never part of this gate.

**Baseline (measured 2026-08-04, Phase 11.4 of the hardening campaign):**

- CI-shaped, `--ignore=tests/slow_integration/`: **75.03%** (5,762 passed, 1 skipped, 3
  pre-existing failures unrelated to coverage scope — see "Current Test Status" above) →
  `fail_under = 73` in `[tool.coverage.report]`.
- This is a drop from the prior 83.52%/`fail_under = 81` baseline (2026-08-03), not a regression
  in the tests themselves: Phase 11.3 added `tools` to `[tool.coverage.run] source` so that its
  two existing test files (`test_safe_clear_index.py`, `test_cleanup_stale_snapshots.py`) would
  actually count toward the gate. That honestly surfaced 7 of `tools/`'s 9 files (~4.5k lines of
  CLI/batch scripts) as having zero test coverage, which they always did — the old baseline just
  never measured them. `codecov.yml` deliberately excludes `tools/**` from its patch gate for the
  same reason; this whole-repo floor is now the only place `tools/`'s coverage is tracked at all.

(Previous baselines: 82.59%/81 combined incl. slow_integration and 81.69%/80 CI-only, both
2026-07-26 — obsolete under the single-gate model above, kept here only as history. 78.53%/77
combined, 2026-06-30, predates the two-gates-differ correction that revision made.)

```bash
# Re-measure the number this gate actually uses (matches CI exactly, no --cov-fail-under
# override — pytest-cov reads fail_under from pyproject.toml):
bash scripts/test/run_tests.sh tests/ --ignore=tests/slow_integration/ \
  --cov --cov-branch --cov-report=term-missing
```

Ratchet upward: when coverage improves, bump `fail_under` in `pyproject.toml` from a fresh
CI-shaped measurement, with a comment recording the date, the measured percentage, and the
passing-test count. Never gate on the full-suite (incl. `slow_integration/`) number — CI never
produces it, so a gate on it can never actually trip.

**Phase 9 coverage additions:** `tests/unit/mcp_server/test_metrics.py` (`SessionMetrics` was at 0%
coverage — a small, zero-mock, deterministic class with no prior tests at all) and
`tests/unit/mcp_server/test_tool_registry.py` (`build_tool_list()` / `_advanced_tools_enabled()` were
at 35%, exercised only incidentally through integration tests). Both are pure in-memory logic with no
I/O beyond `monkeypatch.setenv`, so no mocking was needed. Remaining low-coverage modules
(`mcp_server/guidance.py` 34%, `mcp_server/server.py` 62%, `mcp_server/resource_manager.py` 54%,
`search/searcher.py` 54%, `search/bm25_index.py` 64%) were left untouched — they need async/process-
boundary mocking to test properly, which is a larger, separate effort than this ratchet pass.

### Snapshot / golden-file regression testing (Phase 4 — Syrupy)

`syrupy` is a declared test dependency. Use it for deterministic complex outputs:
pure metric functions, formatter outputs, MCP tool-handler responses.

**Existing snapshot tests:**

- `tests/unit/evaluation/test_metrics_snapshot.py` — `calculate_metrics_from_results` and
  `aggregate_metrics` (9 snapshots)
- `tests/unit/mcp_server/test_search_results_snapshot.py` — `_format_search_results` (4 snapshots)

Snapshot files live in `__snapshots__/` dirs next to each test module and are committed to the
repo. They are diffable JSON (via `JSONSnapshotExtension`) so diffs in PR reviews are human-readable.

#### Fixture pattern (used in this project)

Override the `snapshot` fixture per module to force JSON extension — do not rely on the default
`.ambr` format:

```python
import pytest
from syrupy.extensions.json import JSONSnapshotExtension


@pytest.fixture
def snapshot(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)


def test_some_output(snapshot):
    assert compute_thing() == snapshot  # stored as JSON, one file per test
```

#### Workflow

**First run (generate snapshots):**

```bash
# Generate snapshots for a new test file:
bash scripts/test/run_tests.sh tests/unit/evaluation/test_metrics_snapshot.py \
  --snapshot-update -q

# Then commit the generated __snapshots__/ files along with the test file.
```

**Normal run (no flag needed — snapshots are in the suite):**

```bash
bash scripts/test/run_tests.sh tests/unit/evaluation/test_metrics_snapshot.py -q
# "N snapshots passed." printed by syrupy if all match
```

**After intentional output change — regenerate:**

```bash
bash scripts/test/run_tests.sh tests/unit/evaluation/test_metrics_snapshot.py \
  --snapshot-update -q
# Then review the diff before committing:
git diff tests/unit/evaluation/__snapshots__/
```

#### Reading a snapshot diff

When a snapshot test fails, syrupy prints a unified diff between the stored JSON and the new
output. Example (truncated):

```
AssertionError: snapshot does not match
+ {"mrr": 0.85, "ndcg@5": 0.72, ...}
- {"mrr": 0.80, "ndcg@5": 0.72, ...}
```

`+` is the new value, `-` is the stored value. Review the diff to decide:

- **Expected change** (intentional refactor) → `--snapshot-update` and commit
- **Regression** (metric formula broken) → fix the code, do not update

#### Masking volatile fields

For outputs with timestamps, UUIDs, or absolute paths, mask with `path_type`:

```python
from syrupy.matchers import path_type


def test_with_timestamp(snapshot):
    assert result == snapshot(
        matcher=path_type({".*timestamp.*": (str,), ".*path.*": (str,)})
    )
```

The pure-function targets in this project have no volatile fields — masking is not needed for
existing snapshot tests.

#### Guidelines

- Snapshot tests run in the normal suite with no separate marker (no `@pytest.mark.snapshot`).
- Keep the set small: a handful of high-value pure functions, not every handler.
- Do NOT snapshot heavily-mocked handlers — mock identity dominates the output, not real behaviour.
- `--snapshot-update` is the only way to update; the flag is intentionally absent from CI.

### Mutation testing (Phase 4.2 — periodic, not per-commit)

Engines: **cosmic-ray** (local Windows, config-driven) + **mutmut** (Linux CI,
`workflow_dispatch`-triggered via `.github/workflows/mutation-testing.yml`).

**Governing rule:** mutation testing payoff is inversely proportional to mock density. Only target
pure deterministic cores (zero or near-zero mocks). Do NOT run mutation tests on heavily-mocked
orchestration shells — they test the mocks, not the logic.

#### Tier 1+2 targets (zero-mock deterministic cores)

| Target | Total | Killed | Pragmaed | Genuine survivors | Score |
| -------- | ------- | -------- | ---------- | ------------------ | ------- |
| `chunking/relationships/call_edge_resolver.py` | 56 | 40 | 16 | 0 | **100%** |
| `search/reranker.py` | 529 | 265 | 261 | 0 | **100%** |
| `evaluation/metrics.py` | 581 | 183 | 181 | 1 | **99.5%** |

Score = killed / (killed + genuine survivors). Incompetent and pragmaed mutations are excluded.

`search/reranker.py` pragmas cover: `__init__` default params, `analyze_fusion_quality` body,
`tune_parameters` body, `_calculate_std` body — none affect ranking output. Genuine ranking-math
mutants (lines 66, 68, 88) are killed by precision tests.

`evaluation/metrics.py` pragmas cover: magnitude guards (`> 0` / `!= 0` when value ≥ 0 always),
`round(x, 4)` display-precision constants, `False` defaults when key always present, k-literal
constants in metric labels (5, 7, 10), `while`-condition `<` vs `!=` equivalence for monotonic
index, pointer-advance tie-break `<` vs `<=` for equal endpoints in merged inputs. The 1 remaining
item is a confirmed-killed transient false positive (cosmic-ray `NumberReplacer` on L290,
`merge_ranges` `prev_end + 1`; `test_adjacent` kills it in isolation — verified manually).

#### Local run workflow (cosmic-ray)

```bash
# Per-target session (gitignored configs/sqlite live in project root)
uv run cosmic-ray init cr-<target>.toml cr-<target>.sqlite
uv run cosmic-ray baseline cr-<target>.toml
uv run cr-filter-pragma cr-<target>.sqlite                   # mark # pragma: no mutate lines BEFORE exec
uv run cosmic-ray exec cr-<target>.toml cr-<target>.sqlite   # sequential, not parallel
uv run cr-report cr-<target>.sqlite
```

Windows gotcha: `test-command` must use the absolute venv path, not bare `python`:

```toml
test-command = "D:/claude-context-local/.venv/Scripts/python.exe -m pytest <paths> -q --no-header --tb=no"
```

`subprocess.run(['python', ...])` resolves to system Python via Windows App Paths registry even
when the venv is first in PATH. See `cr-*.toml` (gitignored) for the per-target configs.

#### CI run (mutmut on Linux)

Trigger via `Actions → Mutation Testing (Periodic) → Run workflow`. Select `target` (default:
`all`). The workflow installs dev+test+callgraph extras, runs baseline, then one mutmut step per
target. Artifacts: `.mutmut-cache` (14 days retention).

#### Tier 3 targets (de-mocked; mutation runs in progress / complete)

De-mocked 2026-06-30 — `FakeMetadataStore` + real `SearchConfig`/`RerankerConfig` dataclasses
replace MagicMock; `_session_oom_detected` drives real methods without patching:

| Module                        | Status                | Score              |
|-------------------------------|----------------------|-------------------|
| `search/centrality_ranker.py` | **complete** (2026-07-01) | **100.0%** (199/199) |
| `search/reranking_engine.py`  | **complete** (2026-07-01) | **100.0%** (56/56) |

**`search/centrality_ranker.py`** — 511 mutations total (185 incompetent, 199 killed,
0 survived, 127 pragma-skipped). 10 kill-tests cover all genuine mutants (including
`Div_FloorDiv` in `_apply_size_normalization` via non-divisible `chunk_lines=75, target=50`).
127 `# pragma: no mutate` trailing-inline markers for equivalents (precision `round()`,
unreachable defaults, untestable exception paths, log-only arithmetic, boundary operators
that differ only at exact float equality, CPython-interned string `is`/`==`).

**`search/reranking_engine.py`** — 170 mutations total (8 incompetent, 56 killed,
0 survived, 103 pragma-skipped, 3 NO_TEST for type-annotation `|` union operators).
All pragmas use trailing-inline format (`code  # pragma: no mutate`) required by
`cr-filter-pragma`'s `end_pos_row` check. Covered equivalents: `TYPE_CHECKING` AddNot,
`except ImportError` ExceptionReplacer, VRAM arithmetic `NumberReplacer`/`GtE→Gt`,
type-union annotation operators, OOM detection `And/Or/AddNot/TrueWithFalse`, timing
log-only arithmetic, and other GPU/mock-boundary paths.

#### De-mocking backlog (deferred)

These modules have irreducibly high mock density — mutation testing payoff is near-zero without
first extracting pure scoring cores or building in-memory fakes for heavy dependencies:

| Module | Mock count | Deferral rationale |
|--------|-----------|-------------------|
| `search/hybrid_searcher.py` | ~133 | Pure orchestrator over FAISS/BM25/embedder boundaries — no in-memory fakes exist for these backends. Pure logic was already extracted to sibling modules (`ego_graph_retriever`, `graph_scoring_stage`). Revisit only if a future refactor extracts another pure scoring core. |

### Deferred improvements (trigger thresholds documented here)

| Improvement | Add when |
| ------------- | ---------- |
| `pytest-xdist -n auto` per job | per-runner wall-clock > ~5 min |
| `pytest-split` sharding across runners | per-runner wall-clock > ~10 min after xdist |
| Python 3.12 matrix | validated clean on 3.11 + meaningful new-version diff |
| Combined cross-runner coverage | matrix sharding is added |
| `pyrefly` blocking gate | ✅ **DONE** 2026-06-30 — `continue-on-error` removed; pyrefly exits 0 on development |
| `pre-commit` blocking gate | `uvx pre-commit run --all-files` exits 0 on CI |
| Mutation testing (periodic) | already added; re-run before releases or after major test refactors |

When adding `pytest-split`: use `--splitting-algorithm least_duration` (compatible with
`pytest-randomly`); commit `.test_durations` to repo; re-run `--store-durations` after major suite
changes.

### Codecov integration (Phase 3 CI scaffolding 2026-06-30; `codecov.yml` added Phase 11, 2026-08-03)

`codecov/codecov-action@v5` is wired into `branch-protection.yml` (test job, development branch only).
CI emits `--cov-report=xml`; the XML is uploaded after each run including on coverage-gate
failures, so regressions remain visible on Codecov. The README badge tracks the `development` branch.

`codecov.yml` at the repo root configures two status checks, both distinct from the
`pyproject.toml` `fail_under` whole-repo floor described above:

- **`patch` — blocking.** Target 80% coverage on changed lines only (not the whole repo);
  `threshold: 0%` means no slack below target; `if_ci_failed: error` fails the check if the
  CI run itself failed. This is the gate that actually blocks a PR on coverage — a PR is
  blocked only for regressions it introduces on the lines it touches, not pre-existing gaps
  elsewhere.
- **`project` — informational only.** `target: auto` makes this a true ratchet (it re-baselines
  to whatever the current measured total is, ±0.5% threshold) rather than a hand-maintained
  number; `informational: true` means it never blocks merges, just reports drift.
- **`ignore: ["tests/**", "scripts/**", "tools/**"]`** — none of these count toward either
  Codecov status. `tools/**` is the same set of mostly-untested CLI scripts that dragged the
  `pyproject.toml` whole-repo floor down in Phase 11.3/11.4 above; excluding it from `patch`
  means new `tools/` code isn't held to the 80%-on-changed-lines bar, but the whole-repo
  `fail_under` floor is still the only place its coverage is tracked at all.

**Notes:**

- `fail_ci_if_error: false` — Codecov outages or missing token never fail the CI gate.
- `pyrefly` is now a **blocking gate** (2026-06-30) — `continue-on-error` removed after verified green.
- `pre-commit` remains `continue-on-error: true`; flip to blocking when it exits 0 consistently on CI.

### Integrity-gap remediation (Phases 10–12 — 2026-08-04)

The 2026-06 overhaul above (Phases 1–9) built the scaffolding — config, order-randomization,
coverage gating, snapshot/mutation testing. Phases 10–12 closed a different class of problem:
places where the suite *reported* protection it did not actually provide.

| Area | Before | After |
| ------ | -------- | ------- |
| Flaky-run detection | `detect_flaky_tests.sh` looped a single test file only | `--suite-loop` mode loops the whole tier, randomized order, to surface cross-test ordering flakes |
| `test_index_write_stage.py` flake | documented as an open, tolerated flake since 2026-07-26 | closed as unreproducible (22+ clean randomized whole-suite runs); Phase 10.4's unconditional singleton reset is the plausible incidental fix |
| `test_clear_index_clears_bm25_and_dense` | quarantined (skipped) | un-quarantined, passing |
| `_reset_singleton_state()` | conditional imports, could silently no-op | unconditional imports |
| Real-home-storage guard (`_no_real_storage_pollution`) | attributed any external write in `~/.claude_code_search` to whichever test happened to be running (misattributed a live MCP server's own writes to the test suite) | process-local write ledger (wraps `os.replace`/`os.rename`/`Path.mkdir`); failure message names the actual writing call site |
| `mock_snapshot_manager_for_unit_tests` | patched `SnapshotManager` at its definition module only — silently bypassed by every module that imports the class eagerly (`incremental_indexer.py`, `index_write_stage.py`, `status_handlers.py`, `change_detector.py`, `merkle/__init__.py`) | patches `SnapshotManager.__init__`, the attribute every holder shares regardless of import style |
| BM25 mock-config order dependency (seed `811371831`) | unexplained, order-dependent `MagicMock` attribute-visibility failures in `test_index_sync.py`/`test_hybrid_search.py` | root-caused and fixed (Phase 10.6) |
| `tests/slow_integration/` (107 tests) | never ran in any automated job | weekly CI job (`.github/workflows/weekly.yml`), first-ever automated run confirmed 107 passed/1 skipped |
| `tests/fast_integration/test_mmap_cleanup.py` | gitignored — silently excluded from every run and from git history | untracked from `.gitignore`, committed, running |
| `[tool.coverage.run] source` | omitted `tools/` (4.5k lines, 0% measured) | includes `tools/`; honestly surfaced 7 of 9 files as untested |
| `fail_under` (`pyproject.toml`) | 81, measured before `tools/` was in scope | re-baselined to 73 against the honest 75.03% CI-shaped measurement |
| Coverage gate architecture | described as "two gates, two numbers" (`pyproject.toml` + CI `--cov-fail-under`) | CI's `--cov-fail-under` CLI flag removed (`7a751fb`); `pyproject.toml`'s `fail_under` is the single source of truth |
| `codecov.yml` | did not exist; doc claimed "relying on Codecov defaults" | added — blocking `patch: 80%` (changed-line) gate + informational `project: auto` ratchet, `tools/**`/`scripts/**`/`tests/**` ignored |
| This doc's numbers | several stale (pre-`tools/`-inclusion coverage %, pre-weekly-job slow_integration status, fictional "no codecov.yml") | reconciled against `pyproject.toml`, `branch-protection.yml`, `weekly.yml`, `codecov.yml` (Phase 12.1) |

**Pitfall generalized from Phase 10.5:** `unittest.mock.patch()` (and `patch.object`) rebinds a
name in **one namespace** — the module you point it at. `patch("pkg.module.ClassName")` only
affects code that looks up `pkg.module.ClassName` at call time (e.g. a lazy `import pkg.module`
inside a function, then `pkg.module.ClassName(...)`). Any module that already did
`from pkg.module import ClassName` at its own import time holds an independent local binding —
patching the original module does not touch it, and the mock silently fails to apply with no
error raised. This generalizes beyond `SnapshotManager`: before trusting a `patch()` target,
check every import site (`grep -rn "import ClassName\|from .* import.*ClassName"`) for `from X
import Y` style imports, not just `import X` style. Two fixes, in order of preference: (1) patch
the attribute/method every holder shares regardless of import style — `patch.object(ClassName,
"__init__", ...)` rather than replacing the class reference itself; (2) if the class reference
itself must be swapped, patch it at every eager-import call site, not just the definition
module. A fixture docstring claiming to patch "all import locations" is itself worth verifying —
Phase 10.5 found one that was wrong.
