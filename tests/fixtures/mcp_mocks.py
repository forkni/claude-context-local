"""Mock builders for MCP server handler tests.

Helpers that produce minimal Mock objects passing the type/ready checks in
mcp_server/tools/search_handlers.py, so race/isolation tests can exercise the
handler without loading real models or FAISS indexes.
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import Mock


def make_hybrid_searcher_mock(
    *, search_side_effect: Callable[..., Any] | None = None
) -> Mock:
    """Build a Mock that passes HybridSearcher.is_ready and dense_index shape checks.

    Args:
        search_side_effect: Optional callable used as ``.search.side_effect``.
            When None, ``.search`` returns an empty list.
    """
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

    if search_side_effect is not None:
        mock_searcher.search = Mock(side_effect=search_side_effect)
    else:
        mock_searcher.search = Mock(return_value=[])
    return mock_searcher


def make_intent_decision_mock(
    intent_value: str = "local",
    bm25: float = 0.3,
    dense: float = 0.7,
    *,
    confidence: float = 0.95,
) -> Mock:
    """Build a Mock shaped like IntentDecision with the given intent + weights."""
    decision = Mock()
    decision.intent = Mock()
    decision.intent.value = intent_value
    decision.confidence = confidence
    decision.reason = "test"
    decision.suggested_params = {
        "bm25_weight": bm25,
        "dense_weight": dense,
        "search_mode": "hybrid",
    }
    return decision


def make_app_config_mock() -> Mock:
    """Build a Mock shaped like ApplicationConfig returned by get_config()."""
    app_cfg = Mock()
    app_cfg.intent.enabled = True
    app_cfg.intent.semantic_enabled = False
    app_cfg.intent.confidence_threshold = 0.0
    app_cfg.intent.log_classifications = False
    app_cfg.performance.use_parallel_search = False
    app_cfg.output.max_context_tokens = 0
    return app_cfg
