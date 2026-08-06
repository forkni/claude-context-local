# Chunk-size A/B: `max_chunk_lines` ∈ {60, 100, 160} — 2026-08-06

## Verdict: REJECTED — `max_chunk_lines` stays 100 (live default, unchanged)

Neither alternative arm clears the paired-CI adoption gate (methodology rule 7,
`RECALL_CAMPAIGN_CLOSEOUT_20260802.md:83-93`):

- **60**: CI **excludes** zero but in the wrong direction — dMRR **−0.0646**, 95% CI
  `[-0.1190, -0.0101]`, 9/48 queries moved. Materially and significantly worse.
- **160**: CI **includes** zero — dMRR +0.0047, 95% CI `[-0.0262, +0.0356]`, 4/48 queries
  moved. Indistinguishable from baseline; the gate requires the CI to exclude zero for
  adoption, so this does not ship despite the positive point estimate.

`ChunkingConfig.max_chunk_lines` (`search/config.py`) stays at its current default, 100.
Config and index were restored to the pre-A/B baseline and verified (see Protocol).

## Motivation (`evaluate-rag` skill audit, gap G3)

`max_chunk_lines=100` had only ever been justified from corpus shape
(`CHUNKING_CORPUS_ANALYSIS_20260728.md:269`: "derived value 97 = p90 lines 78 × 1.25 →
effectively optimal") — never A/B'd against retrieval metrics. This is the first retrieval-
metric measurement of the parameter.

## Protocol

- **Arms**: `max_chunk_lines` ∈ {60, 100, 160}, `max_split_chars=3000` and `sizing_mode`
  (`adaptive`) held fixed at their live values for every arm. ×2 rounds per arm.
- **Procedure**: `search_config.json` backed up, then per arm: edit the value (hot-reloads on
  mtime), full non-incremental reindex (`tools/batch_index.py --mode force`), two rounds of
  `./scripts/benchmark/run_benchmark.sh --split train` and `--split val` (63q canonical
  golden set, category D excluded by default). `PYTHONHASHSEED=0` pinned by the harness's own
  re-exec guard (ADR-0021).
- **Chunk counts confirm each reindex actually changed the corpus** (plan verification item
  7 — a silently-unreindexed arm was the primary failure mode this design was exposed to):

  | arm (`max_chunk_lines`) | chunks added (full reindex) |
  |---|---|
  | 60 | 2,434 |
  | 100 (baseline) | 2,323 |
  | 160 | 2,229 |

  Monotonic and in the expected direction (smaller line cap → more AST-block splits → more
  chunks). The final restore-reindex back to 100 also produced exactly 2,323 chunks, matching
  the arm-100 run — confirms the restore round-trips cleanly, not just the config file.
- **Restore**: config restored byte-identical from `.bak` (`cmp`-verified), full force
  reindex back to baseline shape. Both confirmed after the run completed.
- **Rounds were byte-identical within every arm** (r1 == r2 on every metric, every query) —
  the expected result on a determinism-pinned substrate (ADR-0021, "2-agreeing-rounds" rule
  retired for exactly this reason); recorded here as confirmation, not as new evidence.
- **Combined train+val scoring**: the harness's `--split` flag takes one value, so train and
  val were run separately and their `per_query` arrays merged post-hoc (48 = 35 train + 13
  val) before feeding the merged file pair into `run_sscg_benchmark.py --compare` for the
  paired-CI gate — this is exactly the "computable post-hoc from already-saved `per_query`
  arrays, zero re-runs" property methodology rule 7 was built around, applied one step further
  (merge-then-compare, still zero new search calls beyond the 12 runs already needed).

## Results (round 1; round 2 identical, see above)

| arm | n | mrr | recall@5 | recall@10 | ndcg@5 | hit_rate@5 |
|---|---|---|---|---|---|---|
| 60 | 48 | 0.787 | 0.641 | 0.750 | 0.658 | 0.979 |
| 100 (baseline) | 48 | 0.852 | 0.662 | 0.769 | 0.694 | 1.000 |
| 160 | 48 | 0.857 | 0.673 | 0.781 | 0.701 | 1.000 |

### Paired deltas vs baseline (100), train+val n=48

| comparison | metric | mean Δ | SE | 95% CI | n_moved |
|---|---|---|---|---|---|
| 100 → 60 | mrr | **−0.0646** | 0.0278 | **[−0.1190, −0.0101]** | 9/48 |
| 100 → 60 | recall@5 | −0.0205 | 0.0142 | [−0.0483, +0.0074] | 6/48 |
| 100 → 60 | ndcg@5 | −0.0359 | 0.0165 | [−0.0682, −0.0036] | 16/48 |
| 100 → 160 | mrr | +0.0047 | 0.0158 | [−0.0262, +0.0356] | 4/48 |
| 100 → 160 | recall@5 | +0.0111 | 0.0080 | [−0.0046, +0.0268] | 2/48 |
| 100 → 160 | ndcg@5 | +0.0069 | 0.0077 | [−0.0083, +0.0220] | 7/48 |

## Reading

- **60 is a clean, gate-clearing rejection** — the CI excludes zero on both mrr and ndcg@5,
  in the losing direction. Half-size chunks (60 lines vs 100) fragment retrieval targets
  enough to cost real MRR (9/48 queries moved, several by a full rank — e.g. Q19 "encode and
  decode embeddings" dMRR −0.857, Q69 dMRR −0.800). Not adopted, and doesn't need a re-run to
  be sure.
- **160 is a plausible small win that doesn't clear the bar.** Every point estimate moved in
  the positive direction (mrr, recall@5, recall@10, ndcg@5 all up), but every CI still spans
  zero — n=48 (and n=63 with test included) isn't enough queries to separate a real +0.005-ish
  MRR effect from noise at this SE (~0.016). This is the same "13-15-query splits are noisy"
  caveat as `CANON_SPLIT_REPORT_20260806.md`, one level up: 48 queries is enough to convict 60
  but not enough to acquit-with-confidence 160.
- **No adoption cost was priced in** because nothing is being adopted — but for the record,
  had 160 cleared the gate, shipping it would still require a chunk-format-affecting config
  default change plus a forced reindex for every existing user, per the sibling-merge
  precedent (`CHUNKING_SIBLING_MERGE_AB_20260728.md`).

## Reopening condition

160's positive-but-inconclusive signal is the only lead here. A future re-run on the full 63q
set (adding the 15-query test split back in, accepting it's then partially "tuned against" —
a one-time exception, not a new practice) or a larger golden set would sharpen the CI enough
to decide 160 either way. Until then, 100 stays the default; this is a measured, gate-based
non-adoption, not an unexamined default.

## Artifacts

`benchmark_results/chunksize_ab_20260806/` — `arm{60,100,160}_{train,val}_r{1,2}.json` (12
raw runs), `arm{60,100,160}_trainval_r{1,2}.json` (6 post-hoc merged files used for the
paired-CI compare), `run.log` (full reindex + benchmark transcript), `run_ab.sh` (driver).
