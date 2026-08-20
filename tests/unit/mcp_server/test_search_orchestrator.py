"""Unit tests for SearchOrchestrator (Phases B–D)."""

from __future__ import annotations

import asyncio
import inspect
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from mcp_server.state import ApplicationState
from mcp_server.tools.result_view import RESULT_ENRICHERS
from mcp_server.tools.search_orchestrator import ExecutionOutcome, SearchOrchestrator
from search.config import (
    EgoGraphConfig,
    OutputConfig,
    ParentRetrievalConfig,
    SearchConfig,
)
from search.exceptions import DimensionMismatchError
from search.hybrid_searcher import HybridSearcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan(
    query="test query",
    k=4,
    intent_decision=None,
    search_mode="hybrid",
    ego_graph_enabled=None,
    ego_graph_k_hops=2,
    ego_graph_max_neighbors=10,
    include_parent=False,
    file_pattern=None,
    include_dirs=None,
    exclude_dirs=None,
    chunk_type=None,
    include_context=True,
    auto_reindex=True,
    max_age_minutes=5.0,
    max_context_tokens=0,
    display_params=None,
):
    from mcp_server.tools.search_orchestrator import SearchPlan

    # display_params=None omits the field so SearchPlan's default factory
    # (one all-off gate per EnricherSpec row) applies.
    extra = {} if display_params is None else {"display_params": display_params}
    return SearchPlan(
        query=query,
        k=k,
        intent_decision=intent_decision,
        search_mode=search_mode,
        ego_graph_enabled=ego_graph_enabled,
        ego_graph_k_hops=ego_graph_k_hops,
        ego_graph_max_neighbors=ego_graph_max_neighbors,
        include_parent=include_parent,
        file_pattern=file_pattern,
        include_dirs=include_dirs,
        exclude_dirs=exclude_dirs,
        chunk_type=chunk_type,
        include_context=include_context,
        auto_reindex=auto_reindex,
        max_age_minutes=max_age_minutes,
        max_context_tokens=max_context_tokens,
        **extra,
    )


def _dim_mismatch_error():
    err = DimensionMismatchError("test mismatch")
    err.embedder_model = "qwen3_0.6b"
    err.embedder_dim = 1024
    err.index_dim = 768
    return err


