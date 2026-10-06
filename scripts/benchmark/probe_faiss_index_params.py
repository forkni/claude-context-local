#!/usr/bin/env python
"""Measure FAISS index parameters against exact ground truth, read-only.

Background: ``search/faiss_index.py`` chooses ``IndexFlatIP`` up to
``IVF_MIN_VECTORS`` vectors and ``IndexIVFFlat`` above it. Before ADR-0083 the
IVF parameters were fixed (``nlist`` = ``min(100, max(10, d // 8))`` = 100 at
d=1024, ``nprobe`` = 16) and the threshold was 10,000; none of those numbers
had been measured against a recall target at the depth the hybrid funnel
actually asks for (``leg_search_depth`` = ``max(30, k*5)``, i.e. 420 at the
k=84 ceiling). The FAISS wiki's rules of thumb (``nlist`` in
4*sqrt(N)..16*sqrt(N), at least 39 training points per centroid, ``nprobe``
from a measured recall target) are for generic data, and real code embeddings
turned out to be far less clustered than synthetic test data, so the policy
(``IVF_MIN_VECTORS``, ``ivf_nlist_for``, ``ivf_nprobe_for``) is derived from a
sweep on real vectors. Re-run this probe whenever a real corpus above the
threshold appears or the FAISS build changes (e.g. ``faiss-gpu``).

What this probe does for each dataset:

1. Pulls every stored vector out of an existing on-disk index with
   ``reconstruct_n`` (read-only; no project file is touched), or generates a
   clustered synthetic corpus at a requested size.
2. Holds out ``--nq`` vectors as queries and builds exact ground truth with
   ``IndexFlatIP`` at depth 420 (the leg-depth ceiling).
3. Times the flat index at nq in {1, 35, 210} for several OpenMP thread
   counts (p50/p95), so the flat-vs-IVF crossover can be read off directly.
4. Sweeps ``IndexIVFFlat`` with ``METRIC_INNER_PRODUCT`` over a grid of
   ``nlist`` x ``nprobe`` x ``parallel_mode``: recall against the exact top-k
   at k in {1, 10, 35, 70, 210} (``knn_intersection_measure``), the rate of
   ``-1`` padding at depth 210 (a probe that visits too few vectors), the
   inverted-list imbalance factor, train+add time and search latency.
5. Writes ``benchmark_results/faiss_index_params_<ts>.json`` and a Markdown
   report (``evaluation/FAISS_INDEX_PARAMS_<date>.md`` by default).

Reused, not re-implemented: ``evaluation.index_locator.storage_root`` for the
project storage directory; ``search.search_executor.leg_search_depth``'s
arithmetic is restated as the 420 ceiling rather than imported (that function
needs a ``SearchConfig`` and this probe must not load one).

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_faiss_index_params.py \
        --project TD_Glossary --project claude-context-local --combine-all \
        --synthetic 50000 --synthetic 100000
    .venv/Scripts/python.exe scripts/benchmark/probe_faiss_index_params.py --quick
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import faiss  # noqa: E402
from faiss.contrib.evaluation import knn_intersection_measure  # noqa: E402

from evaluation.index_locator import storage_root  # noqa: E402


# Depth the hybrid funnel asks the dense leg for at the k=84 ceiling
# (leg_search_depth = max(30, k*5)); recall is reported at the funnel's
# common operating points below it.
LEG_DEPTH_CEILING = 420
RECALL_KS = (1, 10, 35, 70, 210)
PAD_DEPTH = 210

NLIST_CANDIDATES = (64, 100, 128, 256, 512)
NPROBE_CANDIDATES = (1, 2, 4, 8, 16, 32, 64, 128)
MIN_TRAIN_POINTS_PER_CENTROID = 39  # FAISS warns below this

DIM = 1024


# --------------------------------------------------------------------------
# Data sources
# --------------------------------------------------------------------------


def _project_index_paths(storage: Path) -> dict[str, Path]:
    projects = storage / "projects"
    out: dict[str, Path] = {}
    if not projects.is_dir():
        return out
    for d in sorted(projects.iterdir()):
        p = d / "index" / "code.index"
        if p.exists():
            out[d.name] = p
    return out


def load_project_vectors(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Read an on-disk index and return all stored vectors (read-only)."""
    index = faiss.read_index(str(path))
    ivf = faiss.try_extract_index_ivf(index)
    if ivf is not None and ivf.direct_map.type == faiss.DirectMap.NoMap:
        ivf.make_direct_map()  # in-memory only; nothing is written back
    vectors = index.reconstruct_n(0, index.ntotal).astype(np.float32)
    info = {
        "source": str(path),
        "index_type": type(index).__name__,
        "metric_type": int(index.metric_type),
        "ntotal": int(index.ntotal),
        "d": int(index.d),
    }
    if ivf is not None:
        info["nlist"] = int(ivf.nlist)
        info["nprobe"] = int(ivf.nprobe)
    return vectors, info


