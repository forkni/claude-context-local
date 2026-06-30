"""Unit tests for RankingHeuristics.

Parity section verifies that scores and ordering are identical to the original
IntelligentSearcher._rank_results implementation. Behavior sections test each
documented boost/demotion rule in isolation.
"""

import unittest

from search.ranking_heuristics import RankingHeuristics
from search.reranker import SearchResult


def _result(
    name: str = "fn",
    chunk_type: str = "function",
    similarity_score: float = 1.0,
    relative_path: str = "a/b.py",
    docstring: str | None = None,
    content_preview: str = "x",
) -> SearchResult:
    return SearchResult(
        chunk_id="id",
        score=similarity_score,
        metadata={
            "name": name,
            "chunk_type": chunk_type,
            "relative_path": relative_path,
            "file_path": "/abs/a/b.py",
            "docstring": docstring,
            "content_preview": content_preview,
        },
        source="semantic",
    )


class TestRankingHeuristicsParity(unittest.TestCase):
    """Parity: RankingHeuristics.rank must reproduce the old _rank_results output."""

    def setUp(self):
        self.h = RankingHeuristics()

    def _scores(self, results, query):
        return [self.h._score(r, query) for r in results]

    def test_class_keyword_path_order(self):
        """'class' in query → class chunk ranked above function chunk."""
        cls = _result(name="QueryRouter", chunk_type="class", similarity_score=0.8)
        fn = _result(name="route_query", chunk_type="function", similarity_score=0.85)
        ranked = self.h.rank([fn, cls], "QueryRouter class")
        self.assertEqual(ranked[0].metadata["chunk_type"], "class")

    def test_entity_query_path_order(self):
        """CamelCase entity query → class chunk boosted over function."""
        cls = _result(
            name="IntelligentSearcher", chunk_type="class", similarity_score=0.8
        )
        fn = _result(name="search", chunk_type="function", similarity_score=0.82)
        ranked = self.h.rank([fn, cls], "IntelligentSearcher")
        self.assertEqual(ranked[0].metadata["chunk_type"], "class")

    def test_general_query_module_demoted(self):
        """General query → module chunks scored below functions at equal similarity."""
        fn = _result(name="search", chunk_type="function", similarity_score=0.9)
        mod = _result(name="searcher", chunk_type="module", similarity_score=0.9)
        ranked = self.h.rank([mod, fn], "how does search work")
        self.assertEqual(ranked[0].metadata["chunk_type"], "function")

    def test_score_reproducible(self):
        """Same result + query always returns same score."""
        r = _result(name="QueryRouter", chunk_type="class", similarity_score=0.75)
        s1 = self.h._score(r, "QueryRouter")
        s2 = self.h._score(r, "QueryRouter")
        self.assertAlmostEqual(s1, s2, places=10)


class TestTypeBoosts(unittest.TestCase):
    def setUp(self):
        self.h = RankingHeuristics()

    def test_class_keyword_boosts_class(self):
        r = _result(chunk_type="class", similarity_score=1.0)
        s = self.h._score(r, "show me the class")
        self.assertAlmostEqual(s, 1.4, places=5)

    def test_class_keyword_demotes_module(self):
        r = _result(chunk_type="module", similarity_score=1.0)
        s = self.h._score(r, "find the class")
        self.assertAlmostEqual(s, 0.82, places=5)

    def test_entity_query_boosts_class(self):
        r = _result(name="RankingHeuristics", chunk_type="class", similarity_score=1.0)
        s = self.h._score(r, "RankingHeuristics")
        # entity path: class boost=1.35, exact-name boost=1.4
        self.assertAlmostEqual(s, 1.35 * 1.4, places=5)

    def test_general_query_unknown_type_no_boost(self):
        r = _result(chunk_type="enum", similarity_score=1.0)
        s = self.h._score(r, "how does search work")
        # unknown type → 1.0 boost, no name match, no path match
        self.assertAlmostEqual(s, 1.0, places=5)


class TestNameBoost(unittest.TestCase):
    def setUp(self):
        self.h = RankingHeuristics()

    def test_exact_match_returns_1_4(self):
        self.assertAlmostEqual(
            self.h._calculate_name_boost("search", "search", ["search"]), 1.4
        )

    def test_exact_match_case_insensitive(self):
        self.assertAlmostEqual(
            self.h._calculate_name_boost("Search", "search", ["search"]), 1.4
        )

    def test_high_overlap_returns_1_3(self):
        # query_tokens = ["query", "router"], name_tokens = ["query", "router"]
        boost = self.h._calculate_name_boost(
            "QueryRouter", "query router", ["query", "router"]
        )
        self.assertAlmostEqual(boost, 1.3, places=5)

    def test_no_overlap_returns_1_0(self):
        boost = self.h._calculate_name_boost(
            "embed", "query router", ["query", "router"]
        )
        self.assertAlmostEqual(boost, 1.0, places=5)

    def test_none_name_returns_1_0(self):
        boost = self.h._calculate_name_boost(None, "query", ["query"])
        self.assertAlmostEqual(boost, 1.0, places=5)


