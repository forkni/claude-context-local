"""Unit tests for search.chunk_id — the single owner of the chunk_id wire format."""

import pytest

from search.chunk_id import (
    MIN_CHUNK_ID_COLONS,
    ChunkId,
    extract_line_count,
    extract_name,
    is_chunk_id,
    normalize,
    strip_line_range,
)


# ---------------------------------------------------------------------------
# is_chunk_id
# ---------------------------------------------------------------------------


class TestIsChunkId:
    def test_valid_function(self):
        assert is_chunk_id("search/filters.py:22-31:function:normalize_path") is True

    def test_valid_method(self):
        assert (
            is_chunk_id("search/searcher.py:37-52:method:IntelligentSearcher.__init__")
            is True
        )

    def test_valid_split_block(self):
        assert (
            is_chunk_id(
                "search/hybrid_searcher.py:100-200:split_block:HybridSearcher.__init__"
            )
            is True
        )

    def test_bare_symbol(self):
        assert is_chunk_id("login") is False

    def test_exception_name(self):
        assert is_chunk_id("Exception") is False

    def test_two_colons(self):
        assert is_chunk_id("a:b:c") is False

    def test_exactly_three_colons(self):
        assert is_chunk_id("a:b:c:d") is True

    def test_min_colon_constant(self):
        assert MIN_CHUNK_ID_COLONS == 3


# ---------------------------------------------------------------------------
# ChunkId.parse
# ---------------------------------------------------------------------------


class TestChunkIdParse:
    def test_parse_function(self):
        cid = ChunkId.parse("search/filters.py:22-31:function:normalize_path")
        assert cid is not None
        assert cid.file_path == "search/filters.py"
        assert cid.line_start == 22
        assert cid.line_end == 31
        assert cid.kind == "function"
        assert cid.name == "normalize_path"

    def test_parse_qualified_name(self):
        cid = ChunkId.parse(
            "search/searcher.py:37-52:method:IntelligentSearcher.__init__"
        )
        assert cid is not None
        assert cid.name == "IntelligentSearcher.__init__"
        assert cid.kind == "method"

    def test_parse_windows_backslash(self):
        """File path with Windows backslashes must be normalized."""
        cid = ChunkId.parse("search\\reranker.py:36-137:method:rerank")
        assert cid is not None
        assert cid.file_path == "search/reranker.py"
        assert cid.name == "rerank"

    def test_parse_bare_symbol_returns_none(self):
        assert ChunkId.parse("login") is None

    def test_parse_exception_returns_none(self):
        assert ChunkId.parse("Exception") is None

    def test_parse_garbled_line_range_returns_none(self):
        assert ChunkId.parse("search/foo.py:abc-xyz:function:bar") is None

    def test_parse_missing_line_range_returns_none(self):
        assert ChunkId.parse("search/foo.py:function:bar") is None

    def test_parse_large_range(self):
        cid = ChunkId.parse("embeddings/embedder.py:276-1330:class:CodeEmbedder")
        assert cid is not None
        assert cid.line_start == 276
        assert cid.line_end == 1330


# ---------------------------------------------------------------------------
# ChunkId properties / methods
# ---------------------------------------------------------------------------


