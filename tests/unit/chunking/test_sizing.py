"""Unit tests for chunking.sizing: SizePolicy constructors and measure()."""

from types import SimpleNamespace

import pytest

from chunking.repo_profiler import RepoProfile
from chunking.sizing import SizePolicy, compute_adaptive_threshold
from search.config import ChunkingConfig


def _node(start_byte: int, end_byte: int) -> SimpleNamespace:
    return SimpleNamespace(start_byte=start_byte, end_byte=end_byte)


def _profile(p75: int = 1000, max_complexity: int = 30) -> RepoProfile:
    return RepoProfile(
        function_count=100,
        p25_chars=300,
        p50_chars=500,
        p75_chars=p75,
        p90_chars=2000,
        mean_chars=700,
        max_complexity=max_complexity,
    )


class TestMeasure:
    SOURCE = b"a b\nc d\ne f"

    def test_empty_nodes_measure_zero(self):
        assert SizePolicy(threshold=1, unit="lines").measure([], self.SOURCE) == 0

    def test_lines_counts_span_lines(self):
        nodes = [_node(0, 3), _node(8, 11)]
        assert SizePolicy(threshold=1, unit="lines").measure(nodes, self.SOURCE) == 3

    def test_characters_counts_non_whitespace(self):
        nodes = [_node(0, 3), _node(8, 11)]
        # span is the whole buffer: "a b\nc d\ne f" -> 6 non-whitespace chars
        assert (
            SizePolicy(threshold=1, unit="characters").measure(nodes, self.SOURCE) == 6
        )

    def test_unknown_unit_falls_back_to_lines(self):
        nodes = [_node(0, 11)]
        assert SizePolicy(threshold=1, unit="bogus").measure(nodes, self.SOURCE) == 3


class TestForPreamble:
    def test_uses_static_max_split_chars_for_characters(self):
        cfg = ChunkingConfig(split_size_method="characters", max_split_chars=1234)
        assert SizePolicy.for_preamble(cfg) == SizePolicy(1234, "characters")

    def test_uses_max_chunk_lines_for_lines(self):
        cfg = ChunkingConfig(split_size_method="lines", max_chunk_lines=77)
        assert SizePolicy.for_preamble(cfg) == SizePolicy(77, "lines")

    def test_never_adaptive(self):
        cfg = ChunkingConfig(
            split_size_method="characters", sizing_mode="adaptive", max_split_chars=1234
        )
        assert SizePolicy.for_preamble(cfg).threshold == 1234


class TestForFunction:
    @staticmethod
    def _never_called() -> int:
        raise AssertionError("node_complexity must not be called")

    def test_fixed_mode_uses_static_threshold_and_skips_complexity(self):
        cfg = ChunkingConfig(
            split_size_method="characters", sizing_mode="fixed", max_split_chars=1500
        )
        policy = SizePolicy.for_function(cfg, _profile(), self._never_called)
        assert policy == SizePolicy(1500, "characters")

    def test_adaptive_without_profile_is_static_and_skips_complexity(self):
        cfg = ChunkingConfig(
            split_size_method="characters", sizing_mode="adaptive", max_split_chars=1500
        )
        policy = SizePolicy.for_function(cfg, None, self._never_called)
        assert policy == SizePolicy(1500, "characters")

    def test_adaptive_with_empty_p75_is_static(self):
        cfg = ChunkingConfig(
            split_size_method="characters", sizing_mode="adaptive", max_split_chars=1500
        )
        policy = SizePolicy.for_function(cfg, _profile(p75=0), self._never_called)
        assert policy.threshold == 1500

    def test_adaptive_modulates_by_complexity(self):
        cfg = ChunkingConfig(split_size_method="characters", sizing_mode="adaptive")
        profile = _profile(p75=1000, max_complexity=30)
        calls: list[int] = []

        def complexity() -> int:
            calls.append(1)
            return 15

        policy = SizePolicy.for_function(cfg, profile, complexity)
        assert calls == [1]
        assert policy.unit == "characters"
        assert policy.threshold == compute_adaptive_threshold(
            complexity=15,
            base_threshold=1000,
            max_complexity=30,
            multiplier_max=cfg.adaptive_multiplier_max,
            multiplier_min=cfg.adaptive_multiplier_min,
        )

    def test_adaptive_with_lines_unit_computes_then_ignores(self):
        cfg = ChunkingConfig(
            split_size_method="lines", sizing_mode="adaptive", max_chunk_lines=42
        )
        calls: list[int] = []

        def complexity() -> int:
            calls.append(1)
            return 5

        policy = SizePolicy.for_function(cfg, _profile(), complexity)
        assert calls == [1]
        assert policy == SizePolicy(42, "lines")

    def test_unknown_unit_falls_back_to_max_chunk_lines(self):
        cfg = ChunkingConfig(split_size_method="bogus", max_chunk_lines=42)
        policy = SizePolicy.for_function(cfg, None, self._never_called)
        assert policy.threshold == 42


def test_policy_is_frozen():
    with pytest.raises(AttributeError):
        SizePolicy(1, "lines").threshold = 2  # type: ignore[misc]
