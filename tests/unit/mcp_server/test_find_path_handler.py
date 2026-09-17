"""Unit tests for handle_find_path handler.

Self-contained: does not rely on autouse fixtures from test_tool_handlers.py.
"""

from unittest.mock import Mock, patch

import pytest

from mcp_server.tools.search_handlers import handle_find_path


@pytest.fixture
def dec_state():
    """Mock state with current_project set — satisfies @require_indexed_project."""
    state = Mock()
    state.current_project = "/test/project"
    return state


@pytest.fixture
def passthrough_metadata():
    """MetadataStore mock whose normalize_chunk_id is a no-op pass-through."""
    ms = Mock()
    ms.normalize_chunk_id.side_effect = lambda x: x
    return ms


@pytest.mark.asyncio
async def test_missing_source_returns_error(dec_state):
    """Returns error dict when neither source nor source_chunk_id is supplied."""
    with patch("mcp_server.tools.decorators.get_state", return_value=dec_state):
        result = await handle_find_path(
            {"target_chunk_id": "file.py:20-30:function:target_fn"}
        )

    assert result.get("error") == "Missing source"


@pytest.mark.asyncio
async def test_missing_target_returns_error(dec_state, passthrough_metadata):
    """Returns error dict when neither target nor target_chunk_id is supplied."""
    with (
        patch("mcp_server.tools.decorators.get_state", return_value=dec_state),
        patch("mcp_server.tools.search_handlers.MetadataStore", passthrough_metadata),
        patch("mcp_server.tools.search_handlers.get_searcher"),
    ):
        result = await handle_find_path(
            {"source_chunk_id": "file.py:1-10:function:source_fn"}
        )

    assert result.get("error") == "Missing target"


@pytest.mark.asyncio
async def test_graph_not_available_returns_error(dec_state, passthrough_metadata):
    """Returns error when graph_storage is absent from the searcher."""
    mock_searcher = Mock()
    mock_searcher.graph_storage = None  # falsy → triggers the guard

    with (
        patch("mcp_server.tools.decorators.get_state", return_value=dec_state),
        patch("mcp_server.tools.search_handlers.MetadataStore", passthrough_metadata),
        patch(
            "mcp_server.tools.search_handlers.get_searcher", return_value=mock_searcher
        ),
    ):
        result = await handle_find_path(
            {
                "source_chunk_id": "file.py:1-10:function:source_fn",
                "target_chunk_id": "file.py:20-30:function:target_fn",
            }
        )

    assert result.get("error") == "Graph not available"


@pytest.mark.asyncio
async def test_path_found_attaches_endpoints_and_system_message(
    dec_state, passthrough_metadata
):
    """When find_path returns a result, handler attaches source/target and system_message."""
    source_node = {"name": "source_fn", "file": "file.py"}
    target_node = {"name": "target_fn", "file": "file.py"}
    path_result = {
        "path_found": True,
        "path_length": 2,
        "path": [{"node": source_node}, {"node": target_node}],
        "edge_types_traversed": ["calls"],
    }

    mock_gs = Mock()
    mock_gs.get_node_data.return_value = None
    # Both supplied chunk_ids are already graph members — skip H5 recovery.
    mock_gs.graph.__contains__ = Mock(return_value=True)
    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs

    mock_engine = Mock()
    mock_engine.find_path.return_value = path_result

    with (
        patch("mcp_server.tools.decorators.get_state", return_value=dec_state),
        patch("mcp_server.tools.search_handlers.MetadataStore", passthrough_metadata),
        patch(
            "mcp_server.tools.search_handlers.get_searcher", return_value=mock_searcher
        ),
        patch("graph.graph_queries.GraphQueryEngine", return_value=mock_engine),
    ):
        result = await handle_find_path(
            {
                "source_chunk_id": "file.py:1-10:function:source_fn",
                "target_chunk_id": "file.py:20-30:function:target_fn",
            }
        )

    assert result["path_found"] is True
    assert result["source"] == source_node
    assert result["target"] == target_node
    assert "Found path of length 2" in result["system_message"]
    assert "calls" in result["system_message"]