def _make_async_cm():
    """A MagicMock usable as an ``async with`` context manager (no-op body)."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_rwlock_mock():
    """Mock for the object returned by ``ApplicationState.get_reindex_rwlock()``.

    Exposes ``.read()`` and ``.write()``, each returning a fresh async
    context manager on every call (mirrors real ``_AsyncRWLock`` usage,
    where both may be entered multiple times across a test).
    """
    rwlock = MagicMock()
    rwlock.read = Mock(side_effect=_make_async_cm)
    rwlock.write = Mock(side_effect=_make_async_cm)
    return rwlock


def _patch_execute(real_sc=None, project="/test"):
    """Context manager that patches all external deps for _execute."""
    import contextlib

    sc = real_sc or SearchConfig()

    @contextlib.contextmanager
    def _ctx():
        with (
            patch("mcp_server.tools.search_orchestrator.get_state") as mock_state,
            patch(
                "mcp_server.tools.search_orchestrator.get_search_config",
                return_value=sc,
            ),
            patch("mcp_server.tools.search_orchestrator.get_config_manager") as mock_cm,
            patch("mcp_server.tools.search_orchestrator.get_config") as mock_cfg,
            patch(
                "mcp_server.tools.search_orchestrator.get_searcher"
            ) as mock_get_searcher,
            patch(
                "mcp_server.tools.search_handlers._is_index_stale",
                return_value=True,
            ),
            patch(
                "mcp_server.tools.search_handlers._check_auto_reindex",
                return_value=(False, None),
            ),
        ):
            st = Mock()
            st.current_project = project
            st.searcher = None
            # get_reindex_rwlock() must return an object exposing async
            # context managers from both .read() and .write().
            st.get_reindex_rwlock = Mock(return_value=_make_rwlock_mock())
            mock_state.return_value = st
            mock_cm.return_value.get_search_mode_for_query.return_value = "hybrid"
            mock_cfg.return_value.performance.use_parallel_search = False
            # run() plans via SearchPlanner.plan(), which checks config.intent.enabled
            # before running IntentClassifier. None of the current _run_execute-based
            # callers reach plan() (they call _maybe_reindex/_search directly), so this
            # is a no-op for them; composition tests that call orchestrator.run()
            # directly need it to skip intent classification against a bare MagicMock.
            mock_cfg.return_value.intent.enabled = False
            yield mock_state, mock_get_searcher

    return _ctx()


def _make_ready_searcher():
    """Create a mock HybridSearcher that is ready (1000 chunks).

    ``spec=HybridSearcher`` so ``isinstance(searcher, HybridSearcher)`` — the
    guard on every ego_graph/parent_retrieval/intent-edge mutation block and
    the Block D hybrid-search-call branch in ``_search()`` — actually
    evaluates True, matching what this helper's name and docstring claim. A
    bare ``Mock()`` fails that isinstance check silently, so every one of
    those blocks would be skipped with no test failure to show it (caught by
    ``test_ego_graph_rebuild_preserves_sibling_fields`` /
    ``test_parent_retrieval_rebuild_preserves_sibling_fields``, which read
    back ``effective_config`` and therefore need the mutation to actually
    run). ``index_manager`` is set to None explicitly so that SearcherView
    falls through to ``dense_index`` (the HybridSearcher attribute name).
    """
    s = Mock(spec=HybridSearcher)
    s.is_ready = True
    s.index_manager = None  # HybridSearcher: manager is at .dense_index
    s.bm25_weight = 0.35
    s.dense_weight = 0.65
    dense = Mock()
    dense.index = Mock()
    dense.index.ntotal = 1000
    s.dense_index = dense
    s.search = Mock(return_value=[])
    return s


async def _run_execute(orchestrator: SearchOrchestrator, plan):
    """Mirror the deleted ``_execute`` for these Block-level tests: run
    ``_maybe_reindex`` (Block A) then ``_search`` (Blocks B-D), short-circuiting
    on a dict (error) from either stage — exactly what ``run()`` does, minus
    the read lock ``run()`` now holds across ``_search`` *and* ``_assemble``
    (ADR-0008 amendment). Omitting the lock here changes no assertion: every
    test below stubs ``get_reindex_rwlock()`` via ``_patch_execute()`` /
    ``_make_rwlock_mock()`` with no-op async context managers.
    """
    early = await orchestrator._maybe_reindex(plan)
    if isinstance(early, dict):
        return early
    reindexed, _lock_project = early
    return await orchestrator._search(plan, reindexed)


# ---------------------------------------------------------------------------
# Phase B: _maybe_reindex + _search
# ---------------------------------------------------------------------------


class TestExecuteDimensionMismatch:
    @pytest.mark.asyncio
    async def test_reindex_dimension_mismatch_returns_error_dict(self):
        plan = _make_plan(auto_reindex=True)
        err = _dim_mismatch_error()
        with (
            _patch_execute() as (_, _gs),
            patch(
                "mcp_server.tools.search_handlers._check_auto_reindex",
                side_effect=err,
            ),
        ):
            result = await _run_execute(SearchOrchestrator(), plan)
        assert isinstance(result, dict)
        assert result["error"] == "Dimension mismatch"
        assert "force_reindex" in result["recovery_suggestion"]

    @pytest.mark.asyncio
    async def test_get_searcher_dimension_mismatch_returns_error_dict(self):
        plan = _make_plan()
        err = _dim_mismatch_error()
        with _patch_execute() as (_, mock_gs):
            mock_gs.side_effect = err
            result = await _run_execute(SearchOrchestrator(), plan)
        assert isinstance(result, dict)
        assert result["error"] == "Dimension mismatch"


class TestExecuteReadinessCheck:
    @pytest.mark.asyncio
    async def test_not_ready_searcher_returns_no_index_error(self):
        plan = _make_plan()
        s = Mock()
        s.is_ready = False
        s.index_manager = None  # HybridSearcher-like mock; manager is at .dense_index
        dense = Mock()
        dense.index = Mock()
        dense.index.ntotal = 0
        s.dense_index = dense
        with _patch_execute() as (_, mock_gs):
            mock_gs.return_value = s
            result = await _run_execute(SearchOrchestrator(), plan)
        assert isinstance(result, dict)
        assert "No indexed project" in result["error"]

    @pytest.mark.asyncio
    async def test_zero_chunks_searcher_returns_no_index_error(self):
        plan = _make_plan()
        s = Mock(spec=["index_manager"])
        s.index_manager.get_stats.return_value = {"total_chunks": 0}
        with _patch_execute() as (_, mock_gs):
            mock_gs.return_value = s
            result = await _run_execute(SearchOrchestrator(), plan)
        assert isinstance(result, dict)
        assert "No indexed project" in result["error"]


class TestExecuteHappyPath:
    @pytest.mark.asyncio
    async def test_returns_execution_outcome(self):
        plan = _make_plan()
        searcher = _make_ready_searcher()
        with _patch_execute() as (_, mock_gs):
            mock_gs.return_value = searcher
            result = await _run_execute(SearchOrchestrator(), plan)
        assert isinstance(result, ExecutionOutcome)
        assert result.searcher is searcher
        assert isinstance(result.effective_config, SearchConfig)

    @pytest.mark.asyncio
    async def test_search_called_with_plan_k_and_query(self):
        plan = _make_plan(query="find embedder", k=7)
        searcher = _make_ready_searcher()
        with _patch_execute() as (_, mock_gs):
            mock_gs.return_value = searcher
            await _run_execute(SearchOrchestrator(), plan)
        call_kwargs = searcher.search.call_args.kwargs
        assert call_kwargs["query"] == "find embedder"
        assert call_kwargs["k"] == 7

    @pytest.mark.asyncio
    async def test_filter_build_from_plan(self):
        plan = _make_plan(
            file_pattern="search/",
            include_dirs=["src/"],
            exclude_dirs=["tests/"],
            chunk_type="method",
        )
        searcher = _make_ready_searcher()
        # searcher.search is called inside asyncio.to_thread; capture call_args after execution
        searcher.search.return_value = []

        with _patch_execute() as (_, mock_gs):
            mock_gs.return_value = searcher
            await _run_execute(SearchOrchestrator(), plan)

        call_kwargs = searcher.search.call_args.kwargs
        f = call_kwargs.get("filters", {}) or {}
        assert f.get("file_pattern") == ["search/"]
        assert f.get("include_dirs") == ["src/"]
        assert f.get("exclude_dirs") == ["tests/"]
        assert f.get("chunk_type") == "method"

    @pytest.mark.asyncio
    async def test_auto_reindex_false_skips_reindex(self):
        plan = _make_plan(auto_reindex=False)
        searcher = _make_ready_searcher()
        with (
            _patch_execute() as (_, mock_gs),
            patch(
                "mcp_server.tools.search_handlers._check_auto_reindex"
            ) as mock_reindex,
        ):
            mock_gs.return_value = searcher
            await _run_execute(SearchOrchestrator(), plan)
        mock_reindex.assert_not_called()


class TestExecuteConfigIsolation:
    """The mutable_config() lazy-deepcopy inside _execute must never write to the singleton."""

    @pytest.mark.asyncio
    async def test_config_singleton_not_mutated_by_ego_graph(self):
        sc = SearchConfig()
        original_ego_enabled = sc.ego_graph.enabled
        plan = _make_plan(ego_graph_enabled=True)
        searcher = _make_ready_searcher()
        with _patch_execute(real_sc=sc) as (_, mock_gs):
            mock_gs.return_value = searcher
            await _run_execute(SearchOrchestrator(), plan)
        assert sc.ego_graph.enabled == original_ego_enabled

    @pytest.mark.asyncio
    async def test_ego_graph_rebuild_preserves_sibling_fields(self):
        """Regression: the ego_graph rebuild previously used
        EgoGraphConfig(enabled=..., k_hops=..., max_neighbors_per_hop=...),
        silently discarding every other configured field (expansion_mode,
        ppr_alpha, deduplicate). dataclasses.replace() must preserve them."""
        sc = SearchConfig(
            ego_graph=EgoGraphConfig(
                expansion_mode="ppr",
                ppr_alpha=0.42,
                deduplicate=False,
            )
        )
        plan = _make_plan(
            ego_graph_enabled=True, ego_graph_k_hops=3, ego_graph_max_neighbors=7
        )
        searcher = _make_ready_searcher()
        with _patch_execute(real_sc=sc) as (_, mock_gs):
            mock_gs.return_value = searcher
            result = await _run_execute(SearchOrchestrator(), plan)

        eg = result.effective_config.ego_graph
        assert eg.enabled is True
        assert eg.k_hops == 3
        assert eg.max_neighbors_per_hop == 7
        assert eg.expansion_mode == "ppr"
        assert eg.ppr_alpha == 0.42
        assert eg.deduplicate is False

    @pytest.mark.asyncio
    async def test_parent_retrieval_rebuild_preserves_sibling_fields(self):
        """Regression: the parent_retrieval rebuild previously used
        ParentRetrievalConfig(enabled=...), silently discarding
        include_parent_content. dataclasses.replace() must preserve it."""
        sc = SearchConfig(
            parent_retrieval=ParentRetrievalConfig(include_parent_content=False)
        )
        plan = _make_plan(include_parent=True)
        searcher = _make_ready_searcher()
        with _patch_execute(real_sc=sc) as (_, mock_gs):
            mock_gs.return_value = searcher
            result = await _run_execute(SearchOrchestrator(), plan)

        pr = result.effective_config.parent_retrieval
        assert pr.enabled is True
        assert pr.include_parent_content is False


class TestExecuteConcurrencyIntegration:
    """End-to-end concurrency proof (the plan's 'primary red signal' repro).

    Uses a REAL ApplicationState (real _AsyncRWLock via get_reindex_rwlock)
    so a reindex-triggering run() call and several plain-search run() calls
    exercise the actual _maybe_reindex (Block A) / read-locked _search+_assemble
    (Blocks B-I) lock wiring — not a mocked lock. Targets run() rather than the
    old _execute() so the covered lock span matches the ADR-0008 amendment: the
    read lock now extends through _assemble, not just Blocks B-D. Reproduces
    (in miniature) the concurrent shape from _archive/ERROR_LOG.md: a
    stale-index search triggers a reindex while sibling searches are in
    flight. Proves:

    1. A search's model-inference region (``searcher.search``, standing in
       for the real embed_query / reranker calls) never overlaps a
       concurrent reindex's write-locked critical section — the root cause
       of Errors A and B.
    2. Concurrent searches still run their inference concurrently with each
       other — i.e. the fix is a real reader-writer lock, not an
       accidental full mutex serializing every search.
    """

    @pytest.mark.asyncio
    async def test_reindex_and_concurrent_searches_never_overlap(self):
        state = ApplicationState()
        state.current_project = "/test-project"
        searcher = _make_ready_searcher()

        probe_lock = threading.Lock()
        writer_active = 0
        reader_active = 0
        reader_max_concurrent = 0
        overlap_detected = False
        writer_entered = threading.Event()

        def fake_is_index_stale(project, max_age_minutes):
            # Distinguish the reindex-trigger plan from plain search plans by
            # max_age_minutes: only the trigger plan uses a sub-1 value.
            return max_age_minutes < 1

        def fake_check_auto_reindex(project, max_age_minutes):
            nonlocal writer_active, overlap_detected
            with probe_lock:
                writer_active += 1
                if reader_active > 0:
                    overlap_detected = True
            writer_entered.set()
            # Margin, not just realism: dispatching 5 concurrent run() calls
            # each through several asyncio.to_thread hops (_is_index_stale ->
            # read-lock -> get_searcher -> search) costs tens-to-a-few-hundred ms
            # of pure scheduling overhead on this machine — verified by neutering
            # _AsyncRWLock.read() in a throwaway red-capability check, which saw
            # readers arrive up to ~240ms after writer_entered fired even with no
            # lock blocking them at all. A too-short critical section here would
            # make this test pass vacuously (no overlap window survives dispatch
            # overhead) regardless of whether the read lock actually blocks
            # readers. 0.3s reliably reproduced overlap_detected=True against a
            # neutered lock across repeated runs.
            time.sleep(0.3)
            with probe_lock:
                writer_active -= 1
            return True, None

        def fake_search(*args, **kwargs):
            nonlocal reader_active, reader_max_concurrent, overlap_detected
            with probe_lock:
                reader_active += 1
                reader_max_concurrent = max(reader_max_concurrent, reader_active)
                if writer_active > 0:
                    overlap_detected = True
            time.sleep(0.03)
            with probe_lock:
                reader_active -= 1
            return []

        searcher.search = Mock(side_effect=fake_search)
        sc = SearchConfig()

        with (
            patch("mcp_server.tools.search_orchestrator.get_state", return_value=state),
            patch(
                "mcp_server.tools.search_orchestrator.get_search_config",
                return_value=sc,
            ),
            patch("mcp_server.tools.search_orchestrator.get_config_manager") as mock_cm,
            patch("mcp_server.tools.search_orchestrator.get_config") as mock_cfg,
            patch(
                "mcp_server.tools.search_orchestrator.get_searcher",
                new=lambda: searcher,
            ),
            patch(
                "mcp_server.tools.search_handlers._is_index_stale",
                side_effect=fake_is_index_stale,
            ),
            patch(
                "mcp_server.tools.search_handlers._check_auto_reindex",
                side_effect=fake_check_auto_reindex,
            ),
        ):
            mock_cm.return_value.get_search_mode_for_query.return_value = "hybrid"
            mock_cfg.return_value.performance.use_parallel_search = False
            # run() plans via SearchPlanner.plan(), which checks config.intent.enabled
            # before running IntentClassifier — disable it so this test exercises only
            # the lock wiring, not semantic intent classification (mock_cfg is a bare
            # MagicMock; leaving other config.* attributes as auto-Mocks is fine since
            # the intent branch that would touch them never runs).
            mock_cfg.return_value.intent.enabled = False

            orchestrator = SearchOrchestrator()
            # Raw MCP arguments, not SearchPlan objects — run() builds the plan itself
            # via SearchPlanner.plan(). max_context_tokens is set explicitly because
            # SearchPlanner.plan() computes int(arguments.get("max_context_tokens",
            # config.search_mode.default_max_context_tokens)); leaving the key out would
            # evaluate the MagicMock default and crash the int() conversion.
            reindex_args = {
                "query": "test query",
                "auto_reindex": True,
                "max_age_minutes": 0.001,
                "max_context_tokens": 0,
            }
            search_args_list = [
                {
                    "query": "test query",
                    "auto_reindex": True,
                    "max_age_minutes": 5.0,
                    "max_context_tokens": 0,
                }
                for _ in range(5)
            ]

            reindex_task = asyncio.create_task(orchestrator.run(reindex_args))
            # Block until the reindex task is confirmed inside the write-locked
            # critical section before firing the concurrent searches. This
            # removes sleep-based guessing from "did they actually race" and
            # turns it into a guaranteed overlap *attempt* against the lock.
            await asyncio.to_thread(writer_entered.wait, 5)

            search_results = await asyncio.gather(
                *[orchestrator.run(a) for a in search_args_list]
            )
            reindex_result = await reindex_task

        assert not overlap_detected, (
            "a search's inference region overlapped the reindex's write-locked "
            "critical section — this is exactly Errors A/B from "
            "_archive/ERROR_LOG.md"
        )
        assert reader_max_concurrent > 1, (
            "searches never ran concurrently with each other — this looks like "
            "an accidental full mutex, not a reader-writer lock"
        )
        # run() returns the full response dict (Blocks A-I) rather than an
        # ExecutionOutcome — _assemble now runs inside the same read-locked
        # scope this test is proving, so the return value reflects that.
        assert isinstance(reindex_result, dict)
        assert reindex_result.get("index_refreshed") is True
        for r in search_results:
            assert isinstance(r, dict)
            assert "results" in r


# ---------------------------------------------------------------------------
# Phase C: _assemble helpers (Blocks F–I)
# ---------------------------------------------------------------------------


def _make_outcome(results=None, effective_config=None):
    """Return a minimal ExecutionOutcome for _assemble helper tests."""
    sc = effective_config or SearchConfig()
    return ExecutionOutcome(
        results=results if results is not None else [],
        searcher=Mock(),
        index_manager=None,
        effective_config=sc,
    )


def _make_formatted(chunk_id="a.py:1-5:function:foo", kind="function", score=0.9):
    return {"chunk_id": chunk_id, "kind": kind, "blended_score": score}


class TestBuildResponse:
    """_build_response (Block I): response dict construction."""

    def test_build_response_minimal(self):
        plan = _make_plan(query="what is X")
        results = [_make_formatted()]
        with patch(
            "mcp_server.guidance.add_system_message", side_effect=lambda r, **kw: r
        ):
            response = SearchOrchestrator._build_response(plan, results, None)
        assert response["query"] == "what is X"
        assert response["results"] is results
        assert "subgraph_nodes" not in response
        assert "routing" not in response

    def test_build_response_includes_subgraph_keys(self):
        plan = _make_plan()
        results = [_make_formatted()]
        subgraph_data = {
            "nodes": [{"id": "a"}],
            "edges": [{"src": "a", "tgt": "b"}],
            "topology_order": ["a"],
        }
        with patch(
            "mcp_server.guidance.add_system_message", side_effect=lambda r, **kw: r
        ):
            response = SearchOrchestrator._build_response(plan, results, subgraph_data)
        assert response["subgraph_nodes"] == subgraph_data["nodes"]
        assert response["subgraph_edges"] == subgraph_data["edges"]
        assert response["subgraph_order"] == subgraph_data["topology_order"]

    def test_build_response_subgraph_without_optional_keys(self):
        """subgraph_order is omitted when absent."""
        plan = _make_plan()
        subgraph_data = {"nodes": [{"id": "a"}], "edges": []}
        with patch(
            "mcp_server.guidance.add_system_message", side_effect=lambda r, **kw: r
        ):
            response = SearchOrchestrator._build_response(plan, [], subgraph_data)
        assert "subgraph_nodes" in response
        assert "subgraph_order" not in response


class TestAssembleEnrichmentGates:
    """_assemble (Block E): the gate map resolved by _enrichment_gates is what
    reaches the single result_view.enrich_results call site.

    Post-candidate-4b, _assemble no longer calls the individual enricher
    functions directly (they are reached only through RESULT_ENRICHERS, whose
    entries are captured as direct function references at module load) — so
    patching an individual `_enrich_results_with_*` name here would silently
    no-op rather than intercept. The single seam left to observe is
    `result_view.enrich_results` itself; these tests assert on the `gates`
    dict it receives.
    """

    def _run_assemble(self, plan, effective_config=None):
        orch = SearchOrchestrator()
        orch._graph_scoring_stage = Mock()
        orch._graph_scoring_stage.run.return_value = ([], None)
        outcome = _make_outcome(effective_config=effective_config)
        with (
            patch(
                "mcp_server.guidance.add_system_message",
                side_effect=lambda r, **kw: r,
            ),
            patch(
                "mcp_server.tools.result_view.enrich_results",
                side_effect=lambda results, *a, **kw: results,
            ) as mock_enrich,
        ):
            orch._assemble(plan, outcome)
        mock_enrich.assert_called_once()
        return mock_enrich.call_args.args[2]

    def test_default_off_all_gates_false(self):
        """No plan opt-ins, no config opt-in: every gate is False — byte
        identity with pre-4b behavior."""
        gates = self._run_assemble(_make_plan())
        assert gates == {"graph": False, "top_callers": False, "signatures": False}

    def test_top_callers_opt_in_sets_only_its_gate(self):
        gates = self._run_assemble(
            _make_plan(display_params={"top_callers": True, "signatures": False})
        )
        assert gates["top_callers"] is True
        assert gates["signatures"] is False
        assert gates["graph"] is False

    def test_signatures_opt_in_sets_only_its_gate(self):
        gates = self._run_assemble(
            _make_plan(display_params={"top_callers": False, "signatures": True})
        )
        assert gates["signatures"] is True
        assert gates["top_callers"] is False
        assert gates["graph"] is False

    def test_include_result_graph_config_sets_only_its_gate(self):
        """The graph gate is config-scoped (OutputConfig), not plan-scoped —
        closes a coverage gap that existed before this refactor."""
        sc = SearchConfig()
        sc.output.include_result_graph = True
        gates = self._run_assemble(_make_plan(), effective_config=sc)
        assert gates["graph"] is True
        assert gates["top_callers"] is False
        assert gates["signatures"] is False


class TestEnrichmentGatesRegistry:
    """_enrichment_gates as a pure function, independent of _assemble's
    wiring (covered by TestAssembleEnrichmentGates above)."""

    def test_enrichment_gates_cover_every_registered_enricher(self):
        """Catches 'added an enricher to RESULT_ENRICHERS, forgot to wire its
        gate' — the two must enumerate the same key set."""
        gates = SearchOrchestrator._enrichment_gates(_make_plan(), OutputConfig())
        assert set(gates) == {e.key for e in RESULT_ENRICHERS}

    def test_enricher_specs_join_result_enrichers_on_key(self):
        """The wire side (ENRICHER_SPECS) and the application side
        (RESULT_ENRICHERS) are separate registries joined on key: every spec
        row must have an apply row, and every apply row except the
        config-scoped 'graph' must have a spec row."""
        from mcp_server.enricher_specs import ENRICHER_SPECS

        assert {s.key for s in ENRICHER_SPECS} | {"graph"} == {
            e.key for e in RESULT_ENRICHERS
        }

    def test_enrichment_gates_reflect_plan_and_config(self):
        """Each gate reads from its own declared scope: graph from
        OutputConfig, top_callers/signatures from SearchPlan. Closes a
        coverage gap — include_result_graph had zero test hits before this
        refactor."""
        output_cfg = OutputConfig()
        output_cfg.include_result_graph = True
        plan = _make_plan(display_params={"top_callers": True, "signatures": True})
        gates = SearchOrchestrator._enrichment_gates(plan, output_cfg)
        assert gates == {"graph": True, "top_callers": True, "signatures": True}

    def test_enrichment_gates_all_off_by_default(self):
        gates = SearchOrchestrator._enrichment_gates(_make_plan(), OutputConfig())
        assert gates == {"graph": False, "top_callers": False, "signatures": False}


