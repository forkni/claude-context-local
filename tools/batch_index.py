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


_DRY_RUN_MAX_ROWS = 150


def _safe_print(text: str) -> None:
    """Print with a Windows-console encoding fallback.

    start_mcp_server.cmd runs Python under the default console codepage (no
    chcp 65001 / PYTHONUTF8) — a non-ASCII file or directory name in the
    matched listing would otherwise raise UnicodeEncodeError and abort the
    preview mid-render. Mirrors tools/summarize_audit.py:safe_print.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def _format_size(num_bytes: int) -> str:
    """Scale a byte count to B/KB/MB/GB for compact per-row display."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def _print_matched_listing(
    root_files: list[tuple[str, int]],
    dir_counts: dict[str, int],
    dir_sizes: dict[str, int],
    total_files: int,
    total_size: int,
    *,
    full: bool = False,
) -> None:
    """Print the concrete file/folder inventory a dry run would index.

    Root-level files are listed by name; every other directory that
    directly contains at least one matched file gets one rollup row (file
    count + size) — a pure container directory with only subfolders gets no
    row of its own. Capped at _DRY_RUN_MAX_ROWS rows per section unless
    full=True: an include reaching into a dependency tree (e.g.
    site-packages/torch) can match thousands of directories, and dumping
    all of them unconditionally would flood the interactive menu. Any
    truncation is reported explicitly (count + size of what's hidden),
    never silently dropped.
    """
    if root_files:
        sorted_root = sorted(root_files, key=lambda item: item[0])
        shown = sorted_root if full else sorted_root[:_DRY_RUN_MAX_ROWS]
        name_width = max((len(name) for name, _ in shown), default=0)
        print()
        _safe_print(f"Root files ({len(root_files)})")
        for name, size in shown:
            _safe_print(f"  {name:<{name_width}}  {_format_size(size):>10}")
        remaining = sorted_root[len(shown) :]
        if remaining:
            rem_size = sum(size for _, size in remaining)
            print(
                f"  ... and {len(remaining)} more root file(s) "
                f"({_format_size(rem_size)}) not shown"
            )
            print("      (re-run with --dry-run-full to list every file)")

    if dir_counts:
        sorted_dirs = sorted(dir_counts)
        shown_dirs = sorted_dirs if full else sorted_dirs[:_DRY_RUN_MAX_ROWS]
        dir_width = max((len(d) + 1 for d in shown_dirs), default=0)
        print()
        _safe_print(f"Directories ({len(dir_counts)})")
        for rel_dir in shown_dirs:
            count = dir_counts[rel_dir]
            size = _format_size(dir_sizes[rel_dir])
            _safe_print(f"  {rel_dir + '/':<{dir_width}}  {count:>6} files  {size:>10}")
        remaining_dirs = sorted_dirs[len(shown_dirs) :]
        if remaining_dirs:
            rem_files = sum(dir_counts[d] for d in remaining_dirs)
            rem_size = sum(dir_sizes[d] for d in remaining_dirs)
            print(
                f"  ... and {len(remaining_dirs)} more directories "
                f"({rem_files} files, {_format_size(rem_size)}) not shown"
            )
            print("      (re-run with --dry-run-full to list every directory)")

    print("-" * 70)
    print(
        f"{total_files} files, {len(dir_counts)} directories, "
        f"{total_size / 1_048_576:.2f} MB"
    )


