# Retrieval Canon Re-Baseline (2026-09-14) — first bge-m3 pin on this machine

## Status: MEASURED — pyan-fix gate PASSED; not comparable to any prior pin (embedding-model change)

Owed by the pyan3 dead-tier fix (`ImportError: cannot import name 'cull_subsumed' from
pyan.postprocessor`, root-caused to a stale venv 34 packages behind `uv.lock` — pyan3 2.6.2
installed against code written for the 2.8 postprocessor API). See the accompanying diagnosis
plan (`error-log-13-04-33-hybrid-whimsical-falcon.md`) for the full root-cause trace.

## Critical finding: the 09-08 pin is not a valid comparison point

`CANON_20260908_REBASELINE.md` (and every canon back through the 2026-07-26 adoption,
`EMBEDDER_F2LLM_AB_20260726.md`) was measured with **`codefuse-ai/F2LLM-v2-0.6B`** as the deployed
embedding model — stated explicitly in `CANON_20260901_REBASELINE.md:22`,
`CANON_20260903_REBASELINE.md:18`, `CANON_20260905_REBASELINE.md:50`, and
`CANON_20260905B_ADR0063_REBASELINE.md:69`. The 09-06 and 09-08 docs stop restating the model
(it hadn't changed pin-over-pin), but no commit or CHANGELOG entry between 09-05B and 09-08
(`f8548812`, 2026-09-08) touches `embedding.model_name` — the model carried forward unchanged.

This machine (a notebook, RTX 4060 Laptop GPU, **8.6 GB VRAM**) runs
**`BAAI/bge-m3`** — confirmed via `search_config.json:3`, the live index storage directory
(`claude-context-local_b7ab9381_bge-m3_1024d`), and the HF cache (`~/.cache/huggingface/hub`
contains only `models--BAAI--bge-m3`; F2LLM-v2-0.6B has never been downloaded here).
`CHANGELOG.md:532-535` documents this as a deliberate VRAM-gated split:
`BGE-M3 [DEFAULT]` vs `F2LLM-v2-0.6B [RECOMMENDED 12GB+]` — this notebook is below the 12 GB
threshold and correctly runs the default.

An initial A/B investigation this session (dependency-version counterfactuals: sentence-transformers
6.0.1 vs 5.7.0, transformers 5.16.1/tokenizers 0.23.1 vs 5.14.1/0.22.2, both bit-identical MRR;
config-default diff clean; determinism clean) conclusively ruled out the venv sync as the cause of
a large (~0.12–0.14 MRR) gap vs the 09-08 numbers. The actual cause is the embedding-model mismatch
above, not a code or dependency regression. **The 09-08 F2LLM-v2-0.6B numbers and this pin's
bge-m3 numbers are not comparable** — treat this as the first entry in a separate bge-m3-specific
baseline lineage, not a re-pin in the existing F2LLM lineage.

## The valid gate: same-model Leg A/B, isolating only the pyan fix

Because no bge-m3 canon existed before this session, the pyan-fix regression gate is the paired
Leg A (pyan off) / Leg B (pyan on) comparison below — both legs bge-m3, both legs post-sync,
differing only in `call_graph.resolvers`. This is the actual attribution the diagnosis plan called
for, just against a same-model control rather than the 09-08 pin.

### Substrate (both legs)

`BAAI/bge-m3` (1024d), post-`uv sync --extra callgraph --extra test --extra otel` (pyan3 2.8.1,
sentence-transformers 6.0.1, transformers 5.16.1, tokenizers 0.23.1). Full force reindex
(`tools/batch_index.py --path . --mode force`): 238 files / 2,991 chunks, graph 2,687 base nodes /
17,122 call edges (3,910 resolved / 1,722 ambiguous / 11,490 phantom) before resolver injection.
`audit_golden_dataset.py` CLEAN on both datasets before every leg.
`CLAUDE_AUTO_REINDEX=0`, `PYTHONHASHSEED=0` exported throughout.

- **Leg A (control, pyan off)**: `call_graph.resolvers = ["libcst"]`. Resolver log:
  `[RESOLVERS] libcst: 2295 edges → added=2295, upgraded=0, dropped_equal=0, dropped_lower=0`.
- **Leg B (target, pyan restored)**: `call_graph.resolvers = ["pyan", "libcst"]`. Resolver log:
  `[RESOLVERS] pyan: 3184 edges → added=3171, upgraded=0, dropped_equal=13, dropped_lower=0
  (total merged so far: 3171)` then `[RESOLVERS] libcst: 2295 edges → added=15, upgraded=2280,
  dropped_equal=0, dropped_lower=0 (total merged so far: 3186)` — the literal reproduction and
  resolution of the user's original symptom (previously: `ImportError`, zero pyan edges).

### Results (hybrid, k=10, deterministic)

| Leg | Dataset | Queries | MRR | file |
|---|---|---|---|---|
| A (pyan off) | Canonical (63q) | 63 | 0.696 | `ctrl_63q_r1_20260914.json` |
| B (pyan on) | Canonical (63q) | 63 | **0.702** | `canon_63q_r1_20260914.json` |
| B (pyan on) | Canonical (63q), determinism check | 63 | 0.702 | `canon_63q_r2_20260914.json` |
| B (pyan on) | Expanded (133q, non-D) | 133 | **0.514** | `canon_133q_r1_20260914.json` |
| B (pyan on) | F-via-similar (anchor-chunk, 63q) | 63 | **0.728** | `canon_63q_fsim_r1_20260914.json` |

### Pyan-fix gate: Leg B − Leg A on identical (bge-m3) substrate

| view | ΔMRR | verdict |
|---|---|---|
| 63q canonical | **+0.006** | no regression; small positive move, consistent with 3,171 real
  new-and-correct call edges added by the restored pyan tier |

Determinism: 63q r1/r2 on Leg B bit-identical (`n_moved = 0` on every metric,
`canon_63q_r2_20260914.json`). Dependency-version counterfactuals (ST 5.7.0, transformers
5.14.1/tokenizers 0.22.2) reproduced Leg A's 0.696 bit-for-bit — the ST 6.0.1 /
transformers-tokenizers bump has zero measurable effect on this substrate; ruled out as a
confound. Config defaults (`search/config.py`) diffed clean between `f8548812` and `HEAD`.

## What this pin settles

1. The pyan tier is genuinely fixed: it now resolves 3,184 cross-module call edges per full index
   (previously: silent `ImportError`, 0 edges) with no ranking regression on this substrate —
   +0.006 MRR, well inside noise, but directionally consistent with more/better edges.
2. The large gap that first appeared against `CANON_20260908_REBASELINE.md` was never attributable
   to the venv sync, any single dependency bump, config drift, or an indexing bug — all were tested
   and eliminated. It is fully explained by comparing across two different embedding models
   (F2LLM-v2-0.6B vs bge-m3), which was never previously measured against each other's absolute
   MRR on this dataset in a controlled way.
3. This is the **first published bge-m3 canon on this notebook's substrate** — 63q **0.702**, 133q
   **0.514**, F-via-similar **0.728**. Future re-pins on this machine (bge-m3, ≤8.6 GB VRAM) should
   gate against these numbers, not against the F2LLM lineage in `docs/BENCHMARKS.md`'s main Results
   table.

## Not comparable to (do not read as regressions)

- `CANON_20260908_REBASELINE.md` (0.8241 / 0.6469 / 0.8671) and every canon back to
  `EMBEDDER_F2LLM_AB_20260726.md` — all measured on `codefuse-ai/F2LLM-v2-0.6B`, a materially
  stronger embedder per the original A/B (`evaluation/EMBEDDER_F2LLM_AB_20260726.md`), on a
  different (≥12 GB VRAM) machine.

Supersedes nothing in the F2LLM lineage. Establishes the bge-m3 lineage.
