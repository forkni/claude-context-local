"""Unit tests for graph enrichment in search results (Phase 2 SSCG).

Tests _get_graph_data_for_chunk() with all 21 relationship types,
max_per_type capping, symbol name lookup, and backward compatibility.
"""

from unittest.mock import MagicMock

import networkx as nx
import pytest

from graph.schema import REVERSE_RELATIONS
from mcp_server.tools.result_view import (
    _enrich_results_with_top_callees,
    _enrich_results_with_top_callers,
    _get_graph_data_for_chunk,
    _get_reverse_relation_name,
)


@pytest.fixture
def mock_index_manager():
    """Create a mock index manager with a real NetworkX graph."""
    manager = MagicMock()
    storage = MagicMock()
    g = nx.DiGraph()

    # Nodes
    g.add_node(
        "auth.py:10-50:function:login", name="login", type="function", file="auth.py"
    )
    g.add_node("models.py:5-30:class:User", name="User", type="class", file="models.py")
    g.add_node(
        "models.py:40-60:class:Admin", name="Admin", type="class", file="models.py"
    )
    g.add_node("db.py:5-20:function:query", name="query", type="function", file="db.py")
    g.add_node(
        "api.py:10-30:function:handle_request",
        name="handle_request",
        type="function",
        file="api.py",
    )
    # Symbol name node (lightweight placeholder)
    g.add_node("User", name="User", type="symbol_name", is_target_name=True)
    g.add_node("hashlib", name="hashlib", type="symbol_name", is_target_name=True)

    # Edges: various relationship types
    g.add_edge(
        "auth.py:10-50:function:login",
        "db.py:5-20:function:query",
        type="calls",
        line=15,
    )
    g.add_edge("auth.py:10-50:function:login", "User", type="uses_type", line=12)
    g.add_edge("auth.py:10-50:function:login", "hashlib", type="imports", line=5)
    g.add_edge("models.py:40-60:class:Admin", "User", type="inherits", line=41)
    g.add_edge(
        "models.py:5-30:class:User", "db.py:5-20:function:query", type="calls", line=10
    )
    g.add_edge(
        "api.py:10-30:function:handle_request",
        "auth.py:10-50:function:login",
        type="calls",
        line=15,
    )

    storage.graph = g
    manager.graph_storage = storage
    return manager


def test_full_relationship_enrichment(mock_index_manager):
    """Verify all relationship types appear in graph data."""
    result = _get_graph_data_for_chunk(
        mock_index_manager, "auth.py:10-50:function:login"
    )
    assert result is not None

    # Outgoing: calls, uses_type, imports
    assert "calls" in result
    assert "db.py:5-20:function:query" in result["calls"]
    assert "uses_type" in result
    assert "User" in result["uses_type"]
    assert "imports" in result
    assert "hashlib" in result["imports"]

    # Incoming: called_by
    assert "called_by" in result
    assert "api.py:10-30:function:handle_request" in result["called_by"]


def test_max_per_type_cap(mock_index_manager):
    """Verify truncation when edges exceed max_per_type."""
    g = mock_index_manager.graph_storage.graph

    # Add 10 callers to login
    for i in range(10):
        caller = f"caller{i}.py:1-10:function:fn{i}"
        g.add_node(caller, name=f"fn{i}", type="function", file=f"caller{i}.py")
        g.add_edge(caller, "auth.py:10-50:function:login", type="calls", line=5)

    result = _get_graph_data_for_chunk(
        mock_index_manager, "auth.py:10-50:function:login", max_per_type=5
    )
    assert result is not None
    assert "called_by" in result
    assert len(result["called_by"]) == 5  # Capped at 5 despite 10+ callers


def test_backward_compat_calls(mock_index_manager):
    """Existing calls/called_by behavior unchanged."""
    result = _get_graph_data_for_chunk(
        mock_index_manager, "auth.py:10-50:function:login"
    )
    assert result is not None
    assert "calls" in result
    assert "db.py:5-20:function:query" in result["calls"]

    # called_by should exist (api.handle_request calls login)
    assert "called_by" in result
    assert "api.py:10-30:function:handle_request" in result["called_by"]


