#!/usr/bin/env python3
"""
Batch Indexing Wrapper
CLI wrapper for batch files to call indexing with different modes.
Supports multi-model indexing when CLAUDE_MULTI_MODEL_ENABLED=true.
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tool_handlers import handle_index_directory


def main():
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

    # Check multi-model mode
    multi_model_env = os.getenv("CLAUDE_MULTI_MODEL_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    multi_model = args.multi_model if args.multi_model else None  # None = auto-detect

    # Display configuration
    print("=" * 70)
    print("PROJECT INDEXING")
    print("=" * 70)
    print(f"Path: {project_path}")
    print(f"Mode: {mode_desc}")
    print(f"Incremental: {incremental}")
    if multi_model or (multi_model is None and multi_model_env):
        print("Multi-Model: Enabled (Qwen3, BGE-M3, CodeRankEmbed)")
    else:
        print("Multi-Model: Disabled (single model only)")
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
            return 0

        else:
            print("[ERROR] Indexing failed")
            error = result.get("error", "Unknown error")
            print(f"Error: {error}")
            print("=" * 70)
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
        return 1


if __name__ == "__main__":
    sys.exit(main())
