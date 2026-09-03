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


# ---------------------------------------------------------------------------
# split_block folding (ADR-0061): callee lines inside a long method must
# resolve to that method, not to the enclosing class.
# ---------------------------------------------------------------------------

CLASS_ID = "search/indexer.py:100-400:class:CodeIndexManager"
PREV_METHOD_ID = "search/indexer.py:120-178:method:CodeIndexManager.create_index"
SPLIT_1 = "search/indexer.py:182-217:split_block:CodeIndexManager.add_embeddings"
SPLIT_2 = "search/indexer.py:219-281:split_block:CodeIndexManager.add_embeddings"
NEXT_METHOD_ID = "search/indexer.py:284-400:method:CodeIndexManager.search"
SPLIT_NORM = "search/indexer.py:method:CodeIndexManager.add_embeddings"


def _split_store() -> dict[str, dict[str, dict[str, object]]]:
    """A class whose middle method is chunked as two split_block fragments.

    Mirrors the live self-index: the ``def add_embeddings`` line is 181, the
    first fragment starts at the docstring (182), and no chunk of any kind
    covers 179-181.
    """
    return _make_store(
        (CLASS_ID, "search/indexer.py", 100, 400, "class"),
        (PREV_METHOD_ID, "search/indexer.py", 120, 178, "method"),
        (SPLIT_2, "search/indexer.py", 219, 281, "split_block"),  # out of order
        (SPLIT_1, "search/indexer.py", 182, 217, "split_block"),
        (NEXT_METHOD_ID, "search/indexer.py", 284, 400, "method"),
    )


