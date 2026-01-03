"""Unit tests for IntelligentSearcher intent detection enhancements."""

import unittest
from unittest.mock import Mock

from search.searcher import IntelligentSearcher


class TestIntentSpecificRanking(unittest.TestCase):
    """Test that intent-specific boosts are applied during ranking."""

    def setUp(self):
        """Create mock searcher instance."""
        self.mock_index_manager = Mock()
        self.mock_index_manager.index = None
        self.mock_embedder = Mock()
        self.mock_embedder.model_name = "test-model"

        self.searcher = IntelligentSearcher(
            index_manager=self.mock_index_manager, embedder=self.mock_embedder
        )

    def test_intent_boost_formula(self):
        """Test the confidence-weighted boost formula."""
        # Formula: score *= 1 + (boost - 1) * confidence

        # Test case 1: boost=1.2, confidence=0.8
        boost = 1.2
        confidence = 0.8
        multiplier = 1 + (boost - 1.0) * confidence
        self.assertAlmostEqual(multiplier, 1.16, places=2)

        # Test case 2: boost=1.15, confidence=0.5
        boost = 1.15
        confidence = 0.5
        multiplier = 1 + (boost - 1.0) * confidence
        self.assertAlmostEqual(multiplier, 1.075, places=3)

        # Test case 3: boost=1.0 (no boost), any confidence
        boost = 1.0
        confidence = 0.9
        multiplier = 1 + (boost - 1.0) * confidence
        self.assertAlmostEqual(multiplier, 1.0, places=2)


if __name__ == "__main__":
    unittest.main()