@pytest.mark.asyncio
async def test_no_path_returns_path_found_false_and_hint(
    dec_state, passthrough_metadata
):
    """When find_path returns None for two endpoints that DO exist in the
    graph, handler returns path_found=False with a hint message and
    exists_in_graph=True for both -- a genuine "not connected" answer.

    Post-H5-fix, a chunk_id that is *not* a graph member never reaches this
    branch: it is either recovered via derive_symbol_hint() beforehand or
    the handler returns a structured error, so exists_in_graph is always
    True by the time find_path has actually run. See
    test_handle_find_path_unresolvable_chunk_id_returns_structured_error in
    test_tool_handlers.py for the "doesn't exist" case this replaces.
    """
    source_id = "file.py:1-10:function:source_fn"
    target_id = "file.py:20-30:function:target_fn"

    mock_gs = Mock()
    mock_gs.get_node_data.return_value = None
    mock_gs.graph.__contains__ = Mock(
        side_effect=lambda cid: cid in {source_id, target_id}
    )
    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs

    mock_engine = Mock()
    mock_engine.find_path.return_value = None  # no path found

    with (
        patch("mcp_server.tools.decorators.get_state", return_value=dec_state),
        patch("mcp_server.tools.search_handlers.MetadataStore", passthrough_metadata),
        patch(
            "mcp_server.tools.search_handlers.get_searcher", return_value=mock_searcher
        ),
        patch("graph.graph_queries.GraphQueryEngine", return_value=mock_engine),
    ):
        result = await handle_find_path(
            {
                "source_chunk_id": source_id,
                "target_chunk_id": target_id,
            }
        )

    assert result["path_found"] is False
    assert "No path found" in result["system_message"]
    assert result["source"]["exists_in_graph"] is True
    assert result["target"]["exists_in_graph"] is True


@pytest.mark.asyncio
async def test_source_symbol_unresolved_returns_error(dec_state, passthrough_metadata):
    """Unresolvable source symbol returns a responses.error() envelope with
    path_found=False preserved (P3-B: was a hand-rolled dict)."""
    mock_gs = Mock()
    mock_gs.get_nodes_by_name.return_value = []
    mock_gs.graph.nodes.return_value = []

    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs
    mock_searcher.search.return_value = []  # all resolution tiers miss

    with (
        patch("mcp_server.tools.decorators.get_state", return_value=dec_state),
        patch("mcp_server.tools.search_handlers.MetadataStore", passthrough_metadata),
        patch(
            "mcp_server.tools.search_handlers.get_searcher", return_value=mock_searcher
        ),
    ):
        result = await handle_find_path(
            {
                "source": "nonexistent",
                "target_chunk_id": "file.py:20-30:function:target_fn",
            }
        )

    assert result == {
        "error": "Could not resolve source symbol: nonexistent",
        "path_found": False,
    }


@pytest.mark.asyncio
async def test_target_symbol_unresolved_returns_error(dec_state, passthrough_metadata):
    """Unresolvable target symbol returns a responses.error() envelope with
    path_found=False preserved (P3-B: was a hand-rolled dict)."""
    mock_gs = Mock()
    mock_gs.get_nodes_by_name.return_value = []
    mock_gs.graph.nodes.return_value = []
    # source_chunk_id is already a graph member — skip H5 recovery so the
    # target-symbol failure below is what's under test.
    mock_gs.graph.__contains__ = Mock(return_value=True)

    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs
    mock_searcher.search.return_value = []  # all resolution tiers miss

    with (
        patch("mcp_server.tools.decorators.get_state", return_value=dec_state),
        patch("mcp_server.tools.search_handlers.MetadataStore", passthrough_metadata),
        patch(
            "mcp_server.tools.search_handlers.get_searcher", return_value=mock_searcher
        ),
    ):
        result = await handle_find_path(
            {
                "source_chunk_id": "file.py:1-10:function:source_fn",
                "target": "nonexistent",
            }
        )

    assert result == {
        "error": "Could not resolve target symbol: nonexistent",
        "path_found": False,
    }


@pytest.mark.asyncio
async def test_symbol_resolution_via_semantic_search(dec_state):
    """handler resolves bare symbol names through semantic search as last resort."""
    source_result = Mock()
    source_result.metadata = {"name": "source_fn"}
    source_result.chunk_id = "file.py:1-10:function:source_fn"

    target_result = Mock()
    target_result.metadata = {"name": "target_fn"}
    target_result.chunk_id = "file.py:20-30:function:target_fn"

    mock_gs = Mock()
    # Graph name lookup returns nothing → forces semantic search fallback
    mock_gs.get_nodes_by_name.return_value = []
    mock_gs.graph.nodes.return_value = []
    mock_gs.get_node_data.return_value = None
    mock_gs.graph.__contains__ = Mock(return_value=False)

    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs
    # Return different results for source vs target resolution calls
    mock_searcher.search.side_effect = [[source_result], [target_result]]

    mock_engine = Mock()
    mock_engine.find_path.return_value = None

    with (
        patch("mcp_server.tools.decorators.get_state", return_value=dec_state),
        patch(
            "mcp_server.tools.search_handlers.get_searcher", return_value=mock_searcher
        ),
        patch("graph.graph_queries.GraphQueryEngine", return_value=mock_engine),
    ):
        result = await handle_find_path({"source": "source_fn", "target": "target_fn"})

    assert result["source_resolved"]["resolution_method"] == "semantic_search"
    assert result["target_resolved"]["resolution_method"] == "semantic_search"
    assert result["source_resolved"]["chunk_id"] == "file.py:1-10:function:source_fn"


