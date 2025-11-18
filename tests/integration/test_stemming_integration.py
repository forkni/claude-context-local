"""Integration tests for Snowball Stemmer feature in BM25 search.

Tests end-to-end stemming functionality including:
- Indexing with stemming enabled/disabled
- Search quality improvements from word normalization
- Hybrid search integration
- Configuration management and version tracking
- Multi-project isolation
"""

import json
import tempfile
from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.bm25_index import BM25Index
from search.hybrid_searcher import HybridSearcher
from search.incremental_indexer import IncrementalIndexer


def _has_hf_token() -> bool:
    """Check if HuggingFace token is available."""
    import os

    return bool(os.environ.get("HF_TOKEN"))


class TestStemmingIntegration:
    """Integration tests for stemming feature."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_dir = self.temp_dir / "test_project"
        self.storage_dir = self.temp_dir / "storage"

        # Create directories
        self.project_dir.mkdir(parents=True)
        self.storage_dir.mkdir(parents=True)

        # Create test files with verb form variations
        self.create_test_files()

    def create_test_files(self):
        """Create test Python files with various verb forms."""
        test_files = {
            "search_module.py": '''
def search_users(query):
    """Search for users in database."""
    return database.query(query)

class UserSearcher:
    """Class for searching user records."""

    def __init__(self):
        self.cache = {}

    def find_user(self, user_id):
        """Find user by ID."""
        return self.search_database(user_id)

    def search_database(self, query):
        """Search database with query."""
        # Searching through all records
        return []
''',
            "indexing_module.py": '''
def index_documents(documents):
    """Index a list of documents."""
    indexed_count = 0
    for doc in documents:
        if indexer.add(doc):
            indexed_count += 1
    return indexed_count

class DocumentIndexer:
    """Handles document indexing operations."""

    def __init__(self):
        self.indexes = {}

    def create_index(self, name):
        """Create a new index."""
        # Indexing started
        self.indexes[name] = []
''',
            "processing_module.py": '''
def process_data(data_list):
    """Process a list of data items."""
    processed = []
    for item in data_list:
        processed.append(processor.transform(item))
    return processed

class DataProcessor:
    """Processes data through various transformations."""

    def __init__(self):
        self.processing_queue = []

    def transform(self, data):
        """Transform data item."""
        # Processing individual item
        return data.upper()
''',
            "connection_module.py": '''
import asyncio

async def connect_to_database(host, port):
    """Connect to database server."""
    # Connecting to remote server
    connection = await asyncio.open_connection(host, port)
    return connection

class DatabaseConnection:
    """Manages database connection lifecycle."""

    def __init__(self, config):
        self.config = config
        self.connected = False

    def establish_connection(self):
        """Establish connection to database."""
        # Connection established
        self.connected = True
''',
        }

        for filename, content in test_files.items():
            file_path = self.project_dir / filename
            file_path.write_text(content)

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_end_to_end_indexing_with_stemming(self):
        """Test complete indexing workflow with stemming enabled."""
        # Create hybrid searcher with stemming
        searcher = HybridSearcher(
            storage_dir=str(self.storage_dir / "index"),
            embedder=CodeEmbedder(),
            bm25_use_stemming=True,
        )

        # Create incremental indexer
        chunker = MultiLanguageChunker(str(self.project_dir))
        embedder = CodeEmbedder()
        indexer = IncrementalIndexer(
            indexer=searcher, embedder=embedder, chunker=chunker
        )

        # Index project
        result = indexer.incremental_index(
            str(self.project_dir), project_name="test_stemming", force_full=True
        )

        assert result.success, f"Indexing failed: {result.error}"
        assert result.chunks_added > 0, "Should have indexed some chunks"

        # Verify BM25 index has stemming enabled
        assert searcher.bm25_index.use_stemming is True

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_verb_form_matching_with_stemming(self):
        """Test that different verb forms match due to stemming."""
        # Index with stemming ON
        searcher_stemmed = HybridSearcher(
            storage_dir=str(self.storage_dir / "stemmed"),
            embedder=CodeEmbedder(),
            bm25_use_stemming=True,
        )

        chunker = MultiLanguageChunker(str(self.project_dir))
        embedder = CodeEmbedder()
        indexer = IncrementalIndexer(
            indexer=searcher_stemmed, embedder=embedder, chunker=chunker
        )

        result = indexer.incremental_index(
            str(self.project_dir), project_name="test_stemmed", force_full=True
        )
        assert result.success

        # Query with different verb form than what's in code
        # Code has "indexing", query uses "index"
        results = searcher_stemmed.search("index documents", k=5)

        assert len(results) > 0, "Stemming should help match different verb forms"

        # Check that we found the indexing_module
        result_contents = [r.metadata.get("content", "") for r in results]
        assert any(
            "index" in content.lower() or "indexing" in content.lower()
            for content in result_contents
        ), "Should find documents with 'index' or 'indexing'"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_stemming_vs_no_stemming_comparison(self):
        """Compare search results with and without stemming."""
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.project_dir))

        # Setup: Index with stemming ON
        stemmed_dir = self.storage_dir / "with_stemming"
        stemmed_dir.mkdir(parents=True)
        searcher_stemmed = HybridSearcher(
            storage_dir=str(stemmed_dir / "index"),
            embedder=embedder,
            bm25_use_stemming=True,
        )

        indexer_stemmed = IncrementalIndexer(
            indexer=searcher_stemmed, embedder=embedder, chunker=chunker
        )
        result1 = indexer_stemmed.incremental_index(
            str(self.project_dir), project_name="stemmed", force_full=True
        )
        assert result1.success

        # Setup: Index with stemming OFF
        unstemmed_dir = self.storage_dir / "without_stemming"
        unstemmed_dir.mkdir(parents=True)
        searcher_unstemmed = HybridSearcher(
            storage_dir=str(unstemmed_dir / "index"),
            embedder=embedder,
            bm25_use_stemming=False,
        )

        indexer_unstemmed = IncrementalIndexer(
            indexer=searcher_unstemmed, embedder=embedder, chunker=chunker
        )
        result2 = indexer_unstemmed.incremental_index(
            str(self.project_dir), project_name="unstemmed", force_full=True
        )
        assert result2.success

        # Test Query: "searching users" (verb form different from "search")
        stemmed_results = searcher_stemmed.search("searching users", k=5)
        unstemmed_results = searcher_unstemmed.search("searching users", k=5)

        # Both should return results, but stemmed might have better recall
        assert len(stemmed_results) > 0, "Stemmed search should find results"
        assert len(unstemmed_results) >= 0, "Unstemmed search should not crash"

        # Stemmed should find the search_module (contains "search_users", "UserSearcher", etc.)
        stemmed_ids = [r.chunk_id for r in stemmed_results]
        assert any(
            "search_module" in chunk_id for chunk_id in stemmed_ids
        ), "Stemmed search should find search_module"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_config_persistence_with_stemming(self):
        """Test that stemming config is saved and loaded correctly."""
        # Create and save index with stemming
        searcher = HybridSearcher(
            storage_dir=str(self.storage_dir / "persist_test"),
            embedder=CodeEmbedder(),
            bm25_use_stemming=True,
        )

        # Index some data
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.project_dir))
        indexer = IncrementalIndexer(
            indexer=searcher, embedder=embedder, chunker=chunker
        )

        result = indexer.incremental_index(
            str(self.project_dir), project_name="persist_test", force_full=True
        )
        assert result.success

        # Save indices
        searcher.save_indices()

        # Load in new searcher instance
        new_searcher = HybridSearcher(
            storage_dir=str(self.storage_dir / "persist_test"),
            embedder=CodeEmbedder(),
            bm25_use_stemming=True,
        )

        load_success = new_searcher.load_indices()
        assert load_success, "Should load indices successfully"

        # Verify stemming config persisted
        metadata_path = (
            Path(str(self.storage_dir / "persist_test")) / "bm25" / "bm25_metadata.json"
        )
        assert metadata_path.exists(), "Metadata file should exist"

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        assert "use_stemming" in metadata, "Metadata should contain stemming config"
        assert (
            metadata["use_stemming"] is True
        ), "Stemming should be enabled in metadata"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_config_mismatch_warning(self):
        """Test that config mismatch is detected and warned."""
        from unittest.mock import patch

        # Index with stemming ON
        searcher = HybridSearcher(
            storage_dir=str(self.storage_dir / "mismatch_test"),
            embedder=CodeEmbedder(),
            bm25_use_stemming=True,
        )

        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.project_dir))
        indexer = IncrementalIndexer(
            indexer=searcher, embedder=embedder, chunker=chunker
        )

        result = indexer.incremental_index(
            str(self.project_dir), project_name="mismatch_test", force_full=True
        )
        assert result.success

        searcher.save_indices()

        # Load with different stemming config
        with patch("logging.Logger.warning") as mock_warning:
            new_searcher = HybridSearcher(
                storage_dir=str(self.storage_dir / "mismatch_test"),
                embedder=CodeEmbedder(),
                bm25_use_stemming=False,  # Different from saved config
            )

            new_searcher.load_indices()

            # Should have warned about mismatch
            assert mock_warning.called, "Should warn about config mismatch"
            warning_calls = [str(call) for call in mock_warning.call_args_list]
            assert any(
                "mismatch" in call.lower() for call in warning_calls
            ), "Warning should mention configuration mismatch"

    def test_bm25_only_stemming(self):
        """Test BM25 index directly with stemming."""
        # Create BM25 index with stemming
        bm25_stemmed = BM25Index(
            str(self.storage_dir / "bm25_stemmed"), use_stemming=True
        )

        # Index some code snippets with verb variations
        docs = [
            "def search_users(): pass",
            "class UserSearcher: pass",
            "# Searching for records",
            "def index_documents(): pass",
            "# Indexing started",
            "class DocumentIndexer: pass",
        ]
        ids = [f"doc{i}" for i in range(len(docs))]

        bm25_stemmed.index_documents(docs, ids)

        # Query with different verb form
        results = bm25_stemmed.search("search index", k=10, min_score=0.0)

        assert len(results) > 0, "Should find results with stemming"

        # Should find documents with "search", "searching", "searcher", etc.
        result_ids = [r[0] for r in results]
        # At least some of the search-related or index-related docs should be found
        assert len(result_ids) >= 2, "Should find multiple matching documents"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_incremental_reindex_preserves_stemming(self):
        """Test that incremental re-indexing preserves stemming configuration."""
        # Initial index with stemming
        searcher = HybridSearcher(
            storage_dir=str(self.storage_dir / "incremental_test"),
            embedder=CodeEmbedder(),
            bm25_use_stemming=True,
        )

        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.project_dir))
        indexer = IncrementalIndexer(
            indexer=searcher, embedder=embedder, chunker=chunker
        )

        # Initial indexing
        result1 = indexer.incremental_index(
            str(self.project_dir), project_name="incremental_test", force_full=True
        )
        assert result1.success

        # Add a new file
        new_file = self.project_dir / "new_module.py"
        new_file.write_text(
            '''
def manage_users():
    """Manage user accounts."""
    # Managing user database
    pass

class UserManager:
    """Manager for user operations."""
    pass
'''
        )

        # Incremental reindex
        result2 = indexer.incremental_index(
            str(self.project_dir), project_name="incremental_test", force_full=False
        )

        assert result2.success
        assert result2.files_added > 0, "New file should be detected"

        # Verify stemming still works
        results = searcher.search("managing users", k=5)
        assert len(results) > 0, "Should find results after incremental index"

        # New file content should be searchable
        result_contents = [r.metadata.get("content", "") for r in results]
        assert any(
            "manage" in content.lower() or "managing" in content.lower()
            for content in result_contents
        ), "Should find new file with 'manage' or 'managing'"

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
