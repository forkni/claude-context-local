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
        help="Index for all models in pool (Qwen3, BGE-M3, CodeRankEmbed). Auto-detects if not specified.",
    )
    parser.add_argument(
        "--include-dirs",
        help='Comma-separated directories to include (e.g., "src,lib"). Immutable after project creation.',
    )
    parser.add_argument(
        "--exclude-dirs",
        help='Comma-separated directories to exclude (e.g., "tests,vendor"). Immutable after project creation.',
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

    # Check multi-model mode from config file (priority) or environment
    from search.config import get_search_config

    config = get_search_config()
    multi_model_config = config.routing.multi_model_enabled  # From search_config.json

    # CLI flag overrides, then config, then env var fallback
    if args.multi_model:
        multi_model = True  # Explicit --multi-model flag
    else:
        # Use config file setting (user's menu selection)
        multi_model = multi_model_config

    # Parse directory filters
    include_dirs = None
    if args.include_dirs:
        include_dirs = [d.strip() for d in args.include_dirs.split(",") if d.strip()]

    exclude_dirs = None
    if args.exclude_dirs:
        exclude_dirs = [d.strip() for d in args.exclude_dirs.split(",") if d.strip()]

    # Display configuration
    print("=" * 70)
    print("PROJECT INDEXING")
    print("=" * 70)
    print(f"Path: {project_path}")
    print(f"Mode: {mode_desc}")
    print(f"Incremental: {incremental}")
    if multi_model:
        # Show correct pool based on config
        from search.config import get_search_config

        try:
            config = get_search_config()
            pool_type = config.routing.multi_model_pool or "full"
        except Exception as e:
            print(f"Config unavailable, using full pool: {e}")
            pool_type = "full"

        if pool_type == "lightweight-speed":
            print("Multi-Model: Enabled (BGE-M3 + gte-modernbert, 1.65GB)")
        else:
            print("Multi-Model: Enabled (Qwen3, BGE-Code)")
    else:
        print("Multi-Model: Disabled (single model only)")
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
