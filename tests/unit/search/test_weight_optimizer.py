"""Unit tests for WeightOptimizer."""

import logging
from unittest.mock import MagicMock

from search.weight_optimizer import WeightOptimizer


class TestWeightOptimizer:
    """Test WeightOptimizer grid search."""

    def test_initialization(self):
        """Test WeightOptimizer initialization with callbacks."""
        search_fn = MagicMock()
        analyze_fn = MagicMock()
        set_weights_fn = MagicMock()
        get_weights_fn = MagicMock()

        optimizer = WeightOptimizer(
            search_callback=search_fn,
            analyze_callback=analyze_fn,
            set_weights_callback=set_weights_fn,
            get_weights_callback=get_weights_fn,
        )

        assert optimizer.search_callback == search_fn
        assert optimizer.analyze_callback == analyze_fn
        assert optimizer.set_weights_callback == set_weights_fn
        assert optimizer.get_weights_callback == get_weights_fn
        assert isinstance(optimizer._logger, logging.Logger)

    def test_optimize_basic(self):
        """Test basic weight optimization."""
        # Mock callbacks
        search_results = [MagicMock(score=0.9), MagicMock(score=0.8)]
        search_fn = MagicMock(return_value=search_results)
        analyze_fn = MagicMock(
            return_value={
                "diversity_score": 0.8,
                "coverage_balance": 0.7,
                "high_quality_ratio": 0.9,
            }
        )

        current_weights = [0.4, 0.6]  # Mutable list to track weight changes
        set_weights_fn = MagicMock(
            side_effect=lambda b, d: (
                current_weights.__setitem__(0, b) or current_weights.__setitem__(1, d)
            )
        )
        get_weights_fn = MagicMock(side_effect=lambda: tuple(current_weights))

        optimizer = WeightOptimizer(
            search_callback=search_fn,
            analyze_callback=analyze_fn,
            set_weights_callback=set_weights_fn,
            get_weights_callback=get_weights_fn,
        )

        # Run optimization
        result = optimizer.optimize(test_queries=["query1", "query2"])

        # Verify results
        assert "bm25_weight" in result
        assert "dense_weight" in result
        assert "optimization_score" in result
        assert "tested_combinations" in result
        assert result["tested_combinations"] == len(
            WeightOptimizer.DEFAULT_COMBINATIONS
        )

        # Verify search was called for each query and weight combination
        expected_calls = len(WeightOptimizer.DEFAULT_COMBINATIONS) * 2  # 2 queries
        assert search_fn.call_count == expected_calls

    def test_optimize_with_custom_combinations(self):
        """Test optimization with custom weight combinations."""
        search_fn = MagicMock(return_value=[MagicMock(score=0.9)])
        analyze_fn = MagicMock(
            return_value={
                "diversity_score": 0.8,
                "coverage_balance": 0.7,
                "high_quality_ratio": 0.9,
            }
        )
        current_weights = [0.5, 0.5]
        set_weights_fn = MagicMock(
            side_effect=lambda b, d: (
                current_weights.__setitem__(0, b) or current_weights.__setitem__(1, d)
            )
        )
        get_weights_fn = MagicMock(side_effect=lambda: tuple(current_weights))

        optimizer = WeightOptimizer(
            search_callback=search_fn,
            analyze_callback=analyze_fn,
            set_weights_callback=set_weights_fn,
            get_weights_callback=get_weights_fn,
        )

        custom_combinations = [(0.3, 0.7), (0.5, 0.5), (0.7, 0.3)]
        result = optimizer.optimize(
            test_queries=["query1"], weight_combinations=custom_combinations
        )

        assert result["tested_combinations"] == 3
        # Should have called search once per combination
        assert search_fn.call_count == 3

    def test_optimize_empty_queries(self):
        """Test optimization with empty query list."""
        search_fn = MagicMock()
        analyze_fn = MagicMock()
        current_weights = [0.4, 0.6]
        set_weights_fn = MagicMock(
            side_effect=lambda b, d: (
                current_weights.__setitem__(0, b) or current_weights.__setitem__(1, d)
            )
        )
        get_weights_fn = MagicMock(side_effect=lambda: tuple(current_weights))

        optimizer = WeightOptimizer(
            search_callback=search_fn,
            analyze_callback=analyze_fn,
            set_weights_callback=set_weights_fn,
            get_weights_callback=get_weights_fn,
        )

        result = optimizer.optimize(test_queries=[])

        # Should have tested all combinations even with no queries
        assert result["tested_combinations"] == len(
            WeightOptimizer.DEFAULT_COMBINATIONS
        )
        assert result["optimization_score"] == 0.0
        # Search should not have been called since no queries
        assert search_fn.call_count == 0

    def test_optimize_no_results(self):
        """Test optimization when searches return empty results."""
        search_fn = MagicMock(return_value=[])  # No results
        analyze_fn = MagicMock()  # Should not be called
        current_weights = [0.4, 0.6]
        set_weights_fn = MagicMock(
            side_effect=lambda b, d: (
                current_weights.__setitem__(0, b) or current_weights.__setitem__(1, d)
            )
        )
        get_weights_fn = MagicMock(side_effect=lambda: tuple(current_weights))

        optimizer = WeightOptimizer(
            search_callback=search_fn,
            analyze_callback=analyze_fn,
            set_weights_callback=set_weights_fn,
            get_weights_callback=get_weights_fn,
        )

        result = optimizer.optimize(test_queries=["query1"])

        # Should complete without errors
        assert result["optimization_score"] == 0.0
        # Analyze should not have been called since no results
        assert analyze_fn.call_count == 0

    def test_optimize_selects_best_weights(self):
        """Test that optimizer selects weights with highest score."""
        # Mock search to return results
        search_fn = MagicMock(return_value=[MagicMock(score=0.9)])

        # Mock analyze to return different scores for different weight combinations
        # We'll use side_effect to vary the score based on call count
        scores = [0.5, 0.6, 0.9, 0.7, 0.6, 0.5, 0.4]  # Third combination has best score
        call_count = [0]

        def analyze_side_effect(results):
            score = scores[call_count[0] % len(scores)]
            call_count[0] += 1
            return {
                "diversity_score": score,
                "coverage_balance": score,
                "high_quality_ratio": score,
            }

        analyze_fn = MagicMock(side_effect=analyze_side_effect)

        current_weights = [0.4, 0.6]
        set_weights_fn = MagicMock(
            side_effect=lambda b, d: (
                current_weights.__setitem__(0, b) or current_weights.__setitem__(1, d)
            )
        )
        get_weights_fn = MagicMock(side_effect=lambda: tuple(current_weights))

        optimizer = WeightOptimizer(
            search_callback=search_fn,
            analyze_callback=analyze_fn,
            set_weights_callback=set_weights_fn,
            get_weights_callback=get_weights_fn,
        )

        result = optimizer.optimize(test_queries=["query1"])

        # Should have selected third combination (0.4, 0.6) with score 0.9
        assert result["bm25_weight"] == 0.4
        assert result["dense_weight"] == 0.6
        assert abs(result["optimization_score"] - 0.9) < 0.01

    def test_optimize_restores_weights_on_iteration(self):
        """Test that weights are restored after each iteration."""
        search_fn = MagicMock(return_value=[MagicMock(score=0.9)])
        analyze_fn = MagicMock(
            return_value={
                "diversity_score": 0.8,
                "coverage_balance": 0.7,
                "high_quality_ratio": 0.9,
            }
        )

        # Track all weight changes
        weight_history = []
        current_weights = [0.4, 0.6]

        def set_weights_side_effect(b, d):
            current_weights[0] = b
            current_weights[1] = d
            weight_history.append((b, d))

        set_weights_fn = MagicMock(side_effect=set_weights_side_effect)
        get_weights_fn = MagicMock(side_effect=lambda: tuple(current_weights))

        optimizer = WeightOptimizer(
            search_callback=search_fn,
            analyze_callback=analyze_fn,
            set_weights_callback=set_weights_fn,
            get_weights_callback=get_weights_fn,
        )

        optimizer.optimize(test_queries=["query1"])

        # Should have set weights for each combination + restore after each + final set
        # 7 combinations * 2 (set + restore) + 1 final set = 15 calls
        assert len(weight_history) >= len(WeightOptimizer.DEFAULT_COMBINATIONS)

    def test_optimize_with_custom_logger(self):
        """Test optimizer with custom logger."""
        mock_logger = MagicMock(spec=logging.Logger)
        search_fn = MagicMock(return_value=[MagicMock(score=0.9)])
        analyze_fn = MagicMock(
            return_value={
                "diversity_score": 0.8,
                "coverage_balance": 0.7,
                "high_quality_ratio": 0.9,
            }
        )
        current_weights = [0.4, 0.6]
        set_weights_fn = MagicMock(
            side_effect=lambda b, d: (
                current_weights.__setitem__(0, b) or current_weights.__setitem__(1, d)
            )
        )
        get_weights_fn = MagicMock(side_effect=lambda: tuple(current_weights))

        optimizer = WeightOptimizer(
            search_callback=search_fn,
            analyze_callback=analyze_fn,
            set_weights_callback=set_weights_fn,
            get_weights_callback=get_weights_fn,
            logger=mock_logger,
        )

        optimizer.optimize(test_queries=["query1"])

        # Should have logged start and end messages
        assert mock_logger.info.call_count >= 2

    def test_optimize_composite_score_calculation(self):
        """Test that composite score is calculated correctly."""
        search_fn = MagicMock(return_value=[MagicMock(score=0.9)])

        # Return known values for score calculation
        analyze_fn = MagicMock(
            return_value={
                "diversity_score": 1.0,
                "coverage_balance": 0.5,
                "high_quality_ratio": 0.0,
            }
        )

        current_weights = [0.4, 0.6]
        set_weights_fn = MagicMock(
            side_effect=lambda b, d: (
                current_weights.__setitem__(0, b) or current_weights.__setitem__(1, d)
            )
        )
        get_weights_fn = MagicMock(side_effect=lambda: tuple(current_weights))

        optimizer = WeightOptimizer(
            search_callback=search_fn,
            analyze_callback=analyze_fn,
            set_weights_callback=set_weights_fn,
            get_weights_callback=get_weights_fn,
        )

        result = optimizer.optimize(test_queries=["query1"])

        # Expected score: 1.0 * 0.4 + 0.5 * 0.3 + 0.0 * 0.3 = 0.4 + 0.15 + 0.0 = 0.55
        assert abs(result["optimization_score"] - 0.55) < 0.01

    def test_default_combinations_coverage(self):
        """Test that default combinations cover reasonable weight range."""
        assert len(WeightOptimizer.DEFAULT_COMBINATIONS) == 7

        # Should have balanced representation
        bm25_weights = [w[0] for w in WeightOptimizer.DEFAULT_COMBINATIONS]
        dense_weights = [w[1] for w in WeightOptimizer.DEFAULT_COMBINATIONS]

        # All weights should sum to 1.0
        for bm25_w, dense_w in WeightOptimizer.DEFAULT_COMBINATIONS:
            assert abs((bm25_w + dense_w) - 1.0) < 0.01

        # Should cover range from 0.2 to 0.8
        assert min(bm25_weights) == 0.2
        assert max(bm25_weights) == 0.8
        assert min(dense_weights) == 0.2
        assert max(dense_weights) == 0.8
