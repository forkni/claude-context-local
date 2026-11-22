"""Read-only G6 probe: single-query latency, flat vs deployed IVF, on a real on-disk index."""

import json
import math
import statistics as st
import sys
import time

import faiss
import numpy as np


path = sys.argv[1]
src = faiss.read_index(path)
ivf0 = faiss.try_extract_index_ivf(src)
if ivf0 is not None and ivf0.direct_map.type == faiss.DirectMap.NoMap:
    ivf0.make_direct_map()
x = src.reconstruct_n(0, src.ntotal).astype(np.float32)
faiss.normalize_L2(x)
n, d = x.shape
nlist = max(1, min(round(4 * math.sqrt(n)), n // 39))
nprobe = max(1, min(nlist, max(math.ceil(0.5 * nlist), math.ceil(420 * nlist / n))))

flat = faiss.IndexFlatIP(d)
flat.add(x)
t = time.perf_counter()
q = faiss.IndexFlatIP(d)
ivf = faiss.IndexIVFFlat(q, d, nlist, faiss.METRIC_INNER_PRODUCT)
ivf.train(x)
ivf.add(x)
build_ivf = time.perf_counter() - t
ivf.nprobe = nprobe
t = time.perf_counter()
f2 = faiss.IndexFlatIP(d)
f2.add(x)
build_flat = time.perf_counter() - t

rng = np.random.RandomState(1)
qs = x[rng.choice(n, 200, replace=False)]
K = 210


def bench(index, threads):
    faiss.omp_set_num_threads(threads)
    for i in range(10):
        index.search(qs[i : i + 1], K)
    ts = []
    for i in range(len(qs)):
        t0 = time.perf_counter()
        index.search(qs[i : i + 1], K)
        ts.append((time.perf_counter() - t0) * 1000)
    ts.sort()
    return round(st.median(ts), 2), round(ts[int(0.95 * len(ts))], 2)


out = {
    "n": n,
    "nlist": nlist,
    "nprobe": nprobe,
    "build_ivf_s": round(build_ivf, 2),
    "build_flat_s": round(build_flat, 3),
    "max_threads": faiss.omp_get_max_threads(),
}
maxt = faiss.omp_get_max_threads()
for th in sorted({1, 8, maxt}):
    out[f"flat_t{th}_p50_p95"] = bench(flat, th)
    out[f"ivf_t{th}_p50_p95"] = bench(ivf, th)
try:
    import torch

    if torch.cuda.is_available():
        X = torch.from_numpy(x).cuda().half()
        ts = []
        for i in range(len(qs)):
            qq = torch.from_numpy(qs[i]).cuda().half()
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            s, ix = torch.topk(X @ qq, K)
            ix.cpu()
            ts.append((time.perf_counter() - t0) * 1000)
        ts = sorted(ts[10:])
        out["torch_fp16_gpu_p50_p95"] = (
            round(st.median(ts), 3),
            round(ts[int(0.95 * len(ts))], 3),
        )
except ImportError:
    pass
print(json.dumps(out))