def test_empty_graph_returns_none(mock_index_manager):
    """Verify None returned when chunk has no edges."""
    g = mock_index_manager.graph_storage.graph
    g.add_node(
        "empty.py:1-5:function:noop", name="noop", type="function", file="empty.py"
    )

    result = _get_graph_data_for_chunk(mock_index_manager, "empty.py:1-5:function:noop")
    assert result is None


def test_symbol_name_incoming_edges(mock_index_manager):
    """Verify incoming edges found via bare symbol name."""
    # User chunk should find Admin->User (inherits) via symbol "User"
    result = _get_graph_data_for_chunk(mock_index_manager, "models.py:5-30:class:User")
    assert result is not None

    # The "inherited_by" relation should appear via symbol name "User" lookup
    assert "inherited_by" in result
    assert "models.py:40-60:class:Admin" in result["inherited_by"]


def test_reverse_relation_name_known():
    """Known relation types map to correct reverse names."""
    assert _get_reverse_relation_name("calls") == "called_by"
    assert _get_reverse_relation_name("inherits") == "inherited_by"
    assert _get_reverse_relation_name("uses_type") == "used_as_type_by"
    assert _get_reverse_relation_name("imports") == "imported_by"
    assert _get_reverse_relation_name("decorates") == "decorated_by"
    assert _get_reverse_relation_name("raises") == "raised_by"
    assert _get_reverse_relation_name("catches") == "caught_by"
    assert _get_reverse_relation_name("instantiates") == "instantiated_by"
    assert _get_reverse_relation_name("implements") == "implemented_by"
    assert _get_reverse_relation_name("overrides") == "overridden_by"
    assert _get_reverse_relation_name("assigns_to") == "assigned_by"
    assert _get_reverse_relation_name("reads_from") == "read_by"
    assert _get_reverse_relation_name("defines_constant") == "constant_defined_by"
    assert _get_reverse_relation_name("defines_enum_member") == "enum_member_defined_by"
    assert _get_reverse_relation_name("defines_class_attr") == "class_attr_defined_by"
    assert _get_reverse_relation_name("defines_field") == "field_defined_by"
    assert _get_reverse_relation_name("uses_constant") == "constant_used_by"
    assert _get_reverse_relation_name("uses_default") == "default_used_by"
    assert _get_reverse_relation_name("uses_global") == "global_used_by"
    assert _get_reverse_relation_name("asserts_type") == "type_asserted_by"
    assert (
        _get_reverse_relation_name("uses_context_manager") == "context_manager_used_by"
    )


def test_reverse_relation_name_unknown():
    """Unknown relation types get _by suffix fallback."""
    assert _get_reverse_relation_name("unknown_rel") == "unknown_rel_by"


def test_reverse_relation_map_completeness():
    """Map covers all 21 relationship types."""
    assert len(REVERSE_RELATIONS) == 21


def test_node_not_in_graph(mock_index_manager):
    """Non-existent chunk returns None (not exception)."""
    result = _get_graph_data_for_chunk(
        mock_index_manager, "nonexistent.py:1-5:function:nope"
    )
    assert result is None


# ---------------------------------------------------------------------------
# _enrich_results_with_top_callers (B4 top-caller hints)
# ---------------------------------------------------------------------------


@pytest.fixture
def multidigraph_index_manager():
    """Mock index manager backed by a MultiDiGraph (production graph type)."""
    manager = MagicMock()
    storage = MagicMock()
    g = nx.MultiDiGraph()

    # Target chunk + its bare symbol-name node (unresolved AST edges land there)
    g.add_node(
        "auth.py:10-50:function:login", name="login", type="function", file="auth.py"
    )
    g.add_node("login", name="login", type="symbol_name", is_target_name=True)

    # Callers
    for cid, name in [
        ("api.py:10-30:function:handle_request", "handle_request"),
        ("cli.py:5-15:function:main", "main"),
        ("jobs.py:1-9:function:cron_login", "cron_login"),
    ]:
        g.add_node(cid, name=name, type="function")

    storage.graph = g
    manager.graph_storage = storage
    return manager


def _result(chunk_id="auth.py:10-50:function:login"):
    return {"chunk_id": chunk_id, "kind": "function", "score": 0.9}


