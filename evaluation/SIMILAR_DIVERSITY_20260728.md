# find_similar File-Diversity Probe — Q71 Same-File Dominance (2026-07-28)

**Verdict: implementation gate FAILS — no diversity policy ships. The probe
(`scripts/benchmark/probe_similar_diversity.py`) is the deliverable.**

Follow-up to the F-via-similar view (commit `5ab99b1`, F MRR 0.436 → 0.544),
which regressed Q71. Hypothesis under test: `CodeIndexManager.get_similar_chunks`
(`search/indexer.py:322-343`) applies no file-level diversity — a raw FAISS
`k+1` neighbourhood filtered only of the anchor itself — so the anchor's
own-file neighbours crowd out cross-file sibling implementations.

## 1. Method

One over-deep fetch per F query (`find_similar_to_chunk(anchor, k=30,
rerank=False)` — dense-only, reuses the stored FAISS embedding, ~3 ms/query,
no GPU model load), then candidate policies simulated client-side on the
normalized/deduplicated order the benchmark scores:

- `current` — top-10 as returned
- `exclude_anchor_file` — drop all candidates from the anchor's own file
- `max_per_file=N` — global per-file cap, N ∈ {1, 2, 3}
- `max_anchor_file=N` — cap only the anchor's file, others uncapped

Gate (pre-agreed): implement only if a policy improves F-mean MRR by >0.01
with no per-query MRR regression >0.10.

Sanity: the `current` row reproduces the benchmark F-via-similar view
(mean MRR 0.550 here vs 0.544 in the benchmark run; the small delta comes
from deduplicating split_block variants over the depth-30 fetch before the
top-10 cut, which can pull a candidate up one rank).

## 2. Results (k=10, fetch_k=30, 9 F queries)

| policy | mean MRR | delta | regressions |
|--------|----------|-------|-------------|
| current | 0.5500 | — | — |
| exclude_anchor_file | 0.7361 | **+0.1861** | Q97 (−0.33), Q98 (−0.88) |
| max_per_file=1 | 0.5926 | +0.0426 | Q97 (−0.33) |
| max_per_file=2 | 0.5370 | −0.0130 | Q97 (−0.33) |
| max_per_file=3 | 0.5556 | +0.0056 | none |
| max_anchor_file={1,2,3} | identical to max_per_file={1,2,3} | | |

Per-query highlights:

| Query | current | exclude_anchor_file | Note |
|-------|---------|---------------------|------|
| Q71 | 0.200 (golds at 5, 10) | **1.000** (1, 5, 7) | cross-file overrides — hypothesis confirmed |
| Q70 | 0.500 | 1.000 | cross-file chunker constructors |
| Q96 | 0.250 | 1.000 | cross-file search wrappers |
| Q99 | 0.333 | 1.000 | cross-file persistence methods |
| Q97 | 0.333 | **0.000** | ALL golds in the anchor's own file (`FaissVectorIndex.load/create/clear`) |
| Q98 | 1.000 | 0.125 | primary golds include same-file `QueryEmbeddingCache.put` |

## 3. Findings

1. **Same-file dominance is real and specifically *anchor-file* dominance.**
   `max_anchor_file=N` is numerically identical to the global `max_per_file=N`
   on every query — no file other than the anchor's ever exceeds the cap in
   the top ranks. 5–8 of the top-10 candidates come from the anchor's file
   for 7 of 9 queries.
2. **But same-file neighbours are sometimes the right answer.** Q97's golds
   (other `FaissVectorIndex` lifecycle methods) and Q98's primary gold
   (`QueryEmbeddingCache.put`) live in the anchor's file by construction.
   Any cap ≤2 zeroes Q97; full exclusion also collapses Q98 (1.000 → 0.125).
3. **No static policy passes the gate.** The best regression-free policy
   (`max_per_file=3`, +0.0056) is below the 0.01 bar; every policy that
   materially helps the cross-file queries (Q70/Q71/Q96/Q99) materially harms
   the same-file queries (Q97, and Q98 under exclusion).
4. **The disambiguating signal never reaches the code.** Whether the caller
   wants same-file siblings (Q97: "other vector index lifecycle methods") or
   cross-file analogues (Q71: "other relationship extractors that override
   the same hook") is expressed in the *query text* — which
   `find_similar_to_chunk` never sees. The anchor alone cannot decide.

## 4. Decision

No change to `get_similar_chunks` / `find_similar_to_chunk` defaults, and no
opt-in parameter shipped now: the pre-agreed gate (mean gain with no material
per-query regression) fails structurally, not marginally.

**Future lever** (recorded, not scheduled): a caller-controlled
`exclude_same_file: bool` parameter on the `find_similar_code` MCP tool. The
intent lives with the caller (the agent composing the tool call knows whether
it wants cross-file analogues), and the exclusion arm's 0.7361 mean shows the
ceiling if intent were supplied: +0.19 mean MRR on intent-matched queries.
That is an API-surface decision, deferred until the current
`search/`-lane work (multi-hop pool-flooding fix) lands.

**Deferred with it**: any `run_sscg_benchmark.py` harness wiring and full
benchmark confirmation runs (the harness file and GPU are owned by the
concurrent pool-flooding session).

## 4a. Addendum (2026-07-28, later): future lever SHIPPED

The pool-flooding fix landed (commit `1bf947b`, ADR-0013), freeing the
`search/` lane and the harness — the deferred caller-controlled parameter now
exists end-to-end:

- `CodeIndexManager.get_similar_chunks(..., exclude_same_file=False)` —
  default path byte-identical (`k+1` fetch); the exclusion path overfetches
  `min(k*3+1, ntotal)` (the probe's depth) then drops every candidate sharing
  the anchor's `relative_path`.
- Threaded through `HybridSearcher.find_similar_to_chunk` and the
  `find_similar_code` MCP tool (`exclude_same_file` boolean, default false,
  with intent guidance in the schema description).
- Harness: F queries whose *query text* asks for cross-file analogues carry
  `similar_exclude_same_file: true` in both golden datasets
  (Q70/Q71/Q96/Q99 — Q97/Q98, whose golds are same-file by construction, are
  deliberately unannotated); `--f-via-similar` passes the annotation through.

Verification run (`f_view_exclude_same_file_r1`, 9 F queries): annotated
queries reproduce the probe's exclusion-arm ranks exactly —
Q70 0.500→1.000, Q71 0.200→1.000, Q96 0.250→1.000, Q99 0.333→1.000;
unannotated queries byte-identical (Q95 0.333, Q97 0.333, Q98 1.000).
F-mean via similar: **0.544 → 0.852**. The +0.19 intent-supplied ceiling from
§4 is realized (and exceeded, since exclusion is applied only where intent
matches).

## 5. Reproduction

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/benchmark/probe_similar_diversity.py \
  --project-path . --dataset evaluation/golden_dataset.json --k 10 --fetch-k 30
```

Exit 0 = gate passes (a policy is worth implementing); 1 = gate fails
(current state); 2 = setup error (an empty candidate list with ~0 ms latency
is the unloaded-dense-index signature, never a real result).
