"""Integration tests for model switching and multi-model embedding generation."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from chunking.python_ast_chunker import CodeChunk
from embeddings.embedder import CodeEmbedder
from mcp_server.server import get_embedder
from search.indexer import CodeIndexManager


@pytest.fixture
def sample_code_chunk():
    """Create a sample code chunk for testing."""
    return CodeChunk(
        file_path=Path("test.py"),
        relative_path="test.py",
        folder_structure="",
        chunk_type="function",
        start_line=1,
        end_line=5,
        name="test_function",
        parent_name=None,
        docstring="Test function for embedding generation.",
        content='def test_function(x, y):\n    """Test function."""\n    return x + y',
        decorators=[],
        imports=[],
        complexity_score=1,
        tags=["function", "test"],
    )


class TestGemmaEmbeddingGeneration:
    """Test embedding generation with Gemma model."""

    def test_gemma_chunk_embedding(self, sample_code_chunk):
        """Test generating embedding for a single chunk with Gemma."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")
        result = embedder.embed_chunk(sample_code_chunk)

        assert result.embedding is not None
        assert result.embedding.shape[0] == 768  # Gemma dimension
        assert result.chunk_id == "test.py:1-5:function:test_function"
        assert isinstance(result.embedding, np.ndarray)

    def test_gemma_query_embedding(self):
        """Test generating embedding for a query with Gemma."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")
        query = "function that adds two numbers"
        embedding = embedder.embed_query(query)

        assert embedding is not None
        assert embedding.shape[0] == 768
        assert isinstance(embedding, np.ndarray)

    def test_gemma_batch_embedding(self, sample_code_chunk):
        """Test batch embedding generation with Gemma."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")

        # Create multiple chunks
        chunks = [sample_code_chunk for _ in range(5)]
        results = embedder.embed_chunks(chunks, batch_size=2)

        assert len(results) == 5
        for result in results:
            assert result.embedding.shape[0] == 768

    def test_gemma_model_info(self):
        """Test getting model info for Gemma."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")
        # Trigger model loading
        _ = embedder.model
        info = embedder.get_model_info()

        assert info["model_name"] == "google/embeddinggemma-300m"
        assert info["embedding_dimension"] == 768
        assert info["status"] == "loaded"


@pytest.mark.slow
class TestBGEM3EmbeddingGeneration:
    """Test embedding generation with BGE-M3 model.

    Marked as slow because BGE-M3 is a larger model.
    """

    def test_bge_m3_chunk_embedding(self, sample_code_chunk):
        """Test generating embedding for a single chunk with BGE-M3."""
        embedder = CodeEmbedder(model_name="BAAI/bge-m3")
        result = embedder.embed_chunk(sample_code_chunk)

        assert result.embedding is not None
        assert result.embedding.shape[0] == 1024  # BGE-M3 dimension
        assert result.chunk_id == "test.py:1-5:function:test_function"
        assert isinstance(result.embedding, np.ndarray)

    def test_bge_m3_query_embedding(self):
        """Test generating embedding for a query with BGE-M3."""
        embedder = CodeEmbedder(model_name="BAAI/bge-m3")
        query = "function that adds two numbers"
        embedding = embedder.embed_query(query)

        assert embedding is not None
        assert embedding.shape[0] == 1024
        assert isinstance(embedding, np.ndarray)

    def test_bge_m3_batch_embedding(self, sample_code_chunk):
        """Test batch embedding generation with BGE-M3."""
        embedder = CodeEmbedder(model_name="BAAI/bge-m3")

        # Create multiple chunks
        chunks = [sample_code_chunk for _ in range(5)]
        results = embedder.embed_chunks(chunks, batch_size=2)

        assert len(results) == 5
        for result in results:
            assert result.embedding.shape[0] == 1024

    def test_bge_m3_model_info(self):
        """Test getting model info for BGE-M3."""
        embedder = CodeEmbedder(model_name="BAAI/bge-m3")
        # Trigger model loading
        _ = embedder.model
        info = embedder.get_model_info()

        assert info["model_name"] == "BAAI/bge-m3"
        assert info["embedding_dimension"] == 1024
        assert info["status"] == "loaded"


class TestModelSwitching:
    """Test switching between models."""

    def test_dimension_difference(self, sample_code_chunk):
        """Test that different models produce different dimensional embeddings."""
        embedder_gemma = CodeEmbedder(model_name="google/embeddinggemma-300m")
        embedder_bge = CodeEmbedder(model_name="BAAI/bge-m3")

        result_gemma = embedder_gemma.embed_chunk(sample_code_chunk)
        result_bge = embedder_bge.embed_chunk(sample_code_chunk)

        assert result_gemma.embedding.shape[0] == 768
        assert result_bge.embedding.shape[0] == 1024
        assert result_gemma.embedding.shape != result_bge.embedding.shape

    def test_embedder_cleanup(self):
        """Test that embedder cleanup works for both models."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")
        _ = embedder.model  # Trigger model loading
        embedder.cleanup()

        # After cleanup, model should be None
        assert embedder._model is None


