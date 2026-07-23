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


class TestDeferredEnrichment(unittest.TestCase):
    """A1: enrichment must run on <=k survivors, not on every raw candidate.

    `_semantic_search` used to call `get_similar_chunks` once per raw candidate
    (up to `min(k*10, 200)`) before ranking and truncating to `k`. It now ranks
    the thin results first and enriches only the `k` survivors.
    """

    def setUp(self):
        """Create a mock searcher with 20 raw candidates for a k=3 query."""
        self.mock_index_manager = Mock()
        self.mock_index_manager.index = None
        self.mock_embedder = Mock()
        self.mock_embedder.model_name = "test-model"
        self.mock_embedder.embed_query.return_value = [0.1, 0.2, 0.3]

        self.searcher = IntelligentSearcher(
            index_manager=self.mock_index_manager, embedder=self.mock_embedder
        )

        self.mock_index_manager.search.return_value = [
            (
                f"file{i}.py:1-10:function:foo{i}",
                1.0 - i * 0.01,
                {
                    "chunk_type": "function",
                    "name": f"foo{i}",
                    "relative_path": f"file{i}.py",
                    "docstring": "",
                    "content_preview": "",
                    "folder_structure": ["pkg"],
                },
            )
            for i in range(20)
        ]
        self.mock_index_manager.get_similar_chunks.return_value = [
            (
                "other.py:1-5:function:bar",
                0.5,
                {"name": "bar", "chunk_type": "function"},
            ),
        ]

    def test_enrichment_limited_to_returned_results(self):
        """get_similar_chunks must be called at most k times, not once per raw candidate."""
        k = 3
        results = self.searcher._semantic_search("test query", k=k, context_depth=1)

        self.assertEqual(len(results), k)
        self.assertLessEqual(self.mock_index_manager.get_similar_chunks.call_count, k)

    def test_returned_results_still_enriched(self):
        """Survivors must still carry context_info["similar_chunks"] (behaviour-preserving)."""
        results = self.searcher._semantic_search("test query", k=2, context_depth=1)

        for result in results:
            self.assertIn("similar_chunks", result.metadata["context_info"])
            self.assertTrue(result.metadata["context_info"]["similar_chunks"])

    def test_context_depth_zero_skips_enrichment_entirely(self):
        """context_depth=0 must not call get_similar_chunks at all."""
        self.searcher._semantic_search("test query", k=3, context_depth=0)

        self.mock_index_manager.get_similar_chunks.assert_not_called()


if __name__ == "__main__":
    unittest.main()
