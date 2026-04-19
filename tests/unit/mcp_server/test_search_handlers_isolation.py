"""Tests that handle_search_code does not mutate the get_search_config() singleton.

get_search_config() returns a process-wide cached singleton. Any mutation of that
object races with concurrent requests. The handler must deep-copy before mutating.
"""

import copy
from unittest.mock import Mock, patch

import pytest

from mcp_server import tool_handlers
from search.config import SearchConfig


def _make_hybrid_searcher_mock():
    """Return a minimal Mock that passes the HybridSearcher is_ready / type checks."""
    from search.hybrid_searcher import HybridSearcher

    mock_searcher = Mock(spec=HybridSearcher)
    mock_searcher.is_ready = True
    mock_searcher.bm25_weight = 0.35
    mock_searcher.dense_weight = 0.65

    mock_faiss = Mock()
    mock_faiss.ntotal = 100
    mock_dense = Mock()
    mock_dense.index = mock_faiss
    mock_dense.graph_storage = None
    mock_searcher.dense_index = mock_dense

    mock_searcher.search = Mock(return_value=[])
    return mock_searcher


def _make_intent_decision(intent_value: str, bm25: float = 0.3, dense: float = 0.7):
    """Build a minimal IntentDecision-shaped mock."""

    decision = Mock()
    decision.intent = Mock()
    decision.intent.value = intent_value
    decision.confidence = 0.95
    decision.reason = "test"
    decision.suggested_params = {
        "bm25_weight": bm25,
        "dense_weight": dense,
        "search_mode": "hybrid",
    }
    return decision


@pytest.mark.asyncio
async def test_handle_search_code_does_not_mutate_config_singleton():
    """handle_search_code must not write to the SearchConfig singleton.

    Exercises all 5 mutation-prone code paths:
    - ego_graph settings (ego_graph_enabled=True)
    - intent-adaptive ego threshold
    - parent_retrieval (include_parent=True)
    - intent edge weights (local intent → INTENT_EDGE_WEIGHT_PROFILES["local"])
    - bm25/dense weight override (via suggested_params)
    """
    mock_searcher = _make_hybrid_searcher_mock()
    intent_decision = _make_intent_decision("local", bm25=0.7, dense=0.3)

    # Capture the real singleton before the call
    with patch("mcp_server.tools.search_handlers.get_search_config") as mock_get_cfg:
        original_cfg = SearchConfig()  # fresh default config
        mock_get_cfg.return_value = original_cfg
        snapshot_before = copy.deepcopy(original_cfg)

        with (
            patch(
                "mcp_server.tools.search_handlers.get_searcher",
                return_value=mock_searcher,
            ),
            patch("mcp_server.tools.search_handlers.get_state") as mock_state,
            patch("mcp_server.tools.search_handlers.get_config") as mock_app_cfg,
            patch("mcp_server.tools.search_handlers.get_config_manager") as mock_cm,
            patch("mcp_server.tools.search_handlers.IntentClassifier") as mock_ic_cls,
        ):
            mock_state.return_value.current_project = "/test"
            mock_state.return_value.searcher = None

            app_cfg = Mock()
            app_cfg.intent.enabled = True
            app_cfg.intent.semantic_enabled = False
            app_cfg.intent.confidence_threshold = 0.0
            app_cfg.intent.log_classifications = False
            app_cfg.performance.use_parallel_search = False
            mock_app_cfg.return_value = app_cfg

            mock_cm.return_value.get_search_mode_for_query.return_value = "hybrid"

            ic_instance = Mock()
            ic_instance.classify.return_value = intent_decision
            mock_ic_cls.return_value = ic_instance

            await tool_handlers.handle_search_code(
                {
                    "query": "find all callers of init",
                    "k": 5,
                    "ego_graph_enabled": True,
                    "ego_graph_k_hops": 2,
                    "include_parent": True,
                }
            )

        # Singleton must be byte-for-byte identical to what it was before
        assert original_cfg.ego_graph.enabled == snapshot_before.ego_graph.enabled
        assert (
            original_cfg.ego_graph.min_similarity_threshold
            == snapshot_before.ego_graph.min_similarity_threshold
        )
        assert (
            original_cfg.parent_retrieval.enabled
            == snapshot_before.parent_retrieval.enabled
        )
        assert (
            original_cfg.multi_hop.edge_weights
            == snapshot_before.multi_hop.edge_weights
        )
