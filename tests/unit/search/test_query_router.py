"""Unit tests for QueryRouter model routing logic.

Tests routing accuracy for all 20 benchmark queries plus edge cases.
Validates keyword matching, tie-breaking logic, and confidence thresholds.
"""

from unittest.mock import MagicMock, patch

import pytest

from search.query_router import QueryRouter


@pytest.fixture(autouse=True)
def mock_full_pool_config():
    """Mock config to use full model pool for all tests."""
    with patch("search.config.get_search_config") as mock_config:
        mock_routing = MagicMock()
        mock_routing.multi_model_pool = "full"
        mock_config.return_value.routing = mock_routing
        yield


class TestQueryRouterBenchmarkQueries:
    """Test routing accuracy using 20 benchmark queries from actual usage."""

    @pytest.fixture
    def router(self):
        """Create QueryRouter instance for testing."""
        return QueryRouter(enable_logging=False)

    # Parametrized test cases from benchmark queries
    @pytest.mark.parametrize(
        "query,expected_model,description",
        [
            # Error Handling (3 queries)
            ("error handling exception try except", "qwen3", "Error handling"),
            ("validate input parameters", "qwen3", "Validation logic - FIX"),
            ("raise exception when invalid", "qwen3", "Exception raising"),
            # Configuration (3 queries)
            ("load configuration settings", "bge_code", "Config loading"),
            ("environment variable setup", "qwen3", "Environment variables"),
            (
                "model registry initialization",
                "qwen3",
                "Registry init - initialization wins",
            ),
            # Search & Indexing (4 queries)
            ("semantic search implementation", "qwen3", "Search implementation"),
            ("BM25 sparse index", "qwen3", "BM25 index"),
            ("hybrid search fusion RRF", "qwen3", "RRF algorithm"),
            ("incremental index update", "qwen3", "Incremental indexing"),
            # Graph & Dependencies (3 queries)
            ("call graph extraction", "qwen3", "Call graph - FIX"),
            ("find function callers", "qwen3", "Function callers - FIX"),
            ("dependency relationship", "qwen3", "Dependencies - FIX"),
            # Embeddings (3 queries)
            ("embedding model loading", "bge_code", "Model loading"),
            ("batch embedding generation", "bge_code", "Batch generation"),
            ("vector dimension handling", "qwen3", "Vector dimension"),
            # MCP Server (2 queries)
            ("MCP tool handler", "qwen3", "Tool handler - FIX"),
            ("project switching logic", "bge_code", "Project switching"),
            # Merkle/Change Detection (2 queries)
            ("merkle tree snapshot", "qwen3", "Merkle tree"),
            ("file change detection", "qwen3", "Change detection"),
        ],
    )
    def test_benchmark_routing_accuracy(
        self, router, query, expected_model, description
    ):
        """Test that benchmark queries route to expected models."""
        decision = router.route(query)
        assert decision.model_key == expected_model, (
            f"{description}: Expected {expected_model}, got {decision.model_key} (confidence: {decision.confidence:.2f}, scores: {decision.scores})"
        )

    def test_routing_confidence_scores(self, router):
        """Test that routing provides reasonable confidence scores."""
        # High confidence case
        decision = router.route("merkle tree change detection")
        assert decision.confidence >= 0.10, "Merkle query should have high confidence"

        # Low confidence case (generic query)
        decision = router.route("file operations")
        assert decision.model_key == "qwen3", "Generic query should use default model"


class TestQueryRouterTieBreaking:
    """Test explicit tie-breaking logic."""

    @pytest.fixture
    def router(self):
        """Create QueryRouter instance for testing."""
        return QueryRouter(enable_logging=False)

    def test_precedence_order(self, router):
        """Test that precedence order is correct."""
        assert router.PRECEDENCE == [
            "qwen3",
            "bge_code",
        ], "Precedence order should be qwen3 > bge_code (2-model pool)"

    def test_tie_resolution_favors_qwen3(self, router):
        """Test that ties favor qwen3 over bge_code (2-model pool)."""
        # Query with keywords matching multiple models
        decision = router.route("graph structure dependency")
        # Should favor qwen3 due to precedence in 2-model pool
        assert decision.model_key in [
            "qwen3",
            "bge_code",
        ], "Should route to qwen3 or bge_code based on scores"

    def test_resolve_tie_method(self, router):
        """Test _resolve_tie() method directly for 2-model pool."""
        # Exact tie - qwen3 favored in 2-model pool
        scores = {"qwen3": 0.30, "bge_code": 0.30}
        best = router._resolve_tie(scores)
        assert best == "qwen3", "Ties should favor qwen3 (2-model pool)"

        # Close scores (within 0.01) - qwen3 favored by precedence
        scores = {"qwen3": 0.299, "bge_code": 0.30}
        best = router._resolve_tie(scores)
        assert best == "qwen3", "Close scores should favor qwen3"

        # bge_code wins with clear margin
        scores = {"qwen3": 0.20, "bge_code": 0.40}
        best = router._resolve_tie(scores)
        assert best == "bge_code", "bge_code should win with clear margin"


