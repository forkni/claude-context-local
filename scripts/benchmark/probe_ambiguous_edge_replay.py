#!/usr/bin/env python
"""Offline replay screen: drop ``tag:ambiguous`` call edges from expansion.

A1' (``evaluation/UNTAGGED_EDGE_WITNESS_20260902.md``) found that the AST
resolver's ``confidence == "ambiguous"`` edges are 40% of all chunk-to-chunk
``calls`` edges and are witnessed 25x less often than ``tag:exact`` edges, yet
still feed traversal at confidence 0.5 (above the default
``min_traversal_confidence = 0.0``). This screen asks whether removing them
from the ego-graph and multi-hop neighbor sets would change *membership* for
any golden chunk on the 63q / 133q sets.

Method (read-only, deterministic, zero GPU):

    1. Load the on-disk call graph of the indexed self-project.
    2. Build a second storage whose graph has every ``tag:ambiguous`` edge
       removed (string tag ``ambiguous`` and no float ``resolver_confidence``;
       resolver-upgraded edges keep their float and are untouched).
    3. For every query in a captured ``probe_ego_membership.py`` artifact,
       re-run the production expansion on both graphs from the captured
       anchors:
         - ego: ``get_neighbors_ranked`` depth 2, weighted BFS, stdlib /
           builtin / third-party imports excluded, gate 1 ``is_chunk_id``,
           gate 2 ``[:max_neighbors_per_hop * k_hops]`` in traversal order
           (centrality was empty on the canon run, see D4 of the artifact);
         - multi-hop proxy: depth 1, weighted BFS, gate 1, skip nodes already
           in the anchor set, cap ``max(1, int(k * expansion_factor))`` per
           seed. The real multi-hop seeds and merged pool are not captured, so
           the ego anchors stand in for the seeds and the anchor set for the
           pool. Reported separately and labelled a proxy.
    4. Rescue = gold admitted only with ambiguous edges removed; eviction =
       gold admitted only with them present. Counted as distinct golds per
       dataset and per query.

Pre-registered screen (same bar as the graph-band and window-cap probes):
net rescues (rescues - evictions) >= 2 on EACH dataset, else the lever stays
closed. Replay stops at gate 2 (necessary, not sufficient).

    .venv/Scripts/python.exe -m scripts.benchmark.probe_ambiguous_edge_replay \\
        --project-name claude-context-local \\
        --probe-json evaluation/ego_membership_63q_20260901.json \\
        --probe-json evaluation/ego_membership_133q_20260901.json \\
        --json-out evaluation/ambiguous_edge_replay_20260902.json
"""

from __future__ import annotations

import argparse
import copy
import functools
import json
import sys
from collections import defaultdict
from pathlib import Path

from evaluation.index_locator import (
    AmbiguousIndexError,
    IndexNotFoundError,
    find_index,
    load_call_graph,
)
from evaluation.metrics import normalize_chunk_id
from evaluation.probe_harness import ensure_pinned_hash_seed, write_probe_json
from graph.graph_storage import DEFAULT_EDGE_WEIGHTS, CodeGraphStorage
from graph.schema import edge_relation_type, is_phantom_node
from search.graph_integration import is_chunk_id


EGO_K_HOPS = 2
EGO_MAX_NEIGHBORS_PER_HOP = 10
EGO_MAX_TOTAL = EGO_K_HOPS * EGO_MAX_NEIGHBORS_PER_HOP
EGO_EXCLUDE_CATEGORIES = ["stdlib", "builtin", "third_party"]
MULTI_HOP_K = 10
MULTI_HOP_EXPANSION_FACTOR = 0.5
MULTI_HOP_EXPANSION_K = max(1, int(MULTI_HOP_K * MULTI_HOP_EXPANSION_FACTOR))
NET_RESCUE_BAR = 2


def is_ambiguous_edge(edge_data: dict) -> bool:
    """``tag:ambiguous`` exactly as ``edge_confidence`` would bucket it."""
    if isinstance(edge_data.get("resolver_confidence"), (int, float)):
        return False
    return (
        edge_relation_type(edge_data) == "calls"
        and edge_data.get("confidence") == "ambiguous"
    )


def strip_ambiguous_edges(storage: CodeGraphStorage) -> tuple[CodeGraphStorage, int]:
    """Return a shallow-copied storage whose graph lacks every ambiguous edge."""
    filtered = copy.copy(storage)
    graph = storage.graph.copy()
    doomed = [
        (u, v, key)
        for u, v, key, data in graph.edges(keys=True, data=True)
        if is_ambiguous_edge(data)
    ]
    graph.remove_edges_from(doomed)
    filtered.graph = graph
    return filtered, len(doomed)


