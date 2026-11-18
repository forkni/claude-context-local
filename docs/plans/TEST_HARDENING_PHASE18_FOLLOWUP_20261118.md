# Test hardening, Phase 18: what was done, what is left, and the follow-up brief (2026-11-18)

Status: **Phase 18 (tests and tooling) is finished and on branch `claude/new-session-8bziee`.
The open items below need production-code changes, a Windows run, or a decision.**

Detailed numbers: `tests/TESTING_GUIDE.md` → "Test Suite Audit, Property Tests & Mutation Sweep
(Phase 18 — 2026-11-18)". The full checklist review of four fix commits is in
`docs/reviews/2026-11-18-fix-commit-review.md`. That directory is gitignored, so the findings
that need action are copied into §2.1 below.

Environment the measurements came from: Linux, Python 3.11.15, CPU-only torch 2.11.0, 4 cores,
16 GB RAM, the locked dependency set. Windows-only tests skip there.

---

## 1. Done (Phase 18)

| # | Work | Commit(s) | Evidence |
|---|---|---|---|
| 1 | Synced the `harden-test-suite` scripts into `scripts/`: `scan_test_smells.py` (adds report-only `real-clock`), plus `rank_failures.py`, `replay_fixes.py` and `crap_dry_gate.py`. Fixed the `bitwise-assert` false positive on set intersections (module scope, annotated sets, names built from sets) | `b4c2032` | `tests/unit/tools/test_scan_test_smells.py` (9 cases; dropping module-scope tracking fails 2) |
| 2 | Smell baseline 308 → 307 (gate change, own commit) | `7d68ec8` | the only grandfathered `bitwise-assert` was the false positive |
| 3 | Hypothesis tooling: `hypothesis>=6.116.0` in `[test]`; `ci` / `dev` / `nightly` profiles in `tests/conftest.py`; `uv.lock` entry added by hand | `6d4e128` | `uv lock --check --offline` passes |
| 4 | Phase 4.1: 30 properties on `evaluation/metrics.py`, `RRFReranker.rerank` and `search/chunk_id.py` | `ff11003` | `ci` profile and seeds 1/2/3 green; break-and-revert; one hand mutant (`reserve = reserved_slots`) is caught only by a property |
| 5 | Mutation sweep over 5 cosmic-ray targets. Every survivor was replayed against every covering test, then the real ones got new tests (fusion quality, reserve selection, TM2C2, interleave, rank scores, rerank-skip flags, model-swap direction, process-pool merge, synthetic demotion, metrics cutoffs, aggregates, containment and community credit) | `8fb6802`, `fae8352`, `2301b60`, `a6e3486` | per-target table in TESTING_GUIDE 18.3; about 90 survivors killed, each verified by replaying its mutation diff |
| 6 | Widened 3 `cr-*.toml` test commands to every covering test, with `--hypothesis-profile=ci` (gate change, own commit) | `99b3ee3` | 84 of 99 `reranking_engine` survivors died from scope alone |
| 7 | Regression test for the one fix `replay_fixes.py` reported MISSED (`52614e1`, skipped-rerank race) | `b274d5c` | fails with the fix reverted, passes with it |
| 8 | Audit baseline written into TESTING_GUIDE (coverage 87.94%, 40 functions over CRAP 30, 10/10 random-order runs green, past-fix recall 6/7, smells 307) | `25b6a63`, `cb368d0` | — |
| 9 | Checklist review of `6fd1be8`, `3dcecef`, `4c5d187`, `26b09be` with hand-mutation and a same-bug-class search | not committed (gitignored path) | see §2.1 |

Final state: `tests/unit` 5,524 passed / 25 skipped under random order; the CI-shaped run had
5,620 passed / 26 skipped; ruff and pyrefly (with its baseline) are clean; the smell gate passes.

---

## 2. Remaining, in priority order

### 2.1 Production bugs from the fix-commit review (P1)

1. **The vanished-config fix is lost after every project switch.** `search/config.py` keeps the
   last good file layer in `_last_file_dict` on the `ConfigManager` instance, but
   `invalidate_config_caches()` (`mcp_server/state.py:387`) sets `_config_manager = None` on every
   `switch_project`, `index_directory` and startup restore (`mcp_server/resource_manager.py:342`).
   After any switch, a drive drop reverts silently to `BAAI/bge-m3`. Reproduced.
   Fix: keep the last file layer at module level, as `_indexing_ram_fallback_override` already is.
   Test: load config naming model X, reset the manager, delete the file, expect model X and one
   WARNING.
