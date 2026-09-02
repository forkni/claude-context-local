"""Tests for evaluation.tracer.scoring over a 12-node in-memory graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from evaluation.metrics import normalize_chunk_id as norm
from evaluation.tracer.build import SCHEMA
from evaluation.tracer.scoring import (
    LADDER,
    TAXONOMY,
    canonical_callee,
    classify_miss,
    emit_precision_sample,
    emit_traced_golden,
    extract_static_edges,
    load_traced_edges,
    make_source_lookup,
    score_tiers,
    score_traced,
)


# Raw node ids carry line ranges; normalized ids drop them.
A = "pkg/a.py:10-20:function:a"
B = "pkg/a.py:30-40:function:b"
C = "pkg/b.py:5-9:method:K.c"
D = "pkg/b.py:10-19:method:K.d"
E = "pkg/c.py:1-5:function:e"
F = "pkg/c.py:6-9:function:f"
K = "pkg/b.py:1-30:class:K"
K_INIT = "pkg/b.py:2-4:method:K.__init__"
W = "pkg/d.py:1-9:function:wrapper"  # owns a <locals> code object at runtime
G = "pkg/e.py:1-9:function:g"
M_OTHER = "pkg/f.py:1-9:method:Other.c"  # same method name as C, other class
SPLIT1 = "pkg/g.py:1-10:split_block:big"
SPLIT2 = "pkg/g.py:11-20:split_block:big"
PHANTOM = "d"


def make_graph() -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for n in (A, B, C, D, E, F, K, K_INIT, W, G, M_OTHER, SPLIT1, SPLIT2):
        g.add_node(n, name=n.rsplit(":", 1)[-1], type=n.split(":")[2], file=n)
    g.add_node(PHANTOM, type="symbol_name", is_target_name=True, file="", language="")
    # one static edge per tier
    g.add_edge(A, B, type="calls", resolver_source="lsp", resolver_confidence=0.98)
    g.add_edge(A, C, type="calls", resolver_source="libcst", resolver_confidence=0.9)
    g.add_edge(B, K, type="calls", resolver_source="pyan", resolver_confidence=0.75)
    g.add_edge(C, E, type="calls", confidence="exact")  # ast
    g.add_edge(E, F, type="calls", confidence="ambiguous")  # ast, never traced
    g.add_edge(A, PHANTOM, type="calls")  # phantom target "d"
    g.add_edge(A, M_OTHER, type="calls", resolver_source="pyan")  # dispatch decoy
    g.add_edge(SPLIT1, SPLIT2, type="calls")  # split fragments: dropped
    g.add_edge(A, G, type="imports")  # non-call relation: ignored
    g.add_edge(W, G, type="calls", resolver_source="lsp")
    return g


def traced_payload() -> dict[str, Any]:
    edges = [
        (norm(A), norm(B), True, 0, 5),  # lsp hit
        (norm(A), norm(C), True, 0, 3),  # libcst hit
        (norm(B), norm(K_INIT), True, 0, 1),  # pyan hit via init equivalence
        (norm(C), norm(E), True, 0, 2),  # ast hit
        (norm(A), norm(D), True, 0, 1),  # miss, phantom "d" -> name-only
        (norm(F), norm(G), True, 0, 1),  # miss, nothing static
        (norm(A), norm(F), False, 2, 1),  # indirect, unmatched
        (norm(A), "pkg/zzz.py:function:nope", True, 0, 1),  # unresolved callee
    ]
    executed = sorted({e[0] for e in edges} | {e[1] for e in edges[:-1]})
    return {
        "schema": SCHEMA,
        "integrity": {"schema_ok": True},
        "edges": [
            {"caller": c, "callee": k, "direct": d, "external_depth": x, "hits": h}
            for c, k, d, x, h in edges
        ],
        "executed_chunks": executed,
        "executed_chunks_with_locals": [norm(W)],
        "test_edges": [],
    }


def test_canonical_callee() -> None:
    assert canonical_callee("p.py:method:C.__init__") == ("p.py:class:C", True)
    assert canonical_callee("p.py:method:O.In.__init__") == ("p.py:class:O.In", True)
    assert canonical_callee("p.py:method:C.m") == ("p.py:method:C.m", False)


def test_extract_static_edges_tiers_phantoms_and_splits() -> None:
    static = extract_static_edges(make_graph())
    assert static.by_tier["lsp"] == {(norm(A), norm(B)), (norm(W), norm(G))}
    assert static.by_tier["libcst"] == {(norm(A), norm(C))}
    assert static.by_tier["pyan"] == {(norm(B), norm(K)), (norm(A), norm(M_OTHER))}
    assert static.by_tier["ast"] == {(norm(C), norm(E)), (norm(E), norm(F))}
    assert static.phantom == {(norm(A), PHANTOM)}
    assert norm(SPLIT1) == norm(SPLIT2) == "pkg/g.py:method:big"
    assert (norm(SPLIT1), norm(SPLIT2)) not in static.all_edges
    assert PHANTOM not in static.nodes
    assert static.raw_by_norm["pkg/g.py:method:big"] == [SPLIT1, SPLIT2]


def test_score_tiers_exact_fractions() -> None:
    static = extract_static_edges(make_graph())
    traced = load_traced_edges(traced_payload(), static)
    assert traced.unresolved == 1
    assert len(traced.direct) == 6
    assert len(traced.indirect) == 1
    scores = score_tiers(static, traced)
    den = scores["denominators"]
    assert den == {"D": 6, "I": 1, "E_traced": 8, "EXEC": 8, "traced_unresolved": 1}
    t = scores["tiers"]
    sixth = round(1 / 6, 4)
    assert [t[x]["recall_marginal"] for x in LADDER] == [sixth] * 4
    assert [t[x]["recall_cumulative"] for x in LADDER] == [
        sixth,
        round(2 / 6, 4),
        round(3 / 6, 4),
        round(4 / 6, 4),
    ]
    assert sum(t[x]["hits_D"] for x in LADDER) == scores["ladder_total"]["hits_D"] == 4
    assert scores["ladder_total"]["recall_ladder_total"] == round(4 / 6, 4)
    # lsp has 2 edges (A->B traced, W->G not); W is not executed.
    assert t["lsp"] == {
        "edges": 2,
        "hits_D": 1,
        "recall_marginal": sixth,
        "recall_cumulative": sixth,
        "hits_I": 0,
        "recall_indirect": 0.0,
        "hits_traced": 1,
        "prec_lb": 0.5,
        "edges_cov": 1,
        "hits_cov": 1,
        "prec_lb_cov": 1.0,
        "unwitnessable": 1,
        "unlabeled_cov": 0,
        "example_hits": [(norm(A), norm(B))],
    }
    # ast: C->E traced, E->F not but E executed -> covered and unlabeled.
    assert t["ast"]["prec_lb"] == 0.5
    assert t["ast"]["prec_lb_cov"] == 0.5
    assert t["ast"]["unwitnessable"] == 0
    assert t["ast"]["unlabeled_cov"] == 1
    # pyan: B->K hit only through __init__ canonicalization.
    assert scores["hits_via_init_equivalence"] == 1
    assert scores["ast_name_only"] == {"hits": 1, "of_misses": 2}
    assert scores["misses"] == [(norm(A), norm(D)), (norm(F), norm(G))]


def test_precision_sample_is_deterministic_and_unwitnessed_only() -> None:
    static = extract_static_edges(make_graph())
    traced = load_traced_edges(traced_payload(), static)
    s1 = emit_precision_sample(static, traced, 40)
    s2 = emit_precision_sample(static, traced, 40)
    assert json.dumps(s1, sort_keys=True) == json.dumps(s2, sort_keys=True)
    rows = {(r["tier"], r["caller"], r["callee"]) for r in s1["rows"]}
    assert rows == {("pyan", norm(A), norm(M_OTHER)), ("ast", norm(E), norm(F))}
    assert all(r["label"] is None for r in s1["rows"])


def test_traced_golden_positive_only() -> None:
    static = extract_static_edges(make_graph())
    traced = load_traced_edges(traced_payload(), static)
    golden = {
        "queries": [
            {"id": "C001", "target_chunk_id": norm(B), "expected_callers": ["x"]},
            {"id": "C002", "target_chunk_id": norm(W), "expected_callers": []},
            {"id": "C003", "target_chunk_id": norm(E), "expected_callers": []},
        ]
    }
    out = emit_traced_golden(golden, traced, "callers")
    assert out["_meta"]["semantics"] == "positive-only; missing != absent"
    assert [q["id"] for q in out["queries"]] == ["TC001", "TC003"]
    assert out["queries"][0]["expected_callers"] == [norm(A)]
    assert out["queries"][0]["category"] == "T"
    assert out["_meta"]["skipped"] == [{"id": "C002", "reason": "target not executed"}]
    callees = emit_traced_golden(
        {"queries": [{"id": "X1", "target_chunk_id": norm(A), "expected_callees": []}]},
        traced,
        "callees",
    )
    assert callees["queries"][0]["expected_callees"] == [norm(B), norm(C), norm(D)]


# ---------------------------------------------------------------------------
# taxonomy: one synthetic miss per class, order-sensitive
# ---------------------------------------------------------------------------


def _fixture_for_taxonomy():
    static = extract_static_edges(make_graph())
    payload = traced_payload()
    # Runtime routes A -> W -> G while static collapsed it to A -> G.
    payload["edges"] += [
        {
            "caller": norm(A),
            "callee": norm(W),
            "direct": True,
            "external_depth": 0,
            "hits": 1,
        },
        {
            "caller": norm(W),
            "callee": norm(G),
            "direct": True,
            "external_depth": 0,
            "hits": 1,
        },
    ]
    payload["executed_chunks"] = sorted(
        set(payload["executed_chunks"]) | {norm(W), norm(G)}
    )
    static.by_tier["lsp"].add((norm(A), norm(G)))
    traced = load_traced_edges(payload, static)
    return static, traced


def test_classify_miss_each_class() -> None:
    static, traced = _fixture_for_taxonomy()
    sources = {
        norm(A): "def a():\n    d()\n    return sorted(xs, key=f)\n",
        norm(F): "def f():\n    return 1\n",
    }
    lookup = sources.get
    # A -> W: W has <locals>, traced W -> G, static A -> G  => wrapper_routed
    cls, detail = classify_miss((norm(A), norm(W)), static, traced, lookup)
    assert cls == "wrapper_routed"
    assert detail["collapsed"] == (norm(A), norm(G))
    # A -> F: 'f' referenced in A's source but never called  => via_external
    assert (
        classify_miss((norm(A), norm(F)), static, traced, lookup)[0] == "via_external"
    )
    # A -> D: phantom "d" exists and d() is called  => name_only_unresolved
    assert (
        classify_miss((norm(A), norm(D)), static, traced, lookup)[0]
        == "name_only_unresolved"
    )
    # A -> K.c when static only has A -> Other.c  => dynamic_dispatch
    static.by_tier["libcst"].discard((norm(A), norm(C)))
    src_c = {norm(A): "def a():\n    obj.c()\n"}
    assert (
        classify_miss((norm(A), norm(C)), static, traced, src_c.get)[0]
        == "dynamic_dispatch"
    )
    # F -> G: 'g' absent from F's source  => no_syntactic_call
    assert (
        classify_miss((norm(F), norm(G)), static, traced, lookup)[0]
        == "no_syntactic_call"
    )
    # F -> G with call syntax present, no static edge, no phantom  => unclassified
    src_u = {norm(F): "def f():\n    return g()\n"}
    assert (
        classify_miss((norm(F), norm(G)), static, traced, src_u.get)[0]
        == "unclassified"
    )
    # no source at all also falls to unclassified with the flag recorded
    cls, detail = classify_miss((norm(F), norm(G)), static, traced, None)
    assert (cls, detail) == ("unclassified", {"source_available": False})
    # K -> G: caller is a class chunk  => class_body_eval, before any source check
    cls, detail = classify_miss((norm(K), norm(G)), static, traced, None)
    assert (cls, detail) == ("class_body_eval", {"callee_kind": "function"})


def test_dynamic_dispatch_matches_abstract_decorated_target() -> None:
    static, traced = _fixture_for_taxonomy()
    abstract = "pkg/b.py:decorated_definition:Base.run"
    static.by_tier["lsp"].add((norm(A), abstract))
    cls, detail = classify_miss(
        (norm(A), "pkg/z.py:method:Impl.run"),
        static,
        traced,
        {norm(A): "self.run()"}.get,
    )
    assert (cls, detail) == ("dynamic_dispatch", {"static_target": abstract})


def test_score_traced_report_shape() -> None:
    result = score_traced(traced_payload(), make_graph(), sample_size=8)
    report = result["report"]
    assert report["schema"] == "resolver-tier-scores/1"
    assert set(report["misses"]["taxonomy"]) == set(TAXONOMY)
    assert report["misses"]["count"] == 2
    assert report["misses"]["items"][0]["class"] == "name_only_unresolved"
    assert report["misses"]["items"][1]["class"] == "unclassified"
    assert report["ladder"] == list(LADDER)
    assert result["traced_goldens"] == {}
    assert json.dumps(result, sort_keys=True)  # fully serializable


def test_make_source_lookup_concatenates_split_fragments(tmp_path: Path) -> None:
    src = tmp_path / "m.py"
    src.write_text("l1\nl2\nl3\nl4\n", encoding="utf-8")
    store = {
        "pkg/m.py:1-2:split_block:big": {
            "metadata": {"file_path": str(src), "start_line": 1, "end_line": 2}
        },
        "pkg/m.py:3-4:split_block:big": {
            "metadata": {"file_path": str(src), "start_line": 3, "end_line": 4}
        },
        "pkg/m.py:1-1:function:gone": {
            "metadata": {
                "file_path": str(tmp_path / "x"),
                "start_line": 1,
                "end_line": 1,
            }
        },
    }
    lookup = make_source_lookup(store)
    assert lookup("pkg/m.py:method:big") == "l1\nl2\nl3\nl4"
    assert lookup("pkg/m.py:function:gone") is None
    assert lookup("nope") is None
