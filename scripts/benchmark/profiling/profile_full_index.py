#!/usr/bin/env python3
"""Full-reindex phase profiling (measure-only, no production code changes).

Drives the *real* full-reindex path — the same one `tools/batch_index.py
--mode force` and the `index_directory` MCP tool use — and times phase
boundaries by monkey-patching them in this process only. No file under
`search/`, `chunking/`, or `embeddings/` is modified.

Why go through `mcp_server.tools.index_handlers.handle_index_directory`
instead of constructing `IncrementalIndexer` by hand: the real pipeline
selects `HybridSearcher` vs bare `CodeIndexManager` as the "indexer" object
based on `config.search_mode.enable_hybrid` (true in this repo's shared
config), builds the chunker via `MultiLanguageChunker.for_project()` (wires
import classification), and resolves stored `include_dirs`/`exclude_dirs`
filters from the project's `project_info.json` when none are passed
explicitly. Re-deriving all of that by hand risks silently drifting from
what the server actually does; calling the same entry point `batch_index.py`
calls eliminates that risk. `handle_index_directory` is a thin dispatcher
over `_run_index_directory` (job-registry/background-task ceremony aside) —
this harness pays that same small fixed ceremony cost, same as the CLI does.

Layer 1 (phase wall-clock attribution): every entry point below is
class/module patched with a `time.perf_counter()` wrapper before the run,
so nested calls (e.g. the resolver preamble, hoisted to run once via
`prepare_scoped_files_hoisted` since round 1 of the optimization campaign)
are captured per-call, not just as one lump sum.

Layer 2 (function-level cProfile): on the *last* run only (so profiling
overhead never pollutes the timed median), `PyanResolver.resolve`,
`LibCSTResolver.resolve`, `LSPResolver.resolve`, and `CodeEmbedder.
embed_chunks` are additionally wrapped in a `cProfile.Profile()`, each
dumping a `.prof` file for `pstats`/snakeviz.

Layer 3 (GPU/CPU split for embedding): `CodeEmbedder.create_embedding_content`
(CPU, per-chunk) and the loaded model's `.encode()` (GPU forward pass) are
timed separately, with `torch.cuda.synchronize()` bracketing `.encode()` so
the number reflects real device time, not just "the host stopped waiting".
`torch.cuda.max_memory_reserved()` is reset/read around each `embed_chunks`
call to report peak VRAM per pass.

NOT profiled at phase granularity: `ParallelChunker.chunk_files` runs on a
`ThreadPoolExecutor` (8 workers by default) — its wall-clock IS captured
(Layer 1 wraps the class method, which still times correctly across
threads), but no cProfile breakdown is attempted since stdlib cProfile only
profiles the calling thread. `scripts/benchmark/measure_parse_once.sh`
covers phase 4/5 in more depth and is the documented cross-check.

Usage:
    ./scripts/benchmark/profiling/profile_full_index.sh
    ./scripts/benchmark/profiling/profile_full_index.sh --runs 3
    ./scripts/benchmark/profiling/profile_full_index.sh --runs 1 --no-profile
    ./scripts/benchmark/profiling/profile_full_index.sh --project /path/to/other/repo
"""

from __future__ import annotations

import argparse
import asyncio
import cProfile
import functools
import json
import logging
import os
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    import torch
except ImportError:
    torch = None  # noqa: N816 - matches embeddings/embedder.py's own guarded import