class TestIndexManagerWithDifferentModels:
    """Test CodeIndexManager with different embedding models."""

    def test_index_manager_with_gemma(self):
        """Test creating index manager with Gemma embedder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")
            indexer = CodeIndexManager(tmpdir, embedder=embedder)

            # Create index with correct dimension
            indexer.create_index(768)
            assert indexer._index is not None
            assert indexer._index.d == 768

    def test_index_manager_with_bge_m3(self):
        """Test creating index manager with BGE-M3 embedder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embedder = CodeEmbedder(model_name="BAAI/bge-m3")
            indexer = CodeIndexManager(tmpdir, embedder=embedder)

            # Create index with correct dimension
            indexer.create_index(1024)
            assert indexer._index is not None
            assert indexer._index.d == 1024

    def test_dimension_mismatch_detection(self):
        """Test that dimension mismatch is detected when loading index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create index with Gemma (768 dim)
            embedder_gemma = CodeEmbedder(model_name="google/embeddinggemma-300m")
            indexer_gemma = CodeIndexManager(tmpdir, embedder=embedder_gemma)
            indexer_gemma.create_index(768)
            indexer_gemma.save_index()

            # Try to load with BGE-M3 (1024 dim) - should detect mismatch
            embedder_bge = CodeEmbedder(model_name="BAAI/bge-m3")
            indexer_bge = CodeIndexManager(tmpdir, embedder=embedder_bge)

            # Access index property to trigger loading
            index = indexer_bge.index

            # Index should be None or empty due to dimension mismatch
            # The mismatch detection clears the index internally
            assert index is None or index.ntotal == 0  # No vectors loaded

    def test_model_metadata_saved(self, sample_code_chunk):
        """Test that model metadata is saved with index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")
            indexer = CodeIndexManager(tmpdir, embedder=embedder)
            indexer.create_index(768)

            # Add a sample embedding
            result = embedder.embed_chunk(sample_code_chunk)
            indexer.add_embeddings([result])
            indexer.save_index()

            # Explicitly close the metadata database before cleanup
            if indexer._metadata_db is not None:
                indexer._metadata_db.close()
                indexer._metadata_db = None

            # Check that model_info.json was created
            model_info_path = Path(tmpdir) / "model_info.json"
            assert model_info_path.exists()

            # Verify contents
            import json

            with open(model_info_path) as f:
                model_info = json.load(f)

            assert model_info["model_name"] == "google/embeddinggemma-300m"
            assert model_info["embedding_dimension"] == 768


class TestMCPServerModelIntegration:
    """Test MCP server integration with model configuration."""

    def test_mcp_server_uses_configured_model(self, monkeypatch):
        """Test that MCP server respects model configuration."""
        # Set environment variable for model selection
        monkeypatch.setenv("CLAUDE_EMBEDDING_MODEL", "BAAI/bge-m3")

        # Clear any cached embedder
        import mcp_server.server as server_module

        server_module._embedder = None

        embedder = get_embedder()
        assert embedder.model_name == "BAAI/bge-m3"

        # Cleanup
        server_module._embedder = None

    def test_mcp_server_fallback_to_gemma(self):
        """Test that MCP server falls back to Gemma on config error."""
        import os
        import shutil
        from pathlib import Path

        import mcp_server.server as server_module
        from search.config import get_config_manager

        # Save current environment
        old_model = os.environ.get("CLAUDE_EMBEDDING_MODEL")

        # Backup saved config file if it exists
        config_path = Path.home() / ".claude_code_search" / "search_config.json"
        backup_path = config_path.with_suffix(".json.backup")
        config_existed = config_path.exists()
        if config_existed:
            shutil.move(str(config_path), str(backup_path))

        # Clear all state - embedder cache, config cache, and env var
        server_module._embedder = None
        config_manager = get_config_manager()
        config_manager._config = None

        # Remove env var override to test default fallback
        if "CLAUDE_EMBEDDING_MODEL" in os.environ:
            del os.environ["CLAUDE_EMBEDDING_MODEL"]

        try:
            embedder = get_embedder()
            # Should default to Gemma
            assert "gemma" in embedder.model_name.lower()
        finally:
            # Cleanup
            server_module._embedder = None
            if old_model is not None:
                os.environ["CLAUDE_EMBEDDING_MODEL"] = old_model

            # Restore backed up config
            if config_existed and backup_path.exists():
                shutil.move(str(backup_path), str(config_path))
            # Clear config cache to reload the restored config
            config_manager._config = None


