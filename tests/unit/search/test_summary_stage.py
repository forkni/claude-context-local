"""Unit tests for search/summary_stage.py.

Verifies:
- compute_community_summaries delegates correctly and returns [] on failure
- generate_module_summaries delegates correctly and returns [] on failure
- Centrality enriches hub detection; centrality failure falls back gracefully
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chunking.python_ast_chunker import CodeChunk
from search.summary_stage import SummaryStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    rel_path: str,
    chunk_type: str,
    name: str,
    start_line: int = 1,
    end_line: int = 10,
    parent_name: str | None = None,
    docstring: str | None = None,
    imports: list | None = None,
) -> CodeChunk:
    chunk_id = f"{rel_path}:{start_line}-{end_line}:{chunk_type}:{name}"
    return CodeChunk(
        content=f"def {name}(): pass",
        chunk_type=chunk_type,
        start_line=start_line,
        end_line=end_line,
        file_path=f"/project/{rel_path}",
        relative_path=rel_path,
        folder_structure=list(Path(rel_path).parent.parts),
        name=name,
        parent_name=parent_name,
        docstring=docstring,
        imports=imports or [],
        language="python",
        chunk_id=chunk_id,
    )


# ---------------------------------------------------------------------------
# SummaryStage.compute_community_summaries
# ---------------------------------------------------------------------------


class TestComputeCommunitySummaries:
    def setup_method(self):
        self.stage = SummaryStage()

    def _two_chunk_map(self):
        """Two chunks in community 0 — enough to generate a summary."""
        chunks = [
            _make_chunk("search/foo.py", "class", "Foo"),
            _make_chunk("search/foo.py", "function", "bar"),
        ]
        community_map = {
            chunks[0].chunk_id: 0,
            chunks[1].chunk_id: 0,
        }
        return chunks, community_map

    def test_returns_community_chunks_for_qualifying_community(self):
        chunks, community_map = self._two_chunk_map()
        result = self.stage.compute_community_summaries(chunks, community_map, None)
        assert len(result) == 1
        assert result[0].chunk_type == "community"

    def test_no_temp_graph_skips_centrality(self):
        chunks, community_map = self._two_chunk_map()
        result = self.stage.compute_community_summaries(chunks, community_map, None)
        assert len(result) == 1
        assert "centrality:" not in result[0].content

    def test_centrality_failure_falls_back_gracefully(self):
        """If GraphQueryEngine raises, summaries still produced (line-count hub)."""
        chunks, community_map = self._two_chunk_map()
        mock_graph = MagicMock()
        with patch("graph.graph_queries.GraphQueryEngine") as mock_gqe_cls:
            mock_gqe_cls.return_value.compute_centrality.side_effect = RuntimeError("unavailable")
            result = self.stage.compute_community_summaries(chunks, community_map, mock_graph)
        assert len(result) == 1  # fell back, still generated

    def test_centrality_enriches_hub_annotation(self):
        chunks = [
            _make_chunk("a.py", "function", "small", start_line=1, end_line=5),
            _make_chunk("a.py", "function", "large", start_line=10, end_line=100),
        ]
        community_map = {chunks[0].chunk_id: 0, chunks[1].chunk_id: 0}
        mock_graph = MagicMock()
        centrality = {chunks[0].chunk_id: 0.9, chunks[1].chunk_id: 0.1}
        with patch("graph.graph_queries.GraphQueryEngine") as mock_gqe_cls:
            mock_gqe_cls.return_value.compute_centrality.return_value = centrality
            result = self.stage.compute_community_summaries(chunks, community_map, mock_graph)
        assert "Hub function: small" in result[0].content
        assert "centrality: 0.9000" in result[0].content

    def test_returns_empty_on_generate_failure(self):
        chunks, community_map = self._two_chunk_map()
        with patch(
            "graph.community_summarizer.generate_community_summaries",
            side_effect=RuntimeError("boom"),
        ):
            result = self.stage.compute_community_summaries(chunks, community_map, None)
        assert result == []

    def test_single_member_community_produces_no_summary(self):
        chunks = [_make_chunk("solo.py", "function", "solo")]
        community_map = {chunks[0].chunk_id: 0}
        result = self.stage.compute_community_summaries(chunks, community_map, None)
        assert result == []


# ---------------------------------------------------------------------------
# SummaryStage.generate_module_summaries
# ---------------------------------------------------------------------------


class TestGenerateModuleSummaries:
    def setup_method(self):
        self.stage = SummaryStage()

    def test_returns_module_summary_chunks(self):
        chunks = [
            _make_chunk("utils/helpers.py", "function", "helper"),
            _make_chunk("utils/helpers.py", "function", "other"),
        ]
        result = self.stage.generate_module_summaries(chunks)
        assert len(result) >= 1
        for chunk in result:
            assert chunk.chunk_type == "module"

    def test_returns_empty_on_failure(self):
        with patch(
            "chunking.file_summarizer.generate_file_summaries",
            side_effect=RuntimeError("disk error"),
        ):
            result = self.stage.generate_module_summaries([])
        assert result == []

    def test_returns_empty_list_for_empty_chunks(self):
        result = self.stage.generate_module_summaries([])
        assert isinstance(result, list)
