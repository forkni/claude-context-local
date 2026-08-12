# Search Performance & Benchmark Reference

This file documents **mechanisms and verdicts** — what the retrieval/rerank pipeline does structurally, and what tuning levers have already been
tried and either shipped, rejected, or deferred. It deliberately does **not** carry pinned benchmark numbers: those drift out of date every time the
dataset or config changes, which has happened repeatedly (see "Golden dataset" below). **`docs/BENCHMARKS.md` is the single source of truth for
current numbers**; `SKILL.md` states the current headline once. If you need a number to reason about, get it from there, not from this file.

## Contents

- Benchmark determinism (ADR-0021)
- Retrieval funnel & reranker budget (mechanism)
- Tuning levers tried and their verdicts
- Reranker selection
- Golden dataset
- Re-run benchmark
- Line-overlap metrics (LR / LP / LIoU)
- Mode selection guide
- Result reliability

---

## Benchmark determinism (ADR-0021)

Run-to-run MRR/Recall deltas on identical config **are not GPU floating-point nondeterminism.** That was the original hypothesis and it was tested
and falsified: pinning GPU kernels (`torch.use_deterministic_algorithms`, cuBLAS workspace config) changed nothing — same flip count as the
unpinned control.

**Actual root cause:** unpinned `PYTHONHASHSEED` → Python `set` iteration order → different pool composition on ties during fusion/dedup, not
reranker score noise. Pinning `PYTHONHASHSEED=0` gives **0 flips / 0.0000 spread at zero performance cost** — the benchmark harness
(`scripts/benchmark/run_sscg_benchmark.py`) now auto-re-execs itself with `PYTHONHASHSEED=0` set, so this is handled automatically for any run
through the standard entry point. A `--deterministic-gpu` flag exists for diagnostic use (`utils/determinism.py`) but is not part of the standard
config surface — it was evaluated and deliberately not promoted to a config knob.

**Practical consequence:** with the harness's default auto-re-exec, two runs of the same query set against the same index should now produce
byte-identical results. If you see drift between two runs, first suspect a **substrate change** — index content differs (reindex happened, files
changed) or config differs — before suspecting measurement noise. The historical "±0.01–0.025 noise band, treat deltas <0.03 as insignificant"
guidance predates this fix and no longer applies to properly-pinned runs.

---

## Retrieval funnel & reranker budget (mechanism)

Full mechanism (per-leg pool sizing, `top_k_candidates`, `max_results_multiplier`, the `k*5` widening rule) is documented in
[advanced-features.md](advanced-features.md) → "Retrieval Funnel & Reranker Budget" — this section is a pointer, not a duplicate, since the numbers
there are current config values, not benchmark results.

**`pool_hit_rate`** (defined in `evaluation/metrics.py`, measured by `scripts/benchmark/run_sscg_benchmark.py`) is the diagnostic metric this funnel
exists to keep near 1.0: did every gold chunk for a query reach the pre-rerank candidate pool at all? A `pool_hit_rate` below 1.0 means some misses
are **retrieval misses** (gold never entered the pool — a funnel/recall problem) rather than **ranking misses** (gold was in the pool but ranked
below the cutoff — a reranker/fusion-ordering problem). These require different fixes; check which one you're looking at before tuning.

**Never benchmark deep recall by raising `--k` alone.** Multi-hop/ego-graph expansion pool sizes scale with `k`, so a very large `k` (e.g. 50)
collapses ranking quality rather than improving it — measure recall headroom via pool instrumentation (`pool_hit_rate`, `avg_pool_size`) at the
production `k`, not by inflating `k` past its normal range.

---

## Tuning levers tried and their verdicts

Every row below was measured (not just theorized) against the canonical or expanded golden set. Do not re-propose a REJECTED lever without new
evidence beyond what's cited — most of these were re-tested more than once.

