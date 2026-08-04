"""Unit tests for community-aware file-coverage metrics in evaluation/metrics.py.

Category G (global/thematic) queries are scored on file recall, reported twice:
strict (real code chunks only) and community-expanded (a retrieved synthetic
community chunk credits its member file-set, recovered by inverting the
persisted community_map).  The secondary ``mrr_community_credit`` widens
retrieved community chunks to member golden IDs, modeled on
expand_retrieved_with_containment.

Community ids are read from result ``tags`` at scoring time — never from
golden JSON (Louvain ids shift per reindex).
"""

import pytest

from evaluation.metrics import (
    build_community_file_map,
    build_community_membership,
    build_file_entries,
    calculate_file_recall_at_k,
    calculate_mrr,
    expand_retrieved_with_community_credit,
    extract_community_id,
    normalize_chunk_ids,
)


COMMUNITY_MAP = {
    "search/hybrid_searcher.py:1-50:class:HybridSearcher": 7,
    "search/searcher.py:10-90:class:IntelligentSearcher": 7,
    "search\\indexer.py:5-40:function:index_project": 7,
    "graph/storage.py:1-30:class:GraphStorage": 9,
    "graph/storage.py:1-8:module": 9,
}


class TestExtractCommunityId:
    def test_extracts_id(self):
        assert extract_community_id(["community:194"]) == 194

    def test_ignores_other_tags(self):
        assert extract_community_id(["lang:python", "community:7"]) == 7

    def test_none_when_absent(self):
        assert extract_community_id(["lang:python"]) is None
        assert extract_community_id(None) is None
        assert extract_community_id([]) is None

    def test_malformed_id_returns_none(self):
        assert extract_community_id(["community:not-a-number"]) is None


class TestBuildCommunityFileMap:
    def test_inverts_by_path_token(self):
        files = build_community_file_map(COMMUNITY_MAP)
        assert files[7] == frozenset(
            {"search/hybrid_searcher.py", "search/searcher.py", "search/indexer.py"}
        )
        assert files[9] == frozenset({"graph/storage.py"})

    def test_backslash_paths_normalized(self):
        files = build_community_file_map({"sub\\m.py:1-5:function:f": 3})
        assert files[3] == frozenset({"sub/m.py"})

    def test_empty_map(self):
        assert build_community_file_map({}) == {}


class TestBuildFileEntries:
    RESULTS = [
        {"relative_path": "search/hybrid_searcher.py", "tags": ["lang:python"]},
        {
            "relative_path": "__community__/search_HybridSearcher",
            "tags": ["community:7"],
        },
        {"relative_path": "other/noise.py"},
    ]

    def test_strict_ignores_community_chunks(self):
        strict, _expanded = build_file_entries(
            self.RESULTS, build_community_file_map(COMMUNITY_MAP)
        )
        assert strict == [{"search/hybrid_searcher.py"}, set(), {"other/noise.py"}]

    def test_expanded_credits_member_file_set(self):
        _strict, expanded = build_file_entries(
            self.RESULTS, build_community_file_map(COMMUNITY_MAP)
        )
        assert expanded[1] == {
            "search/hybrid_searcher.py",
            "search/searcher.py",
            "search/indexer.py",
        }
        # Real chunks identical in both variants
        assert expanded[0] == {"search/hybrid_searcher.py"}
        assert expanded[2] == {"other/noise.py"}

    def test_unknown_community_id_expands_to_nothing(self):
        results = [{"relative_path": "__community__/root_x", "tags": ["community:999"]}]
        strict, expanded = build_file_entries(
            results, build_community_file_map(COMMUNITY_MAP)
        )
        assert strict == [set()]
        assert expanded == [set()]

    def test_no_community_files_map(self):
        # Detection-off arms: community chunks cover nothing in either variant
        strict, expanded = build_file_entries(self.RESULTS, None)
        assert strict[1] == set()
        assert expanded[1] == set()

    def test_backslash_result_path_normalized(self):
        strict, _ = build_file_entries([{"relative_path": "search\\indexer.py"}], {})
        assert strict == [{"search/indexer.py"}]


