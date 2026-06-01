"""Unit tests for SearchOrchestrator (Phases B–D)."""

from __future__ import annotations

import dataclasses
from unittest.mock import Mock, patch

import pytest

from mcp_server.tools.search_orchestrator import ExecutionOutcome, SearchOrchestrator
from search.config import SearchConfig
from search.exceptions import DimensionMismatchError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan(
    query="test query",
    k=4,
    model_key="qwen3_0.6b",
    intent_decision=None,
    search_mode="hybrid",
    ego_graph_enabled=False,
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
    suggested_bm25=None,
    suggested_dense=None,
):
    from mcp_server.tools.search_orchestrator import SearchPlan

    return SearchPlan(
        query=query,
        k=k,
        selected_model_key=model_key,
        routing_info=None,
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
        suggested_bm25=suggested_bm25,
        suggested_dense=suggested_dense,
    )


def _dim_mismatch_error():
    err = DimensionMismatchError("test mismatch")
    err.embedder_model = "qwen3_0.6b"
    err.embedder_dim = 1024
    err.index_dim = 768
    return err


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
                "mcp_server.tools.search_handlers._check_auto_reindex",
                return_value=(False, None),
            ),
            patch(
                "mcp_server.tools.search_handlers._get_index_manager_from_searcher",
                return_value=None,
            ),
        ):
            st = Mock()
            st.current_project = project
            st.searcher = None
            mock_state.return_value = st
            mock_cm.return_value.get_search_mode_for_query.return_value = "hybrid"
            mock_cfg.return_value.performance.use_parallel_search = False
            yield mock_state, mock_get_searcher

    return _ctx()


def _make_ready_searcher():
    """Create a mock HybridSearcher that is ready (1000 chunks)."""
    s = Mock()
    s.is_ready = True
    s.bm25_weight = 0.35
    s.dense_weight = 0.65
    dense = Mock()
    dense.index = Mock()
    dense.index.ntotal = 1000
    s.dense_index = dense
    s.search = Mock(return_value=[])
    return s


# ---------------------------------------------------------------------------
# Phase B: _execute
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
            result = await SearchOrchestrator()._execute(plan)
        assert isinstance(result, dict)
        assert result["error"] == "Dimension mismatch"
        assert "force_reindex" in result["recovery_suggestion"]

    @pytest.mark.asyncio
    async def test_get_searcher_dimension_mismatch_returns_error_dict(self):
        plan = _make_plan()
        err = _dim_mismatch_error()
        with _patch_execute() as (_, mock_gs):
            mock_gs.side_effect = err
            result = await SearchOrchestrator()._execute(plan)
        assert isinstance(result, dict)
        assert result["error"] == "Dimension mismatch"


class TestExecuteReadinessCheck:
    @pytest.mark.asyncio
    async def test_not_ready_searcher_returns_no_index_error(self):
        plan = _make_plan()
        s = Mock()
        s.is_ready = False
        dense = Mock()
        dense.index = Mock()
        dense.index.ntotal = 0
        s.dense_index = dense
        with _patch_execute() as (_, mock_gs):
            mock_gs.return_value = s
            result = await SearchOrchestrator()._execute(plan)
        assert isinstance(result, dict)
        assert "No indexed project" in result["error"]

    @pytest.mark.asyncio
    async def test_zero_chunks_searcher_returns_no_index_error(self):
        plan = _make_plan()
        s = Mock(spec=["index_manager"])
        s.index_manager.get_stats.return_value = {"total_chunks": 0}
        with _patch_execute() as (_, mock_gs):
            mock_gs.return_value = s
            result = await SearchOrchestrator()._execute(plan)
        assert isinstance(result, dict)
        assert "No indexed project" in result["error"]


class TestExecuteHappyPath:
    @pytest.mark.asyncio
    async def test_returns_execution_outcome(self):
        plan = _make_plan()
        searcher = _make_ready_searcher()
        with _patch_execute() as (_, mock_gs):
            mock_gs.return_value = searcher
            result = await SearchOrchestrator()._execute(plan)
        assert isinstance(result, ExecutionOutcome)
        assert result.searcher is searcher
        assert isinstance(result.effective_config, SearchConfig)

    @pytest.mark.asyncio
    async def test_search_called_with_plan_k_and_query(self):
        plan = _make_plan(query="find embedder", k=7)
        searcher = _make_ready_searcher()
        with _patch_execute() as (_, mock_gs):
            mock_gs.return_value = searcher
            await SearchOrchestrator()._execute(plan)
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
            await SearchOrchestrator()._execute(plan)

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
            await SearchOrchestrator()._execute(plan)
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
            await SearchOrchestrator()._execute(plan)
        assert sc.ego_graph.enabled == original_ego_enabled


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
            "communities": {"1": {"label": "search", "count": 1}},
        }
        with patch(
            "mcp_server.guidance.add_system_message", side_effect=lambda r, **kw: r
        ):
            response = SearchOrchestrator._build_response(plan, results, subgraph_data)
        assert response["subgraph_nodes"] == subgraph_data["nodes"]
        assert response["subgraph_edges"] == subgraph_data["edges"]
        assert response["subgraph_order"] == subgraph_data["topology_order"]
        assert response["subgraph_communities"] == subgraph_data["communities"]

    def test_build_response_subgraph_without_optional_keys(self):
        """subgraph_order and subgraph_communities are omitted when absent."""
        plan = _make_plan()
        subgraph_data = {"nodes": [{"id": "a"}], "edges": []}
        with patch(
            "mcp_server.guidance.add_system_message", side_effect=lambda r, **kw: r
        ):
            response = SearchOrchestrator._build_response(plan, [], subgraph_data)
        assert "subgraph_nodes" in response
        assert "subgraph_order" not in response
        assert "subgraph_communities" not in response

    def test_build_response_routing_gated_by_confidence(self):
        """routing key included when confidence<0.9 or reason contains 'Fallback'/'routed'."""
        plan_low = dataclasses.replace(
            _make_plan(),
            routing_info={"confidence": 0.7, "reason": "routed to model"},
        )
        plan_high = dataclasses.replace(
            _make_plan(),
            routing_info={"confidence": 0.95, "reason": "direct match"},
        )
        with patch(
            "mcp_server.guidance.add_system_message", side_effect=lambda r, **kw: r
        ):
            r_low = SearchOrchestrator._build_response(plan_low, [], None)
            r_high = SearchOrchestrator._build_response(plan_high, [], None)
        assert "routing" in r_low
        assert "routing" not in r_high


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
            "mcp_server.tools.search_handlers._reorder_by_source_position",
            return_value=list(reversed(results)),
        ) as mock_reorder:
            out = SearchOrchestrator._apply_source_order_and_budget(
                _make_plan(max_context_tokens=0), outcome, list(results)
            )
        mock_reorder.assert_called_once()
        assert out == list(reversed(results))

    def test_source_order_skipped_when_single_result(self):
        sc = SearchConfig()
        sc.output.source_order_output = True
        outcome = _make_outcome(effective_config=sc)
        single = [_make_formatted()]
        with patch(
            "mcp_server.tools.search_handlers._reorder_by_source_position"
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
