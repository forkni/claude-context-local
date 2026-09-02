#!/usr/bin/env python
"""A0 -- ego-membership headroom probe (read-only, measurement only).

Implements `docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md`'s
approved A0 scope (see `evaluation/EGO_MEMBERSHIP_PROBE_20260901.md` for the
disposition once run). Classifies every graded gold in a golden dataset into
exactly one of the five ego-graph-expansion gates it survives or is cut by:

    (c)  unreachable       -- absent from the raw 2-hop traversal closure
    (b1) symbol-filtered   -- dropped by the `is_chunk_id` gate
    (b2) gate-2 truncated  -- dropped by `retrieve_ego_graph`'s `[:max_total]`
    (b3) similarity-cut    -- dropped by `score_neighbors`'s min-similarity gate
    (b4) max_ego-cut       -- dropped by `_apply_ego_graph_expansion`'s cap
    (a)  survivor           -- present in the post-cap ego set (anchor or neighbor)

`bucket (b) := b1 | b2 | b3 | b4`. The pre-registered gate for building
Phase 2 (see the plan) is: bucket (b) has >= 2 distinct golds on EACH of the
63q and 133q sets, AND the confidence histogram (D1) shows >= 10% of
traversed edges below 0.65.

Queries are routed through `SearchOrchestrator.run()` (not
`HybridSearcher.search()` directly) so the gate-2 truncation-event count is
directly comparable to `evaluation/CANON_20260901_REBASELINE.md`'s
`truncation_events` (422 on 63q, 902 on 133q) and so D4's centrality-
injection check exercises the real production path, not a shortcut around it.
The five class-level patches below fire regardless of which `HybridSearcher`
instance the orchestrator uses internally, since `get_searcher()` caches one
instance per project path -- see `Instrumentation`'s docstring.

No config-file writes, no production edits. The one in-memory mutation is
`get_search_config().intent.enabled = False`, re-asserted before every query to
mirror the canon's `pin_intent_off=True` methodology (see `_run_queries`); it
lives in this process only and is never saved.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field

from evaluation import probe_harness
from evaluation.metrics import normalize_chunk_id
from graph.traversal_policy import TraversalPolicy


CONFIDENCE_FLOOR = 0.65

BUCKET_ANCHOR = "a_survivor_anchor"
BUCKET_SURVIVOR = "a_survivor_neighbor"
BUCKET_UNREACHABLE = "c_unreachable"
BUCKET_SYMBOL_FILTERED = "b1_symbol_filtered"
BUCKET_GATE2_TRUNCATED = "b2_gate2_truncated"
BUCKET_SIMILARITY_CUT = "b3_similarity_cut"
BUCKET_MAX_EGO_CUT = "b4_max_ego_cut"
BUCKET_NO_EXPANSION = "ego_not_applied"

BUCKET_B = frozenset(
    {
        BUCKET_SYMBOL_FILTERED,
        BUCKET_GATE2_TRUNCATED,
        BUCKET_SIMILARITY_CUT,
        BUCKET_MAX_EGO_CUT,
    }
)


# ---------------------------------------------------------------------------
# D1 -- confidence-source classification
# ---------------------------------------------------------------------------


def _classify_confidence_source(
    edge_data: dict, edge_type: str
) -> tuple[str, float | None]:
    """Mirror `graph.graph_storage.edge_confidence`'s resolution order, but
    keep the *path* that produced the number (float resolver_confidence vs.
    string tag vs. untagged-calls-fallback vs. float-tag-fallthrough), not
    just the number -- that is what D1's histogram shape needs.
    """
    from graph.graph_storage import AST_CONFIDENCE_BY_TAG

    resolver_confidence = edge_data.get("resolver_confidence")
    if isinstance(resolver_confidence, (int, float)):
        return "resolver_confidence", float(resolver_confidence)
    tag = edge_data.get("confidence")
    if isinstance(tag, str) and tag in AST_CONFIDENCE_BY_TAG:
        return f"tag:{tag}", AST_CONFIDENCE_BY_TAG[tag]
    if edge_type == "calls":
        if isinstance(tag, (int, float)):
            return "untagged_calls_float_fallthrough", 0.5
        return "untagged_calls", 0.5
    return "unresolved", None


# ---------------------------------------------------------------------------
# Per-query capture + class-level patch-and-restore layer
# ---------------------------------------------------------------------------


@dataclass
class QueryCapture:
    anchors: list[str] = field(default_factory=list)
    raw_traversal: dict[str, list[str]] = field(default_factory=dict)
    edge_records: list[tuple[str, str, str, float | None]] = field(default_factory=list)
    # Per-anchor best (max-confidence) resolution label + confidence seen for
    # each RAW neighbor id encountered while building that anchor's
    # raw_traversal entry -- Phase 2 Step 1: the offline gate-2 replay's R3
    # (confidence-sort) / R4 (confidence hard-filter) arms need a confidence
    # value tied to neighbor identity, which A0 captured (edge_records) but
    # never associated with a neighbor id. "Best" mirrors this repo's
    # resolver confidence-precedence merge convention (run_resolvers()):
    # a neighbor survives on its strongest evidence, not its weakest.
    neighbor_confidence: dict[str, dict[str, tuple[str, float | None]]] = field(
        default_factory=dict
    )
    post_gate2: dict[str, list[str]] = field(default_factory=dict)
    pre_gate3_ids: list[str] = field(default_factory=list)
    post_gate3_ids: list[str] = field(default_factory=list)
    post_gate4_ids: list[str] = field(default_factory=list)
    expansion_called: bool = False


class Instrumentation:
    """Class-level patch-and-restore layer over the five ego-membership gate
    call sites, following this repo's blessed pattern
    (`scripts/benchmark/probe_duplicate_crowding.py`'s `Instrumentation`):
    save originals, patch the class, restore in `uninstall()`. Records
    chunk-id strings only -- never live `SearchResult` objects, since
    `_apply_ego_graph_expansion` and the reranker both mutate `.score` in
    place.

    All five targets are patched at the *class* level, so it does not matter
    whether a query is dispatched via `HybridSearcher.search()` directly or
    via `SearchOrchestrator.run()` routing into a (possibly different, but
    same-class) `HybridSearcher` instance -- the patches fire either way.

    Recording is scoped to the `retrieve_ego_graph` call window via the
    `_recording_ego` flag, because `CodeGraphStorage.get_neighbors_ranked`
    and `_iter_matching_neighbors` are *also* called from
    `search/multi_hop_searcher.py` for the earlier, unrelated multi-hop leg
    that runs before ego-graph expansion in the same `search()` call --
    without the flag, that traversal would contaminate the ego-membership
    raw-traversal union.
    """

    def __init__(self) -> None:
        from graph.graph_storage import CodeGraphStorage
        from search.ego_graph_retriever import EgoGraphRetriever
        from search.hybrid_searcher import HybridSearcher

        self._storage_cls = CodeGraphStorage
        self._ego_cls = EgoGraphRetriever
        self._searcher_cls = HybridSearcher
        self._orig_get_neighbors_ranked = CodeGraphStorage.get_neighbors_ranked
        self._orig_iter_matching = CodeGraphStorage._iter_matching_neighbors
        self._orig_retrieve_ego = EgoGraphRetriever.retrieve_ego_graph
        self._orig_score_neighbors = EgoGraphRetriever.score_neighbors
        self._orig_apply_expansion = HybridSearcher._apply_ego_graph_expansion
        self._recording_ego = False
        self.current: QueryCapture | None = None
        # Anchors whose retrieve_ego_graph entry never lands in the returned
        # dict -- signature of the per-anchor `except Exception` at
        # ego_graph_retriever.py:150-152 swallowing something. Logged, not
        # silently folded into a gate bucket.
        self.anchor_exception_count = 0
        # Scratch accumulator for the single in-flight get_neighbors_ranked()
        # call (one per anchor -- retrieve_ego_graph never calls it
        # recursively; deeper hops stay inside orig_get_neighbors_ranked via
        # direct _iter_matching_neighbors calls). Reset around each call so
        # confidence stays tied to the anchor that produced it.
        self._scratch_neighbor_confidence: (
            dict[str, tuple[str, float | None]] | None
        ) = None

    def start_query(self) -> QueryCapture:
        self.current = QueryCapture()
        return self.current

    def install(self) -> None:
        instrumentation = self
        orig_get_neighbors_ranked = self._orig_get_neighbors_ranked
        orig_iter_matching = self._orig_iter_matching
        orig_retrieve_ego = self._orig_retrieve_ego
        orig_score_neighbors = self._orig_score_neighbors
        orig_apply_expansion = self._orig_apply_expansion

        def patched_get_neighbors_ranked(self_storage, chunk_id, *args, **kwargs):
            cap = instrumentation.current
            recording = cap is not None and instrumentation._recording_ego
            if recording:
                instrumentation._scratch_neighbor_confidence = {}
            out = orig_get_neighbors_ranked(self_storage, chunk_id, *args, **kwargs)
            if recording:
                # Store RAW (unnormalized) neighbor ids -- `is_chunk_id` is a
                # colon-count heuristic (MIN_CHUNK_ID_COLONS=3) and
                # `normalize_chunk_id`'s dedup_key strips the line-range
                # segment, dropping a colon. Normalizing here would make
                # every reachable neighbor spuriously fail gate 1 in
                # `classify_gold`. Dict keys (anchors) stay normalized for
                # consistent lookup; only the list *values* stay raw.
                cap.raw_traversal[normalize_chunk_id(chunk_id)] = list(out)
                cap.neighbor_confidence[normalize_chunk_id(chunk_id)] = (
                    instrumentation._scratch_neighbor_confidence
                )
                instrumentation._scratch_neighbor_confidence = None
            return out

        def patched_iter_matching_neighbors(
            self_storage, current_id, relation_types, exclude_import_categories
        ):
            cap = instrumentation.current
            recording = instrumentation._recording_ego
            for neighbor_id, edge_type, edge_data in orig_iter_matching(
                self_storage, current_id, relation_types, exclude_import_categories
            ):
                if cap is not None and recording:
                    label, conf = _classify_confidence_source(edge_data, edge_type)
                    cap.edge_records.append((neighbor_id, edge_type, label, conf))
                    scratch = instrumentation._scratch_neighbor_confidence
                    if scratch is not None:
                        prior = scratch.get(neighbor_id)
                        if prior is None or (conf or 0.0) > (prior[1] or 0.0):
                            scratch[neighbor_id] = (label, conf)
                yield neighbor_id, edge_type, edge_data

        def patched_retrieve_ego_graph(
            self_ego, anchor_chunk_ids, config, *args, **kwargs
        ):
            instrumentation._recording_ego = True
            try:
                out = orig_retrieve_ego(
                    self_ego, anchor_chunk_ids, config, *args, **kwargs
                )
            finally:
                instrumentation._recording_ego = False
            cap = instrumentation.current
            if cap is not None:
                # Keys normalized (anchor identity for lookup); values stay
                # RAW -- same rationale as patched_get_neighbors_ranked above.
                # Gate 1 (is_chunk_id) has already run by this point inside
                # `retrieve_ego_graph`, so these are always chunk-id-shaped,
                # but classify_gold still needs the raw form to test gate 1
                # membership on golds that were dropped by it.
                post_gate2_raw = {
                    normalize_chunk_id(a): list(vs) for a, vs in out.items()
                }
                cap.post_gate2 = post_gate2_raw
                expected = {normalize_chunk_id(a) for a in anchor_chunk_ids}
                instrumentation.anchor_exception_count += len(
                    expected - set(post_gate2_raw)
                )
            return out

        def patched_score_neighbors(
            self_ego,
            results,
            ego_graphs,
            expanded_chunk_ids,
            query,
            ego_config,
            **kwargs,
        ):
            cap = instrumentation.current
            if cap is not None:
                original_ids = {r.chunk_id for r in results}
                cap.pre_gate3_ids = [
                    normalize_chunk_id(c)
                    for c in expanded_chunk_ids
                    if c not in original_ids
                ]
            out = orig_score_neighbors(
                self_ego,
                results,
                ego_graphs,
                expanded_chunk_ids,
                query,
                ego_config,
                **kwargs,
            )
            if cap is not None:
                cap.post_gate3_ids = [normalize_chunk_id(r.chunk_id) for r in out]
            return out

        def patched_apply_ego_graph_expansion(
            self_searcher, results, ego_config, original_k, query, *args, **kwargs
        ):
            cap = instrumentation.current
            if cap is not None:
                cap.expansion_called = True
                cap.anchors = [normalize_chunk_id(r.chunk_id) for r in results]
            out = orig_apply_expansion(
                self_searcher, results, ego_config, original_k, query, *args, **kwargs
            )
            if cap is not None:
                cap.post_gate4_ids = [
                    normalize_chunk_id(r.chunk_id) for r in out[len(results) :]
                ]
            return out

        self._storage_cls.get_neighbors_ranked = patched_get_neighbors_ranked
        self._storage_cls._iter_matching_neighbors = patched_iter_matching_neighbors
        self._ego_cls.retrieve_ego_graph = patched_retrieve_ego_graph
        self._ego_cls.score_neighbors = patched_score_neighbors
        self._searcher_cls._apply_ego_graph_expansion = (
            patched_apply_ego_graph_expansion
        )

    def uninstall(self) -> None:
        self._storage_cls.get_neighbors_ranked = self._orig_get_neighbors_ranked
        self._storage_cls._iter_matching_neighbors = self._orig_iter_matching
        self._ego_cls.retrieve_ego_graph = self._orig_retrieve_ego
        self._ego_cls.score_neighbors = self._orig_score_neighbors
        self._searcher_cls._apply_ego_graph_expansion = self._orig_apply_expansion


class _GateTwoLogHandler(logging.Handler):
    """Free cross-check: reproduces `_EgoConfoundRecorder`'s technique
    (`scripts/benchmark/run_sscg_benchmark.py:491-532`) -- scrape the
    `"Limiting N neighbors to M for <anchor>"` DEBUG record off the
    `search.ego_graph_retriever` logger. This is gate 2 only (gate 4's
    "Capping ego-graph neighbors" is a different logger,
    `search.hybrid_searcher`, and is not in the canon's `truncation_events`).
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.count = 0

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
        except (TypeError, ValueError):
            return
        if "Limiting " in message:
            self.count += 1


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_gold(gold: str, cap: QueryCapture, is_chunk_id) -> str:
    """`gold` is always the normalize_chunk_id-normalized form (golden
    `grades` keys are pre-normalized at load). `is_chunk_id` must be tested
    against the RAW (unnormalized) traversal entries, not against `gold`
    itself -- `normalize_chunk_id`'s dedup_key strips the line-range segment,
    dropping a colon, so a normalized gold can fail the
    MIN_CHUNK_ID_COLONS=3 heuristic even when the raw graph node that
    produced it passed gate 1 cleanly. Testing is_chunk_id(gold) directly
    would misclassify every reachable neighbor gold as b1.
    """
    if not cap.expansion_called:
        return BUCKET_NO_EXPANSION
    if gold in cap.anchors:
        return BUCKET_ANCHOR

    raw_union_normalized: set[str] = set()
    passed_symbol_filter_normalized: set[str] = set()
    for neighbors in cap.raw_traversal.values():
        for n in neighbors:
            norm = normalize_chunk_id(n)
            raw_union_normalized.add(norm)
            if is_chunk_id(n):
                passed_symbol_filter_normalized.add(norm)
    if gold not in raw_union_normalized:
        return BUCKET_UNREACHABLE
    if gold not in passed_symbol_filter_normalized:
        return BUCKET_SYMBOL_FILTERED

    post_gate2_union: set[str] = set()
    for neighbors in cap.post_gate2.values():
        post_gate2_union.update(normalize_chunk_id(n) for n in neighbors)
    if gold not in post_gate2_union:
        return BUCKET_GATE2_TRUNCATED
    if gold not in set(cap.post_gate3_ids):
        return BUCKET_SIMILARITY_CUT
    if gold not in set(cap.post_gate4_ids):
        return BUCKET_MAX_EGO_CUT
    return BUCKET_SURVIVOR


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="A0 ego-membership headroom probe (read-only, measurement only).",
        parents=[probe_harness.probe_parser("ego-membership probe")],
    )


def _intern(
    chunk_id_table: list[str], chunk_id_index: dict[str, int], value: str
) -> int:
    """Intern `value` into the shared `chunk_id_table`, returning its index.

    Phase 2 Step 1: the raw per-anchor traversal/post-gate-2 lists needed for
    the offline replay (Step 2) are far smaller than A0's own D1 edge count
    (364,490 / 790,353 total traversed edges across the two datasets) would
    suggest -- they hold only each anchor's *own* neighbor set, not a running
    union -- but full-string repetition across ~130 queries still bloats the
    payload for no reason. Integer indices into one deduplicated table keep
    it lossless and small.
    """
    idx = chunk_id_index.get(value)
    if idx is None:
        idx = len(chunk_id_table)
        chunk_id_table.append(value)
        chunk_id_index[value] = idx
    return idx


async def _run_queries(
    orchestrator,
    session,
    calls: list[dict],
    items,
    instrumentation: Instrumentation,
    gate2_log_handler: _GateTwoLogHandler,
    args,
    is_chunk_id,
    default_edge_weights,
    chunk_id_table: list[str],
    chunk_id_index: dict[str, int],
) -> tuple[
    list[dict],
    list[tuple[str, str, str, float | None]],
    list[dict],
    list[dict],
    list[dict],
]:
    per_query_records: list[dict] = []
    all_edge_records: list[tuple[str, str, str, float | None]] = []
    anchor_neighbor_counts: list[dict] = []
    per_query_gate4: list[dict] = []
    d2_results: list[dict] = []

    from search.config import get_search_config

    for item in items:
        cap = instrumentation.start_query()
        calls_before = len(calls)
        arguments = {
            "query": item.query,
            "k": args.k,
            "search_mode": "hybrid",
            "include_context": True,
            "max_context_tokens": 0,
        }
        # Re-assert intent.enabled=False before every query, mirroring
        # run_sscg_benchmark.py::_run_query's pin_intent_off=True default
        # (the canon's own methodology). Without this, category-F queries
        # ("find X implementations similar to...") trigger SearchOrchestrator's
        # intent-based find_similar redirect, which runs a much lighter
        # ego-graph traversal than the pinned-off path the canon measures --
        # confirmed empirically: 9/63 queries diverged by exactly 49 gate-2
        # truncation events (422 canon vs 373 unpinned), all category F.
        get_search_config().intent.enabled = False
        try:
            await orchestrator.run(arguments)
        except Exception as exc:  # noqa: BLE001 - per-query resilience for a diagnostic probe
            print(f"[WARN] {item.id}: orchestrator.run failed: {exc}", file=sys.stderr)
            per_query_records.append(
                {"query_id": item.id, "category": item.category, "error": str(exc)}
            )
            continue
        calls_after = calls[calls_before:]

        max_total = (
            session.config.ego_graph.max_neighbors_per_hop
            * session.config.ego_graph.k_hops
        )
        max_ego = min(max_total, args.k * 3)

        for anchor in cap.anchors:
            raw = cap.raw_traversal.get(anchor, [])
            post_symbol = [n for n in raw if is_chunk_id(n)]
            post2 = cap.post_gate2.get(anchor, [])
            anchor_neighbor_counts.append(
                {
                    "query_id": item.id,
                    "anchor": anchor,
                    "pre_filter": len(raw),
                    "post_symbol_filter": len(post_symbol),
                    "post_gate2": len(post2),
                    "gate2_fired": len(post_symbol) > max_total,
                }
            )

        pre_gate4_count = len(cap.post_gate3_ids)
        per_query_gate4.append(
            {
                "query_id": item.id,
                "pre_gate4_count": pre_gate4_count,
                "max_ego": max_ego,
                "gate4_fired": pre_gate4_count > max_ego,
            }
        )

        all_edge_records.extend(cap.edge_records)

        gold_records = []
        for gold, grade in item.grades.items():
            bucket = classify_gold(gold, cap, is_chunk_id)
            gold_records.append({"gold": gold, "grade": grade, "bucket": bucket})
            if bucket == BUCKET_UNREACHABLE:
                widened_reachable = False
                for anchor in cap.anchors:
                    widened = (
                        session.searcher.ego_graph_retriever.graph.get_neighbors_ranked(
                            anchor,
                            TraversalPolicy(
                                relation_types=list(default_edge_weights.keys()),
                                max_depth=session.config.ego_graph.k_hops,
                            ),
                        )
                    )
                    if gold in {normalize_chunk_id(w) for w in widened}:
                        widened_reachable = True
                        break
                d2_results.append(
                    {
                        "query_id": item.id,
                        "gold": gold,
                        "reachable_widened": widened_reachable,
                    }
                )

        # Phase 2 Step 1: serialize the ordered pre-truncation and
        # post-gate-2 neighbor lists (already populated in-process above,
        # A0 never wrote them out) plus a per-neighbor confidence, all
        # chunk-id-interned for size. This is what the offline gate-2
        # replay (Step 2) simulates alternate truncation policies against.
        raw_traversal_interned: dict[str, list[int]] = {
            str(_intern(chunk_id_table, chunk_id_index, anchor)): [
                _intern(chunk_id_table, chunk_id_index, n) for n in neighbors
            ]
            for anchor, neighbors in cap.raw_traversal.items()
        }
        post_gate2_interned: dict[str, list[int]] = {
            str(_intern(chunk_id_table, chunk_id_index, anchor)): [
                _intern(chunk_id_table, chunk_id_index, n) for n in neighbors
            ]
            for anchor, neighbors in cap.post_gate2.items()
        }
        neighbor_confidence_interned: dict[str, dict[str, list]] = {
            str(_intern(chunk_id_table, chunk_id_index, anchor)): {
                str(_intern(chunk_id_table, chunk_id_index, neighbor)): [label, conf]
                for neighbor, (label, conf) in conf_map.items()
            }
            for anchor, conf_map in cap.neighbor_confidence.items()
        }

        per_query_records.append(
            {
                "query_id": item.id,
                "category": item.category,
                "expansion_called": cap.expansion_called,
                "anchor_count": len(cap.anchors),
                "gate2_log_events_cumulative": gate2_log_handler.count,
                "rerank_calls": len(calls_after),
                "golds": gold_records,
                "ego_traversal": {
                    "raw_traversal": raw_traversal_interned,
                    "post_gate2": post_gate2_interned,
                    "neighbor_confidence": neighbor_confidence_interned,
                },
            }
        )

    return (
        per_query_records,
        all_edge_records,
        anchor_neighbor_counts,
        per_query_gate4,
        d2_results,
    )


def main() -> int:
    args = build_parser().parse_args()
    dataset_path = probe_harness.resolve_dataset_path(args.dataset)
    items = probe_harness.load_golden_queries(dataset_path, args.query_ids)

    from graph.graph_storage import DEFAULT_EDGE_WEIGHTS
    from mcp_server.tools.search_orchestrator import SearchOrchestrator
    from search.graph_integration import is_chunk_id

    instrumentation = Instrumentation()
    gate2_log_handler = _GateTwoLogHandler()
    ego_logger = logging.getLogger("search.ego_graph_retriever")
    original_level = ego_logger.level
    ego_logger.setLevel(logging.DEBUG)
    ego_logger.addHandler(gate2_log_handler)

    orchestrator = SearchOrchestrator()
    chunk_id_table: list[str] = []
    chunk_id_index: dict[str, int] = {}

    try:
        with probe_harness.open_probe(args) as session, session.instrument() as calls:
            instrumentation.install()
            try:
                (
                    per_query_records,
                    all_edge_records,
                    anchor_neighbor_counts,
                    per_query_gate4,
                    d2_results,
                ) = asyncio.run(
                    _run_queries(
                        orchestrator,
                        session,
                        calls,
                        items,
                        instrumentation,
                        gate2_log_handler,
                        args,
                        is_chunk_id,
                        DEFAULT_EDGE_WEIGHTS,
                        chunk_id_table,
                        chunk_id_index,
                    )
                )
            finally:
                instrumentation.uninstall()

            centrality_scores_empty = not bool(
                session.searcher.ego_graph_retriever._centrality_scores
            )

            # One-shot GLOBAL centrality map for the Step 2 replay's R2 arm
            # (QW1 repaired: sort gate-2's raw traversal by centrality before
            # truncating). Constructed independently via GraphQueryEngine +
            # CentralityRanker, mirroring the production pattern in
            # graph_scoring_stage.py:_apply_centrality -- deliberately NOT
            # read from session.searcher.ego_graph_retriever._centrality_scores,
            # which D4 (above) proves stays empty all run: that is the
            # production defect QW1 names, and reading it here would just
            # serialize an empty map instead of measuring the repaired path.
            from graph.graph_queries import GraphQueryEngine
            from search.centrality_ranker import CentralityRanker

            session_centrality_method = session.config.graph_enhanced.centrality_method
            graph_query_engine = GraphQueryEngine(
                session.searcher.ego_graph_retriever.graph
            )
            centrality_ranker = CentralityRanker(
                graph_query_engine=graph_query_engine,
                method=session_centrality_method,
                alpha=session.config.graph_enhanced.centrality_alpha,
                config=session.config.graph_enhanced,
            )
            global_centrality_scores = centrality_ranker.get_centrality_scores()
            global_centrality_interned = {
                str(_intern(chunk_id_table, chunk_id_index, chunk_id)): score
                for chunk_id, score in global_centrality_scores.items()
            }

            # Captured here, while the session (and its config object) is
            # still live -- open_probe()'s __exit__ restores the global
            # SearchConfig snapshot, which may mutate the same object
            # in place rather than merely dropping a reference.
            eg = session.config.ego_graph
            ge = session.config.graph_enhanced
            d5_summary = {
                "ego_graph": {
                    "enabled": eg.enabled,
                    "expansion_mode": eg.expansion_mode,
                    "k_hops": eg.k_hops,
                    "max_neighbors_per_hop": eg.max_neighbors_per_hop,
                    "min_similarity_threshold": eg.min_similarity_threshold,
                    "deduplicate": eg.deduplicate,
                },
                "graph_enhanced": {
                    "min_traversal_confidence": ge.min_traversal_confidence,
                    "traversal_confidence_weighting_enabled": ge.traversal_confidence_weighting_enabled,
                    "centrality_annotation": ge.centrality_annotation,
                },
            }
    finally:
        ego_logger.removeHandler(gate2_log_handler)
        ego_logger.setLevel(original_level)

    # --- D1: confidence histogram -----------------------------------------
    # edge_records tuples are (neighbor_id, edge_type, resolution_label,
    # confidence) as of Phase 2 Step 1 -- neighbor_id is unused here (D1 is
    # an aggregate histogram) but retained by the other two unpack sites
    # below for the same reason it exists at all.
    confidences = [c for (_, _, _, c) in all_edge_records if c is not None]
    below_floor = [c for c in confidences if c < CONFIDENCE_FLOOR]
    d1_summary = {
        "total_edges_observed": len(all_edge_records),
        "with_resolved_confidence": len(confidences),
        "below_floor_count": len(below_floor),
        "below_floor_fraction": (len(below_floor) / len(confidences))
        if confidences
        else 0.0,
        "mean_gap_below_floor": (
            statistics.mean(CONFIDENCE_FLOOR - c for c in below_floor)
            if below_floor
            else 0.0
        ),
        "by_resolution_path": dict(
            Counter(label for (_, _, label, _) in all_edge_records)
        ),
    }

    # --- D2: widened relation_types reachability ---------------------------
    d2_summary = {
        "unreachable_golds_tested": len(d2_results),
        "newly_reachable_count": sum(1 for r in d2_results if r["reachable_widened"]),
    }

    # --- D3: per-anchor / per-query gate pressure ---------------------------
    gate2_fired_count = sum(1 for a in anchor_neighbor_counts if a["gate2_fired"])
    gate4_fired_count = sum(1 for q in per_query_gate4 if q["gate4_fired"])
    d3_summary = {
        "anchor_count": len(anchor_neighbor_counts),
        "gate2_fired_count": gate2_fired_count,
        "gate2_fired_fraction": (
            gate2_fired_count / len(anchor_neighbor_counts)
            if anchor_neighbor_counts
            else 0.0
        ),
        "query_count_with_gate4": len(per_query_gate4),
        "gate4_fired_count": gate4_fired_count,
        "gate4_fired_fraction": (
            gate4_fired_count / len(per_query_gate4) if per_query_gate4 else 0.0
        ),
    }

    # --- D4: centrality-injection defect ------------------------------------
    d4_note = {
        "centrality_scores_empty_after_run": centrality_scores_empty,
        "matches_canon_centrality_seeded_0": centrality_scores_empty,
        "note": (
            "Probe routes every query through SearchOrchestrator.run() (same "
            "path run_sscg_benchmark.py's canons use), so GraphScoringStage's "
            "_inject_ego_centrality is genuinely reachable here -- this is not "
            "a probe-bypasses-the-orchestrator artifact. _centrality_scores "
            "staying empty across the whole run (not just query 1) confirms "
            "the canon's centrality_seeded:0 is a real production defect, not "
            "a benchmark-harness quirk. See plan's D4 for prime-suspect list "
            "(swallowed except at graph_scoring_stage.py:138-139; "
            "index_manager/graph_storage falsy in the orchestrator's call "
            "context; searcher-identity mismatch). Diagnosed, not fixed here."
        ),
    }

    # --- Bucket aggregation ---------------------------------------------------
    bucket_counts: Counter[str] = Counter()
    b_distinct_golds: set[str] = set()
    for rec in per_query_records:
        for g in rec.get("golds", []):
            bucket_counts[g["bucket"]] += 1
            if g["bucket"] in BUCKET_B:
                b_distinct_golds.add(g["gold"])

    gate_component_pass = (
        len(b_distinct_golds) >= 2 and d1_summary["below_floor_fraction"] >= 0.10
    )

    payload = {
        "dataset": str(dataset_path),
        "k": args.k,
        "query_count": len(items),
        "bucket_counts": dict(bucket_counts),
        "bucket_b_distinct_gold_count": len(b_distinct_golds),
        "bucket_b_distinct_golds": sorted(b_distinct_golds),
        "gate2_log_event_count": gate2_log_handler.count,
        "anchor_exception_count": instrumentation.anchor_exception_count,
        "gate_component_pass_this_dataset": gate_component_pass,
        "d1_confidence_histogram": d1_summary,
        "d2_widened_reachability": d2_summary,
        "d2_detail": d2_results,
        "d3_gate_pressure": d3_summary,
        "d4_centrality_injection": d4_note,
        "d5_config_echo": d5_summary,
        # Phase 2 Step 1: shared interning table for every chunk-id index
        # referenced under per_query[*]["ego_traversal"] and in
        # global_centrality (below) -- lossless, decode via chunk_id_table[i].
        "chunk_id_table": chunk_id_table,
        "global_centrality": global_centrality_interned,
        "global_centrality_method": session_centrality_method,
        "per_query": per_query_records,
    }
    if args.json_out:
        probe_harness.write_probe_json(args.json_out, payload)

    print(f"Dataset: {dataset_path}  k={args.k}  queries={len(items)}")
    print(
        f"Gate-2 log events (cross-check vs canon truncation_events): {gate2_log_handler.count}"
    )
    print(
        f"Anchor exceptions (retrieve_ego_graph swallowed): {instrumentation.anchor_exception_count}"
    )
    print("Bucket counts:")
    for bucket in (
        BUCKET_ANCHOR,
        BUCKET_SURVIVOR,
        BUCKET_UNREACHABLE,
        BUCKET_SYMBOL_FILTERED,
        BUCKET_GATE2_TRUNCATED,
        BUCKET_SIMILARITY_CUT,
        BUCKET_MAX_EGO_CUT,
        BUCKET_NO_EXPANSION,
    ):
        print(f"  {bucket:24s} {bucket_counts.get(bucket, 0)}")
    print(
        f"Bucket (b) distinct golds: {len(b_distinct_golds)} -> {sorted(b_distinct_golds)}"
    )
    print(
        f"D1 below-{CONFIDENCE_FLOOR} fraction: {d1_summary['below_floor_fraction']:.3f} "
        f"({d1_summary['below_floor_count']}/{d1_summary['with_resolved_confidence']})"
    )
    print(
        f"D2 unreachable golds newly reachable under widened relation_types: "
        f"{d2_summary['newly_reachable_count']}/{d2_summary['unreachable_golds_tested']}"
    )
    print(
        f"D3 gate-2 fired on {d3_summary['gate2_fired_fraction']:.1%} of anchors, "
        f"gate-4 fired on {d3_summary['gate4_fired_fraction']:.1%} of queries"
    )
    print(f"D4 centrality_scores empty after run: {centrality_scores_empty}")
    print(f"Gate component pass (this dataset only): {gate_component_pass}")
    if args.json_out:
        print(f"Results saved to: {args.json_out}")
    return 0


if __name__ == "__main__":
    probe_harness.ensure_pinned_hash_seed()
    sys.exit(main())