| Lever | Verdict | Why |
|---|---|---|
| Multi-hop `expansion_k` floor `max(5,…)` | **Rejected** | No gate win; within run-to-run noise band |
| Ego-graph `min_similarity_threshold` 0.15→0.05 | **Rejected** | No gate win; within noise |
| `expansion_mode: "ppr"` (personalized PageRank ego-graph) | **Rejected for recall; shipped as opt-in latency profile** | Aggregate MRR flat but causal per-query losses replicated across sessions (e.g. two queries losing all measured headroom); separately measured **−15.8% latency** with recall@20 −0.025, MRR flat — shipped as a documented opt-in config in `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md` for latency-sensitive use, default stays `"bfs"` |
| BM25 stopword removal | **Rejected** | Recall@5 −0.0349, MRR −0.0138 — both past the regression threshold |
| Intent-adaptive fusion weights (per-intent static profiles) | **Rejected and deleted** (ADR-0019) | Pre-registered A/B: negative on both datasets, one query's score collapsed 1.000→0.333 in every replicate; the config surface (`INTENT_WEIGHT_PROFILES` and related) was removed from the codebase, not just disabled |
| `bm25_reserved_slots` (hop-1 fused-tail injection) | **Rejected** | 9/9 sweep runs failed to rescue the target query; MRR regressed −0.017 to −0.034 across variants |
| `hop1_reserved_slots` (multi-hop rerank window reserve) | **Shipped, default 6** (ADR-0013) | Different mechanism than the rejected `bm25_reserved_slots` above — reserves at the multi-hop rerank window rather than hop-1 fusion; positive on both canonical and expanded sets |
| Final-pool-assembly reserve (raw-BM25-top-3 rescue) | **Spec'd and deferred** | Best variant rescued only run-to-run-flapping queries with zero collateral damage, but zero *stable* (reproducible) misses fixed — not worth shipping until a lever with real signal is found |
| `centrality_alpha` > 0.0 | **Rejected** | Higher values cost recall; replicated finding. Default stays `0.0`, so `blended_score` reduces to `semantic_score` |
| Query expansion (curated concept-variant legs, ADR-0012) | **Ships disabled** | Feature is complete and functional but flat-to-negative against controls; most candidate target queries turned out not to be true vocabulary gaps (fixed instead by other levers), and expansion floods the pool for queries that were already fine. Re-eval closed (ADR-0012 follow-up); stays off by default |
| fp32 reranker dtype (vs. shipped bf16) | **Rejected for determinism** | Flip count unchanged, and fp32's own run-to-run spread was *worse* than bf16's — confirms the root cause is fusion/pool-composition order (see ADR-0021 above), not weight precision. `listwise_dtype` config knob ships anyway, default `"auto"`, harmless |

---

## Reranker selection

**Deployed:** `jinaai/jina-reranker-v3` (listwise cross-encoder) on this machine's 24GB workstation config, alongside the F2LLM-v2-0.6B embedder.
Listwise means it scores the whole candidate pool in relative context in a single pass, rather than each candidate independently — this is why pool
size (`top_k_candidates`, see funnel section above) directly affects both latency and ranking quality.

**Alternatives compared and not adopted:**

- `BAAI/bge-reranker-v2-m3` — loads fine, but scored measurably worse on this code corpus (general-purpose model, not code-tuned) and several times
  slower per query.
- `Alibaba-NLP/gte-reranker-modernbert-base` — the recommended choice for ≤8GB GPUs where `jina-reranker-v3`'s listwise long-context design doesn't
  fit; still a reasonable fallback, just not the deployed default on higher-VRAM hardware.

---

## Golden dataset

- **Canonical set** (`evaluation/golden_dataset.json`): **77 total queries, 63 non-D queries** (`_meta.total_queries`), split train=43/val=16/test=18.
  `recommended_k: 7`.
- **Expanded set** (`evaluation/golden_dataset_expanded.json`): **147 total queries, 133 non-D queries** — broader, harder query mix than the
  canonical set; used for A/B tests that need more statistical power or coverage outside the canonical 63.
