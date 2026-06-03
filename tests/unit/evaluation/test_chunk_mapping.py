"""Unit tests for evaluation.chunk_mapping."""

from __future__ import annotations

from pathlib import Path

from evaluation.chunk_mapping import (
    build_line_to_chunk_map,
    chunk_id_from_fqn,
    find_enclosing_chunk,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(*entries: tuple[str, str, int, int, str]) -> dict:
    """Build a minimal metadata_store dict.

    Each entry is (raw_id, relative_path, start_line, end_line, chunk_type).
    """
    store = {}
    for raw_id, rel_path, start, end, chunk_type in entries:
        store[raw_id] = {
            "metadata": {
                "relative_path": rel_path,
                "start_line": start,
                "end_line": end,
                "chunk_type": chunk_type,
            }
        }
    return store


# ---------------------------------------------------------------------------
# build_line_to_chunk_map
# ---------------------------------------------------------------------------


class TestBuildLineToChunkMap:
    def test_normalize_true_strips_line_range(self) -> None:
        store = _make_store(
            ("pkg/a.py:10-20:function:helper", "pkg/a.py", 10, 20, "function"),
        )
        line_map = build_line_to_chunk_map(store, normalize=True)
        assert "pkg/a.py" in line_map
        _, _, cid = line_map["pkg/a.py"][0]
        assert ":10-20:" not in cid
        assert cid == "pkg/a.py:function:helper"

    def test_normalize_false_keeps_raw_id(self) -> None:
        raw_id = "pkg/a.py:10-20:function:helper"
        store = _make_store((raw_id, "pkg/a.py", 10, 20, "function"))
        line_map = build_line_to_chunk_map(store, normalize=False)
        _, _, cid = line_map["pkg/a.py"][0]
        assert cid == raw_id

    def test_sorted_by_start_line(self) -> None:
        store = _make_store(
            ("f.py:30-40:function:b", "f.py", 30, 40, "function"),
            ("f.py:10-20:function:a", "f.py", 10, 20, "function"),
        )
        line_map = build_line_to_chunk_map(store)
        starts = [s for s, _, _ in line_map["f.py"]]
        assert starts == sorted(starts)

    def test_non_semantic_type_excluded_by_default(self) -> None:
        store = _make_store(
            ("f.py:1-5:import:x", "f.py", 1, 5, "import"),
        )
        line_map = build_line_to_chunk_map(store)
        assert "f.py" not in line_map

    def test_custom_semantic_types(self) -> None:
        store = _make_store(
            ("f.py:1-5:import:x", "f.py", 1, 5, "import"),
            ("f.py:6-10:function:y", "f.py", 6, 10, "function"),
        )
        line_map = build_line_to_chunk_map(store, semantic_types=frozenset({"import"}))
        assert "f.py" in line_map
        _, _, cid = line_map["f.py"][0]
        assert "x" in cid

    def test_windows_backslash_relative_path_normalized(self) -> None:
        """Windows-style backslash relative_path must be normalized to forward slashes."""
        store = {
            "pkg/a.py:10-20:function:helper": {
                "metadata": {
                    "relative_path": "pkg\\a.py",  # Windows backslash
                    "start_line": 10,
                    "end_line": 20,
                    "chunk_type": "function",
                }
            }
        }
        line_map = build_line_to_chunk_map(store, normalize=False)
        # Key must be normalized to forward slashes
        assert "pkg/a.py" in line_map
        assert "pkg\\a.py" not in line_map

    def test_missing_relative_path_skipped(self) -> None:
        store = {
            "bad:1-5:function:f": {
                "metadata": {"start_line": 1, "end_line": 5, "chunk_type": "function"}
            }
        }
        line_map = build_line_to_chunk_map(store)
        assert not line_map


# ---------------------------------------------------------------------------
# find_enclosing_chunk
# ---------------------------------------------------------------------------


class TestFindEnclosingChunk:
    def test_exact_start_line(self) -> None:
        line_map = {"f.py": [(10, 20, "cid_A")]}
        assert find_enclosing_chunk(line_map, "f.py", 10) == "cid_A"

    def test_exact_end_line(self) -> None:
        line_map = {"f.py": [(10, 20, "cid_A")]}
        assert find_enclosing_chunk(line_map, "f.py", 20) == "cid_A"

    def test_line_before_range_returns_none(self) -> None:
        line_map = {"f.py": [(10, 20, "cid_A")]}
        assert find_enclosing_chunk(line_map, "f.py", 9) is None

    def test_line_after_range_returns_none(self) -> None:
        line_map = {"f.py": [(10, 20, "cid_A")]}
        assert find_enclosing_chunk(line_map, "f.py", 21) is None

    def test_picks_innermost_nested_chunk(self) -> None:
        """Method chunk nested inside class chunk: method wins (smaller span)."""
        line_map = {
            "f.py": [
                (1, 30, "cid_class"),  # class spans lines 1-30
                (5, 10, "cid_method"),  # method spans lines 5-10
            ]
        }
        assert find_enclosing_chunk(line_map, "f.py", 7) == "cid_method"

    def test_unknown_file_returns_none(self) -> None:
        line_map = {"f.py": [(1, 10, "cid_A")]}
        assert find_enclosing_chunk(line_map, "other.py", 5) is None


# ---------------------------------------------------------------------------
# chunk_id_from_fqn
# ---------------------------------------------------------------------------


class TestChunkIdFromFqn:
    def test_simple_function_fqn(self) -> None:
        line_map = {
            "evaluation/metrics.py": [
                (1, 10, "evaluation/metrics.py:function:normalize_chunk_id"),
            ]
        }
        result = chunk_id_from_fqn(
            "evaluation.metrics.normalize_chunk_id", line_map, Path(".")
        )
        assert result == "evaluation/metrics.py:function:normalize_chunk_id"

    def test_method_fqn(self) -> None:
        line_map = {
            "search/hybrid_searcher.py": [
                (
                    50,
                    60,
                    "search/hybrid_searcher.py:method:HybridSearcher.get_by_chunk_id",
                ),
            ]
        }
        result = chunk_id_from_fqn(
            "search.hybrid_searcher.HybridSearcher.get_by_chunk_id",
            line_map,
            Path("."),
        )
        assert (
            result == "search/hybrid_searcher.py:method:HybridSearcher.get_by_chunk_id"
        )

    def test_unknown_fqn_returns_none(self) -> None:
        line_map: dict = {}
        result = chunk_id_from_fqn("some.unknown.Symbol", line_map, Path("."))
        assert result is None

    def test_raw_id_lookup(self) -> None:
        """normalize=False map: chunk_id_from_fqn still finds the entry."""
        raw_id = "a/b.py:5-15:function:do_thing"
        line_map = {
            "a/b.py": [(5, 15, raw_id)],
        }
        result = chunk_id_from_fqn("a.b.do_thing", line_map, Path("."))
        assert result == raw_id
