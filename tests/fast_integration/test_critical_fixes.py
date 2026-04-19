"""Critical bug validation tests for low-level MCP server.

Tests that verify the critical fixes:
1. project_id=None bug is eliminated
2. SSE race conditions are prevented
3. State initialization is consistent

NOTE (2025-11-13): Lifecycle tests removed after migration to application-level initialization.
The server no longer uses per-connection server_lifespan - initialization happens at application
startup via Starlette's app_lifespan, guaranteeing state is ready before any connections.
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server import tool_handlers


# REMOVED (2025-11-13): test_lifespan_hook_initializes_project
# Reason: server_lifespan no longer exists - initialization now happens at application
# startup via Starlette's app_lifespan, guaranteeing state before any connections.
# The behavior this tested is now architecturally guaranteed.


# REMOVED (2025-11-13): test_project_id_never_none_in_get_index_manager
# Reason: Application-level initialization guarantees _current_project is set before tool calls.


# REMOVED (2025-11-13): test_state_consistency_across_tool_calls
# Reason: State consistency is now guaranteed by application-level initialization.


# REMOVED (2025-11-13): test_lifespan_hook_runs_before_first_tool
# Reason: Starlette's application lifecycle guarantees initialization before accepting connections.


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parallel_tool_calls_dont_cause_race_condition():
    """Verify parallel tool calls don't cause state inconsistencies."""

    test_project = str(Path.cwd())

    with (
        patch.dict(os.environ, {"CLAUDE_DEFAULT_PROJECT": test_project}),
        patch("mcp_server.tools.status_handlers.get_storage_dir") as mock_storage,
    ):
        mock_storage.return_value = Path("/tmp/test")

        with patch("search.config.get_search_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.search_mode.enable_hybrid = True
            mock_cfg.search_mode.bm25_weight = 0.4
            mock_cfg.search_mode.dense_weight = 0.6
            mock_cfg.search_mode.rrf_k_parameter = 60
            mock_cfg.performance.use_parallel_search = True
            mock_cfg.embedding.model_name = "test"
            mock_config.return_value = mock_cfg

            # Call multiple tools in parallel
            results = await asyncio.gather(
                tool_handlers.handle_get_search_config_status({}),
                tool_handlers.handle_list_projects({}),
                tool_handlers.handle_list_embedding_models({}),
                return_exceptions=True,
            )

            # All should succeed (no race condition errors)
            for result in results:
                assert not isinstance(result, Exception)
                assert "error" not in result or "project_id" not in str(
                    result.get("error", "")
                )


# REMOVED (2025-11-13): test_cleanup_called_on_shutdown
# Reason: Cleanup is now part of app_lifespan finally block in Starlette application.


# REMOVED (2025-11-13): test_model_pool_initialized_in_lifespan
# Reason: Model pool initialization is now in app_lifespan, verified by integration testing.


# REMOVED (2025-11-13): test_no_tools_run_before_lifespan_complete
# Reason: Starlette's application lifecycle architecturally guarantees initialization order.


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_search_weight_isolation():
    """handle_search_code passes per-request intent weights as kwargs to searcher.search.

    Verifies the fix for the shared-state race: intent weights must be threaded as
    per-call kwargs instead of mutating searcher.bm25_weight / searcher.dense_weight.

    Runs N calls with distinct weight pairs, checks that searcher.search received
    each pair as explicit kwargs (not instance-state mutations).
    """
    import threading

    from search.config import SearchConfig
    from search.hybrid_searcher import HybridSearcher

    n_calls = 5
    # Unique (bm25, dense) per call so we can distinguish them
    weight_pairs = [
        (round(0.1 * (i + 1), 1), round(1 - 0.1 * (i + 1), 1)) for i in range(n_calls)
    ]

    # Thread-safe capture: store (bm25_weight, dense_weight) kwargs per call index
    captured: list[dict] = []
    capture_lock = threading.Lock()

    def make_search_side_effect():
        """Capture the bm25_weight/dense_weight kwargs on each call to searcher.search."""

        def _search(**kwargs):
            with capture_lock:
                captured.append(
                    {
                        "bm25_weight": kwargs.get("bm25_weight"),
                        "dense_weight": kwargs.get("dense_weight"),
                    }
                )
            return []

        return _search

    mock_searcher = Mock(spec=HybridSearcher)
    mock_searcher.is_ready = True
    mock_searcher.bm25_weight = 0.35
    mock_searcher.dense_weight = 0.65
    mock_searcher.search = Mock(side_effect=make_search_side_effect())

    mock_faiss = Mock()
    mock_faiss.ntotal = 100
    mock_dense_idx = Mock()
    mock_dense_idx.index = mock_faiss
    mock_dense_idx.graph_storage = None
    mock_searcher.dense_index = mock_dense_idx

    # Pre-build IntentDecision mocks (one per call, keyed by query string)
    def make_intent_decision(bm25: float, dense: float):
        d = Mock()
        d.intent = Mock()
        d.intent.value = "local"
        d.confidence = 0.95
        d.reason = "test"
        d.suggested_params = {
            "bm25_weight": bm25,
            "dense_weight": dense,
            "search_mode": "hybrid",
        }
        return d

    decisions = {
        f"query_{i}": make_intent_decision(*weight_pairs[i]) for i in range(n_calls)
    }

    def classify_side_effect(query):
        return decisions.get(query, make_intent_decision(0.35, 0.65))

    with (
        patch(
            "mcp_server.tools.search_handlers.get_searcher", return_value=mock_searcher
        ),
        patch("mcp_server.tools.search_handlers.get_state") as mock_state,
        patch("mcp_server.tools.search_handlers.get_config") as mock_app_cfg,
        patch("mcp_server.tools.search_handlers.get_config_manager") as mock_cm,
        patch("mcp_server.tools.search_handlers.get_search_config") as mock_cfg,
        patch("mcp_server.tools.search_handlers.IntentClassifier") as mock_ic_cls,
        patch(
            "mcp_server.tools.search_handlers._check_auto_reindex",
            return_value=(False, None),
        ),
    ):
        mock_state.return_value.current_project = "/test"
        mock_state.return_value.searcher = None

        app_cfg = Mock()
        app_cfg.intent.enabled = True
        app_cfg.intent.semantic_enabled = False
        app_cfg.intent.confidence_threshold = 0.0
        app_cfg.intent.log_classifications = False
        app_cfg.performance.use_parallel_search = False
        app_cfg.output.max_context_tokens = 0
        mock_app_cfg.return_value = app_cfg

        mock_cfg.return_value = SearchConfig()
        mock_cm.return_value.get_search_mode_for_query.return_value = "hybrid"

        ic_instance = Mock()
        ic_instance.classify.side_effect = classify_side_effect
        mock_ic_cls.return_value = ic_instance

        await asyncio.gather(
            *[
                tool_handlers.handle_search_code({"query": f"query_{i}", "k": 3})
                for i in range(n_calls)
            ]
        )

    # Every call must have forwarded its own (bm25_weight, dense_weight) as kwargs
    assert len(captured) == n_calls, (
        f"Expected {n_calls} search calls, got {len(captured)}"
    )
    captured_pairs = {(c["bm25_weight"], c["dense_weight"]) for c in captured}
    expected_pairs = set(weight_pairs)
    assert captured_pairs == expected_pairs, (
        f"Weight pairs mismatch. Expected {expected_pairs}, got {captured_pairs}. "
        "This indicates intent weights were not correctly forwarded as per-call kwargs."
    )
    # Instance state must remain untouched for all calls
    assert mock_searcher.bm25_weight == 0.35
    assert mock_searcher.dense_weight == 0.65


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
