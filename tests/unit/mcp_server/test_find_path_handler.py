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
    mock_searcher.dense_index.graph_storage = None  # falsy → triggers the guard

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
    mock_searcher = Mock()
    mock_searcher.dense_index.graph_storage = mock_gs

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
    """When find_path returns None, handler returns path_found=False with a hint message."""
    mock_gs = Mock()
    mock_gs.get_node_data.return_value = None
    mock_gs.graph.__contains__ = Mock(return_value=False)
    mock_searcher = Mock()
    mock_searcher.dense_index.graph_storage = mock_gs

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
                "source_chunk_id": "file.py:1-10:function:source_fn",
                "target_chunk_id": "file.py:20-30:function:target_fn",
            }
        )

    assert result["path_found"] is False
    assert "No path found" in result["system_message"]
    assert result["source"]["exists_in_graph"] is False
    assert result["target"]["exists_in_graph"] is False


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
    mock_searcher.index_manager.symbol_cache.get_by_symbol_name.return_value = None
    mock_searcher.dense_index.graph_storage = mock_gs
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