def synthetic_vectors(
    n: int, seed: int = 0, n_clusters: int = 64, d: int = DIM
) -> np.ndarray:
    """Clustered Gaussian mixture (unit-norm) so IVF has structure to exploit."""
    rng = np.random.default_rng(seed)
    centers = rng.standard_normal((n_clusters, d)).astype(np.float32)
    labels = rng.integers(0, n_clusters, n)
    x = centers[labels] + 0.6 * rng.standard_normal((n, d)).astype(np.float32)
    faiss.normalize_L2(x)
    return x


# --------------------------------------------------------------------------
# Measurement helpers
# --------------------------------------------------------------------------


def _timeit(fn, reps: int) -> dict[str, float]:
    fn()  # warm
    samples = []
    for _ in range(reps):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1e3)
    samples.sort()
    p95_idx = min(len(samples) - 1, int(math.ceil(0.95 * len(samples))) - 1)
    return {
        "p50_ms": round(statistics.median(samples), 3),
        "p95_ms": round(samples[p95_idx], 3),
        "reps": reps,
    }


def _recall_table(gt_ids: np.ndarray, ids: np.ndarray) -> dict[str, float]:
    out = {}
    for k in RECALL_KS:
        if k > gt_ids.shape[1] or k > ids.shape[1]:
            continue
        out[f"recall@{k}"] = round(
            float(knn_intersection_measure(ids[:, :k], gt_ids[:, :k])), 4
        )
    return out


