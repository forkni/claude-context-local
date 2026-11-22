"""Read-only probe: FAISS Lloyd (as IndexIVF trains it) vs e-means for IVF coarse centroids.

Reads an on-disk code.index, never writes back. Prints JSON lines.

    .venv/Scripts/python.exe -I scripts/benchmark/probe_emeans_ivf.py <index>/code.index <label>

Result 2026-11-22 (63K and 54K real corpora): e-means lowered the k-means objective 2-4% but
recall at the production nprobe and training time were unchanged; not adopted. Re-run at ~1M
vectors (docs/adr/0083-faiss-index-parameter-policy.md, addendum).
"""

import json
import math
import sys
import time

import faiss
import numpy as np
from faiss.contrib.e_means import NumpyEmeans


def load(path):
    index = faiss.read_index(path)
    ivf = faiss.try_extract_index_ivf(index)
    if ivf is not None and ivf.direct_map.type == faiss.DirectMap.NoMap:
        ivf.make_direct_map()
    x = index.reconstruct_n(0, index.ntotal).astype(np.float32)
    faiss.normalize_L2(x)
    return x


def objective(x, c):
    c = c.copy()
    faiss.normalize_L2(c)
    idx = faiss.IndexFlatIP(c.shape[1])
    idx.add(c)
    s, a = idx.search(x, 1)
    sizes = np.bincount(a[:, 0], minlength=c.shape[0])
    return float(np.mean(2 - 2 * s[:, 0])), int((sizes == 0).sum()), float(sizes.std())


def lloyd(x, k, niter=10, seed=1234):
    d = x.shape[1]
    clus = faiss.Clustering(d, k)
    clus.niter = niter
    clus.spherical = True
    clus.max_points_per_centroid = 256
    clus.seed = seed
    q = faiss.IndexFlatIP(d)
    t = time.perf_counter()
    clus.train(x, q)
    dt = time.perf_counter() - t
    return faiss.vector_float_to_array(clus.centroids).reshape(k, d), dt


def emeans(x, k, nepochs, seed=1234):
    e = NumpyEmeans(x.shape[1], k, nepochs=nepochs, spherical=True, seed=seed)
    t = time.perf_counter()
    c, _ = e.train(x)
    dt = time.perf_counter() - t
    return np.ascontiguousarray(c, dtype=np.float32), dt


def recall(x, c, q_idx, gt, nprobes, ks=(10, 210)):
    d = x.shape[1]
    quant = faiss.IndexFlatIP(d)
    cc = c.copy()
    faiss.normalize_L2(cc)
    quant.add(cc)
    ivf = faiss.IndexIVFFlat(quant, d, c.shape[0], faiss.METRIC_INNER_PRODUCT)
    ivf.is_trained = True
    ivf.add(x)
    out = {}
    for npb in nprobes:
        ivf.nprobe = npb
        t = time.perf_counter()
        _, ids = ivf.search(x[q_idx], max(ks))
        dt = (time.perf_counter() - t) / len(q_idx) * 1000
        r = {}
        for kk in ks:
            hit = [
                len(set(ids[i, :kk]) & set(gt[i, :kk])) / kk for i in range(len(q_idx))
            ]
            r[f"R@{kk}"] = round(float(np.mean(hit)), 4)
        r["ms_per_q"] = round(dt, 3)
        out[npb] = r
    return out


def main():
    path, label = sys.argv[1], sys.argv[2]
    x = load(path)
    n, d = x.shape
    k = max(1, min(round(4 * math.sqrt(n)), n // 39))
    prod_nprobe = max(1, min(k, max(math.ceil(0.5 * k), math.ceil(420 * k / n))))
    rng = np.random.RandomState(0)
    q_idx = rng.choice(n, 1000, replace=False)
    flat = faiss.IndexFlatIP(d)
    flat.add(x)
    _, gt = flat.search(x[q_idx], 210)
    nprobes = sorted({max(1, k // 50), max(1, k // 20), k // 10, k // 4, prod_nprobe})
    print(
        json.dumps(
            {"corpus": label, "n": n, "d": d, "nlist": k, "prod_nprobe": prod_nprobe}
        ),
        flush=True,
    )

    runs = [
        ("lloyd_niter10", lambda: lloyd(x, k, 10)),
        ("lloyd_niter25", lambda: lloyd(x, k, 25)),
    ]
    for ep in (1, 2, 5):
        runs.append((f"emeans_ep{ep}", lambda ep=ep: emeans(x, k, ep)))
    for name, fn in runs:
        c, dt = fn()
        obj, empty, sd = objective(x, c)
        rec = recall(x, c, q_idx, gt, nprobes)
        print(
            json.dumps(
                {
                    "corpus": label,
                    "method": name,
                    "train_s": round(dt, 2),
                    "obj": round(obj, 5),
                    "empty_lists": empty,
                    "list_size_sd": round(sd, 1),
                    "recall": rec,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
