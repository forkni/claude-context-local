#!/usr/bin/env python
"""Read-only probe: does excluding ``contains`` edges from PageRank centrality
move any BM25-adaptive-boost outcome on a golden-relevant chunk?

Gates the ``contains``-centrality isolation A/B recorded as an open item after
the 2026-09-05b canon re-pin (``evaluation/CANON_20260905B_ADR0063_REBASELINE.md``,
Follow-up). Two channels were left entangled there:

1. centrality -- all class->method ``contains`` edges enter
   ``GraphQueryEngine._simple_digraph_view`` (no relation-type filter) and so
   PageRank, whose max-normalised scores feed ``CentralityRanker._apply_bm25_boost``
   (``boost = min(c * factor, cap)`` when ``c > threshold``);
2. pool composition -- the +74 new chunks competing in BM25/dense pools.

This probe computes PageRank on the persisted graph twice -- as deployed, and on
an edge-filtered view with every ``contains`` edge removed (the exact seam the
knob would use) -- max-normalises both, derives the per-chunk boost each would
produce, and intersects the chunks whose boost differs with (a) every gold id in
both golden datasets and (b) every id the 09-05b canon runs actually retrieved.

Pre-registered gate (see ``evaluation/CONTAINS_CENTRALITY_ISOLATION_20260906.md``):
zero golden-relevant / canon-retrieved boost changes -> channel provably inert
on this substrate, no A/B; otherwise build the knob and run the paired A/B with
the reported movers as the expected-movers list.

Read-only: never mutates or saves ``CodeGraphStorage``.

Usage (module form required -- ``scripts`` is not in the editable-install
package map, ADR-0040)::

    .venv/Scripts/python.exe -m scripts.benchmark.probe_contains_centrality
        --project-name claude-context-local
        [--canon evaluation/canon_63q_r1_20260905b.json ...]
        [--golden evaluation/golden_dataset.json ...]
        [--json tmp/contains_centrality_probe.json]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import networkx as nx

from chunking.relationships.relationship_types import RelationshipType
from evaluation.metrics import normalize_chunk_id
from graph.graph_queries import GraphQueryEngine
from graph.graph_storage import CodeGraphStorage
from graph.schema import EDGE_ATTR_TYPE
from graph.schema import is_phantom_node as is_phantom
from scripts.benchmark.graph_phantom_preflight import (
    DEFAULT_STORAGE_DIR,
    find_call_graph_dir,
    load_storage,
)
from search.config import GraphEnhancedConfig


CONTAINS = RelationshipType.CONTAINS.value

DEFAULT_CANONS = (
    Path("evaluation/canon_63q_r1_20260905b.json"),
    Path("evaluation/canon_133q_r1_20260905b.json"),
)
DEFAULT_GOLDENS = (
    Path("evaluation/golden_dataset.json"),
    Path("evaluation/golden_dataset_expanded.json"),
)


def _normalise(raw: dict[str, float]) -> dict[str, float]:
    """Mirror ``CentralityRanker.get_centrality_scores``' max-normalisation."""
    if not raw:
        return {}
    max_score = max(raw.values())
    if max_score <= 0:
        return dict.fromkeys(raw, 0.0)
    return {n: s / max_score for n, s in raw.items()}


def _boost(c: float, cfg: GraphEnhancedConfig) -> float:
    """Mirror ``CentralityRanker.rerank`` + ``_apply_bm25_boost`` exactly."""
    if c > cfg.centrality_boost_threshold:
        return min(c * cfg.centrality_boost_factor, cfg.centrality_boost_cap)
    return 0.0


def contains_free_view(graph: nx.MultiDiGraph):
    """Edge-filtered read-only view with every ``contains`` edge removed.

    Filters on the edge key (``CodeGraphStorage.add_relationship_edge`` sets
    ``key=relationship_type.value``) OR the ``EDGE_ATTR_TYPE`` attribute, so a
    persisted graph whose keys were renumbered on reload is still filtered.
    """

    def keep(u, v, k) -> bool:
        if k == CONTAINS:
            return False
        return graph[u][v][k].get(EDGE_ATTR_TYPE) != CONTAINS

    return nx.subgraph_view(graph, filter_edge=keep)


def pagerank_pair(storage: CodeGraphStorage) -> tuple[dict, dict, dict]:
    graph = storage.graph
    engine = GraphQueryEngine(storage)
    with_c = engine.compute_centrality(method="pagerank")
    view = contains_free_view(graph)
    without_c = nx.pagerank(nx.DiGraph(view))
    by_key = sum(1 for _, _, k in graph.edges(keys=True) if k == CONTAINS)
    by_attr = sum(
        1 for _, _, d in graph.edges(data=True) if d.get(EDGE_ATTR_TYPE) == CONTAINS
    )
    stats = {
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "contains_edges_by_key": by_key,
        "contains_edges_by_attr": by_attr,
        "view_edges": view.number_of_edges(),
        "simple_edges_with": nx.DiGraph(graph).number_of_edges(),
        "simple_edges_without": nx.DiGraph(view).number_of_edges(),
    }
    return with_c, without_c, stats


