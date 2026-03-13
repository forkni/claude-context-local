"""
First-query diagnostic: snoop tracing + pyheat heatmap of search pipeline.

Profiles the search pipeline after initialization:
  1. get_searcher() construction  [mcp_server/search_factory.py:247-261]
  2. embed_query()                [embeddings/embedder.py:1121-1209]
  3. HybridSearcher.search()      [search/hybrid_searcher.py:595-640]
  4. SearchExecutor.execute_single_hop() [search/search_executor.py:83-179]

Usage:
    # Silent run — suitable for pyheat heatmap generation
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_first_query.py

    # snoop line-by-line trace to stderr (requires: pip install -e ".[profile]")
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_first_query.py --snoop

    # Custom query and depth
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_first_query.py --snoop --depth 2 --query "authentication"

NOTE: snoop and pyheat both use sys.settrace — NEVER combine them.
      Use pyheat via _pyheat_wrapper_query.py (no --snoop flag).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


# Add project root to sys.path
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# pyheat guard
if not sys.argv:
    sys.argv = ["profile_first_query.py"]


def _check_venv() -> None:
    """Fail fast if not running inside the project .venv."""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if not in_venv:
        print(
            "ERROR: Run from .venv to ensure all dependencies are available.\n"
            "       Use: .venv/Scripts/python.exe scripts/benchmark/profiling/profile_first_query.py",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    if not sys.argv:
        sys.argv = ["profile_first_query.py"]

    _check_venv()

    parser = argparse.ArgumentParser(
        prog="profile_first_query.py",
        description="Profile claude-context-local first search query pipeline",
    )
    parser.add_argument(
        "--snoop",
        action="store_true",
        default=False,
        help=(
            "Enable snoop line-by-line tracing on key search methods. "
            "Outputs to stderr. WARNING: adds overhead — do not use with pyheat."
        ),
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help="snoop trace depth (default: 1)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Redirect snoop output to this file path (default: stderr)",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Project path to use (default: project root)",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="function definition",
        help="Query string to use for profiling (default: 'function definition')",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=4,
        help="Number of results to return (default: 4)",
    )
    args = parser.parse_args()

    project_path = args.project or _PROJECT_ROOT
    os.environ.setdefault("CLAUDE_DEFAULT_PROJECT", project_path)

    # -----------------------------------------------------------------------
    # Initialize server state first (not the focus of this script)
    # -----------------------------------------------------------------------
    print("[PROFILE] Initializing server state...", file=sys.stderr)
    t_init = time.perf_counter()
    from mcp_server.resource_manager import initialize_server_state

    initialize_server_state()
    init_ms = (time.perf_counter() - t_init) * 1000
    print(f"  initialize_server_state(): {init_ms:.0f}ms", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Optionally monkey-patch search methods with @snoop
    # -----------------------------------------------------------------------
    if args.snoop:
        try:
            from utils.debug_utils import create_snoop_config

            cfg = create_snoop_config(out=args.output, enabled=True)
            if cfg is None:
                print(
                    "[WARNING] snoop not installed. "
                    "Install with: pip install -e '.[profile]'",
                    file=sys.stderr,
                )
                args.snoop = False
            else:
                from embeddings.embedder import CodeEmbedder
                from search.search_executor import SearchExecutor

                depth = args.depth
                _snoop = cfg.snoop(depth=depth)

                CodeEmbedder.embed_query = _snoop(CodeEmbedder.embed_query)
                SearchExecutor.execute_single_hop = _snoop(
                    SearchExecutor.execute_single_hop
                )

                print(
                    f"[INFO] snoop active (depth={depth}) — tracing:",
                    file=sys.stderr,
                )
                print("         CodeEmbedder.embed_query()", file=sys.stderr)
                print("         SearchExecutor.execute_single_hop()", file=sys.stderr)
                print(file=sys.stderr)
        except ImportError as e:
            print(f"[WARNING] snoop setup failed: {e}", file=sys.stderr)
            args.snoop = False

    # -----------------------------------------------------------------------
    # Step 1: get_searcher() — constructs HybridSearcher + loads indices
    # -----------------------------------------------------------------------
    print("[PROFILE] get_searcher()...", file=sys.stderr)
    t_searcher = time.perf_counter()
    from mcp_server.search_factory import get_searcher

    searcher = get_searcher()
    searcher_ms = (time.perf_counter() - t_searcher) * 1000
    print(f"  get_searcher(): {searcher_ms:.0f}ms", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Step 2: First embed_query() (JIT warm-up)
    # -----------------------------------------------------------------------
    print(f"[PROFILE] First embed_query('{args.query}')...", file=sys.stderr)
    from mcp_server.model_pool_manager import get_embedder

    embedder = get_embedder()
    t_embed = time.perf_counter()
    embedder.embed_query(args.query)
    embed_ms = (time.perf_counter() - t_embed) * 1000
    print(f"  embed_query(): {embed_ms:.0f}ms", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Step 3: Full search pipeline
    # -----------------------------------------------------------------------
    print(f"[PROFILE] searcher.search('{args.query}', k={args.k})...", file=sys.stderr)
    t_search = time.perf_counter()
    results = searcher.search(args.query, k=args.k)
    search_ms = (time.perf_counter() - t_search) * 1000
    result_count = len(results) if results else 0
    print(
        f"  search(): {search_ms:.0f}ms ({result_count} results)",
        file=sys.stderr,
    )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    total_ms = searcher_ms + embed_ms + search_ms
    print(file=sys.stderr)
    print("[PROFILE SUMMARY]", file=sys.stderr)
    print(f"  get_searcher():    {searcher_ms:>8.0f}ms", file=sys.stderr)
    print(f"  embed_query():     {embed_ms:>8.0f}ms", file=sys.stderr)
    print(
        f"  search():          {search_ms:>8.0f}ms  ({result_count} results)",
        file=sys.stderr,
    )
    print("  ─────────────────────────────────────", file=sys.stderr)
    print(f"  TOTAL:             {total_ms:>8.0f}ms", file=sys.stderr)
    print(file=sys.stderr)
    print("[OK] First query profile complete.", file=sys.stderr)


if __name__ == "__main__":
    main()
