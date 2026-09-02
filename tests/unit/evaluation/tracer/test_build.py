"""Tests for evaluation.tracer.build over synthetic raw runs and a fake store."""

from __future__ import annotations

from typing import Any

import pytest

from evaluation.tracer.build import (
    RAW_SCHEMA,
    SCHEMA,
    Intersection,
    build_line_map,
    build_traced_callgraph,
    check_schema,
    intersect_runs,
    map_endpoints,
)


A = ("pkg/a.py", 10, 11, "outer")
A_LAMBDA = ("pkg/a.py", 14, 14, "outer.<locals>.<lambda>")
B = ("pkg/a.py", 30, 31, "helper")
C = ("pkg/b.py", 5, 6, "Klass.method")
C_INIT = ("pkg/b.py", 2, 3, "Klass.__init__")
D_SPLIT = ("pkg/c.py", 40, 47, "long_fn")  # decorated: def_line 40, body 47
UNINDEXED = ("pkg/zzz.py", 1, 2, "nowhere")
GAP = ("pkg/a.py", 200, 201, "outside_any_chunk")


def raw_run(
    edges: dict[tuple[tuple, tuple, int], int],
    hits: dict[tuple, int] | None = None,
    test_edges: dict[tuple[str, str, tuple], int] | None = None,
) -> dict[str, Any]:
    """Build a ``callgraph-trace-raw/1`` payload from endpoint tuples."""
    keys: set[tuple] = set(hits or {})
    for c, k, _ in edges:
        keys.update((c, k))
    for _p, _q, k in test_edges or {}:
        keys.add(k)
    ordered = sorted(keys, key=lambda e: (e[0], e[1], e[3]))
    idx = {e: i for i, e in enumerate(ordered)}
    return {
        "schema": RAW_SCHEMA,
        "nodes": [
            {
                "path": e[0],
                "def_line": e[1],
                "body_line": e[2],
                "qual": e[3],
                "hits": (hits or {}).get(e, 0),
            }
            for e in ordered
        ],
        "edges": sorted([idx[c], idx[k], d, n] for (c, k, d), n in edges.items()),
        "test_edges": sorted(
            [p, q, idx[k], n] for (p, q, k), n in (test_edges or {}).items()
        ),
        "counters": {},
    }


def make_store() -> dict[str, Any]:
    entries = [
        ("pkg/a.py:10-20:function:outer", "pkg/a.py", 10, 20, "function"),
        ("pkg/a.py:30-35:function:helper", "pkg/a.py", 30, 35, "function"),
        ("pkg/b.py:1-9:class:Klass", "pkg/b.py", 1, 9, "class"),
        ("pkg/b.py:2-4:method:Klass.__init__", "pkg/b.py", 2, 4, "method"),
        ("pkg/b.py:5-9:method:Klass.method", "pkg/b.py", 5, 9, "method"),
        # decorated + split: chunk starts at the first body statement (47).
        ("pkg/c.py:47-60:split_block:long_fn", "pkg/c.py", 47, 60, "split_block"),
        ("pkg/c.py:61-80:split_block:long_fn", "pkg/c.py", 61, 80, "split_block"),
        ("pkg/a.py:0-0:module:a", "pkg/a.py", 1, 300, "module"),  # not mapped
    ]
    return {
        raw: {
            "metadata": {
                "relative_path": rel,
                "start_line": s,
                "end_line": e,
                "chunk_type": t,
            }
        }
        for raw, rel, s, e, t in entries
    }


def test_intersect_keeps_common_edges_with_min_counts() -> None:
    r1 = raw_run({(A, B, 0): 3, (B, C, 1): 2, (A, C, 0): 1}, hits={A: 5, B: 3})
    r2 = raw_run({(A, B, 0): 2, (B, C, 1): 2}, hits={A: 4, B: 3, C: 1})
    r3 = raw_run({(A, B, 0): 7, (B, C, 1): 9}, hits={A: 5, B: 3})
    inter = intersect_runs([r1, r2, r3])
    assert inter.runs == 3
    assert inter.edges == {(A, B, 0): 2, (B, C, 1): 2}
    assert inter.hits == {A: 4, B: 3}
    assert inter.dropped_edges == [((A, C, 0), [1, 0, 0])]
    assert inter.dropped_hits == [(C, [0, 1, 0])]
    assert not inter.deterministic


def test_intersect_single_identical_runs_is_deterministic() -> None:
    run = raw_run({(A, B, 0): 1}, hits={A: 1, B: 1})
    inter = intersect_runs([run, run])
    assert inter.deterministic
    assert inter.edges == {(A, B, 0): 1}
    with pytest.raises(ValueError):
        intersect_runs([])


def test_map_endpoints_body_line_first_then_def_line_then_reasons() -> None:
    line_map = build_line_map(make_store())
    mapped = map_endpoints([A, A_LAMBDA, C_INIT, D_SPLIT, UNINDEXED, GAP], line_map)
    assert mapped[A].chunk_id == "pkg/a.py:function:outer"
    assert mapped[A].via == "body_line"
    assert mapped[A_LAMBDA].chunk_id == "pkg/a.py:function:outer"
    # Innermost span wins over the enclosing class.
    assert mapped[C_INIT].chunk_id == "pkg/b.py:method:Klass.__init__"
    # Decorated split function: def_line 40 is outside every chunk, body 47 hits.
    # dedup_key collapses split_block to the "method" kind regardless of nesting;
    # graph node ids normalize the same way, so the two sides stay comparable.
    assert mapped[D_SPLIT].chunk_id == "pkg/c.py:method:long_fn"
    assert mapped[D_SPLIT].via == "body_line"
    assert mapped[UNINDEXED].chunk_id is None
    assert mapped[UNINDEXED].reason == "unindexed_file"
    assert mapped[GAP].chunk_id is None
    assert mapped[GAP].reason == "unmapped_endpoint"


