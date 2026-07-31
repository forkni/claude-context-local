#!/usr/bin/env python3
"""EmbeddingGemma vs BGE-M3 A/B benchmark (Dependency Optimization Plan, Phase G).

Compares google/embeddinggemma-300m against the deployed default BAAI/bge-m3
on this repo's own golden dataset, to decide whether embeddinggemma should be
dropped from MODEL_REGISTRY (feeds Phase B's model-drop list).

Safety design (this is the load-bearing part — read before changing anything):

- The BGE-M3 arm is READ-ONLY: it benchmarks the already-fresh, on-disk index
  (2345 chunks, 206 files) and never reindexes it.
- The EmbeddingGemma arm swaps ``config.embedding.model_name`` IN-MEMORY ONLY
  on the process-wide ``SearchConfigManager`` singleton returned by
  ``search.config.get_search_config()`` -- ``config_manager.save_config()`` is
  never called. ``SearchConfigManager.load_config()`` caches by (file mtime,
  overrides mtime) and returns the same cached ``SearchConfig`` object when
  neither changed (search/config.py:1079-1084), so this mutation never
  touches the shared ``search_config.json`` file that this session's live
  ``code-search`` MCP server process also reads. ``mcp_server.services.get_config``
  is a direct re-export of this same ``get_search_config`` (mcp_server/services.py:11),
  and ``model_pool_manager.get_embedder()`` / ``storage_manager.get_project_storage_dir()``
  both read ``config.embedding.model_name`` through it -- so every consumer in
  this process sees the swapped model, while the on-disk config and any other
  process (the live MCP server) sees only the original BAAI/bge-m3.
- Because ``get_project_storage_dir()`` derives its directory purely from the
  (in-memory) model name, the embeddinggemma arm's force-reindex lands in a
  brand-new, previously-nonexistent per-model directory
  (``..._gemma-300m_768d``) -- fully isolated from the live
  ``..._bge-m3_1024d`` directory. Zero write contention, zero risk to the
  live server's index or this session's own search tools.
- Reindexing goes through the real production entry point
  (``mcp_server.tools.index_handlers.handle_index_directory``), mirroring
  ``scripts/benchmark/profiling/profile_full_index.py``, including its
  success/files_added/chunks_added sanity check (guards against the known
  silent-zero-files pitfall, e.g. a file lock held by another process).
- Benchmarking reuses ``scripts/benchmark/run_sscg_benchmark.py``'s
  ``run_single()`` / ``_setup_project()`` directly -- same scoring
  (``evaluation.metrics``), same category-D exclusion, same VRAM-capture
  idiom -- so results are numerically comparable to the SSCG baselines
  already recorded elsewhere in this repo.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/embedder_gemma_vs_bgem3_ab.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

PROJECT_PATH = str(_PROJECT_ROOT)
os.environ.setdefault("CLAUDE_DEFAULT_PROJECT", PROJECT_PATH)

BGE_M3 = "BAAI/bge-m3"
GEMMA = "google/embeddinggemma-300m"

# Recall-over-speed decision band (same ±0.005 noise band used in Phase F's
# bm25_stopwords_ab.py) -- both deltas must be non-negative within this band
# to justify keeping embeddinggemma.
NOISE_BAND = 0.005


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _reset_vram():
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            return torch
    except ImportError:
        pass
    return None


def _peak_vram_mb(torch_module) -> float | None:
    if torch_module is not None:
        return round(torch_module.cuda.max_memory_reserved() / (1024**2), 1)
    return None


def run_arm(model_name: str, dataset: dict, k: int, reindex: bool) -> dict:
    """Benchmark one embedding model. See module docstring for the safety design."""
    from mcp_server.state import get_state
    from search.config import MODEL_REGISTRY, get_search_config

    cfg = get_search_config()
    old_model = cfg.embedding.model_name
    if old_model != model_name:
        print(
            f"[SWITCH] {old_model} -> {model_name} "
            "(in-memory only -- save_config() never called)"
        )
        cfg.embedding.model_name = model_name
        cfg.embedding.dimension = MODEL_REGISTRY[model_name]["dimension"]
        get_state().reset_for_model_switch()

    from mcp_server.storage_manager import get_project_storage_dir

    storage_dir = get_project_storage_dir(PROJECT_PATH)
    print(f"[STORAGE] {model_name} -> {storage_dir}")

    index_time_s = None
    embed_vram_mb = None
    reindex_result = None
    if reindex:
        from mcp_server.tools.index_handlers import handle_index_directory

        torch_mod = _reset_vram()
        t0 = time.perf_counter()
        reindex_result = asyncio.run(
            handle_index_directory(
                {"directory_path": PROJECT_PATH, "incremental": False}
            )
        )
        index_time_s = round(time.perf_counter() - t0, 1)
        embed_vram_mb = _peak_vram_mb(torch_mod)
        if (
            not reindex_result.get("success")
            or not reindex_result.get("files_added")
            or not reindex_result.get("chunks_added")
        ):
            raise RuntimeError(
                f"Reindex failed or added nothing for {model_name}: {reindex_result}"
            )
        print(
            f"[REINDEX] {model_name}: {reindex_result.get('files_added')} files, "
            f"{reindex_result.get('chunks_added')} chunks, {index_time_s}s, "
            f"peak_vram={embed_vram_mb}MB"
        )

    storage_bytes = _dir_size_bytes(storage_dir)
    dense_dir = storage_dir / "index" / "dense"
    dense_bytes = _dir_size_bytes(dense_dir)

    # Reuse the proven SSCG benchmark machinery for scoring.
    from scripts.benchmark.run_sscg_benchmark import _setup_project, run_single

    _setup_project(PROJECT_PATH)
    result = run_single(
        project_path=PROJECT_PATH,
        dataset=dataset,
        config_name=model_name,
        k=k,
        bm25_weight=None,
        dense_weight=None,
        search_mode=None,
        category_filter=None,
        verbose=False,
    )

    result["config_metadata"]["embedding_model"] = model_name
    result["config_metadata"]["storage_dir"] = str(storage_dir)
    result["config_metadata"]["storage_bytes"] = storage_bytes
    result["config_metadata"]["dense_index_bytes"] = dense_bytes
    if index_time_s is not None:
        result["config_metadata"]["reindex_time_s"] = index_time_s
    if embed_vram_mb is not None:
        result["config_metadata"]["embed_peak_vram_mb"] = embed_vram_mb
    if reindex_result is not None:
        result["config_metadata"]["files_added"] = reindex_result.get("files_added")
        result["config_metadata"]["chunks_added"] = reindex_result.get("chunks_added")
    return result


def main() -> None:
    from mcp_server.resource_manager import initialize_server_state

    initialize_server_state()

    dataset_path = _PROJECT_ROOT / "evaluation" / "golden_dataset.json"
    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)
    print(f"[INFO] Golden dataset: {len(dataset['queries'])} queries")

    k = dataset.get("_meta", {}).get("recommended_k", 7)
    print(f"[INFO] k={k}")

    print("\n=== Arm 1: BAAI/bge-m3 (deployed default, read-only, no reindex) ===")
    bge_result = run_arm(BGE_M3, dataset, k, reindex=False)

    print(
        "\n=== Arm 2: google/embeddinggemma-300m "
        "(in-memory switch + isolated reindex) ==="
    )
    gemma_result = run_arm(GEMMA, dataset, k, reindex=True)

    # Restore in-memory config back to the deployed default so this process
    # doesn't leave shared state pointed at gemma if anything imports it later.
    from mcp_server.state import get_state
    from search.config import MODEL_REGISTRY, get_search_config

    cfg = get_search_config()
    cfg.embedding.model_name = BGE_M3
    cfg.embedding.dimension = MODEL_REGISTRY[BGE_M3]["dimension"]
    get_state().reset_for_model_switch()

    print(f"\n=== Aggregate comparison (excludes category D, k={k}) ===")
    print(
        f"{'Model':30s} {'MRR':>7s} {'R@5':>7s} {'R@10':>7s} "
        f"{'Hit@5':>7s} {'Lat(ms)':>9s} {'IdxMB':>8s}"
    )
    for r in (bge_result, gemma_result):
        agg = r["aggregate"]
        idx_mb = r["config_metadata"].get("storage_bytes", 0) / (1024**2)
        print(
            f"{r['config_name']:30s} {agg['mrr']:7.4f} {agg['recall@5']:7.4f} "
            f"{agg['recall@10']:7.4f} {agg['hit_rate@5']:7.4f} "
            f"{r['avg_latency_ms']:9.1f} {idx_mb:8.1f}"
        )

    d_mrr = round(gemma_result["aggregate"]["mrr"] - bge_result["aggregate"]["mrr"], 4)
    d_r5 = round(
        gemma_result["aggregate"]["recall@5"] - bge_result["aggregate"]["recall@5"], 4
    )
    print(f"\ndMRR (gemma-bge)={d_mrr:+.4f}  dRecall@5 (gemma-bge)={d_r5:+.4f}")
    if d_r5 >= -NOISE_BAND and d_mrr >= -NOISE_BAND:
        verdict = "KEEP embeddinggemma (recall/MRR on par or better than bge-m3)"
    else:
        verdict = "DROP embeddinggemma (measurable recall/MRR regression vs bge-m3)"
    print(f"Verdict: {verdict}")

    out_dir = _PROJECT_ROOT / "benchmark_results"
    out_dir.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"embedder_gemma_vs_bgem3_ab_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "bge_m3": bge_result,
                "embeddinggemma": gemma_result,
                "decision": {
                    "d_mrr": d_mrr,
                    "d_recall_at_5": d_r5,
                    "noise_band": NOISE_BAND,
                    "verdict": verdict,
                },
            },
            f,
            indent=2,
        )
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
