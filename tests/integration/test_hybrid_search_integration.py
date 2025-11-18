"""
Integration tests for hybrid search functionality.

These tests use real components (no mocks) to verify the complete
data flow through the hybrid search system.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest
from huggingface_hub import HfFolder

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.config import SearchConfigManager
from search.hybrid_searcher import HybridSearcher
from search.incremental_indexer import IncrementalIndexer


def _has_hf_token():
    """Check if HuggingFace token is available."""
    return HfFolder.get_token() is not None


class TestHybridSearchIntegration:
    """Integration tests for hybrid search system."""

    def setup_method(self):
        """Set up test environment with real components."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_dir = self.temp_dir / "test_project"
        self.storage_dir = self.temp_dir / "storage"

        # Create test project structure
        self.project_dir.mkdir(parents=True)
        self.storage_dir.mkdir(parents=True)

        # Create test files
        self.create_test_files()

        # Initialize components
        self.embedder = None
        self.chunker = None
        self.hybrid_searcher = None
        self.incremental_indexer = None

    def create_test_files(self):
        """Create test Python files for indexing."""
        test_files = {
            "calculator.py": '''
def add_numbers(a, b):
    """Add two numbers together."""
    return a + b

def multiply_numbers(a, b):
    """Multiply two numbers."""
    return a * b

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def calculate_sum(self, numbers):
        """Calculate sum of a list of numbers."""
        result = sum(numbers)
        self.history.append(f"sum({numbers}) = {result}")
        return result
''',
            "user_manager.py": '''
class UserManager:
    """Manages user operations."""

    def __init__(self):
        self.users = {}

    def get_user(self, user_id):
        """Retrieve user by ID."""
        return self.users.get(user_id)

    def authenticate_user(self, username, password):
        """Authenticate a user with username and password."""
        user = self.find_user_by_username(username)
        if user and user.check_password(password):
            return user
        return None

    def find_user_by_username(self, username):
        """Find user by username."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
''',
            "api_client.py": '''
import asyncio
from typing import Optional, Dict, Any

async def fetch_data(url: str, headers: Optional[Dict] = None) -> Dict[Any, Any]:
    """Fetch data from API endpoint."""
    # Simulate API call
    await asyncio.sleep(0.1)
    return {"status": "success", "data": {}}

def handle_api_error(error: Exception) -> Dict[str, Any]:
    """Handle API errors gracefully."""
    return {
        "error": str(error),
        "status": "failed",
        "retry": True
    }

class APIClient:
    """HTTP API client for external services."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None

    async def get(self, endpoint: str) -> Dict[Any, Any]:
        """GET request to API endpoint."""
        url = f"{self.base_url}{endpoint}"
        return await fetch_data(url)
''',
            "database.py": '''
import sqlite3
from typing import List, Dict, Any

class DatabaseConnection:
    """Database connection manager."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establish database connection."""
        self.connection = sqlite3.connect(self.db_path)
        return self.connection

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        cursor.execute(query, params)

        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))

        return results
''',
        }

        for filename, content in test_files.items():
            file_path = self.project_dir / filename
            file_path.write_text(content)

    def initialize_components(self):
        """Initialize all components for testing."""
        try:
            # Initialize embedder
            self.embedder = CodeEmbedder()

            # Initialize chunker
            self.chunker = MultiLanguageChunker(str(self.project_dir))

            # Initialize hybrid searcher
            self.hybrid_searcher = HybridSearcher(
                storage_dir=str(self.storage_dir), bm25_weight=0.4, dense_weight=0.6
            )

            # Initialize incremental indexer
            # This should work with HybridSearcher as indexer
            self.incremental_indexer = IncrementalIndexer(
                indexer=self.hybrid_searcher,
                embedder=self.embedder,
                chunker=self.chunker,
            )

        except Exception as e:
            pytest.skip(f"Could not initialize components: {e}")

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_hybrid_searcher_has_add_embeddings_method(self):
        """Test that HybridSearcher has add_embeddings method."""
        self.initialize_components()

        # This should not fail
        assert hasattr(
            self.hybrid_searcher, "add_embeddings"
        ), "HybridSearcher missing add_embeddings method required by incremental indexer"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_incremental_indexing_with_hybrid_search(self):
        """Test that incremental indexing works with hybrid search."""
        self.initialize_components()

        # Attempt to index the project
        try:
            result = self.incremental_indexer.incremental_index(
                str(self.project_dir), project_name="test_project", force_full=True
            )

            assert result.success, f"Indexing failed: {result.error}"
            assert result.chunks_added > 0, "No chunks were added to the index"

        except AttributeError as e:
            if "add_embeddings" in str(e):
                pytest.fail("HybridSearcher missing add_embeddings method")
            else:
                raise

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_hybrid_indices_are_populated(self):
        """Test that both BM25 and dense indices are populated after indexing."""
        self.initialize_components()

        # Index the project
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )

        assert result.success, "Indexing must succeed for this test"

        # Check that HybridSearcher is ready (both indices populated)
        assert (
            self.hybrid_searcher.is_ready
        ), "HybridSearcher should be ready after indexing (both BM25 and dense indices populated)"

        # Check BM25 index specifically
        assert (
            not self.hybrid_searcher.bm25_index.is_empty
        ), "BM25 index should not be empty after indexing"

        # Check dense index specifically
        assert (
            self.hybrid_searcher.dense_index.index is not None
        ), "Dense index should exist after indexing"
        assert (
            self.hybrid_searcher.dense_index.index.ntotal > 0
        ), "Dense index should contain vectors after indexing"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_hybrid_search_returns_results(self):
        """Test that hybrid search returns results from both indices."""
        self.initialize_components()

        # Index the project
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )
        assert result.success, "Indexing must succeed"

        # Test search queries that should favor different indices
        queries_to_test = [
            # Should favor BM25 (exact text matches)
            "def add_numbers",
            "UserManager",
            "sqlite3",
            # Should favor dense/semantic (conceptual matches)
            "database connection",
            "user authentication",
            "API client",
            "error handling",
            "calculate numbers",
        ]

        for query in queries_to_test:
            results = self.hybrid_searcher.search(query, k=5)
            assert len(results) > 0, f"No results found for query: '{query}'"

            # Check that results have the expected format
            for result in results:
                assert hasattr(result, "chunk_id"), "Result missing chunk_id"
                assert hasattr(result, "score"), "Result missing score"
                assert hasattr(result, "metadata"), "Result missing metadata"
                assert (
                    result.score > 0
                ), f"Result score should be positive: {result.score}"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_bm25_vs_dense_results_differ(self):
        """Test that BM25-only and dense-only searches return different results."""
        self.initialize_components()

        # Index the project
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )
        assert result.success, "Indexing must succeed"

        # Test a query that should show different results for BM25 vs dense
        query = "user authentication"

        # Get BM25-only results
        bm25_results = self.hybrid_searcher._search_bm25(query, k=5, min_score=0.0)

        # Get dense-only results
        dense_results = self.hybrid_searcher._search_dense(query, k=5, filters=None)

        # Both should return results
        assert len(bm25_results) > 0, "BM25 search should return results"
        assert len(dense_results) > 0, "Dense search should return results"

        # Extract doc IDs for comparison
        bm25_doc_ids = [doc_id for doc_id, _, _ in bm25_results]
        dense_doc_ids = [doc_id for doc_id, _, _ in dense_results]

        # The results should be different (different ranking/selection)
        # This tests that both indices are contributing to the search
        assert (
            bm25_doc_ids != dense_doc_ids
        ), "BM25 and dense search should return different results for semantic queries"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_hybrid_reranking_combines_results(self):
        """Test that hybrid reranking properly combines BM25 and dense results."""
        self.initialize_components()

        # Index the project
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )
        assert result.success, "Indexing must succeed"

        query = "calculate sum"

        # Get results from both searches
        bm25_results = self.hybrid_searcher._search_bm25(query, k=10, min_score=0.0)
        dense_results = self.hybrid_searcher._search_dense(query, k=10, filters=None)

        # Get hybrid results
        hybrid_results = self.hybrid_searcher.search(query, k=5, use_parallel=False)

        # Hybrid results should exist
        assert len(hybrid_results) > 0, "Hybrid search should return results"

        # Check that hybrid results contain documents from both searches
        hybrid_chunk_ids = {result.chunk_id for result in hybrid_results}
        bm25_chunk_ids = {doc_id for doc_id, _, _ in bm25_results}
        dense_chunk_ids = {doc_id for doc_id, _, _ in dense_results}

        # At least some hybrid results should come from BM25 or dense
        assert (
            len(hybrid_chunk_ids & bm25_chunk_ids) > 0
            or len(hybrid_chunk_ids & dense_chunk_ids) > 0
        ), "Hybrid results should include documents from BM25 or dense searches"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_parallel_vs_sequential_search(self):
        """Test that parallel and sequential search modes work and return similar results."""
        self.initialize_components()

        # Index the project
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )
        assert result.success, "Indexing must succeed"

        query = "database connection"

        # Get results with both modes
        parallel_results = self.hybrid_searcher.search(query, k=5, use_parallel=True)
        sequential_results = self.hybrid_searcher.search(query, k=5, use_parallel=False)

        # Both should return results
        assert len(parallel_results) > 0, "Parallel search should return results"
        assert len(sequential_results) > 0, "Sequential search should return results"

        # Results should be similar (same reranking algorithm)
        parallel_chunk_ids = [r.chunk_id for r in parallel_results]
        sequential_chunk_ids = [r.chunk_id for r in sequential_results]

        # Allow for some differences due to threading, but expect significant overlap
        overlap = len(set(parallel_chunk_ids) & set(sequential_chunk_ids))
        assert (
            overlap >= len(parallel_results) // 2
        ), "Parallel and sequential search should have significant overlap in results"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_index_persistence(self):
        """Test that hybrid indices persist across searcher instances."""
        self.initialize_components()

        # Index with first searcher instance
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )
        assert result.success, "Initial indexing must succeed"

        # Save indices
        self.hybrid_searcher.save_indices()

        # Create new searcher instance
        new_searcher = HybridSearcher(
            storage_dir=str(self.storage_dir), bm25_weight=0.4, dense_weight=0.6
        )

        # Load indices
        load_success = new_searcher.load_indices()
        assert load_success, "Loading indices should succeed"

        # Verify the new searcher is ready
        assert (
            new_searcher.is_ready
        ), "New searcher should be ready after loading indices"

        # Test that search works with loaded indices
        query = "calculate sum"
        results = new_searcher.search(query, k=3)
        assert len(results) > 0, "Search should work with loaded indices"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_incremental_updates(self):
        """Test that incremental updates work with hybrid search."""
        self.initialize_components()

        # Initial indexing
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )
        assert result.success, "Initial indexing must succeed"

        # Add a new file
        new_file = self.project_dir / "new_module.py"
        new_file.write_text(
            '''
def process_data(data_list):
    """Process a list of data items."""
    processed = []
    for item in data_list:
        if validate_item(item):
            processed.append(transform_item(item))
    return processed

def validate_item(item):
    """Validate a single data item."""
    return item is not None and len(str(item)) > 0
'''
        )

        # Incremental update
        update_result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=False
        )

        assert update_result.success, "Incremental update must succeed"
        assert update_result.files_added > 0, "New file should be detected"
        assert update_result.chunks_added > 0, "New chunks should be added"

        # Verify that new content is searchable
        results = self.hybrid_searcher.search("process data", k=3)
        assert len(results) > 0, "New content should be searchable"

        # Check that at least one result is from the new file
        new_file_results = [r for r in results if "new_module.py" in r.chunk_id]
        assert len(new_file_results) > 0, "Should find results from new file"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_search_mode_configuration(self):
        """Test search mode configuration and switching."""
        self.initialize_components()

        # Index the project
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )
        assert result.success, "Indexing must succeed"

        # Test weight adjustment
        original_bm25_weight = self.hybrid_searcher.bm25_weight
        original_dense_weight = self.hybrid_searcher.dense_weight

        # Change weights
        self.hybrid_searcher.bm25_weight = 0.8
        self.hybrid_searcher.dense_weight = 0.2

        # Search should still work
        results = self.hybrid_searcher.search("user authentication", k=3)
        assert len(results) > 0, "Search should work with different weights"

        # Restore weights
        self.hybrid_searcher.bm25_weight = original_bm25_weight
        self.hybrid_searcher.dense_weight = original_dense_weight

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_error_handling(self):
        """Test error handling in hybrid search system."""
        self.initialize_components()

        # Test search on empty index
        results = self.hybrid_searcher.search("test query", k=5)
        assert results == [], "Search on empty index should return empty results"

        # Test with invalid query
        results = self.hybrid_searcher.search("", k=5)
        assert isinstance(results, list), "Empty query should return list"

        # Test with zero k
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )
        assert result.success, "Indexing must succeed"

        results = self.hybrid_searcher.search("test", k=0)
        assert len(results) == 0, "k=0 should return no results"

    @pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_statistics_and_monitoring(self):
        """Test statistics collection and monitoring features."""
        self.initialize_components()

        # Index the project
        result = self.incremental_indexer.incremental_index(
            str(self.project_dir), project_name="test_project", force_full=True
        )
        assert result.success, "Indexing must succeed"

        # Get initial stats
        stats = self.hybrid_searcher.stats
        assert "bm25_stats" in stats, "Stats should include BM25 information"
        assert "dense_stats" in stats, "Stats should include dense information"
        assert "gpu_memory" in stats, "Stats should include GPU memory information"

        # Perform some searches to generate performance stats
        queries = ["calculate", "user", "database", "API"]
        for query in queries:
            self.hybrid_searcher.search(query, k=3)

        # Get search mode stats
        search_stats = self.hybrid_searcher.get_search_mode_stats()
        assert search_stats["total_searches"] == len(
            queries
        ), "Should track search count"
        assert "average_times" in search_stats, "Should include timing information"

    def teardown_method(self):
        """Clean up test environment."""
        try:
            if hasattr(self, "hybrid_searcher") and self.hybrid_searcher:
                self.hybrid_searcher.shutdown()
        except Exception:
            pass

        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass


