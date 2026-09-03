# Canon Gate: Ambiguous Fan-Out Cap (2026-09-03)

## Status: PASS (structural proof, not a literal bit-identical byte match)

Executes the Verification step of `docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md`
for plan step 8 (fan-out cap + `CallGraphConfig` knobs, commit `eff2126`): confirm no Wall-2
change leaked into the Python retrieval path.

## Why this is not a literal bit-identical comparison against the 09-01 pin

`evaluation/CANON_20260901_REBASELINE.md` pinned 63q MRR 0.8419 / 133q MRR 0.6378 against a
219-file/2,642-chunk index. Since that pin, five more plan steps landed on real, indexed Python
source (`chunking/languages/{_c_family,c,cpp}.py`, `chunking/relationships/edge_specs.py`,
`search/graph_integration.py`, `search/config.py`, plus this step's own edits) — the self-index
has legitimately grown to 232 files / 2,805 chunks. Editing indexed source between benchmark
captures shifts the corpus (embeddings, BM25 stats, PageRank centrality) independent of any
retrieval-logic change — a documented, expected phenomenon, not drift to chase byte-for-byte.

## Structural proof (the actual gate)

The fan-out cap only applies inside `GraphIntegration._get_ambiguous_candidates` when
`language in _C_FAMILY_LANGUAGES` (i.e. `"c"`/`"cpp"`). This project's own self-index is
Python-only — `get_index_status` reports `top_tags: {"python": 2598}`, zero `cpp`/`c` tags
(the two C/C++ fixture files under `tests/fixtures/chunker_corpus/` and
`tests/test_data/multi_language/` are never indexed: `tests/` is in the effective exclude-dirs
list). The cap's truncation line therefore cannot execute for a single call site in this graph,
by construction — not measured indirectly via MRR, but true by the language gate itself. This is
also pinned by a dedicated deterministic unit test,
`test_python_ambiguous_fanout_uncapped_regardless_of_cap_value`
(`tests/unit/search/test_graph_integration.py`).

## Results (informational — corpus-drift-affected, not the pass/fail signal)

Full non-incremental-equivalent pickup via `tools/batch_index.py --mode incremental` (11 modified
files, 146 chunks added/replaced; `index_is_current: true` confirmed before capture).

| Run | queries | MRR | vs 09-01 pin | per-query MRR movers |
|---|---|---|---|---|
| `canon_63q_r1_20260902_post_fanout_cap.json` | 63 | 0.8348 | −0.0071 | 4/63 |
| `canon_133q_r1_20260902_post_fanout_cap.json` | 133 | 0.6375 | −0.0003 | 29/133 |

Both aggregates are flat relative to the pin (well inside the corpus-drift band already observed
earlier the same day: the post-Wall-2/pre-fan-out-cap intermediate capture
`canon_63q_r1_20260902_deps.json`, itself −0.0074 off the pin before this step's code even
landed). Movers run in both directions with no net direction and no concentration in
Wall-2/fan-out-cap-adjacent files (`Q77`→`search/bm25_index.py`, `Q70`/`Q86`→chunker/relationship
files edited in earlier, already-committed plan steps, not this one). This is the signature of
ordinary reranker/corpus perturbation, not a systematic regression.

## Full test suite

- `./scripts/test/run_tests.sh tests/unit/ -q` → 4377 passed, 2 skipped (pre-commit, this step's
  8 new tests included).
- `./scripts/test/run_tests.sh tests/unit/chunking/ -q` → 517 passed, 2 skipped, 10 snapshots
  passed.

## Verdict

No Wall-2/fan-out-cap leak into the Python retrieval path. Gate satisfied by construction
(language-gated code path unreachable on an all-Python corpus) and corroborated by flat
aggregate MRR on both golden sets. Plan step 8 (task #7 in the working task list) closes here;
proceeding to the remaining C/C++-facing tasks (ADR, CHANGELOG, probe re-run, hand-labeling,
external-project reindex).
