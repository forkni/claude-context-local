# Retrieval Canon Re-Baseline (2026-09-20)

## Status: MEASURED — gate marginally breached on recall@20/MRR (all three views), attributed to a named, diagnosed cause; adopted as canon-of-record anyway

This re-pin was triggered by discovering that `evaluation/CANON_20260908_REBASELINE.md` (and the
five re-baselines before it, 09-03 → 09-07) were measured on a **pyan-dark substrate**: the venv
had silently drifted 34 packages behind `uv.lock` since `f5acd585` (2026-09-02), so
`pyan_available()` kept reporting the pyan cross-module call-edge tier usable while the real
`ImportError` fired inside a resolver subprocess and was swallowed as non-fatal (`ee63b8ef`,
2026-09-14). Restoring the venv brought the pyan tier back online, which changes the call graph
enough to move ranking through the centrality channel (see "Part 1" below) — that is the entire
explanation for this pin's deltas. No code regression is implicated.

## Substrate

`tools/batch_index.py --path . --mode force` equivalent state at clean HEAD `624fef0c`, tree
clean (`git_dirty: False` on three of the four capture legs — see the dirty-tree note below for
the fourth): **238 files / 3,061 chunks**, `codefuse-ai/F2LLM-v2-0.6B` / 1024d, LSP enabled. Call
graph **7,050 nodes / 31,567 edges** — vs the 09-08 pin's recorded **6,855 / 30,610**
(**+195 nodes / +957 edges**), all of it the restored pyan tier. Resolver mix on the call-edge
tier itself (`resolver_edge_counts`): `lsp 2029 / chunker 1132 / libcst 775 / pyan 573`. The 09-08
pin's own doc predates the fingerprint field entirely for the 63q dump (no `substrate` block at
all — see "Confound guard" below) but its prose records `6,855 nodes / 30,610 edges` with pyan
silently absent from that count.

All legs run with `CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0` exported, strictly sequential
(`run_sscg_benchmark.py --project-path .`), one GPU, no concurrent reranker loads.

## Part 1 — the diagnosed cause (resolver-mix restoration, not a regression)

PageRank centrality reaches ranking through two live channels — the centrality-adaptive BM25
boost and `EgoGraphRetriever.set_centrality_scores` (`search/graph_scoring_stage.py:158-180`) —
so a +957-edge graph change reorders heads even on files with **zero** source commits since the
09-08 pin. That is exactly the signature observed: five queries move on the 63q set (Q43 −0.333,
Q99 −0.286, Q76/Q56/Q73 −0.250 on their per-query metric), `pool_hit_rate` stays 1.000 throughout,
and 3 of those 5 golds are still inside the new top-10 — this is a **reordering** effect, not a
recall failure.

Two alternative explanations were checked and ruled out:

- **Not a gold-set artifact.** Re-scoring the 09-08 pin's own stored top-10 retrieval lists under
  the corrected 2026-09-14 golden-dataset commit (`9680fa9b`) reproduces the 09-08 doc's stored
  per-query recall@5/@10/MRR/NDCG@5 exactly (300/300 checks on the 63q set) — the re-score is not
  itself introducing drift — and under the corrected golds 63q recall@5 moves only
  0.6533 → 0.6514 while MRR actually **rises** +0.0093. The gold-set commit is not the driver of
  this pin's deltas.
- **Not a lexical/BM25-corpus-statistics artifact.** `search/bm25_index.py` and `search/indexer.py`
  carry zero commits between the two pins, so any BM25-side shift would have to come from IDF
  movement across the small chunk-count change (+83 chunks total across the whole burst since
  09-08) rather than code — checked and found consistent with the resolver-mix explanation, not a
  competing one.

**Disposition:** the cause is the restored pyan tier acting through the centrality-adaptive BM25
boost and the ego-graph neighbour-ordering channel. It is real, it is understood, and it is
priced into the gate verdict below rather than hidden.

## Pre-registered gate

|ΔMRR| ≤ 0.02 and Δrecall@20 ≥ −0.02 vs the 09-08 pin (0.8241 / 0.6469 / 0.8671) on all three
views; guard-rails `Overall: PASS` on every leg; 63q determinism bit-identical across rounds.

**This gate is marginally breached on all three views** — by 0.0001–0.0014 on recall@20 for two
views and by 0.0005 on MRR for the third. Per the plan that authorized this re-pin: *"Expect the
63q recall deltas to sit at/near the floor — do not suppress that; record it as a declared
finding with Part 1's cause attached."* That expectation held, and it also turned out to apply to
133q's recall@20 and F-via-similar's MRR, each by a comparably thin margin. Given Part 1's
diagnosis — a specific, checked, non-code-regression cause — this pin is adopted as
canon-of-record anyway; the alternative (keeping the pyan-dark 09-08 numbers as canon) is worse,
since those numbers reflect a resolver tier that was silently broken. See "What this supersedes"
below.

## Results (hybrid, k=10, deterministic, intent pinned off — see caveat below)

| Dataset | Queries | MRR | Recall@5 | Recall@10 | Recall@20 | NDCG@5 | pool_hit_rate | file |
|---|---|---|---|---|---|---|---|---|
| Canonical (`golden_dataset.json`, A–F excl. D) | 63 | **0.8330** | 0.6390 | 0.7414 | 0.8126 | 0.6669 | 1.0000 | `canon_63q_r1_20260920.json` |
| Expanded (`golden_dataset_expanded.json`, non-D) | 133 | **0.6514** | 0.6171 | 0.7143 | 0.7684 | 0.5983 | 0.9098 | `canon_133q_r1_20260920.json` |
| F-via-similar (anchor-chunk view, whole-63q aggregate) | 63 | **0.8876** | 0.6441 | 0.7397 | 0.7897 | 0.6856 | 1.0000 | `canon_63q_fsim_r1_20260920.json` |

