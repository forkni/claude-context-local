# Shared interface for offline retrieval probes: `evaluation/probe_harness.py`

Status: accepted
Date: 2026-08-17

## Context

`scripts/benchmark/probe_*.py` is a family of read-only diagnostic scripts (never production code)
used to measure retrieval-funnel behaviour before proposing a config change — leg-search depth,
fusion-cut membership, hop-1 rerank demotion, and so on. Each one is built to answer one question and
then either gates a change or gets filed as a rejected/deferred disposition (see the project's A/B
campaign history in `evaluation/*_AB_*.md` and the memory index). By 2026-08-17 the family had grown
to 27 scripts, and `evaluation/probe_harness.py`'s own module docstring records the hand-copying this
had produced by the time it was written:

- 23 independent `sys.path.insert(0, ...)` bootstraps.
- 5 near-identical `load_queries` golden-set loaders.
- 25 hand-rolled `ArgumentParser`s, 14 of them pointing at the same
  `evaluation/golden_dataset_expanded.json` default path.
- 14 separate `get_searcher()` constructions.
- Unguarded `SearchConfig` mutations with no script restoring the config afterward.
- Two independent rerank-instrumentation adapters (`probe_final_pool_reserve.py`'s
  `instrument_rerank` and `probe_duplicate_crowding.py`'s `Instrumentation` class) that had converged
  on the same design without either knowing about the other.

The load-bearing failure mode, not just duplication: **two live copies of the hop-1 funnel-width
arithmetic** (`search_k = max(reranker_budget, k * 5)`) had already drifted from
`search/search_executor.py`'s actual production formula, which reads
`config.search_mode.leg_search_multiplier` rather than a hardcoded `5`. A probe re-deriving that
arithmetic locally silently reports the wrong `search_k` for any project whose base
`search_config.json` (first hit in `search/config_paths.py`'s `CONFIG_PATH_CANDIDATES`, gitignored
per-machine) or ADR-0014 `search_overrides.json` layer pins a non-default multiplier — exactly what
this project's own live `search_config.json` did at the time this module was written (see "A
concrete drift bug" below). A probe that measures the wrong funnel width invalidates whatever gate
it was built to support.

## Decision

Build `evaluation/probe_harness.py` as the shared seam every probe should route through, modeled on
`evaluation/arm_overrides.py`'s shape (module-level functions plus small data carriers, no DI
container — ADR-0005). It replaces hand-copying with:

- `ensure_pinned_hash_seed()` — moved from `scripts/benchmark/run_sscg_benchmark.py`, the ADR-0021
  determinism guard (re-exec with `PYTHONHASHSEED=0` when unset; re-exec only under `__main__`, never
  at import time).
- `GoldenQuery` / `load_golden_queries(dataset, query_ids=None, exclude_categories=("D",),
  require_grades=True)` — one loader replacing five, grades pre-normalized via
  `evaluation.metrics.normalize_chunk_id`.
- `probe_parser(description)` — one parent `ArgumentParser` owning every probe's common flags
  (`--dataset`, `--project-path`, `--k`, `--query-ids`, `--json`, `--set`).
- `resolve_dataset_path`, `write_probe_json` — the verbatim-repeated dataset-path resolution and
  JSON-output one-liner.
- `open_probe(args)` / `ProbeSession` — searcher construction plus `--set` override apply/restore
  built on `evaluation.arm_overrides` (`apply_overrides`, `requires_rebuild`, `parse_set_flags`)
  rather than reimplementing config validation.
- `ProbeSession.replay_legs(query, k=None, depth=None)` — hop-1 leg replay at the actual production
  width, via `search.search_executor.leg_search_depth` / `fused_pool_cut` (never a re-derived
  literal). Single depth per call by design; probes needing raw legs re-cut at multiple depths in one
  pass (`probe_leg_depth_fusion.py`, `probe_stable_misses.py`) call the raw
  `executor.search_bm25`/`search_dense` and keep their own fusion closure local instead.
- `ProbeSession.instrument()` — the rerank-interception adapter the two independent originals above
  both reinvented.

