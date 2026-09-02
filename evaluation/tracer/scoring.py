"""Score each call-graph resolver tier against execution-witnessed edges.

Inputs: a ``traced-callgraph/1`` payload (:mod:`evaluation.tracer.build`) and
the persisted NetworkX call graph. Labels are positive-only: a static edge
absent from the trace is *unlabeled*, never false. Every metric below is
defined in :data:`DEFINITIONS`, which the calibration record quotes verbatim.

Tier = ``resolver_source`` on the edge, or ``"ast"`` when absent. Because
``run_resolvers`` overwrites lower tiers in place, a tier's stored edges are
its *marginal* contribution over the tiers above it, not its standalone
output.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from evaluation.metrics import normalize_chunk_id
from graph.schema import edge_relation_type, is_phantom_node


SCHEMA = "resolver-tier-scores/1"
LADDER: tuple[str, ...] = ("lsp", "libcst", "pyan", "ast")  # highest tier first
TAXONOMY: tuple[str, ...] = (
    "wrapper_routed",
    "class_body_eval",
    "via_external",
    "name_only_unresolved",
    "dynamic_dispatch",
    "no_syntactic_call",
    "unclassified",
)
MAX_EXAMPLES = 10

DEFINITIONS: dict[str, str] = {
    "D": (
        "traced edges that are direct (external_depth 0) with both endpoints "
        "resolved to non-phantom graph nodes; one shared denominator for all tiers"
    ),
    "I": "traced edges with external_depth > 0, both endpoints resolved; scored "
    "in a separate column and never added to D",
    "E_t": "static call edges whose resolver_source is t (ast when absent), both "
    "endpoints non-phantom, ids normalized; a tier's stored edges are its "
    "marginal contribution over the tiers above it",
    "recall_marginal(t)": "|E_t ∩ D| / |D|",
    "recall_cumulative(≥t)": "|(∪_{t' ≥ t} E_t') ∩ D| / |D| down the ladder "
    "lsp > libcst > pyan > ast",
    "recall_ladder_total": "|E_all ∩ D| / |D|",
    "recall_indirect(t)": "|E_t ∩ I| / |I|",
    "prec_lb(t)": "|E_t ∩ E_traced| / |E_t| where E_traced is every traced edge "
    "(direct and indirect)",
    "EXEC": "every chunk that owns at least one traced endpoint",
    "E_t_cov": "{e ∈ E_t : caller(e) ∈ EXEC}; caller-only restriction, since "
    "requiring the callee in EXEC would push the bound to 1 by construction",
    "prec_lb_cov(t)": "|E_t_cov ∩ E_traced| / |E_t_cov|",
    "unwitnessable(t)": "|E_t| − |E_t_cov|",
    "prec_est(t)": "(|E_t_cov ∩ E_traced| + p̂·|E_t_cov \\ E_traced|) / |E_t_cov| "
    "where p̂ is the hand-labeled true-positive rate of the unwitnessed sample",
    "init_equivalence": "a traced callee p.py:method:C.__init__ matches a static "
    "callee p.py:class:C and vice versa (both sides canonicalized to class:C); "
    "hits obtained this way are counted in hits_via_init_equivalence",
    "ast_name_only": "lenient column: a missed D edge counts as a name-only hit "
    "iff the graph has caller → phantom whose key equals the callee's bare "
    "name or Class.method; never added to any recall",
}

_INIT_RE = re.compile(r"^(?P<path>.+):method:(?P<cls>.+)\.__init__$")
_CLASS_RE = re.compile(r"^(?P<path>.+):class:(?P<cls>.+)$")

Edge = tuple[str, str]


def canonical_callee(chunk_id: str) -> tuple[str, bool]:
    """Map ``method:C.__init__`` to ``class:C``; return (canonical, rewritten)."""
    m = _INIT_RE.match(chunk_id)
    if m:
        return f"{m.group('path')}:class:{m.group('cls')}", True
    return chunk_id, False


def _simple_name(chunk_id: str) -> str:
    return chunk_id.rsplit(":", 1)[-1]


def _kind(chunk_id: str) -> str:
    parts = chunk_id.split(":")
    return parts[-2] if len(parts) >= 3 else ""


@dataclass
class StaticEdges:
    """Static call edges grouped by tier, ids normalized and canonicalized."""

    by_tier: dict[str, set[Edge]] = field(default_factory=dict)
    phantom: set[Edge] = field(default_factory=set)  # (caller, phantom key)
    nodes: set[str] = field(default_factory=set)  # normalized non-phantom ids
    raw_by_norm: dict[str, list[str]] = field(default_factory=dict)

    @property
    def all_edges(self) -> set[Edge]:
        out: set[Edge] = set()
        for edges in self.by_tier.values():
            out |= edges
        return out

    def tiers_of(self, edge: Edge) -> list[str]:
        return [t for t in LADDER if edge in self.by_tier.get(t, set())]


def extract_static_edges(graph: Any) -> StaticEdges:
    """Read ``calls`` edges off a NetworkX (Multi)DiGraph into :class:`StaticEdges`."""
    out = StaticEdges(by_tier={t: set() for t in LADDER})
    phantom_nodes: set[str] = set()
    for node, data in graph.nodes(data=True):
        if is_phantom_node(data):
            phantom_nodes.add(node)
            continue
        norm = normalize_chunk_id(node)
        out.nodes.add(norm)
        out.raw_by_norm.setdefault(norm, []).append(node)
    for raws in out.raw_by_norm.values():
        raws.sort()
    for u, v, data in graph.edges(data=True):
        if edge_relation_type(data) != "calls" or u in phantom_nodes:
            continue
        caller = normalize_chunk_id(u)
        if v in phantom_nodes:
            out.phantom.add((caller, v))
            continue
        callee, _ = canonical_callee(normalize_chunk_id(v))
        if caller == callee:
            continue  # split fragments of one function calling each other
        tier = data.get("resolver_source") or "ast"
        out.by_tier.setdefault(tier, set()).add((caller, callee))
    return out


@dataclass
class TracedEdges:
    direct: set[Edge]  # D
    indirect: set[Edge]  # I
    all_traced: set[Edge]  # every traced edge, resolved or not (canonicalized)
    executed: set[str]
    with_locals: set[str]
    rewritten: set[Edge]  # traced edges whose callee was canonicalized
    unresolved: int  # traced edges with an endpoint missing from the graph

    @property
    def resolved(self) -> set[Edge]:
        return self.direct | self.indirect


def load_traced_edges(payload: Mapping[str, Any], static: StaticEdges) -> TracedEdges:
    direct: set[Edge] = set()
    indirect: set[Edge] = set()
    all_traced: set[Edge] = set()
    rewritten: set[Edge] = set()
    unresolved = 0
    for e in payload["edges"]:
        callee, was_rewritten = canonical_callee(e["callee"])
        edge = (e["caller"], callee)
        all_traced.add(edge)
        if was_rewritten:
            rewritten.add(edge)
        resolved = e["caller"] in static.nodes and (
            callee in static.nodes or e["callee"] in static.nodes
        )
        if not resolved:
            unresolved += 1
            continue
        (direct if e["direct"] else indirect).add(edge)
    return TracedEdges(
        direct=direct,
        indirect=indirect,
        all_traced=all_traced,
        executed=set(payload["executed_chunks"]),
        with_locals=set(payload.get("executed_chunks_with_locals", [])),
        rewritten=rewritten,
        unresolved=unresolved,
    )


def _ratio(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def score_tiers(static: StaticEdges, traced: TracedEdges) -> dict[str, Any]:
    """Per-tier recall / precision-lower-bound table plus ladder totals."""
    d_set, i_set = traced.direct, traced.indirect
    witnessed = traced.all_traced
    tiers: dict[str, Any] = {}
    cumulative: set[Edge] = set()
    for tier in LADDER:
        edges = static.by_tier.get(tier, set())
        cumulative |= edges
        cov = {e for e in edges if e[0] in traced.executed}
        hits_d = edges & d_set
        tiers[tier] = {
            "edges": len(edges),
            "hits_D": len(hits_d),
            "recall_marginal": _ratio(len(hits_d), len(d_set)),
            "recall_cumulative": _ratio(len(cumulative & d_set), len(d_set)),
            "hits_I": len(edges & i_set),
            "recall_indirect": _ratio(len(edges & i_set), len(i_set)),
            "hits_traced": len(edges & witnessed),
            "prec_lb": _ratio(len(edges & witnessed), len(edges)),
            "edges_cov": len(cov),
            "hits_cov": len(cov & witnessed),
            "prec_lb_cov": _ratio(len(cov & witnessed), len(cov)),
            "unwitnessable": len(edges) - len(cov),
            "unlabeled_cov": len(cov - witnessed),
            "example_hits": sorted(hits_d)[:5],
        }
    all_edges = static.all_edges
    ladder_hits = all_edges & d_set
    misses = sorted(d_set - all_edges)
    name_only = {
        e
        for e in misses
        if any((e[0], key) in static.phantom for key in _name_only_keys(e[1]))
    }
    return {
        "denominators": {
            "D": len(d_set),
            "I": len(i_set),
            "E_traced": len(witnessed),
            "EXEC": len(traced.executed),
            "traced_unresolved": traced.unresolved,
        },
        "tiers": tiers,
        "ladder_total": {
            "edges": len(all_edges),
            "hits_D": len(ladder_hits),
            "recall_ladder_total": _ratio(len(ladder_hits), len(d_set)),
            "prec_lb": _ratio(len(all_edges & witnessed), len(all_edges)),
        },
        "hits_via_init_equivalence": len(ladder_hits & traced.rewritten),
        "ast_name_only": {"hits": len(name_only), "of_misses": len(misses)},
        "misses": misses,
    }


def _name_only_keys(callee: str) -> tuple[str, ...]:
    name = _simple_name(callee)
    keys = [name]
    if "." in name:
        keys.append(name.rsplit(".", 1)[-1])
    return tuple(keys)


# ---------------------------------------------------------------------------
# B5 taxonomy
# ---------------------------------------------------------------------------

SourceLookup = Callable[[str], "str | None"]


_METHOD_KINDS = frozenset({"method", "decorated_definition"})


def _method_name(chunk_id: str) -> str | None:
    """Bare method name for ``method``/decorated ``Class.name`` chunks, else None."""
    if _kind(chunk_id) not in _METHOD_KINDS:
        return None
    name = _simple_name(chunk_id)
    if "." not in name:
        return None
    return name.rsplit(".", 1)[-1]


def classify_miss(
    edge: Edge,
    static: StaticEdges,
    traced: TracedEdges,
    source_lookup: SourceLookup | None = None,
) -> tuple[str, dict[str, Any]]:
    """First-match taxonomy for a D edge no tier produced. Returns (class, detail)."""
    caller, callee = edge
    all_static = static.all_edges

    # wrapper_routed: caller -> W -> callee at runtime where W owns a <locals>
    # code object (decorator wrapper / closure) and static has caller -> callee.
    if callee in traced.with_locals:
        for w_callee in _outgoing(traced.resolved, callee):
            if (caller, w_callee) in all_static:
                return "wrapper_routed", {
                    "wrapper": callee,
                    "collapsed": (caller, w_callee),
                }
    if caller in traced.with_locals:
        for upstream in _incoming(traced.resolved, caller):
            if (upstream, callee) in all_static:
                return "wrapper_routed", {
                    "wrapper": caller,
                    "collapsed": (upstream, callee),
                }

    # class_body_eval: the call ran while the class body was being evaluated
    # (decorator application, default arguments, class-attribute instantiation);
    # static extractors never attribute those calls to the class chunk.
    if _kind(caller) == "class":
        return "class_body_eval", {"callee_kind": _kind(callee)}

    source = source_lookup(caller) if source_lookup else None
    name = _simple_name(callee).rsplit(".", 1)[-1]
    called = (
        bool(source) and re.search(rf"\b{re.escape(name)}\s*\(", source) is not None
    )
    referenced = (
        bool(source) and re.search(rf"\b{re.escape(name)}\b", source) is not None
    )

    if source is not None and referenced and not called:
        return "via_external", {"name": name, "heuristic": "referenced-not-called"}
    if any((caller, key) in static.phantom for key in _name_only_keys(callee)):
        return "name_only_unresolved", {"phantom": _name_only_keys(callee)}
    method = _method_name(callee)
    if method is not None:
        for c, k in all_static:
            if c == caller and k != callee and _method_name(k) == method:
                return "dynamic_dispatch", {"static_target": k}
    if source is not None and not referenced:
        return "no_syntactic_call", {"name": name, "heuristic": "name-absent"}
    return "unclassified", {"source_available": source is not None}


def _outgoing(edges: Iterable[Edge], node: str) -> list[str]:
    return sorted(k for c, k in edges if c == node)


def _incoming(edges: Iterable[Edge], node: str) -> list[str]:
    return sorted(c for c, k in edges if k == node)


def classify_misses(
    misses: Iterable[Edge],
    static: StaticEdges,
    traced: TracedEdges,
    source_lookup: SourceLookup | None = None,
) -> dict[str, Any]:
    items = []
    histogram: Counter[str] = Counter()
    collapsed: set[Edge] = set()
    examples: dict[str, list[str]] = {t: [] for t in TAXONOMY}
    for edge in sorted(misses):
        cls, detail = classify_miss(edge, static, traced, source_lookup)
        histogram[cls] += 1
        if cls == "wrapper_routed":
            collapsed.add(tuple(detail["collapsed"]))  # type: ignore[arg-type]
        if len(examples[cls]) < MAX_EXAMPLES:
            examples[cls].append(f"{edge[0]} -> {edge[1]}")
        items.append({"caller": edge[0], "callee": edge[1], "class": cls, **detail})
    return {
        "count": len(items),
        "taxonomy": {t: histogram.get(t, 0) for t in TAXONOMY},
        "wrapper_collapsed_credits": len(collapsed),
        "examples": examples,
        "items": items,
    }


def make_source_lookup(store: Any) -> SourceLookup:
    """Build a normalized-chunk-id → source-text lookup from a metadata store.

    ``store`` only needs ``.items()`` yielding ``(raw_chunk_id, entry)`` with
    ``entry["metadata"]`` carrying ``file_path``, ``start_line``, ``end_line``.
    Split fragments of one function are concatenated in line order; unreadable
    files yield ``None`` so callers fall through to the heuristic-free classes.
    """
    spans: dict[str, list[tuple[int, int, str]]] = {}
    for raw_id, entry in store.items():
        meta = entry.get("metadata", entry) if isinstance(entry, Mapping) else {}
        path = meta.get("file_path")
        start, end = meta.get("start_line"), meta.get("end_line")
        if not path or start is None or end is None:
            continue
        spans.setdefault(normalize_chunk_id(raw_id), []).append((start, end, path))
    file_cache: dict[str, list[str] | None] = {}

    def _lines(path: str) -> list[str] | None:
        if path not in file_cache:
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    file_cache[path] = fh.read().splitlines()
            except OSError:
                file_cache[path] = None
        return file_cache[path]

    def lookup(chunk_id: str) -> str | None:
        parts = []
        for start, end, path in sorted(spans.get(chunk_id, [])):
            lines = _lines(path)
            if lines is None:
                return None
            parts.append("\n".join(lines[max(start - 1, 0) : end]))
        return "\n".join(parts) if parts else None

    return lookup


# ---------------------------------------------------------------------------
# Precision sample + traced goldens
# ---------------------------------------------------------------------------


def emit_precision_sample(
    static: StaticEdges, traced: TracedEdges, size: int
) -> dict[str, Any]:
    """Deterministic, evenly-spaced sample of unwitnessed covered edges per tier."""
    per_tier = max(size // len(LADDER), 1)
    rows = []
    for tier in LADDER:
        pool = sorted(
            e
            for e in static.by_tier.get(tier, set())
            if e[0] in traced.executed and e not in traced.all_traced
        )
        if not pool:
            continue
        stride = max(len(pool) // per_tier, 1)
        for e in pool[::stride][:per_tier]:
            rows.append({"tier": tier, "caller": e[0], "callee": e[1], "label": None})
    return {
        "schema": "resolver-precision-sample/1",
        "instructions": "label each row true (the caller really can call the "
        "callee) or false; p̂ per tier feeds prec_est(t)",
        "rows": rows,
    }


def emit_traced_golden(
    golden: Mapping[str, Any],
    traced: TracedEdges,
    direction: str,
) -> dict[str, Any]:
    """Rewrite a caller/callee golden with traced positives for executed targets."""
    key = "expected_callees" if direction == "callees" else "expected_callers"
    queries = []
    skipped = []
    for q in golden.get("queries", []):
        target = normalize_chunk_id(q["target_chunk_id"])
        if target not in traced.executed:
            skipped.append({"id": q["id"], "reason": "target not executed"})
            continue
        if direction == "callees":
            expected = _outgoing(traced.direct, target)
        else:
            expected = _incoming(traced.direct, target)
        if not expected:
            skipped.append({"id": q["id"], "reason": "no traced direct edges"})
            continue
        queries.append(
            {
                "id": f"T{q['id']}",
                "category": "T",
                "description": f"traced {direction} of {target}",
                "target_chunk_id": target,
                key: expected,
            }
        )
    return {
        "_meta": {
            "description": f"Execution-witnessed direct {direction}",
            "semantics": "positive-only; missing != absent",
            "categories": {"T": "traced under tests/unit with the callgraph plugin"},
            "normalization": "evaluation/metrics.py:normalize_chunk_id; "
            "method:C.__init__ callees appear as class:C",
            "total_queries": len(queries),
            "skipped": skipped,
        },
        "queries": queries,
    }


# ---------------------------------------------------------------------------
# Entry point used by the CLI
# ---------------------------------------------------------------------------


def score_traced(
    payload: Mapping[str, Any],
    graph: Any,
    *,
    source_lookup: SourceLookup | None = None,
    sample_size: int = 40,
    goldens: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Full scoring pass; ``goldens`` maps ``callers``/``callees`` to golden dicts."""
    static = extract_static_edges(graph)
    traced = load_traced_edges(payload, static)
    scores = score_tiers(static, traced)
    misses = classify_misses(scores.pop("misses"), static, traced, source_lookup)
    report = {
        "schema": SCHEMA,
        "definitions": DEFINITIONS,
        "ladder": list(LADDER),
        "traced_integrity": dict(payload.get("integrity", {})),
        **scores,
        "misses": misses,
        "blind_spots": [
            "tests/ is not indexed: test-to-project calls are recorded only in "
            "test_edges and never scored",
            "dataclass-generated __init__ has co_filename '<string>' and is "
            "external: instantiation of such classes is unwitnessed",
            "threads started before the profiler installed are untraceable on "
            "Python 3.11",
            "C-implemented callables create no Python frame: a callback passed "
            "to sorted()/map() shows as a direct edge from the caller",
        ],
    }
    out: dict[str, Any] = {
        "report": report,
        "sample": emit_precision_sample(static, traced, sample_size),
        "traced_goldens": {},
    }
    for direction, golden in (goldens or {}).items():
        out["traced_goldens"][f"{direction[:-1]}_golden_traced.json"] = (
            emit_traced_golden(golden, traced, direction)
        )
    return out