def _check_venv() -> None:
    """Fail fast if not running inside the project .venv."""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if not in_venv:
        print(
            "ERROR: Run from .venv to ensure all dependencies are available.\n"
            "       Use: .venv/Scripts/python.exe scripts/benchmark/profiling/profile_full_index.py",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Recorder — collects (phase_name -> [duration, ...]) for the CURRENT run.
# A fresh Recorder is installed per run; wrapper closures below always read
# the module-level `_recorder` at call time, not at patch time.
# ---------------------------------------------------------------------------


class _Recorder:
    def __init__(self) -> None:
        self.times: dict[str, list[float]] = defaultdict(list)
        self.extra: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def record(self, name: str, elapsed: float, **extra: Any) -> None:
        self.times[name].append(elapsed)
        if extra:
            self.extra[name].append(extra)

    def total(self, name: str) -> float:
        return sum(self.times.get(name, []))

    def count(self, name: str) -> int:
        return len(self.times.get(name, []))


_recorder: _Recorder | None = None
_profile_active = False
_profile_dir: Path | None = None


def _record(name: str, elapsed: float, **extra: Any) -> None:
    if _recorder is not None:
        _recorder.record(name, elapsed, **extra)


def _timed_wrap(obj: Any, attr_name: str, phase_name: str) -> bool:
    """Patch obj.attr_name with a perf_counter wrapper recording under phase_name.

    Works uniformly for module-level functions (obj=module) and class methods
    (obj=class — getattr/setattr operate on the plain function, so instance
    calls still pass `self` through *args correctly).

    Returns False (and logs a warning instead of raising) if attr_name isn't
    found — some targets are optional (e.g. a resolver's module may not be
    importable if its optional dependency isn't installed).
    """
    if not hasattr(obj, attr_name):
        print(
            f"[WARN] Cannot wrap {obj!r}.{attr_name} — attribute not found",
            file=sys.stderr,
        )
        return False

    orig = getattr(obj, attr_name)

    @functools.wraps(orig)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        try:
            return orig(*args, **kwargs)
        finally:
            _record(phase_name, time.perf_counter() - t0)

    setattr(obj, attr_name, wrapper)
    return True


def _cprofiled_wrap(
    obj: Any, attr_name: str, phase_name: str, profile_stem: str
) -> bool:
    """Like _timed_wrap, but additionally cProfiles the call when
    `_profile_active` is True (only set on the designated profiled run) and
    dumps a `.prof` file under `_profile_dir`.
    """
    if not hasattr(obj, attr_name):
        print(
            f"[WARN] Cannot wrap {obj!r}.{attr_name} — attribute not found",
            file=sys.stderr,
        )
        return False

    orig = getattr(obj, attr_name)

    @functools.wraps(orig)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if _profile_active and _profile_dir is not None:
            pr = cProfile.Profile()
            t0 = time.perf_counter()
            pr.enable()
            try:
                return orig(*args, **kwargs)
            finally:
                pr.disable()
                _record(phase_name, time.perf_counter() - t0)
                pr.dump_stats(str(_profile_dir / f"{profile_stem}.prof"))
        else:
            t0 = time.perf_counter()
            try:
                return orig(*args, **kwargs)
            finally:
                _record(phase_name, time.perf_counter() - t0)

    setattr(obj, attr_name, wrapper)
    return True


# ---------------------------------------------------------------------------
# Layer 3 — GPU/CPU split for embedding.
# ---------------------------------------------------------------------------

_encode_patched_classes: set[type] = set()


def _wrap_model_encode(model_cls: type) -> None:
    if model_cls in _encode_patched_classes or not hasattr(model_cls, "encode"):
        return
    orig_encode = model_cls.encode

    @functools.wraps(orig_encode)
    def timed_encode(self: Any, *args: Any, **kwargs: Any) -> Any:
        if torch is not None and torch.cuda.is_available():
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        try:
            return orig_encode(self, *args, **kwargs)
        finally:
            if torch is not None and torch.cuda.is_available():
                torch.cuda.synchronize()
            _record("embed_gpu_encode", time.perf_counter() - t0)

    model_cls.encode = timed_encode
    _encode_patched_classes.add(model_cls)


def _install_layer3_embedding_split() -> None:
    """Wrap CodeEmbedder.create_embedding_content (CPU, per-chunk) and patch
    the loaded model's .encode() (GPU) the first time embed_chunks resolves
    the model — the concrete model class isn't known until then.
    """
    import embeddings.embedder as embedder_mod

    orig_create_content = embedder_mod.CodeEmbedder.create_embedding_content

    @functools.wraps(orig_create_content)
    def timed_create_content(self: Any, *args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        try:
            return orig_create_content(self, *args, **kwargs)
        finally:
            _record("embed_cpu_create_content", time.perf_counter() - t0)

    embedder_mod.CodeEmbedder.create_embedding_content = timed_create_content

    orig_embed_chunks = embedder_mod.CodeEmbedder.embed_chunks

    @functools.wraps(orig_embed_chunks)
    def timed_embed_chunks(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            _wrap_model_encode(type(self.model))
        except Exception as e:  # noqa: BLE001 - best-effort instrumentation, must never break the real pipeline
            print(
                f"[WARN] Could not patch model.encode for GPU timing: {e}",
                file=sys.stderr,
            )
        if torch is not None and torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()
        try:
            return orig_embed_chunks(self, *args, **kwargs)
        finally:
            elapsed = time.perf_counter() - t0
            extra: dict[str, Any] = {}
            if torch is not None and torch.cuda.is_available():
                extra["max_memory_reserved_mb"] = round(
                    torch.cuda.max_memory_reserved() / (1024**2), 1
                )
            _record("phase7_embed_chunks", elapsed, **extra)

    embedder_mod.CodeEmbedder.embed_chunks = timed_embed_chunks


# ---------------------------------------------------------------------------
# Install all patches (Layer 1 + hooks for Layer 2's cProfile targets).
# ---------------------------------------------------------------------------


def _install_patches(enable_hybrid: bool) -> None:
    import chunking.relationships.call_edge_resolver as call_edge_resolver_mod
    import chunking.relationships.external_call_graph as pyan_mod
    import chunking.relationships.libcst_call_graph as libcst_mod
    import chunking.repo_profiler as repo_profiler_mod
    import merkle.merkle_dag as merkle_dag_mod
    import merkle.snapshot_manager as snapshot_manager_mod
    import search.hybrid_searcher as hybrid_searcher_mod
    import search.index_write_stage as write_stage_mod
    import search.indexer as indexer_mod
    import search.parallel_chunker as parallel_chunker_mod

    # Phase 2 — snapshot delete + clear_index.
    _timed_wrap(
        snapshot_manager_mod.SnapshotManager,
        "delete_snapshot",
        "phase2_delete_snapshot",
    )
    index_cls = (
        hybrid_searcher_mod.HybridSearcher
        if enable_hybrid
        else indexer_mod.CodeIndexManager
    )
    _timed_wrap(index_cls, "clear_index", "phase2_clear_index")

    # Phase 3 — Merkle DAG build.
    _timed_wrap(merkle_dag_mod.MerkleDAG, "build", "phase3_merkle_build")

    # Phase 4 — profile pass. Imported lazily inside _full_index
    # (`from chunking.repo_profiler import profile_repository`) on every
    # call, so patching the origin module attribute is picked up correctly.
    _timed_wrap(repo_profiler_mod, "profile_repository", "phase4_profile_repository")

    # Phase 5 — chunk pass (wall-clock only; see module docstring for why).
    _timed_wrap(
        parallel_chunker_mod.ParallelChunker, "chunk_files", "phase5_chunk_files"
    )

    # Phase 7 — embedding (Layer 1 total + Layer 3 CPU/GPU split).
    _install_layer3_embedding_split()

    # Phase 8 — FAISS add + graph populate.
    _timed_wrap(index_cls, "add_embeddings", "phase8_add_embeddings")

    # Phase 9 — call-edge resolvers.
    _timed_wrap(
        write_stage_mod.IndexWriteStage,
        "_inject_call_edges",
        "phase9_inject_call_edges",
    )
    # run_resolvers is imported by name into index_write_stage's namespace
    # (`from chunking.relationships.call_edge_resolver import run_resolvers`)
    # — must patch the reference bound there, not the origin module.
    _timed_wrap(write_stage_mod, "run_resolvers", "phase9_run_resolvers")
    # prepare_scoped_files is now hoisted into run_resolvers() itself (called
    # once for all resolvers instead of once per resolver) — patch the single
    # origin-module binding used there instead of the three per-resolver
    # fallback bindings (pyan/libcst/lsp only fall back to calling it
    # themselves when run_resolvers's hoisted py_files comes back None).
    _timed_wrap(
        call_edge_resolver_mod, "prepare_scoped_files", "prepare_scoped_files_hoisted"
    )

    try:
        _cprofiled_wrap(
            pyan_mod.PyanResolver, "resolve", "resolver_pyan", "resolver_pyan"
        )
    except Exception as e:  # noqa: BLE001 - optional dependency (pyan3) may not be installed
        print(f"[WARN] pyan resolver not patchable: {e}", file=sys.stderr)

    try:
        _cprofiled_wrap(
            libcst_mod.LibCSTResolver, "resolve", "resolver_libcst", "resolver_libcst"
        )
    except Exception as e:  # noqa: BLE001 - optional dependency (libcst) may not be installed
        print(f"[WARN] LibCST resolver not patchable: {e}", file=sys.stderr)

    try:
        import chunking.relationships.lsp_call_graph as lsp_mod

        _cprofiled_wrap(lsp_mod.LSPResolver, "resolve", "resolver_lsp", "resolver_lsp")
    except Exception as e:  # noqa: BLE001 - optional dependency (basedpyright LSP) may not be installed/enabled
        print(f"[WARN] LSP resolver not patchable: {e}", file=sys.stderr)

    # Phase 10 — snapshot save, save_indices, BM25 resync.
    _timed_wrap(
        snapshot_manager_mod.SnapshotManager, "save_snapshot", "phase10_save_snapshot"
    )
    _timed_wrap(index_cls, "save_indices", "phase10_save_indices")
    _timed_wrap(index_cls, "resync_if_desynced", "phase10_resync_bm25")


# Top-level buckets whose sum (against total wall-clock) yields "unattributed"
# time — phase9_run_resolvers/resolver_*/prepare_scoped_files_* are nested
# INSIDE phase9_inject_call_edges and must not be double-counted here.
_TOP_LEVEL_PHASES = [
    "phase2_delete_snapshot",
    "phase2_clear_index",
    "phase3_merkle_build",
    "phase4_profile_repository",
    "phase5_chunk_files",
    "phase7_embed_chunks",
    "phase8_add_embeddings",
    "phase9_inject_call_edges",
    "phase10_save_snapshot",
    "phase10_save_indices",
    "phase10_resync_bm25",
]

# Nested-under-phase9 breakdown, printed separately for hypothesis-checking.
# Since run_resolvers() now dispatches pyan/libcst/lsp concurrently on a
# thread pool, resolver_pyan/resolver_libcst/resolver_lsp overlap in wall-clock
# with each other (and with prepare_scoped_files_hoisted, which runs before
# they're submitted) — their sum can exceed phase9_run_resolvers.
_RESOLVER_SUBPHASES = [
    "phase9_run_resolvers",
    "prepare_scoped_files_hoisted",
    "resolver_pyan",
    "resolver_libcst",
    "resolver_lsp",
]

_EMBED_SUBPHASES = [
    "embed_cpu_create_content",
    "embed_gpu_encode",
]


def _run_one_reindex(project_path: str) -> dict[str, Any]:
    """Drive one real force-reindex pass via the real MCP handler entry point.

    Returns the result dict from handle_index_directory (success, files_added,
    chunks_added, time_taken, ...). Raises RuntimeError if the pass reports
    zero files/chunks — the known PermissionError-silent-failure pitfall
    (SESSION_LOG 2026-07-21) means a "success" exit code alone is not proof
    the pass actually did anything.
    """
    from mcp_server.tools.index_handlers import handle_index_directory

    result = asyncio.run(
        handle_index_directory({"directory_path": project_path, "incremental": False})
    )
    if not result.get("success"):
        raise RuntimeError(f"Force reindex reported failure: {result}")
    if not result.get("files_added"):
        raise RuntimeError(
            f"Force reindex reported files_added=0 — likely the silent "
            f"PermissionError failure mode (is the MCP server still running "
            f"and holding metadata.db open?). Full result: {result}"
        )
    if not result.get("chunks_added"):
        raise RuntimeError(
            f"Force reindex reported chunks_added=0. Full result: {result}"
        )
    return result


def _print_phase_table(recorder: _Recorder, total_wall: float) -> None:
    print()
    print("=" * 78)
    print("PHASE WALL-CLOCK (this run)")
    print("=" * 78)
    print(f"{'Phase':<32} {'seconds':>10} {'% total':>9} {'calls':>7}")
    print("-" * 78)
    attributed = 0.0
    for name in _TOP_LEVEL_PHASES:
        t = recorder.total(name)
        attributed += t
        pct = (t / total_wall * 100) if total_wall > 0 else 0.0
        print(f"{name:<32} {t:>10.3f} {pct:>8.1f}% {recorder.count(name):>7}")
    unattributed = max(0.0, total_wall - attributed)
    pct = (unattributed / total_wall * 100) if total_wall > 0 else 0.0
    print("-" * 78)
    print(f"{'(unattributed)':<32} {unattributed:>10.3f} {pct:>8.1f}%")
    print(f"{'TOTAL (handle_index_directory)':<32} {total_wall:>10.3f} {'100.0%':>9}")

    print()
    print("Phase 9 breakdown (resolver preamble):")
    for name in _RESOLVER_SUBPHASES:
        if recorder.count(name):
            print(
                f"  {name:<34} {recorder.total(name):>8.3f}s  (n={recorder.count(name)})"
            )

    print()
    print("Phase 7 breakdown (embedding CPU/GPU split):")
    for name in _EMBED_SUBPHASES:
        if recorder.count(name):
            print(
                f"  {name:<34} {recorder.total(name):>8.3f}s  (n={recorder.count(name)})"
            )
    for extra in recorder.extra.get("phase7_embed_chunks", []):
        if "max_memory_reserved_mb" in extra:
            print(f"  peak VRAM reserved: {extra['max_memory_reserved_mb']:.1f} MB")


def main() -> None:
    _check_venv()
    logging.getLogger().setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(
        description=(
            "Profile the real full-reindex pipeline phase-by-phase "
            "(measure-only, no production code changes)."
        )
    )
    parser.add_argument(
        "--project",
        default=str(_PROJECT_ROOT),
        help="Project to reindex (default: this repo)",
    )
    parser.add_argument(
        "--runs", type=int, default=3, help="Timed runs; reports median (default: 3)"
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip the untimed warm-up pass (default: 1 untimed warm-up run first)",
    )
    parser.add_argument(
        "--no-profile",
        action="store_true",
        help="Skip Layer 2 cProfile dumps on the last run (Layer 1 timing always runs)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_PROJECT_ROOT / "benchmark_results"),
        help="Directory for the JSON artifact and .prof dumps",
    )
    args = parser.parse_args()

    project_path = str(Path(args.project).resolve())
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("CLAUDE_DEFAULT_PROJECT", project_path)
    from mcp_server.resource_manager import initialize_server_state
    from search.config import get_search_config

    initialize_server_state()
    config = get_search_config()
    enable_hybrid = config.search_mode.enable_hybrid
    print(f"Project: {project_path}")
    print(
        f"enable_hybrid={enable_hybrid}  sizing_mode={config.chunking.sizing_mode}  "
        f"resolvers={config.call_graph.resolvers}  lsp_enabled={config.call_graph.lsp_enabled}"
    )

    global _recorder, _profile_active, _profile_dir
    _install_patches(enable_hybrid)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    _profile_dir = output_dir / f"full_index_profiles_{timestamp}"

    if not args.no_warmup:
        print("\nWarm-up run (untimed, real force reindex)...")
        _recorder = _Recorder()
        t0 = time.perf_counter()
        warmup_result = _run_one_reindex(project_path)
        print(
            f"  done in {time.perf_counter() - t0:.1f}s "
            f"(files_added={warmup_result['files_added']}, chunks_added={warmup_result['chunks_added']})"
        )

    run_records: list[_Recorder] = []
    run_totals: list[float] = []
    run_results: list[dict[str, Any]] = []
    instrumented_run_idx: int | None = None  # 1-based; the run cProfile ran on, if any

    for run_idx in range(1, args.runs + 1):
        is_last = run_idx == args.runs
        _profile_active = is_last and not args.no_profile
        if _profile_active:
            instrumented_run_idx = run_idx
            _profile_dir.mkdir(parents=True, exist_ok=True)
            print(
                f"\nTimed run {run_idx}/{args.runs} (cProfile ON for resolvers + embed_chunks)..."
            )
        else:
            print(f"\nTimed run {run_idx}/{args.runs}...")

        _recorder = _Recorder()
        t0 = time.perf_counter()
        result = _run_one_reindex(project_path)
        total_wall = time.perf_counter() - t0

        print(
            f"  done in {total_wall:.1f}s "
            f"(files_added={result['files_added']}, chunks_added={result['chunks_added']})"
        )
        _print_phase_table(_recorder, total_wall)

        run_records.append(_recorder)
        run_totals.append(total_wall)
        run_results.append(result)

    _profile_active = False

    # ------------------------------------------------------------------
    # Cross-run summary (median across CLEAN timed runs only).
    # ------------------------------------------------------------------
    # The last run is optionally cProfile-instrumented (Layer 2) — cProfile's
    # per-call overhead measurably inflates that run's wall-clock (it wraps
    # PyanResolver.resolve/LibCSTResolver.resolve/LSPResolver.resolve/
    # CodeEmbedder.embed_chunks), so folding it into the median would
    # contaminate the timing stats with instrumentation noise rather than
    # real pipeline cost. Excluded here; still present in the JSON artifact's
    # full per-run list below, tagged via "cprofile_instrumented".
    if instrumented_run_idx is not None and args.runs > 1:
        clean_indices = [i for i in range(args.runs) if i != instrumented_run_idx - 1]
    else:
        clean_indices = list(range(args.runs))
        if instrumented_run_idx is not None:
            print(
                "\n[WARN] Only one run and it was cProfile-instrumented — the "
                "summary below includes instrumentation overhead. Pass "
                "--runs 2+ or --no-profile for a clean measurement.",
                file=sys.stderr,
            )
    clean_totals = [run_totals[i] for i in clean_indices]
    clean_records = [run_records[i] for i in clean_indices]

    median_total = statistics.median(clean_totals)
    print()
    print("#" * 78)
    excluded_note = (
        f" (run {instrumented_run_idx} excluded — cProfile-instrumented)"
        if instrumented_run_idx is not None and args.runs > 1
        else ""
    )
    print(f"SUMMARY — median of {len(clean_totals)} clean run(s){excluded_note}")
    print("#" * 78)
    print(
        f"{'total wall-clock':<32} {median_total:>10.3f}s  (spread: {min(clean_totals):.1f}-{max(clean_totals):.1f}s)"
    )
    all_phase_names = _TOP_LEVEL_PHASES + _RESOLVER_SUBPHASES + _EMBED_SUBPHASES
    medians: dict[str, float] = {}
    for name in all_phase_names:
        vals = [r.total(name) for r in clean_records]
        medians[name] = statistics.median(vals)
        if medians[name] > 0:
            pct = medians[name] / median_total * 100 if median_total > 0 else 0.0
            print(f"{name:<32} {medians[name]:>10.3f}s {pct:>8.1f}%")

    # ------------------------------------------------------------------
    # JSON artifact.
    # ------------------------------------------------------------------
    artifact = {
        "timestamp": timestamp,
        "project": project_path,
        "config": {
            "enable_hybrid": enable_hybrid,
            "sizing_mode": config.chunking.sizing_mode,
            "max_chunking_workers": config.performance.max_chunking_workers,
            "batch_size": config.embedding.batch_size,
            "resolvers": config.call_graph.resolvers,
            "lsp_enabled": config.call_graph.lsp_enabled,
        },
        "runs": [
            {
                "run_index": idx,
                "total_wall_clock": total,
                "files_added": res["files_added"],
                "chunks_added": res["chunks_added"],
                "cprofile_instrumented": idx == instrumented_run_idx,
                "phases": {
                    name: rec.total(name) for name in all_phase_names if rec.count(name)
                },
                "phase_call_counts": {
                    name: rec.count(name) for name in all_phase_names if rec.count(name)
                },
                "extra": {k: v for k, v in rec.extra.items() if v},
            }
            for idx, (total, res, rec) in enumerate(
                zip(run_totals, run_results, run_records, strict=True), start=1
            )
        ],
        "instrumented_run_index": instrumented_run_idx,
        "clean_run_indices": [i + 1 for i in clean_indices],
        "median": {
            "total_wall_clock": median_total,
            "phases": medians,
            "note": "computed over clean_run_indices only -- excludes the cProfile-instrumented run",
        },
        "profile_dir": str(_profile_dir) if not args.no_profile else None,
    }
    json_path = output_dir / f"full_index_profile_{timestamp}.json"
    json_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"\nJSON artifact: {json_path}")
    if not args.no_profile:
        print(f".prof dumps:    {_profile_dir}")


if __name__ == "__main__":
    main()
