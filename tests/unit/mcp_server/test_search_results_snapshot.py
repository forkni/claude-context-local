"""Snapshot tests for mcp_server.tools.search_handlers._format_search_results.

Pins the list[dict] output contract for the HybridSearcher result format
(the else-branch in _format_search_results that handles SearchResult objects).

All test fixtures use fixed float scores → no masking needed.
Run ``pytest --snapshot-update tests/unit/mcp_server/test_search_results_snapshot.py``
once to generate JSON snapshots, then commit the ``__snapshots__/`` dir.
"""

import pytest
from syrupy.extensions.json import JSONSnapshotExtension

from mcp_server.tools.search_handlers import _format_search_results
from search.reranker import SearchResult


@pytest.fixture
def snapshot(snapshot):
    """Use diffable JSON serialisation instead of the default amber format."""
    return snapshot.use_extension(JSONSnapshotExtension)


def _sr(
    chunk_id: str,
    score: float,
    metadata: dict,
    source: str = "hybrid",
    rank: int = 0,
) -> SearchResult:
    """Construct a SearchResult with explicit field values."""
    return SearchResult(
        chunk_id=chunk_id,
        score=score,
        metadata=metadata,
        source=source,
        rank=rank,
    )


class TestFormatSearchResultsSnapshot:
    """Snapshot the formatted list[dict] for representative SearchResult inputs."""

    def test_empty_results(self, snapshot):
        """Empty input → empty list."""
        assert _format_search_results([]) == snapshot

    def test_standard_function_and_class(self, snapshot):
        """Two results: function (no extras) and class (with reranker_score).

        Output keys expected:
          - function: file, lines, kind, score, chunk_id, name, source
          - class: file, lines, kind, score, chunk_id, name, reranker_score, source
        """
        results = [
            _sr(
                "search/config.py:function:get_config",
                score=0.875,
                metadata={
                    "relative_path": "search/config.py",
                    "start_line": 10,
                    "end_line": 25,
                    "chunk_type": "function",
                    "name": "get_config",
                },
                source="hybrid",
                rank=0,
            ),
            _sr(
                "search/hybrid_searcher.py:class:HybridSearcher",
                score=0.812,
                metadata={
                    "relative_path": "search/hybrid_searcher.py",
                    "start_line": 50,
                    "end_line": 120,
                    "chunk_type": "class",
                    "name": "HybridSearcher",
                    "reranker_score": 0.9234,
                },
                source="dense",
                rank=1,
            ),
        ]
        assert _format_search_results(results) == snapshot

    def test_module_result_with_docstring(self, snapshot):
        """Module/community chunk type → summary key added (truncated to 200 chars)."""
        results = [
            _sr(
                "search/config.py:module:config",
                score=0.750,
                metadata={
                    "relative_path": "search/config.py",
                    "start_line": 1,
                    "end_line": 8,
                    "chunk_type": "module",
                    "name": "config",
                    "docstring": (
                        "Configuration classes for semantic code search and embedding "
                        "models. Loaded once from search_config.json at server start."
                    ),
                },
                source="hybrid",
            ),
        ]
        assert _format_search_results(results) == snapshot

    def test_ego_graph_result_with_complexity(self, snapshot):
        """Ego-graph neighbor with complexity_score → both source and complexity added."""
        results = [
            _sr(
                "utils/helpers.py:function:normalize",
                score=0.650,
                metadata={
                    "relative_path": "utils/helpers.py",
                    "start_line": 5,
                    "end_line": 15,
                    "chunk_type": "function",
                    "name": "normalize",
                    "complexity_score": 3,
                },
                source="ego_graph",
            ),
        ]
        assert _format_search_results(results) == snapshot
