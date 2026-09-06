"""Unit tests for GraphQueryEngine.compute_centrality's exclude_phantoms knob
(Workstream E, ADR-0055).

Covers all four centrality methods deliberately: ``degree``/``pagerank``
route through ``_simple_digraph_view()``, but ``betweenness``/``closeness``
call ``nx.*_centrality()`` directly on the raw MultiDiGraph -- threading the
flag only through the view would make it silently no-op on half the methods.
"""

import tempfile
from pathlib import Path

import pytest

from graph.graph_queries import GraphQueryEngine
from graph.graph_storage import CodeGraphStorage


METHODS = ("degree", "betweenness", "closeness", "pagerank")

REAL_A = "a.py:1-5:function:foo"
REAL_B = "b.py:1-5:function:bar"
PHANTOM = "unresolved_symbol"


@pytest.fixture
def temp_storage():
    """Create temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def graph_storage(temp_storage):
    """Create a graph storage instance."""
    return CodeGraphStorage(project_id="test_project", storage_dir=temp_storage)


@pytest.fixture
def query_engine(graph_storage):
    """Create a query engine instance."""
    return GraphQueryEngine(graph_storage)


@pytest.fixture
def graph_with_phantom(graph_storage):
    """Two real chunk nodes (A -> B) plus a phantom placeholder node.

    ``add_call_edge`` to an unresolved callee name auto-creates a
    ``NODE_TYPE_SYMBOL_NAME`` / ``is_target_name=True`` placeholder node --
    the exact same phantom-creation path production call-graph extraction
    uses, per ``CodeGraphStorage.add_call_edge``'s docstring.
    """
    graph_storage.add_node(REAL_A, "foo", "function", "a.py")
    graph_storage.add_node(REAL_B, "bar", "function", "b.py")
    graph_storage.graph.add_edge(REAL_A, REAL_B, type="calls")
    graph_storage.add_call_edge(REAL_A, PHANTOM, line_number=3)
    return graph_storage


@pytest.mark.parametrize("method", METHODS)
def test_exclude_phantoms_false_is_byte_identical_to_implicit_default(
    query_engine, graph_with_phantom, method
):
    """Explicit exclude_phantoms=False must match the pre-existing (implicit)
    default byte-for-byte -- the knob must not change behavior when off."""
    explicit = query_engine.compute_centrality(method=method, exclude_phantoms=False)
    implicit = query_engine.compute_centrality(method=method)
    assert explicit == implicit
    assert PHANTOM in explicit


@pytest.mark.parametrize("method", METHODS)
def test_exclude_phantoms_true_drops_phantom_node(
    query_engine, graph_with_phantom, method
):
    """Enabling the flag removes the phantom placeholder node's score entirely."""
    scores = query_engine.compute_centrality(method=method, exclude_phantoms=True)
    assert PHANTOM not in scores


@pytest.mark.parametrize("method", METHODS)
def test_exclude_phantoms_true_keeps_real_chunk_nodes(
    query_engine, graph_with_phantom, method
):
    """Real chunk nodes must never be dropped by the phantom filter."""
    scores = query_engine.compute_centrality(method=method, exclude_phantoms=True)
    assert REAL_A in scores
    assert REAL_B in scores


def test_exclude_phantoms_does_not_mutate_storage_graph(
    query_engine, graph_with_phantom
):
    """The filtered view must be read-only -- the phantom node must survive
    on the storage graph for a later exclude_phantoms=False call."""
    query_engine.compute_centrality(method="pagerank", exclude_phantoms=True)
    assert PHANTOM in graph_with_phantom.graph
    assert graph_with_phantom.graph.number_of_nodes() == 3


# ---------------------------------------------------------------------------
# exclude_containment (contains-centrality isolation, 2026-09-06)
# ---------------------------------------------------------------------------

CLASS_C = "c.py:1-20:class:Widget"
METHOD_D = "c.py:5-10:method:Widget.render"