2. **`save_config` does not refresh the cached layer** (`search/config.py:2722-2744`). A vanish
   after a save restores the pre-save settings, or the defaults if nothing was loaded first.
   Reproduced. Test: load X, save Y, delete the file, expect Y.
3. **The snapshot drop after a partial clear has no test.** Making
   `_drop_snapshot_if_index_changed` a no-op, removing `error.index_changed = index_changed`
   (`search/index_write_lock.py:121`), or removing any one call site
   (`search/incremental_indexer.py:438`, `:654`, `:963`) passes the whole suite. Tests: raise
   `files_in_use_error(..., index_changed=True)` from `clear_index` and assert `delete_snapshot`
   is called; with `index_changed=False`, assert it is not.
4. Same bug class, pre-existing: `mcp_server/tools/index_handlers.py:564-570` (delete project) and
   `:310-348` / the response near `:469` (`_purge_index_dir`) report any `PermissionError` /
   `OSError` as "locked" and put raw `[WinError 32 ...]` text into the response. Route both
   through `files_in_use_guard` / `is_lock_violation` as `26b09be` did.
5. Pre-existing, lower priority: `search/config.py:2489` races `exists()` against
   `stat().st_mtime` (a file vanishing between the two calls raises `FileNotFoundError`);
   `:2483-2487` silently falls back to `search_config.json.example` when only the real file
   vanished; an unreadable per-project `search_overrides.json` is dropped without a warning
   (`:2449-2457`).
6. Test nits: no test for `6fd1be8`'s `except OSError` branch; `test_resolver_applies_the_swap`
   (`3dcecef`) asserts only that a log line is absent; parametrize
   `test_is_lock_violation_reads_the_windows_error_code` with `ids=`.

### 2.2 Mutation gate and pragmas (P1: scheduled CI will fail)

7. `call_edge_resolver` survival is 35% (44 of 107), over `mutation-testing.yml`'s
   `cr-rate --fail-over 25.0`. 33 survivors are annotation mutants on `list[str] | None` at
   `chunking/relationships/call_edge_resolver.py` lines 171, 306, 354. Add
   `# pragma: no mutate` on those lines; the rest are logging-only counters and executor-shutdown
   flags (see TESTING_GUIDE 18.3). Re-run `cr-call_edge.toml` to confirm it drops below 25%.
   `evaluation/metrics.py` L355 (`dict[str, float | bool | None]`, 20 mutants) needs the same.
8. Pragma drift: after `ruff format`, the `# pragma: no mutate` comments in
   `RRFReranker.analyze_fusion_quality` (and possibly elsewhere) sit on closing-paren lines.
   Grep for pragmas on lines that hold only `)` / `]` / `}` and move each onto the line it is meant
   to cover, or delete it where a test now kills the mutant.
9. Re-run all five targets with the widened configs and record the scores in TESTING_GUIDE
   (expected: `reranking_engine` near 3%, `reranker` near 6%, `metrics` near 4%).
10. `search/hybrid_searcher.py` (`cr-hybrid-searcher.toml`) was not run: about 12 h on 4 cores
    (33 of 692 in 35 min). Either run it on a bigger machine or narrow its `module-path` to the
    pure helpers.

### 2.3 Windows-only verification (P2: needs a Windows machine)

11. Run the skipped real-handle lock test `tests/unit/search/test_indexer_clear_index.py:187`.
    `26b09be` counts only WinError 32/33 as locks; confirm that delete-pending or mapped-file
    states do not surface as WinError 5 (see the comments at `search/mmap_vectors.py:212-221`).
12. Regenerate `uv.lock` with a normal `uv lock` (the Hypothesis entry was added by hand because
    `download.pytorch.org` was unreachable) and confirm the diff touches only `hypothesis`.
13. Re-measure coverage on Windows; 87.94% here is with the Windows-only branches skipped.

### 2.4 Coverage and complexity debt (P2)

