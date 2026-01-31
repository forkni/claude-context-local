"""Unit tests for graph enrichment in search results (Phase 2 SSCG).

Tests _get_graph_data_for_chunk() with all 21 relationship types,
max_per_type capping, symbol name lookup, and backward compatibility.
"""

from unittest.mock import MagicMock

import networkx as nx
import pytest

from mcp_server.tools.search_handlers import (
    _REVERSE_RELATION_MAP,
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
    assert len(_REVERSE_RELATION_MAP) == 21


def test_node_not_in_graph(mock_index_manager):
    """Non-existent chunk returns None (not exception)."""
    result = _get_graph_data_for_chunk(
        mock_index_manager, "nonexistent.py:1-5:function:nope"
    )
    assert result is None