- **⚠️ Stale metadata trap:** `golden_dataset.json`'s own `_meta.current_metrics` block still cites a 2026-06-26 DSPy agent eval. That subsystem was
  removed wholesale in v0.23.0 (ADR-0016, 13 files / 4,849 lines deleted). Treat that block as stale historical metadata, not a current benchmark
  status — `docs/BENCHMARKS.md` is current, this file's `_meta` block is not.
- After any refactor touching chunk boundaries or dedup logic, run `scripts/benchmark/audit_golden_dataset.py` to catch golden IDs that no longer
  resolve — this has caught real drift before (e.g. `dedup_key` normalization gaps after a chunking refactor).

---

## Re-run benchmark

```bash
# Single mode (default hybrid):
./scripts/benchmark/run_benchmark.sh --project-path <project-path>

# Specific mode:
./scripts/benchmark/run_benchmark.sh --project-path <project-path> --search-mode bm25
./scripts/benchmark/run_benchmark.sh --project-path <project-path> --search-mode semantic

# Weight sweep (4 BM25/dense splits):
./scripts/benchmark/run_benchmark.sh --project-path <project-path> --sweep
```

`scripts/benchmark/run_sscg_benchmark.py` is the underlying runner and supports the canonical/expanded golden sets directly; see its `--help` for
current flags (dataset selection, `--search-mode`, deterministic-GPU diagnostics).

---

## Line-Overlap Metrics (LR / LP / LIoU)

In addition to chunk-level Recall/MRR/NDCG, the runner computes **Chroma-style line-range overlap** between retrieved chunks and each golden query's
`expected_primary` line ranges:

| Metric | Symbol | Meaning |
|--------|--------|---------|
| Line Recall | LR | Fraction of expected source lines that appear somewhere in the top-k retrieved chunks |
| Line Precision | LP | Fraction of retrieved source lines that are actually relevant (the rest is surrounding-code overhead from whole-chunk retrieval) |
| Line IoU | LIoU | Intersection over union of the expected and retrieved line sets |

**Interpretation pattern that holds across runs:** LP and LIoU are structurally lower than LR, and that's expected, not a quality problem — chunks
span whole functions/classes, so retrieving the *correct* chunk always brings in surrounding lines beyond the exact golden range. A high LR with
low LP/LIoU means the search is finding the right regions of code; it does not mean the search is imprecise. Current numbers: `docs/BENCHMARKS.md`.

---

## Mode Selection Guide

| Mode | Best for |
|------|---------|
| `auto` (default) | Most queries — routes intelligently |
| `bm25` | Exact function/class names, API calls |
| `hybrid` | Concepts + exact terms combined |
| `semantic` | Intent/concept queries, fuzzy matching |

**Practical rule:** Start with `auto`, `k=7`. Switch to `bm25` when you know the exact symbol name. Use `k=10` for architectural/global queries.

---

## Result Reliability

- **Not all primaries rank first.** MRR well below 1.0 on every measured run means rank-1 alone is not reliable — always scan all `k` results before
  concluding a query has no answer, rather than trusting the top hit in isolation.
- **Why `k=7` over `k=5`:** targets may rank 6th or 7th on complex or multi-target queries; `golden_dataset.recommended_k=7` reflects this measured
  pattern, not a default chosen arbitrarily.
- **When rank-1 is most reliable:** exact symbol lookup, small function discovery ("get X", "validate Y") — narrow, unambiguous queries.
- **When you must scan all results:** class overviews, sibling pairs ("encode and decode", "save and load"), and any query where a module-summary
  chunk (see `advanced-features.md` → "A2: File-Level Summary Chunks") might legitimately outrank the specific implementation you actually want.
- Current MRR/Recall/Hit@k numbers for all of the above: `docs/BENCHMARKS.md`.
