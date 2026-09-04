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


# ---------------------------------------------------------------------------
# Filtered BFS expands through matching edges only
# ---------------------------------------------------------------------------


def _add(storage, cid, kind="function", file="f.py"):
    storage.add_node(cid, cid.split(":")[-1], kind, file, language="python")


@pytest.fixture
def mixed_chain_graph(graph_storage):
    """X -calls-> Y -contains-> Z  and  W -calls-> X.

    Under ``relation_types=["calls"]`` Z has *no* callers at any depth: the
    only inbound edge into Z is ``contains``. Y has X (depth 1) and W (depth 2).
    Reproduces the TouchDesigner shape where an operator's structural
    neighbours (contains/docked_to) pulled in Python callers as "indirect
    callers" because the BFS kept expanding through the non-call hop.
    """
    z = "net.py:1-99:network:Z"
    y = "net.py:10-20:operator:Y"
    x = "a.py:1-5:function:X"
    w = "b.py:1-5:function:W"
    for cid in (z, y, x, w):
        _add(graph_storage, cid)
    graph_storage.graph.add_edge(y, z, key="contains", type="contains", confidence=1.0)
    graph_storage.graph.add_edge(x, y, key="calls", type="calls", confidence=1.0)
    graph_storage.graph.add_edge(w, x, key="calls", type="calls", confidence=1.0)
    return graph_storage, z, y, x, w


def test_filtered_inbound_does_not_expand_through_non_matching_edge(
    query_engine, mixed_chain_graph
):
    _, z, _y, _x, _w = mixed_chain_graph
    entries = query_engine.get_relationships(
        z, direction="inbound", relation_types=["calls"], max_depth=3
    )
    assert entries == []


def test_filtered_inbound_still_follows_matching_chain(query_engine, mixed_chain_graph):
    _, _z, y, x, w = mixed_chain_graph
    entries = query_engine.get_relationships(
        y, direction="inbound", relation_types=["calls"], max_depth=3
    )
    assert {(e.chunk_id, e.depth) for e in entries} == {(x, 1), (w, 2)}
    assert all(e.relationship_type == "calls" for e in entries)


def test_unfiltered_inbound_expansion_is_unchanged(query_engine, mixed_chain_graph):
    """No filter → every edge matches → expansion through contains still happens."""
    _, z, y, x, w = mixed_chain_graph
    entries = query_engine.get_relationships(z, direction="inbound", max_depth=3)
    assert {(e.chunk_id, e.depth) for e in entries} == {(y, 1), (x, 2), (w, 3)}


def test_filtered_outbound_does_not_expand_through_non_matching_edge(
    query_engine, graph_storage
):
    """A -uses_type-> B -calls-> C: under a calls filter A has no callees."""
    a, b, c = "a.py:1-5:function:A", "b.py:1-5:class:B", "c.py:1-5:function:C"
    for cid in (a, b, c):
        _add(graph_storage, cid)
    graph_storage.graph.add_edge(
        a, b, key="uses_type", type="uses_type", confidence=1.0
    )
    graph_storage.graph.add_edge(b, c, key="calls", type="calls", confidence=1.0)

    filtered = query_engine.get_relationships(
        a, direction="outbound", relation_types=["calls"], max_depth=3
    )
    assert filtered == []
    unfiltered = query_engine.get_relationships(a, direction="outbound", max_depth=3)
    assert {(e.chunk_id, e.depth) for e in unfiltered} == {(b, 1), (c, 2)}
