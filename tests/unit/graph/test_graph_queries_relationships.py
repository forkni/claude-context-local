"""Unit tests for GraphQueryEngine.get_relationships() parallel-edge handling.

Covers the parallel-edge-collapse fix (ADR-0027): a (u, v) pair connected by
more than one relationship type must expose every type via
RelationshipEntry.parallel_edges, not just the primary edge get_edge_data()
would pick before this fix -- and it must do so on both the filtered and the
unfiltered path, since verification showed find_connections's normal
(unfiltered) call was the one silently losing relationships.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from graph.graph_queries import GraphQueryEngine
from graph.graph_storage import CodeGraphStorage
from graph.schema import NODE_ATTR_IS_TARGET_NAME, NODE_ATTR_TYPE, NODE_TYPE_SYMBOL_NAME


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


# ---------------------------------------------------------------------------
# TD chunks get no symbol-name lookup variants (cross-language name collision)
# ---------------------------------------------------------------------------


@pytest.fixture
def name_collision_graph(graph_storage):
    """A TD operator named ``Logger`` next to a Python class ``Logger``.

    Python call edges target the *symbol name* node ("Logger"), which is how
    ``_node_variants`` finds a class's callers. The TD operator must not pick
    those callers up just because its bare name is the same string. TD edges
    (here ``scripted_by``) target full chunk ids and must still resolve.
    """
    td_op = "Graph/net.tdgraph.json:10-20:operator:Logger"
    td_host = "Graph/net.tdgraph.json:30-40:operator:timer1"
    py_cls = "log.py:1-20:class:Logger"
    py_main = "main.py:1-10:function:main"
    graph_storage.add_node(
        td_op, "Logger", "operator", "Graph/net.tdgraph.json", language="td_network"
    )
    graph_storage.add_node(
        td_host, "timer1", "operator", "Graph/net.tdgraph.json", language="td_network"
    )
    graph_storage.add_node(py_cls, "Logger", "class", "log.py", language="python")
    graph_storage.add_node(py_main, "main", "function", "main.py", language="python")
    graph_storage.graph.add_node("Logger")  # symbol-name node Python edges target
    graph_storage.graph.add_edge(py_main, "Logger", key="calls", type="calls")
    graph_storage.graph.add_edge(
        td_host, td_op, key="scripted_by", type="scripted_by", confidence=1.0
    )
    return td_op, td_host, py_cls, py_main


def test_td_operator_gets_only_its_own_id_as_variant(
    query_engine, name_collision_graph
):
    td_op, _, py_cls, _ = name_collision_graph
    assert query_engine._node_variants(td_op) == [td_op]
    assert query_engine._node_variants(py_cls) == [py_cls, "Logger"]


def test_td_operator_does_not_inherit_python_callers_of_same_name(
    query_engine, name_collision_graph
):
    td_op, _, _, _ = name_collision_graph
    callers = query_engine.get_relationships(
        td_op, direction="inbound", relation_types=["calls"], max_depth=3
    )
    assert callers == []


def test_python_class_still_finds_callers_via_symbol_variant(
    query_engine, name_collision_graph
):
    _, _, py_cls, py_main = name_collision_graph
    callers = query_engine.get_relationships(
        py_cls, direction="inbound", relation_types=["calls"], max_depth=1
    )
    assert [(e.chunk_id, e.depth) for e in callers] == [(py_main, 1)]


def test_td_full_id_edges_still_resolve_without_variants(
    query_engine, name_collision_graph
):
    td_op, td_host, _, _ = name_collision_graph
    inbound = query_engine.get_relationships(td_op, direction="inbound", max_depth=1)
    assert [(e.chunk_id, e.relationship_type) for e in inbound] == [
        (td_host, "scripted_by")
    ]


def test_kind_fallback_when_td_node_is_absent_from_graph(query_engine):
    """A TD chunk id that has no graph node (nothing links to it) still gets
    no variants -- the kind segment is enough to classify it."""
    missing = "Graph/net.tdgraph.json:1-5:operator:Logger"
    assert query_engine._node_variants(missing) == [missing]
    py_missing = "log.py:1-5:class:Logger"
    assert query_engine._node_variants(py_missing) == [py_missing, "Logger"]


# ---------------------------------------------------------------------------
# Phantom-node shadowing of resolved call edges (D1 fix)
#
# One call site produces two edges from the same caller: a resolved edge to
# the real chunk (index-time resolution, carries the real "confidence" tag)
# and a phantom edge to the bare symbol name (base AST extraction, no
# "confidence" key at all -- see CodeGraphStorage.add_call_edge). Both edges
# share the same caller, so the traversal's caller-keyed first-visit dedup
# races between them. Reproduces the UndoStack::push defect: the resolver
# correctly tagged the edge "ambiguous", but querying inbound "calls"
# returned it as "exact" whenever the phantom edge was visited first.
# ---------------------------------------------------------------------------


def _add_phantom_call_target(storage, name):
    """Mirror CodeGraphStorage.add_call_edge's placeholder-node creation for
    an unresolved callee (NODE_TYPE_SYMBOL_NAME / NODE_ATTR_IS_TARGET_NAME)."""
    storage.graph.add_node(
        name,
        **{
            "name": name,
            NODE_ATTR_TYPE: NODE_TYPE_SYMBOL_NAME,
            NODE_ATTR_IS_TARGET_NAME: True,
            "file": "",
            "language": "",
        },
    )


@pytest.fixture
def phantom_shadow_graph(graph_storage):
    caller = "caller.py:1-10:function:do_thing"
    real_callee = "undo.py:1-20:method:UndoStack.push"
    phantom = "push"
    graph_storage.add_node(
        caller, "do_thing", "function", "caller.py", language="python"
    )
    graph_storage.add_node(real_callee, "push", "method", "undo.py", language="python")
    _add_phantom_call_target(graph_storage, phantom)

    graph_storage.graph.add_edge(
        caller,
        real_callee,
        key="calls",
        type="calls",
        line=3,
        is_method=True,
        is_resolved=True,
        confidence="ambiguous",
    )
    graph_storage.graph.add_edge(
        caller,
        phantom,
        key="calls",
        type="calls",
        line=3,
        is_method=True,
        is_resolved=False,
        # No confidence key -- exactly what add_call_edge(is_resolved=False) leaves.
    )
    return graph_storage, caller, real_callee, phantom


def test_inbound_confidence_survives_phantom_shadow_race(
    query_engine, phantom_shadow_graph
):
    """The resolved edge's "ambiguous" tag must win regardless of which of
    the two same-caller edges the traversal visits first (in-process repro,
    at whatever hash seed this pytest process happens to have).

    _traverse_inbound's race is over ``current_query``, a *set* of 2-3
    query-node variants rebuilt via a set comprehension on every call -- its
    iteration order depends on CPython's per-process, siphash-randomized
    string hashing, not on graph/edge insertion order. That makes this
    in-process assertion pass or fail depending on PYTHONHASHSEED, which
    nothing in this repo's unit-test harness pins (see
    test_inbound_confidence_survives_phantom_shadow_race_hash_seed_pinned
    below for the seed-independent version of this same repro, which is the
    actual regression gate)."""
    _storage, caller, real_callee, _phantom = phantom_shadow_graph

    entries = query_engine.get_relationships(
        real_callee, direction="inbound", relation_types=["calls"], max_depth=1
    )

    assert len(entries) == 1
    assert entries[0].chunk_id == caller
    assert entries[0].edge_data.get("confidence") == "ambiguous"


_PHANTOM_SHADOW_REPRO_SCRIPT = """
import sys
sys.path.insert(0, {project_root!r})

