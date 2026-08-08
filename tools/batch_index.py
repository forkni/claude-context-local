#!/usr/bin/env python3
"""
Batch Indexing Wrapper
CLI wrapper for batch files to call indexing with different modes.
Supports multi-model indexing when CLAUDE_MULTI_MODEL_ENABLED=true.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tool_handlers import handle_index_directory


def _dry_run(
    project_path: Path, include_dirs: list[str] | None, exclude_dirs: list[str] | None
) -> int:
    """Preview what an include/exclude filter set would match, without indexing.

    Walks project_path applying the exact same PathFilter precedence resolver
    (defaults + include + exclude) the real indexing path uses, but skips
    hashing/chunking/embedding entirely. Prints a per-pattern breakdown of
    matched files/size, and flags any pattern that matched zero
    files/directories — the silent-failure class this preview exists to catch
    (e.g. a typo'd or absent package name under site-packages).

    Args:
        project_path: Root project directory (resolved against this for
            absolute/relative pattern parsing).
        include_dirs: Raw include_dirs patterns, or None/empty for no include
            filter (whole supported-extension tree, minus defaults/excludes).
        exclude_dirs: Raw exclude_dirs patterns, or None/empty.

    Returns:
        Exit code: 0 if the filter set matched at least one file (or no
        include patterns were given), 1 if every include pattern matched
        zero files (nothing would be indexed).
    """
    import os

    from chunking.language_registry import SUPPORTED_EXTENSIONS
    from search.filters import MatchKind, PathFilter, match_pattern

    root = project_path.resolve()
    path_filter = PathFilter(include_dirs, exclude_dirs, root)

    per_pattern_size: dict[str, int] = dict.fromkeys(
        (p.raw for p in path_filter.include_patterns), 0
    )
    file_count = 0
    total_size = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirpath_p = Path(dirpath)
        rel_dir = (
            "."
            if dirpath_p == root
            else str(dirpath_p.relative_to(root)).replace("\\", "/")
        )

        dirnames[:] = [
            d
            for d in sorted(dirnames)
            if path_filter.should_traverse_dir(
                d if rel_dir == "." else f"{rel_dir}/{d}"
            )
        ]

        for name in sorted(filenames):
            if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            rel_file = name if rel_dir == "." else f"{rel_dir}/{name}"
            if not path_filter.should_index_file(rel_file):
                continue

            try:
                size = (dirpath_p / name).stat().st_size
            except OSError:
                size = 0
            file_count += 1
            total_size += size

            if path_filter.include_patterns:
                rel_parts = tuple(rel_file.split("/"))
                for pat in path_filter.include_patterns:
                    if match_pattern(pat, rel_parts) is MatchKind.INSIDE:
                        per_pattern_size[pat.raw] += size

    print("=" * 70)
    print("DRY RUN - FILTER PREVIEW (no files indexed)")
    print("=" * 70)

    if path_filter.include_patterns:
        matched = 0
        absent = []
        for pat in path_filter.include_patterns:
            count = path_filter.include_hits.get(pat.raw, 0)
            size_mb = per_pattern_size.get(pat.raw, 0) / 1_048_576
            if count:
                matched += 1
                print(f"  {pat.raw:<45} {count:>6} files  {size_mb:>9.2f} MB")
            else:
                absent.append(pat.raw)
                print(f"  {pat.raw:<45} (absent - matched 0 files)")
        print("-" * 70)
        print(
            f"{len(path_filter.include_patterns)} include pattern(s), {matched} matched, "
            f"{len(absent)} absent -> {file_count} files, {total_size / 1_048_576:.2f} MB"
        )
        if absent:
            print()
            print(f"[WARN] {len(absent)} include pattern(s) matched 0 files: {absent}")
    else:
        print("No include_dirs given - whole tree scanned (minus defaults/excludes).")
        print(f"{file_count} files, {total_size / 1_048_576:.2f} MB")

    unmatched_excludes = [
        pat.raw
        for pat in path_filter.exclude_patterns
        if path_filter.exclude_hits.get(pat.raw, 0) == 0
    ]
    if unmatched_excludes:
        print()
        print(
            f"[WARN] {len(unmatched_excludes)} exclude pattern(s) matched 0 "
            f"directories/files: {unmatched_excludes}"
        )

    print("=" * 70)

    if file_count > 5000:
        print(
            f"[WARN] {file_count} files would be indexed - this may take a "
            "while for a large corpus."
        )
        print()

    if path_filter.include_patterns and path_filter.all_includes_unmatched():
        print(
            "[ERROR] Every include_dirs pattern matched 0 files - nothing "
            "would be indexed."
        )
        return 1

    return 0


def main():
    """Entry point for batch indexing CLI.

    Parses command-line arguments for project indexing configuration
    including path, mode, multi-model, and directory filters.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    parser = argparse.ArgumentParser(
        description="Index project for semantic code search"
    )
    parser.add_argument("--path", required=True, help="Path to project directory")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["new", "incremental", "force"],
        help="Indexing mode: new (first-time), incremental (change detection), force (full reindex)",
    )
    parser.add_argument(
        "--multi-model",
        action="store_true",
        help="Index for all models in pool (Qwen3, BGE-M3, F2LLM-v2). Auto-detects if not specified.",
    )
    parser.add_argument(
        "--include-dirs",
        help='Comma-separated directories to include (e.g., "src,lib"). Omit to reuse '
        "the stored list; passing this REPLACES it wholesale (not merged) and forces "
        "a full reindex — always re-pass every directory you still want included.",
    )
    parser.add_argument(
        "--exclude-dirs",
        help='Comma-separated directories to exclude (e.g., "tests,vendor"). Omit to '
        "reuse the stored list; passing this REPLACES it wholesale (not merged) and "
        "forces a full reindex — always re-pass every directory you still want excluded, "
        "or the omitted ones silently become indexable again.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which files --include-dirs/--exclude-dirs would match, with a "
        "per-pattern file-count/size breakdown, then exit WITHOUT indexing. Any "
        "include pattern that matches 0 files is reported explicitly (never silently "
        "dropped). Requires --include-dirs and/or --exclude-dirs to be meaningful; "
        "with neither, it previews the whole supported-extension tree minus defaults.",
    )

    args = parser.parse_args()

    # Validate path
    project_path = Path(args.path)
    if not project_path.exists():
        print(f"[ERROR] Path does not exist: {project_path}")
        return 1

    if not project_path.is_dir():
        print(f"[ERROR] Path is not a directory: {project_path}")
        return 1

    # Determine incremental mode
    if args.mode == "incremental":
        incremental = True
        mode_desc = "Incremental (change detection with Merkle tree)"
    else:  # new or force
        incremental = False
        if args.mode == "new":
            mode_desc = "New (first-time full index)"
        else:
            mode_desc = "Force (full reindex, bypass snapshot)"

    multi_model = False  # Multi-model removed; always single-model

    # Parse directory filters
    include_dirs = None
    if args.include_dirs:
        include_dirs = [d.strip() for d in args.include_dirs.split(",") if d.strip()]
    elif args.mode == "new":
        # "new" means first-time/from-scratch indexing — explicitly clear any
        # filters stored from a prior index of this same path instead of
        # silently inheriting them. None (the default when the flag is
        # omitted) means "caller didn't specify" and triggers snapshot
        # inheritance in mcp_server/tools/index_handlers.py; [] means "user
        # explicitly cleared it".
        include_dirs = []

    exclude_dirs = None
    if args.exclude_dirs:
        exclude_dirs = [d.strip() for d in args.exclude_dirs.split(",") if d.strip()]
    elif args.mode == "new":
        exclude_dirs = []

    if args.dry_run:
        return _dry_run(project_path, include_dirs, exclude_dirs)

    # Display configuration
    print("=" * 70)
    print("PROJECT INDEXING")
    print("=" * 70)
    print(f"Path: {project_path}")
    print(f"Mode: {mode_desc}")
    print(f"Incremental: {incremental}")
    print("Mode: Single-model")
    if include_dirs:
        print(f"Include dirs: {include_dirs}")
    if exclude_dirs:
        print(f"Exclude dirs: {exclude_dirs}")
    print("=" * 70)
    print()

    # Start indexing
    start_time = time.time()

    try:
        print("[INFO] Starting indexing...")
        print()

        # Call async handler
        result = asyncio.run(
            handle_index_directory(
                {
                    "directory_path": str(project_path),
                    "incremental": incremental,
                    "multi_model": multi_model,
                    "include_dirs": include_dirs,
                    "exclude_dirs": exclude_dirs,
                }
            )
        )

        elapsed = time.time() - start_time

        # Display results
        print()
        print("=" * 70)
        print("INDEXING RESULTS")
        print("=" * 70)

        if result.get("success"):
            print("[OK] Indexing completed successfully")
            print()
            print(f"Project: {result.get('project', project_path)}")
            print(f"Mode: {result.get('mode', 'unknown')}")
            print()

            # Multi-model results
            if result.get("multi_model"):
                print(
                    f"Multi-Model: Enabled ({result.get('models_indexed', 0)} models)"
                )
                print()

                # Display per-model results
                for model_result in result.get("results", []):
                    model_name = model_result.get("model", "Unknown").split("/")[-1]
                    dimension = model_result.get("dimension", 0)
                    print(f"  [{model_name} ({dimension}d)]")
                    print(f"    Files added: {model_result.get('files_added', 0)}")
                    print(
                        f"    Files modified: {model_result.get('files_modified', 0)}"
                    )
                    print(f"    Files removed: {model_result.get('files_removed', 0)}")
                    print(f"    Chunks added: {model_result.get('chunks_added', 0)}")
                    print(f"    Time: {model_result.get('time_taken', 0):.2f}s")
                    print()

                # Display totals
                print(f"Total time: {result.get('total_time', elapsed):.2f} seconds")
                print(f"Total files added: {result.get('total_files_added', 0)}")
                print(f"Total chunks added: {result.get('total_chunks_added', 0)}")

            # Single-model results
            else:
                # Effective filters actually used for this run (explicit CLI
                # flag or, when omitted, the project's stored filters) —
                # surfaced here so a corpus-size surprise (e.g. 9,211 chunks
                # instead of ~2,182) is visible instead of silently indexing
                # the whole tree.
                effective_include = result.get("include_dirs")
                effective_exclude = result.get("exclude_dirs")
                if effective_include:
                    print(f"Include dirs (effective): {effective_include}")
                if effective_exclude:
                    print(f"Exclude dirs (effective): {effective_exclude}")
                if effective_include or effective_exclude:
                    print()
                print(f"Files added: {result.get('files_added', 0)}")
                print(f"Files removed: {result.get('files_removed', 0)}")
                print(f"Files modified: {result.get('files_modified', 0)}")
                print()
                print(f"Chunks added: {result.get('chunks_added', 0)}")
                print()
                print(f"Time taken: {result.get('time_taken', elapsed):.2f} seconds")

            print("=" * 70)
            sys.stdout.flush()
            return 0

        else:
            print("[ERROR] Indexing failed")
            error = result.get("error", "Unknown error")
            print(f"Error: {error}")
            print("=" * 70)
            sys.stdout.flush()
            return 1

    except Exception as e:
        elapsed = time.time() - start_time
        print()
        print("=" * 70)
        print("[ERROR] Indexing failed with exception")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print(f"Time elapsed: {elapsed:.2f} seconds")
        print("=" * 70)
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
        return 1


if __name__ == "__main__":
    import os

    exit_code = main()
    sys.stdout.flush()
    # Force exit to avoid hanging on model cleanup (GPU/CUDA resources)
    os._exit(exit_code)
