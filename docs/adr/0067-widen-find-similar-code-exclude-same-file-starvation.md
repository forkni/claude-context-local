# Widen `find_similar_code(exclude_same_file=True)` on starved pools

Status: accepted
Date: 2026-09-07

## Context

While running an architecture review of an external TouchDesigner project (`TD_Glossary_tox`,
2,474 chunks / 368 files) through this repo's MCP server, `find_similar_code` returned similarity
scores clustered so tightly (0.82-0.87 for every method in a class, trivial or complex alike) that
they carried no ranking signal. Probing that symptom uncovered a harder defect underneath it:
`find_similar_code(exclude_same_file=True)` silently returns an empty list when the anchor chunk's
own file dominates the retrieval pool — a wrong-answer bug that looks like an honest negative, the
worst kind, since the caller has no way to tell the difference.

Measured live (MCP, `TD_Glossary_tox`), anchor `NetworkGraphExt._continue_walk` (59 lines):

| `exclude_same_file` | `k` | returned |
|---|---|---|
| false | 8 | 8 — scores 0.82-0.87 |
| **true** | 8 | **0** |
| **true** | 30 | **6** |
| **true** | 60 | 60 — scores 0.53-0.67 |

Returned count falls far below `k` and grows super-linearly with it. The MCP default is `k=7`
(`search_mode.default_k`, `mcp_server/tools/search_handlers.py:304`), so the default call is the
broken one on any large single-class file.

**Root cause** — `search/indexer.py`'s `get_similar_chunks`, `exclude_same_file` branch: a
post-retrieval filter over an already-truncated pool, with a hard `[:k]` and no back-fill.
`search_k = min(k * 3 + 1, ntotal)` fetches a fixed-depth pool, filters out the anchor's own file,
then truncates — whatever survives is all the caller ever sees, even when the corpus holds far more
cross-file analogues one search deeper. Modeling `survivors ~ min(k, max(0, 3k+1 - N_f))`, where
`N_f` is the anchor file's chunk count ranking inside the pool, solving the `k=30` row gives
`N_f = 85`, which then predicts the other two rows exactly (`k=8`: `25-85 < 0` -> 0; `k=60`:
`181-85 = 96` -> capped to 60). Two different anchors, one parameter, three exact hits. The `k*3`
overfetch was a deliberate choice (`evaluation/SIMILAR_DIVERSITY_20260728.md`) built on the
assumption that same-file neighbors are "5-8 of the top-10" — true for modular files, false for one
giant single-class file.

This is corpus-shape dependent. Probing this repo's own golden-set category-F anchors at
benchmark `k=10` (Q70 `PythonChunker.__init__`, Q99 `GraphIntegration.save`) found both healthy,
10/10 — `claude-context-local`'s files are modular enough that `3k+1` never starves. The defect did
not bite this repo's golden set, which is what made the cheap self-baseline gate below legitimate
— re-verified rather than assumed (see Verification).

A second, independent defect shared the same code path: `find_similar_code` raised `TypeError`
whenever `enable_hybrid=False` routed it through `IntelligentSearcher` instead of `HybridSearcher`
— `search/searcher.py`'s `find_similar_to_chunk` had no `exclude_same_file` parameter, but the MCP
handler always passes that kwarg. Latent (`enable_hybrid` defaults `True`), trivial, fixed here.

**Out of scope**: the 0.82-0.87 same-file score band itself is self-inflicted by shared embedding
prefixes (`embeddings/document_composer.py`'s import-context and class-signature prefixing, both
default-on) — a real +0.25 inflation on raw cosine, not a scale artifact, but re-embedding every
chunk to fix it needs a full canon re-pin. Recorded as a follow-up candidate, not started here.

**Not re-litigated**: `evaluation/SIMILAR_DIVERSITY_20260728.md` rejected automatic same-file caps
and automatic same-file exclusion, structurally — whether the caller wants same-file siblings or
cross-file analogues is expressed in the query text, not decidable from the anchor alone. The
caller-controlled `exclude_same_file` flag is what shipped instead. This fix makes that flag work as
specified; it adds no new policy and no automatic behavior.

## Decision

Widen only when starved, in the one place that owns the filter. Three commits, the shape proven by
ADR-0064/0065/0066:

**Gate 0** (`0b29e8c4`, committed first, green against unmodified code): characterization tests in
`tests/unit/search/test_indexer_similar_chunks.py` pinning today's starvation (`k=5,
exclude_same_file=True` -> 0 results on a wide-corpus fixture), the `searcher.py` `TypeError`, and
the MCP default `k=7`. All six pre-existing exclusion tests were traced by hand first and confirmed
they stay green under the new design (an unstarved anchor's first pass already satisfies `k`, so
the loop never iterates for them) — only genuinely new behavior was expected to flip.

**Commit 1** (`db34e43f`, pure refactor): extracted the survivor comprehension into
`_drop_anchor_and_same_file`, a static helper — no behavior change, so it needed no new test
expectations. Gives the widening loop a filter it can re-apply to successive, deeper pools without
duplicating the comprehension.

**Commit 2** (`f30494a5`, the reviewed behavior change):

```python
if exclude_same_file:
    anchor_path = metadata_entry["metadata"].get("relative_path")
    ntotal = self.index.ntotal
    search_k = min(k * 3 + 1, ntotal)
    while True:
        results = self.search(embedding, search_k)
        survivors = self._drop_anchor_and_same_file(results, chunk_id, anchor_path)
        if len(survivors) >= k or search_k >= ntotal or len(results) < search_k:
            return survivors[:k]
        search_k = min(search_k * 2, ntotal)