class TestAssembleEnrichmentOwnership:
    """Ownership gate: RESULT_ENRICHERS + _enrichment_gates is the single
    enumeration of result enrichers — _assemble itself must not carry a
    per-enricher `if` block (that asymmetry is exactly what candidate 4b
    removed)."""

    def test_assemble_has_no_per_enricher_if_block(self):
        source = inspect.getsource(SearchOrchestrator._assemble)
        for gate_key in (
            "include_top_callers",
            "include_signatures",
            "include_result_graph",
        ):
            assert gate_key not in source, (
                f"_assemble references {gate_key!r} directly — enrichment "
                "gating must go through _enrichment_gates + "
                "result_view.enrich_results, not a per-enricher `if` block."
            )


class TestApplySourceOrderAndBudget:
    """_apply_source_order_and_budget (Block H)."""

    def test_source_order_applied_when_enabled(self):
        """When source_order_output=True and len>1, reorder is called."""
        sc = SearchConfig()
        sc.output.source_order_output = True
        outcome = _make_outcome(effective_config=sc)
        results = [
            {
                "chunk_id": "b.py:10-20:function:b",
                "file_path": "b.py",
                "start_line": 10,
            },
            {"chunk_id": "a.py:1-5:function:a", "file_path": "a.py", "start_line": 1},
        ]
        with patch(
            "mcp_server.tools.result_view._reorder_by_source_position",
            return_value=list(reversed(results)),
        ) as mock_reorder:
            out = SearchOrchestrator._apply_source_order_and_budget(
                _make_plan(max_context_tokens=0), outcome, list(results)
            )
        mock_reorder.assert_called_once_with(results)
        assert out == list(reversed(results))

    def test_source_order_with_reranking_logs_warning(self, caplog):
        """B1: turning source_order_output on while reranking is enabled
        overrides the reranker's ordering — this should be surfaced as a
        warning, not silently applied.
        """
        sc = SearchConfig()
        sc.output.source_order_output = True
        sc.reranker.enabled = True
        outcome = _make_outcome(effective_config=sc)
        results = [
            {"chunk_id": "b.py:10-20:function:b", "file_path": "b.py"},
            {"chunk_id": "a.py:1-5:function:a", "file_path": "a.py"},
        ]
        with caplog.at_level("WARNING"):
            SearchOrchestrator._apply_source_order_and_budget(
                _make_plan(max_context_tokens=0), outcome, list(results)
            )
        assert any(
            "source_order_output" in r.message and "reranker" in r.message.lower()
            for r in caplog.records
        )

    def test_source_order_without_reranking_no_warning(self, caplog):
        """No warning when reranking is disabled — no conflict to flag."""
        sc = SearchConfig()
        sc.output.source_order_output = True
        sc.reranker.enabled = False
        outcome = _make_outcome(effective_config=sc)
        results = [
            {"chunk_id": "b.py:10-20:function:b", "file_path": "b.py"},
            {"chunk_id": "a.py:1-5:function:a", "file_path": "a.py"},
        ]
        with caplog.at_level("WARNING"):
            SearchOrchestrator._apply_source_order_and_budget(
                _make_plan(max_context_tokens=0), outcome, list(results)
            )
        assert not any("source_order_output" in r.message for r in caplog.records)

    def test_source_order_skipped_when_single_result(self):
        sc = SearchConfig()
        sc.output.source_order_output = True
        outcome = _make_outcome(effective_config=sc)
        single = [_make_formatted()]
        with patch(
            "mcp_server.tools.result_view._reorder_by_source_position"
        ) as mock_reorder:
            out = SearchOrchestrator._apply_source_order_and_budget(
                _make_plan(max_context_tokens=0), outcome, list(single)
            )
        mock_reorder.assert_not_called()
        assert out == single

    def test_context_budget_truncates(self):
        """max_context_tokens>0 drops results that exceed the token budget."""
        plan = _make_plan(max_context_tokens=50)  # very tight budget
        sc = SearchConfig()
        sc.output.source_order_output = False
        outcome = _make_outcome(effective_config=sc)
        # Each result is a large dict; at 50 token budget only 1 should survive.
        big_results = [
            {"chunk_id": f"f.py:{i}-{i + 10}:function:f{i}", "content": "x" * 150}
            for i in range(5)
        ]
        out = SearchOrchestrator._apply_source_order_and_budget(
            plan, outcome, list(big_results)
        )
        assert len(out) < len(big_results)

    def test_context_budget_zero_keeps_all(self):
        """max_context_tokens=0 means no truncation."""
        plan = _make_plan(max_context_tokens=0)
        sc = SearchConfig()
        sc.output.source_order_output = False
        outcome = _make_outcome(effective_config=sc)
        results = [
            _make_formatted(f"f.py:{i}-{i + 5}:function:f{i}") for i in range(10)
        ]
        out = SearchOrchestrator._apply_source_order_and_budget(
            plan, outcome, list(results)
        )
        assert len(out) == 10

    def test_signature_bytes_counted_by_budget(self):
        """L3's signature field is added at Block E, which runs before Block
        H's max_context_tokens truncation (_assemble's Block ordering) — the
        budget estimate (json.dumps(r) // 4) must therefore include it rather
        than silently exceeding the caller's budget. Same tight-budget shape
        as test_context_budget_truncates, but comparing a bare result set
        against an otherwise-identical set carrying a signature field: more
        bare results must survive the same budget.
        """
        sc = SearchConfig()
        sc.output.source_order_output = False
        outcome = _make_outcome(effective_config=sc)
        plan = _make_plan(max_context_tokens=50)  # tight budget, as in truncates test
        bare_results = [
            {"chunk_id": f"f.py:{i}-{i + 10}:function:f{i}"} for i in range(5)
        ]
        signed_results = [
            {
                "chunk_id": f"f.py:{i}-{i + 10}:function:f{i}",
                "signature": "x" * 150,
            }
            for i in range(5)
        ]
        bare_out = SearchOrchestrator._apply_source_order_and_budget(
            plan, outcome, list(bare_results)
        )
        signed_out = SearchOrchestrator._apply_source_order_and_budget(
            plan, outcome, list(signed_results)
        )
        assert len(signed_out) < len(bare_out)


