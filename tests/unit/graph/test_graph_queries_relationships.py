"""Unit tests for GraphQueryEngine.get_relationships() parallel-edge handling.

Covers the parallel-edge-collapse fix (ADR-0027): a (u, v) pair connected by
more than one relationship type must expose every type via
RelationshipEntry.parallel_edges, not just the primary edge get_edge_data()
would pick before this fix -- and it must do so on both the filtered and the
unfiltered path, since verification showed find_connections's normal
(unfiltered) call was the one silently losing relationships.
"""

import tempfile
from pathlib import Path

import pytest

from graph.graph_queries import GraphQueryEngine
from graph.graph_storage import CodeGraphStorage


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
def parallel_edge_graph(graph_storage):
    """A -> B connected by BOTH 'implements' and 'uses_constant' edges.

    Reproduces the ALL_CAPS-base-class case (e.g. a class literally named
    "ABC") where both extractors fire on the same node pair -- the repro
    named in CodeGraphStorage.get_edge_data's docstring.
    """
    u = "test.py:1-10:class:Concrete"
    v = "base.py:1-5:class:ABC"
    graph_storage.add_node(u, "Concrete", "class", "test.py", language="python")
    graph_storage.add_node(v, "ABC", "class", "base.py", language="python")

    graph_storage.graph.add_edge(
        u, v, key="uses_constant", type="uses_constant", line=3, confidence=1.0
    )
    graph_storage.graph.add_edge(
        u, v, key="implements", type="implements", line=3, confidence=1.0
    )

    return graph_storage, u, v


def test_unfiltered_outbound_entry_carries_all_parallel_types(
    query_engine, parallel_edge_graph
):
    """relation_types=None must keep exactly one entry per node (cardinality
    unchanged -- direct_callers/direct_callees/total_impacted depend on this)
    but that entry's parallel_edges must list every relationship type."""
    _storage, u, v = parallel_edge_graph

    entries = query_engine.get_relationships(u, direction="outbound", max_depth=1)

    assert len(entries) == 1, "unfiltered path must keep exactly one entry per node"
    entry = entries[0]
    assert entry.chunk_id == v
    parallel_types = {d["relationship_type"] for d in entry.parallel_edges}
    assert parallel_types == {"uses_constant", "implements"}


def test_filtered_outbound_recovers_shadowed_type(query_engine, parallel_edge_graph):
    """Before the fix, filtering for 'implements' returned nothing whenever the
    primary edge (whichever wins the resolver_confidence tiebreak) was the
    other type. After the fix the node must be returned regardless of which
    edge is primary, labeled with the type that was actually asked for."""
    _storage, u, v = parallel_edge_graph

    entries = query_engine.get_relationships(
        u, direction="outbound", max_depth=1, relation_types=["implements"]
    )

    assert len(entries) == 1
    assert entries[0].chunk_id == v
    assert entries[0].relationship_type == "implements"


def test_filtered_outbound_no_match_returns_empty(query_engine, parallel_edge_graph):
    """A filter matching neither parallel type must still drop the node."""
    _storage, u, v = parallel_edge_graph

    entries = query_engine.get_relationships(
        u, direction="outbound", max_depth=1, relation_types=["inherits"]
    )

    assert entries == []


def test_two_type_filter_yields_exactly_one_entry(query_engine, parallel_edge_graph):
    """A filter matching both parallel types must still report the node once,
    not twice -- issue #23's node-level dedup (`reported`) must hold."""
    _storage, u, v = parallel_edge_graph

    entries = query_engine.get_relationships(
        u,
        direction="outbound",
        max_depth=1,
        relation_types=["implements", "uses_constant"],
    )

    assert len(entries) == 1
    # Deterministic tiebreak: sorted type name among matches -> "implements" first.
    assert entries[0].relationship_type == "implements"


def test_inbound_direction_also_carries_parallel_edges(
    query_engine, parallel_edge_graph
):
    """_traverse_inbound must populate parallel_edges too, not just outbound."""
    _storage, u, v = parallel_edge_graph

    entries = query_engine.get_relationships(v, direction="inbound", max_depth=1)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.chunk_id == u
    parallel_types = {d["relationship_type"] for d in entry.parallel_edges}
    assert parallel_types == {"uses_constant", "implements"}


def test_single_edge_pair_still_works(query_engine, graph_storage):
    """A pair with only one relationship type must behave exactly as before:
    one entry, parallel_edges containing that single edge."""
    u = "test.py:1-10:function:foo"
    v = "test.py:20-30:function:bar"
    graph_storage.add_node(u, "foo", "function", "test.py", language="python")
    graph_storage.add_node(v, "bar", "function", "test.py", language="python")
    graph_storage.add_call_edge(u, v, line_number=5)

    entries = query_engine.get_relationships(u, direction="outbound", max_depth=1)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.relationship_type == "calls"
    assert len(entry.parallel_edges) == 1
    assert entry.parallel_edges[0]["relationship_type"] == "calls"
