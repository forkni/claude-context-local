#!/usr/bin/env python
"""Read-only phantom-node diagnostic, gating Workstreams D and E (see the
"Fix silent indexing loss" plan, `graph/graph_storage.py` and
`graph/graph_queries.py`).

Two independent questions, answered from the SAME graph snapshot so both
gates share one load:

1. Workstream D (orphan phantom pruning) — is there anything for
   ``CodeGraphStorage.prune_orphan_symbol_nodes()`` to prune on THIS index
   right now? If ``orphan_phantoms == 0``, pruning is provably a no-op here
   (nothing removed -> no pagerank/MRR delta possible), matching the plan's
   own reasoning that a from-scratch index has no orphans.

2. Workstream E (phantom-excluded PageRank) pre-flight — per the plan, this
   "gates the A/B, not the other way round": dumps the top-20 nodes by raw
   PageRank and reports (a) what fraction of the top 20 are phantoms, and
   (b) what fraction of REAL (non-phantom) nodes clear
   ``GraphEnhancedConfig.centrality_boost_threshold`` after max-normalization
   (mirroring ``search/centrality_ranker.py::get_centrality_scores``'s own
   ``score / max_score`` normalization exactly). If the top node is not a
   phantom and most real chunks already clear the threshold, the hypothesis
   is falsified and Workstream E is dropped without spending A/B time.

Phantom predicate is ``graph.schema.is_phantom_node`` -- the single shared
definition also used by ``CodeGraphStorage.prune_orphan_symbol_nodes`` and
``GraphQueryEngine`` (NOT the colon-count heuristic in
``search/chunk_id.py::is_chunk_id``, which the plan calls out as less
robust). See ADR-0055.

Read-only: loads the persisted graph JSON and computes pagerank in memory.
Never mutates or saves ``CodeGraphStorage``.

Usage (module form required -- ``scripts`` is not in the editable-install
package map, ADR-0040):
    .venv/Scripts/python.exe -m scripts.benchmark.graph_phantom_preflight \
        --project-name claude-context-local \
        [--storage-dir C:/Users/Inter/.claude_code_search] \
        [--top-n 20] [--threshold 0.02] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from graph.graph_queries import GraphQueryEngine
from graph.graph_storage import CodeGraphStorage
from graph.schema import is_phantom_node as is_phantom
from search.config import GraphEnhancedConfig


DEFAULT_STORAGE_DIR = Path.home() / ".claude_code_search" / "projects"


def find_call_graph_dir(storage_root: Path, project_name: str) -> Path:
    """Locate a project's storage dir under ``.../projects/`` by substring
    match on the directory name (e.g. "claude-context-local" matches
    "claude-context-local_9e7f0a98_f2llm-v2-0.6b_1024d")."""
    matches = sorted(
        d for d in storage_root.iterdir() if d.is_dir() and project_name in d.name
    )
    if not matches:
        raise SystemExit(
            f"No project directory containing {project_name!r} found under {storage_root}"
        )
    if len(matches) > 1:
        names = ", ".join(m.name for m in matches)
        raise SystemExit(
            f"Ambiguous --project-name {project_name!r}, matches: {names}. "
            f"Pass a more specific substring."
        )
    return matches[0]


def load_storage(project_dir: Path) -> CodeGraphStorage:
    graph_files = list(project_dir.glob("*_call_graph.json"))
    if not graph_files:
        raise SystemExit(f"No *_call_graph.json found under {project_dir}")
    project_id = graph_files[0].name[: -len("_call_graph.json")]
    storage = CodeGraphStorage(project_id, storage_dir=project_dir)
    if not storage.load():
        raise SystemExit(f"Failed to load call graph from {graph_files[0]}")
    return storage


def run_diagnostic(storage: CodeGraphStorage, top_n: int, threshold: float) -> dict:
    graph = storage.graph
    total_nodes = graph.number_of_nodes()

    phantom_ids = [n for n, d in graph.nodes(data=True) if is_phantom(d)]
    orphan_phantom_ids = [n for n in phantom_ids if graph.degree(n) == 0]

    engine = GraphQueryEngine(storage)
    raw_scores = engine.compute_centrality(method="pagerank")
    max_score = max(raw_scores.values()) if raw_scores else 0.0

    ranked = sorted(raw_scores.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:top_n]
    top_phantom_flags = [is_phantom(graph.nodes[n]) for n, _ in top]
    top_phantom_fraction = (
        sum(top_phantom_flags) / len(top_phantom_flags) if top_phantom_flags else 0.0
    )

    real_ids = [n for n in raw_scores if n not in set(phantom_ids)]
    real_clearing = 0
    if max_score > 0:
        for n in real_ids:
            normalized = raw_scores[n] / max_score
            if normalized > threshold:
                real_clearing += 1
    real_clearing_fraction = real_clearing / len(real_ids) if real_ids else 0.0

    return {
        # Workstream D gate
        "total_nodes": total_nodes,
        "phantom_nodes": len(phantom_ids),
        "orphan_phantom_nodes": len(orphan_phantom_ids),
        "prune_is_noop_here": len(orphan_phantom_ids) == 0,
        # Workstream E pre-flight
        "top_n": top_n,
        "top_nodes": [
            {"node": n, "raw_pagerank": score, "is_phantom": phantom}
            for (n, score), phantom in zip(top, top_phantom_flags, strict=True)
        ],
        "top_phantom_fraction": top_phantom_fraction,
        "max_node_is_phantom": bool(top_phantom_flags[0])
        if top_phantom_flags
        else False,
        "threshold": threshold,
        "real_node_count": len(real_ids),
        "real_clearing_threshold": real_clearing,
        "real_clearing_fraction": real_clearing_fraction,
        "hypothesis_falsified": (
            top_phantom_flags
            and not top_phantom_flags[0]
            and real_clearing_fraction > 0.5
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-name",
        required=True,
        help="Substring to match a project directory under --storage-dir",
    )
    parser.add_argument(
        "--storage-dir",
        type=Path,
        default=DEFAULT_STORAGE_DIR,
        help=f"Root 'projects' dir to search under (default: {DEFAULT_STORAGE_DIR})",
    )
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--threshold",
        type=float,
        default=GraphEnhancedConfig().centrality_boost_threshold,
        help="Normalized-centrality threshold (default: config field default)",
    )
    parser.add_argument("--json", type=Path, default=None, help="Optional output path")
    args = parser.parse_args()

    project_dir = find_call_graph_dir(args.storage_dir, args.project_name)
    storage = load_storage(project_dir)
    result = run_diagnostic(storage, args.top_n, args.threshold)

    print(f"Project dir: {project_dir}")
    print(f"Total nodes: {result['total_nodes']}")
    print(
        f"Phantom nodes: {result['phantom_nodes']} "
        f"(orphan/degree-0: {result['orphan_phantom_nodes']})"
    )
    print(f"[Workstream D] prune_is_noop_here: {result['prune_is_noop_here']}")
    print()
    print(f"Top {result['top_n']} nodes by raw PageRank:")
    for entry in result["top_nodes"]:
        flag = "PHANTOM" if entry["is_phantom"] else "real"
        print(f"  {entry['raw_pagerank']:.6f}  [{flag}]  {entry['node']}")
    print()
    print(
        f"Top-{result['top_n']} phantom fraction: {result['top_phantom_fraction']:.2%}"
    )
    print(f"Max-PageRank node is phantom: {result['max_node_is_phantom']}")
    print(
        f"Real chunks clearing threshold={result['threshold']}: "
        f"{result['real_clearing_threshold']}/{result['real_node_count']} "
        f"({result['real_clearing_fraction']:.2%})"
    )
    print(f"[Workstream E] hypothesis_falsified: {result['hypothesis_falsified']}")

    if args.json:
        args.json.write_text(json.dumps(result, indent=2))
        print(f"\nWrote {args.json}")


if __name__ == "__main__":
    main()