def test_top_callers_basic_attach(multidigraph_index_manager):
    """A single calls-edge caller is attached as {name, file}."""
    g = multidigraph_index_manager.graph_storage.graph
    g.add_edge(
        "api.py:10-30:function:handle_request",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    results = _enrich_results_with_top_callers([_result()], multidigraph_index_manager)
    assert results[0]["top_callers"] == [{"name": "handle_request", "file": "api.py"}]


def test_top_callers_cap_at_max(multidigraph_index_manager):
    """Three callers are cut to max_callers=2."""
    g = multidigraph_index_manager.graph_storage.graph
    for cid in [
        "api.py:10-30:function:handle_request",
        "cli.py:5-15:function:main",
        "jobs.py:1-9:function:cron_login",
    ]:
        g.add_edge(cid, "auth.py:10-50:function:login", key="calls", type="calls")
    results = _enrich_results_with_top_callers([_result()], multidigraph_index_manager)
    assert len(results[0]["top_callers"]) == 2


def test_top_callers_confidence_ordering(multidigraph_index_manager):
    """resolver_confidence floats rank ahead of confidence-less edges,
    higher float first."""
    g = multidigraph_index_manager.graph_storage.graph
    g.add_edge(
        "api.py:10-30:function:handle_request",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    g.add_edge(
        "cli.py:5-15:function:main",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
        resolver_confidence=0.9,
    )
    g.add_edge(
        "jobs.py:1-9:function:cron_login",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
        resolver_confidence=0.75,
    )
    results = _enrich_results_with_top_callers([_result()], multidigraph_index_manager)
    assert [c["name"] for c in results[0]["top_callers"]] == ["main", "cron_login"]


def test_top_callers_insertion_order_fallback(multidigraph_index_manager):
    """Without any resolver_confidence floats, discovery order is kept."""
    g = multidigraph_index_manager.graph_storage.graph
    g.add_edge(
        "cli.py:5-15:function:main",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    g.add_edge(
        "api.py:10-30:function:handle_request",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    results = _enrich_results_with_top_callers([_result()], multidigraph_index_manager)
    assert [c["name"] for c in results[0]["top_callers"]] == [
        "main",
        "handle_request",
    ]


def test_top_callers_symbol_name_lookup(multidigraph_index_manager):
    """Unresolved edges targeting the bare symbol-name node are found."""
    g = multidigraph_index_manager.graph_storage.graph
    g.add_edge("cli.py:5-15:function:main", "login", key="calls", type="calls")
    results = _enrich_results_with_top_callers([_result()], multidigraph_index_manager)
    assert results[0]["top_callers"] == [{"name": "main", "file": "cli.py"}]


def test_top_callers_dedup_across_both_lookups(multidigraph_index_manager):
    """A caller with edges to BOTH the chunk_id node and the symbol-name node
    appears once."""
    g = multidigraph_index_manager.graph_storage.graph
    g.add_edge(
        "api.py:10-30:function:handle_request",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    g.add_edge(
        "api.py:10-30:function:handle_request", "login", key="calls", type="calls"
    )
    results = _enrich_results_with_top_callers([_result()], multidigraph_index_manager)
    assert results[0]["top_callers"] == [{"name": "handle_request", "file": "api.py"}]


def test_top_callers_non_calls_edges_filtered(multidigraph_index_manager):
    """Parallel non-calls edges (MultiDiGraph) don't produce caller entries."""
    g = multidigraph_index_manager.graph_storage.graph
    g.add_edge(
        "api.py:10-30:function:handle_request",
        "auth.py:10-50:function:login",
        key="imports",
        type="imports",
    )
    results = _enrich_results_with_top_callers([_result()], multidigraph_index_manager)
    assert "top_callers" not in results[0]


def test_top_callers_self_edge_excluded(multidigraph_index_manager):
    """A recursive self-call does not list the chunk as its own caller."""
    g = multidigraph_index_manager.graph_storage.graph
    g.add_edge(
        "auth.py:10-50:function:login",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    results = _enrich_results_with_top_callers([_result()], multidigraph_index_manager)
    assert "top_callers" not in results[0]


def test_top_callers_missing_node_no_op(multidigraph_index_manager):
    """Chunk absent from the graph: result passes through without the key."""
    results = _enrich_results_with_top_callers(
        [_result("ghost.py:1-5:function:ghost")], multidigraph_index_manager
    )
    assert "top_callers" not in results[0]


def test_top_callers_no_index_manager_no_op():
    """None index_manager (or missing graph storage) is a silent no-op."""
    results = _enrich_results_with_top_callers([_result()], None)
    assert "top_callers" not in results[0]

    manager = MagicMock()
    manager.graph_storage = None
    results = _enrich_results_with_top_callers([_result()], manager)
    assert "top_callers" not in results[0]


def test_top_callers_chunk_tier_fills_quota_skips_symbol_fallback(
    multidigraph_index_manager,
):
    """Fix #2 regression guard: when the chunk-id node alone already yields
    max_callers real edges, the bare symbol-name node (which conflates every
    definition of that name project-wide, per the Fix #2 census) is never
    even consulted -- a bogus symbol-node hint cannot leak in just because it
    happens to sort first by insertion order. Mirrors the live
    ``CleanupQueue._save`` case: two real callers, both correct."""
    g = multidigraph_index_manager.graph_storage.graph
    g.add_edge(
        "api.py:10-30:function:handle_request",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    g.add_edge(
        "cli.py:5-15:function:main",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    # A false hit via the bare symbol node -- would be picked up if the
    # fallback ran, since it would otherwise fill the remaining slot.
    g.add_edge("jobs.py:1-9:function:cron_login", "login", key="calls", type="calls")
    results = _enrich_results_with_top_callers(
        [_result()], multidigraph_index_manager, max_callers=2
    )
    assert [c["name"] for c in results[0]["top_callers"]] == [
        "handle_request",
        "main",
    ]


def test_top_callers_chunk_tier_ranks_above_symbol_tier(multidigraph_index_manager):
    """Fix #2: a chunk-node caller always outranks a symbol-node caller, even
    when the symbol-node edge carries a higher resolver_confidence float --
    the lookup tier is the confidence signal, not the raw float, because
    every symbol-node edge is untagged and can be a false hit."""
    g = multidigraph_index_manager.graph_storage.graph
    # Chunk-node hit: no float at all.
    g.add_edge(
        "api.py:10-30:function:handle_request",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    # Symbol-node hit: a (hypothetically) high float -- still must sort last.
    g.add_edge(
        "cli.py:5-15:function:main",
        "login",
        key="calls",
        type="calls",
        resolver_confidence=0.98,
    )
    results = _enrich_results_with_top_callers(
        [_result()], multidigraph_index_manager, max_callers=2
    )
    assert [c["name"] for c in results[0]["top_callers"]] == [
        "handle_request",
        "main",
    ]


def test_top_callers_symbol_fallback_fills_remaining_slots_only(
    multidigraph_index_manager,
):
    """When the chunk-id node yields fewer than max_callers, the symbol-node
    fallback fills the rest, sorted after every chunk-tier candidate."""
    g = multidigraph_index_manager.graph_storage.graph
    g.add_edge(
        "api.py:10-30:function:handle_request",
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
    )
    g.add_edge("cli.py:5-15:function:main", "login", key="calls", type="calls")
    g.add_edge("jobs.py:1-9:function:cron_login", "login", key="calls", type="calls")
    results = _enrich_results_with_top_callers(
        [_result()], multidigraph_index_manager, max_callers=2
    )
    names = [c["name"] for c in results[0]["top_callers"]]
    assert names[0] == "handle_request"  # chunk tier always first
    assert len(names) == 2


# ---------------------------------------------------------------------------
# _enrich_results_with_top_callees (A5 top-callee hints)
# ---------------------------------------------------------------------------

_CALLER = "svc.py:1-40:function:run"


@pytest.fixture
def callee_index_manager():
    """MultiDiGraph with one caller chunk, three callee chunks, one phantom."""
    manager = MagicMock()
    storage = MagicMock()
    g = nx.MultiDiGraph()
    g.add_node(_CALLER, name="run", type="function", file="svc.py")
    for cid, name in [
        ("auth.py:10-50:function:login", "login"),
        ("db.py:5-15:function:connect", "connect"),
        ("log.py:1-9:function:emit", "emit"),
    ]:
        g.add_node(cid, name=name, type="function")
    g.add_node("fmt", name="fmt", type="symbol_name", is_target_name=True)
    storage.graph = g
    manager.graph_storage = storage
    return manager


def test_top_callees_basic_attach(callee_index_manager):
    g = callee_index_manager.graph_storage.graph
    g.add_edge(_CALLER, "auth.py:10-50:function:login", key="calls", type="calls")
    results = _enrich_results_with_top_callees([_result(_CALLER)], callee_index_manager)
    assert results[0]["top_callees"] == [{"name": "login", "file": "auth.py"}]


def test_top_callees_cap_at_max(callee_index_manager):
    g = callee_index_manager.graph_storage.graph
    for cid in (
        "auth.py:10-50:function:login",
        "db.py:5-15:function:connect",
        "log.py:1-9:function:emit",
    ):
        g.add_edge(_CALLER, cid, key="calls", type="calls")
    results = _enrich_results_with_top_callees([_result(_CALLER)], callee_index_manager)
    assert len(results[0]["top_callees"]) == 2


def test_top_callees_confidence_ordering(callee_index_manager):
    """Float-confident edges rank first within the chunk tier."""
    g = callee_index_manager.graph_storage.graph
    g.add_edge(
        _CALLER,
        "auth.py:10-50:function:login",
        key="calls",
        type="calls",
        resolver_confidence=0.7,
    )
    g.add_edge(
        _CALLER,
        "db.py:5-15:function:connect",
        key="calls",
        type="calls",
        resolver_confidence=0.98,
    )
    results = _enrich_results_with_top_callees([_result(_CALLER)], callee_index_manager)
    assert [c["name"] for c in results[0]["top_callees"]] == ["connect", "login"]


def test_top_callees_phantom_targets_rank_below_chunks(callee_index_manager):
    """A phantom (bare symbol) target is the lower tier even when the chunk
    edge has no confidence, and renders with an empty file."""
    g = callee_index_manager.graph_storage.graph
    g.add_edge(_CALLER, "fmt", key="calls", type="calls", resolver_confidence=0.9)
    g.add_edge(_CALLER, "auth.py:10-50:function:login", key="calls", type="calls")
    results = _enrich_results_with_top_callees([_result(_CALLER)], callee_index_manager)
    assert results[0]["top_callees"] == [
        {"name": "login", "file": "auth.py"},
        {"name": "fmt", "file": ""},
    ]


def test_top_callees_phantom_only(callee_index_manager):
    g = callee_index_manager.graph_storage.graph
    g.add_edge(_CALLER, "fmt", key="calls", type="calls")
    results = _enrich_results_with_top_callees([_result(_CALLER)], callee_index_manager)
    assert results[0]["top_callees"] == [{"name": "fmt", "file": ""}]


def test_top_callees_non_calls_edges_filtered(callee_index_manager):
    g = callee_index_manager.graph_storage.graph
    g.add_edge(_CALLER, "auth.py:10-50:function:login", key="imports", type="imports")
    results = _enrich_results_with_top_callees([_result(_CALLER)], callee_index_manager)
    assert "top_callees" not in results[0]


def test_top_callees_self_edge_excluded(callee_index_manager):
    g = callee_index_manager.graph_storage.graph
    g.add_edge(_CALLER, _CALLER, key="calls", type="calls")
    results = _enrich_results_with_top_callees([_result(_CALLER)], callee_index_manager)
    assert "top_callees" not in results[0]


def test_top_callees_dedup_parallel_edges(callee_index_manager):
    """Two parallel calls edges to the same target yield one hint."""
    g = callee_index_manager.graph_storage.graph
    g.add_edge(_CALLER, "auth.py:10-50:function:login", key="calls", type="calls")
    g.add_edge(_CALLER, "auth.py:10-50:function:login", key="calls2", type="calls")
    results = _enrich_results_with_top_callees([_result(_CALLER)], callee_index_manager)
    assert results[0]["top_callees"] == [{"name": "login", "file": "auth.py"}]


def test_top_callees_missing_node_no_op(callee_index_manager):
    results = _enrich_results_with_top_callees(
        [_result("nope.py:1-2:function:absent")], callee_index_manager
    )
    assert "top_callees" not in results[0]


def test_top_callees_no_index_manager_no_op():
    results = _enrich_results_with_top_callees([_result(_CALLER)], None)
    assert "top_callees" not in results[0]


def test_top_callees_does_not_touch_callers(callee_index_manager):
    """Out-edges only: an in-edge into the result never appears as a callee."""
    g = callee_index_manager.graph_storage.graph
    g.add_edge("auth.py:10-50:function:login", _CALLER, key="calls", type="calls")
    results = _enrich_results_with_top_callees([_result(_CALLER)], callee_index_manager)
    assert "top_callees" not in results[0]