# ---------------------------------------------------------------------------
# Composition (end-to-end, deterministic) — search-latency plan Verification
# ---------------------------------------------------------------------------


def _build_composition_graph_storage(tmp_path):
    """A real, tiny CodeGraphStorage — a→b→c call chain — used in place of a
    mock so Fix 3's storage-level centrality memo (version-keyed cache on
    CodeGraphStorage) is genuinely exercised: cold on the first run() call,
    warm on the second, against the *same* instance across both calls.
    """
    from graph.graph_storage import CodeGraphStorage

    storage = CodeGraphStorage(project_id="composition-test", storage_dir=tmp_path)
    storage.add_node("a.py:1-10:function:alpha", "alpha", "function", "a.py")
    storage.add_node("b.py:1-10:function:beta", "beta", "function", "b.py")
    storage.add_node("c.py:1-10:function:gamma", "gamma", "function", "c.py")
    # Full chunk_ids as callee_name (not bare names) so the edges land directly
    # between the tracked nodes instead of spawning separate symbol-name stubs.
    storage.add_call_edge(
        "a.py:1-10:function:alpha",
        "b.py:1-10:function:beta",
        line_number=5,
        is_resolved=True,
    )
    storage.add_call_edge(
        "b.py:1-10:function:beta",
        "c.py:1-10:function:gamma",
        line_number=7,
        is_resolved=True,
    )
    return storage