```

Three termination conditions: enough survivors, depth exhausted (`search_k >= ntotal`), or index
exhausted (`search` returned fewer rows than asked). Worst case ~`log2(ntotal / 3k)` iterations —
about 7 on a 3,000-chunk index — and only on a starved anchor; the unstarved path returns on the
first pass, byte-identical to before. Also added `exclude_same_file: bool = False` to
`search/searcher.py`'s `find_similar_to_chunk`, forwarded to `get_similar_chunks`, fixing the
`TypeError`. `tests/fixtures/search_fakes.py`'s `FakeDenseIndex.get_similar_chunks` — which
replicated the production `k*3+1` arithmetic verbatim as a faithful bug-carrier — was updated in
lockstep so `test_hybrid_search.py` exercises the corrected behavior instead of asserting the old
bug. The Gate 0 starvation tests flip to their corrected expectations in this same commit.

**Rejected seats**: raising the `search()` break condition in `get_similar_chunks`'s non-exclusion
path (shared with `search_code` — would move the canon for no reason); widening `fetch_k` in
`hybrid_searcher.py` (only shifts the `k` at which the cliff appears, doesn't remove it); retrying
in the MCP handler (hides the bug at the boundary and doubles latency on every starved call); a
per-file chunk count column (`MetadataStore` is a blob store keyed by chunk_id with no path column
— would need a schema change and a full index rebuild for a count the widening loop gets for free).

## Verification

The unstarved path is provably untouched (first pass already satisfies `k`, loop exits
immediately), and no golden-set F anchor starves on this repo's substrate (verified above) — so the
prediction was that the fix is **inert** on this repo's own benchmark. Proved rather than asserted,
using ADR-0066's paired self-baseline bit-identity method — deliberately stronger than the usual
±0.02 drift band, because it fails loudly if the inertness reasoning is wrong:

1. Full non-incremental reindex, `audit_golden_dataset.py` CLEAN on both `golden_dataset.json` and
   `golden_dataset_expanded.json`. Index at gate time: 235 files / 2,968 chunks.
2. **Leg 1 vs. Leg 2** — 63-query benchmark on pre-fix code (`git checkout db34e43f --
   search/indexer.py search/searcher.py`) vs. post-fix code (`git checkout HEAD -- <same files>`),
   same index, no reindex between legs, `CLAUDE_AUTO_REINDEX=0` exported for both. Aggregate
   metrics bit-identical (MRR 0.823, R@5 0.659, R@7 0.730, R@10 0.777, HR@5 1.000, NDCG@5 0.683);
   paired-delta `--compare` showed `mean_d = +0.0000` and `n_moved = 0` on every metric across all
   63 shared queries. Only `avg_latency_ms` differed (4604.7 vs. 4593.0 — timing noise) and the
   `config_name`/`timestamp` metadata fields, confirmed by a full-file diff with `latency_ms`
   stripped.
3. **Leg 3 vs. Leg 4** — the dedicated `--f-via-similar` view, same pre-fix/post-fix pairing, same
   index. This view specifically routes the 4 anchored category-F queries that carry
   `similar_exclude_same_file: true` (Q70, Q71, Q96, Q99) through `find_similar_to_chunk` with
   `exclude_same_file=True` — the exact code path the fix touches, and one the standard legs above
   never exercise (`run_sscg_benchmark.py` only reaches that branch when `f_via_similar=True`).
   Aggregate metrics bit-identical (MRR 0.866, R@5 0.664, R@7 0.736, R@10 0.773); paired delta again
   `mean_d = +0.0000`, `n_moved = 0` on all 63 queries, Q70/Q71/Q96/Q99 rows byte-identical between
   legs. No starved anchor was missed.
4. **End-to-end acceptance** — the original reported symptom, re-run against `TD_Glossary_tox`
   directly via `CodeIndexManager.get_similar_chunks` on the same anchor
   (`Extensions/OperatorGlossary/dat_NetworkGraphExt.py:...:method:NetworkGraphExt._continue_walk`,
   discovered by substring match after a same-day reindex shifted its exact line range):
   `k=8, exclude_same_file=True` now returns **8** results (was 0), top-scoring **0.6688** —
   matching the ~0.67 prediction. `k=30` and `k=60` now return full 30/60 (previously 6 and 60).

Full unit suite green at every step; lint, format, and pyrefly clean on all three commits.

## Consequences

- `find_similar_code(exclude_same_file=True)` now returns `k` cross-file results whenever the
  corpus contains `k` of them, on every corpus shape — not just modular ones.
- `find_similar_code` no longer raises `TypeError` under `enable_hybrid=False`.
- Every non-starved caller, including this repo's entire benchmark corpus, is provably unaffected —
  confirmed bit-identical rather than assumed.

## Out of scope

- **The same-file score-inflation band (0.82-0.87)** — caused by shared embedding prefixes
  (`enable_import_context`, `enable_class_context`, both default-on in
  `embeddings/document_composer.py` / `search/config.py`). Fixing it re-embeds every chunk and needs
  a full canon re-pin — a campaign, not a bug fix. Named knobs for that follow-up:
  `enable_import_context`, `enable_class_context`, `max_import_lines`,
  `max_class_signature_lines`.
- Automatic same-file capping or exclusion — permanently rejected by
  `evaluation/SIMILAR_DIVERSITY_20260728.md`; not reopened here.
