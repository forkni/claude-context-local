"""
Init-path diagnostic: snoop tracing + pyheat heatmap of server initialization.

Profiles the full server startup pipeline:
  1. Import timing (torch, sentence_transformers)
  2. initialize_server_state()  [mcp_server/resource_manager.py:171-239]
  3. ModelLoader.load()         [embeddings/model_loader.py:218-496]
  4. HybridSearcher.__init__()  [search/hybrid_searcher.py:48-174]
  5. First embed_query()        [embeddings/embedder.py:1121-1209]

Usage:
    # Silent run — suitable for pyheat heatmap generation
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_init.py

    # snoop line-by-line trace to stderr (requires: pip install -e ".[profile]")
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_init.py --snoop

    # Deeper trace — also traces methods called from patched targets
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_init.py --snoop --depth 2

    # Redirect snoop output to file
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_init.py --snoop --output debug.log

NOTE: snoop and pyheat both use sys.settrace — NEVER combine them.
      Use pyheat via _pyheat_wrapper_init.py (no --snoop flag).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


# Add project root to sys.path so all project packages are importable
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# pyheat (pprofile) clears sys.argv before running the profiled script.
# Guard against IndexError in argparse when argv is empty.
if not sys.argv:
    sys.argv = ["profile_init.py"]


def _check_venv() -> None:
    """Fail fast if not running inside the project .venv."""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if not in_venv:
        print(
            "ERROR: Run from .venv to ensure all dependencies are available.\n"
            "       Use: .venv/Scripts/python.exe scripts/benchmark/profiling/profile_init.py",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    # pyheat guard (re-applied here for safety when called via wrapper)
    if not sys.argv:
        sys.argv = ["profile_init.py"]

    _check_venv()

    parser = argparse.ArgumentParser(
        prog="profile_init.py",
        description="Profile claude-context-local server initialization pipeline",
    )
    parser.add_argument(
        "--snoop",
        action="store_true",
        default=False,
        help=(
            "Enable snoop line-by-line tracing on key init methods. "
            "Outputs to stderr. WARNING: adds overhead — do not use with pyheat."
        ),
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        help=(
            "snoop trace depth: 1=only patched method, "
            "2=also trace methods they call (default: 1)"
        ),
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
        help="Project path to use for searcher init (default: project root)",
    )
    args = parser.parse_args()

    project_path = args.project or _PROJECT_ROOT

    # -----------------------------------------------------------------------
    # Step 1: Import timing
    # -----------------------------------------------------------------------
    print("[PROFILE] Measuring import times...", file=sys.stderr)

    t_torch = time.perf_counter()
    import torch  # noqa: F401

    torch_ms = (time.perf_counter() - t_torch) * 1000

    t_st = time.perf_counter()
    import sentence_transformers  # noqa: F401

    st_ms = (time.perf_counter() - t_st) * 1000

    print(f"  torch import:                {torch_ms:.0f}ms", file=sys.stderr)
    print(f"  sentence_transformers import: {st_ms:.0f}ms", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Optionally monkey-patch target methods with @snoop BEFORE instantiation.
    # snoop.install() only makes pp/snoop/spy builtins available — it does NOT
    # auto-trace imported code. We must explicitly decorate target methods.
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
                from embeddings.model_cache import ModelCacheManager
                from embeddings.model_loader import ModelLoader
                from mcp_server.model_pool_manager import ModelPoolManager
                from mcp_server.resource_manager import (
                    initialize_server_state as _init_fn,
                )
                from search.hybrid_searcher import HybridSearcher

                depth = args.depth
                _snoop = cfg.snoop(depth=depth)

                ModelLoader.load = _snoop(ModelLoader.load)
                ModelCacheManager.validate_cache = _snoop(
                    ModelCacheManager.validate_cache
                )
                HybridSearcher.__init__ = _snoop(HybridSearcher.__init__)
                HybridSearcher._load_indices_parallel = _snoop(
                    HybridSearcher._load_indices_parallel
                )
                ModelPoolManager.get_embedder = _snoop(ModelPoolManager.get_embedder)

                import mcp_server.resource_manager as _rm_mod

                _rm_mod.initialize_server_state = _snoop(_init_fn)

                print(
                    f"[INFO] snoop active (depth={depth}) — tracing:",
                    file=sys.stderr,
                )
                print("         ModelLoader.load()", file=sys.stderr)
                print("         ModelCacheManager.validate_cache()", file=sys.stderr)
                print("         HybridSearcher.__init__()", file=sys.stderr)
                print(
                    "         HybridSearcher._load_indices_parallel()", file=sys.stderr
                )
                print("         ModelPoolManager.get_embedder()", file=sys.stderr)
                print("         initialize_server_state()", file=sys.stderr)
                print(file=sys.stderr)
        except ImportError as e:
            print(f"[WARNING] snoop setup failed: {e}", file=sys.stderr)
            args.snoop = False

    # -----------------------------------------------------------------------
    # Step 2: initialize_server_state()
    # -----------------------------------------------------------------------
    print("[PROFILE] initialize_server_state()...", file=sys.stderr)
    os.environ.setdefault("CLAUDE_DEFAULT_PROJECT", project_path)

    t0 = time.perf_counter()
    from mcp_server.resource_manager import initialize_server_state

    initialize_server_state()
    init_ms = (time.perf_counter() - t0) * 1000
    print(f"  initialize_server_state(): {init_ms:.0f}ms", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Step 3: get_searcher() + ModelLoader.load() (lazy, triggered here)
    # -----------------------------------------------------------------------
    print("[PROFILE] get_searcher() — triggers ModelLoader.load()...", file=sys.stderr)
    t1 = time.perf_counter()
    from mcp_server.search_factory import get_searcher

    get_searcher()
    searcher_ms = (time.perf_counter() - t1) * 1000
    print(f"  get_searcher() total: {searcher_ms:.0f}ms", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Step 4: First embed_query() (JIT warm-up)
    # -----------------------------------------------------------------------
    print("[PROFILE] First embed_query()...", file=sys.stderr)
    from mcp_server.model_pool_manager import get_embedder

    embedder = get_embedder()
    t2 = time.perf_counter()
    embedder.embed_query("function definition")
    first_query_ms = (time.perf_counter() - t2) * 1000
    print(f"  first embed_query(): {first_query_ms:.0f}ms", file=sys.stderr)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    total_ms = (time.perf_counter() - t_torch) * 1000
    print(file=sys.stderr)
    print("[PROFILE SUMMARY]", file=sys.stderr)
    print(f"  torch import:                {torch_ms:>8.0f}ms", file=sys.stderr)
    print(f"  sentence_transformers import:{st_ms:>8.0f}ms", file=sys.stderr)
    print(f"  initialize_server_state():   {init_ms:>8.0f}ms", file=sys.stderr)
    print(f"  get_searcher() (model+index):{searcher_ms:>8.0f}ms", file=sys.stderr)
    print(f"  first embed_query():         {first_query_ms:>8.0f}ms", file=sys.stderr)
    print("  ─────────────────────────────────────", file=sys.stderr)
    print(f"  TOTAL (from first import):   {total_ms:>8.0f}ms", file=sys.stderr)
    print(file=sys.stderr)
    print("[OK] Initialization profile complete.", file=sys.stderr)


if __name__ == "__main__":
    main()
