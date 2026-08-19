"""Unit tests for RerankWindowPolicy (C2 step 3: parameter object)."""

import dataclasses

import pytest

from search.config import RerankerConfig, SearchConfig
from search.rerank_window_policy import RerankWindowPolicy


class TestTail:
    def test_tail_is_all_defaults(self):
        window = RerankWindowPolicy.tail()

        assert window.hop1_reserved_slots == 0
        assert window.merged_pool_policy == "score"
        assert window.graph_hop_window_cap == 0
        assert window.graph_hop_unscored is False

    def test_tail_matches_bare_construction(self):
        assert RerankWindowPolicy.tail() == RerankWindowPolicy()


class TestMergedPool:
    def test_merged_pool_reads_the_three_knobs_off_config(self):
        config = SearchConfig(
            reranker=RerankerConfig(
                hop1_reserved_slots=6,
                merged_pool_policy="channel_priority",
                graph_hop_window_cap=3,
            )
        )

        window = RerankWindowPolicy.merged_pool(config)

        assert window.hop1_reserved_slots == 6
        assert window.merged_pool_policy == "channel_priority"
        assert window.graph_hop_window_cap == 3

    def test_merged_pool_derives_graph_hop_unscored_true_when_a1_off(self):
        """graph_hop_call_evidence_enabled defaults False, so graph_hop
        candidates carry the ADR-0039 fabricated placeholder — unscored."""
        window = RerankWindowPolicy.merged_pool(SearchConfig())

        assert window.graph_hop_unscored is True

    def test_merged_pool_derives_graph_hop_unscored_false_when_a1_on(self):
        """With the A1 call-evidence scorer on, graph_hop candidates carry
        real anchor-conditioned scores — not the placeholder."""
        config = SearchConfig()
        config.graph_enhanced.graph_hop_call_evidence_enabled = True

        window = RerankWindowPolicy.merged_pool(config)

        assert window.graph_hop_unscored is False


class TestFrozen:
    def test_policy_is_frozen(self):
        window = RerankWindowPolicy.tail()

        with pytest.raises(dataclasses.FrozenInstanceError):
            window.hop1_reserved_slots = 6
