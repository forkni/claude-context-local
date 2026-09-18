# LSP Stage-3 resolver tier goes live on the bge-m3 lineage

Status: accepted
Date: 2026-09-14

## Context

`lsp_enabled: true` has been the shipped default in `search_config.json` since the Stage-3
resolver (`basedpyright-langserver`, `ResolverConfidence.LSP = 0.98`) was built, but the `[lsp]`
extra had never been installed on this development machine — every index log carried a silent
"lsp resolver unavailable" line, and the tier had never actually run against this repo's own
index. Commit `2779916a` installed the extra (`basedpyright==1.39.10`) and confirmed the tier
dispatches: a force reindex moved the resolver mix from two tiers to three, adding 113 new call
edges and upgrading 1,847 existing edges to `confidence=0.98`. That commit's scope was
"install + verify only" — it explicitly did not run a retrieval A/B, leaving the tier's effect on
`search_code` ranking quality unmeasured.

A same-day attempt to close that gap concluded "LSP is retrieval-neutral, PASS on all three
views" and began being written up as canon. That conclusion was **not supportable**: the user
challenged it directly ("review actual queries, they could be stale" / "I don't believe LSP could
make recall worse"), and investigation found the gate's control (captured 13:43:36) and treatment
(captured 18:37:37) legs spanned a commit (`2779916a` itself, plus `CHANGELOG.md` /
`docs/INSTALLATION_GUIDE.md` / `pyproject.toml` edits) that changed the indexed corpus between
legs — 2,991 vs 2,992 chunks. Different corpus means different BM25 IDF statistics, different
dense neighbourhoods, and different PageRank mass; the two legs differed by more than the LSP
tier. 17 of 63 queries (27%) had different `retrieved` lists between legs — more churn than 113
new edges alone should plausibly cause. That gate's deliverables were reverted.

Three further defects were found and fixed as part of re-measuring cleanly (see the governing
plan, `error-log-13-happy-quasar.md`, and their own commits):

1. Benchmark result artifacts recorded no substrate information (`config_metadata` was just
   `{project_path, k, category_filter, split_filter}`) — nothing in the JSON could have caught the
   corpus drift that produced the confounded gate.
2. `[FILTER_SEMANTICS]` warning: a legacy `project_info.json` with a missing
   `filter_semantics_version` field read back as `None`, which the old `is not None` check treated
   as "not stale" — excluding exactly the legacy projects the migration was meant to catch, so the
   warning could never clear itself.
3. The LSP availability guard silently produced zero edges on a server that initialized but didn't
   advertise `callHierarchyProvider`, with no diagnostic distinguishing that from "no calls found."

## Decision

Ship the LSP Stage-3 resolver as **on by default** (`lsp_enabled: true`, unchanged from its prior
default), backed by a clean, same-corpus retrieval gate rather than the confounded one.

### Substrate fingerprinting (`scripts/benchmark/run_sscg_benchmark.py`)

`config_metadata` now records `total_chunks`, `files_indexed`, per-`resolver_source` edge counts,
`embedding_model`/dimension, `git_sha`/dirty flag, and the resolved `lsp_enabled`/`resolvers`. A
`--compare` guard prints a prominent `[CONFOUND]` warning naming any mismatched field between the
two result files being compared, so a cross-substrate comparison can no longer pass silently.

### The clean gate

A single campaign, code frozen, both legs indexed back-to-back with `CLAUDE_AUTO_REINDEX=0` /
`PYTHONHASHSEED=0`, output written outside the indexed tree until capture was complete (the exact
discipline that was missing the first time — writing benchmark JSONs into `evaluation/` between
legs is itself a corpus-drift vector). Leg A (`lsp_enabled: false`) and leg B (`lsp_enabled: true`)
both landed at **238 files / 2,998 chunks** — verified identical before any comparison was trusted
(the substrate-fingerprint guard fired on none of the three paired comparisons that followed).

Full results and the Q56 single-query investigation: `evaluation/CANON_20260914B_LSP_REBASELINE.md`.
Gate: `|ΔMRR| ≤ 0.02` and `Δrecall@20 ≥ −0.02` (or not statistically distinguishable from that
band), all three views — **PASS**:

| view | ΔMRR | Δrecall@20 |
|---|---|---|
| 63q canonical | −0.0116 | −0.0115 |
| 133q expanded | −0.0058 | −0.0205 (CI touches zero; single-query harness artifact, not a regression) |
| F-via-similar (63q) | −0.0136 | −0.0093 |

`search/config.py`'s `lsp_enabled` field now carries a `benchmark_locked` citation to this gate,
matching the pattern already used for `resolvers` (ADR-0022's benchmark-lock mechanism) — turning
the tier off is now a human decision that must cite a reason, not a silent config edit.

## Consequences

- The LSP tier ships on, with a real (not assumed) retrieval-neutrality measurement behind it —
  113 new call edges and 1,847 confidence upgrades to `0.98`, no measurable ranking harm.
- The original "LSP made recall worse" finding was corpus drift, not a real effect. The user's
  skepticism was correct and prevented an incorrect conclusion from being published as canon.
- Benchmark artifacts now self-attest their substrate; this confound class (silently comparing
  two different corpora) is caught automatically going forward via `--compare`'s `[CONFOUND]`
  guard, not just for LSP-related gates.
- A benchmark-harness artifact was found during the Q56 investigation: a specific combination of
  `k=10` and full-batch query execution deterministically excludes a query's top-ranked gold from
  the reported top-10, even though the same query in isolation (or at `k=50`, in or out of batch)
  correctly ranks it first. This is reproducible and deterministic (not GPU/reranker flakiness —
  two independent full-batch re-runs matched to 4 decimal places), but its root cause (a
  k-dependent candidate-pool composition effect) was not chased further; it explains the 133q
  view's one borderline metric and is filed as a follow-up bug, not blocking this gate.
- Three gold-dataset defects (Q56, Q70, Q94) found during this investigation are corrected
  separately, after this pin, as a declared comparability break — not folded into this gate so the
  A/B stays clean.

## Out of scope

- Root-causing the k/batch-dependent benchmark-harness artifact itself.
- `centrality_boost_factor` / `centrality_boost_cap` tuning — the `centrality_reranking: false`
  ablation run during this investigation was not a clean isolation (it degrades overall quality
  broadly, not selectively) and was not decisive; not pursued further here.
- Gold-dataset corrections (Q56/Q70/Q94) — tracked as a separate, declared comparability-break
  re-pin.
