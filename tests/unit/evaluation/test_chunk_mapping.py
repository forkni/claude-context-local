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


class TestChunkIdFromFqnSameFileCollision:
    """Same bare name defined twice in one file: as a method and as a function.

    Mirrors ``utils/observability.py`` (``_NoopExporter.force_flush`` at
    line 76, module-level ``force_flush`` at line 90) — resolver precision
    row 11, 2026-09-02.  The method sorts first in the line map, so a pure
    suffix match used to return it for the *function* FQN.
    """

    METHOD = "utils/observability.py:76-77:method:_NoopExporter.force_flush"
    FUNCTION = "utils/observability.py:90-102:function:force_flush"

    def _line_map(self) -> dict:
        return {
            "utils/observability.py": [(76, 77, self.METHOD), (90, 102, self.FUNCTION)]
        }

    def test_function_fqn_prefers_module_function(self) -> None:
        result = chunk_id_from_fqn(
            "utils.observability.force_flush", self._line_map(), Path(".")
        )
        assert result == self.FUNCTION

    def test_method_fqn_prefers_method(self) -> None:
        result = chunk_id_from_fqn(
            "utils.observability._NoopExporter.force_flush",
            self._line_map(),
            Path("."),
        )
        assert result == self.METHOD

    def test_order_independent(self) -> None:
        """Result does not depend on which chunk sorts first in the file."""
        reversed_map = {
            "utils/observability.py": [(90, 102, self.FUNCTION), (76, 77, self.METHOD)]
        }
        assert (
            chunk_id_from_fqn(
                "utils.observability.force_flush", reversed_map, Path(".")
            )
            == self.FUNCTION
        )
        assert (
            chunk_id_from_fqn(
                "utils.observability._NoopExporter.force_flush",
                reversed_map,
                Path("."),
            )
            == self.METHOD
        )

    def test_normalized_ids_same_behaviour(self) -> None:
        method = "utils/observability.py:method:_NoopExporter.force_flush"
        function = "utils/observability.py:function:force_flush"
        line_map = {"utils/observability.py": [(76, 77, method), (90, 102, function)]}
        assert (
            chunk_id_from_fqn("utils.observability.force_flush", line_map, Path("."))
            == function
        )
        assert (
            chunk_id_from_fqn(
                "utils.observability._NoopExporter.force_flush", line_map, Path(".")
            )
            == method
        )


class TestChunkIdFromFqnFallbacks:
    def test_suffix_fallback_when_no_exact(self) -> None:
        """pyan-style FQN that omits the class still resolves via suffix."""
        method = "pkg/mod.py:10-20:method:Klass.run"
        line_map = {"pkg/mod.py": [(10, 20, method)]}
        assert chunk_id_from_fqn("pkg.mod.run", line_map, Path(".")) == method

    def test_shape_preference_among_suffix_candidates(self) -> None:
        """Synthetic: two suffix candidates, the kind matching the tail shape wins.

        Tail ``run`` is one part, so the ``function``-kind chunk is preferred
        over the ``method``-kind one regardless of file order.
        """
        method = "pkg/mod.py:5-8:method:Outer.run"
        function = "pkg/mod.py:20-30:function:Inner.run"
        ordered = {"pkg/mod.py": [(5, 8, method), (20, 30, function)]}
        flipped = {"pkg/mod.py": [(20, 30, function), (5, 8, method)]}
        assert chunk_id_from_fqn("pkg.mod.run", ordered, Path(".")) == function
        assert chunk_id_from_fqn("pkg.mod.run", flipped, Path(".")) == function

    def test_decorated_definition_uses_name_shape(self) -> None:
        """decorated_definition kind is shape-agnostic: name part count decides."""
        deco_method = "pkg/mod.py:5-8:decorated_definition:Klass.run"
        deco_func = "pkg/mod.py:20-30:decorated_definition:run"
        line_map = {"pkg/mod.py": [(5, 8, deco_method), (20, 30, deco_func)]}
        assert chunk_id_from_fqn("pkg.mod.run", line_map, Path(".")) == deco_func
        assert (
            chunk_id_from_fqn("pkg.mod.Klass.run", line_map, Path(".")) == deco_method
        )

    def test_tie_falls_back_to_file_order(self) -> None:
        """Identical shape and name (e.g. split_block halves): first in file wins."""
        first = "pkg/mod.py:5-8:split_block:run"
        second = "pkg/mod.py:9-12:split_block:run"
        line_map = {"pkg/mod.py": [(5, 8, first), (9, 12, second)]}
        assert chunk_id_from_fqn("pkg.mod.run", line_map, Path(".")) == first

    def test_file_present_but_no_match_continues_split(self) -> None:
        """A file that exists but lacks the name doesn't stop the split search.

        ``a.b.c`` first tries ``a/b.py`` with tail ``c``; that file has only
        ``other``, so the search continues to ``a.py`` with tail ``b.c``.
        """
        nested = "a.py:1-3:method:b.c"
        line_map = {
            "a/b.py": [(1, 3, "a/b.py:1-3:function:other")],
            "a.py": [(1, 3, nested)],
        }
        assert chunk_id_from_fqn("a.b.c", line_map, Path(".")) == nested

    def test_id_without_kind_segment_matches_by_name(self) -> None:
        """Defensive: an id with no kind segment still matches on its name."""
        bare = "pkg/mod.py:run"
        line_map = {"pkg/mod.py": [(1, 3, bare)]}
        assert chunk_id_from_fqn("pkg.mod.run", line_map, Path(".")) == bare
