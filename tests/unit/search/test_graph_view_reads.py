"""GraphView read helpers added for the boundary refactor."""

import networkx as nx

from search.graph_view import GraphView


class _Storage:
    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph


def _view() -> GraphView:
    g = nx.MultiDiGraph()
    g.add_node("a.py:1-2:function:f", name="f")
    g.add_node("b.py:1-2:function:g")
    g.add_edge(
        "a.py:1-2:function:f",
        "b.py:1-2:function:g",
        key="calls",
        type="calls",
        resolver_confidence=0.9,
    )
    g.add_edge(
        "a.py:1-2:function:f", "b.py:1-2:function:g", key="imports", type="imports"
    )
    return GraphView(_Storage(g))  # type: ignore[arg-type]


def test_node_count_and_ids() -> None:
    v = _view()
    assert v.node_count() == 2
    assert set(v.node_ids()) == {"a.py:1-2:function:f", "b.py:1-2:function:g"}


def test_call_edge_confidence_ignores_parallel_non_call_edges() -> None:
    v = _view()
    assert v.call_edge_confidence("a.py:1-2:function:f", "b.py:1-2:function:g") == 0.9
    assert v.call_edge_confidence("b.py:1-2:function:g", "a.py:1-2:function:f") is None


def test_edges_filter_and_keys() -> None:
    v = _view()
    assert len(v.edges()) == 2
    (imp,) = v.edges("imports")
    assert imp.key == "imports" and imp.resolver_confidence is None


def test_out_edges_carry_confidence() -> None:
    (e,) = [
        e for e in _view().out_edges("a.py:1-2:function:f") if e.rel_type == "calls"
    ]
    assert e.resolver_confidence == 0.9


def test_node_attrs_missing_is_empty() -> None:
    v = _view()
    assert v.node_attrs("nope") == {}
    assert v.node_attrs("a.py:1-2:function:f")["name"] == "f"