class TestCalculateFileRecallAtK:
    EXPECTED = ["search/hybrid_searcher.py", "search/searcher.py", "search/indexer.py"]

    def test_plan_verification_scenario(self):
        """Community chunk covering 2/3 expected files → expanded 2/3, strict 0."""
        results = [
            {
                "relative_path": "__community__/search_HybridSearcher",
                "tags": ["community:5"],
            },
        ]
        community_files = {
            5: frozenset({"search/hybrid_searcher.py", "search/searcher.py"})
        }
        strict, expanded = build_file_entries(results, community_files)
        assert calculate_file_recall_at_k(strict, self.EXPECTED, 10) == 0.0
        assert calculate_file_recall_at_k(expanded, self.EXPECTED, 10) == pytest.approx(
            2 / 3
        )

    def test_strict_unchanged_by_community_presence(self):
        results = [
            {"relative_path": "search/hybrid_searcher.py"},
            {
                "relative_path": "__community__/search_HybridSearcher",
                "tags": ["community:7"],
            },
        ]
        strict, _ = build_file_entries(results, build_community_file_map(COMMUNITY_MAP))
        assert calculate_file_recall_at_k(strict, self.EXPECTED, 10) == pytest.approx(
            1 / 3
        )

    def test_k_cutoff_applies(self):
        entries = [{"search/hybrid_searcher.py"}, {"search/searcher.py"}]
        assert calculate_file_recall_at_k(entries, self.EXPECTED, 1) == pytest.approx(
            1 / 3
        )

    def test_duplicate_files_across_ranks_not_double_counted(self):
        entries = [{"search/searcher.py"}, {"search/searcher.py"}]
        assert calculate_file_recall_at_k(entries, self.EXPECTED, 5) == pytest.approx(
            1 / 3
        )

    def test_expected_paths_normalized(self):
        entries = [{"search/indexer.py"}]
        assert calculate_file_recall_at_k(entries, ["search\\indexer.py"], 5) == 1.0

    def test_empty_expected_returns_zero(self):
        assert calculate_file_recall_at_k([{"a.py"}], [], 5) == 0.0


class TestBuildCommunityMembership:
    def test_pairs_from_named_chunks(self):
        membership = build_community_membership(COMMUNITY_MAP)
        assert ("search/hybrid_searcher.py", "HybridSearcher") in membership[7]
        assert ("search/indexer.py", "index_project") in membership[7]

    def test_nameless_module_ids_skipped(self):
        membership = build_community_membership(COMMUNITY_MAP)
        assert membership[9] == frozenset({("graph/storage.py", "GraphStorage")})

    def test_empty_map(self):
        assert build_community_membership({}) == {}


class TestExpandRetrievedWithCommunityCredit:
    GOLD = "search/searcher.py:class:IntelligentSearcher"

    def test_community_chunk_credits_member_gold(self):
        raw = [
            "__community__/search_HybridSearcher:0-0:community:search_HybridSearcher"
        ]
        entries = expand_retrieved_with_community_credit(
            raw,
            [["community:7"]],
            [self.GOLD],
            build_community_membership(COMMUNITY_MAP),
        )
        assert len(entries) == 1
        assert isinstance(entries[0], set)
        assert self.GOLD in entries[0]
        assert calculate_mrr(entries, [self.GOLD]) == 1.0

    def test_non_community_results_pass_through(self):
        raw = ["search/config.py:1-10:class:SearchConfig"]
        entries = expand_retrieved_with_community_credit(
            raw,
            [["lang:python"]],
            [self.GOLD],
            build_community_membership(COMMUNITY_MAP),
        )
        assert entries == normalize_chunk_ids(raw)

    def test_community_without_contained_gold_stays_plain(self):
        raw = ["__community__/graph_GraphStorage:0-0:community:graph_GraphStorage"]
        entries = expand_retrieved_with_community_credit(
            raw,
            [["community:9"]],
            [self.GOLD],
            build_community_membership(COMMUNITY_MAP),
        )
        assert entries == normalize_chunk_ids(raw)

    def test_empty_membership_is_noop(self):
        # Detection-off arms have no communities; callers report N/A, and the
        # expansion itself must degrade to plain normalization.
        raw = ["a.py:1-10:function:foo", "b.py:5-9:function:bar"]
        entries = expand_retrieved_with_community_credit(
            raw, [["community:1"], None], [self.GOLD], {}
        )
        assert entries == normalize_chunk_ids(raw)

    def test_dedup_by_normalized_own_id(self):
        raw = ["a.py:1-10:function:foo", "a.py:12-20:function:foo"]
        entries = expand_retrieved_with_community_credit(raw, [None, None], [], {})
        assert entries == ["a.py:function:foo"]

    def test_nameless_gold_never_credited(self):
        # graph/storage.py:1-8:module has no symbol name → no member pair
        gold_module = "graph/storage.py:module"
        raw = ["__community__/graph_GraphStorage:0-0:community:graph_GraphStorage"]
        entries = expand_retrieved_with_community_credit(
            raw,
            [["community:9"]],
            [gold_module],
            build_community_membership(COMMUNITY_MAP),
        )
        assert entries == normalize_chunk_ids(raw)
