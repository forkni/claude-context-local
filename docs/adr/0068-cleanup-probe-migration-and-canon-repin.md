# Cleanup, probe-harness migration, and the owed canon re-pin

Status: accepted
Date: 2026-09-07

## Context

A `/improve-codebase-architecture` handoff named the probe/instrumentation seam (C5) as the next
target. Re-verifying it against the live index with the MCP search tools changed the answer: C5 is
a poor next target (the handoff undercounted the interception mechanisms — six exist, not four —
and its stated payoff contradicted its own stated scope), two of the handoff's loose-end claims did
not hold (`_NEVER_DROP_FILTERED_KEYS` is not triplicated; the incremental embed→add path's missing
try/except is deliberate, not an oversight), and — the load-bearing finding — **a canon re-pin was
already owed independent of anything else being built**: [ADR-0067](0067-widen-find-similar-code-exclude-same-file-starvation.md)
landed the same day, moved the indexed substrate (+12 chunks), and gated on paired bit-identity
rather than a re-pin, leaving `evaluation/CANON_20260906_REBASELINE.md` (measured on 2,956 chunks)
stale by construction.

This ADR closes three items from that corrected review in one sitting, landed as three commits so
each step gates independently:

1. **Cleanup** (`cec770b5`) — five verified-dead symbols deleted (zero callers/reads repo-wide):
   `graph/graph_storage.py`'s `get_graph()`, `mcp_server/tools/search_handlers.py`'s
   `_get_index_manager_from_searcher`, `ExecutionOutcome.index_manager`,
   `RerankingEngine.__init__`'s unused `embedder`/`metadata_store` parameters, and
   `SearchExecutor.gpu_monitor`. Plus doc-accuracy fixes: `search/graph_view.py`'s ADR citation
   (`ADR-0001/0005/0006` → the correct `ADR-0051`, duplicated at
   `tests/unit/search/test_graph_scoring_stage.py:189`) and `docs/adr/0065-*.md`'s
   `_NEVER_DROP_FILTERED_KEYS` wording (one constant, not three — a differently-named sibling exists
   at `mcp_server/output_formatter.py`, not a triplication).

   Deleting `_get_index_manager_from_searcher` broke a golden-set assertion:
   `evaluation/golden_dataset.json`'s Q68 (`expected_primary`/`relevance_grades`) pointed at that
   exact chunk_id as "the helper that bridges the MCP orchestrator to the index manager." Repaired
   both golden datasets to point Q68 at
   `mcp_server/tools/searcher_view.py:decorated_definition:SearcherView.index_manager` (grade 3) —
   the actual surviving bridge, since `_get_index_manager_from_searcher` was exactly a one-line
   delegation to it. This changes what the re-pin below scores against; priced in, not a new
   confound.

2. **Probe migration** (`1122254d`) — `scripts/benchmark/probe_reserve_depth.py` moved onto
   `evaluation/probe_harness.py` (ADR-0040's shared seam) for golden-query loading, CLI parsing,
   dataset-path resolution, and searcher/config lifecycle, in place of its own hand-rolled
   versions. `tests/unit/evaluation/test_probe_hygiene.py`'s `BASELINE_SYS_PATH_BOOTSTRAP_COUNT`
   ratchet dropped 19 → 18 (it had been sitting on its ceiling since the denominator grew 27 → 36).
   The migration also fixed a latent config-leak: the pre-migration script applied
   `bm25_reserved_slots: 0` for its reserve=0 head capture and never restored it, leaking the
   override into any later in-process caller; the migrated `capture_fused_head` now snapshots and
   restores the field.

3. **Canon re-pin** (this ADR) — absorbs both commits' substrate drift plus ADR-0067's, in one
   re-pin rather than three.

## Decision

Full non-incremental reindex + the standard three-view sequential benchmark capture
(`CLAUDE_AUTO_REINDEX=0`, `PYTHONHASHSEED=0`, MCP `cleanup_resources` before the force reindex,
`audit_golden_dataset.py` CLEAN gate on both datasets before capture) — the same protocol every
canon re-pin since 2026-09-01 has used. Full results, gate, and delta table live in
`evaluation/CANON_20260907_REBASELINE.md`; summary:

| Dataset | MRR | ΔMRR vs 09-06 | Recall@20 | Δrecall@20 vs 09-06 | gate |
|---|---|---|---|---|---|
| 63q canonical | 0.8228 | +0.0077 | 0.8264 | −0.0036 | PASS |
| 133q expanded | 0.6435 | +0.0111 | 0.7724 | −0.0136 | PASS |
| F-via-similar | 0.8657 | 0.0000 | 0.8137 | −0.0021 | PASS |

All three inside the pre-registered ±0.02 MRR band and ≥ −0.02 recall@20 guard; guard-rails
`Overall: PASS` on every leg; 63q determinism bit-identical across two rounds
(`mean_d = +0.0000`, `n_moved = 0` on all 63 shared queries). Substrate: 235 files / 2,965 chunks
(net +9 vs the 09-06 pin's 2,956 — ADR-0067's +12 minus the cleanup commit's five deletions minus
the probe rewrite's own delta).

Read as ordinary substrate drift across the three commits, not an isolated measurement of any one
of them — consistent with every prior re-pin's attribution since 2026-09-01.

## Consequences

- `evaluation/CANON_20260907_REBASELINE.md` supersedes `CANON_20260906_REBASELINE.md` as current
  canon.
- No code changed as part of the re-pin itself — this ADR is a measurement record, not a fix.
- `tests/unit/evaluation/test_probe_hygiene.py`'s `BASELINE_SYS_PATH_BOOTSTRAP_COUNT` ratchet: 18
  (was 19). 12 of 36 `scripts/benchmark/*.py` files remain on the harness
  (`MIGRATED_PROBES`); the rest still hand-roll their own bootstrap.
- Golden dataset Q68 now asserts against `SearcherView.index_manager` in both
  `golden_dataset.json` and `golden_dataset_expanded.json` — a permanent fixture change, not
  specific to this re-pin.

## Out of scope

- **C5, the probe/instrumentation-seam unification** — dropped as a target this sitting (see
  Context); not reopened here. Six interception mechanisms exist, not four; closing the gap would
  buy freeing exactly one cross-import (`probe_leg_depth_fusion.py`'s import of
  `probe_rerank_window.py`'s richer `Instrumentation`) while `probe_rerank_window.py` and
  `probe_leg_depth_fusion.py`'s `fidelity_check` stay permanently excluded from migration by
  design — a large API delta for a small, already-scoped-out payoff.
- **C4** (the `graph/graph_storage.py` 1,230-line class, `storage.graph` call-site census, etc.) —
  diagnosis re-verified this sitting (several of the handoff's exact counts were wrong: 31
  `storage.graph` sites not ~28, 7 `_name_index` maintenance blocks not 5, 0 `storage is None`
  checks in `graph_queries.py` not 11), genuinely needs a full re-pin of its own, not bundled here.
- Remaining `scripts/benchmark/*.py` migrations onto `probe_harness` — one probe per future sitting,
  per the ratchet's own design; `probe_duplicate_crowding.py` and `probe_rerank_window.py` stay
  permanently excluded (see `test_probe_hygiene.py`'s `NEVER_MIGRATE`).
