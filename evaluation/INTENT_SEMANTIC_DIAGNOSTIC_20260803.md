# Semantic intent classification diagnostic (2026-08-03)

**Script**: `scripts/benchmark/test_semantic_intent.py --no-retrieval --confidence-threshold 0.4`
(Part A only — classification comparison, no searches, no index writes). Embedder confirmed bound
(`_get_searcher` → real `searcher.search_executor.embedder`; confidence deltas are non-zero
throughout, not the all-`changed:false` signature of a silent `None`-embedder fallback).

Run against both golden sets:

- `evaluation/golden_dataset.json` (77 queries + 8 novel) →
  `evaluation/intent_semantic_diagnostic_63q.json`
- `evaluation/golden_dataset_expanded.json` (145 queries + 8 novel) →
  `evaluation/intent_semantic_diagnostic_131q.json`

These are the **full** dataset files, not the harness's `canon_C3` 63q/131q filtered subsets —
counts (85 and 153 total classified) don't line up with `canon_C3` and aren't meant to.

## Result

**4 of 77 SSCG queries changed classification** on both runs (same 4 IDs, byte-identical
confidence values — the two golden files share these query IDs, so this is one finding, not two).
Zero novel-phrasing changes (all 8 novel queries classify identically on/off; keyword scoring
already handles the synonym cases they were designed to probe).

| Query | Text | off → on | conf off → on | `params_on` |
|---|---|---|---|---|
| Q04 | "validate chunk id format" | hybrid → local | 0.20 → 0.44 | `{k:5, search_mode:hybrid}` |
| Q05 | "normalize file path separators" | hybrid → local | 0.20 → 0.44 | `{k:5, search_mode:hybrid}` |
| Q31 | "how does HybridSearcher combine BM25 and semantic search" | hybrid → global | 0.20 → 0.44 | `{k:10, search_mode:hybrid}` |
| Q34 | "how does FaissVectorIndex store embeddings" | hybrid → global | 0.20 → 0.44 | `{k:10, search_mode:hybrid}` |

Avg confidence delta across all classified queries: **-0.0315** (63q) / **-0.0179** (131q) — i.e.
semantic scoring is mildly conservative overall; these 4 are the outliers that cross the `0.4`
gate upward.

## Live-production read

`params_on` for each changed query, checked against the redirect gate
(`search_orchestrator.py:140-232`, `confidence >= 0.4`):

- **Q04/Q05 → LOCAL, k=5**: no live effect. LOCAL's `suggested_params["k"]` is read nowhere —
  the redirect gate only fires on `intent == GLOBAL` (`search_orchestrator.py:209`). This is the
  same dead code C1 targets for removal; this run is empirical confirmation it's unreachable, not
  just statically dead.
- **Q31/Q34 → GLOBAL, k=10, confidence 0.44 ≥ 0.4**: **live effect**. The redirect fires
  (`suggested_k=10 > base_k`), so in production these two queries would search at `k=10` instead
  of the caller's default (`k=4`) whenever `semantic_enabled=True` — which is the current
  production default (`config.py:570-576`). This is the one concrete, measurable behavioural
  delta semantic intent scoring introduces over keyword-only scoring on this golden set.

## Gate verdict (per plan)

Per the plan's gate: semantic-on **does** change classifications (4/77, non-zero) and **does**
enable one live redirect class (GLOBAL k-bump, not ego-graph — no query in either set crosses into
`ego_graph_enabled` this run). That clears the bar for "semantic-on changes something measurable,"
but the entire effect is two queries picking up a wider `k`, not a new retrieval mode. No MRR
number is claimed here — a benchmark capture isolating the Q31/Q34 k=10 effect could be proposed as
a follow-up with that as its stated hypothesis, but is out of scope for this diagnostic run.

## Caveat inherited from the script itself

Part B (retrieval comparison) was skipped (`--no-retrieval`, as directed) and would not have been
authoritative if run — its `_apply_intent_params` mirror is missing the redirect legs added to
`search_orchestrator.py` since it was written (see the docstring note added alongside this run,
commit `8deacbe`). The `params_on` GLOBAL-k-bump read above comes directly from the classifier's
own `suggested_params` output, not from that stale mirror, so it is not subject to that caveat.