def ego_admitted(storage: CodeGraphStorage, anchor: str) -> list[str]:
    """Production ego gate sequence for one anchor (centrality empty)."""
    neighbors = storage.get_neighbors_ranked(
        anchor,
        relation_types=None,
        max_depth=EGO_K_HOPS,
        exclude_import_categories=EGO_EXCLUDE_CATEGORIES,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
        min_confidence=0.0,
        confidence_weighting=False,
    )
    valid = [n for n in neighbors if is_chunk_id(n)]
    return valid[:EGO_MAX_TOTAL]


def multi_hop_admitted(
    storage: CodeGraphStorage, seed: str, pool: set[str]
) -> list[str]:
    """Multi-hop graph-hop admission for one seed (proxy: pool = anchors)."""
    neighbors = storage.get_neighbors_ranked(
        seed,
        max_depth=1,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
        min_confidence=0.0,
        confidence_weighting=False,
    )
    admitted: list[str] = []
    for neighbor in neighbors:
        if not is_chunk_id(neighbor) or neighbor in pool:
            continue
        if len(admitted) >= MULTI_HOP_EXPANSION_K:
            break
        admitted.append(neighbor)
    return admitted


def build_reverse_map(storage: CodeGraphStorage) -> dict[str, list[str]]:
    """normalized id -> raw node ids, for every non-phantom node.

    Anchors include ``module_preamble`` / ``module`` chunks whose ids have
    fewer colons than ``is_chunk_id`` demands, so the map is keyed on every
    node that is not a bare symbol (phantom) node.
    """
    reverse: dict[str, list[str]] = defaultdict(list)
    for node, data in storage.graph.nodes(data=True):
        if not is_phantom_node(data):
            reverse[normalize_chunk_id(node)].append(node)
    return {k: sorted(v) for k, v in reverse.items()}


def ego_reachable(storage: CodeGraphStorage, anchor: str) -> set[str]:
    """Depth-2 reachable chunk set before gate 2 (normalized ids)."""
    neighbors = storage.get_neighbors_ranked(
        anchor,
        relation_types=None,
        max_depth=EGO_K_HOPS,
        exclude_import_categories=EGO_EXCLUDE_CATEGORIES,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
        min_confidence=0.0,
        confidence_weighting=False,
    )
    return {normalize_chunk_id(n) for n in neighbors if is_chunk_id(n)}