class TestHybridSearchConfigIntegration:
    """Integration tests for hybrid search configuration."""

    def setup_method(self):
        """Set up configuration test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "search_config.json"

    def test_config_file_loading(self):
        """Test loading configuration from file."""
        # Create test config
        config_data = {
            "default_search_mode": "hybrid",
            "enable_hybrid_search": True,
            "bm25_weight": 0.3,
            "dense_weight": 0.7,
            "use_parallel_search": True,
        }

        with open(self.config_file, "w") as f:
            json.dump(config_data, f)

        # Load config
        config_manager = SearchConfigManager(str(self.config_file))
        config = config_manager.load_config()

        assert config.default_search_mode == "hybrid"
        assert config.enable_hybrid_search
        assert config.bm25_weight == 0.3
        assert config.dense_weight == 0.7
        assert config.use_parallel_search

    def test_hybrid_searcher_uses_config(self):
        """Test that HybridSearcher respects configuration."""
        # Create config with specific weights
        config_data = {
            "bm25_weight": 0.7,
            "dense_weight": 0.3,
            "rrf_k_parameter": 50,
            "use_parallel_search": False,
        }

        with open(self.config_file, "w") as f:
            json.dump(config_data, f)

        # Create searcher (should use config values)
        config_manager = SearchConfigManager(str(self.config_file))
        config = config_manager.load_config()

        searcher = HybridSearcher(
            storage_dir=str(self.temp_dir / "indices"),
            bm25_weight=config.bm25_weight,
            dense_weight=config.dense_weight,
            rrf_k=config.rrf_k_parameter,
        )

        assert searcher.bm25_weight == 0.7
        assert searcher.dense_weight == 0.3
        assert searcher.reranker.k == 50

    def teardown_method(self):
        """Clean up configuration test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