def test_map_endpoints_def_line_fallback() -> None:
    line_map = build_line_map(make_store())
    # body_line outside any chunk, def_line inside: fallback lands on def_line.
    weird = ("pkg/a.py", 12, 150, "odd")
    mapped = map_endpoints([weird], line_map)
    assert mapped[weird].chunk_id == "pkg/a.py:function:outer"
    assert mapped[weird].via == "def_line"


def test_build_aggregates_drops_and_integrity() -> None:
    edges = {
        (A, B, 0): 3,
        (A_LAMBDA, B, 0): 2,  # collapses into A -> B
        (A, A_LAMBDA, 0): 2,  # self-loop after mapping
        (B, C_INIT, 0): 1,
        (B, C, 1): 1,
        (A, UNINDEXED, 0): 4,
        (GAP, B, 0): 1,
    }
    hits = {A: 5, A_LAMBDA: 2, B: 6, C: 1, C_INIT: 1, UNINDEXED: 4, GAP: 1, D_SPLIT: 2}
    run = raw_run(edges, hits, test_edges={("tests/t.py", "test_x", B): 2})
    inter = intersect_runs([run, run, run])
    payload = build_traced_callgraph(
        inter, build_line_map(make_store()), run_files=["r1", "r2", "r3"]
    )
    assert payload["schema"] == SCHEMA
    assert payload["integrity"]["schema_ok"] is True
    assert payload["integrity"]["deterministic"] is True
    assert payload["integrity"]["density_ok"] is True
    assert payload["integrity"]["cross_function_edges"] == 3
    assert payload["integrity"]["direct_cross_function_edges"] == 2
    assert payload["integrity"]["unresolved_endpoints"] == 2
    assert payload["integrity"]["unresolved_edge_endpoints"] == 2
    # Sorted by (caller, callee, depth); "helper" sorts before "outer".
    assert payload["edges"] == [
        {
            "caller": "pkg/a.py:function:helper",
            "callee": "pkg/b.py:method:Klass.__init__",
            "direct": True,
            "external_depth": 0,
            "hits": 1,
        },
        {
            "caller": "pkg/a.py:function:helper",
            "callee": "pkg/b.py:method:Klass.method",
            "direct": False,
            "external_depth": 1,
            "hits": 1,
        },
        {
            "caller": "pkg/a.py:function:outer",
            "callee": "pkg/a.py:function:helper",
            "direct": True,
            "external_depth": 0,
            "hits": 5,
        },
    ]
    assert payload["executed_chunks"] == [
        "pkg/a.py:function:helper",
        "pkg/a.py:function:outer",
        "pkg/b.py:method:Klass.__init__",
        "pkg/b.py:method:Klass.method",
        "pkg/c.py:method:long_fn",
    ]
    assert payload["executed_chunk_hits"]["pkg/a.py:function:outer"] == 7
    assert payload["executed_chunks_with_locals"] == ["pkg/a.py:function:outer"]
    assert payload["test_edges"] == [
        ["tests/t.py", "test_x", "pkg/a.py:function:helper", 2]
    ]
    dropped = {d["reason"]: d for d in payload["dropped"]}
    assert set(dropped) == {"unindexed_file", "unmapped_endpoint", "self_loop"}
    assert dropped["self_loop"]["count"] == 2
    assert dropped["unindexed_file"]["count"] == 1
    assert dropped["unmapped_endpoint"]["count"] == 1
    assert payload["mapping"] == {"mapped": 6, "via_body_line": 6, "via_def_line": 0}
    assert payload["run_files"] == ["r1", "r2", "r3"]


def test_build_reports_nondeterminism() -> None:
    r1 = raw_run({(A, B, 0): 1, (B, C, 0): 1}, hits={A: 1, B: 1, C: 1})
    r2 = raw_run({(A, B, 0): 1}, hits={A: 1, B: 1})
    inter = intersect_runs([r1, r2])
    payload = build_traced_callgraph(inter, build_line_map(make_store()))
    assert payload["integrity"]["deterministic"] is False
    assert payload["integrity"]["dropped_nondeterministic"] == 2  # edge + hit
    assert payload["integrity"]["density_ok"] is False
    nondet = next(d for d in payload["dropped"] if d["reason"] == "nondeterministic")
    assert any("Klass.method" in ex for ex in nondet["examples"])


def test_check_schema_rejects_bad_payloads() -> None:
    good = build_traced_callgraph(
        Intersection(1, {(A, B, 0): 1}, {A: 1, B: 1}, {}), build_line_map(make_store())
    )
    assert check_schema(good)
    bad_loop = {
        **good,
        "edges": [{**good["edges"][0], "callee": good["edges"][0]["caller"]}],
    }
    assert not check_schema(bad_loop)
    bad_direct = {**good, "edges": [{**good["edges"][0], "direct": False}]}
    assert not check_schema(bad_direct)
    bad_unknown = {**good, "edges": [{**good["edges"][0], "callee": "x.py:function:y"}]}
    assert not check_schema(bad_unknown)
    assert not check_schema({**good, "executed_chunks": good["executed_chunks"][::-1]})
    assert not check_schema({**good, "schema": "other"})