Extended metrics (not part of the pre-registered gate, recorded for completeness):

| Dataset | Recall@1 | Recall@7 | Recall@50 | NDCG@10 | hit_rate@5 | hit_rate@7 | line_recall | avg_pool_size |
|---|---|---|---|---|---|---|---|---|
| Canonical (63q) | 0.2775 | 0.7000 | 0.8126 | 0.7165 | 0.9841 | 1.0000 | 0.9266 | 29.0 |
| Expanded (133q) | 0.2850 | 0.6644 | 0.7684 | 0.6404 | 0.8571 | 0.8647 | 0.8209 | 28.4 |
| F-via-similar (63q) | 0.2958 | 0.7104 | 0.7897 | 0.7277 | 0.9841 | 1.0000 | 0.9328 | 28.9 |

## Delta vs the superseded pin (2026-09-08: 0.8241 / 0.6469 / 0.8671)

| set | ΔMRR | Δrecall@10 | Δrecall@20 | ΔNDCG@5 | gate |
|---|---|---|---|---|---|
| 63q | +0.0089 | −0.0220 | **−0.0201** | −0.0137 | **breach (0.0001 over floor)** |
| 133q | +0.0045 | −0.0092 | **−0.0214** | −0.0049 | **breach (0.0014 over floor)** |
| F-via-similar | **+0.0205** | −0.0156 | −0.0174 | −0.0057 | **breach (0.0005 over ceiling)** |

Every breach is on the metric Part 1 diagnoses (recall@20 pushed down or MRR pushed up by
centrality-mediated reordering from the restored pyan tier), every breach is inside 0.0014 of the
pre-registered band, and none of the three views lost `pool_hit_rate` (63q and F-via-similar stay
at 1.0000; 133q stays at 0.9098, unchanged from 09-08). This is read as the diagnosed cause, not a
new regression — but it is reported as a breach, not rounded into a pass.

## Dirty-tree note on the F-via-similar leg

The F-via-similar capture (`canon_63q_fsim_r1_20260920.json`) recorded `git_dirty: True` in its
substrate fingerprint, while the 63q and 133q legs — captured with the identical `git_sha`,
identical `resolver_edge_counts`, identical `total_chunks`/`files_indexed` — recorded
`git_dirty: False`. This is **not** a substrate confound: the F-via-similar leg was launched in
the background before this session's Part 3 documentation edits began, and several `Edit` calls
to `docs/adr/0077-*.md`, `docs/adr/0076-*.md`, and `docs/BENCHMARKS.md` landed on disk while it
was still running — the dirty-tree flag is evaluated at result-write time, not at launch time, and
none of those edits touch retrieval code or run under `CLAUDE_AUTO_REINDEX=0`. All four legs'
substrate fingerprints (chunk/file counts, embedding model, resolver edge counts) are otherwise
byte-identical, so the actual FAISS index, BM25 postings, and call graph consumed by this leg are
provably the same ones the other two legs consumed. Recorded here per the "do not suppress"
instruction rather than silently accepted.

## Determinism

63q r1/r2 paired `--compare` (`canon_63q_r1_20260920.json` vs `canon_63q_r2_20260920b.json`)
showed `mean_d = +0.0000`, `n_moved = 0` on every metric across all 63 shared queries —
bit-identical. Adopted `canon_63q_r1_20260920.json` as r1; `canon_63q_r2_20260920b.json` as the
confirming r2.

## Confound guard

No `[CONFOUND]` line on any same-generation paired `--compare` this pin ran (r1-vs-r2, and each
09-20 view vs its own kind). The 09-08 comparison's clean guard is **not** informative either way:
`canon_63q_r1_20260908.json` has no `substrate` block at all (the fingerprint field landed later,
in `e5f1a03b`), so the guard has nothing to compare against on that side and cannot fire regardless
of what changed.

## Intent-pinned-off caveat

All numbers above are measured with the intent layer pinned off
(`run_sscg_benchmark.py`'s `pin_intent_off=True`), which re-asserts `intent.enabled=False` before
every call. `search_config.json` enables intent on the live MCP server
(`default_intent: "HYBRID"`), so `GraphScoringStage._reorder_synthetic`'s module-chunk demotion is
inert in every benchmark run above but active in production — live queries do not compete against
`module:`-kind chunks for top-5 slots the way the numbers in this doc do. This gap predates this
pin, applies identically to every canon in this lineage, and is intentionally left unfixed here
(changing `pin_intent_off` is out of scope for this re-pin — see `docs/BENCHMARKS.md` for the full
caveat and live-query evidence).

## What this supersedes

Supersedes `evaluation/CANON_20260908_REBASELINE.md` as canon-of-record for this machine
(`codefuse-ai/F2LLM-v2-0.6B` + `jinaai/jina-reranker-v3`, `search_config.json:3,71` —
**non-default** config; the packaged defaults remain `BAAI/bge-m3` +
`gte-reranker-modernbert-base` for VRAM reasons). The 09-08 pin's numbers are not wrong as
*measurements of that substrate*; that substrate was missing the pyan call-edge tier, which this
pin restores.

This pin does **not** supersede and is **not comparable to** the
`evaluation/CANON_20260914_REBASELINE.md` / `CANON_20260914B_LSP_REBASELINE.md` lineage. Those
were captured on a different physical machine (a notebook, RTX 4060 Laptop GPU, 8.6 GB VRAM)
running the packaged `BAAI/bge-m3` default embedder — a different model, different VRAM budget,
and different hardware, not a re-pin of the same benchmark.