def _nlist_grid(n: int) -> list[int]:
    max_nlist = max(1, n // MIN_TRAIN_POINTS_PER_CENTROID)
    grid = {c for c in NLIST_CANDIDATES if c <= max_nlist}
    four_sqrt = int(round(4 * math.sqrt(n)))
    for cand in (four_sqrt, max_nlist):
        if 1 <= cand <= max_nlist:
            grid.add(cand)
    # Repo default is 100 regardless of N; keep it even when under-trained so
    # the current policy is always in the table (flagged below).
    grid.add(100)
    return sorted(c for c in grid if c >= 1)


def measure_flat(
    xb: np.ndarray,
    xq: np.ndarray,
    thread_counts: list[int],
    reps: int,
) -> dict[str, Any]:
    flat = faiss.IndexFlatIP(xb.shape[1])
    start = time.perf_counter()
    flat.add(xb)
    build_s = time.perf_counter() - start
    batches = {"nq1": xq[:1].copy(), "nq35": xq[:35].copy(), "nq210": xq[:210].copy()}
    latency: dict[str, dict[str, Any]] = {}
    max_threads = faiss.omp_get_max_threads()
    for nt in thread_counts:
        faiss.omp_set_num_threads(nt)
        latency[str(nt)] = {
            name: _timeit(lambda q=q: flat.search(q, LEG_DEPTH_CEILING), reps)
            for name, q in batches.items()
            if len(q) > 0
        }
    faiss.omp_set_num_threads(max_threads)
    return {"build_s": round(build_s, 3), "latency_by_threads": latency}, flat


def measure_ivf_grid(
    xb: np.ndarray,
    xq: np.ndarray,
    gt_ids: np.ndarray,
    reps: int,
    nprobes: tuple[int, ...],
    parallel_modes: tuple[int, ...],
) -> list[dict[str, Any]]:
    n, d = xb.shape
    depth = min(LEG_DEPTH_CEILING, n)
    rows: list[dict[str, Any]] = []
    q1 = xq[:1].copy()
    q35 = xq[:35].copy()
    for nlist in _nlist_grid(n):
        quantizer = faiss.IndexFlatIP(d)
        ivf = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
        start = time.perf_counter()
        ivf.train(xb)
        train_s = time.perf_counter() - start
        start = time.perf_counter()
        ivf.add(xb)
        add_s = time.perf_counter() - start
        ivf.make_direct_map()
        imbalance = float(ivf.invlists.imbalance_factor())
        under_trained = n < MIN_TRAIN_POINTS_PER_CENTROID * nlist
        for nprobe in nprobes:
            if nprobe > nlist:
                continue
            ivf.nprobe = nprobe
            ivf.parallel_mode = 0
            dist, ids = ivf.search(xq, depth)
            recall = _recall_table(gt_ids[:, :depth], ids)
            pad_depth = min(PAD_DEPTH, depth)
            pad_rate = float(np.mean(ids[:, :pad_depth] == -1))
            score_min = float(dist[ids != -1].min()) if np.any(ids != -1) else None
            score_max = float(dist[ids != -1].max()) if np.any(ids != -1) else None
            for pm in parallel_modes:
                ivf.parallel_mode = pm
                row = {
                    "nlist": nlist,
                    "nprobe": nprobe,
                    "parallel_mode": pm,
                    "under_trained": under_trained,
                    "train_s": round(train_s, 3),
                    "add_s": round(add_s, 3),
                    "imbalance_factor": round(imbalance, 3),
                    "pad_rate@210": round(pad_rate, 4),
                    "score_min": None if score_min is None else round(score_min, 4),
                    "score_max": None if score_max is None else round(score_max, 4),
                    **recall,
                    "lat_nq1": _timeit(
                        lambda ix=ivf: ix.search(q1, LEG_DEPTH_CEILING), reps
                    ),
                    "lat_nq35": _timeit(
                        lambda ix=ivf: ix.search(q35, LEG_DEPTH_CEILING), reps
                    ),
                }
                rows.append(row)
                print(
                    f"    nlist={nlist:5d} nprobe={nprobe:4d} pm={pm} "
                    f"R@10={row.get('recall@10', float('nan')):.4f} "
                    f"R@210={row.get('recall@210', float('nan')):.4f} "
                    f"pad={pad_rate:.4f} nq1={row['lat_nq1']['p50_ms']:.2f}ms "
                    f"nq35={row['lat_nq35']['p50_ms']:.2f}ms"
                    + ("  [under-trained]" if under_trained else ""),
                    flush=True,
                )
            ivf.parallel_mode = 0
    return rows


def run_dataset(
    name: str,
    vectors: np.ndarray,
    info: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    rng = np.random.default_rng(args.seed)
    n_total = len(vectors)
    nq = min(args.nq, max(1, n_total // 10))
    perm = rng.permutation(n_total)
    xq = np.ascontiguousarray(vectors[perm[:nq]])
    xb = np.ascontiguousarray(vectors[perm[nq:]])
    n = len(xb)
    print(f"\n=== {name}: N={n} (held out nq={nq}) d={xb.shape[1]} ===", flush=True)

    flat_stats, flat = measure_flat(xb, xq, args.threads, args.reps)
    depth = min(LEG_DEPTH_CEILING, n)
    _, gt_ids = flat.search(xq, depth)
    for nt, lat in flat_stats["latency_by_threads"].items():
        print(
            f"  flat threads={nt:>2}: "
            + "  ".join(
                f"{k} p50={v['p50_ms']:.2f}/p95={v['p95_ms']:.2f}ms"
                for k, v in lat.items()
            ),
            flush=True,
        )

    ivf_rows: list[dict[str, Any]] = []
    if n >= args.min_ivf_n:
        print("  IVF sweep (METRIC_INNER_PRODUCT):", flush=True)
        ivf_rows = measure_ivf_grid(
            xb, xq, gt_ids, args.reps, tuple(args.nprobes), tuple(args.parallel_modes)
        )
    else:
        print(f"  skipping IVF sweep: N={n} < --min-ivf-n {args.min_ivf_n}", flush=True)

    return {
        "name": name,
        "source": info,
        "n_base": n,
        "n_queries": nq,
        "gt_depth": depth,
        "flat": flat_stats,
        "ivf": ivf_rows,
    }


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _best_nprobe(rows: list[dict[str, Any]], nlist: int, target: float) -> int | None:
    cands = [
        r
        for r in rows
        if r["nlist"] == nlist
        and r["parallel_mode"] == 0
        and r.get("recall@210", r.get("recall@70", 0.0)) >= target
        and r["pad_rate@210"] == 0.0
    ]
    return min((r["nprobe"] for r in cands), default=None)


def render_markdown(results: dict[str, Any]) -> str:
    env = results["environment"]
    lines = [
        f"# FAISS index parameter probe ({results['date']})",
        "",
        f"Harness: `scripts/benchmark/probe_faiss_index_params.py`; raw JSON: "
        f"`{results['json_path']}`.",
        "",
        f"Environment: faiss {env['faiss_version']}, {env['omp_max_threads']} OpenMP threads, "
        f"{env['platform']}, numpy {env['numpy_version']}. Ground truth: exact `IndexFlatIP` at "
        f"depth {LEG_DEPTH_CEILING} (the `leg_search_depth` ceiling); queries are held-out "
        "corpus vectors. Recall = `knn_intersection_measure` against the exact top-k. "
        "`pad@210` = fraction of `-1` ids in the first 210 slots (probe visited too few "
        "vectors). `under-trained` = fewer than 39 training points per centroid.",
        "",
        "## Flat (exact) latency by OpenMP threads, ms p50 / p95, k=420",
        "",
    ]
    for ds in results["datasets"]:
        lines += [
            f"### {ds['name']} (N={ds['n_base']})",
            "",
            "| threads | nq=1 | nq=35 | nq=210 |",
            "|---|---|---|---|",
        ]
        for nt, lat in ds["flat"]["latency_by_threads"].items():
            cells = [
                f"{lat[k]['p50_ms']:.2f} / {lat[k]['p95_ms']:.2f}" if k in lat else "—"
                for k in ("nq1", "nq35", "nq210")
            ]
            lines.append(f"| {nt} | " + " | ".join(cells) + " |")
        lines.append("")

    lines += ["## IVF sweep (`IndexIVFFlat`, inner product), parallel_mode=0", ""]
    for ds in results["datasets"]:
        if not ds["ivf"]:
            continue
        lines += [
            f"### {ds['name']} (N={ds['n_base']})",
            "",
            "| nlist | nprobe | R@1 | R@10 | R@35 | R@70 | R@210 | pad@210 | imbalance | train s | nq=1 p50 ms | nq=35 p50 ms | note |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in ds["ivf"]:
            if r["parallel_mode"] != 0:
                continue
            rec = [
                f"{r[f'recall@{k}']:.3f}" if f"recall@{k}" in r else "—"
                for k in RECALL_KS
            ]
            note = "under-trained" if r["under_trained"] else ""
            lines.append(
                f"| {r['nlist']} | {r['nprobe']} | "
                + " | ".join(rec)
                + f" | {r['pad_rate@210']:.3f} | {r['imbalance_factor']:.2f} | {r['train_s']:.2f} "
                f"| {r['lat_nq1']['p50_ms']:.2f} | {r['lat_nq35']['p50_ms']:.2f} | {note} |"
            )
        lines.append("")
        pm1 = [r for r in ds["ivf"] if r["parallel_mode"] == 1]
        if pm1:
            lines += ["parallel_mode=1 vs 0, nq=1 p50 ms (same nlist/nprobe):", ""]
            lines += ["| nlist | nprobe | pm=0 | pm=1 |", "|---|---|---|---|"]
            by_key = {
                (r["nlist"], r["nprobe"], r["parallel_mode"]): r for r in ds["ivf"]
            }
            for r in pm1:
                r0 = by_key[(r["nlist"], r["nprobe"], 0)]
                lines.append(
                    f"| {r['nlist']} | {r['nprobe']} | {r0['lat_nq1']['p50_ms']:.2f} | {r['lat_nq1']['p50_ms']:.2f} |"
                )
            lines.append("")
        lines += [
            "Smallest nprobe reaching recall@210 >= 0.99 with no padding, per nlist:",
            "",
        ]
        lines += [
            "| nlist | nprobe (R@210 >= 0.99) | nprobe (R@210 >= 0.95) |",
            "|---|---|---|",
        ]
        for nlist in sorted({r["nlist"] for r in ds["ivf"]}):
            lines.append(
                f"| {nlist} | {_best_nprobe(ds['ivf'], nlist, 0.99)} | {_best_nprobe(ds['ivf'], nlist, 0.95)} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--project",
        action="append",
        default=[],
        help="Substring of a project dir under <storage>/projects (repeatable)",
    )
    p.add_argument(
        "--all-projects", action="store_true", help="Run every on-disk project index"
    )
    p.add_argument(
        "--combine-all",
        action="store_true",
        help="Also run the union of all on-disk project vectors as one corpus",
    )
    p.add_argument(
        "--synthetic",
        action="append",
        type=int,
        default=[],
        help="Synthetic clustered corpus size (repeatable)",
    )
    p.add_argument(
        "--storage",
        default=None,
        help="Storage root override (default: CODE_SEARCH_STORAGE or ~/.claude_code_search)",
    )
    p.add_argument("--nq", type=int, default=200, help="Held-out queries per dataset")
    p.add_argument("--reps", type=int, default=15, help="Timing repetitions per cell")
    p.add_argument(
        "--threads",
        type=int,
        nargs="+",
        default=None,
        help="OpenMP thread counts to time flat search at (default: 1 4 8 max)",
    )
    p.add_argument("--nprobes", type=int, nargs="+", default=list(NPROBE_CANDIDATES))
    p.add_argument("--parallel-modes", type=int, nargs="+", default=[0, 1])
    p.add_argument(
        "--min-ivf-n",
        type=int,
        default=2000,
        help="Skip the IVF sweep below this many base vectors",
    )
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out-dir", default=str(_PROJECT_ROOT / "benchmark_results"))
    p.add_argument(
        "--md",
        default=None,
        help="Markdown report path (default: evaluation/FAISS_INDEX_PARAMS_<date>.md)",
    )
    p.add_argument("--quick", action="store_true", help="Small grid for a smoke run")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    max_threads = faiss.omp_get_max_threads()
    if args.threads is None:
        args.threads = sorted(
            {1, 4, 8, max_threads} - {t for t in (4, 8) if t > max_threads}
        )
    if args.quick:
        args.nprobes = [1, 8, 32]
        args.parallel_modes = [0]
        args.reps = 5
        args.nq = min(args.nq, 50)

    storage = storage_root(args.storage)
    on_disk = _project_index_paths(storage)
    selected: list[tuple[str, Path]] = []
    if args.all_projects:
        selected = list(on_disk.items())
    else:
        for sub in args.project:
            matches = [(k, v) for k, v in on_disk.items() if sub in k]
            if len(matches) != 1:
                print(
                    f"ERROR: --project {sub!r} matched {len(matches)} dirs: {[m[0] for m in matches]}"
                )
                return 2
            selected.append(matches[0])
    if not selected and not args.synthetic and not args.combine_all:
        print(f"No datasets selected. On-disk indexes under {storage / 'projects'}:")
        for k, v in on_disk.items():
            print(f"  {k}: {v}")
        return 2

    try:
        import threadpoolctl

        pool_info = threadpoolctl.threadpool_info()
    except Exception:  # noqa: BLE001 - optional diagnostics only
        pool_info = []

    results: dict[str, Any] = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "environment": {
            "faiss_version": faiss.__version__,
            "numpy_version": np.__version__,
            "omp_max_threads": max_threads,
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "threadpool_info": pool_info,
        },
        "args": vars(args),
        "datasets": [],
    }

    all_vectors: list[np.ndarray] = []
    for name, path in selected:
        vectors, info = load_project_vectors(path)
        all_vectors.append(vectors)
        results["datasets"].append(run_dataset(name, vectors, info, args))
    if args.combine_all:
        pool = [v for _, p in on_disk.items() for v in [load_project_vectors(p)[0]]]
        combined = np.concatenate(pool, axis=0)
        results["datasets"].append(
            run_dataset(
                f"combined_real_{len(on_disk)}_projects",
                combined,
                {
                    "source": "union of all on-disk project indexes",
                    "ntotal": int(len(combined)),
                },
                args,
            )
        )
    for n in args.synthetic:
        results["datasets"].append(
            run_dataset(
                f"synthetic_{n}",
                synthetic_vectors(n, args.seed),
                {"source": "synthetic clustered gaussians", "ntotal": n},
                args,
            )
        )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"faiss_index_params_{ts}.json"
    results["json_path"] = (
        str(json_path.relative_to(_PROJECT_ROOT))
        if json_path.is_relative_to(_PROJECT_ROOT)
        else str(json_path)
    )
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    md_path = (
        Path(args.md)
        if args.md
        else _PROJECT_ROOT
        / "evaluation"
        / f"FAISS_INDEX_PARAMS_{datetime.now().strftime('%Y%m%d')}.md"
    )
    md_path.write_text(render_markdown(results), encoding="utf-8")
    print(f"\nWrote {json_path}\nWrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
