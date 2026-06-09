"""Unit tests for RelationshipAnalyzer — Phase 1 & Phase 4 changes.

Tests cover:
  * _resolve_by_symbol: returns None on all-tier miss; resolves via symbol_cache (Tier 1)
  * _enrich_callers: exact hit, stale-ID recovery, ambiguous-confidence passthrough
  * ImpactReport.to_dict: caller_confidence breakdown only emitted when non-zero
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Tiny stubs — keep tests self-contained and import-free
# ---------------------------------------------------------------------------


@dataclass
class _FakeResult:
    """Minimal stub that mimics a search result object."""

    chunk_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    content: str = "# stub"
    score: float = 1.0
    file_path: str = ""
    chunk_type: str = "function"
    relative_path: str = ""

    def __post_init__(self) -> None:
        if not self.metadata:
            self.metadata = {
                "chunk_type": self.chunk_type,
                "file": self.file_path or self.chunk_id.split(":")[0],
            }


def _make_entry(chunk_id: str, confidence: str | None = None, depth: int = 1) -> Any:
    """Build a mock RelationshipEntry with optional edge_data confidence."""
    entry = MagicMock()
    entry.chunk_id = chunk_id
    entry.depth = depth
    entry.relationship_type = "calls"
    entry.edge_data = {}
    if confidence:
        entry.edge_data["confidence"] = confidence
    return entry


# ---------------------------------------------------------------------------
# Helpers to build a RelationshipAnalyzer under test
# ---------------------------------------------------------------------------


def _make_analyzer(
    *,
    get_by_chunk_id_side_effect=None,
    search_side_effect=None,
    symbol_cache_map: dict[str, str] | None = None,
    graph_nodes: list[str] | None = None,
):
    """Return (analyzer, mock_searcher) with the given side-effects pre-wired."""
    from search.relationship_analyzer import RelationshipAnalyzer

    mock_searcher = MagicMock()
    mock_searcher.get_by_chunk_id.side_effect = get_by_chunk_id_side_effect or (
        lambda cid: None
    )
    mock_searcher.search.side_effect = search_side_effect or (lambda *a, **kw: [])

    analyzer = RelationshipAnalyzer.__new__(RelationshipAnalyzer)
    analyzer.searcher = mock_searcher
    analyzer.graph_engine = None
    analyzer.symbol_cache = None

    if symbol_cache_map is not None:
        sc = MagicMock()
        sc.get_by_symbol_name.side_effect = lambda name: symbol_cache_map.get(name)
        analyzer.symbol_cache = sc

    # Lightweight stub for _result_to_dict so we don't pull in the full stack
    def _result_to_dict(result, cid):
        return {
            "chunk_id": cid,
            "file": cid.split(":")[0] if ":" in cid else "",
            "name": cid.split(":")[-1],
            "content": getattr(result, "content", ""),
        }

    analyzer._result_to_dict = _result_to_dict
    return analyzer, mock_searcher


# ---------------------------------------------------------------------------
# Tests: _resolve_by_symbol
# ---------------------------------------------------------------------------


class TestResolveBySymbol(TestCase):
    """_resolve_by_symbol: Tier 1→3 cascade with None-on-miss contract."""

    def test_returns_none_when_all_tiers_miss(self):
        """No cache, no graph, empty search → None."""
        analyzer, _ = _make_analyzer(search_side_effect=lambda *a, **kw: [])
        result = analyzer._resolve_by_symbol("missing_fn", None)
        self.assertIsNone(result)

    def test_tier1_symbol_cache_hit(self):
        """Symbol cache match → returns (result, cid) immediately."""
        cid = "src/foo.py:function:normalize_chunk_id"
        fake_result = _FakeResult(chunk_id=cid)

        analyzer, mock_searcher = _make_analyzer(
            symbol_cache_map={"normalize_chunk_id": cid},
            get_by_chunk_id_side_effect=lambda c: fake_result if c == cid else None,
        )

        resolved = analyzer._resolve_by_symbol("normalize_chunk_id", None)
        self.assertIsNotNone(resolved)
        result, resolved_cid = resolved
        self.assertEqual(resolved_cid, cid)
        self.assertIs(result, fake_result)

    def test_tier1_cache_miss_falls_through_to_tier3(self):
        """Symbol cache miss → falls through to semantic search (Tier 3)."""
        cid = "src/bar.py:function:bar_fn"
        fake_result = _FakeResult(chunk_id=cid)

        # Mock: search returns one result matching the symbol name
        def _search(query, k=30, filters=None):
            return [fake_result] if query == "bar_fn" else []

        analyzer, _ = _make_analyzer(
            symbol_cache_map={"other_fn": "src/other.py:function:other_fn"},
            search_side_effect=_search,
        )
        resolved = analyzer._resolve_by_symbol("bar_fn", None)
        self.assertIsNotNone(resolved)
        _, resolved_cid = resolved
        self.assertEqual(resolved_cid, cid)

    def test_search_exception_returns_none(self):
        """If Tier 3 search raises, _resolve_by_symbol returns None (not raised)."""

        def _bad_search(*a, **kw):
            raise RuntimeError("index unavailable")

        analyzer, _ = _make_analyzer(search_side_effect=_bad_search)
        # Must not propagate; failure must be logged at DEBUG level
        with self.assertLogs("search.relationship_analyzer", level="DEBUG") as cm:
            result = analyzer._resolve_by_symbol("anything", None)
        self.assertIsNone(result)
        self.assertTrue(
            any("Tier 3 semantic search failed" in msg for msg in cm.output),
            f"Expected Tier 3 failure log, got: {cm.output}",
        )


# ---------------------------------------------------------------------------
# Tests: _enrich_callers
# ---------------------------------------------------------------------------


class TestEnrichCallers(TestCase):
    """_enrich_callers: exact, recovered, ambiguous, stale paths."""

    def test_exact_hit_tagged_exact(self):
        """When get_by_chunk_id succeeds, caller gets confidence='exact'."""
        cid = "src/a.py:function:a_fn"
        fake_result = _FakeResult(chunk_id=cid)
        entry = _make_entry(cid)

        analyzer, _ = _make_analyzer(
            get_by_chunk_id_side_effect=lambda c: fake_result if c == cid else None
        )

        callers, stale, exact, recovered, ambiguous = analyzer._enrich_callers(
            [entry], None
        )
        self.assertEqual(len(callers), 1)
        self.assertEqual(callers[0]["confidence"], "exact")
        self.assertEqual(exact, 1)
        self.assertEqual(recovered, 0)
        self.assertEqual(ambiguous, 0)
        self.assertEqual(stale, 0)

    def test_ambiguous_edge_confidence_preserved(self):
        """When edge carries confidence='ambiguous', that tag is preserved."""
        cid = "src/b.py:function:b_fn"
        fake_result = _FakeResult(chunk_id=cid)
        entry = _make_entry(cid, confidence="ambiguous")

        analyzer, _ = _make_analyzer(
            get_by_chunk_id_side_effect=lambda c: fake_result if c == cid else None
        )

        callers, stale, exact, recovered, ambiguous = analyzer._enrich_callers(
            [entry], None
        )
        self.assertEqual(len(callers), 1)
        self.assertEqual(callers[0]["confidence"], "ambiguous")
        self.assertEqual(exact, 0)
        self.assertEqual(ambiguous, 1)
        self.assertEqual(stale, 0)

    def test_stale_id_recovery_via_resolve_by_symbol(self):
        """When exact lookup misses, _resolve_by_symbol is called.
        If it succeeds, caller is tagged 'recovered' and stale count is 0."""
        stale_id = "src/c.py:100-150:function:c_fn"  # drifted line range
        current_id = "src/c.py:110-160:function:c_fn"  # current position
        fake_result = _FakeResult(chunk_id=current_id)

        # Exact lookup fails for stale_id; symbol resolution succeeds
        def _get_by_chunk_id(cid):
            return fake_result if cid == current_id else None

        symbol_cache = {"c_fn": current_id}

        entry = _make_entry(stale_id)
        analyzer, _ = _make_analyzer(
            get_by_chunk_id_side_effect=_get_by_chunk_id,
            symbol_cache_map=symbol_cache,
        )

        callers, stale, exact, recovered, ambiguous = analyzer._enrich_callers(
            [entry], None
        )
        self.assertEqual(len(callers), 1)
        self.assertEqual(callers[0]["confidence"], "recovered")
        self.assertEqual(callers[0]["original_chunk_id"], stale_id)
        self.assertEqual(recovered, 1)
        self.assertEqual(stale, 0)
        self.assertEqual(exact, 0)

    def test_unrecoverable_id_increments_stale(self):
        """When both exact lookup and _resolve_by_symbol fail, stale increments."""
        bad_id = "src/d.py:1-5:function:ghost_fn"
        entry = _make_entry(bad_id)

        # Exact lookup: always None; symbol_cache: empty; search: empty
        analyzer, _ = _make_analyzer()

        callers, stale, exact, recovered, ambiguous = analyzer._enrich_callers(
            [entry], None
        )
        self.assertEqual(len(callers), 0)
        self.assertEqual(stale, 1)
        self.assertEqual(exact, 0)
        self.assertEqual(recovered, 0)

    def test_mixed_entries_counted_correctly(self):
        """Multiple entries: one exact, one recovered, one stale."""
        cid_exact = "src/e.py:function:exact_fn"
        cid_stale = "src/e.py:100-110:function:stale_fn"
        cid_current = "src/e.py:200-210:function:stale_fn"
        cid_ghost = "src/e.py:function:ghost_fn"

        result_exact = _FakeResult(chunk_id=cid_exact)
        result_current = _FakeResult(chunk_id=cid_current)

        def _get_by_chunk_id(cid):
            if cid == cid_exact:
                return result_exact
            if cid == cid_current:
                return result_current
            return None

        sym_cache = {"stale_fn": cid_current}

        entries = [
            _make_entry(cid_exact),
            _make_entry(cid_stale),
            _make_entry(cid_ghost),
        ]
        analyzer, _ = _make_analyzer(
            get_by_chunk_id_side_effect=_get_by_chunk_id,
            symbol_cache_map=sym_cache,
        )

        callers, stale, exact, recovered, ambiguous = analyzer._enrich_callers(
            entries, None
        )
        self.assertEqual(len(callers), 2)  # exact + recovered
        self.assertEqual(exact, 1)
        self.assertEqual(recovered, 1)
        self.assertEqual(stale, 1)


# ---------------------------------------------------------------------------
# Tests: ImpactReport.to_dict — caller_confidence emission
# ---------------------------------------------------------------------------


class TestImpactReportCallerConfidence(TestCase):
    """ImpactReport.to_dict emits caller_confidence only when non-zero."""

    def _make_report(self, **kwargs):
        from search.types import ImpactReport

        defaults = {
            "symbol": {"name": "test"},
            "chunk_id": "src/test.py:function:test",
            "direct_callers": [],
            "indirect_callers": [],
            "similar_code": [],
            "total_impacted": 0,
            "unique_files": set(),
            "dependency_graph": {},
        }
        defaults.update(kwargs)
        return ImpactReport(**defaults)

    def test_no_confidence_counts_no_caller_confidence_key(self):
        """All counters at 0 → no 'caller_confidence' key in to_dict()."""
        report = self._make_report()
        d = report.to_dict()
        self.assertNotIn("caller_confidence", d)

    def test_exact_count_emits_caller_confidence(self):
        """Non-zero exact_d → caller_confidence present."""
        report = self._make_report(direct_callers_exact=3)
        d = report.to_dict()
        self.assertIn("caller_confidence", d)
        self.assertEqual(d["caller_confidence"]["exact"], 3)
        self.assertEqual(d["caller_confidence"]["recovered"], 0)
        self.assertEqual(d["caller_confidence"]["ambiguous"], 0)

    def test_recovered_count_emits_caller_confidence(self):
        """Non-zero recovered → caller_confidence present."""
        report = self._make_report(direct_callers_recovered=2)
        d = report.to_dict()
        self.assertIn("caller_confidence", d)
        self.assertEqual(d["caller_confidence"]["recovered"], 2)

    def test_all_confidence_counts_combined(self):
        """All three counters non-zero → emitted together."""
        report = self._make_report(
            direct_callers_exact=5,
            direct_callers_recovered=2,
            direct_callers_ambiguous=1,
        )
        d = report.to_dict()
        cc = d["caller_confidence"]
        self.assertEqual(cc["exact"], 5)
        self.assertEqual(cc["recovered"], 2)
        self.assertEqual(cc["ambiguous"], 1)

    def test_stale_chunk_count_still_emitted(self):
        """Existing stale_chunk_count behavior preserved."""
        report = self._make_report(stale_chunk_count=3)
        d = report.to_dict()
        self.assertEqual(d["stale_chunk_count"], 3)