**Migration is a shrink-only ratchet, not a rewrite.** `tests/unit/evaluation/test_probe_hygiene.py`
pins `BASELINE_SYS_PATH_BOOTSTRAP_COUNT` and `BASELINE_LOCAL_LOAD_QUERIES_COUNT` at the pre-harness
tallies and asserts today's counts never exceed them; a `MIGRATED_PROBES` set additionally asserts
that any script claimed as migrated has no bootstrap, no local loader, and does reference
`probe_harness`. Four beachhead probes were migrated onto the seam this round:

| Probe | Commit |
|---|---|
| `probe_tm2c2_fusion.py` | `a08bd24` |
| `probe_final_pool_reserve.py` | `551a28d` |
| `probe_leg_depth_fusion.py` | `2bef68c` |
| `probe_stable_misses.py` | `131cead` |

`scripts/benchmark/run_sscg_benchmark.py`'s own local `_ensure_pinned_hash_seed` copy — the original
this function was moved from — was retired in favor of importing `probe_harness.ensure_pinned_hash_seed`
(`c145d79`), removing the last independent copy of the determinism guard.

**Two scripts are permanently excluded, not just not-yet-migrated:**

- `probe_duplicate_crowding.py` — untracked, actively-changing WIP ("two hats": don't refactor code
  someone is mid-edit on). `test_never_migrate_probes_are_not_claimed_as_migrated` /
  `test_never_migrate_probes_still_exist` guard this exclusion so it can't silently lapse.
- `probe_rerank_window.py` — a third, out-of-scope instrumentation adapter.
  `probe_leg_depth_fusion.py`'s `fidelity_check` depends on its own, richer `Instrumentation` API that
  `ProbeSession.instrument()` does not (yet) replicate.

The remaining 19 `scripts/benchmark/*.py` files (of 27 total) still hand-roll their own bootstrap —
that is the current `BASELINE_SYS_PATH_BOOTSTRAP_COUNT`. Migrating them is future work, one probe at a
time, gated by the same ratchet.

## A concrete drift bug the migration surfaced, not introduced

Migrating `probe_stable_misses.py` replaced its hand-copied
`search_k = max(reranker_budget, hop1_k * 5)` with `leg_search_depth(config, hop1_k)`. That retired
formula was *latent*, not wrong in general — numerically correct only while
`leg_search_multiplier == 5`.

At migration time (2026-08-17) this machine's live **base config**,
`<repo-root>/search_config.json` (gitignored, `search/config_paths.py`'s first
`CONFIG_PATH_CANDIDATES` entry, resolved independently of process cwd), pinned
`search_mode.leg_search_multiplier = 1` — left over from that day's cross-system Arm-B
duplicate-crowding benchmark runs (`SESSION_LOG.md`'s 2026-08-17 session entry;
`evaluation/CROSS_SYSTEM_RESULTS_OURS_ARM_B_R1_20260817.md`), not from the ADR-0014
`search_overrides.json` per-project layer, which carries no `search_mode` key at all and so did
nothing to restore the default on merge. The retired formula therefore reported `search_k=100` for a
`k=10` query (`hop1_k = k * multi_hop.initial_k_multiplier = 20`) while the actual deployed funnel
ran `search_k=30` — a real, silent 3.3x over-report in the hand-copied arithmetic, not a migration
regression. Verified via a structured before/after JSON diff against Q119/Q121/H063
(`PYTHONHASHSEED=0`, identical `--query-ids`/flags on the pre- and post-migration script, no `--set`
needed since the pin lived in the base config both times): every `dense`/`bm25`/`fused_deep` rank
(derived at the depth-independent `probe_depth=200`) was byte-identical; only `search_k` and the
miss-classes gated on it changed, fully explained by this one formula fix. This is exactly the
failure mode the module docstring's "load-bearing failure" line names — now with a live reproduction
instead of a hypothetical.