def load_relevant_ids(canons: list[Path], goldens: list[Path]) -> dict[str, set[str]]:
    """normalized chunk id -> set of query tags that reference it (gold or retrieved)."""
    relevant: dict[str, set[str]] = defaultdict(set)
    for path in goldens:
        data = json.loads(path.read_text(encoding="utf-8"))
        for q in data["queries"]:
            ids = set(q.get("expected", [])) | set(q.get("expected_primary", []))
            for gid in ids:
                relevant[normalize_chunk_id(gid)].add(f"{path.stem}:{q['id']}:gold")
    for path in canons:
        data = json.loads(path.read_text(encoding="utf-8"))
        for q in data["per_query"]:
            for rid in q.get("retrieved", []):
                relevant[normalize_chunk_id(rid)].add(
                    f"{path.stem}:{q['id']}:retrieved"
                )
    return relevant


def run_probe(
    storage: CodeGraphStorage,
    cfg: GraphEnhancedConfig,
    relevant: dict[str, set[str]],
    top_n: int,
) -> dict:
    graph = storage.graph
    with_raw, without_raw, stats = pagerank_pair(storage)
    with_n, without_n = _normalise(with_raw), _normalise(without_raw)
    max_with = max(with_raw, key=with_raw.get) if with_raw else None
    max_without = max(without_raw, key=without_raw.get) if without_raw else None

    real = [n for n in graph.nodes if not is_phantom(graph.nodes[n])]
    movers = []
    up = down = 0
    for n in real:
        bw = _boost(with_n.get(n, 0.0), cfg)
        bo = _boost(without_n.get(n, 0.0), cfg)
        if bw != bo:
            movers.append(
                {
                    "node": n,
                    "normalized": normalize_chunk_id(n),
                    "c_with": with_n.get(n, 0.0),
                    "c_without": without_n.get(n, 0.0),
                    "boost_with": bw,
                    "boost_without": bo,
                    "delta": bo - bw,
                }
            )
            if bo > bw:
                up += 1
            else:
                down += 1
    movers.sort(key=lambda m: abs(m["delta"]), reverse=True)

    golden_movers = [
        {**m, "queries": sorted(relevant[m["normalized"]])}
        for m in movers
        if m["normalized"] in relevant
    ]
    thr = cfg.centrality_boost_threshold
    clearing_with = sum(1 for n in real if with_n.get(n, 0.0) > thr)
    clearing_without = sum(1 for n in real if without_n.get(n, 0.0) > thr)

    return {
        **stats,
        "threshold": thr,
        "factor": cfg.centrality_boost_factor,
        "cap": cfg.centrality_boost_cap,
        "max_node_with": max_with,
        "max_node_with_is_phantom": bool(
            max_with and is_phantom(graph.nodes[max_with])
        ),
        "max_node_without": max_without,
        "max_node_without_is_phantom": bool(
            max_without and is_phantom(graph.nodes[max_without])
        ),
        "real_nodes": len(real),
        "real_clearing_with": clearing_with,
        "real_clearing_without": clearing_without,
        "boost_movers": len(movers),
        "boost_movers_up": up,
        "boost_movers_down": down,
        "relevant_ids": len(relevant),
        "golden_relevant_movers": len(golden_movers),
        "gate": "G-inert" if not golden_movers else "G-live",
        "top_movers": movers[:top_n],
        "golden_movers": golden_movers,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--storage-dir", type=Path, default=DEFAULT_STORAGE_DIR)
    parser.add_argument("--canon", type=Path, nargs="*", default=list(DEFAULT_CANONS))
    parser.add_argument("--golden", type=Path, nargs="*", default=list(DEFAULT_GOLDENS))
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    project_dir = find_call_graph_dir(args.storage_dir, args.project_name)
    storage = load_storage(project_dir)
    cfg = GraphEnhancedConfig()
    relevant = load_relevant_ids(args.canon, args.golden)
    result = run_probe(storage, cfg, relevant, args.top_n)

    print(f"Project dir: {project_dir}")
    print(
        f"Graph: {result['graph_nodes']} nodes / {result['graph_edges']} edges; "
        f"contains by key={result['contains_edges_by_key']} "
        f"by attr={result['contains_edges_by_attr']}; "
        f"view edges={result['view_edges']}"
    )
    print(
        f"Simple-DiGraph edges: with={result['simple_edges_with']} "
        f"without={result['simple_edges_without']}"
    )
    print(
        f"Max node with:    {result['max_node_with']} "
        f"(phantom={result['max_node_with_is_phantom']})"
    )
    print(
        f"Max node without: {result['max_node_without']} "
        f"(phantom={result['max_node_without_is_phantom']})"
    )
    print(
        f"Real chunks clearing threshold {result['threshold']}: "
        f"with={result['real_clearing_with']} "
        f"without={result['real_clearing_without']} of {result['real_nodes']}"
    )
    print(
        f"Boost movers: {result['boost_movers']} "
        f"(up={result['boost_movers_up']}, down={result['boost_movers_down']})"
    )
    print(f"\nTop {args.top_n} movers by |delta|:")
    for m in result["top_movers"]:
        print(
            f"  {m['delta']:+.4f}  c {m['c_with']:.4f}->{m['c_without']:.4f}  "
            f"{m['node']}"
        )
    print(
        "\nGolden-relevant ids (gold + canon-retrieved, normalized): "
        f"{result['relevant_ids']}"
    )
    print(f"Golden-relevant movers: {result['golden_relevant_movers']}")
    for m in result["golden_movers"]:
        print(
            f"  {m['delta']:+.4f}  boost {m['boost_with']:.4f}->"
            f"{m['boost_without']:.4f}  {m['node']}"
        )
        for q in m["queries"]:
            print(f"      {q}")
    print(f"\nGATE: {result['gate']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")


if __name__ == "__main__":
    main()
