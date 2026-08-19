"""Unit tests for mcp_server/tools/result_view.py's L3 signature view.

Covers the extractor (_extract_signature_estimate) ported from
scripts/benchmark/probe_context_cost.py, and the enricher
(_enrich_results_with_signatures) that attaches it via
CodeIndexManager.metadata_store.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from mcp_server.tools.result_view import (
    _enrich_results_with_signatures,
    _extract_signature_estimate,
    _format_search_results,
)
from search.reranker import SearchResult


class TestExtractSignatureEstimate:
    """Line-scan for a def/async def/class anchor, capped at max_lines; a
    bounded fallback when no anchor is found."""

    def test_anchored_python_function(self):
        text = "def foo(a, b):\n    return a + b\n"
        assert _extract_signature_estimate(text) == "def foo(a, b):"

    def test_decorated_def(self):
        text = "@decorator\ndef foo(a, b):\n    pass\n"
        assert _extract_signature_estimate(text) == "@decorator\ndef foo(a, b):"

    def test_multi_line_signature(self):
        text = "def foo(\n    a,\n    b,\n):\n    pass\n"
        assert _extract_signature_estimate(text) == "def foo(\n    a,\n    b,\n):"

    def test_async_def_anchor(self):
        text = "async def foo(a):\n    await bar()\n"
        assert _extract_signature_estimate(text) == "async def foo(a):"

    def test_class_anchor(self):
        text = "class Foo(Base):\n    x = 1\n"
        assert _extract_signature_estimate(text) == "class Foo(Base):"

    def test_go_shaped_chunk_uses_no_anchor_cap_not_15_lines(self):
        """A Go/Rust/C++-shaped chunk has no def/class keyword, so it must
        degrade to the 3-line no_anchor_lines cap, not the full 15-line
        anchored-scan body."""
        text = (
            "func Foo(a int, b int) int {\n"
            "\tsum := a + b\n"
            "\tsum *= 2\n"
            "\treturn sum\n"
            "}\n"
        )
        result = _extract_signature_estimate(text)
        assert result == "func Foo(a int, b int) int {\n\tsum := a + b\n\tsum *= 2"
        assert result.count("\n") == 2  # 3 lines, not the full 5-line body

    def test_module_preamble_chunk_uses_no_anchor_cap(self):
        text = 'import (\n\t"fmt"\n\t"os"\n)\n\nvar x = 1\n'
        result = _extract_signature_estimate(text)
        assert result == 'import (\n\t"fmt"\n\t"os"'

    def test_empty_text(self):
        assert _extract_signature_estimate("") == ""

    def test_custom_no_anchor_lines_cap(self):
        text = "line1\nline2\nline3\nline4\nline5\n"
        result = _extract_signature_estimate(text, no_anchor_lines=2)
        assert result == "line1\nline2"

    def test_minified_single_line_chunk_is_truncated_by_max_chars(self):
        """A minified-JS-shaped chunk (one giant unanchored 'line') must be
        bounded by max_chars, not just the line caps -- the line caps bound
        line *count*, not line *length*."""
        text = "x" * 5000
        result = _extract_signature_estimate(text)
        assert len(result) == 600

    def test_signature_exactly_at_max_chars_is_untouched(self):
        text = "x" * 600
        result = _extract_signature_estimate(text)
        assert result == text
        assert len(result) == 600

    def test_normal_multi_line_python_signature_unaffected_by_max_chars(self):
        text = "def foo(\n    a,\n    b,\n):\n    pass\n"
        result = _extract_signature_estimate(text)
        assert result == "def foo(\n    a,\n    b,\n):"

    def test_custom_max_chars_cap(self):
        text = "def foo(a, b):\n    return a + b\n"
        result = _extract_signature_estimate(text, max_chars=5)
        assert result == "def f"


class TestFormatSearchResults:
    """_format_search_results: SearchResult -> MCP JSON dict. Covers the
    ``is_unscored`` flag (D9) added for parent-expansion's fabricated 0.0."""

    def _result(self, **overrides):
        defaults = {
            "chunk_id": "a.py:1-2:function:foo",
            "score": 0.5,
            "metadata": {"relative_path": "a.py", "start_line": 1, "end_line": 2},
            "source": "bm25",
        }
        defaults.update(overrides)
        return SearchResult(**defaults)

    def test_ranked_result_has_no_is_unscored_key(self):
        """A normal, real-scored result must not carry the flag at all --
        matches the file's only-add-when-relevant convention."""
        out = _format_search_results([self._result(source="bm25", score=0.85)])
        assert "is_unscored" not in out[0]

    def test_parent_expansion_result_is_flagged_unscored(self):
        out = _format_search_results(
            [self._result(source="parent_expansion", score=0.0)]
        )
        assert out[0]["is_unscored"] is True
        assert out[0]["score"] == 0.0

    def test_graph_hop_zero_score_is_not_flagged_unscored(self):
        """graph_hop is deliberately excluded from UNSCORED_SOURCES (its
        unscored-ness is per-call, not a static property of the source tag,
        ADR-0039) -- a graph_hop result with score 0.0 must format the same
        as any other ranked result."""
        out = _format_search_results([self._result(source="graph_hop", score=0.0)])
        assert "is_unscored" not in out[0]

    def test_mixed_results_only_parent_expansion_flagged(self):
        results = [
            self._result(chunk_id="r0", source="bm25", score=0.9),
            self._result(chunk_id="p0", source="parent_expansion", score=0.0),
        ]
        out = _format_search_results(results)
        assert "is_unscored" not in out[0]
        assert out[1]["is_unscored"] is True