def _make_composition_results():
    """Fresh SearchResult-like objects each call — chunk_ids match the graph
    nodes above so centrality annotation has something real to attach to.
    """
    specs = [
        ("a.py:1-10:function:alpha", 0.9, "a.py", "alpha"),
        ("b.py:1-10:function:beta", 0.8, "b.py", "beta"),
        ("c.py:1-10:function:gamma", 0.7, "c.py", "gamma"),
    ]
    return [
        SimpleNamespace(
            chunk_id=chunk_id,
            score=score,
            metadata={
                "relative_path": path,
                "start_line": 1,
                "end_line": 10,
                "chunk_type": "function",
                "name": name,
            },
        )
        for chunk_id, score, path, name in specs
    ]


def _make_composition_searcher(graph_storage):
    """A non-HybridSearcher mock (isinstance checks in _search/_assemble stay
    False, matching _make_ready_searcher's style) whose dense_index carries
    the real graph_storage, so GraphScoringStage reads it via
    SearcherView(searcher).index_manager -> dense_index.graph_storage.
    """
    searcher = Mock()
    searcher.is_ready = True
    searcher.index_manager = None  # HybridSearcher-shaped: manager is at .dense_index
    dense = Mock()
    dense.index = Mock()
    dense.index.ntotal = 1000
    dense.graph_storage = graph_storage
    searcher.dense_index = dense
    searcher.search = Mock(side_effect=lambda **kwargs: _make_composition_results())
    return searcher