# ---------------------------------------------------------------------------
# A1': confidence-bucket witness (are untagged ``calls`` edges real?)
# ---------------------------------------------------------------------------

BUCKET_SCHEMA = "confidence-bucket-witness/1"
UNTAGGED = "untagged"
BUCKET_DEFINITIONS: dict[str, str] = {
    "bucket": (
        "how graph.graph_storage.edge_confidence would resolve the edge: "
        "resolver:<source> when a float resolver_confidence is present; "
        "tag:<exact|ambiguous|recovered> when only the legacy string tag is; "
        "untagged when neither (the 0.5 fallback under test)"
    ),
    "phantom": (
        "edges whose callee is a bare symbol node (graph.schema.is_phantom_node); "
        "counted per bucket but never in any denominator"
    ),
    "same_file": "caller and callee share the file-path prefix of their chunk ids",
    "is_resolved": "the EDGE_ATTR_IS_RESOLVED flag written by add_call_edge",
    "callee_kind": "chunk kind of the callee after canonical_callee (class for __init__)",
    "metrics": (
        "edges/edges_cov/hits_traced/prec_lb/prec_lb_cov/hits_D/recall_marginal/"
        "unwitnessable exactly as in score_tiers; edge_share = edges / all "
        "non-phantom calls edges"
    ),
    "verdict": (
        "vacuous when the untagged bucket has no coverable non-phantom edge; "
        "otherwise untagged is as_reliable_as_ast iff prec_lb_cov(untagged) >= 0.8 * "
        "prec_lb_cov(tag:exact) and no secondary sub-bucket with edges_cov >= 100 "
        "has prec_lb_cov below half of prec_lb_cov(untagged); otherwise the worst "
        "such sub-bucket is the tagging target"
    ),
}
VERDICT_RATIO = 0.8
SUBBUCKET_MIN_COV = 100
SUBBUCKET_HALF = 0.5