def cut_fidelity(
    payload: dict,
    base: CodeGraphStorage,
    treated: CodeGraphStorage,
    reverse: dict[str, list[str]],
) -> dict:
    """How the captured gate-2 cut relates to today's graph, per distinct anchor.

    Gate 2 truncates in weighted-BFS order whose tie-break is edge insertion
    order, so the cut is a different realisation on every reindex even when
    the reachable set is unchanged. Three numbers make that visible:
    captured-cut members still reachable today (drift of the reachable set),
    captured-cut members reachable today without ambiguous edges (how much of
    the canon-era cut the lever would have removed), and today's base-cut
    members reachable without ambiguous edges (the same share on the replay
    substrate).
    """
    table: list[str] = payload["chunk_id_table"]
    seen: set[str] = set()
    cap_n = cap_base = cap_treated = 0
    cut_n = cut_kept = 0
    jaccards: list[float] = []
    for rec in payload["per_query"]:
        et = rec.get("ego_traversal")
        if not et:
            continue
        for key, interned in et["post_gate2"].items():
            norm = normalize_chunk_id(table[int(key)])
            raw_ids = reverse.get(norm)
            if not raw_ids or norm in seen or not interned:
                continue
            seen.add(norm)
            captured = {normalize_chunk_id(table[i]) for i in interned}
            reach_base = ego_reachable(base, raw_ids[0])
            reach_treated = ego_reachable(treated, raw_ids[0])
            cap_n += len(captured)
            cap_base += len(captured & reach_base)
            cap_treated += len(captured & reach_treated)
            cut = {normalize_chunk_id(n) for n in ego_admitted(base, raw_ids[0])}
            cut_n += len(cut)
            cut_kept += len(cut & reach_treated)
            jaccards.append(len(cut & captured) / len(cut | captured))
    jaccards.sort()
    return {
        "distinct_anchors": len(seen),
        "captured_cut_members": cap_n,
        "captured_cut_reachable_today": cap_base / cap_n if cap_n else None,
        "captured_cut_reachable_without_ambiguous": (
            cap_treated / cap_n if cap_n else None
        ),
        "today_base_cut_reachable_without_ambiguous": (
            cut_kept / cut_n if cut_n else None
        ),
        "per_anchor_cut_jaccard_median": (
            jaccards[len(jaccards) // 2] if jaccards else None
        ),
    }


def _multi_hop_with_pool(
    storage: CodeGraphStorage, seed: str, pool: set[str]
) -> list[str]:
    return multi_hop_admitted(storage, seed, pool)


def _admitted_union(
    storage: CodeGraphStorage,
    anchors_raw: list[str],
    anchor_norm_set: set[str],
    admit,
) -> set[str]:
    """Normalized union of ``admit(storage, anchor)`` over anchors, minus anchors."""
    out: set[str] = set()
    for anchor in anchors_raw:
        out.update(normalize_chunk_id(n) for n in admit(storage, anchor))
    return out - anchor_norm_set


def _summary(rescued: set[str], evicted: set[str]) -> dict:
    net = len(rescued) - len(evicted)
    return {
        "rescued": sorted(rescued),
        "evicted": sorted(evicted),
        "rescued_count": len(rescued),
        "evicted_count": len(evicted),
        "net": net,
        "passes_bar": net >= NET_RESCUE_BAR,
    }


def replay_dataset(
    payload: dict,
    base: CodeGraphStorage,
    treated: CodeGraphStorage,
    reverse: dict[str, list[str]],
) -> dict:
    table: list[str] = payload["chunk_id_table"]
    per_query: list[dict] = []
    ego_rescued: set[str] = set()
    ego_evicted: set[str] = set()
    mh_rescued: set[str] = set()
    mh_evicted: set[str] = set()
    anchors_total = anchors_missing = anchors_split = 0
    overlap_num = overlap_den = 0

    for rec in payload["per_query"]:
        et = rec.get("ego_traversal")
        if not et:
            continue
        golds = {g["gold"] for g in rec.get("golds", []) if g.get("grade", 0) > 0}
        anchors_norm = [normalize_chunk_id(table[int(i)]) for i in et["raw_traversal"]]
        anchors_raw: list[str] = []
        for norm in anchors_norm:
            anchors_total += 1
            raw_ids = reverse.get(norm)
            if not raw_ids:
                anchors_missing += 1
                continue
            if len(raw_ids) > 1:
                anchors_split += 1
            anchors_raw.append(raw_ids[0])
        anchor_pool = set(anchors_raw)
        anchor_norm_set = set(anchors_norm)

        ego_base = _admitted_union(base, anchors_raw, anchor_norm_set, ego_admitted)
        ego_treated = _admitted_union(
            treated, anchors_raw, anchor_norm_set, ego_admitted
        )
        mh_base = _admitted_union(
            base,
            anchors_raw,
            anchor_norm_set,
            functools.partial(_multi_hop_with_pool, pool=anchor_pool),
        )
        mh_treated = _admitted_union(
            treated,
            anchors_raw,
            anchor_norm_set,
            functools.partial(_multi_hop_with_pool, pool=anchor_pool),
        )

        captured: set[str] = set()
        for interned in et["post_gate2"].values():
            captured.update(normalize_chunk_id(table[i]) for i in interned)
        captured -= anchor_norm_set
        overlap_num += len(captured & ego_base)
        overlap_den += len(captured | ego_base)
        q_jaccard = (
            len(captured & ego_base) / len(captured | ego_base)
            if captured | ego_base
            else None
        )

        q_ego_rescue = sorted(golds & (ego_treated - ego_base))
        q_ego_evict = sorted(golds & (ego_base - ego_treated))
        q_mh_rescue = sorted(golds & (mh_treated - mh_base))
        q_mh_evict = sorted(golds & (mh_base - mh_treated))
        ego_rescued.update(q_ego_rescue)
        ego_evicted.update(q_ego_evict)
        mh_rescued.update(q_mh_rescue)
        mh_evicted.update(q_mh_evict)
        per_query.append(
            {
                "query_id": rec["query_id"],
                "anchors": len(anchors_raw),
                "captured_vs_replayed_ego_jaccard": q_jaccard,
                "ego_base_size": len(ego_base),
                "ego_treated_size": len(ego_treated),
                "ego_gold_hits_base": len(golds & ego_base),
                "ego_gold_hits_treated": len(golds & ego_treated),
                "ego_rescued": q_ego_rescue,
                "ego_evicted": q_ego_evict,
                "mh_base_size": len(mh_base),
                "mh_treated_size": len(mh_treated),
                "mh_rescued": q_mh_rescue,
                "mh_evicted": q_mh_evict,
            }
        )

    return {
        "dataset": payload.get("dataset"),
        "queries": len(per_query),
        "anchors": {
            "total": anchors_total,
            "missing_on_current_graph": anchors_missing,
            "split_ambiguous": anchors_split,
        },
        "ego_membership_changed_queries": sum(
            1 for q in per_query if q["ego_base_size"] != q["ego_treated_size"]
        ),
        "mh_membership_changed_queries": sum(
            1 for q in per_query if q["mh_base_size"] != q["mh_treated_size"]
        ),
        "captured_vs_replayed_ego_jaccard": (
            overlap_num / overlap_den if overlap_den else None
        ),
        "cut_fidelity": cut_fidelity(payload, base, treated, reverse),
        "ego": _summary(ego_rescued, ego_evicted),
        "multi_hop_proxy": _summary(mh_rescued, mh_evicted),
        "per_query": per_query,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--storage", default=None)
    parser.add_argument("--model-slug", default=None)
    parser.add_argument(
        "--probe-json", action="append", required=True, dest="probe_jsons"
    )
    parser.add_argument(
        "--json-out", default="evaluation/ambiguous_edge_replay_20260902.json"
    )
    args = parser.parse_args(argv)

    try:
        paths = find_index(
            args.project_name, storage=args.storage, model_slug=args.model_slug
        )
    except (IndexNotFoundError, AmbiguousIndexError) as exc:
        print(f"index lookup failed: {exc}", file=sys.stderr)
        return 1
    base = load_call_graph(paths)
    treated, removed = strip_ambiguous_edges(base)
    reverse = build_reverse_map(base)
    calls_edges = sum(
        1
        for _, v, d in base.graph.edges(data=True)
        if edge_relation_type(d) == "calls" and is_chunk_id(v)
    )

    report: dict = {
        "index": {
            "project_dir": str(paths.project_dir),
            "call_graph": str(paths.call_graph),
        },
        "graph": {
            "nodes": base.graph.number_of_nodes(),
            "edges": base.graph.number_of_edges(),
            "chunk_to_chunk_calls_edges": calls_edges,
            "ambiguous_edges_removed": removed,
            "treated_edges": treated.graph.number_of_edges(),
        },
        "config": {
            "ego_k_hops": EGO_K_HOPS,
            "ego_max_total": EGO_MAX_TOTAL,
            "multi_hop_expansion_k": MULTI_HOP_EXPANSION_K,
            "net_rescue_bar": NET_RESCUE_BAR,
        },
        "datasets": {},
    }
    for path_str in args.probe_jsons:
        path = Path(path_str)
        payload = json.loads(path.read_text(encoding="utf-8"))
        report["datasets"][path.name] = replay_dataset(payload, base, treated, reverse)

    print(
        f"graph: nodes={report['graph']['nodes']} edges={report['graph']['edges']} "
        f"chunk->chunk calls={calls_edges} ambiguous removed={removed}"
    )
    verdict_all = True
    for name, ds in report["datasets"].items():
        print(
            f"\n{name}: anchors={ds['anchors']} "
            f"ego-changed={ds['ego_membership_changed_queries']}/{ds['queries']} "
            f"mh-changed={ds['mh_membership_changed_queries']} "
            f"captured-vs-replayed jaccard={ds['captured_vs_replayed_ego_jaccard']:.3f}"
        )
        f = ds["cut_fidelity"]
        print(
            f"  cut fidelity: anchors={f['distinct_anchors']} "
            f"captured reachable today={f['captured_cut_reachable_today']:.3f} "
            f"without ambiguous={f['captured_cut_reachable_without_ambiguous']:.3f} "
            f"today base cut without ambiguous="
            f"{f['today_base_cut_reachable_without_ambiguous']:.3f} "
            f"per-anchor cut jaccard median={f['per_anchor_cut_jaccard_median']:.3f}"
        )
        for arm in ("ego", "multi_hop_proxy"):
            s = ds[arm]
            print(
                f"  {arm:<16} rescued={s['rescued_count']} evicted={s['evicted_count']} "
                f"net={s['net']} {'PASS' if s['passes_bar'] else 'fail'}"
            )
            for label in ("rescued", "evicted"):
                for gold in s[label]:
                    print(f"    {label}: {gold}")
        verdict_all &= ds["ego"]["passes_bar"]
    report["verdict"] = {
        "ego_passes_on_every_dataset": verdict_all,
        "rule": f"net rescues >= {NET_RESCUE_BAR} on each dataset (ego arm)",
    }
    print(
        f"\nverdict: ego net-rescue bar {'PASSED' if verdict_all else 'FAILED'} -> "
        f"{'carry to live A/B' if verdict_all else 'lever stays closed'}"
    )
    write_probe_json(args.json_out, report)
    return 0


if __name__ == "__main__":
    ensure_pinned_hash_seed()
    sys.exit(main())
