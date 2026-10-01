"""Unit tests for RerankWindowPolicy (ADR-0079)."""

import dataclasses

import pytest

from search.rerank_window_policy import RerankWindowPolicy


class TestTail:
    def test_tail_does_not_interleave(self):
        assert RerankWindowPolicy.tail().interleave is False

    def test_tail_matches_bare_construction(self):
        assert RerankWindowPolicy.tail() == RerankWindowPolicy()


class TestMergedPool:
    def test_merged_pool_interleaves(self):
        assert RerankWindowPolicy.merged_pool().interleave is True


class TestFrozen:
    def test_policy_is_frozen(self):
        window = RerankWindowPolicy.tail()

        with pytest.raises(dataclasses.FrozenInstanceError):
            window.interleave = True
