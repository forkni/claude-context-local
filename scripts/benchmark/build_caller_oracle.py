#!/usr/bin/env python3
"""Build caller oracle dataset for direct-caller recall benchmarking.

Uses two sources to establish ground truth:
  1. PyCG (pip install pycg) — high-precision (~99%) static call graph
  2. Ripgrep — over-approximation for catching PyCG misses

Writes to evaluation/caller_golden.json (or --output path) in the same
normalized-chunk-ID format as evaluation/golden_dataset.json.

Usage:
    # Build oracle for all targets in DEFAULT_TARGETS
    python build_caller_oracle.py --project-path /path/to/project

    # Add a custom target
    python build_caller_oracle.py --project-path /path \\
        --target search/relationship_analyzer.py:method:RelationshipAnalyzer.analyze_impact

    # Save to custom path
    python build_caller_oracle.py --project-path /path \\
        --output evaluation/my_callers.json

    # Dry-run: show targets without saving
    python build_caller_oracle.py --project-path /path --dry-run
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.chunk_mapping import (  # noqa: E402, I001
    build_line_to_chunk_map as _build_line_to_chunk_map_shared,
    chunk_id_from_fqn as _chunk_id_from_fqn_shared,
    find_enclosing_chunk as _find_enclosing_chunk_shared,
)
from evaluation.metrics import normalize_chunk_id  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Default target list (hand-curated)
# ---------------------------------------------------------------------------

DEFAULT_TARGETS: list[dict[str, str]] = [
    {
        "id": "C001",
        "category": "O",
        "target_chunk_id": "evaluation/metrics.py:function:normalize_chunk_id",
        "description": "normalize_chunk_id strips line-range from chunk IDs",
        "symbol": "normalize_chunk_id",
    },
    {
        "id": "C002",
        "category": "O",
        "target_chunk_id": "search/relationship_analyzer.py:method:RelationshipAnalyzer._enrich_callers",
        "description": "_enrich_callers converts RelationshipEntry list to enriched dicts",
        "symbol": "_enrich_callers",
    },
    {
        "id": "C003",
        "category": "O",
        "target_chunk_id": "evaluation/metrics.py:function:calculate_recall_at_k",
        "description": "calculate_recall_at_k is the core Recall@k metric",
        "symbol": "calculate_recall_at_k",
    },
    {
        "id": "C004",
        "category": "O",
        "target_chunk_id": "graph/graph_storage.py:method:CodeGraphStorage.add_call_edge",
        "description": "add_call_edge adds a caller→callee edge",
        "symbol": "add_call_edge",
    },
    {
        "id": "C005",
        "category": "O",
        "target_chunk_id": "search/hybrid_searcher.py:method:HybridSearcher.get_by_chunk_id",
        "description": "get_by_chunk_id does exact chunk metadata lookup",
        "symbol": "get_by_chunk_id",
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LINE_RANGE_RE = re.compile(r":\d+-\d+:")


def _build_line_to_chunk_map(
    metadata_store: Any,
    semantic_types: frozenset[str] | None = None,
) -> dict[str, list[tuple[int, int, str]]]:
    """Build a per-file sorted list of (start, end, normalized_chunk_id).

    Delegates to :func:`evaluation.chunk_mapping.build_line_to_chunk_map`
    with ``normalize=True`` (oracle always uses normalized ids).
    """
    return _build_line_to_chunk_map_shared(
        metadata_store, semantic_types=semantic_types, normalize=True
    )


def _find_enclosing_chunk(
    line_map: dict[str, list[tuple[int, int, str]]],
    rel_path: str,
    line_num: int,
) -> str | None:
    """Return the normalized chunk_id of the innermost chunk containing (rel_path, line_num)."""
    return _find_enclosing_chunk_shared(line_map, rel_path, line_num)


def _rg_find_callers(
    symbol: str,
    project_root: Path,
) -> list[tuple[str, int]]:
    """Run ripgrep to find all `symbol(` call sites.

    Returns list of (relative_path, line_number) tuples.
    Requires ripgrep (rg) on PATH.
    """
    pattern = rf"\b{re.escape(symbol)}\s*\("
    try:
        proc = subprocess.run(
            ["rg", "--type", "py", "-n", "--no-heading", pattern, str(project_root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        print("[WARN] ripgrep (rg) not found — ripgrep pass skipped", file=sys.stderr)
        return []
    except subprocess.TimeoutExpired:
        print(f"[WARN] ripgrep timed out for symbol '{symbol}'", file=sys.stderr)
        return []

    results: list[tuple[str, int]] = []
    for line in proc.stdout.splitlines():
        # rg output format: /abs/path/file.py:42:  code line
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        abs_path, lineno_str = parts[0], parts[1]
        try:
            lineno = int(lineno_str)
        except ValueError:
            continue
        # Skip test files
        if "/test_" in abs_path or "/tests/" in abs_path:
            continue
        try:
            rel_path = str(Path(abs_path).relative_to(project_root)).replace("\\", "/")
        except ValueError:
            continue
        results.append((rel_path, lineno))
    return results


def _pycg_find_callers(
    target_fqn: str,
    project_root: Path,
) -> list[str]:
    """Run PyCG to get fully-qualified callers of target_fqn.

    Args:
        target_fqn: Fully-qualified name like "evaluation.metrics.normalize_chunk_id"
        project_root: Project root directory

    Returns:
        List of fully-qualified caller names.  Empty if PyCG unavailable.
    """
    try:
        import pycg  # type: ignore[import]
        import pycg.pycg  # type: ignore[import]
    except ImportError:
        return []

    try:
        py_files = list(project_root.rglob("*.py"))
        # Filter out test files and hidden dirs
        py_files = [
            f
            for f in py_files
            if "/tests/" not in str(f).replace("\\", "/")
            and "/.venv/" not in str(f).replace("\\", "/")
        ]

        cg_generator = pycg.pycg.CallGraphGenerator(
            [str(f) for f in py_files], str(project_root), max_iter=10
        )
        cg_generator.analyze()
        cg = cg_generator.output()

        callers: list[str] = []
        for caller, callees in cg.items():
            if target_fqn in callees or any(
                target_fqn.endswith("." + callee) for callee in callees
            ):
                callers.append(caller)
        return callers
    except Exception as e:
        print(f"[WARN] PyCG analysis failed: {e}", file=sys.stderr)
        return []


def _chunk_id_from_pycg_fqn(
    fqn: str,
    line_map: dict[str, list[tuple[int, int, str]]],
    project_root: Path,
) -> str | None:
    """Best-effort mapping from PyCG FQN to normalized chunk_id.

    Delegates to :func:`evaluation.chunk_mapping.chunk_id_from_fqn`.
    """
    return _chunk_id_from_fqn_shared(fqn, line_map, project_root)


# ---------------------------------------------------------------------------
# Main oracle builder
# ---------------------------------------------------------------------------


def build_oracle_for_target(
    target: dict[str, str],
    searcher: Any,
    project_root: Path,
) -> list[str]:
    """Compute the expected-caller set for a target using ripgrep + PyCG.

    Returns a sorted, deduplicated list of normalized caller chunk IDs.
    """
    symbol = target["symbol"]
    print(f"  [{target['id']}] {target['target_chunk_id']}", flush=True)

    # Build per-file line→chunk map from the live index
    metadata_store = None
    try:
        metadata_store = searcher.dense_index.metadata_store
    except AttributeError:
        print("    [WARN] Cannot access metadata_store — line mapping unavailable")

    line_map: dict[str, list[tuple[int, int, str]]] = {}
    if metadata_store is not None:
        line_map = _build_line_to_chunk_map(metadata_store)
        print(f"    Line map: {len(line_map)} files indexed")

    callers: set[str] = set()

    # 1. ripgrep pass
    rg_hits = _rg_find_callers(symbol, project_root)
    print(f"    ripgrep: {len(rg_hits)} call sites (non-test)")
    for rel_path, lineno in rg_hits:
        cid = _find_enclosing_chunk(line_map, rel_path, lineno)
        if cid:
            # Exclude self-callers (target calling itself, e.g. recursion)
            if normalize_chunk_id(target["target_chunk_id"]) != cid:
                callers.add(cid)
        else:
            print(f"    [SKIP] {rel_path}:{lineno} — no enclosing chunk found")

    # 2. PyCG pass (optional, dev-only)
    # Convert target chunk_id back to a PyCG-style FQN for lookup
    target_norm = normalize_chunk_id(target["target_chunk_id"])
    # e.g. "evaluation/metrics.py:function:normalize_chunk_id"
    # → "evaluation.metrics.normalize_chunk_id"
    path_part = target_norm.split(":")[0].replace("/", ".").removesuffix(".py")
    name_part = target_norm.split(":")[-1]
    target_fqn = f"{path_part}.{name_part}"

    pycg_callers = _pycg_find_callers(target_fqn, project_root)
    if pycg_callers:
        print(f"    PyCG: {len(pycg_callers)} callers")
        for fqn in pycg_callers:
            cid = _chunk_id_from_pycg_fqn(fqn, line_map, project_root)
            if cid and cid != target_norm:
                callers.add(cid)
    else:
        print("    PyCG: unavailable or returned no results")

    result = sorted(callers)
    print(f"    → {len(result)} expected callers")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build caller oracle dataset from PyCG + ripgrep"
    )
    parser.add_argument(
        "--project-path",
        required=True,
        help="Path to the indexed project root",
    )
    parser.add_argument(
        "--output",
        default=str(_PROJECT_ROOT / "evaluation" / "caller_golden.json"),
        help="Output path for the caller_golden.json (default: evaluation/caller_golden.json)",
    )
    parser.add_argument(
        "--target",
        action="append",
        dest="extra_targets",
        metavar="CHUNK_ID",
        help="Additional target chunk ID (normalized) to add. Repeatable.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print targets without writing output",
    )
    args = parser.parse_args()

    project_root = Path(args.project_path).resolve()
    if not project_root.exists():
        print(f"[ERROR] Project path not found: {project_root}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Project root: {project_root}")
    print(f"[INFO] Output: {args.output}")

    # Load searcher to access metadata store
    try:
        from mcp_server.search_factory import get_searcher

        searcher = get_searcher(project_path=str(project_root))
        print(f"[INFO] Searcher loaded: {type(searcher).__name__}")
    except Exception as e:
        print(f"[WARN] Could not load searcher: {e}", file=sys.stderr)
        print("[WARN] Line-map-based caller resolution unavailable", file=sys.stderr)
        searcher = None

    targets = list(DEFAULT_TARGETS)

    # Add extra targets from CLI
    if args.extra_targets:
        for i, extra in enumerate(args.extra_targets):
            normalized = normalize_chunk_id(extra)
            symbol = normalized.split(":")[-1]
            targets.append(
                {
                    "id": f"CX{i + 1:02d}",
                    "category": "O",
                    "target_chunk_id": normalized,
                    "description": f"Extra target: {normalized}",
                    "symbol": symbol,
                }
            )

    print(f"\n[INFO] Building oracle for {len(targets)} targets...")
    queries = []
    for target in targets:
        try:
            expected = build_oracle_for_target(target, searcher, project_root)
        except Exception as e:
            print(f"  [ERROR] Failed for {target['id']}: {e}", file=sys.stderr)
            expected = []

        queries.append(
            {
                "id": target["id"],
                "category": target["category"],
                "description": target["description"],
                "target_chunk_id": normalize_chunk_id(target["target_chunk_id"]),
                "expected_callers": expected,
            }
        )

    dataset = {
        "_meta": {
            "description": "Golden caller dataset for direct-caller recall benchmarking",
            "generated_by": "scripts/benchmark/build_caller_oracle.py",
            "normalization": "Chunk IDs normalized (line ranges stripped)",
            "total_queries": len(queries),
            "sources": ["ripgrep", "pycg (if installed)"],
        },
        "queries": queries,
    }

    if args.dry_run:
        print("\n[DRY-RUN] Would write:")
        print(json.dumps(dataset, indent=2))
        return

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"\n[INFO] Written to {output_path}")


if __name__ == "__main__":
    main()