from graph.graph_queries import GraphQueryEngine
from graph.graph_storage import CodeGraphStorage
from graph.schema import NODE_ATTR_IS_TARGET_NAME, NODE_ATTR_TYPE, NODE_TYPE_SYMBOL_NAME

import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as temp_dir:
    storage = CodeGraphStorage(project_id="test_project", storage_dir=Path(temp_dir))

    caller = "caller.py:1-10:function:do_thing"
    real_callee = "undo.py:1-20:method:UndoStack.push"
    phantom = "push"
    storage.add_node(caller, "do_thing", "function", "caller.py", language="python")
    storage.add_node(real_callee, "push", "method", "undo.py", language="python")
    storage.graph.add_node(
        phantom,
        **{{
            "name": phantom,
            NODE_ATTR_TYPE: NODE_TYPE_SYMBOL_NAME,
            NODE_ATTR_IS_TARGET_NAME: True,
            "file": "",
            "language": "",
        }},
    )
    storage.graph.add_edge(
        caller, real_callee, key="calls", type="calls", line=3,
        is_method=True, is_resolved=True, confidence="ambiguous",
    )
    storage.graph.add_edge(
        caller, phantom, key="calls", type="calls", line=3,
        is_method=True, is_resolved=False,
    )

    engine = GraphQueryEngine(storage)
    entries = engine.get_relationships(
        real_callee, direction="inbound", relation_types=["calls"], max_depth=1
    )
    assert len(entries) == 1, entries
    print(entries[0].edge_data.get("confidence"))
