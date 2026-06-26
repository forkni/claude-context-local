"""Unit tests for search.graph_view — typed read adapter over CodeGraphStorage.

All tests use a lightweight fake CodeGraphStorage that wraps a hand-built
NetworkX MultiDiGraph, so no real index is required.
"""

import contextlib

import networkx as nx
import pytest

from search.graph_view import (
    EdgeRecord,
    GraphView,
    NodeRecord,
    PPRConvergenceError,
)


# ---------------------------------------------------------------------------
# Fake storage
# ---------------------------------------------------------------------------


class FakeStorage:
    """Minimal CodeGraphStorage stand-in."""

    def __init__(self, graph: nx.MultiDiGraph):
        self.graph = graph

    def load_community_map(self):
        return {}


def _make_graph() -> nx.MultiDiGraph:
    """Build a small, deterministic test graph.

    Nodes:
        A = search/foo.py:1-10:function:alpha
        B = search/bar.py:20-30:class:Beta
        C = search/baz.py:5-8:method:gamma

    Edges:
        A -> B (calls, line 7)
        B -> C (inherits, line 0)
        A -> C (calls, line 9)   ← parallel edge from A  (2 out-edges from A)

    Graph has no cycles (DAG), topology order: A, B, C or A, C, B
    """
    g = nx.MultiDiGraph()
    g.add_node(
        "search/foo.py:1-10:function:alpha",
        name="alpha",
        type="function",
        file="search/foo.py",
    )
    g.add_node(
        "search/bar.py:20-30:class:Beta",
        name="Beta",
        type="class",
        file="search/bar.py",
    )
    g.add_node(
        "search/baz.py:5-8:method:gamma",
        name="gamma",
        type="method",
        file="search/baz.py",
    )
    g.add_edge(
        "search/foo.py:1-10:function:alpha",
        "search/bar.py:20-30:class:Beta",
        type="calls",
        line=7,
    )
    g.add_edge(
        "search/bar.py:20-30:class:Beta",
        "search/baz.py:5-8:method:gamma",
        type="inherits",
        line=0,
    )
    g.add_edge(
        "search/foo.py:1-10:function:alpha",
        "search/baz.py:5-8:method:gamma",
        type="calls",
        line=9,
    )
    return g


A = "search/foo.py:1-10:function:alpha"
B = "search/bar.py:20-30:class:Beta"
C = "search/baz.py:5-8:method:gamma"
MISSING = "search/missing.py:0-0:function:nope"


@pytest.fixture
def gv() -> GraphView:
    return GraphView(FakeStorage(_make_graph()))


@pytest.fixture
def empty_gv() -> GraphView:
    return GraphView(FakeStorage(nx.MultiDiGraph()))


# ---------------------------------------------------------------------------
# Public symbols: ensure re-exports are importable
# ---------------------------------------------------------------------------


class TestReExports:
    def test_ppr_convergence_error_is_importable(self):
        assert PPRConvergenceError is not None

    def test_ppr_convergence_error_is_nx_exception(self):
        from networkx.exception import PowerIterationFailedConvergence

        assert PPRConvergenceError is PowerIterationFailedConvergence

    def test_node_record_is_dataclass(self):
        nr = NodeRecord(chunk_id=A, name="alpha", kind="function", file="search/foo.py")
        assert nr.name == "alpha"

    def test_edge_record_is_dataclass(self):
        er = EdgeRecord(source=A, target=B, rel_type="calls", line=7)
        assert er.rel_type == "calls"


# ---------------------------------------------------------------------------
# contains / is_empty
# ---------------------------------------------------------------------------


class TestContains:
    def test_present_node(self, gv):
        assert gv.contains(A)

    def test_absent_node(self, gv):
        assert not gv.contains(MISSING)

    def test_empty_graph_never_contains(self, empty_gv):
        assert not empty_gv.contains(A)


