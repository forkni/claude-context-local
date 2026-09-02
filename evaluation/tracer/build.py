"""Turn raw trace runs into ``evaluation/traced_callgraph.json``.

Three stages, each pure and separately testable:

1. :func:`intersect_runs` -- edge set = intersection over runs of
   ``(caller, callee, external_depth)`` on index-agnostic endpoint keys;
   anything outside the intersection is reported as nondeterministic.
2. :func:`map_endpoints` -- endpoint ``(path, def_line, body_line, qual)`` to a
   normalized chunk id via :func:`evaluation.chunk_mapping.find_enclosing_chunk`,
   trying ``body_line`` first (lands ``split_block`` and ``decorated_definition``
   chunks) then ``def_line``.
3. :func:`build_traced_callgraph` -- aggregate mapped edges, drop self-loops
   (a lambda or comprehension calling out of its own chunk collapses to one),
   and compute the TraceEval-style integrity block.

Only positives are recorded: an edge absent here is unwitnessed, not absent.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evaluation.chunk_mapping import build_line_to_chunk_map, find_enclosing_chunk


SCHEMA = "traced-callgraph/1"
RAW_SCHEMA = "callgraph-trace-raw/1"
MAPPED_TYPES = frozenset(
    {"function", "method", "class", "decorated_definition", "split_block"}
)
MAX_EXAMPLES = 10

EndpointKey = tuple[str, int, int, str]  # (path, def_line, body_line, qual)
EdgeKey = tuple[EndpointKey, EndpointKey, int]


def endpoint_key(node: Mapping[str, Any]) -> EndpointKey:
    return (node["path"], int(node["def_line"]), int(node["body_line"]), node["qual"])


def load_run(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != RAW_SCHEMA:
        raise ValueError(
            f"{path}: expected schema {RAW_SCHEMA!r}, got {payload.get('schema')!r}"
        )
    return payload


@dataclass
class Intersection:
    runs: int
    edges: dict[EdgeKey, int]  # min hit count across runs
    hits: dict[EndpointKey, int]  # endpoints hit in every run, min count
    test_edges: dict[tuple[str, str, EndpointKey], int]
    dropped_edges: list[tuple[EdgeKey, list[int]]] = field(default_factory=list)
    dropped_hits: list[tuple[EndpointKey, list[int]]] = field(default_factory=list)

    @property
    def deterministic(self) -> bool:
        return not self.dropped_edges and not self.dropped_hits


def _run_edges(run: Mapping[str, Any]) -> dict[EdgeKey, int]:
    nodes = [endpoint_key(n) for n in run["nodes"]]
    out: dict[EdgeKey, int] = {}
    for caller_idx, callee_idx, depth, count in run["edges"]:
        out[(nodes[caller_idx], nodes[callee_idx], int(depth))] = int(count)
    return out


def _run_hits(run: Mapping[str, Any]) -> dict[EndpointKey, int]:
    return {endpoint_key(n): int(n.get("hits", 0)) for n in run["nodes"]}


def _run_test_edges(run: Mapping[str, Any]) -> dict[tuple[str, str, EndpointKey], int]:
    nodes = [endpoint_key(n) for n in run["nodes"]]
    return {
        (path, qual, nodes[callee_idx]): int(count)
        for path, qual, callee_idx, count in run.get("test_edges", [])
    }


def intersect_runs(runs: Sequence[Mapping[str, Any]]) -> Intersection:
    """Keep only edges/endpoints present in every run; report the rest."""
    if not runs:
        raise ValueError("at least one run is required")
    per_run_edges = [_run_edges(r) for r in runs]
    per_run_hits = [_run_hits(r) for r in runs]
    per_run_test = [_run_test_edges(r) for r in runs]

    edge_union: set[EdgeKey] = set().union(*per_run_edges)
    edges: dict[EdgeKey, int] = {}
    dropped_edges: list[tuple[EdgeKey, list[int]]] = []
    for key in sorted(edge_union):
        counts = [e.get(key, 0) for e in per_run_edges]
        if all(counts):
            edges[key] = min(counts)
        else:
            dropped_edges.append((key, counts))

    hit_union: set[EndpointKey] = set().union(*per_run_hits)
    hits: dict[EndpointKey, int] = {}
    dropped_hits: list[tuple[EndpointKey, list[int]]] = []
    for key in sorted(hit_union):
        counts = [h.get(key, 0) for h in per_run_hits]
        if all(counts):
            hits[key] = min(counts)
        else:
            dropped_hits.append((key, counts))

    test_union: set[tuple[str, str, EndpointKey]] = set().union(*per_run_test)
    test_edges = {
        key: min(t.get(key, 0) for t in per_run_test)
        for key in sorted(test_union)
        if all(t.get(key, 0) for t in per_run_test)
    }
    return Intersection(
        runs=len(runs),
        edges=edges,
        hits=hits,
        test_edges=test_edges,
        dropped_edges=dropped_edges,
        dropped_hits=dropped_hits,
    )


@dataclass
class MappedEndpoint:
    chunk_id: str | None
    reason: str | None  # None when mapped; else unindexed_file | unmapped_endpoint
    via: str | None = None  # "body_line" | "def_line"


def build_line_map(metadata_store: Any) -> dict[str, list[tuple[int, int, str]]]:
    return build_line_to_chunk_map(
        metadata_store, semantic_types=MAPPED_TYPES, normalize=True
    )


def map_endpoints(
    endpoints: Iterable[EndpointKey],
    line_map: Mapping[str, list[tuple[int, int, str]]],
) -> dict[EndpointKey, MappedEndpoint]:
    out: dict[EndpointKey, MappedEndpoint] = {}
    for key in endpoints:
        path, def_line, body_line, _qual = key
        if path not in line_map:
            out[key] = MappedEndpoint(None, "unindexed_file")
            continue
        cid = find_enclosing_chunk(line_map, path, body_line)
        via = "body_line"
        if cid is None and def_line != body_line:
            cid = find_enclosing_chunk(line_map, path, def_line)
            via = "def_line"
        if cid is None:
            out[key] = MappedEndpoint(None, "unmapped_endpoint")
        else:
            out[key] = MappedEndpoint(cid, None, via)
    return out


def _fmt_endpoint(key: EndpointKey) -> str:
    path, def_line, body_line, qual = key
    return f"{path}:{def_line}({body_line}):{qual}"


def build_traced_callgraph(
    inter: Intersection,
    line_map: Mapping[str, list[tuple[int, int, str]]],
    *,
    run_files: Sequence[str] = (),
    index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the ``traced-callgraph/1`` payload."""
    endpoints: set[EndpointKey] = set(inter.hits)
    for caller, callee, _d in inter.edges:
        endpoints.add(caller)
        endpoints.add(callee)
    for _p, _q, callee in inter.test_edges:
        endpoints.add(callee)
    mapped = map_endpoints(sorted(endpoints), line_map)

    dropped: dict[str, dict[str, Any]] = {
        reason: {"reason": reason, "count": 0, "examples": []}
        for reason in (
            "nondeterministic",
            "unindexed_file",
            "unmapped_endpoint",
            "self_loop",
        )
    }

    def drop(reason: str, example: str, count: int = 1) -> None:
        bucket = dropped[reason]
        bucket["count"] += count
        if len(bucket["examples"]) < MAX_EXAMPLES:
            bucket["examples"].append(example)

    for key, counts in inter.dropped_edges:
        drop(
            "nondeterministic",
            f"{_fmt_endpoint(key[0])} -> {_fmt_endpoint(key[1])} depth={key[2]} counts={counts}",
        )
    for key, counts in inter.dropped_hits:
        drop("nondeterministic", f"{_fmt_endpoint(key)} hits={counts}")

    unmapped_reported: set[EndpointKey] = set()

    def chunk_of(key: EndpointKey) -> str | None:
        m = mapped[key]
        if m.chunk_id is None and key not in unmapped_reported:
            unmapped_reported.add(key)
            drop(m.reason or "unmapped_endpoint", _fmt_endpoint(key))
        return m.chunk_id

    executed: set[str] = set()
    endpoint_hits: dict[str, int] = {}
    for key, count in inter.hits.items():
        cid = chunk_of(key)
        if cid is not None:
            executed.add(cid)
            endpoint_hits[cid] = endpoint_hits.get(cid, 0) + count
    # Chunks owning a nested code object (closure, lambda, decorator wrapper):
    # the scorer's wrapper_routed taxonomy needs this since qualnames are gone
    # after mapping.
    with_locals = {
        m.chunk_id
        for key, m in mapped.items()
        if m.chunk_id is not None and "<locals>" in key[3]
    }

    agg: dict[tuple[str, str, int], int] = {}
    unresolved_edge_endpoints = 0
    for (caller, callee, depth), count in inter.edges.items():
        c_id = chunk_of(caller)
        k_id = chunk_of(callee)
        if c_id is None or k_id is None:
            unresolved_edge_endpoints += 1
            continue
        if c_id == k_id:
            drop("self_loop", f"{c_id} (via {caller[3]} -> {callee[3]})", count)
            continue
        # Both endpoints ran, so both are executed chunks even if the caller's
        # own call event predates the profiler install.
        executed.add(c_id)
        executed.add(k_id)
        agg_key = (c_id, k_id, depth)
        agg[agg_key] = agg.get(agg_key, 0) + count

    edges = [
        {
            "caller": c_id,
            "callee": k_id,
            "direct": depth == 0,
            "external_depth": depth,
            "hits": count,
        }
        for (c_id, k_id, depth), count in sorted(agg.items())
    ]
    test_edges = []
    for (path, qual, callee), count in inter.test_edges.items():
        k_id = mapped[callee].chunk_id
        if k_id is not None:
            test_edges.append([path, qual, k_id, count])
    test_edges.sort()

    cross = {(e["caller"], e["callee"]) for e in edges}
    direct_cross = {(e["caller"], e["callee"]) for e in edges if e["direct"]}
    integrity = {
        "runs": inter.runs,
        "deterministic": inter.deterministic,
        "dropped_nondeterministic": dropped["nondeterministic"]["count"],
        "cross_function_edges": len(cross),
        "direct_cross_function_edges": len(direct_cross),
        "unresolved_endpoints": sum(1 for m in mapped.values() if m.chunk_id is None),
        "unresolved_edge_endpoints": unresolved_edge_endpoints,
        "density_ok": len(cross) >= 2,
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "runs": inter.runs,
        "run_files": list(run_files),
        "index": dict(index or {}),
        "integrity": integrity,
        "executed_chunks": sorted(executed),
        "executed_chunk_hits": {k: endpoint_hits[k] for k in sorted(endpoint_hits)},
        "executed_chunks_with_locals": sorted(with_locals & executed),
        "edges": edges,
        "test_edges": test_edges,
        "dropped": [dropped[r] for r in dropped if dropped[r]["count"]],
        "mapping": {
            "mapped": sum(1 for m in mapped.values() if m.chunk_id is not None),
            "via_body_line": sum(1 for m in mapped.values() if m.via == "body_line"),
            "via_def_line": sum(1 for m in mapped.values() if m.via == "def_line"),
        },
    }
    integrity["schema_ok"] = check_schema(payload)
    return payload


def check_schema(payload: Mapping[str, Any]) -> bool:
    """Structural validity of a ``traced-callgraph/1`` payload (``test_edges`` exempt)."""
    if payload.get("schema") != SCHEMA:
        return False
    executed = payload.get("executed_chunks")
    if not isinstance(executed, list) or executed != sorted(set(executed)):
        return False
    if not all(isinstance(c, str) and c for c in executed):
        return False
    executed_set = set(executed)
    seen: set[tuple[str, str, int]] = set()
    for e in payload.get("edges", []):
        caller, callee, depth = (
            e.get("caller"),
            e.get("callee"),
            e.get("external_depth"),
        )
        if not (
            isinstance(caller, str) and isinstance(callee, str) and caller and callee
        ):
            return False
        if caller == callee or caller not in executed_set or callee not in executed_set:
            return False
        if not isinstance(depth, int) or depth < 0 or e.get("direct") != (depth == 0):
            return False
        if not isinstance(e.get("hits"), int) or e["hits"] < 1:
            return False
        key = (caller, callee, depth)
        if key in seen:
            return False
        seen.add(key)
    return True
