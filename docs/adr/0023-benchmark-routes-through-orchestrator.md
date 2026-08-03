# Route the SSCG benchmark through SearchOrchestrator

Status: accepted
Date: 2026-08-02

## Context

`run_sscg_benchmark.py` called `HybridSearcher.search()` directly — one layer below the
path the MCP `search_code` tool actually serves (`SearchOrchestrator.run()`). Every
published canon was produced through that seam, and it had already forced two hand-written
replays of production logic:

- `_apply_centrality_stage` — an ~89-line function that re-ran `GraphScoringStage` over
  hand-formatted results after the fact and mapped the reordered dicts back onto the raw
  `SearchResult` objects by `chunk_id`, so the harness could measure centrality blending at
  all.
- ADR-0019's `_IntentWeightReplay` — the measurement basis for a reject-and-delete decision
  on intent-adaptive fusion weights, built because the harness had no other way to exercise
  the intent layer.

`SearchOrchestrator.run()` also gates a `PlanRedirect` branch, GLOBAL-intent `suggested_k`
override, CONTEXTUAL-intent auto-ego-graph, and Block H's source-order/context-budget
truncation — none of which the direct `HybridSearcher.search()` call ever exercised. Fixing
the instrument before refactoring anything it measures was the point of this change.

## Decision

### B1 — swap the call site, intent off

`_run_query` now calls `await orchestrator.run({query, k, search_mode, include_context:
True, max_context_tokens: 0})` instead of `searcher.search(...)`, copying the adapter shape
from `run_mcp_pipeline_eval.py`. `max_context_tokens: 0` disables Block H's context-budget
truncation (its guard is `> 0`), so the harness measures the full ranked list rather than a
presentation-layer-truncated one — MRR keeps meaning "over a ranked list of k".
`search_mode` is always passed as a concrete string, never bare `"auto"`, so
`get_search_mode_for_query` can't re-derive it out from under the harness.

Deployed config has `intent.enabled: true`, so routing through `run()` unconditionally
would also turn on `plan.intent_decision` — a second, unrelated variable changing at the
same time as the call-site swap. `main_async` pins `get_search_config().intent.enabled =
False` for this arm (B1); a later, separate arm (B1b) flips it on to measure the intent
layer's retrieval impact in isolation — the first such measurement, since ADR-0019 only
covered its fusion-weight sibling.

`_apply_centrality_stage` and its two call sites (the scored loop and a cold-start warm-up
query) are deleted outright: `GraphScoringStage` now runs inside every query's own scoring
stage unconditionally, config-driven, exactly like production, so there is no separate
replay stage — and no separate warm-up query — left to run. The `--with-centrality` /
`--centrality-alpha` CLI flags are deleted along with it; every published canon already ran
with `--centrality-alpha 0.0`, matching the deployed `graph_enhanced.centrality_alpha`
default, so centrality becomes unconditional at the same effective value.

The scored loop (`_run_query` → `run_benchmark` → `run_single` → `main_async`) is converted
to `async def`, driven by exactly one `asyncio.run(main_async(args))` call inside a thin
sync `main()` — mirroring `run_mcp_pipeline_eval.py`'s `main()`/`main_async()` split. The
loop is not wrapped in a fresh event loop per query: `orchestrator.run()` offloads work via
`asyncio.to_thread`, and a fresh loop per query would serialize those offloads differently
and perturb the latency numbers being measured.

### Metadata rehydration (not in the original plan text, closes a scoring gap)

`orchestrator.run()` returns thin formatted dicts
(`mcp_server/tools/result_view.py::_format_search_results`) — `file`, `lines` (a
`"{start}-{end}"` string), `kind`, `score`, `chunk_id`, and a few optional fields. Notably
absent: `tags`, which `evaluation/metrics.py`'s community-credit scoring
(`extract_community_id`, `build_file_entries`, `expand_retrieved_with_community_credit`)
reads directly off each result's metadata. Parsing the formatted dict's display strings (as
originally proposed) would have silently degraded `mrr_community_credit` to N/A.

Instead, `_run_query` rehydrates each returned `chunk_id` against the shared searcher's own
`MetadataStore` — the same store `_build_line_lookup` / `_build_community_scoring_lookup`
already read directly, via the same `get_chunk_by_id`-style `.get(chunk_id)["metadata"]`
shape used elsewhere in `search/indexer.py` — and reconstructs full-fidelity
`SearchResult(chunk_id, score, metadata, source)` objects. Every downstream call site
(`raw_ids = [r.chunk_id ...]`, `getattr(r, "metadata", {})`,
`_extract_ranges_from_results`) keeps working unchanged, with full metadata fidelity (line
ranges, community `tags`) instead of degrading to N/A — while the search execution itself
still runs through the real `SearchOrchestrator.run()` pipeline.