def _dry_run(
    project_path: Path,
    include_dirs: list[str] | None,
    exclude_dirs: list[str] | None,
    include_exclusive: bool = False,
    *,
    full: bool = False,
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
        include_exclusive: When True, every include pattern is treated as
            narrowing (today's whitelist-only behavior) even if it reaches
            into a dependency tree (venv, site-packages, node_modules, ...).
            When False (default), dependency-tree patterns are additive —
            re-admitted on top of the normal root-down scope.
        full: When True, print every matched root file / directory row
            instead of capping each section at _DRY_RUN_MAX_ROWS.

    Returns:
        Exit code: 0 if the filter set matched at least one file (or no
        include patterns were given), 1 if every include pattern matched
        zero files (nothing would be indexed).
    """
    import os

    from chunking.language_registry import SUPPORTED_EXTENSIONS
    from search.filters import MatchKind, PathFilter, match_pattern

    root = project_path.resolve()
    path_filter = PathFilter(
        include_dirs, exclude_dirs, root, include_exclusive=include_exclusive
    )

    per_pattern_size: dict[str, int] = dict.fromkeys(
        (p.raw for p in path_filter.include_patterns), 0
    )
    additive_raws = {p.raw for p in path_filter.additive_patterns}
    file_count = 0
    total_size = 0
    matched_files: list[str] = []
    root_files: list[tuple[str, int]] = []
    dir_counts: dict[str, int] = {}
    dir_sizes: dict[str, int] = {}

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
            matched_files.append(rel_file)

            if rel_dir == ".":
                root_files.append((name, size))
            else:
                dir_counts[rel_dir] = dir_counts.get(rel_dir, 0) + 1
                dir_sizes[rel_dir] = dir_sizes.get(rel_dir, 0) + size

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
        if path_filter.include_exclusive:
            print(
                "include_exclusive=True - every pattern below is NARROWING "
                "(dependency-tree re-admission disabled)."
            )
        for pat in path_filter.include_patterns:
            count = path_filter.include_hits.get(pat.raw, 0)
            size_mb = per_pattern_size.get(pat.raw, 0) / 1_048_576
            kind = "additive " if pat.raw in additive_raws else "narrowing"
            if count:
                matched += 1
                print(f"  [{kind}] {pat.raw:<45} {count:>6} files  {size_mb:>9.2f} MB")
            else:
                absent.append(pat.raw)
                print(f"  [{kind}] {pat.raw:<45} (absent - matched 0 files)")
        print("-" * 70)
        n_additive = sum(
            1 for pat in path_filter.include_patterns if pat.raw in additive_raws
        )
        n_narrowing = len(path_filter.include_patterns) - n_additive
        print(
            f"{len(path_filter.include_patterns)} include pattern(s) "
            f"({n_additive} additive, {n_narrowing} narrowing), {matched} matched, "
            f"{len(absent)} absent -> {file_count} files, {total_size / 1_048_576:.2f} MB"
        )
        if n_narrowing == 0 and n_additive > 0 and not path_filter.include_exclusive:
            print(
                "All patterns reach into a dependency tree (venv, site-packages, "
                "node_modules, ...) -> ADDITIVE: the normal root-down source scope "
                "is indexed too, these patterns only re-admit what would otherwise "
                "be excluded."
            )
        elif n_narrowing > 0 and not path_filter.include_exclusive:
            print(
                "One or more patterns do NOT reach into a dependency tree -> "
                "NARROWING is in effect: only paths inside/under a narrowing "
                "pattern are indexed (additive patterns still widen that set)."
            )
        if absent:
            print()
            print(f"[WARN] {len(absent)} include pattern(s) matched 0 files: {absent}")
        _print_matched_listing(
            root_files, dir_counts, dir_sizes, file_count, total_size, full=full
        )
    else:
        print("No include_dirs given - whole tree scanned (minus defaults/excludes).")
        _print_matched_listing(
            root_files, dir_counts, dir_sizes, file_count, total_size, full=full
        )

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

    if path_filter.only_dependency_paths_matched(matched_files):
        segments = path_filter.dependency_segments(matched_files)
        if include_exclusive:
            print(
                f"[WARN] Every matched file lies inside a dependency tree {segments} "
                f"- include_dirs={include_dirs} narrowed the whole project down to "
                "library code only, with no first-party source surviving. "
                "include_exclusive=True was passed deliberately, so this would "
                "proceed and produce a dependency-only index."
            )
        else:
            print(
                f"[ERROR] Every matched file lies inside a dependency tree {segments} "
                f"- include_dirs={include_dirs} narrowed the whole project down to "
                "library code only, with no first-party source surviving. If a "
                "dependency-only index is intentional, pass --include-exclusive to "
                "acknowledge and proceed."
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
        help='Comma-separated directories/patterns to include (e.g., "src,lib" or '
        '"venv/Lib/site-packages/torch"). Composition depends on what you name: a '
        "path reaching into a dependency tree (venv, site-packages, node_modules, "
        "...) is ADDITIVE — indexed on top of the normal root-down source scope, "
        "not instead of it; any other path is NARROWING — restricts indexing to "
        'just what you name (e.g. "src/core" alone means ONLY src/core). Mixing '
        "both in one list unions them. Pass --include-exclusive to force every "
        "pattern to be narrowing regardless. Omit to reuse the stored list; "
        "passing this REPLACES it wholesale (not merged) and forces a full "
        "reindex — always re-pass every directory you still want included.",
    )
    parser.add_argument(
        "--exclude-dirs",
        help='Comma-separated directories to exclude (e.g., "tests,vendor"). Always '
        "ADDED to the built-in exclusions (never replaces them) — the opposite "
        "composition rule from --include-dirs above. Omit to reuse the stored "
        "list; passing this REPLACES it wholesale (not merged) and forces a full "
        "reindex — always re-pass every directory you still want excluded, or "
        "the omitted ones silently become indexable again.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which files --include-dirs/--exclude-dirs would match, with a "
        "per-pattern file-count/size breakdown, then exit WITHOUT indexing. Any "
        "include pattern that matches 0 files is reported explicitly (never silently "
        "dropped). Requires --include-dirs and/or --exclude-dirs to be meaningful; "
        "with neither, it previews the whole supported-extension tree minus defaults. "
        "Also lists root-level files by name and every matched directory with its "
        "file count/size, capped at 150 rows per section (see --dry-run-full).",
    )
    parser.add_argument(
        "--dry-run-full",
        action="store_true",
        help="With --dry-run, list every matched root file and directory instead of "
        "capping each section at 150 rows. No effect without --dry-run.",
    )
    parser.add_argument(
        "--include-exclusive",
        action="store_true",
        default=None,
        help="Escape hatch: treat every --include-dirs pattern as narrowing (index "
        "ONLY the named paths), even patterns that reach into a dependency tree "
        "(venv, site-packages, node_modules, ...). By default those dependency-tree "
        "patterns are ADDITIVE — re-admitted on top of the normal root-down source "
        "scope, not a replacement for it. Omit to reuse the stored value; forces a "
        "full reindex when it changes.",
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
        return _dry_run(
            project_path,
            include_dirs,
            exclude_dirs,
            bool(args.include_exclusive),
            full=bool(args.dry_run_full),
        )

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
    if args.include_exclusive:
        print("Include exclusive: True (dependency-tree patterns NOT additive)")
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
                    "include_exclusive": args.include_exclusive,
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
                effective_exclusive = result.get("include_exclusive")
                if effective_include:
                    print(f"Include dirs (effective): {effective_include}")
                if effective_exclude:
                    print(f"Exclude dirs (effective): {effective_exclude}")
                if effective_exclusive:
                    print(f"Include exclusive (effective): {effective_exclusive}")
                if effective_include or effective_exclude or effective_exclusive:
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
