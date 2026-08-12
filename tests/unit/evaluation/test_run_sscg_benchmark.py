"""Regression tests for the benchmark harness's ``_run_query`` adapter.

``_run_query`` (``scripts/benchmark/run_sscg_benchmark.py``) drives every
query -- including category-F -- through ``SearchOrchestrator.run()`` and
reads its ``"results"`` key. Two related bugs were found by tracing why one
131q benchmark round returned ``retrieved: []`` for all 9 category-F queries
with no error:

1. The harness pins ``intent.enabled = False`` once at startup by mutating
   the cached ``SearchConfig`` singleton in place. ``get_search_config()``
   does an unconditional ``stat()`` on every call, so any config-file write
   during the run (e.g. a concurrent MCP server process) silently reloads
   from disk and undoes the pin.
2. Once intent classification is live, ``SearchOrchestrator`` can redirect a
   SIMILARITY-intent query to ``handle_find_similar_code``, whose response
   shape is ``{"reference_chunk", "similar_chunks"}`` -- no ``"results"``
   key. ``_run_query`` read only ``"results"``, so a redirect silently
   scored as zero retrieved results instead of being read correctly.

These tests pin both fixes: the pin is re-asserted per query, and a
``similar_chunks``-shaped response is parsed like a normal one.

B1b (ADR-0023) added two more things this file covers: ``pin_intent_off``
makes the re-pin arm-aware (an arm that deliberately turns intent on via
``arm_overrides`` must not have its override silently undone every query),
and ``_run_query`` now returns a 3-tuple whose third element,
``redirect_kind``, distinguishes a ``find_similar`` redirect (already scored
via the ``similar_chunks`` fallback) from a ``find_path`` redirect (whose
``{"path_found": ...}`` response has no ranked chunk list to score at all)
from ordinary, non-redirected results (``None``).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.benchmark.run_sscg_benchmark import _run_query


@pytest.mark.asyncio
async def test_run_query_reasserts_intent_disabled_before_each_call():
    """intent.enabled is forced False on every call, not just once at startup.

    Guards against SearchConfigManager's mtime-cache silently reviving
    intent classification mid-run (any config-file write during the run
    reloads from disk and would otherwise undo a startup-only pin).
    """
    mock_config = MagicMock()
    mock_config.intent.enabled = True  # simulate a reverted pin
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value={"results": []})
    searcher = MagicMock(dense_index=None)

    with patch("search.config.get_search_config", return_value=mock_config):
        await _run_query(orchestrator, searcher, "some query", k=10)

    assert mock_config.intent.enabled is False


@pytest.mark.asyncio
async def test_run_query_falls_back_to_similar_chunks_response_shape():
    """A find_similar_code-style redirect response is scored, not dropped.

    Response has no "results" key -- only "reference_chunk"/"similar_chunks",
    exactly what handle_find_similar_code returns
    (mcp_server/tools/search_handlers.py:341-344).
    """
    mock_config = MagicMock()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(
        return_value={
            "reference_chunk": "search/bm25_index.py:method:BM25Index.search",
            "similar_chunks": [
                {
                    "chunk_id": "search/bm25_index.py:method:BM25Index.index_documents",
                    "score": 0.9,
                },
                {
                    "chunk_id": "search/faiss_index.py:method:FaissVectorIndex.search",
                    "score": 0.8,
                },
            ],
        }
    )
    searcher = MagicMock(dense_index=None)

    with patch("search.config.get_search_config", return_value=mock_config):
        results, _latency_ms, redirect_kind = await _run_query(
            orchestrator, searcher, "some query", k=10
        )

    assert [r.chunk_id for r in results] == [
        "search/bm25_index.py:method:BM25Index.index_documents",
        "search/faiss_index.py:method:FaissVectorIndex.search",
    ]
    assert redirect_kind == "find_similar"


@pytest.mark.asyncio
async def test_run_query_prefers_results_key_when_both_present():
    """ "results" wins over "similar_chunks" when a response somehow has both."""
    mock_config = MagicMock()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(
        return_value={
            "results": [{"chunk_id": "from_results", "score": 1.0}],
            "similar_chunks": [{"chunk_id": "from_similar_chunks", "score": 1.0}],
        }
    )
    searcher = MagicMock(dense_index=None)

    with patch("search.config.get_search_config", return_value=mock_config):
        results, _latency_ms, redirect_kind = await _run_query(
            orchestrator, searcher, "some query", k=10
        )

    assert [r.chunk_id for r in results] == ["from_results"]
    assert redirect_kind is None


@pytest.mark.asyncio
async def test_run_query_returns_empty_for_genuinely_empty_results():
    """A response with an empty "results" list still scores as empty.

    Distinguishes "no results" (correct: []) from "wrong key" (bug: []).
    """
    mock_config = MagicMock()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value={"results": []})
    searcher = MagicMock(dense_index=None)

    with patch("search.config.get_search_config", return_value=mock_config):
        results, _latency_ms, redirect_kind = await _run_query(
            orchestrator, searcher, "some query", k=10
        )

    assert results == []
    assert redirect_kind is None


@pytest.mark.asyncio
async def test_run_query_detects_find_path_redirect():
    """A find_path redirect (``{"path_found": ...}``) is flagged, not silently
    scored as empty results.

    ``handle_find_path``'s response shape has no ``"results"`` or
    ``"similar_chunks"`` key -- a path result isn't a ranked chunk list, so
    there is nothing to score it against golden chunk IDs with. B1b's
    ``mrr_excl_redirect`` (computed in ``run_single``) relies on this signal
    to exclude these queries instead of zero-scoring them.
    """
    mock_config = MagicMock()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(
        return_value={
            "path_found": True,
            "path": ["a", "b"],
            "path_length": 1,
            "source": {"chunk_id": "a"},
            "target": {"chunk_id": "b"},
            "edge_types_traversed": ["calls"],
            "system_message": "found",
        }
    )
    searcher = MagicMock(dense_index=None)

    with patch("search.config.get_search_config", return_value=mock_config):
        results, _latency_ms, redirect_kind = await _run_query(
            orchestrator, searcher, "some query", k=10
        )

    assert results == []
    assert redirect_kind == "find_path"


@pytest.mark.asyncio
async def test_run_query_pin_intent_off_false_skips_repin():
    """B1b: an arm that turns intent on via overrides isn't undone per query.

    ``run_single`` passes ``pin_intent_off=False`` when the arm's overrides
    already set ``intent.enabled`` -- the unconditional re-pin this file's
    other tests exercise would otherwise silently defeat that arm every
    query.
    """
    mock_config = MagicMock()
    mock_config.intent.enabled = True
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value={"results": []})
    searcher = MagicMock(dense_index=None)

    with patch("search.config.get_search_config", return_value=mock_config):
        await _run_query(
            orchestrator, searcher, "some query", k=10, pin_intent_off=False
        )

    assert mock_config.intent.enabled is True


@pytest.mark.asyncio
async def test_run_query_ego_per_request_absent_by_default():
    """No prior capture ever set ``ego_graph_enabled`` -- confirm the default
    stays that way, or every existing canon capture is silently reinterpreted.

    ``plan.ego_graph_enabled`` gates QW5 (``build_effective_config``'s
    intent-adaptive ego similarity threshold); it must stay unset unless a
    caller opts in via ``ego_per_request=True``.
    """
    mock_config = MagicMock()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value={"results": []})
    searcher = MagicMock(dense_index=None)

    with patch("search.config.get_search_config", return_value=mock_config):
        await _run_query(orchestrator, searcher, "some query", k=10)

    called_arguments = orchestrator.run.await_args.args[0]
    assert "ego_graph_enabled" not in called_arguments


@pytest.mark.asyncio
async def test_run_query_ego_per_request_true_sets_plan_flag():
    """``ego_per_request=True`` sets ``ego_graph_enabled=True`` in the
    ``SearchOrchestrator.run()`` arguments dict -- the one-line change that
    lets the harness exercise QW5 for the first time (see
    ``docs/adr/0030-deepen-config-searcher-seam.md``'s Out of scope section).
    """
    mock_config = MagicMock()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value={"results": []})
    searcher = MagicMock(dense_index=None)

    with patch("search.config.get_search_config", return_value=mock_config):
        await _run_query(
            orchestrator, searcher, "some query", k=10, ego_per_request=True
        )

    called_arguments = orchestrator.run.await_args.args[0]
    assert called_arguments["ego_graph_enabled"] is True
