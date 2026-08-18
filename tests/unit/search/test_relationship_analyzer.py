"""Unit tests for RelationshipAnalyzer — Phase 1 & Phase 4 changes.

Tests cover:
  * _resolve_by_symbol: returns None on all-tier miss; resolves via graph lookup (Tier 1)
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
    graph_nodes_map: dict[str, list[str]] | None = None,
):
    """Return (analyzer, mock_searcher) with the given side-effects pre-wired.

    ``graph_nodes_map`` simulates the Tier 1 graph exact-name lookup
    (``graph_storage.get_nodes_by_name``) used by ``_resolve_by_symbol``.
    """
    from search.relationship_analyzer import RelationshipAnalyzer

    mock_searcher = MagicMock()
    mock_searcher.get_by_chunk_id.side_effect = get_by_chunk_id_side_effect or (
        lambda cid, **kwargs: None
    )
    mock_searcher.search.side_effect = search_side_effect or (lambda *a, **kw: [])

    analyzer = RelationshipAnalyzer.__new__(RelationshipAnalyzer)
    analyzer.searcher = mock_searcher
    analyzer.graph_engine = None

    if graph_nodes_map is not None:
        storage = MagicMock()
        storage.get_nodes_by_name.side_effect = lambda name: graph_nodes_map.get(
            name, []
        )
        storage.graph.nodes.return_value = []
        graph_engine = MagicMock()
        graph_engine.storage = storage
        analyzer.graph_engine = graph_engine

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
    """_resolve_by_symbol: Tier 1→2 cascade with None-on-miss contract."""

    def test_returns_none_when_all_tiers_miss(self):
        """No graph, empty search → None."""
        analyzer, _ = _make_analyzer(search_side_effect=lambda *a, **kw: [])
        result = analyzer._resolve_by_symbol("missing_fn", None)
        self.assertIsNone(result)

    def test_tier1_graph_lookup_hit(self):
        """Graph exact-name match → returns (result, cid) immediately."""
        cid = "src/foo.py:function:normalize_chunk_id"
        fake_result = _FakeResult(chunk_id=cid)

        analyzer, mock_searcher = _make_analyzer(
            graph_nodes_map={"normalize_chunk_id": [cid]},
            get_by_chunk_id_side_effect=lambda c, **kw: (
                fake_result if c == cid else None
            ),
        )

        resolved = analyzer._resolve_by_symbol("normalize_chunk_id", None)
        self.assertIsNotNone(resolved)
        result, resolved_cid = resolved
        self.assertEqual(resolved_cid, cid)
        self.assertIs(result, fake_result)

    def test_tier1_graph_miss_falls_through_to_tier2(self):
        """Graph lookup miss → falls through to semantic search (Tier 2)."""
        cid = "src/bar.py:function:bar_fn"
        fake_result = _FakeResult(chunk_id=cid)

        # Mock: search returns one result matching the symbol name
        def _search(query, k=30, filters=None):
            return [fake_result] if query == "bar_fn" else []

        analyzer, _ = _make_analyzer(
            graph_nodes_map={"other_fn": ["src/other.py:function:other_fn"]},
            search_side_effect=_search,
        )
        resolved = analyzer._resolve_by_symbol("bar_fn", None)
        self.assertIsNotNone(resolved)
        _, resolved_cid = resolved
        self.assertEqual(resolved_cid, cid)

    def test_search_exception_returns_none(self):
        """If Tier 2 search raises, _resolve_by_symbol returns None (not raised)."""

        def _bad_search(*a, **kw):
            raise RuntimeError("index unavailable")

        analyzer, _ = _make_analyzer(search_side_effect=_bad_search)
        # Must not propagate; failure must be logged at DEBUG level
        with self.assertLogs("search.relationship_analyzer", level="DEBUG") as cm:
            result = analyzer._resolve_by_symbol("anything", None)
        self.assertIsNone(result)
        self.assertTrue(
            any("Tier 2 semantic search failed" in msg for msg in cm.output),
            f"Expected Tier 2 failure log, got: {cm.output}",
        )

    def test_lenient_default_guesses_when_no_name_match(self):
        """Default (strict_name_match=False, used by _resolve_target/user queries):
        Tier 2 falls back to the top semantic hit even when no candidate's name
        actually matches the query. This is the existing, intentionally lenient
        behavior for ambiguous/fuzzy user-facing symbol lookups."""
        unrelated_cid = "src/wrong.py:function:unrelated_fn"
        fake_result = _FakeResult(chunk_id=unrelated_cid)

        analyzer, _ = _make_analyzer(search_side_effect=lambda *a, **kw: [fake_result])

        resolved = analyzer._resolve_by_symbol("len", None)
        self.assertIsNotNone(resolved)
        _, resolved_cid = resolved
        self.assertEqual(resolved_cid, unrelated_cid)

    def test_strict_name_match_returns_none_when_no_name_match(self):
        """strict_name_match=True (used by the edge-recovery paths): when no Tier 2
        candidate's name matches the query, return None instead of guessing.

        Regression test for the false-bind bug where an unresolved call-graph
        symbol (e.g. 'len') was recovered to an unrelated top semantic hit
        (e.g. 'estimate_tokens') purely because nothing matched by name."""
        unrelated_cid = "src/wrong.py:function:unrelated_fn"
        fake_result = _FakeResult(chunk_id=unrelated_cid)

        analyzer, _ = _make_analyzer(search_side_effect=lambda *a, **kw: [fake_result])

        resolved = analyzer._resolve_by_symbol("len", None, strict_name_match=True)
        self.assertIsNone(resolved)

    def test_strict_name_match_still_resolves_real_match(self):
        """strict_name_match=True must not block genuine name matches."""
        cid = "src/util.py:function:frobnicate"
        fake_result = _FakeResult(chunk_id=cid)

        def _search(query, k=30, filters=None):
            return [fake_result] if query == "frobnicate" else []

        analyzer, _ = _make_analyzer(search_side_effect=_search)

        resolved = analyzer._resolve_by_symbol(
            "frobnicate", None, strict_name_match=True
        )
        self.assertIsNotNone(resolved)
        _, resolved_cid = resolved
        self.assertEqual(resolved_cid, cid)


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
            get_by_chunk_id_side_effect=lambda c, **kw: (
                fake_result if c == cid else None
            )
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
            get_by_chunk_id_side_effect=lambda c, **kw: (
                fake_result if c == cid else None
            )
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

        graph_nodes_map = {"c_fn": [current_id]}

        entry = _make_entry(stale_id)
        analyzer, _ = _make_analyzer(
            get_by_chunk_id_side_effect=_get_by_chunk_id,
            graph_nodes_map=graph_nodes_map,
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

        # Exact lookup: always None; graph: no engine; search: empty
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

        graph_nodes_map = {"stale_fn": [cid_current]}

        entries = [
            _make_entry(cid_exact),
            _make_entry(cid_stale),
            _make_entry(cid_ghost),
        ]
        analyzer, _ = _make_analyzer(
            get_by_chunk_id_side_effect=_get_by_chunk_id,
            graph_nodes_map=graph_nodes_map,
        )

        callers, stale, exact, recovered, ambiguous = analyzer._enrich_callers(
            entries, None
        )
        self.assertEqual(len(callers), 2)  # exact + recovered
        self.assertEqual(exact, 1)
        self.assertEqual(recovered, 1)
        self.assertEqual(stale, 1)


# ---------------------------------------------------------------------------
# Tests: _enrich_callees — builtin/common-method guard + strict Tier-3 match
# (Part B regression: the len()->estimate_tokens style false-bind)
# ---------------------------------------------------------------------------


class TestEnrichCallees(TestCase):
    """_enrich_callees: exact, guarded-builtin, guarded-common-method,
    no-name-match, and legitimate-recovery paths."""

    def test_exact_hit_tagged_exact(self):
        """When get_by_chunk_id succeeds, callee gets confidence='exact'."""
        cid = "src/a.py:function:a_fn"
        fake_result = _FakeResult(chunk_id=cid)
        entry = _make_entry(cid)

        analyzer, _ = _make_analyzer(
            get_by_chunk_id_side_effect=lambda c, **kw: (
                fake_result if c == cid else None
            )
        )

        callees, stale, exact, recovered, ambiguous = analyzer._enrich_callees(
            [entry], None
        )
        self.assertEqual(len(callees), 1)
        self.assertEqual(callees[0]["confidence"], "exact")
        self.assertEqual(exact, 1)
        self.assertEqual(recovered, 0)
        self.assertEqual(stale, 0)

    def test_initial_probe_passes_warn_on_miss_false(self):
        """Log-hygiene item G: the initial get_by_chunk_id probe (callee_id may be
        a bare symbol name, not a real chunk_id) must opt out of the miss WARNING
        -- a miss here is expected control flow the recovery ladder handles, not
        a defect. Uses an exact-hit scenario so there is exactly one call to
        assert on, with no Tier 1/Tier 2 recovery cascade in play."""
        cid = "src/a.py:function:a_fn"
        fake_result = _FakeResult(chunk_id=cid)
        entry = _make_entry(cid)

        analyzer, mock_searcher = _make_analyzer(
            get_by_chunk_id_side_effect=lambda c, **kw: (
                fake_result if c == cid else None
            )
        )

        analyzer._enrich_callees([entry], None)

        mock_searcher.get_by_chunk_id.assert_called_once_with(cid, warn_on_miss=False)

    def test_builtin_callee_name_not_recovered(self):
        """A phantom callee node named 'len' (a Python builtin) must never be
        Tier-3 guessed — it should stay unresolved (stale), and Tier 3 search
        must not even be invoked."""
        entry = _make_entry("len")
        search_calls: list[str] = []

        def _search(query, k=30, filters=None):
            search_calls.append(query)
            return [_FakeResult(chunk_id="src/util.py:function:estimate_tokens")]

        analyzer, _ = _make_analyzer(search_side_effect=_search)

        callees, stale, exact, recovered, ambiguous = analyzer._enrich_callees(
            [entry], None
        )
        self.assertEqual(len(callees), 0)
        self.assertEqual(stale, 1)
        self.assertEqual(recovered, 0)
        self.assertEqual(search_calls, [], "builtin guard must short-circuit Tier 3")

    def test_common_method_callee_name_not_recovered(self):
        """A phantom callee node named 'append' (blocklisted common method) must
        stay unresolved rather than binding to an unrelated project function."""
        entry = _make_entry("append")

        def _search(query, k=30, filters=None):
            return [_FakeResult(chunk_id="src/other.py:function:build_stuff")]

        analyzer, _ = _make_analyzer(search_side_effect=_search)

        callees, stale, exact, recovered, ambiguous = analyzer._enrich_callees(
            [entry], None
        )
        self.assertEqual(len(callees), 0)
        self.assertEqual(stale, 1)
        self.assertEqual(recovered, 0)

    def test_unmatched_name_semantic_result_not_recovered(self):
        """Regression for the len()->estimate_tokens false-bind: a non-builtin,
        non-blocklisted symbol with no true name match among Tier 3 results must
        stay unresolved, not bind to the top semantic neighbor."""
        entry = _make_entry("frobnicate")  # not a builtin, not in _COMMON_METHODS

        def _search(query, k=30, filters=None):
            return [_FakeResult(chunk_id="src/other.py:function:unrelated_fn")]

        analyzer, _ = _make_analyzer(search_side_effect=_search)

        callees, stale, exact, recovered, ambiguous = analyzer._enrich_callees(
            [entry], None
        )
        self.assertEqual(len(callees), 0)
        self.assertEqual(stale, 1)
        self.assertEqual(recovered, 0)

    def test_real_name_match_still_recovered(self):
        """A phantom callee that legitimately name-matches a project symbol must
        still be recovered — the guard only blocks false binds, not real ones."""
        target_cid = "src/util.py:function:frobnicate"
        entry = _make_entry("frobnicate")
        fake_result = _FakeResult(chunk_id=target_cid)

        analyzer, _ = _make_analyzer(
            graph_nodes_map={"frobnicate": [target_cid]},
            get_by_chunk_id_side_effect=lambda c, **kw: (
                fake_result if c == target_cid else None
            ),
        )

        callees, stale, exact, recovered, ambiguous = analyzer._enrich_callees(
            [entry], None
        )
        self.assertEqual(len(callees), 1)
        self.assertEqual(callees[0]["confidence"], "recovered")
        self.assertEqual(recovered, 1)
        self.assertEqual(stale, 0)


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


# The 23 relationship-bucket names ImpactReport.to_dict() emits today, in
# today's order. This is the byte-identity gate for the ImpactReport
# consolidation refactor: step 1 (23 fields -> one `relationships` dict) must
# not change this list or its order; step 2 (populate the dropped buckets)
# appends to it rather than reordering it.
_RELATIONSHIP_FIELDS_TODAY = [
    "parent_classes",
    "child_classes",
    "uses_types",
    "used_as_type_in",
    "imports",
    "imported_by",
    "decorates",
    "decorated_by",
    "exceptions_raised",
    "exception_handlers",
    "exceptions_caught",
    "instantiates",
    "instantiated_by",
    "defines_constants",
    "uses_constants",
    "defines_enum_members",
    "uses_defaults",
    "defines_class_attrs",
    "class_attr_definitions",
    "defines_fields",
    "field_definitions",
    "uses_context_managers",
    "context_manager_usages",
]


class TestDedupAndSortEdges(TestCase):
    """RelationshipAnalyzer._dedup_and_sort_edges — used identically by
    direct_callers, direct_callees, and (since this defect fix) indirect_callers.
    """

    def test_dedups_by_chunk_id_keeping_highest_resolver_confidence(self):
        from search.relationship_analyzer import RelationshipAnalyzer

        entries = [
            {"chunk_id": "a.py:1:function:a", "resolver_confidence": 0.5},
            {"chunk_id": "a.py:1:function:a", "resolver_confidence": 0.98},
            {"chunk_id": "a.py:1:function:a", "resolver_confidence": 0.7},
        ]
        result = RelationshipAnalyzer._dedup_and_sort_edges(entries)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["resolver_confidence"], 0.98)

    def test_sorts_by_confidence_desc_then_chunk_id_asc(self):
        from search.relationship_analyzer import RelationshipAnalyzer

        entries = [
            {"chunk_id": "z.py:1:function:z", "resolver_confidence": 0.9},
            {"chunk_id": "b.py:1:function:b", "resolver_confidence": 0.9},
            {"chunk_id": "a.py:1:function:a", "resolver_confidence": 0.5},
        ]
        result = RelationshipAnalyzer._dedup_and_sort_edges(entries)
        self.assertEqual(
            [e["chunk_id"] for e in result],
            ["b.py:1:function:b", "z.py:1:function:z", "a.py:1:function:a"],
        )

    def test_deterministic_across_repeated_calls_regardless_of_input_order(self):
        """Same entries, different input order -> identical output order --
        this is the property that was missing from indirect_callers before it
        was routed through this helper."""
        from search.relationship_analyzer import RelationshipAnalyzer

        entries = [
            {"chunk_id": "c.py:1:function:c", "resolver_confidence": 0.6},
            {"chunk_id": "a.py:1:function:a", "resolver_confidence": 0.6},
            {"chunk_id": "b.py:1:function:b", "resolver_confidence": 0.9},
        ]
        reversed_entries = list(reversed(entries))

        result_a = RelationshipAnalyzer._dedup_and_sort_edges(entries)
        result_b = RelationshipAnalyzer._dedup_and_sort_edges(reversed_entries)

        self.assertEqual(result_a, result_b)

    def test_missing_resolver_confidence_uses_half_default_for_comparison(self):
        """0.5 is only a comparison/sort default -- an entry missing the key
        outright is neither mutated nor dropped."""
        from search.relationship_analyzer import RelationshipAnalyzer

        entries = [{"chunk_id": "a.py:1:function:a"}]
        result = RelationshipAnalyzer._dedup_and_sort_edges(entries)
        self.assertEqual(len(result), 1)
        self.assertNotIn("resolver_confidence", result[0])

    def test_empty_list_returns_empty_list(self):
        from search.relationship_analyzer import RelationshipAnalyzer

        self.assertEqual(RelationshipAnalyzer._dedup_and_sort_edges([]), [])


class TestImpactReportToDictKeyOrder(TestCase):
    """Characterization test for ImpactReport.to_dict()'s wire shape.

    mcp_server/output_formatter.py serializes to_dict()'s result to JSON
    text, so key insertion order is observable in the MCP wire output even
    though dict equality is not. This pins today's exact key set and order
    so the ImpactReport consolidation refactor (23 fields -> one
    `relationships` dict) can be verified byte-identical.
    """

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

    def test_all_relationship_fields_populated_key_order(self):
        """Every relationship bucket non-empty -> to_dict() emits them in
        this exact order, after the fixed symbol/chunk_id/total_impacted/
        file_count prefix.
        """
        relationships = {
            name: [{"chunk_id": "x"}] for name in _RELATIONSHIP_FIELDS_TODAY
        }
        report = self._make_report(relationships=relationships)
        d = report.to_dict()

        expected_order = [
            "symbol",
            "chunk_id",
            "total_impacted",
            "file_count",
            *_RELATIONSHIP_FIELDS_TODAY,
        ]
        self.assertEqual(list(d.keys()), expected_order)

    def test_empty_relationship_fields_omitted(self):
        """omit-empty: none of the 23 relationship keys appear when none of
        the buckets have data.
        """
        report = self._make_report()
        d = report.to_dict()
        self.assertFalse(set(_RELATIONSHIP_FIELDS_TODAY) & d.keys())


# ---------------------------------------------------------------------------
# Tests: filter_ambiguous_edges — hide_ambiguous display filter (B1)
# ---------------------------------------------------------------------------


def _edge(cid: str, confidence: str) -> dict[str, Any]:
    return {"chunk_id": cid, "confidence": confidence, "resolver_confidence": 0.5}


class TestFilterAmbiguousEdges(TestCase):
    """filter_ambiguous_edges drops string-tagged ambiguous call edges only."""

    def _make_report_dict(self, **kwargs) -> dict[str, Any]:
        from search.types import ImpactReport

        defaults = {
            "symbol": {"name": "t"},
            "chunk_id": "src/t.py:function:t",
            "direct_callers": [],
            "indirect_callers": [],
            "similar_code": [],
            "total_impacted": 0,
            "unique_files": set(),
            "dependency_graph": {},
        }
        defaults.update(kwargs)
        return ImpactReport(**defaults).to_dict()

    def test_drops_ambiguous_from_all_three_call_lists(self):
        """Ambiguous entries removed from direct_callers, direct_callees, AND
        indirect_callers. All three are routed through _dedup_and_sort_edges
        upstream in analyze_impact, but this filter must still cover all three
        independently since it also runs standalone on hand-built dicts like
        this one that never went through that dedup/sort step."""
        from search.relationship_analyzer import filter_ambiguous_edges

        d = self._make_report_dict(
            direct_callers=[
                _edge("a.py:1-2:function:a", "exact"),
                _edge("b.py:1-2:function:b", "ambiguous"),
            ],
            indirect_callers=[
                _edge("c.py:1-2:function:c", "ambiguous"),
                _edge("d.py:1-2:function:d", "recovered"),
            ],
            direct_callees=[_edge("e.py:1-2:function:e", "exact")],
        )
        out = filter_ambiguous_edges(d)
        self.assertEqual(
            [e["chunk_id"] for e in out["direct_callers"]], ["a.py:1-2:function:a"]
        )
        self.assertEqual(
            [e["chunk_id"] for e in out["indirect_callers"]], ["d.py:1-2:function:d"]
        )
        self.assertEqual(
            [e["chunk_id"] for e in out["direct_callees"]], ["e.py:1-2:function:e"]
        )

    def test_emptied_list_key_is_removed(self):
        """A list that becomes empty is dropped entirely, matching
        to_dict()'s omit-empty contract."""
        from search.relationship_analyzer import filter_ambiguous_edges

        d = self._make_report_dict(
            direct_callees=[_edge("f.py:1-2:function:f", "ambiguous")],
        )
        out = filter_ambiguous_edges(d)
        self.assertNotIn("direct_callees", out)

    def test_totals_and_confidence_counters_untouched(self):
        """total_impacted / file_count / caller+callee confidence breakdowns
        stay pre-filter — the breakdown is the 'N were hidden' signal."""
        from search.relationship_analyzer import filter_ambiguous_edges

        d = self._make_report_dict(
            direct_callers=[
                _edge("a.py:1-2:function:a", "exact"),
                _edge("b.py:1-2:function:b", "ambiguous"),
            ],
            total_impacted=2,
            unique_files={"a.py", "b.py"},
            direct_callers_exact=1,
            direct_callers_ambiguous=1,
        )
        out = filter_ambiguous_edges(d)
        self.assertEqual(out["total_impacted"], 2)
        self.assertEqual(out["file_count"], 2)
        self.assertEqual(out["caller_confidence"]["ambiguous"], 1)
        self.assertEqual(out["caller_confidence"]["exact"], 1)

    def test_float_confidence_relationship_buckets_untouched(self):
        """The 'confidence' key is polymorphic — float on non-call buckets.
        Those lists must pass through unfiltered."""
        from search.relationship_analyzer import filter_ambiguous_edges

        d = self._make_report_dict(
            relationships={
                "parent_classes": [{"chunk_id": "g.py:1-2:class:G", "confidence": 0.9}],
                "imports": [{"chunk_id": "h.py:1-2:module:h", "confidence": 0.5}],
            },
        )
        out = filter_ambiguous_edges(d)
        self.assertEqual(len(out["parent_classes"]), 1)
        self.assertEqual(len(out["imports"]), 1)

    def test_no_ambiguous_entries_is_identity(self):
        """A report with no ambiguous edges comes back equal to the input."""
        from search.relationship_analyzer import filter_ambiguous_edges

        d = self._make_report_dict(
            direct_callers=[_edge("a.py:1-2:function:a", "exact")],
        )
        self.assertEqual(filter_ambiguous_edges(d), d)

    def test_input_dict_not_mutated(self):
        """Pure function: the caller's dict and its lists are unchanged."""
        from search.relationship_analyzer import filter_ambiguous_edges

        d = self._make_report_dict(
            direct_callers=[
                _edge("a.py:1-2:function:a", "exact"),
                _edge("b.py:1-2:function:b", "ambiguous"),
            ],
        )
        before = [e["chunk_id"] for e in d["direct_callers"]]
        filter_ambiguous_edges(d)
        self.assertEqual([e["chunk_id"] for e in d["direct_callers"]], before)

    def test_missing_call_lists_tolerated(self):
        """Reports with no caller/callee keys at all pass through unchanged."""
        from search.relationship_analyzer import filter_ambiguous_edges

        d = self._make_report_dict()
        self.assertEqual(filter_ambiguous_edges(d), d)
