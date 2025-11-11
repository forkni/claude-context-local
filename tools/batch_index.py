#!/usr/bin/env python3
"""
Batch Indexing Wrapper
CLI wrapper for batch files to call indexing with different modes.
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.server import index_directory


def main():
    parser = argparse.ArgumentParser(
        description="Index project for semantic code search"
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to project directory"
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["new", "incremental", "force"],
        help="Indexing mode: new (first-time), incremental (change detection), force (full reindex)"
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

    # Display configuration
    print("=" * 70)
    print("PROJECT INDEXING")
    print("=" * 70)
    print(f"Path: {project_path}")
    print(f"Mode: {mode_desc}")
    print(f"Incremental: {incremental}")
    print("=" * 70)
    print()

    # Start indexing
    start_time = time.time()

    try:
        print("[INFO] Starting indexing...")
        print()

        result = index_directory(
            str(project_path),
            incremental=incremental
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
            print(f"Project: {result.get('project_name', 'Unknown')}")
            print(f"Directory: {result.get('directory', project_path)}")
            print(f"Mode: {'Incremental' if result.get('incremental') else 'Full'}")
            print()
            print(f"Files added: {result.get('files_added', 0)}")
            print(f"Files removed: {result.get('files_removed', 0)}")
            print(f"Files modified: {result.get('files_modified', 0)}")
            print()
            print(f"Chunks added: {result.get('chunks_added', 0)}")
            print(f"Chunks removed: {result.get('chunks_removed', 0)}")
            print()
            print(f"Time taken: {result.get('time_taken', elapsed):.2f} seconds")

            # Show index statistics
            index_stats = result.get('index_stats', {})
            if index_stats:
                print()
                print("Index Statistics:")
                print(f"  Total files: {index_stats.get('total_files', 0)}")
                print(f"  Supported files: {index_stats.get('supported_files', 0)}")
                print(f"  Total chunks: {index_stats.get('chunks_indexed', 0)}")

            print("=" * 70)
            return 0

        else:
            print("[ERROR] Indexing failed")
            error = result.get('error', 'Unknown error')
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
