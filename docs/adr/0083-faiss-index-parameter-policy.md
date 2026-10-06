# FAISS index parameter policy: inner-product IVF, 50K flat ceiling, size-derived `nlist`/`nprobe`

Status: accepted
Date: 2026-10-05

## Context

A study of the FAISS wiki's optimisation guidance against `search/faiss_index.py` found one
correctness bug and a parameter policy that had never been measured:

- **IVF indexes were built with `METRIC_L2`.** `faiss.IndexIVFFlat(quantizer, d, nlist)` defaults
  to L2 when the metric is omitted, so any project above the IVF threshold returned squared L2
  distances (0.0 for an exact match, larger = worse) where every score consumer (ranking
  heuristics, TM2C2 normalisation in the reranker, descending sort, display) assumes inner
  products (1.0 for an exact match, larger = better). Rank order on unit-norm vectors is the same,
  so the symptom was inverted boosts and a broken dense normalisation rather than wrong neighbours.
  The L2 quantizer also disabled spherical k-means.
- **Fixed `nlist = min(100, max(10, d // 8))` (always 100 at d=1024) and `nprobe = 16`**, chosen
  without a recall target. `IVF_MIN_VECTORS = 10000` switched from exact to approximate search at a
  size where exact search still took ~1 ms per query.
- `remove_positions` reconstructed kept vectors one row at a time and *skipped* failures while the
  caller renumbered survivors assuming none were skipped; `reconstruct_embeddings` rebuilt a
  `{chunk_id: position}` dict of size N per call; `get_similar_chunks_batched` bypassed the wrapper;
  a metadata-filtered dense search fetched `k*3` candidates and never widened.

`scripts/benchmark/probe_faiss_index_params.py` was written to settle the parameters: pull every
vector out of an on-disk index read-only, build exact ground truth with `IndexFlatIP` at depth 420
(`leg_search_depth` at the k=84 ceiling), time flat search by thread count, and sweep
inner-product `IndexIVFFlat` over `nlist` x `nprobe` x `parallel_mode`, scoring recall with
`knn_intersection_measure` at k in {1, 10, 35, 70, 210}. Results:
`evaluation/FAISS_INDEX_PARAMS_20261005.md`, raw JSON `benchmark_results/faiss_index_params_20261005_230701.json`.
The 21,910-vector project that motivated the original `nprobe` comment no longer exists locally;
the largest real corpus available was the union of four real indexes (17,197 vectors), plus two
real projects (7,250 and 2,925) and clustered synthetic corpora at 50K and 100K.

### What the probe showed (d=1024, bge-m3, 24 OpenMP threads, faiss-cpu 1.15.1)

Flat `IndexFlatIP`, p50 ms, nq = 1 / 35 / 210 (k=420):

| N | nq=1 | nq=35 | nq=210 |
|---|---|---|---|
| 2,925 | 0.3 | 1.4 | 5.5 |
| 7,250 | 1.1 | 4.0 | 9.2 |
| 17,197 | 3.7 | 14.5 | 22.3 |
| 49,800 (synthetic) | 5.5 | 54.4 | 70.3 |
| 99,800 (synthetic) | 9.4 | 135.8 | 113.8 |

IVF on the 17,197-vector real corpus (`-1` padding was 0 everywhere; imbalance 1.2-1.4):

| nlist | nprobe | R@10 | R@210 | nq=1 p50 ms | nq=35 p50 ms |
|---|---|---|---|---|---|
| 100 | 16 (old policy) | 0.980 | 0.941 | 0.5 | 4.2 |
| 100 | 64 | 1.000 | 0.999 | 4.3 | 12.5 |
| 64 | 32 | 0.998 | 0.994 | 3.1 | 9.7 |
| 128 | 64 | 0.998 | 0.995 | 2.0 | 9.7 |
| 256 | 128 | 1.000 | 0.998 | 3.4 | 10.5 |
| 440 (4 sqrt N) | 128 | 0.999 | 0.994 | 2.8 | 7.4 |

- Real code embeddings are *less* clustered than the synthetic Gaussians, not more: recall@210
  >= 0.99 against exact search needs 29-64% of the lists probed on real data (7,250-vector project:
  nlist 100 -> nprobe 64; 2,925: 100 -> 64) versus ~3% on synthetic data. The old 100/16 scored
  R@210 = 0.941 (17K) and 0.947 (7,250).
- At the recall target, IVF is **not faster than flat** at 17K (nq=1 ~3 ms either way) and the
  multi-hop batch (nq=35) is at best on par. The crossover where exact search becomes expensive is
  around 50K vectors (nq=35 p95 65 ms synthetic). Training `4 sqrt N` centroids costs 1.9 s at 50K
  and 4.7 s at 100K.