14. 0%-covered functions over CRAP 30: `MultiLanguageChunker.chunk_directory` (CC 12),
    `TraceCollector._on_call` (10), `GraphQueryEngine.find_all_callers` / `find_all_callees` (9),
    `RelationshipAnalyzer._resolve_type_chunk` (9), `pytest_callgraph._check_guards` (8).
    Triage each one (TEST-VALUE: unit-test hard, integration-test briefly, or delete if dead).
15. Two functions over `max-complexity = 15` without a per-file ignore:
    `chunking/languages/c.py` `extract_metadata` (16) and `search/neural_reranker.py`
    `_load_or_fetch` (16). Split them, or add them to the debt list with a reason.

### 2.5 Suite hygiene (P3)

16. Add `-ra` to `addopts` so skips and xfails are summarised by default.
17. Extend `_check_quarantine` in `tests/conftest.py` with the one-re-date rule (`redated=`,
    unknown-kwarg check), as in the skill's SCAFFOLDING.
18. The 12 report-only `real-clock` findings (`scan_test_smells.py tests -v | grep real-clock`)
    are flake candidates; move them to an injected clock or an event wait.
19. `scripts/rank_failures.py` with a directory input also parses `*.log` / `*.txt`. Keep run
    files in their own directory, or add a `--junit-only` flag.
20. `replay_fixes.py` counted `26b09be` and `4c5d187` as CAUGHT via a pytest *error*, not an
    assertion failure. Check whether the error comes from a missing import or fixture and, if so,
    whether the assertion itself would catch the bug.
21. Not given a property in Phase 4.1: `call_edge_resolver` (orchestration) and
    `centrality_ranker` (3 survivors). Revisit only if a pure core is extracted.

---

## 3. Follow-up brief for the next agent session

Paste this as the opening message of a new session on this repository:

> Continue the test-hardening campaign in this repo (Phase 19). Read
> `docs/plans/TEST_HARDENING_PHASE18_FOLLOWUP_20261118.md` first, then
> `tests/TESTING_GUIDE.md` Phase 18. Work on a new branch from the default branch after
> `claude/new-session-8bziee` is merged (or on top of it if it is not merged yet).
>
> Scope, in this order, one commit per item, gate files (`conftest.py`, `pyproject.toml`
> `[tool.coverage]` / `[tool.pytest]`, `.smell-baseline.json`, `cr-*.toml`, workflows) in their
> own commits:
>
> 1. §2.1 items 1-3: fix the two config-cache bugs in `search/config.py` (keep the last good file
>    layer across manager resets and refresh it on `save_config`) and add the missing
>    snapshot-drop tests for `search/incremental_indexer.py`. Write each test first, show it
>    failing on the current code, then fix. Run `python scripts/replay_fixes.py --fix-commit <sha>`
>    on your own fix commits afterwards.
> 2. §2.1 item 4: route the delete-project and purge-index error paths in
>    `mcp_server/tools/index_handlers.py` through `files_in_use_guard` / `is_lock_violation`, with
>    tests for a WinError 32 (lock) and a WinError 5 (access denied) `PermissionError`.
> 3. §2.2 items 7-8: add `# pragma: no mutate` to the annotation lines named there, fix pragma
>    drift, then re-run `cosmic-ray` for `cr-call_edge.toml` and confirm `cr-rate` is under 25%.
>    Every new pragma needs a one-line reason, as the existing ones have.
> 4. §2.5 items 16-17 (pytest `-ra`, quarantine re-date rule), in one gate commit.
>
> Rules: follow the harden-test-suite skill (classicist tests, mocks only at boundaries, no
> recomputed expectations, every new test passes under `pytest-randomly` seeds 1, 2, 3, and a
> hand-mutation of the line it covers makes it fail). Do not lower `fail_under` (87) or raise
> the smell baseline (307). Run `ruff check`, `ruff format --check`,
> `pyrefly check --baseline pyrefly-baseline.json`,
> `python scripts/scan_test_smells.py tests --baseline .smell-baseline.json` and the unit tier
> before each push. Update `tests/TESTING_GUIDE.md` with a Phase 19 section and a before/after
> table. Leave §2.3 (Windows-only) and §2.4 (coverage debt) unless asked; list them as still open
> at the end.