### F-via-similar stays on the direct call

`handle_find_similar_code` adds only chunk-ID normalization and default-`k` resolution on
top of `HybridSearcher.find_similar_to_chunk()`, and the harness's F-via-similar path
already does both explicitly. Measurement-identical either way; kept as a documented,
bounded exception rather than an oversight.

### No new side-channel touched

`reranking_engine.last_candidate_ids` and the confound-recorder probes keep working exactly
as before: the harness and `SearchOrchestrator` share the same `get_searcher()` singleton,
so a pure call-site swap has exactly one cause for any canon delta. This side channel is a
documented interface consumed by three other scripts (`probe_stable_misses.py`,
`grade_candidate_queries.py`, `probe_reserve_depth.py`) and two evaluation records — touching
it was explicitly out of scope for this change.

## Consequences

- **Canon break, deliberate.** `canon_B1` (intent off) is not comparable to any prior
  canon — it is the first measurement taken through the real production pipeline instead of
  a one-layer-lower seam. See Verification below for the measured delta.
- **`_maybe_reindex` now fires on every request, not previously exercised.**
  `SearchOrchestrator.run()`'s Block A (`_maybe_reindex`, `search_orchestrator.py:291-331`,
  call site `:778`) runs unconditionally whenever `plan.auto_reindex` is set, gated only by a
  cheap time-based staleness check (`_is_index_stale`, logs `"Auto-reindexing ... (index older
  than 30.0 minutes)"`). The direct `HybridSearcher.search()` call the harness used before B1
  never exercised this path — a gap the originating plan's comparability table didn't list.
  Practical effect: a round started against an index older than 30 minutes pays a reindex
  attempt on top of every query's latency until the index is fresh again, making its latency
  numbers incomparable to pre-B1 canons (which never paid this cost). Both rounds published
  below were run immediately after a full reindex to avoid this.