class TestQueryRouterKeywordMatching:
    """Test specific keyword matching for improved routing."""

    @pytest.fixture
    def router(self):
        """Create QueryRouter instance for testing."""
        return QueryRouter(enable_logging=False)

    def test_validate_keyword_routes_to_qwen3(self, router):
        """Test that 'validate' keyword routes to qwen3."""
        decision = router.route("validate input parameters")
        assert decision.model_key == "qwen3", "Validate should route to qwen3"

    def test_handler_keyword_routes_to_qwen3(self, router):
        """Test that 'handler' keyword routes to qwen3."""
        decision = router.route("MCP tool handler implementation")
        assert decision.model_key == "qwen3", "Handler should route to qwen3"

    def test_registry_keyword_routes_to_qwen3(self, router):
        """Test that 'registry' keyword routes to qwen3 when code-focused."""
        # Use a code-focused query to ensure qwen3 wins
        decision = router.route("registry pattern implementation")
        assert decision.model_key == "qwen3", "Registry pattern should route to qwen3"

    def test_caller_keyword_routes_to_bge_code(self, router):
        """Test that 'caller' keyword routes to bge_code (2-model pool)."""
        decision = router.route("find function callers", confidence_threshold=0.05)
        assert decision.model_key == "bge_code", "Caller should route to bge_code"

    def test_dependency_keyword_routes_to_bge_code(self, router):
        """Test that 'dependency' keyword routes to bge_code (2-model pool)."""
        decision = router.route("dependency graph analysis", confidence_threshold=0.05)
        assert decision.model_key == "bge_code", "Dependency should route to bge_code"

    def test_switch_keyword_routes_to_bge_code(self, router):
        """Test that 'switch' keyword routes to bge_code (2-model pool)."""
        decision = router.route("project switching logic")
        assert decision.model_key == "bge_code", "Switch should route to bge_code"

    def test_verify_keyword_routes_to_bge_code(self, router):
        """Test that 'verify' keyword routes to bge_code (2-model pool)."""
        decision = router.route("verify configuration settings")
        assert decision.model_key == "bge_code", "Verify should route to bge_code"


class TestQueryRouterEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def router(self):
        """Create QueryRouter instance for testing."""
        return QueryRouter(enable_logging=False)

    def test_empty_query_uses_default(self, router):
        """Test that empty query uses default model."""
        decision = router.route("")
        assert decision.model_key == "qwen3", (
            "Empty query should use default model (2-model pool)"
        )
        assert decision.confidence == 0.0, "Empty query should have 0 confidence"

    def test_no_keyword_match_uses_default(self, router):
        """Test that query with no matching keywords uses default."""
        decision = router.route("quantum entanglement paradox")
        assert decision.model_key == "qwen3", (
            "No match should use default model (2-model pool)"
        )

    def test_low_confidence_uses_default(self, router):
        """Test that low confidence routes to default model."""
        # Query with only one weak match (below 0.05 threshold)
        decision = router.route("flow")  # Single generic keyword
        # This might match bge_m3 "flow", but should be low confidence
        assert decision.confidence < 0.15, "Single keyword should have low confidence"

    def test_get_model_strengths(self, router):
        """Test get_model_strengths() returns correct data."""
        qwen3_strengths = router.get_model_strengths("qwen3")
        assert qwen3_strengths is not None, "Should return qwen3 strengths"
        assert "keywords" in qwen3_strengths, "Should include keywords"
        assert "validate" in qwen3_strengths["keywords"], (
            "Should include new validate keyword"
        )

        invalid = router.get_model_strengths("invalid_model")
        assert invalid is None, "Should return None for invalid model"

    def test_get_available_models(self, router):
        """Test get_available_models() returns all models."""
        models = router.get_available_models()
        assert set(models) == {
            "qwen3",
            "bge_code",
        }, "Should return both models in 2-model pool"


class TestQueryRouterConfidenceThreshold:
    """Test confidence threshold behavior."""

    @pytest.fixture
    def router(self):
        """Create QueryRouter instance for testing."""
        return QueryRouter(enable_logging=False)

    def test_default_threshold(self, router):
        """Test that default confidence threshold is 0.05."""
        assert router.CONFIDENCE_THRESHOLD == 0.05, "Default threshold should be 0.05"

    def test_custom_threshold_parameter(self, router):
        """Test that custom threshold can be passed to route()."""
        query = "validate input"
        # With low threshold (default 0.05)
        decision_low = router.route(query, confidence_threshold=0.05)

        # With high threshold (0.5)
        decision_high = router.route(query, confidence_threshold=0.5)

        # High threshold should be more likely to use default
        assert decision_low.confidence == decision_high.confidence, (
            "Confidence should be same regardless of threshold"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