def confidence_bucket(edge_data: Mapping[str, Any]) -> str:
    """Name the path :func:`graph.graph_storage.edge_confidence` would take.

    Same resolution order as that function and as
    ``scripts/benchmark/probe_ego_membership.py:_classify_confidence_source``
    (A0's D1 histogram), so the two records name the same buckets.
    """
    from graph.graph_storage import AST_CONFIDENCE_BY_TAG

    rc = edge_data.get("resolver_confidence")
    if isinstance(rc, (int, float)) and not isinstance(rc, bool):
        return f"resolver:{edge_data.get('resolver_source') or 'unknown'}"
    tag = edge_data.get("confidence")
    if isinstance(tag, str) and tag in AST_CONFIDENCE_BY_TAG:
        return f"tag:{tag}"
    return UNTAGGED


@dataclass
class BucketedEdges:
    """Static ``calls`` edges keyed by confidence bucket, with per-edge facets."""

    by_bucket: dict[str, dict[Edge, dict[str, Any]]] = field(default_factory=dict)
    phantom_by_bucket: Counter = field(default_factory=Counter)


def _file_of(chunk_id: str) -> str:
    return chunk_id.split(":", 1)[0]


def extract_bucketed_edges(graph: Any) -> BucketedEdges:
    """Like :func:`extract_static_edges` but grouped by confidence bucket.

    An edge pair reached through several raw edges (split fragments, parallel
    MultiDiGraph edges) is one entry per bucket; ``is_resolved`` is OR-merged.
    """
    out = BucketedEdges()
    phantom_nodes = {n for n, d in graph.nodes(data=True) if is_phantom_node(d)}
    for u, v, data in graph.edges(data=True):
        if edge_relation_type(data) != "calls" or u in phantom_nodes:
            continue
        bucket = confidence_bucket(data)
        if v in phantom_nodes:
            out.phantom_by_bucket[bucket] += 1
            continue
        caller = normalize_chunk_id(u)
        callee, _ = canonical_callee(normalize_chunk_id(v))
        if caller == callee:
            continue
        facets = out.by_bucket.setdefault(bucket, {}).setdefault(
            (caller, callee),
            {
                "same_file": _file_of(caller) == _file_of(callee),
                "is_resolved": False,
                "callee_kind": _kind(callee) or "unknown",
            },
        )
        facets["is_resolved"] = facets["is_resolved"] or bool(
            data.get("is_resolved", False)
        )
    return out


