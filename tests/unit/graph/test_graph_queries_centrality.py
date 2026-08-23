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
