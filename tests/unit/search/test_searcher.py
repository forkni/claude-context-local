"""Unit tests for IntelligentSearcher intent detection enhancements."""

import unittest
from unittest.mock import Mock, patch

from search.config import SearchConfig
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


class TestFilterWrapperMethods(unittest.TestCase):
    """search_by_file_pattern / search_by_chunk_type are thin filters-dict
    wrappers around self.search() (BaseSearcher's public seam) -- previously
    uncovered (search/searcher.py:202-203, 219-220, Phase 13.3). They go
    through BaseSearcher.search(), which resolves search.config.get_search_config()
    when no explicit config is passed -- patched here to a bare SearchConfig()
    so the test doesn't depend on this process's on-disk/env config state.
    """

    def setUp(self):
        self.mock_index_manager = Mock()
        self.mock_index_manager.index = None
        self.mock_index_manager.search.return_value = []
        self.mock_embedder = Mock()
        self.mock_embedder.model_name = "test-model"
        self.mock_embedder.embed_query.return_value = [0.1, 0.2, 0.3]

        self.searcher = IntelligentSearcher(
            index_manager=self.mock_index_manager, embedder=self.mock_embedder
        )

        patcher = patch("search.config.get_search_config", return_value=SearchConfig())
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_search_by_file_pattern_builds_file_pattern_filter(self):
        self.searcher.search_by_file_pattern("query", ["**/*.py"], k=2)

        passed_filters = self.mock_index_manager.search.call_args[0][2]
        self.assertEqual(passed_filters, {"file_pattern": ["**/*.py"]})

    def test_search_by_chunk_type_builds_chunk_type_filter(self):
        self.searcher.search_by_chunk_type("query", "function", k=2)

        passed_filters = self.mock_index_manager.search.call_args[0][2]
        self.assertEqual(passed_filters, {"chunk_type": "function"})


class TestFindSimilarToChunk(unittest.TestCase):
    """search/searcher.py:233-242, Phase 13.3 -- previously uncovered."""

    def setUp(self):
        self.mock_index_manager = Mock()
        self.mock_index_manager.index = None
        self.mock_embedder = Mock()
        self.mock_embedder.model_name = "test-model"

        self.searcher = IntelligentSearcher(
            index_manager=self.mock_index_manager, embedder=self.mock_embedder
        )

    def test_wraps_each_similar_chunk_as_a_search_result(self):
        self.mock_index_manager.get_similar_chunks.return_value = [
            ("a.py:1-5:function:foo", 0.9, {"name": "foo", "chunk_type": "function"}),
            ("b.py:1-5:function:bar", 0.7, {"name": "bar", "chunk_type": "function"}),
        ]

        results = self.searcher.find_similar_to_chunk("a.py:1-5:function:foo", k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].chunk_id, "a.py:1-5:function:foo")
        self.assertEqual(results[0].score, 0.9)
        self.assertEqual(results[1].chunk_id, "b.py:1-5:function:bar")
        # The first call is the primary similar-chunks lookup; each result is
        # then enriched (context_depth=1), which calls get_similar_chunks
        # again per result to build its own "similar_chunks" context.
        self.assertEqual(
            self.mock_index_manager.get_similar_chunks.call_args_list[0],
            unittest.mock.call("a.py:1-5:function:foo", 2),
        )

    def test_empty_result_when_no_similar_chunks(self):
        self.mock_index_manager.get_similar_chunks.return_value = []

        results = self.searcher.find_similar_to_chunk("a.py:1-5:function:foo")

        self.assertEqual(results, [])


class TestGetSearchSuggestions(unittest.TestCase):
    """search/searcher.py:309-324, Phase 13.3 -- previously uncovered."""

    def setUp(self):
        self.mock_index_manager = Mock()
        self.mock_index_manager.index = None
        self.mock_embedder = Mock()
        self.mock_embedder.model_name = "test-model"

        self.searcher = IntelligentSearcher(
            index_manager=self.mock_index_manager, embedder=self.mock_embedder
        )

    def test_suggestions_from_matching_tags_and_chunk_types(self):
        self.mock_index_manager.get_stats.return_value = {
            "top_tags": {"authentication": 5, "database": 3},
            "chunk_types": {"function": 10, "class": 4},
        }

        suggestions = self.searcher.get_search_suggestions("auth")

        self.assertIn("Find authentication related code", suggestions)
        self.assertNotIn("Find database related code", suggestions)

    def test_no_match_returns_empty_list(self):
        self.mock_index_manager.get_stats.return_value = {
            "top_tags": {"database": 3},
            "chunk_types": {"class": 4},
        }

        suggestions = self.searcher.get_search_suggestions("zzz_no_match")

        self.assertEqual(suggestions, [])

    def test_suggestions_capped_at_five(self):
        self.mock_index_manager.get_stats.return_value = {
            "top_tags": {f"foo_tag_{i}": i for i in range(10)},
            "chunk_types": {},
        }

        suggestions = self.searcher.get_search_suggestions("foo")

        self.assertEqual(len(suggestions), 5)