class TestSearchLatencyComposition:
    """End-to-end composition proof for the search-latency plan (Fixes 3-5).

    The per-fix equivalence tests (test_centrality_ranker.py, test_graph_storage.py,
    test_graph_scoring_stage.py) each prove one fix preserves its own output in
    isolation. This class proves the fixes compose: a full SearchOrchestrator.run()
    round-trip through a REAL CodeGraphStorage — so Fix 3's memo is genuinely cold
    on the first call and genuinely warm on the second, both under the read lock
    Fix 5 now extends through _assemble — must not change the response between
    calls. HybridSearcher's own retrieval (BM25/FAISS/RRF) stays mocked with a
    fixed, deterministic return, as elsewhere in this file; the composition risk
    under test lives in SearchOrchestrator/GraphScoringStage/CentralityRanker/
    CodeGraphStorage, not in the mocked searcher.
    """

    @pytest.mark.asyncio
    async def test_cold_and_warm_centrality_memo_produce_identical_response(
        self, tmp_path
    ):
        """First run() populates the storage-level centrality memo (cold);
        second run() hits it (warm, Fix 3). Both skip discarded subgraph
        extraction by default (Fix 4 — output.include_subgraph=False). The
        two responses must be byte-identical.
        """
        graph_storage = _build_composition_graph_storage(tmp_path)
        searcher = _make_composition_searcher(graph_storage)
        sc = SearchConfig()
        sc.reranker.enabled = False

        args = {
            "query": "alpha",
            "k": 3,
            "auto_reindex": False,
            "max_age_minutes": 5.0,
            "max_context_tokens": 0,
        }

        with _patch_execute(real_sc=sc) as (_, mock_gs):
            mock_gs.return_value = searcher
            orchestrator = SearchOrchestrator()
            first = await orchestrator.run(dict(args))
            second = await orchestrator.run(dict(args))

        assert first == second
        # Sanity: prove centrality actually ran and annotated real scores — a
        # vacuous pass (e.g. an empty-graph short-circuit) would make the
        # equivalence assertion above meaningless.
        assert any(r.get("centrality", 0) > 0 for r in first["results"])

    @pytest.mark.asyncio
    async def test_reranker_enabled_does_not_crash(self, tmp_path):
        """Smoke check only, per the plan's explicit non-determinism carve-out:
        with reranker.enabled=True the composed pipeline must not crash. Not
        asserting output equality here — the real neural reranker is
        nondeterministic run-to-run (no torch.manual_seed anywhere in the
        stack); this test keeps the searcher mocked/deterministic and only
        flips the config flag, proving the reranker-on branches (source-order
        warning check, response assembly) compose without raising.
        """
        graph_storage = _build_composition_graph_storage(tmp_path)
        searcher = _make_composition_searcher(graph_storage)
        sc = SearchConfig()
        sc.reranker.enabled = True

        args = {
            "query": "alpha",
            "k": 3,
            "auto_reindex": False,
            "max_age_minutes": 5.0,
            "max_context_tokens": 0,
        }

        with _patch_execute(real_sc=sc) as (_, mock_gs):
            mock_gs.return_value = searcher
            result = await SearchOrchestrator().run(args)

        assert isinstance(result, dict)
        assert "results" in result