- **That staleness check surfaced a real, pre-existing bug — found by B1, not caused by it.**
  The first attempt at the two required 63q rounds hit it: Windows' legacy console (cp1252)
  can't encode the Braille glyph rich's `Progress` bar uses
  (`parallel_chunker.py::_progress_context`). `utils.console.get_progress_console()` already
  guards against this by checking `sys.stdout.encoding`, but that check doesn't cover rich's
  `_win32_console.LegacyWindowsTerm` write path, which encodes via the raw Win32 console
  codepage independent of Python's own stream encoding. Every one of round 1's 63 queries found
  the index "stale" per the check above, attempted a reindex, and crashed on this encoding bug
  mid-chunk. `_attempt_recovery`'s `clear_index()` call is not atomic across its FAISS/BM25/
  `metadata.db` deletions, and partially succeeded on 62 consecutive retries — deleting the
  FAISS index binary and all BM25 files while a live handle elsewhere (this repo's own MCP
  server session, still serving the correct in-memory index) kept `metadata.db` locked and
  undeletable. Round 1 itself measured cleanly against a frozen, undamaged substrate the whole
  way through (confirmed via the per-query vector count in its log) and produced a plausible,
  PASSing result — but the wreckage its own failed recovery attempts left behind meant round 2,
  run minutes later, measured against an empty index and returned all-zero metrics. Repaired via
  `cleanup_resources` (releases the MCP server's `metadata.db` handle) followed by a forced full
  reindex (`handle_index_directory({"incremental": False})`, invoked directly — the
  `index_directory` MCP tool itself wasn't available in the repairing session) with the progress
  console's legacy-Windows path disabled for that one repair run only. The repair rebuilt the
  index at a slightly different chunk count (2294 → 2292: `docs/` files were edited between the
  original round 1 and the repair, and `docs/` is not in this project's own exclude list) — an
  expected one-file drift, not further damage. Because round 1's original substrate no longer
  existed after the repair, both published rounds below are a fresh pair, run back-to-back
  against the repaired index rather than reusing the first (otherwise-valid) round 1. This
  crash-then-partial-clear sequence is real, user-facing risk in ordinary auto-reindex use, not
  just a benchmark-harness artifact, and is out of scope for B1 to fix — see Out of scope.
- **`--with-centrality` / `--centrality-alpha` no longer parse.** A handful of historical
  evaluation records (`evaluation/BM25_PATH_AUG_TRACK_D_20260726.md`,
  `EMBEDDER_F2LLM_AB_20260726.md`, `POOL_MISS_DIAGNOSIS.md`,
  `RERANKER_JINAV3_DOC_CAP_20260728.md`, `RERANKER_QWEN3_4B_AB_20260728.md`) record the exact
  CLI invocation used for a past experiment, including these flags. They are left as-is:
  rewriting a point-in-time reproducibility record to use flags that didn't exist at the
  time would misrepresent what was actually run. Readers of those records should substitute
  "centrality always on at config default" when reproducing post-ADR-0023.
- **B1b, P4, A, B2 remain open**, each needing its own plan once `canon_B1` (and later
  `canon_B1b`) exist — see the originating plan's "Out of scope" section.

## Verification

- Full unit suite: 5,546 passed, 2 skipped — includes deleting the 8 `TestApplyCentralityStage`
  tests in `tests/unit/evaluation/test_line_overlap_metrics.py` (the function they exercised
  no longer exists) and no regressions elsewhere.
- Two 63q rounds, `PYTHONHASHSEED=0` (harness self-pins per ADR-0021 when the variable is
  unset), run back-to-back against the freshly repaired index (see Consequences above for why
  the first attempt was discarded and re-run): `sscg_B1_r1_20260802.json` /
  `sscg_B1_r2_20260802.json`.
  - **0 flips.** Aggregate metrics and all 63 per-query rows are identical between rounds
    except `latency_ms` (round-to-round timing noise, not a scoring field) — confirms
    ADR-0021's determinism guarantee holds through the new `SearchOrchestrator.run()` call
    site.
  - **`canon_B1`** (intent off): mrr 0.8249, recall@1 0.278, recall@5 0.6477, recall@7 0.7234,
    recall@10 0.7655, recall@20/50 0.8436, precision@1 0.8254, ndcg@5 0.6771, ndcg@10 0.7311,
    hit_rate@5/7 1.0, pool_hit_rate 1.0 (avg pool 28.8), line_recall 0.9307, line_precision
    0.2282, line_iou 0.2755, file_recall@5 0.83, file_recall@10 0.8831,
    hard_negative_intrusion_rate 0.2593, avg_latency_ms 4399.7 / 4636.9 (r1/r2). Overall: PASS.
  - **Delta vs. pre-B1 canon** (63q μ0.7942, recall@10 0.7795, recall@20 0.8465, pool_hit 1.0):
    mrr +0.0307, recall@10 −0.014, recall@20 −0.0029, pool_hit unchanged at 1.0 — small in both
    directions, as this plan expected. Every prior canon already ran centrality at the deployed
    `centrality_alpha=0.0`, so the delta is attributable to the call-site swap itself (metadata
    rehydration, Block H bypassed via `max_context_tokens: 0`, `intent.enabled=False` so
    `suggested_k`/`PlanRedirect` are not reachable), not to a centrality-replay drift.
- Confirmed no `[CONTEXT_BUDGET] Truncated` line in either round's log — Block H's
  truncation guard is bypassed, not silently cutting.
- `.venv/Scripts/ruff.exe check` + `format --check`: clean on both modified files.
- `pyrefly check`: 2 pre-existing errors on `scripts/benchmark/run_sscg_benchmark.py`
  (`EgoGraphConfig` missing `community_bounded` / `cross_community_penalty` attributes,
  lines untouched by this change) — confirmed present on `development` HEAD before this
  change via `git stash`; not introduced or addressed here.

## Out of scope

- **B1b** — flip `intent.enabled` on, handle `PlanRedirect` responses as a distinct outcome
  rather than a zero score, log `suggested_k != requested k` mismatches. Separate commit.
- **P4** (`RetrievalRequest` → `ReRankingEngine`), **A** (a plan object owning retrieval
  widths), **B2** (deleting the 11 config-mutation sweep shims) — each needs `canon_B1b`
  first, or in B2's case, P4 + A first.
- **Non-atomic `clear_index()`** (`search/indexer.py:785` et al. — FAISS/BM25/`metadata.db`
  deleted as three independent, non-transactional steps) and **the legacy-Windows rich
  console crash** (`utils/console.py::get_progress_console`'s guard checks
  `sys.stdout.encoding`, not the Win32 console codepage rich's `LegacyWindowsTerm` actually
  writes through) — both real, user-facing bugs surfaced by this change (see Consequences),
  neither introduced by it. Worth a GitHub issue each; not fixed here.
