"""Tests that handle_search_code does not mutate the get_search_config() singleton.

get_search_config() returns a process-wide cached singleton. Any mutation of that
object races with concurrent requests. The handler must deep-copy before mutating.
"""

import copy
from unittest.mock import Mock, patch

import pytest

from mcp_server import tool_handlers
from search.config import SearchConfig
from tests.fixtures.mcp_mocks import (
    make_app_config_mock,
    make_hybrid_searcher_mock,
    make_intent_decision_mock,
)


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
    mock_searcher = make_hybrid_searcher_mock()
    intent_decision = make_intent_decision_mock("local", bm25=0.7, dense=0.3)

    # Capture the real singleton before the call.
    # After Phases B-C, get_search_config lives in search_orchestrator (used by _execute).
    original_cfg = SearchConfig()  # fresh default config
    snapshot_before = copy.deepcopy(original_cfg)

    with (
        # Singleton: must be passed to _execute as config_singleton
        patch(
            "mcp_server.tools.search_orchestrator.get_search_config",
            return_value=original_cfg,
        ),
        # get_searcher and readiness now in search_orchestrator._execute
        patch(
            "mcp_server.tools.search_orchestrator.get_searcher",
            return_value=mock_searcher,
        ),
        # get_state: orchestrator (for embedder + current_project)
        patch("mcp_server.tools.search_orchestrator.get_state") as mock_orch_state,
        # get_config: orchestrator uses it for intent + parallel_search
        patch("mcp_server.tools.search_orchestrator.get_config") as mock_orch_cfg,
        # get_config_manager: orchestrator uses it for actual_search_mode
        patch("mcp_server.tools.search_orchestrator.get_config_manager") as mock_cm,
        # IntentClassifier lives in search_orchestrator
        patch("mcp_server.tools.search_orchestrator.IntentClassifier") as mock_ic_cls,
        # _route_query_to_model imported lazily by planner from search_handlers
        patch("mcp_server.tools.search_handlers._route_query_to_model") as mock_route,
        patch(
            "mcp_server.tools.search_handlers._check_auto_reindex",
            return_value=(False, None),
        ),
        # _assemble helpers (prevent format/subgraph code from blowing up on mock data)
        patch(
            "mcp_server.tools.search_handlers._format_search_results", return_value=[]
        ),
        patch(
            "mcp_server.tools.search_handlers._enrich_results_with_graph_data",
            side_effect=lambda r, _: r,
        ),
        patch(
            "mcp_server.tools.search_handlers._get_index_manager_from_searcher",
            return_value=None,
        ),
    ):
        mock_orch_state.return_value.current_project = "/test"
        mock_orch_state.return_value.searcher = None

        app_cfg = make_app_config_mock()
        mock_orch_cfg.return_value = app_cfg

        mock_cm.return_value.get_search_mode_for_query.return_value = "hybrid"
        mock_route.return_value = ("qwen3_0.6b", None)

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
        assert (
            original_cfg.ego_graph.edge_weights
            == snapshot_before.ego_graph.edge_weights
        )