- `parallel_mode = 1` (parallelise over probed lists) was slower than the default at every
  nq, including nq=1 (median 0.05-0.5x the default's throughput).
- Thread count: fewer threads help nq=1 slightly at small N (3.7 -> 1.6 ms at 17K with 8 threads)
  and hurt batches everywhere; not worth a process-wide knob while torch shares the OpenMP pool.
- Earlier synthetic probes (plan stage): HNSW32 R@10 0.22-0.76 at d=1024 and no `remove_ids`;
  SQ8 lossy and slower; SQfp16 exact but slower than flat.

## Decision

1. **Metric.** `create()` passes `faiss.METRIC_INNER_PRODUCT`. An on-disk IVF index that reports
   `METRIC_L2` is a legacy index: `load()` logs one WARNING ("reindex recommended") and `search()`
   converts `ip = 1 - d^2 / 2` so scores stay inner products; `describe()["metric"]` reports
   `"ip"` or `"l2_legacy"`. Legacy indexes keep their on-disk `nlist` until the next rebuild.
2. **Flat ceiling.** `IVF_MIN_VECTORS = 50_000`. Exact search is preferred until it is genuinely
   slow (recall-over-speed preference); every real corpus seen so far is flat under this rule.
3. **IVF sizing from the vector count.** `create(dimension, "ivf")` requires `expected_count`
   (`ValueError` otherwise); `CodeIndexManager.add_embeddings` passes the first-batch size and
   `remove_positions` passes the kept count.
   - `ivf_nlist_for(n) = max(1, min(round(4 sqrt n), n // 39))`: the low end of FAISS's
     4-16 sqrt(N) range (fewer, larger lists keep recall high on weakly clustered data), capped so
     every centroid has >= 39 training points (`IVF_MIN_TRAIN_PER_CENTROID`).
   - `ivf_nprobe_for(nlist, n) = max(1, min(nlist, max(ceil(0.5 nlist), ceil(420 nlist / n))))`:
     half the lists (`IVF_PROBE_FRACTION`, inside the measured 0.29-0.64 band), raised so a probe
     can visit at least 420 vectors (`IVF_MIN_VISITED`, no `-1` padding at the leg-depth ceiling).
   - `_configure_ivf` applies `nprobe` on every `create()` and `load()` from `ntotal` (falling back
     to `expected_count` on an empty index); a persisted `nprobe` is ignored. A legacy
     `nlist = 100` index at 21,910 vectors is therefore searched with `nprobe = 50` after load.
4. **Bit-identical cheap wins.** `remove_positions` uses `reconstruct_n` + boolean mask and raises
   on a reconstruct failure instead of skipping (closes the metadata-desync hole);
   `position_of()` / `reconstruct_batch()` replace per-row lookups and `get_similar_chunks_batched`
   goes through the wrapper. `CodeIndexManager.search` widens a metadata-filtered dense search x4
   from `k*3` up to `FILTERED_SEARCH_CAP = 4096` (or `ntotal`) until k survivors, mirroring the
   ADR-0067 loop in `get_similar_chunks`.
5. **Not shipped**, each with a revisit trigger:

   | Option | Why not | Revisit when |
   |---|---|---|
   | `parallel_mode = 1` | slower at every nq measured | FAISS changes the implementation, or N > 500K |
   | `omp_set_num_threads` in `search()` | helps nq=1 only, hurts batches, torch shares the pool | FAISS > 20% of end-to-end latency on a flat index |
   | HNSW | R@10 <= 0.76 at d=1024, no incremental removal | N > 500K and removal moves to tombstones |
   | SQ8 / SQfp16 / PQ | slower than flat here, SQ8 lossy | index > 25% of RAM or N > 1M |
   | `IO_FLAG_MMAP`, OnDiskInvertedLists | 12.8 MB index loads in ms | load > 1 s or index > 50% of RAM |
   | `IDSelector` filtered search | needs an id -> filter bitmap per query | the widening loop hits its cap in production logs |
   | GPU FAISS | `faiss-cpu` is installed; the index never leaves the CPU, GPU is torch embedding only | FAISS > 20% of latency or N > 1M. If `faiss-gpu` is installed, re-run the probe: items 1, 3 and 4 hold (metric and `nprobe` are set before `index_cpu_to_all_gpus`), but the flat ceiling and `nprobe` band were measured on the CPU |

## Consequences

- Scores from an IVF index are inner products in [-1, 1] like the flat index; boosts and TM2C2
  normalisation behave the same above and below the threshold.
- Any project indexed as IVF under the old policy (10K-50K vectors) is still searched correctly
  via the shim, with `nprobe` widened to the policy value, but should be reindexed to drop the
  legacy metric and become flat.
- `expected_count` is a required argument for IVF creation; tests that build small IVF fixtures
  must pass it (`nlist` is `N // 39` for N < 1,521).
- Flat search above ~17K vectors costs 3-4 ms per query and ~15 ms for a 35-query multi-hop
  batch; the dense leg stays exact up to 50K. `IVF_MIN_VECTORS` is a module constant, not a
  `search_config.json` field.
- Unfiltered results are bit-identical to the previous release (P2/P4 are pure refactors;
  P1/P3 only change indexes above the old threshold, of which none exist locally).
- `docs/adr/0001-faiss-as-vector-index-backend.md`'s 2026-09-30 amendment (10,000 / `nprobe = 16`)
  is superseded by this record; ADR-0082's index-kind invariant (kind frozen by the first batch)
  is unchanged.
