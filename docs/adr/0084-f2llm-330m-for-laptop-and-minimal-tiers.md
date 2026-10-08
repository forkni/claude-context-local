# F2LLM-v2-330M is the recommended embedder for the laptop and minimal VRAM tiers

Status: accepted
Date: 2026-10-08

## Context

The laptop (6-10 GB) and minimal (under 6 GB) tiers recommended `BAAI/bge-m3`. An audit of the
bge-m3 dense path against the paper (arXiv 2402.03216) and the HF card found the implementation
correct (CLS pooling, L2 norm, inner-product index, no query instruction). The weak link is the
model on code: MTEB-Code (v1) 58.22, with 344K CodeSearchNet pairs the only code in its training
mix.

The workstation lineage (F2LLM-v2-0.6B + jina-reranker-v3) does not fit an 8 GB laptop, and
Qwen3-Embedding-0.6B OOM'd there with a reranker. `codefuse-ai/F2LLM-v2-330M` is pruned from
F2LLM-v2-0.6B (16 layers, dim 896, 0.67 GB bf16 weights, Apache-2.0, MTEB-Code 75.74) and uses the
same prompt template and last-token pooling, so it reuses the existing F2LLM registry pattern.
F2LLM trained on some MTEB-Code splits, so the leaderboard figure is optimistic; the repo's own
golden sets were the gate.

## Decision

Set `recommended_model = "codefuse-ai/F2LLM-v2-330M"` for the `minimal` and `laptop` tiers in
`search/vram_manager.py`, and register the model in `MODEL_REGISTRY` (`search/config.py`).
`gte-reranker-modernbert-base` stays as the laptop reranker. `search_config.json.example` keeps
`BAAI/bge-m3`; changing the shared default is a separate decision. The desktop and workstation
tiers are untouched, and `index_probe` will now flag existing bge-m3 indexes on these tiers as
tier-mismatched, which is intended.

## Evidence

2x2 on the RTX 4060 Laptop (8188 MiB, 1.3-1.6 GB held by desktop apps), same corpus (243 files /
3146 chunks per leg), `--deterministic-gpu`, one run per view. Full tables and CIs:
`evaluation/EMBEDDER_LAPTOP_AB_20261008.md`.

- **F2LLM-330M + gte vs bge-m3 + gte** (paired 95% bootstrap CIs): MRR and R@20 improve on all three
  views (63q, 133q, F-via-similar); no CI excludes 0 negatively. F-via-similar R@10 (+0.036) and
  R@20 (+0.031) CIs exclude 0 positively. Effect sizes are small, so the result reads "at least as
  good", not "clearly better".
- **VRAM:** peak `max_memory_reserved` 4.24 GB (search) and 4.04 GB (index) against 1.9 GB for
  bge-m3, within 0.9 x free-at-start (about 5.9 GB), with no OOM halving in any log.
- **gte reranker:** lifts R@20 by 0.15-0.20 for both embedders (CIs exclude 0), so it stays.
- **Reranker-off, 330M vs bge-m3:** mixed. R@10 and R@20 are better on 63q and F-via-similar, but
  133q MRR is worse (CI excludes 0).

## Consequences

- Reindex needed for anyone moving off bge-m3: the per-model storage dir encodes the dimension
  (896 vs 1024), and the old index stays on disk.
- The 330M peaks at about 2.3 GB more than bge-m3 at batch 4. It fits an 8 GB card with desktop
  apps open, but it was **not measured below 6 GB**. The minimal tier runs with reranking off, and
  a 4 GB card has little headroom for a 4.0 GB index peak. If a minimal-tier user reports OOM,
  the 160M model (dim 640, MTEB-Code 70.38) is the follow-up leg and has not been run.
- A new model-storage dir has no persisted exclude filters, so a first reindex indexes the default
  file set (562 files here instead of 243). Seed `project_info.json` before comparing legs.
- Results come from one Python-heavy corpus.

## Alternatives considered

- **Keep bge-m3:** safe, but the weakest code retriever of the options and larger on disk.
- **F2LLM-v2-160M:** smaller still (about 0.32 GB, MTEB-Code 70.38); deferred because the 330M passed
  the VRAM gate.
- **0.6B-class embedders (F2LLM-0.6B, Qwen3-0.6B) and jina-reranker-v3:** do not fit with a reranker
  on 8 GB; they remain the workstation lineage.
- **jina-code-embeddings-0.5b, splade-code:** CC-BY-NC.
