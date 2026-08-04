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
        results, _latency_ms = await _run_query(
            orchestrator, searcher, "some query", k=10
        )

    assert [r.chunk_id for r in results] == [
        "search/bm25_index.py:method:BM25Index.index_documents",
        "search/faiss_index.py:method:FaissVectorIndex.search",
    ]


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
        results, _latency_ms = await _run_query(
            orchestrator, searcher, "some query", k=10
        )

    assert [r.chunk_id for r in results] == ["from_results"]


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
        results, _latency_ms = await _run_query(
            orchestrator, searcher, "some query", k=10
        )

    assert results == []
