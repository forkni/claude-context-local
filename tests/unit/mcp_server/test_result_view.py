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
)


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
