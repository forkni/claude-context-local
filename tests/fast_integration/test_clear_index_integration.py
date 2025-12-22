"""Integration tests for clear_index functionality (BM25 + Dense).

Uses mocked embeddings for fast execution (~1s) without GPU requirements.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from mcp_server.state import get_state
from mcp_server.tool_handlers import (
    handle_clear_index,
    handle_get_index_status,
    handle_index_directory,
)


def _create_test_project(project_dir: Path):
    """Create minimal test project for indexing."""
    project_dir.mkdir(parents=True, exist_ok=True)

    test_file = project_dir / "test_module.py"
    test_file.write_text(
        '''
def hello_world():
    """Simple test function."""
    return "Hello, World!"

class TestClass:
    """Simple test class."""
    def method(self):
        return 42
'''
    )


@pytest.fixture
def mock_embedder():
    """Mock embedder to avoid GPU/model requirements."""

    def mock_encode(sentences, **kwargs):
        if isinstance(sentences, str):
            return np.random.rand(768).astype(np.float32)
        return np.random.rand(len(sentences), 768).astype(np.float32)

    with patch("embeddings.embedder.SentenceTransformer") as mock_st:
        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_model.max_seq_length = 512
        mock_model.device = "cpu"
        mock_st.return_value = mock_model
        yield mock_st


@pytest.mark.asyncio
async def test_clear_index_clears_bm25_and_dense(mock_embedder):
    """Integration test: clear_index removes BOTH BM25 and dense indices."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        _create_test_project(project_dir)

        # Step 1: Index project
        result = await handle_index_directory(
            {
                "directory_path": str(project_dir),
                "incremental": False,
                "multi_model": False,
            }
        )
        assert "error" not in result, f"Index failed: {result}"

        # Step 2: Verify non-zero counts
        status_before = await handle_get_index_status({})
        stats_before = status_before.get("index_statistics", {})
        assert stats_before.get("bm25_documents", 0) > 0, "BM25 should have docs"
        assert stats_before.get("dense_vectors", 0) > 0, "Dense should have vectors"

        # Step 3: Clear index
        clear_result = await handle_clear_index({})
        assert clear_result.get("success") is True

        # Step 4: Verify zero counts after clear
        status_after = await handle_get_index_status({})
        stats_after = status_after.get("index_statistics", {})
        assert stats_after.get("bm25_documents", -1) == 0, "BM25 should be cleared"
        assert stats_after.get("dense_vectors", -1) == 0, "Dense should be cleared"
        assert (
            stats_after.get("total_chunks", -1) == 0
        ), "Total chunks should be 0 after clear"
        assert stats_after.get("synced", False) is True, "Indices should be synced"


@pytest.mark.asyncio
async def test_clear_index_persists_after_searcher_recreation(mock_embedder):
    """
    Verify BM25 stays cleared after searcher is recreated.

    This test validates the critical fix: BM25 files must be DELETED from disk,
    not just recreated in memory, to prevent reload on next searcher creation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        _create_test_project(project_dir)

        # Step 1: Index project
        result = await handle_index_directory(
            {
                "directory_path": str(project_dir),
                "incremental": False,
                "multi_model": False,
            }
        )
        assert "error" not in result, f"Index failed: {result}"

        # Step 2: Verify initial counts > 0
        status1 = await handle_get_index_status({})
        stats1 = status1.get("index_statistics", {})
        bm25_before = stats1.get("bm25_documents", 0)
        dense_before = stats1.get("dense_vectors", 0)
        assert bm25_before > 0, "BM25 should have docs before clear"
        assert dense_before > 0, "Dense should have vectors before clear"

        # Step 3: Force save to disk (simulate real indexing behavior)
        state = get_state()
        if state.searcher and hasattr(state.searcher, "bm25_index"):
            state.searcher.bm25_index.save()

        # Step 4: Clear index
        clear_result = await handle_clear_index({})
        assert clear_result.get("success") is True

        # Step 5: Simulate server restart - clear in-memory state
        state.searcher = None
        state.index_manager = None

        # Step 6: Get status again (creates NEW searcher, triggers load())
        status2 = await handle_get_index_status({})
        stats2 = status2.get("index_statistics", {})

        # THIS IS THE KEY ASSERTION - BM25 should NOT reload from disk
        assert (
            stats2.get("bm25_documents", -1) == 0
        ), f"BM25 reloaded from disk after clear: {stats2.get('bm25_documents')} docs (expected 0)"
        assert stats2.get("dense_vectors", -1) == 0, "Dense should stay cleared"
        assert (
            stats2.get("total_chunks", -1) == 0
        ), "Total chunks should be 0 after clear"
        assert (
            stats2.get("synced", False) is True
        ), "Indices should be synced after clear"
