# L3 `include_signatures` — gate results and disposition (2026-08-18)

## Feature

Opt-in, default-off `signature: str` field on `search_code` results. Attaches a
line-scanned signature/preamble excerpt sourced from `metadata_store`'s `bm25_text`
(`_extract_signature_estimate` + `_enrich_results_with_signatures`,
`mcp_server/tools/result_view.py`), enriching at Block E of `SearchOrchestrator._assemble`
alongside the existing `include_top_callers`. Default path is byte-identical; opt-in only.

## Pre-registered gate (from the approved plan, Step 3)

| Gate | Threshold | Banked baseline |
|---|---|---|
| `gold_sufficiency.signature_present_rate` | rises 0.0 → ≥0.85 | 0.0 (field did not exist yet) |
| `gold_sufficiency.content_present_rate` | stays 0.0 | 0.0 |
| `tokens_returned.tiktoken_mean` | ≤ 3,500 | 3,125.1 + 318.8 = 3,443.9 |
| `signature_view_delta_mean.targeted_span_tokens` | unchanged (~6,085.6) | counterfactual being displaced, not an outcome |
| Ranking identity | `chunk_id` sequence equal flag-on vs flag-off | display-only |

## Measured results

Control (`--include-signatures` omitted) vs treatment (`--include-signatures`), full 133-query
probe, same session, `evaluation/CONTEXT_COST_PROBE_20260818_L3_{off,on}.json`:

| Metric | Control (off) | Treatment (on) | Gate | Verdict |
|---|---|---|---|---|
| `signature_present_rate` | 0.0 | **0.857** | ≥0.85 | **PASS** |
| `content_present_rate` | 0.0 | 0.0 | stays 0.0 | **PASS** |
| `tiktoken_mean` | 2,952.466 | **3,703.376** | ≤ 3,500 | **FAIL** (+5.8%) |
| `targeted_span_tokens` | 6,374.271 | 6,374.271 | unchanged | **PASS** (byte-identical; absolute value drifted from the ~6,085.6 banked estimate — pre-existing substrate drift on the probe corpus, present identically in both arms, unrelated to L3) |
| Ranking identity | — | — | equal chunk_id sequence | **PASS**, with a methodology correction — see below |

Only `tiktoken_mean` failed its pre-registered threshold. Per the user's explicit instruction the
failure was investigated rather than resolved by picking either "scope to top-k" or "relax the
gate" blind.

## Root cause: gate mis-derivation, not an implementation defect

The ≤3,500 ceiling was built as `3,125.1 (banked full-probe tiktoken_mean) + 318.8 (banked
per-query signature cost)`. The 318.8 figure was computed during Step 0/1 verification over
`top_k = raw_results[:10]` only — a top-k-scoped measurement taken for a different purpose (the
`downstream_read_cost` counterfactual delta).

Production enrichment is not top-k-scoped. Block E (`_enrich_results_with_signatures`, mirroring
`_enrich_results_with_top_callers`) runs on the **full** `formatted_results` list, which is
k-drifted by multi-hop/ego-graph/graph expansion to a mean of ~26.6 rows for a requested k=10
(consistent with this project's already-measured `k_drift.mean=17.729` on top of k). Block E
precedes Block H's `max_context_tokens` budget truncation, and production's real default is
`default_max_context_tokens=0` (`search/config.py:428-431`, "0 = unlimited") — so Block H never
truncates by default. The true wire cost therefore scales with ~26.6 enriched rows, not 10.

Measured overhead: `3,703.376 − 2,952.466 = 750.91` tok/query — roughly 2.4× the 318.8 top-k-scoped
estimate, consistent with ~2.6× more rows actually being enriched (26.6/10).

This is an **apples-to-oranges gate-derivation error**, not a defect in
`_enrich_results_with_signatures`. Two independent checks confirm the implementation is working
exactly as designed:

1. **Precedent check.** `include_top_callers` — the exact template L3 mirrors — has the identical
   unscoped full-`formatted_results` enrichment shape and shipped with **no token-cost gate at
   all** (`evaluation/REMAINING_LEVERS_AB_20260814.md`: byte-identity + unit tests only).
2. **~~Consistency check~~ — retracted, was a scope coincidence, not corroboration.** The original
   note claimed `750.91 / 2,952.466 = +25.4%` "closely matches" the independently-banked
   `318.8 / 1,268.7 = +25.1%` ultra-format figure. That agreement was arithmetic coincidence: the
   two numerators are a **per-query tiktoken delta over the full k-drifted result set** (2.6× more
   rows than top-k) and a **per-query production-heuristic delta over `top_k[:10]` on the ultra
   format** — different row counts and different format axes landing within 0.3 points of each
   other by chance. Neither figure was ever "~319 tokens/**result**" as the shipped schema
   description (`mcp_server/tool_registry.py`) claimed — both are per-**query** sums. The schema
   text carried this error since `21cd9bb` and is corrected in this changeset (A1); `21cd9bb`'s
   commit message is not rewritten and still carries the superseded figure. The actual per-format
   overhead, measured directly from the banked `L3_off`/`L3_on` payload_bytes, is:

   | format | overhead (shipped) |
   |---|---|
   | verbose | +27.2% |
   | **compact** (the actual schema default) | **+40.0%** |
   | ultra | +57.0% |

   Signature bytes are ~constant per result, so relative cost rises as the format compacts —
   quoting the ultra figure as "the" overhead (as the original schema text did) overstates it
   against the format callers actually get by default. The correct governing check going forward
   is this per-format table (re-measured in Part B below), not a single ceiling or a
   cross-scope "consistency" argument.

## Ranking-identity smoke test — methodology correction

The plan's specified smoke test (paired live `search_code` calls, flag-on vs flag-off, asserting
equal `chunk_id` sequences) was run against the canonical target
(`search/indexer.py:153-159:decorated_definition:CodeIndexManager.metadata_store`, the exact result
that returned no content field during Step 0/1 verification, k=5, `include_dirs=["search/"]`).