"""


@pytest.mark.parametrize("hash_seed", ["2", "7"])
def test_inbound_confidence_survives_phantom_shadow_race_hash_seed_pinned(hash_seed):
    """Seed-independent regression gate for the same race as the test above.

    Python randomizes str hashing per-process unless PYTHONHASHSEED is pinned
    before interpreter startup -- something no fixture or monkeypatch can
    control retroactively, because the actual race site
    (GraphQueryEngine._traverse_inbound's ``current_query: set[str] = {v for
    v in origin_set if ...}``) is a set *comprehension*, compiled straight to
    BUILD_SET/SET_ADD bytecode -- it never calls the module-level ``set``
    name, so monkeypatching ``graph_queries.set`` cannot intercept it either.
    A subprocess with PYTHONHASHSEED pinned is the only mechanically correct
    way to make this deterministic.

    Seeds "2" and "7" were empirically confirmed (by sweeping
    PYTHONHASHSEED=0..10 against this exact fixture) to reproduce the bug
    pre-fix: the phantom edge wins the race and the caller is reported with
    confidence 1.0 instead of "ambiguous". After D1 lands (_authority_order
    sorts query nodes real-chunk-before-phantom, then lexicographically) the
    outcome no longer depends on hash order at all, so this stays green on
    every seed -- these two are not "the seeds that happen to work", they are
    two of many that demonstrate the pre-fix failure.
    """
    project_root = str(Path(__file__).resolve().parents[3])
    script = _PHANTOM_SHADOW_REPRO_SCRIPT.format(project_root=project_root)

    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "PYTHONHASHSEED": hash_seed},
        capture_output=True,
        text=True,
        timeout=30,
        cwd=project_root,
    )

    assert result.returncode == 0, (
        f"seed={hash_seed}: repro script failed\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert result.stdout.strip().splitlines()[-1] == "ambiguous", (
        f"seed={hash_seed}: expected confidence 'ambiguous', "
        f"got stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_authority_order_ranks_real_chunk_before_phantom_both_input_orders(
    query_engine, phantom_shadow_graph
):
    """_authority_order must put the real chunk node before the phantom
    symbol-name node regardless of input order -- the fix must not depend on
    set/hash iteration order to be deterministic."""
    _storage, _caller, real_callee, phantom = phantom_shadow_graph

    assert query_engine._authority_order([real_callee, phantom]) == [
        real_callee,
        phantom,
    ]
    assert query_engine._authority_order([phantom, real_callee]) == [
        real_callee,
        phantom,
    ]