@pytest.fixture
def graph_with_containment(graph_storage):
    """A class node containing a method (``contains``) plus an unrelated
    ``calls`` edge, so the two relationship types can be told apart.

    The ``contains`` edge is added with the exact key/attr shape that
    ``CodeGraphStorage.add_relationship_edge`` writes (key == attr type ==
    ``RelationshipType.CONTAINS.value``), which is what the filter matches on.
    """
    graph_storage.add_node(REAL_A, "foo", "function", "a.py")
    graph_storage.add_node(REAL_B, "bar", "function", "b.py")
    graph_storage.add_node(CLASS_C, "Widget", "class", "c.py")
    graph_storage.add_node(METHOD_D, "Widget.render", "method", "c.py")
    graph_storage.graph.add_edge(REAL_A, REAL_B, key="calls", type="calls")
    graph_storage.graph.add_edge(CLASS_C, METHOD_D, key="contains", type="contains")
    # Chain the method into the call graph so betweenness/closeness have a
    # path that only exists *through* the contains edge: C -contains-> D -calls-> A -calls-> B.
    graph_storage.graph.add_edge(METHOD_D, REAL_A, key="calls", type="calls")
    return graph_storage


@pytest.mark.parametrize("method", METHODS)
def test_exclude_containment_false_is_byte_identical_to_implicit_default(
    query_engine, graph_with_containment, method
):
    """Explicit exclude_containment=False must match the implicit default
    byte-for-byte -- the knob must not change behavior when off."""
    explicit = query_engine.compute_centrality(method=method, exclude_containment=False)
    implicit = query_engine.compute_centrality(method=method)
    assert explicit == implicit


@pytest.mark.parametrize("method", METHODS)
def test_exclude_containment_true_removes_contains_edge_influence(
    query_engine, graph_with_containment, method
):
    """With the flag on, the class loses its only edge and the method loses
    its only in-edge, while the ``calls`` chain D -> A -> B is untouched."""
    scores = query_engine.compute_centrality(method=method, exclude_containment=True)
    # Nodes survive (edge filter only).
    assert CLASS_C in scores and METHOD_D in scores
    if method == "degree":
        assert scores[CLASS_C] == 0.0
        assert scores[METHOD_D] == 1.0 and scores[REAL_A] == 2.0
    elif method == "pagerank":
        # Neither C nor D has an in-edge any more, so both sit on the floor.
        assert scores[CLASS_C] == pytest.approx(scores[METHOD_D])
        assert scores[REAL_A] > scores[METHOD_D]
    else:
        # betweenness: nothing routes through D; closeness: nothing reaches D.
        assert scores[METHOD_D] == 0.0
    with_edges = query_engine.compute_centrality(method=method)
    assert with_edges[METHOD_D] > scores[METHOD_D]
    assert with_edges != scores


def test_exclude_containment_does_not_mutate_storage_graph(
    query_engine, graph_with_containment
):
    """The filtered view must be read-only -- the ``contains`` edge must
    survive on the storage graph for traversal and a later default call."""
    query_engine.compute_centrality(method="pagerank", exclude_containment=True)
    assert graph_with_containment.graph.has_edge(CLASS_C, METHOD_D, key="contains")
    assert graph_with_containment.graph.number_of_edges() == 3
    default = query_engine.compute_centrality(method="pagerank")
    assert default[METHOD_D] > default[CLASS_C]


@pytest.mark.parametrize("method", METHODS)
def test_exclude_containment_composes_with_exclude_phantoms(
    query_engine, graph_with_containment, method
):
    """Both filters stack: phantom node gone AND contains edge ignored."""
    graph_with_containment.add_call_edge(REAL_A, PHANTOM, line_number=3)
    scores = query_engine.compute_centrality(
        method=method, exclude_phantoms=True, exclude_containment=True
    )
    assert PHANTOM not in scores
    assert set(scores) == {REAL_A, REAL_B, CLASS_C, METHOD_D}
    only_phantoms = query_engine.compute_centrality(
        method=method, exclude_phantoms=True
    )
    assert only_phantoms != scores