class TestChunkIdProperties:
    def test_line_count(self):
        cid = ChunkId.parse("search/filters.py:22-31:function:normalize_path")
        assert cid.line_count == 10  # 31 - 22 + 1

    def test_line_count_single_line(self):
        cid = ChunkId.parse("search/x.py:5-5:function:noop")
        assert cid.line_count == 1

    def test_without_line_range(self):
        cid = ChunkId.parse("search/filters.py:22-31:function:normalize_path")
        assert cid.without_line_range() == "search/filters.py:function:normalize_path"

    def test_str_round_trip(self):
        raw = "search/filters.py:22-31:function:normalize_path"
        cid = ChunkId.parse(raw)
        assert str(cid) == raw

    def test_str_round_trip_qualified(self):
        raw = "search/searcher.py:37-52:method:IntelligentSearcher.__init__"
        cid = ChunkId.parse(raw)
        assert str(cid) == raw

    def test_frozen_immutable(self):
        cid = ChunkId.parse("search/filters.py:22-31:function:normalize_path")
        with pytest.raises((AttributeError, TypeError)):
            cid.name = "other"  # type: ignore[misc]

    def test_split_block_dedup_same_function(self):
        """Two split_block pieces of the same function share without_line_range()."""
        cid1 = ChunkId.parse(
            "search/hybrid_searcher.py:50-200:split_block:HybridSearcher.__init__"
        )
        cid2 = ChunkId.parse(
            "search/hybrid_searcher.py:201-350:split_block:HybridSearcher.__init__"
        )
        assert cid1 is not None and cid2 is not None
        assert cid1.without_line_range() == cid2.without_line_range()


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_forward_slashes_unchanged(self):
        raw = "search/reranker.py:36-137:method:rerank"
        assert normalize(raw) == raw

    def test_windows_backslash(self):
        raw = "search\\reranker.py:36-137:method:rerank"
        assert normalize(raw) == "search/reranker.py:36-137:method:rerank"

    def test_deep_path(self):
        raw = "chunking\\relationships\\call_graph_extractor.py:10-50:class:Foo"
        assert (
            normalize(raw)
            == "chunking/relationships/call_graph_extractor.py:10-50:class:Foo"
        )

    def test_short_string_passthrough(self):
        # Less than 4 components: normalizes whole string as path
        raw = "login"
        assert normalize(raw) == "login"


# ---------------------------------------------------------------------------
# extract_name
# ---------------------------------------------------------------------------


class TestExtractName:
    def test_function(self):
        assert (
            extract_name("search/filters.py:22-31:function:normalize_path")
            == "normalize_path"
        )

    def test_qualified_method(self):
        assert (
            extract_name("search/searcher.py:37-52:method:IntelligentSearcher.__init__")
            == "IntelligentSearcher.__init__"
        )

    def test_bare_symbol_returns_empty(self):
        assert extract_name("login") == ""

    def test_three_colons_no_name_returns_empty(self):
        # Only 3 components: "a", "b", "c" — no 4th part
        assert extract_name("a:b:c") == ""


# ---------------------------------------------------------------------------
# extract_line_count
# ---------------------------------------------------------------------------


class TestExtractLineCount:
    def test_normal_range(self):
        assert (
            extract_line_count("embeddings/embedder.py:276-1330:class:CodeEmbedder")
            == 1055
        )

    def test_small_range(self):
        assert (
            extract_line_count("search/filters.py:22-31:function:normalize_path") == 10
        )

    def test_single_line(self):
        assert extract_line_count("search/x.py:5-5:function:noop") == 1

    def test_malformed_no_range(self):
        assert extract_line_count("invalid:format") == 0

    def test_malformed_non_numeric(self):
        assert extract_line_count("search/foo.py:abc-xyz:function:bar") == 0

    def test_too_few_parts(self):
        assert extract_line_count("only_one_part") == 0


# ---------------------------------------------------------------------------
# strip_line_range
# ---------------------------------------------------------------------------


class TestStripLineRange:
    def test_strips_range(self):
        assert (
            strip_line_range("search/filters.py:22-31:function:normalize_path")
            == "search/filters.py:function:normalize_path"
        )

    def test_qualified_name_preserved(self):
        assert (
            strip_line_range(
                "search/searcher.py:37-52:method:IntelligentSearcher.__init__"
            )
            == "search/searcher.py:method:IntelligentSearcher.__init__"
        )

    def test_short_string_passthrough(self):
        assert strip_line_range("login") == "login"

    def test_split_block_dedup(self):
        """Two split_block pieces strip to the same string."""
        s1 = strip_line_range(
            "search/hybrid_searcher.py:50-200:split_block:HybridSearcher.__init__"
        )
        s2 = strip_line_range(
            "search/hybrid_searcher.py:201-350:split_block:HybridSearcher.__init__"
        )
        assert s1 == s2