class TestPathBoost(unittest.TestCase):
    def setUp(self):
        self.h = RankingHeuristics()

    def test_matching_token_adds_5_percent(self):
        boost = self.h._calculate_path_boost("search/searcher.py", ["search"])
        self.assertAlmostEqual(boost, 1.05, places=5)

    def test_two_matching_tokens(self):
        boost = self.h._calculate_path_boost(
            "search/ranking_heuristics.py", ["search", "ranking"]
        )
        self.assertAlmostEqual(boost, 1.10, places=5)

    def test_no_match_returns_1_0(self):
        boost = self.h._calculate_path_boost("graph/community.py", ["search"])
        self.assertAlmostEqual(boost, 1.0, places=5)

    def test_empty_tokens_returns_1_0(self):
        boost = self.h._calculate_path_boost("search/searcher.py", [])
        self.assertAlmostEqual(boost, 1.0, places=5)


class TestLifecycleDemotion(unittest.TestCase):
    def setUp(self):
        self.h = RankingHeuristics()

    def test_init_demoted_on_general_query(self):
        r = _result(name="__init__", chunk_type="function", similarity_score=1.0)
        s = self.h._score(r, "how does search work")
        self.assertAlmostEqual(s, 1.2 * 0.85, places=5)

    def test_init_not_demoted_when_query_has_init(self):
        r = _result(name="__init__", chunk_type="function", similarity_score=1.0)
        s_demoted = self.h._score(r, "how does search work")
        s_kept = self.h._score(r, "show me the init method")
        self.assertGreater(s_kept, s_demoted)

    def test_non_lifecycle_not_demoted(self):
        # name="embed" has no overlap with query tokens → pure type boost only
        r = _result(name="embed", chunk_type="function", similarity_score=1.0)
        s = self.h._score(r, "how does search work")
        self.assertAlmostEqual(s, 1.2, places=5)


class TestDocstringBoost(unittest.TestCase):
    def setUp(self):
        self.h = RankingHeuristics()

    def test_docstring_boosts_non_module(self):
        r = _result(
            chunk_type="function", similarity_score=1.0, docstring="Searches code."
        )
        s = self.h._score(r, "how does search work")
        self.assertAlmostEqual(s, 1.2 * 1.05, places=5)

    def test_module_docstring_small_boost_on_entity_query(self):
        # name="module_init" has no overlap with query "Embedder" → only type+docstring boosts
        r = _result(
            name="module_init",
            chunk_type="module",
            similarity_score=1.0,
            docstring="Module docs.",
        )
        # entity query (CamelCase, 1 token) → is_entity_query=True
        s = self.h._score(r, "Embedder")
        # module on entity query → type_boost=0.85, name_boost=1.0, docstring=1.02
        self.assertAlmostEqual(s, 0.85 * 1.02, places=5)

    def test_no_docstring_no_boost(self):
        r_with = _result(chunk_type="function", similarity_score=1.0, docstring="doc")
        r_without = _result(chunk_type="function", similarity_score=1.0, docstring=None)
        s_with = self.h._score(r_with, "how does search work")
        s_without = self.h._score(r_without, "how does search work")
        self.assertGreater(s_with, s_without)


class TestContentPreviewPenalty(unittest.TestCase):
    def setUp(self):
        self.h = RankingHeuristics()

    def test_long_preview_penalised(self):
        short = _result(
            chunk_type="function", similarity_score=1.0, content_preview="x"
        )
        long_ = _result(
            chunk_type="function", similarity_score=1.0, content_preview="x" * 1001
        )
        s_short = self.h._score(short, "how does search work")
        s_long = self.h._score(long_, "how does search work")
        self.assertGreater(s_short, s_long)
        self.assertAlmostEqual(s_long, 1.2 * 0.98, places=5)

    def test_exactly_1000_chars_no_penalty(self):
        r = _result(
            chunk_type="function", similarity_score=1.0, content_preview="x" * 1000
        )
        s = self.h._score(r, "how does search work")
        self.assertAlmostEqual(s, 1.2, places=5)


class TestNormalizeToTokens(unittest.TestCase):
    def setUp(self):
        self.h = RankingHeuristics()

    def test_camel_case_split(self):
        tokens = self.h._normalize_to_tokens("QueryRouter")
        self.assertIn("query", tokens)
        self.assertIn("router", tokens)

    def test_snake_case_split(self):
        tokens = self.h._normalize_to_tokens("rank_results")
        self.assertEqual(tokens, ["rank", "results"])

    def test_already_lowercase(self):
        tokens = self.h._normalize_to_tokens("search code")
        self.assertEqual(tokens, ["search", "code"])

    def test_mixed(self):
        tokens = self.h._normalize_to_tokens("IntelligentSearcher._rank_results")
        for expected in ["intelligent", "searcher", "rank", "results"]:
            self.assertIn(expected, tokens)


class TestIsEntityLikeQuery(unittest.TestCase):
    def setUp(self):
        self.h = RankingHeuristics()

    def test_camel_case_is_entity(self):
        tokens = self.h._normalize_to_tokens("QueryRouter")
        self.assertTrue(self.h._is_entity_like_query("QueryRouter", tokens))

    def test_action_word_not_entity(self):
        tokens = self.h._normalize_to_tokens("find the class")
        self.assertFalse(self.h._is_entity_like_query("find the class", tokens))

    def test_long_phrase_not_entity(self):
        tokens = ["how", "does", "search", "work"]
        self.assertFalse(self.h._is_entity_like_query("how does search work", tokens))

    def test_short_noun_is_entity(self):
        tokens = self.h._normalize_to_tokens("searcher")
        self.assertTrue(self.h._is_entity_like_query("searcher", tokens))


if __name__ == "__main__":
    unittest.main()
