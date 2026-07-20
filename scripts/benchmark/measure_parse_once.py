#!/usr/bin/env python3
"""Parse-once feasibility measurement (Candidate B exploration).

Candidate A (the `ParsedSource` seam, chunking/tree_sitter.py) unified how the
profile pass (pass 1, chunking/repo_profiler.py) and the chunk pass (pass 2,
search/parallel_chunker.py) each parse a file. It was the deliberate on-ramp
for Candidate B: reusing pass-1's parsed trees in pass 2 so files aren't
tree-sitter-parsed twice.

Candidate B has two hard constraints (see CONTEXT.md's ParsedSource entry and
chunking/tree_sitter.py:146-166): the adaptive-sizing threshold needs a
whole-repo P75 before any file can be chunked (global-ordering barrier), and
ParsedSource.tree is only valid on the thread that produced it (profile runs
serial on the main thread; chunking runs on a ThreadPoolExecutor) — so
carrying trees across passes means either holding all of them in memory or
crossing thread affinity.

This script does not attempt Candidate B. It measures whether the redundant
parse is even worth eliminating, by timing the *real* profile and chunk
passes standalone — no reimplementation of either.

Drives:
    - merkle.merkle_dag.MerkleDAG              (file discovery, same as
      IncrementalIndexer._full_index)
    - search.incremental_indexer.IncrementalIndexer._get_supported_files
    - chunking.repo_profiler.profile_repository
    - chunking.tree_sitter.TreeSitterChunker.parse_file
    - search.parallel_chunker.ParallelChunker.chunk_files

Usage:
    ./scripts/benchmark/measure_parse_once.sh
    ./scripts/benchmark/measure_parse_once.sh --project /path/to/other/repo
    ./scripts/benchmark/measure_parse_once.sh --workers 8 --runs 5
"""

import argparse
import logging
import os
import statistics
import sys
import time
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from chunking.repo_profiler import RepoProfile, profile_repository  # noqa: E402
from chunking.tree_sitter import TreeSitterChunker  # noqa: E402
from merkle.merkle_dag import MerkleDAG  # noqa: E402
from search.config import get_search_config  # noqa: E402
from search.incremental_indexer import IncrementalIndexer  # noqa: E402
from search.parallel_chunker import ParallelChunker  # noqa: E402


def _discover_supported_files(
    project_path: str,
    include_dirs: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
) -> list[str]:
    """Mirror IncrementalIndexer._full_index's file discovery exactly:
    MerkleDAG.get_all_files() -> _get_supported_files() filtering.

    Constructing IncrementalIndexer() is cheap here — Indexer(temp_dir) and
    CodeEmbedder() both defer real work (no model load, no GPU) until first
    use, and this harness never calls embed/search.

    include_dirs/exclude_dirs are NOT read from search_config.json — the real
    index's directory filters are supplied by whoever calls index_directory()
    (an MCP tool argument, not a repo-wide default), so pass --exclude-dirs
    to match a specific live index's file set.
    """
    indexer = IncrementalIndexer(include_dirs=include_dirs, exclude_dirs=exclude_dirs)
    dag = MerkleDAG(
        project_path,
        indexer.include_dirs,
        indexer.exclude_dirs,
        supported_extensions=indexer.supported_extensions,
    )
    dag.build()
    all_files = dag.get_all_files()
    return indexer._get_supported_files(project_path, all_files)


def _time_profile(
    project_path: str, files: list[str]
) -> tuple[float, RepoProfile | None]:
    start = time.perf_counter()
    profile = profile_repository(project_path, files)
    return time.perf_counter() - start, profile


def _time_parse_only(project_path: str, files: list[str]) -> float:
    """Sweep parse_file() over every file, discarding the result.

    Isolates read+parse from repo_profiler's function-node walk, so
    t_walk = t_profile - t_parse_only shows how much of pass 1 is *not*
    recoverable just by carrying the tree forward.
    """
    chunker = TreeSitterChunker()
    start = time.perf_counter()
    for rel_path in files:
        abs_path = str(Path(project_path) / rel_path)
        try:
            chunker.parse_file(abs_path, rel_path=rel_path)
        except Exception:  # noqa: BLE001 - benchmark sweep: one bad file shouldn't abort timing
            continue
    return time.perf_counter() - start