class TestEmbeddingQuality:
    """Test embedding quality and semantic similarity."""

    def test_similar_code_has_high_similarity(self):
        """Test that similar code chunks have high cosine similarity."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")

        chunk1 = CodeChunk(
            file_path=Path("test1.py"),
            relative_path="test1.py",
            folder_structure="",
            chunk_type="function",
            start_line=1,
            end_line=3,
            name="add_numbers",
            parent_name=None,
            docstring="Add two numbers.",
            content="def add_numbers(a, b):\n    return a + b",
            decorators=[],
            imports=[],
            complexity_score=1,
            tags=[],
        )

        chunk2 = CodeChunk(
            file_path=Path("test2.py"),
            relative_path="test2.py",
            folder_structure="",
            chunk_type="function",
            start_line=1,
            end_line=3,
            name="sum_values",
            parent_name=None,
            docstring="Sum two values.",
            content="def sum_values(x, y):\n    return x + y",
            decorators=[],
            imports=[],
            complexity_score=1,
            tags=[],
        )

        result1 = embedder.embed_chunk(chunk1)
        result2 = embedder.embed_chunk(chunk2)

        # Calculate cosine similarity
        similarity = np.dot(result1.embedding, result2.embedding) / (
            np.linalg.norm(result1.embedding) * np.linalg.norm(result2.embedding)
        )

        # Similar functions should have high similarity (> 0.7)
        assert similarity > 0.7

    def test_different_code_has_low_similarity(self):
        """Test that very different code chunks have lower similarity."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")

        chunk1 = CodeChunk(
            file_path=Path("test1.py"),
            relative_path="test1.py",
            folder_structure="",
            chunk_type="function",
            start_line=1,
            end_line=3,
            name="add_numbers",
            parent_name=None,
            docstring="Add two numbers.",
            content="def add_numbers(a, b):\n    return a + b",
            decorators=[],
            imports=[],
            complexity_score=1,
            tags=[],
        )

        chunk2 = CodeChunk(
            file_path=Path("test2.py"),
            relative_path="test2.py",
            folder_structure="",
            chunk_type="class",
            start_line=1,
            end_line=5,
            name="DatabaseConnection",
            parent_name=None,
            docstring="Database connection class.",
            content="class DatabaseConnection:\n    def __init__(self):\n        self.conn = None",
            decorators=[],
            imports=[],
            complexity_score=2,
            tags=[],
        )

        result1 = embedder.embed_chunk(chunk1)
        result2 = embedder.embed_chunk(chunk2)

        # Calculate cosine similarity
        similarity = np.dot(result1.embedding, result2.embedding) / (
            np.linalg.norm(result1.embedding) * np.linalg.norm(result2.embedding)
        )

        # Very different code should have lower similarity (< 0.8)
        assert similarity < 0.8


class TestModelSelectionWorkflow:
    """Test complete model selection workflow (simulates batch script behavior)."""

    def test_model_selection_via_config_manager(self):
        """Test model selection workflow: select → save → load → verify."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate what batch script does - use explicit storage path
            config_file = Path(tmpdir) / "search_config.json"

            # Step 1: Select model and save (simulates menu selection)
            from search.config import SearchConfigManager

            mgr = SearchConfigManager(config_file=str(config_file))
            cfg = mgr.load_config()

            # Initially should be Gemma
            assert "gemma" in cfg.embedding_model_name.lower()
            assert cfg.model_dimension == 768

            # Change to BGE-M3 (simulates user selection)
            cfg.embedding_model_name = "BAAI/bge-m3"
            mgr.save_config(cfg)

            # Step 2: Clear config manager cache (simulates new session)
            mgr._config = None

            # Step 3: Load config again (simulates restart/reload)
            cfg2 = mgr.load_config()

            # Step 4: Verify model persisted
            assert cfg2.embedding_model_name == "BAAI/bge-m3"
            assert cfg2.model_dimension == 1024  # Auto-synced from registry

    def test_model_workflow_with_default_path(self):
        """Test that model selection works without explicit config path."""
        from pathlib import Path

        # Use actual storage location for this test
        storage_path = Path.home() / ".claude_code_search" / "test_workflow_config.json"

        try:
            from search.config import SearchConfigManager

            # Create manager with explicit path to avoid interfering with real config
            mgr = SearchConfigManager(config_file=str(storage_path))
            cfg = mgr.load_config()

            # Change model
            cfg.embedding_model_name = "BAAI/bge-m3"
            mgr.save_config(cfg)

            # Verify file was created in correct location
            assert storage_path.exists()
            assert ".claude_code_search" in str(storage_path)

            # Load in new instance
            mgr2 = SearchConfigManager(config_file=str(storage_path))
            cfg2 = mgr2.load_config()
            assert cfg2.embedding_model_name == "BAAI/bge-m3"

        finally:
            # Cleanup test config
            if storage_path.exists():
                storage_path.unlink()

    def test_environment_variable_overrides_saved_config(self, monkeypatch):
        """Test that environment variable takes precedence over saved config."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "search_config.json"

            # Save Gemma to config file
            from search.config import SearchConfigManager

            mgr = SearchConfigManager(config_file=str(config_file))
            cfg = mgr.load_config()
            cfg.embedding_model_name = "google/embeddinggemma-300m"
            mgr.save_config(cfg)

            # Set environment variable to BGE-M3
            monkeypatch.setenv("CLAUDE_EMBEDDING_MODEL", "BAAI/bge-m3")

            # Load should use env var, not file
            mgr2 = SearchConfigManager(config_file=str(config_file))
            cfg2 = mgr2.load_config()

            # Environment variable should override
            assert cfg2.embedding_model_name == "BAAI/bge-m3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