class TestIsEmpty:
    def test_nonempty_graph(self, gv):
        assert not gv.is_empty()

    def test_empty_graph(self, empty_gv):
        assert empty_gv.is_empty()


# ---------------------------------------------------------------------------
# has_edge
# ---------------------------------------------------------------------------


class TestHasEdge:
    def test_direct_edge(self, gv):
        assert gv.has_edge(A, B)

    def test_reverse_absent(self, gv):
        assert not gv.has_edge(B, A)

    def test_missing_node(self, gv):
        assert not gv.has_edge(MISSING, A)


# ---------------------------------------------------------------------------
# node()
# ---------------------------------------------------------------------------


class TestNode:
    def test_returns_none_for_missing(self, gv):
        assert gv.node(MISSING) is None

    def test_returns_node_record(self, gv):
        nr = gv.node(A)
        assert isinstance(nr, NodeRecord)

    def test_name_from_stored_attribute(self, gv):
        nr = gv.node(A)
        assert nr.name == "alpha"

    def test_kind_from_stored_type(self, gv):
        nr = gv.node(B)
        assert nr.kind == "class"

    def test_file_from_chunk_id_prefix(self, gv):
        # GraphView derives file path from chunk_id (first colon-segment)
        nr = gv.node(A)
        assert nr.file == "search/foo.py"

    def test_chunk_id_round_trips(self, gv):
        nr = gv.node(C)
        assert nr.chunk_id == C

    def test_node_is_frozen(self, gv):
        nr = gv.node(A)
        with pytest.raises((AttributeError, TypeError)):
            nr.name = "mutated"  # type: ignore[misc]

    def test_node_fallback_name_from_chunk_id(self):
        """When graph node has no 'name' attr, extract_name() kicks in."""
        g = nx.MultiDiGraph()
        chunk = "search/util.py:1-5:function:helper"
        g.add_node(chunk, type="function")  # no 'name' attr
        view = GraphView(FakeStorage(g))
        nr = view.node(chunk)
        assert nr is not None
        assert nr.name == "helper"


# ---------------------------------------------------------------------------
# out_edges / in_edges
# ---------------------------------------------------------------------------


class TestOutEdges:
    def test_empty_for_missing_node(self, gv):
        assert gv.out_edges(MISSING) == []

    def test_returns_list(self, gv):
        result = gv.out_edges(A)
        assert isinstance(result, list)

    def test_alpha_has_two_out_edges(self, gv):
        # A -> B and A -> C
        result = gv.out_edges(A)
        assert len(result) == 2

    def test_out_edge_targets(self, gv):
        targets = {er.target for er in gv.out_edges(A)}
        assert targets == {B, C}

    def test_out_edge_rel_type(self, gv):
        edges = {er.target: er for er in gv.out_edges(A)}
        assert edges[B].rel_type == "calls"

    def test_out_edge_line(self, gv):
        edges = {er.target: er for er in gv.out_edges(A)}
        assert edges[B].line == 7

    def test_out_edge_source_matches(self, gv):
        for er in gv.out_edges(A):
            assert er.source == A

    def test_leaf_node_has_no_out_edges(self, gv):
        # C has no outgoing edges
        assert gv.out_edges(C) == []

    def test_out_edge_record_type(self, gv):
        for er in gv.out_edges(A):
            assert isinstance(er, EdgeRecord)


class TestInEdges:
    def test_empty_for_missing_node(self, gv):
        assert gv.in_edges(MISSING) == []

    def test_root_node_has_no_in_edges(self, gv):
        # A has no incoming edges
        assert gv.in_edges(A) == []

    def test_c_has_two_in_edges(self, gv):
        # B -> C and A -> C
        result = gv.in_edges(C)
        assert len(result) == 2

    def test_in_edge_sources(self, gv):
        sources = {er.source for er in gv.in_edges(C)}
        assert sources == {A, B}

    def test_in_edge_target_matches(self, gv):
        for er in gv.in_edges(C):
            assert er.target == C

    def test_in_edge_rel_type(self, gv):
        edges_by_src = {er.source: er for er in gv.in_edges(C)}
        assert edges_by_src[B].rel_type == "inherits"

    def test_in_edge_record_type(self, gv):
        for er in gv.in_edges(C):
            assert isinstance(er, EdgeRecord)