# ---------------------------------------------------------------------------
# Direct unit tests for _resolve_symbol_to_chunk_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_tier1_graph_name_exact():
    """Tier-1: get_nodes_by_name hit returns first match with graph_lookup method."""
    from mcp_server.tools.search_handlers import _resolve_symbol_to_chunk_id

    mock_gs = Mock()
    mock_gs.get_nodes_by_name.return_value = ["file.py:1-10:function:my_func"]

    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs

    chunk_id, info = await _resolve_symbol_to_chunk_id("my_func", mock_searcher)

    assert chunk_id == "file.py:1-10:function:my_func"
    assert info["resolution_method"] == "graph_lookup"


@pytest.mark.asyncio
async def test_resolve_tier1_suffix_colon():
    """Tier-1: suffix scan matches ':name' pattern when name index returns nothing."""
    from mcp_server.tools.search_handlers import _resolve_symbol_to_chunk_id

    mock_gs = Mock()
    mock_gs.get_nodes_by_name.return_value = []
    mock_gs.graph.nodes.return_value = [
        "file.py:1-10:function:other",
        "file.py:11-20:function:my_func",  # ends with ":my_func"
    ]

    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs

    chunk_id, info = await _resolve_symbol_to_chunk_id("my_func", mock_searcher)

    assert chunk_id == "file.py:11-20:function:my_func"
    assert info["resolution_method"] == "graph_lookup"


@pytest.mark.asyncio
async def test_resolve_tier1_suffix_dot():
    """Tier-1: suffix scan matches '.name' pattern for class-qualified chunk_ids.

    Regression guard: the old inline code only checked ':{name}', missing
    class-qualified IDs like 'ClassName.method_name'.
    """
    from mcp_server.tools.search_handlers import _resolve_symbol_to_chunk_id

    mock_gs = Mock()
    mock_gs.get_nodes_by_name.return_value = []
    mock_gs.graph.nodes.return_value = [
        "other_node",
        "MyClass.my_method",  # ends with ".my_method"
    ]

    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs

    chunk_id, info = await _resolve_symbol_to_chunk_id("my_method", mock_searcher)

    assert chunk_id == "MyClass.my_method"
    assert info["resolution_method"] == "graph_lookup"


@pytest.mark.asyncio
async def test_resolve_tier2_semantic_name_match_preferred():
    """Tier-2: semantic result whose name matches the symbol is preferred over first."""
    from mcp_server.tools.search_handlers import _resolve_symbol_to_chunk_id

    first_result = Mock()
    first_result.metadata = {"name": "other"}
    first_result.chunk_id = "file.py:1-5:function:other"

    exact_match = Mock()
    exact_match.metadata = {"name": "my_func"}
    exact_match.chunk_id = "file.py:10-20:function:my_func"

    mock_gs = Mock()
    mock_gs.get_nodes_by_name.return_value = []
    mock_gs.graph.nodes.return_value = []

    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs
    mock_searcher.search.return_value = [first_result, exact_match]

    chunk_id, info = await _resolve_symbol_to_chunk_id("my_func", mock_searcher)

    assert chunk_id == "file.py:10-20:function:my_func"
    assert info["resolution_method"] == "semantic_search"


@pytest.mark.asyncio
async def test_resolve_not_found_returns_none_none():
    """All tiers exhausted → returns (None, None)."""
    from mcp_server.tools.search_handlers import _resolve_symbol_to_chunk_id

    mock_gs = Mock()
    mock_gs.get_nodes_by_name.return_value = []
    mock_gs.graph.nodes.return_value = []

    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs
    mock_searcher.search.return_value = []

    chunk_id, info = await _resolve_symbol_to_chunk_id("nonexistent", mock_searcher)

    assert chunk_id is None
    assert info is None


@pytest.mark.asyncio
async def test_resolve_tier1_prefers_real_language_over_td_operator():
    """ADR-0062 fence: a TD operator sharing the name stays reachable but a
    Python definition wins when both exist."""
    from unittest.mock import MagicMock

    from mcp_server.tools.search_handlers import _resolve_symbol_to_chunk_id

    td = "Graph/net.tdgraph.json:10-20:operator:view"
    py = "views.py:1-5:function:view"
    langs = {td: "td_network", py: "python"}

    mock_gs = MagicMock()
    mock_gs.get_nodes_by_name.return_value = [td, py]
    mock_gs.get_node_language.side_effect = lambda cid: langs.get(cid, "")

    mock_searcher = Mock()
    mock_searcher.graph_storage = mock_gs

    chunk_id, info = await _resolve_symbol_to_chunk_id("view", mock_searcher)
    assert chunk_id == py
    assert info["resolution_method"] == "graph_lookup"

    mock_gs.get_nodes_by_name.return_value = [td]
    chunk_id, _ = await _resolve_symbol_to_chunk_id("view", mock_searcher)
    assert chunk_id == td