The pin was restored to the adopted default `5` on 2026-08-18 once this section's evidence was
captured (`evaluation/LEG_DEPTH_FUSION_AB_20260815.md`'s verdict keeps it there) — a reader checking
`search_config.json` today will find `5`, not `1`. The bug was real and reproducible at the time;
its trigger has since been cleared, and the harness now derives `search_k` from whatever value is
live instead of drifting from it.

## A packaging gotcha the migration surfaced

`.venv/Lib/site-packages/__editable__.claude_context_local-0.25.0.pth` makes `chunking`, `embeddings`,
`evaluation`, `graph`, `mcp_server`, `merkle`, `search`, and `utils` importable as top-level packages
regardless of invocation method or working directory — but **`scripts` is not in that map**. Any probe
that cross-imports a sibling under `scripts.benchmark.*` (only `probe_leg_depth_fusion.py` does this,
pulling `ALPHAS`/`fuse_tm2c2`/`rank_of`/`theoretical_min_max_normalize` from
`probe_tm2c2_fusion.py`) must be invoked as `python -m scripts.benchmark.probe_leg_depth_fusion` —
module-form invocation inserts the repo root into `sys.path[0]`, which a direct file invocation
(`python scripts/benchmark/probe_leg_depth_fusion.py`) does not do once the old `sys.path.insert`
bootstrap is removed. Probes that only import from `evaluation`/`search`/etc. are unaffected either
way. Documented in that script's own Usage docstring rather than reintroducing a bootstrap that would
trip the ratchet.

## Verification

- `ruff check` / `ruff format --check` clean on every touched file.
- `pyrefly check` clean on `evaluation/probe_harness.py` and all four migrated probes; the two
  findings the migration surfaced were resolved directly rather than left as noise:
  - `probe_stable_misses.py`'s `getattr(r, "chunk_id", None) or r["chunk_id"]` fallback was flagged
    `bad-index` once the migrated `probe_query`'s typed `session: ProbeSession` parameter let pyrefly
    narrow `searcher.search(...)`'s return to `list[SearchResult]` (a dataclass with no
    `__getitem__`) — the original's untyped `searcher` parameter had suppressed this check entirely.
    `SearchResult.chunk_id` is a required `str` field, so the dict-index fallback was dead code;
    simplified to `r.chunk_id`.
  - `write_probe_json(args.json_out, reports)` passed a bare `list[dict[str, Any]]` where the
    signature declared `dict[str, Any]` — `probe_stable_misses.py` deliberately keeps its JSON output
    a bare list (unlike the other three migrated probes' `{"summary": ..., "reports": ...}` shape) to
    stay comparable across the before/after capture above. Fixed by widening
    `write_probe_json`'s signature to `dict[str, Any] | list[Any]` rather than changing the probe's
    output shape.
- `tests/unit/evaluation/test_probe_hygiene.py` — all 8 hygiene tests pass, including the
  ratchet-bites sanity check (`test_ratchet_bites_on_a_reintroduced_bootstrap`) and the two-hats/
  out-of-scope exclusion guards.
- `./scripts/test/run_tests.sh tests/unit/ tests/fast_integration/ -q` — 6104 passed, 1 skipped (full
  suite, after the `run_sscg_benchmark.py` hash-seed migration).
- `run_sscg_benchmark.py --help` smoke-tested both with `PYTHONHASHSEED` already set (no re-exec) and
  unset (re-exec branch fires, re-execs with `PYTHONHASHSEED=0`, then runs) — both paths work
  identically to the retired local copy.
- Each probe migration additionally ran a live functional invocation
  (`.venv/Scripts/python.exe -m scripts.benchmark.<name> --project-path . --query-ids ...`) producing
  sane output before being committed.

## Consequences

- Four probes and `run_sscg_benchmark.py` now share one hop-1-arithmetic, one loader, one parser, and
  one determinism guard with production — future probes drift with `search_executor.py` automatically
  instead of needing a second hand-edit.
- The ratchet (`test_probe_hygiene.py`) prevents any *new* script from reintroducing a bootstrap or
  local loader without failing CI, and prevents `MIGRATED_PROBES` from silently including
  `probe_duplicate_crowding.py` or `probe_rerank_window.py`.
- 19 of 27 `scripts/benchmark/*.py` files remain unmigrated; each future migration is expected to
  follow the same pattern (route hop-1 arithmetic through `leg_search_depth`/`fused_pool_cut`, loader
  through `load_golden_queries`, parser through `probe_parser`, keep any multi-depth or
  richer-instrumentation logic the harness doesn't support local, verify via before/after capture
  rather than assuming byte-identity).
- `ProbeSession.instrument()` does not yet replicate `probe_rerank_window.py`'s richer
  `Instrumentation` API — closing that gap is a prerequisite for ever migrating either
  `probe_rerank_window.py` or `probe_leg_depth_fusion.py`'s `fidelity_check` off its direct dependency
  on it.