class TestSplitBlockFolding:
    def test_split_block_included_by_default(self) -> None:
        line_map = build_line_to_chunk_map(_split_store(), normalize=False)
        ids = {cid for _, _, cid in line_map["search/indexer.py"]}
        assert SPLIT_1 in ids

    def test_fragments_fold_into_one_span(self) -> None:
        line_map = build_line_to_chunk_map(_split_store(), normalize=False)
        spans = [s for s in line_map["search/indexer.py"] if ":split_block:" in s[2]]
        assert len(spans) == 1
        start, end, cid = spans[0]
        # From the line after the previous sibling to the last fragment's end.
        assert (start, end) == (179, 281)
        # Keyed to the first (lowest start_line) fragment, an existing graph node.
        assert cid == SPLIT_1

    def test_def_line_resolves_to_method_not_class(self) -> None:
        """The LSP / pyan callee line is the ``def`` line, outside every fragment."""
        line_map = build_line_to_chunk_map(_split_store(), normalize=False)
        assert find_enclosing_chunk(line_map, "search/indexer.py", 181) == SPLIT_1

    def test_body_line_in_any_fragment_resolves_to_first_fragment(self) -> None:
        line_map = build_line_to_chunk_map(_split_store(), normalize=False)
        assert find_enclosing_chunk(line_map, "search/indexer.py", 200) == SPLIT_1
        assert find_enclosing_chunk(line_map, "search/indexer.py", 250) == SPLIT_1
        # The blank line between fragments belongs to the method too.
        assert find_enclosing_chunk(line_map, "search/indexer.py", 218) == SPLIT_1

    def test_class_statement_still_resolves_to_class(self) -> None:
        line_map = build_line_to_chunk_map(_split_store(), normalize=False)
        assert find_enclosing_chunk(line_map, "search/indexer.py", 100) == CLASS_ID
        assert find_enclosing_chunk(line_map, "search/indexer.py", 283) == CLASS_ID

    def test_siblings_unaffected(self) -> None:
        line_map = build_line_to_chunk_map(_split_store(), normalize=False)
        assert (
            find_enclosing_chunk(line_map, "search/indexer.py", 178) == PREV_METHOD_ID
        )
        assert (
            find_enclosing_chunk(line_map, "search/indexer.py", 284) == NEXT_METHOD_ID
        )

    def test_normalized_map_uses_parent_kind_key(self) -> None:
        line_map = build_line_to_chunk_map(_split_store(), normalize=True)
        assert find_enclosing_chunk(line_map, "search/indexer.py", 181) == SPLIT_NORM
        spans = [s for s in line_map["search/indexer.py"] if s[2] == SPLIT_NORM]
        assert spans == [(179, 281, SPLIT_NORM)]

    def test_first_member_bounded_by_class_statement(self) -> None:
        """No previous sibling: extend up to, but not over, the class line."""
        store = _make_store(
            ("f.py:10-90:class:K", "f.py", 10, 90, "class"),
            ("f.py:14-40:split_block:K.big", "f.py", 14, 40, "split_block"),
            ("f.py:41-90:split_block:K.big", "f.py", 41, 90, "split_block"),
        )
        line_map = build_line_to_chunk_map(store, normalize=False)
        assert find_enclosing_chunk(line_map, "f.py", 10) == "f.py:10-90:class:K"
        assert (
            find_enclosing_chunk(line_map, "f.py", 11) == "f.py:14-40:split_block:K.big"
        )
        assert (
            find_enclosing_chunk(line_map, "f.py", 13) == "f.py:14-40:split_block:K.big"
        )

    def test_decorated_container_keeps_its_own_statement_line(self) -> None:
        """A decorated class starts at the decorator; its ``class`` line is later."""
        store = {
            "f.py:10-90:decorated_definition:K": {
                "metadata": {
                    "relative_path": "f.py",
                    "start_line": 10,
                    "end_line": 90,
                    "chunk_type": "decorated_definition",
                    "decorators": ["@dataclass", "@final"],
                }
            },
            **_make_store(
                ("f.py:16-40:split_block:K.big", "f.py", 16, 40, "split_block"),
                ("f.py:41-90:split_block:K.big", "f.py", 41, 90, "split_block"),
            ),
        }
        line_map = build_line_to_chunk_map(store, normalize=False)
        # Lines 10-12 are the two decorators and the ``class`` statement.
        for line in (10, 11, 12):
            assert (
                find_enclosing_chunk(line_map, "f.py", line)
                == "f.py:10-90:decorated_definition:K"
            )
        assert (
            find_enclosing_chunk(line_map, "f.py", 13) == "f.py:16-40:split_block:K.big"
        )

    def test_multi_line_decorator_counts_its_source_lines(self) -> None:
        """Decorator text is the full node text and may span lines (review #66)."""
        store = {
            "f.py:10-90:decorated_definition:K": {
                "metadata": {
                    "relative_path": "f.py",
                    "start_line": 10,
                    "end_line": 90,
                    "chunk_type": "decorated_definition",
                    # Lines 10-13: a three-line decorator, then ``class K:``.
                    "decorators": ["@register(\n    name='k',\n)"],
                }
            },
            **_make_store(
                ("f.py:17-40:split_block:K.big", "f.py", 17, 40, "split_block"),
                ("f.py:41-90:split_block:K.big", "f.py", 41, 90, "split_block"),
            ),
        }
        line_map = build_line_to_chunk_map(store, normalize=False)
        for line in (10, 11, 12, 13):
            assert (
                find_enclosing_chunk(line_map, "f.py", line)
                == "f.py:10-90:decorated_definition:K"
            )
        assert (
            find_enclosing_chunk(line_map, "f.py", 14) == "f.py:17-40:split_block:K.big"
        )

    def test_module_level_split_function_extends_to_previous_chunk(self) -> None:
        """Non-semantic chunks (module preamble) still bound the definition."""
        store = _make_store(
            ("f.py:1-8:module_preamble:f", "f.py", 1, 8, "module_preamble"),
            ("f.py:12-60:split_block:main", "f.py", 12, 60, "split_block"),
            ("f.py:61-120:split_block:main", "f.py", 61, 120, "split_block"),
        )
        line_map = build_line_to_chunk_map(store, normalize=False)
        assert line_map["f.py"] == [(9, 120, "f.py:12-60:split_block:main")]
        assert find_enclosing_chunk(line_map, "f.py", 8) is None

    def test_split_function_with_no_preceding_chunk_extends_to_line_one(self) -> None:
        store = _make_store(
            ("f.py:5-30:split_block:main", "f.py", 5, 30, "split_block"),
            ("f.py:31-50:split_block:main", "f.py", 31, 50, "split_block"),
        )
        line_map = build_line_to_chunk_map(store, normalize=False)
        assert line_map["f.py"] == [(1, 50, "f.py:5-30:split_block:main")]

    def test_two_split_methods_in_one_class_stay_separate(self) -> None:
        store = _make_store(
            ("f.py:1-100:class:K", "f.py", 1, 100, "class"),
            ("f.py:4-30:split_block:K.a", "f.py", 4, 30, "split_block"),
            ("f.py:31-50:split_block:K.a", "f.py", 31, 50, "split_block"),
            ("f.py:54-80:split_block:K.b", "f.py", 54, 80, "split_block"),
            ("f.py:81-100:split_block:K.b", "f.py", 81, 100, "split_block"),
        )
        line_map = build_line_to_chunk_map(store, normalize=False)
        assert find_enclosing_chunk(line_map, "f.py", 3) == "f.py:4-30:split_block:K.a"
        assert (
            find_enclosing_chunk(line_map, "f.py", 52) == "f.py:54-80:split_block:K.b"
        )
        assert find_enclosing_chunk(line_map, "f.py", 1) == "f.py:1-100:class:K"

    def test_split_block_excluded_when_not_in_semantic_types(self) -> None:
        """Opting out reproduces the pre-ADR-0061 behaviour (class wins)."""
        line_map = build_line_to_chunk_map(
            _split_store(),
            semantic_types=frozenset({"function", "method", "class"}),
            normalize=False,
        )
        assert find_enclosing_chunk(line_map, "search/indexer.py", 181) == CLASS_ID

    def test_chunk_id_from_fqn_finds_folded_split_symbol(self) -> None:
        line_map = build_line_to_chunk_map(_split_store(), normalize=False)
        result = chunk_id_from_fqn(
            "search.indexer.CodeIndexManager.add_embeddings", line_map, Path(".")
        )
        assert result == SPLIT_1


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
        """A file that exists but lacks the name doesn't stop the split search."""
        deeper = "a/b.py:1-3:function:c"
        line_map = {
            "a/b/c.py": [(1, 3, "a/b/c.py:1-3:function:other")],
            "a/b.py": [(1, 3, deeper)],
        }
        assert chunk_id_from_fqn("a.b.c", line_map, Path(".")) == deeper