class TestEnrichResultsWithSignatures:
    """Attaches ``signature`` from metadata_store's bm25_text; degrades
    silently when data is absent, matching _enrich_results_with_top_callers's
    resilience style."""

    def _index_manager(self, bm25_text_by_chunk_id):
        store = MagicMock()

        def _get(chunk_id):
            text = bm25_text_by_chunk_id.get(chunk_id)
            if text is None:
                return None
            return {"metadata": {"bm25_text": text}}

        store.get.side_effect = _get
        manager = MagicMock()
        manager.metadata_store = store
        return manager

    def test_none_index_manager_returns_unchanged(self):
        results = [{"chunk_id": "a.py:1-2:function:foo"}]
        out = _enrich_results_with_signatures(results, None)
        assert out == results
        assert "signature" not in out[0]

    def test_absent_metadata_store_returns_unchanged(self):
        manager = MagicMock()
        manager.metadata_store = None
        results = [{"chunk_id": "a.py:1-2:function:foo"}]
        out = _enrich_results_with_signatures(results, manager)
        assert "signature" not in out[0]

    def test_happy_path_attaches_signature(self):
        chunk_id = "a.py:1-2:function:foo"
        manager = self._index_manager({chunk_id: "def foo(a, b):\n    return a + b\n"})
        results = [{"chunk_id": chunk_id}]
        out = _enrich_results_with_signatures(results, manager)
        assert out[0]["signature"] == "def foo(a, b):"

    def test_entry_not_found_skips_item(self):
        """metadata_store.get returns None (chunk_id not in the store)."""
        chunk_id = "a.py:1-2:function:foo"
        manager = self._index_manager({chunk_id: None})
        results = [{"chunk_id": chunk_id}]
        out = _enrich_results_with_signatures(results, manager)
        assert "signature" not in out[0]

    def test_empty_bm25_text_skips_item(self):
        """Entry found, but bm25_text is falsy (e.g. empty string)."""
        chunk_id = "a.py:1-2:function:foo"
        manager = self._index_manager({chunk_id: ""})
        results = [{"chunk_id": chunk_id}]
        out = _enrich_results_with_signatures(results, manager)
        assert "signature" not in out[0]

    def test_entry_present_without_bm25_text_key_skips_item(self):
        """Entry found, metadata dict has no bm25_text key at all."""
        chunk_id = "a.py:1-2:function:foo"
        manager = MagicMock()
        manager.metadata_store.get.return_value = {"metadata": {}}
        results = [{"chunk_id": chunk_id}]
        out = _enrich_results_with_signatures(results, manager)
        assert "signature" not in out[0]

    def test_missing_chunk_id_skips_item(self):
        results = [{"kind": "function"}]
        manager = self._index_manager({})
        out = _enrich_results_with_signatures(results, manager)
        assert "signature" not in out[0]

    def test_metadata_store_lookup_exception_degrades_silently(self):
        chunk_id = "a.py:1-2:function:foo"
        manager = MagicMock()
        manager.metadata_store.get.side_effect = RuntimeError("boom")
        results = [{"chunk_id": chunk_id}]
        out = _enrich_results_with_signatures(results, manager)
        assert "signature" not in out[0]

    def test_multiple_results_each_enriched_independently(self):
        manager = self._index_manager(
            {
                "a.py:1-2:function:foo": "def foo():\n    pass\n",
                "b.py:1-2:function:bar": None,
            }
        )
        results = [
            {"chunk_id": "a.py:1-2:function:foo"},
            {"chunk_id": "b.py:1-2:function:bar"},
        ]
        out = _enrich_results_with_signatures(results, manager)
        assert out[0]["signature"] == "def foo():"
        assert "signature" not in out[1]

    def test_module_kind_is_skipped_entirely(self):
        """module/module_preamble chunks carry no def/class anchor -- their
        'signature' would be filler (a docstring line, an import, a
        comment), not a callable contract. Gated on the result dict's
        existing `kind` field, so this must not even hit metadata_store."""
        chunk_id = "a.py:0-0:module:a"
        manager = self._index_manager({chunk_id: '"""Module docstring."""\n'})
        results = [{"chunk_id": chunk_id, "kind": "module"}]
        out = _enrich_results_with_signatures(results, manager)
        assert "signature" not in out[0]
        manager.metadata_store.get.assert_not_called()

    def test_module_preamble_kind_is_skipped_entirely(self):
        chunk_id = "a.py:1-10:module_preamble"
        manager = self._index_manager({chunk_id: "import os\nimport sys\n"})
        results = [{"chunk_id": chunk_id, "kind": "module_preamble"}]
        out = _enrich_results_with_signatures(results, manager)
        assert "signature" not in out[0]
        manager.metadata_store.get.assert_not_called()

    def test_function_kind_is_still_enriched_alongside_gated_kinds(self):
        """Guards against an over-broad gate: a real definition kind in the
        same result set as a gated kind must still get its signature."""
        manager = self._index_manager(
            {
                "a.py:1-2:function:foo": "def foo():\n    pass\n",
                "a.py:0-0:module:a": '"""Docstring."""\n',
            }
        )
        results = [
            {"chunk_id": "a.py:1-2:function:foo", "kind": "function"},
            {"chunk_id": "a.py:0-0:module:a", "kind": "module"},
        ]
        out = _enrich_results_with_signatures(results, manager)
        assert out[0]["signature"] == "def foo():"
        assert "signature" not in out[1]

    def test_go_shaped_function_kind_still_enriched(self):
        """Non-Python definition kinds (Go/Rust/C++/...) are un-anchored but
        must NOT be caught by the kind-gate -- only module/module_preamble
        are. Their 3-line excerpt is the only signature they have."""
        chunk_id = "a.go:1-5:function:Foo"
        text = "func Foo(a int) int {\n\treturn a\n}\n"
        manager = self._index_manager({chunk_id: text})
        results = [{"chunk_id": chunk_id, "kind": "function"}]
        out = _enrich_results_with_signatures(results, manager)
        assert out[0]["signature"] == "func Foo(a int) int {\n\treturn a\n}"

    def test_missing_kind_field_is_not_gated(self):
        """A result dict without a `kind` key at all (defensive -- kind is
        always set by _format_search_results in production) must not be
        mistaken for a gated kind; falls through to normal enrichment."""
        chunk_id = "a.py:1-2:function:foo"
        manager = self._index_manager({chunk_id: "def foo():\n    pass\n"})
        results = [{"chunk_id": chunk_id}]
        out = _enrich_results_with_signatures(results, manager)
        assert out[0]["signature"] == "def foo():"