def _time_chunk(project_path: str, files: list[str], workers: int) -> float:
    indexer = IncrementalIndexer()
    parallel_chunker = ParallelChunker(
        chunker=indexer.chunker, enable_parallel=True, max_workers=workers
    )
    start = time.perf_counter()
    parallel_chunker.chunk_files(project_path, files)
    return time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Measure the real cost of the profile-pass/chunk-pass double-parse "
            "(Candidate B exploration) — no production code changes."
        )
    )
    parser.add_argument(
        "--project",
        default=str(_PROJECT_ROOT),
        help="Project to measure (default: this repo)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Chunking worker count (default: config.performance.max_chunking_workers)",
    )
    parser.add_argument(
        "--runs", type=int, default=3, help="Timed runs per phase; reports median"
    )
    parser.add_argument(
        "--include-dirs",
        default=None,
        help="Comma-separated dirs to include (matches a specific live index's filters)",
    )
    parser.add_argument(
        "--exclude-dirs",
        default=None,
        help="Comma-separated dirs to exclude (matches a specific live index's filters)",
    )
    args = parser.parse_args()

    # Quiet the pipeline's own INFO logging (profile_repository, parallel
    # chunker) so the timing table isn't buried — this harness prints its
    # own summary instead.
    logging.getLogger().setLevel(logging.WARNING)

    project_path = str(Path(args.project).resolve())
    config = get_search_config()
    workers = args.workers or config.performance.max_chunking_workers

    print(f"Project: {project_path}")
    print(
        f"Workers: {workers}  |  Runs per phase: {args.runs}  |  CPUs: {os.cpu_count()}"
    )
    print(
        f"sizing_mode: {config.chunking.sizing_mode}"
        + (
            ""
            if config.chunking.sizing_mode == "adaptive"
            else "  (profile pass would NOT run for this project's real indexing)"
        )
    )
    print()

    include_dirs = args.include_dirs.split(",") if args.include_dirs else None
    exclude_dirs = args.exclude_dirs.split(",") if args.exclude_dirs else None
    files = _discover_supported_files(project_path, include_dirs, exclude_dirs)
    print(f"Discovered {len(files)} supported files")
    if exclude_dirs:
        print(f"  (exclude_dirs={exclude_dirs})")

    # Untimed warm-up run — pages files into OS cache so the first timed run
    # isn't penalized by cold disk I/O relative to the rest.
    print("Warm-up run (untimed)...")
    profile_repository(project_path, files)
    _time_chunk(project_path, files, workers)

    print(f"Timing profile pass ({args.runs} runs)...")
    profile_runs = []
    last_profile = None
    for _ in range(args.runs):
        elapsed, last_profile = _time_profile(project_path, files)
        profile_runs.append(elapsed)
    t_profile = statistics.median(profile_runs)

    print(f"Timing parse-only sweep ({args.runs} runs)...")
    parse_only_runs = [_time_parse_only(project_path, files) for _ in range(args.runs)]
    t_parse_only = statistics.median(parse_only_runs)

    print(f"Timing chunk pass ({args.runs} runs)...")
    chunk_runs = [_time_chunk(project_path, files, workers) for _ in range(args.runs)]
    t_chunk = statistics.median(chunk_runs)

    t_walk = t_profile - t_parse_only
    ceiling = t_profile / (t_profile + t_chunk) if (t_profile + t_chunk) > 0 else 0.0

    print()
    print("=" * 64)
    print("RESULTS (median of runs, seconds)")
    print("=" * 64)
    print(f"{'t_profile (pass 1, full)':<32} {t_profile:>10.3f}s")
    print(f"{'  t_parse_only (read+parse)':<32} {t_parse_only:>10.3f}s")
    print(f"{'  t_walk (function-node walk)':<32} {t_walk:>10.3f}s")
    print(f"{'t_chunk (pass 2)':<32} {t_chunk:>10.3f}s")
    print("-" * 64)
    print(f"Parse-once ceiling = t_profile / (t_profile + t_chunk) = {ceiling:.1%}")
    if last_profile is not None:
        print(
            f"RepoProfile: function_count={last_profile.function_count} "
            f"P75={last_profile.p75_chars} P90={last_profile.p90_chars} "
            f"max_cc={last_profile.max_complexity}"
        )
    else:
        print("RepoProfile: None (< 10 functions found)")
    print("=" * 64)


if __name__ == "__main__":
    main()
