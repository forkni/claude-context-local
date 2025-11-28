"""Integration test that follows the exact MCP tool implementation path."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from huggingface_hub import HfFolder

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager


def _has_hf_token():
    """Check if HuggingFace token is available."""
    return HfFolder.get_token() is not None


@pytest.mark.slow
class TestMCPIndexing:
    """Test that follows the exact same path as the MCP index_directory tool."""

    @pytest.fixture(autouse=True)
    def mock_embedder(self):
        """Mock SentenceTransformer to prevent model downloads."""

        def mock_encode(sentences, show_progress_bar=False):
            if isinstance(sentences, str):
                return np.ones(768, dtype=np.float32) * 0.5
            else:
                return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

        with patch("embeddings.embedder.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.encode.side_effect = mock_encode
            mock_st.return_value = mock_model
            yield mock_st

    @pytest.fixture
    def test_project_path(self):
        """Path to the test Python project."""
        return Path(__file__).parent.parent / "test_data" / "python_project"

    @pytest.fixture
    def mock_storage_dir(self):
        """Create a temporary storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "test_storage"

    def test_mcp_index_directory_path(self, test_project_path, mock_storage_dir):
        """Test indexing following the exact MCP tool implementation path."""

        # This follows the exact implementation in mcp_server/server.py index_directory()
        directory_path = Path(test_project_path).resolve()
        project_name = directory_path.name
        incremental = False  # Force full index for test

        # Initialize components EXACTLY as in the MCP tool
        index_manager = CodeIndexManager(str(mock_storage_dir))
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(
            str(directory_path)
        )  # Initialize with project root

        incremental_indexer = IncrementalIndexer(
            indexer=index_manager, embedder=embedder, chunker=chunker
        )

        # Perform indexing - this is the exact call from the MCP tool
        result = incremental_indexer.incremental_index(
            str(directory_path), project_name, force_full=not incremental
        )

        # Get updated statistics - same as MCP tool
        stats = incremental_indexer.get_indexing_stats(str(directory_path))

        # Build response exactly as MCP tool does
        response = {
            "success": result.success,
            "directory": str(directory_path),
            "project_name": project_name,
            "incremental": incremental and result.files_modified > 0,
            "files_added": result.files_added,
            "files_removed": result.files_removed,
            "files_modified": result.files_modified,
            "chunks_added": result.chunks_added,
            "chunks_removed": result.chunks_removed,
            "time_taken": round(result.time_taken, 2),
            "index_stats": stats,
        }

        if result.error:
            response["error"] = result.error

        # Assertions - the real tool should work!
        assert result.success, f"Indexing failed: {result.error}"
        assert result.files_added > 0, "Should have indexed some files"

        assert result.chunks_added > 0, "Should have created chunks from the files"

        # Verify the response structure matches what MCP returns
        assert response["success"] is True
        assert response["files_added"] > 0
        assert response["chunks_added"] > 0

        # Cleanup embedder to free GPU memory
        embedder.cleanup()

        print(f"MCP Response: {json.dumps(response, indent=2)}")

    def test_incremental_indexing_mcp_path(self, test_project_path, mock_storage_dir):
        """Test incremental indexing following MCP implementation."""

        directory_path = Path(test_project_path).resolve()
        project_name = directory_path.name

        # Create a copy of the project for modification
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_project = Path(temp_dir) / "test_project_copy"
            shutil.copytree(test_project_path, temp_project)

            # First index - full
            index_manager = CodeIndexManager(str(mock_storage_dir))
            embedder = CodeEmbedder()
            chunker = MultiLanguageChunker(str(temp_project))

            incremental_indexer = IncrementalIndexer(
                indexer=index_manager, embedder=embedder, chunker=chunker
            )

            # Initial full index
            result1 = incremental_indexer.incremental_index(
                str(temp_project), project_name, force_full=True
            )

            assert result1.success
            assert result1.chunks_added > 0
            initial_chunks = result1.chunks_added

            # Modify a file
            auth_file = temp_project / "src" / "auth" / "authenticator.py"
            if auth_file.exists():
                content = auth_file.read_text()
                new_content = (
                    content
                    + "\n\ndef new_function():\n    '''Added by test.'''\n    return True\n"
                )
                auth_file.write_text(new_content)

            # Re-index with incremental=True (MCP default)
            # Need to create new chunker for modified project
            chunker2 = MultiLanguageChunker(str(temp_project))
            incremental_indexer2 = IncrementalIndexer(
                indexer=index_manager, embedder=embedder, chunker=chunker2
            )

            result2 = incremental_indexer2.incremental_index(
                str(temp_project),
                project_name,
                force_full=False,  # incremental=True in MCP means force_full=False
            )

            assert result2.success
            assert result2.files_modified > 0, "Should detect modified file"

            # The chunks should change because we modified the file
            # Note: chunks_added might be 0 if the incremental indexer
            # removes old chunks and adds new ones with the same count

            print(
                f"Initial index: {result1.files_added} files, {initial_chunks} chunks"
            )
            print(
                f"Incremental update: {result2.files_modified} files modified, "
                f"{result2.chunks_added} chunks added, {result2.chunks_removed} removed"
            )

            # Cleanup embedder to free GPU memory
            embedder.cleanup()

    def test_catches_chunk_file_bug(self, test_project_path, mock_storage_dir):
        """Test that would catch the chunk_file(path, content) bug."""

        directory_path = Path(test_project_path).resolve()

        # Create a mock chunker that validates the signature
        class StrictChunker(MultiLanguageChunker):
            def chunk_file(self, file_path: str) -> list:
                # This will fail if called with extra arguments
                # simulating the actual signature
                return super().chunk_file(file_path)

        index_manager = CodeIndexManager(str(mock_storage_dir))
        embedder = CodeEmbedder()
        chunker = StrictChunker(str(directory_path))

        incremental_indexer = IncrementalIndexer(
            indexer=index_manager, embedder=embedder, chunker=chunker
        )

        # This should work with the fix, would fail with the bug
        result = incremental_indexer.incremental_index(
            str(directory_path), "test_project", force_full=True
        )

        assert result.success, f"Failed with error: {result.error}"
        assert result.chunks_added > 0, "Should have created chunks"

        # Cleanup embedder to free GPU memory
        embedder.cleanup()