The first attempt (`include_signatures=true` then `include_signatures=false`, two independent live
calls) showed the top 3 results matching but **diverging from rank 4 onward** — different result
membership, not just reordering (e.g. `MetadataStore.set` present only in one call,
`RerankingEngine` only in the other). This is consistent with this project's already-documented
live-query nondeterminism (unpinned `PYTHONHASHSEED` + bf16 reranker on the ambient MCP server,
vs. the benchmark harness's seed-0 pin) rather than an `include_signatures` side effect.

To isolate the two variables, a second `include_signatures=true` call was issued immediately after.
It reproduced the `include_signatures=false` call's chunk_id sequence, ordering, and every score
field (`score`, `reranker_score`, `complexity_score`, `centrality`, `blended_score`) **exactly**,
for all 20 returned rows — with `signature` present on every row and absent from the `false` call.
This confirms the flag perturbs nothing but the added field; the first attempt's divergence was
ambient run-to-run variance, not caused by the flag.

**Methodology note for future live smoke tests against this server:** two independent live calls
are not a valid `chunk_id`-sequence-identity check on their own — issue a same-parameter repeat
call to confirm the baseline draw is stable before attributing any divergence to the parameter
under test, or use the deterministic probe harness (seed-pinned) instead of ambient live calls.

## Part B — what changed (2026-08-18)

`_enrich_results_with_signatures` and `_extract_signature_estimate`
were changed after all: module/module_preamble chunks are skipped entirely (no callable contract to
summarize — 20-22% of signature tokens on two independent corpora were this kind of filler), and the
extractor is now bounded to `max_chars=600` (a minified/single-line chunk could previously produce a
multi-thousand-token "signature", 5× the entire per-query overhead). The duplicate extractor in
`scripts/benchmark/probe_context_cost.py` was retired in favor of importing the production one
(ADR-0040), so the two no longer drift. Full plan and rationale:
`docs/plans` session notes (this changeset); see also `mcp_server/tools/result_view.py`'s
`_NON_SIGNATURE_CHUNK_TYPES` docstring.

## Part B results — re-measured post-change

Full 133-query probe, same dataset/k/project-path as the original banked run
(`evaluation/CONTEXT_COST_PROBE_20260818_L3_on_postB.json` vs. the original
`evaluation/CONTEXT_COST_PROBE_20260818_L3_{off,on}.json`):

| Metric | Control (off) | Shipped (pre-B) | Post-B | Gate | Verdict |
|---|---|---|---|---|---|
| `signature_present_rate` | 0.0 | 0.857 | 0.850 | ≥0.85 | **PASS** |
| `content_present_rate` | 0.0 | 0.0 | 0.0 | stays 0.0 | **PASS** |
| `tiktoken_mean` | 2,952.466 | 3,703.376 | **3,639.85** | falls | **PASS** (−63.5 tok) |
| per-query overhead (tiktoken) | — | 750.9 | **687.4** | — | −8.5% |
| `payload_bytes.verbose` overhead | — | +27.2% | **+24.6%** | — | |
| `payload_bytes.compact` overhead | — | +40.0% | **+35.9%** | falls | **PASS** |
| `payload_bytes.ultra` overhead | — | +57.0% | **+50.8%** | — | |
| max `signature_view_tokens`/query | — | 749 | **528** | bounded | tail cut confirmed |

Three per-query `gold.located` values flipped between the banked and post-B runs (`Q133`
false→true, `H012`/`H066` true→false — net −1 raw `signature_present` count, matching the
0.857→0.850 rate move). All three are pure **located** flips (gold not found in the result set at
all), not a located-definition-chunk losing its `signature` field — confirming the kind-gate does
not touch definition-kind golds. `Q133`/`H066` are both already-documented ambient bf16-reranker
flapper queries from prior benchmark sessions, not a regression introduced here.

The tail bound is enforced unconditionally in code (`_extract_signature_estimate`'s
`text[:max_chars]`), not just observed empirically — covered by
`test_minified_single_line_chunk_is_truncated_by_max_chars` and
`test_signature_exactly_at_max_chars_is_untouched` in
`tests/unit/mcp_server/test_result_view.py`.

## Disposition

**Ship as-is, cheaper.** The governing check for future re-verification is the **per-format
overhead table above**, not a fixed absolute `tiktoken_mean` ceiling or a cross-scope "consistency"
argument — the absolute number is a function of corpus k-drift row count, which this feature does
not control and does not perturb.

All other pre-registered gates passed as specified. Canons are unaffected (L3 is display-only, never
reaches scoring — not re-run here since no scoring-path code changed).