def _bucket_row(edges: set[Edge], traced: TracedEdges) -> dict[str, Any]:
    witnessed = traced.all_traced
    cov = {e for e in edges if e[0] in traced.executed}
    hits_d = edges & traced.direct
    return {
        "edges": len(edges),
        "hits_D": len(hits_d),
        "recall_marginal": _ratio(len(hits_d), len(traced.direct)),
        "hits_traced": len(edges & witnessed),
        "prec_lb": _ratio(len(edges & witnessed), len(edges)),
        "edges_cov": len(cov),
        "hits_cov": len(cov & witnessed),
        "prec_lb_cov": _ratio(len(cov & witnessed), len(cov)),
        "unwitnessable": len(edges) - len(cov),
        "example_hits": sorted(hits_d)[:5],
    }


def _facet_split(
    edges: Mapping[Edge, Mapping[str, Any]], facet: str, traced: TracedEdges
) -> dict[str, dict[str, Any]]:
    groups: dict[str, set[Edge]] = {}
    for edge, facets in edges.items():
        groups.setdefault(str(facets[facet]), set()).add(edge)
    return {key: _bucket_row(groups[key], traced) for key in sorted(groups)}


def score_confidence_buckets(
    bucketed: BucketedEdges, traced: TracedEdges
) -> dict[str, Any]:
    """Per-bucket witness table, untagged secondary splits, pre-registered verdict."""
    buckets = {
        name: _bucket_row(set(edges), traced)
        for name, edges in sorted(bucketed.by_bucket.items())
    }
    total_edges = sum(row["edges"] for row in buckets.values())
    for row in buckets.values():
        row["edge_share"] = _ratio(row["edges"], total_edges)
    untagged_edges = bucketed.by_bucket.get(UNTAGGED, {})
    splits = {
        facet: _facet_split(untagged_edges, facet, traced)
        for facet in ("same_file", "is_resolved", "callee_kind")
    }

    untagged = buckets.get(UNTAGGED) or _bucket_row(set(), traced)
    exact = buckets.get("tag:exact") or _bucket_row(set(), traced)
    threshold = round(VERDICT_RATIO * exact["prec_lb_cov"], 4)
    weak: list[dict[str, Any]] = []
    for facet, rows in splits.items():
        for key, row in rows.items():
            if (
                row["edges_cov"] >= SUBBUCKET_MIN_COV
                and row["prec_lb_cov"] < SUBBUCKET_HALF * untagged["prec_lb_cov"]
            ):
                weak.append(
                    {
                        "facet": facet,
                        "value": key,
                        "edges_cov": row["edges_cov"],
                        "prec_lb_cov": row["prec_lb_cov"],
                    }
                )
    weak.sort(key=lambda w: (w["prec_lb_cov"], -w["edges_cov"], w["facet"]))
    vacuous = untagged["edges_cov"] == 0
    as_reliable = (not vacuous) and untagged["prec_lb_cov"] >= threshold and not weak
    return {
        "schema": BUCKET_SCHEMA,
        "definitions": BUCKET_DEFINITIONS,
        "denominators": {
            "D": len(traced.direct),
            "E_traced": len(traced.all_traced),
            "EXEC": len(traced.executed),
            "edges_non_phantom": total_edges,
            "edges_phantom": sum(bucketed.phantom_by_bucket.values()),
        },
        "buckets": buckets,
        "phantom_by_bucket": dict(sorted(bucketed.phantom_by_bucket.items())),
        "untagged_splits": splits,
        "verdict": {
            "as_reliable_as_ast": as_reliable,
            "vacuous": vacuous,
            "untagged_edges": untagged["edges"],
            "untagged_edges_cov": untagged["edges_cov"],
            "untagged_prec_lb_cov": untagged["prec_lb_cov"],
            "tag_exact_prec_lb_cov": exact["prec_lb_cov"],
            "threshold": threshold,
            "weak_subbuckets": weak,
            "tagging_target": weak[0] if weak else None,
        },
    }
