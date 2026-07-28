# Curated-vocabulary query expansion over PRF or LLM query rewriting

Status: accepted
Date: 2026-07-28

Query expansion for zero-identifier paraphrase queries is implemented as a
curated concept→terms vocabulary table (`config/query_expansion_variants.yaml`)
matched by deterministic trigger containment, fused as discounted extra RRF
legs. It ships disabled (`QueryExpansionConfig.enabled = False`).

## Context

The 77-query golden set contains paraphrase queries that name a behaviour
without any code identifier ("write the analyzed relationships out so they
survive a restart" → `CodeGraphStorage.save`). BM25 cannot bridge the
vocabulary gap and dense retrieval ranked the golds outside the funnel on the
pre-v4 index. Three mechanisms were considered to rewrite or augment such
queries at search time:

1. **Pseudo-relevance feedback (PRF)** — expand the query with terms from the
   top-k initial results. A feasibility probe on the three target queries
   (Q101/Q104/Q122) showed the initial result lists are dominated by
   *wrong-but-topical* chunks (e.g. Q122's top result is a different query's
   gold); PRF would reinforce the wrong neighbourhood, not bridge to the gold.
2. **LLM query rewriting** — ask a model to translate the paraphrase into code
   vocabulary. Adds a search-time model dependency, latency, and
   non-determinism to a system whose selling point is local, reproducible,
   sub-second retrieval. Production deployments would not enable it.
3. **Curated vocabulary table** — a small (~10–15 concepts) hand-written map
   from general software-domain concepts (persistence, eviction, pooling, …)
   to code-domain terms, activated by lowercase trigger containment.

## Decision

Option 3. The table is deterministic, costs one extra BM25 leg per matched
concept (microseconds of matching, single-digit-ms leg search), and is
auditable in review. Curation policy is stated in the YAML header: every entry
must pass a generality test (plausibly serves queries outside the golden set),
entries are never keyed to or named after a benchmark query, and the table is
capped at ~15 concepts.

Integration shape: matched concepts produce **variant legs** — the query text
plus the concept's terms, searched against BM25 (`apply_to_bm25`, default on)
and/or dense (`apply_to_dense`, default off) — fused through the existing
N-list `RRFReranker.rerank()` at `primary_weight × variant_weight_discount`.
Disabled or unmatched queries take the exact pre-existing `rerank_simple`
path (regression-tested).

## Consequences

- The feature ships **disabled**. The 2026-07-28 A/B closed FAIL on its
  primary criterion (1 of 3 targets flipped; bar was 2): of the three target
  misses, only Q101 is a genuine hop-1 vocabulary gap on the current v4
  index (identifier-preserving tokenizer + path/symbol augmentation already
  fixed Q104/Q122 at hop-1 — their golds rank 1 and 6 out of hop-1 yet are
  demoted by the listwise neural reranker over the multi-hop-expanded
  candidate pool, a stage where query-side expansion has no direct
  leverage; Q122 flipped anyway via pool-composition perturbation, an
  indirect effect not worth adopting on). Rescuing Q101 would require
  variant weight ≥ primary BM25 weight, which measurably dilutes the dense
  leg for other queries (Q122's hop-1 fused rank degraded 21→36 at
  discount 1.0). Aggregates and latency were neutral (criteria b/c passed).
  See `evaluation/QUERY_EXPANSION_AB_20260728.md`.
- The mechanism, config surface, and vocabulary table remain in place for
  opt-in use and future re-evaluation if the post-retrieval demotion issue
  is addressed.
- The YAML schema does not preclude a future embedding-based trigger matcher;
  only the matcher would change.