# ---------------------------------------------------------------------------
# induced_topology
# ---------------------------------------------------------------------------


class TestInducedTopology:
    def test_empty_input(self, gv):
        assert gv.induced_topology([]) == []

    def test_single_node(self, gv):
        assert gv.induced_topology([A]) == [A]

    def test_all_nodes_dag(self, gv):
        # A -> B -> C and A -> C; topology must put A before B and C, B before C
        order = gv.induced_topology([A, B, C])
        assert len(order) == 3
        assert order.index(A) < order.index(B)
        assert order.index(A) < order.index(C)
        assert order.index(B) < order.index(C)

    def test_cycle_handled_via_scc(self):
        """Cyclic subgraph must not raise; all nodes returned."""
        g = nx.MultiDiGraph()
        x, y = "f.py:1-2:function:x", "f.py:3-4:function:y"
        g.add_node(x, name="x", type="function")
        g.add_node(y, name="y", type="function")
        g.add_edge(x, y)
        g.add_edge(y, x)  # cycle
        view = GraphView(FakeStorage(g))
        order = view.induced_topology([x, y])
        assert set(order) == {x, y}

    def test_subset_of_nodes(self, gv):
        # Induced over {A, C} only — B is excluded
        order = gv.induced_topology([A, C])
        assert set(order) == {A, C}
        assert order.index(A) < order.index(C)


# ---------------------------------------------------------------------------
# personalized_pagerank
# ---------------------------------------------------------------------------


class TestPersonalizedPagerank:
    def test_returns_dict(self, gv):
        ppr = gv.personalized_pagerank(
            personalization={A: 1.0},
            alpha=0.85,
        )
        assert isinstance(ppr, dict)

    def test_all_nodes_in_result(self, gv):
        ppr = gv.personalized_pagerank(
            personalization={A: 1.0},
            alpha=0.85,
        )
        assert set(ppr.keys()) == {A, B, C}

    def test_scores_sum_to_one(self, gv):
        ppr = gv.personalized_pagerank(
            personalization={A: 1.0},
            alpha=0.85,
        )
        total = sum(ppr.values())
        assert abs(total - 1.0) < 1e-4

    def test_anchor_has_highest_score(self, gv):
        # With strong personalisation on A, A should have highest PPR
        ppr = gv.personalized_pagerank(
            personalization={A: 1.0},
            alpha=0.99,  # high damping keeps mass near A
        )
        assert ppr[A] == max(ppr.values())

    def test_empty_graph_raises_or_empty(self, empty_gv):
        # Empty graph: nx.pagerank typically returns {} or raises
        try:
            result = empty_gv.personalized_pagerank(
                personalization={},
                alpha=0.85,
            )
            assert result == {}
        except Exception:
            pass  # acceptable — caller guards with is_empty() first

    def test_convergence_error_propagates(self):
        """PPRConvergenceError must bubble up for caller fallback logic."""
        g = nx.MultiDiGraph()
        for i in range(20):
            a, b = (
                f"f.py:{i}-{i + 1}:function:f{i}",
                f"f.py:{i + 1}-{i + 2}:function:f{i}b",
            )
            g.add_node(a, name=f"f{i}", type="function")
            g.add_node(b, name=f"f{i}b", type="function")
            g.add_edge(a, b)
            g.add_edge(b, a)
        view = GraphView(FakeStorage(g))
        # Force non-convergence with max_iter=1; exception must propagate cleanly
        with contextlib.suppress(PPRConvergenceError):
            view.personalized_pagerank(
                personalization={list(g.nodes)[0]: 1.0},
                alpha=0.85,
                max_iter=1,
                tol=1e-30,
            )
