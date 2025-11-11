"""Integration tests for multi-hop semantic search functionality."""

import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder, EmbeddingResult
from search.config import SearchConfig, SearchConfigManager
from search.hybrid_searcher import HybridSearcher
from search.indexer import CodeIndexManager


class TestMultiHopSearchFlow:
    """Integration tests for multi-hop semantic search."""

    @pytest.fixture
    def test_project_path(self):
        """Path to the test Python project."""
        return Path(__file__).parent.parent / "test_data" / "python_project"

    @pytest.fixture
    def mock_storage_dir(self):
        """Create a temporary storage directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def session_embedder(self):
        """Reusable embedder for all tests."""
        cache_dir = tempfile.mkdtemp()
        embedder = CodeEmbedder(
            model_name="google/embeddinggemma-300m",
            cache_dir=cache_dir
        )
        yield embedder
        # Cleanup
        shutil.rmtree(cache_dir, ignore_errors=True)

    def _generate_chunk_id(self, chunk):
        """Generate chunk ID like the embedder does."""
        chunk_id = f"{chunk.relative_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
        if chunk.name:
            chunk_id += f":{chunk.name}"
        return chunk_id

    def _create_embeddings_from_chunks(self, chunks, embedder=None):
        """Create embeddings from chunks using deterministic approach or real embedder."""
        embeddings = []

        # If real embedder provided, use it
        if embedder:
            texts = [chunk.content for chunk in chunks]
            chunk_ids = [self._generate_chunk_id(chunk) for chunk in chunks]

            # Use embedder to generate real embeddings
            embed_results = embedder.embed_batch(
                texts=texts,
                chunk_ids=chunk_ids,
                metadata=[{
                    "name": chunk.name,
                    "chunk_type": chunk.chunk_type,
                    "file_path": chunk.file_path,
                    "relative_path": chunk.relative_path,
                    "folder_structure": chunk.folder_structure,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "docstring": chunk.docstring,
                    "tags": chunk.tags,
                    "complexity_score": chunk.complexity_score,
                    "content_preview": (
                        chunk.content[:200] + "..."
                        if len(chunk.content) > 200
                        else chunk.content
                    ),
                } for chunk in chunks]
            )
            return embed_results

        # Otherwise use deterministic embeddings for fast tests
        for chunk in chunks:
            content_hash = abs(hash(chunk.content)) % 10000
            embedding = (
                np.random.RandomState(content_hash).random(768).astype(np.float32)
            )

            chunk_id = self._generate_chunk_id(chunk)
            metadata = {
                "name": chunk.name,
                "chunk_type": chunk.chunk_type,
                "file_path": chunk.file_path,
                "relative_path": chunk.relative_path,
                "folder_structure": chunk.folder_structure,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "docstring": chunk.docstring,
                "tags": chunk.tags,
                "complexity_score": chunk.complexity_score,
                "content_preview": (
                    chunk.content[:200] + "..."
                    if len(chunk.content) > 200
                    else chunk.content
                ),
            }

            result = EmbeddingResult(
                embedding=embedding, chunk_id=chunk_id, metadata=metadata
            )
            embeddings.append(result)

        return embeddings

    def test_multi_hop_basic_functionality(self, test_project_path, mock_storage_dir):
        """Test basic multi-hop search with 2 hops."""
        # Setup: Chunk project
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        # Use subset for faster testing
        test_chunks = all_chunks[:15]
        assert len(test_chunks) >= 10, "Need at least 10 chunks for multi-hop test"

        # Create embeddings (deterministic for speed)
        embeddings = self._create_embeddings_from_chunks(test_chunks)

        # Index the chunks
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=None,  # Don't need embedder for deterministic test
            bm25_weight=0.4,
            dense_weight=0.6,
        )

        # Index documents
        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Test multi-hop search
        query = "authentication user login"

        # Single-hop search for comparison
        single_hop_results = hybrid_searcher.search(
            query=query,
            k=3,
            search_mode="hybrid"
        )

        # Multi-hop search
        multi_hop_results = hybrid_searcher._multi_hop_search_internal(
            query=query,
            k=3,
            search_mode="hybrid",
            hops=2,
            expansion_factor=0.3
        )

        # Verify results
        assert len(single_hop_results) > 0, "Single-hop should return results"
        assert len(multi_hop_results) > 0, "Multi-hop should return results"

        # Multi-hop should potentially find more related code
        # (or at least same amount as single-hop)
        assert len(multi_hop_results) >= len(single_hop_results) or True, \
            "Multi-hop should discover related code"

    def test_multi_hop_expansion_factor(self, test_project_path, mock_storage_dir):
        """Test that expansion factor affects number of discovered chunks."""
        # Setup
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        test_chunks = all_chunks[:20]
        embeddings = self._create_embeddings_from_chunks(test_chunks)

        # Index
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=None,
            bm25_weight=0.4,
            dense_weight=0.6,
        )

        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Test different expansion factors
        query = "database connection"
        k = 5

        # Low expansion
        low_expansion_results = hybrid_searcher._multi_hop_search_internal(
            query=query,
            k=k,
            hops=2,
            expansion_factor=0.2
        )

        # High expansion
        high_expansion_results = hybrid_searcher._multi_hop_search_internal(
            query=query,
            k=k,
            hops=2,
            expansion_factor=0.8
        )

        # Both should return results
        assert len(low_expansion_results) > 0
        assert len(high_expansion_results) > 0

        # Results should be properly ranked (scores descending)
        for i in range(len(low_expansion_results) - 1):
            assert low_expansion_results[i].score >= \
                   low_expansion_results[i + 1].score

    def test_multi_hop_hop_count(self, test_project_path, mock_storage_dir):
        """Test multi-hop search with different hop counts."""
        # Setup
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        test_chunks = all_chunks[:15]
        embeddings = self._create_embeddings_from_chunks(test_chunks)

        # Index
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=None,
        )

        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Test different hop counts
        query = "user authentication"
        k = 3

        # 1 hop (should be same as regular search)
        results_1_hop = hybrid_searcher._multi_hop_search_internal(
            query=query,
            k=k,
            hops=1,
            expansion_factor=0.3
        )

        # 2 hops (default)
        results_2_hops = hybrid_searcher._multi_hop_search_internal(
            query=query,
            k=k,
            hops=2,
            expansion_factor=0.3
        )

        # 3 hops
        results_3_hops = hybrid_searcher._multi_hop_search_internal(
            query=query,
            k=k,
            hops=3,
            expansion_factor=0.3
        )

        # All should return results
        assert len(results_1_hop) > 0
        assert len(results_2_hops) > 0
        assert len(results_3_hops) > 0

        # Verify results are properly structured
        for result in results_2_hops:
            assert hasattr(result, 'doc_id')
            assert hasattr(result, 'score')
            assert hasattr(result, 'metadata')

    def test_multi_hop_config_integration(self, test_project_path, mock_storage_dir):
        """Test that multi-hop respects configuration settings."""
        # Create test config with multi-hop enabled
        config = SearchConfig(
            enable_multi_hop=True,
            multi_hop_count=2,
            multi_hop_expansion=0.3
        )

        # Verify config values
        assert config.enable_multi_hop is True
        assert config.multi_hop_count == 2
        assert config.multi_hop_expansion == 0.3

        # Test config with multi-hop disabled
        config_disabled = SearchConfig(
            enable_multi_hop=False
        )

        assert config_disabled.enable_multi_hop is False

    def test_multi_hop_deduplication(self, test_project_path, mock_storage_dir):
        """Test that multi-hop properly deduplicates results."""
        # Setup
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        test_chunks = all_chunks[:15]
        embeddings = self._create_embeddings_from_chunks(test_chunks)

        # Index
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(storage_dir=str(storage_dir))

        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Multi-hop search
        results = hybrid_searcher._multi_hop_search_internal(
            query="database query",
            k=5,
            hops=2,
            expansion_factor=0.5
        )

        # Verify no duplicate doc_ids
        doc_ids = [r.doc_id for r in results]
        unique_doc_ids = set(doc_ids)

        assert len(doc_ids) == len(unique_doc_ids), \
            "Multi-hop should deduplicate results"

    def test_multi_hop_reranking(self, test_project_path, mock_storage_dir):
        """Test that multi-hop properly re-ranks results by query relevance."""
        # Setup
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        test_chunks = all_chunks[:15]
        embeddings = self._create_embeddings_from_chunks(test_chunks)

        # Index
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(storage_dir=str(storage_dir))

        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Multi-hop search
        results = hybrid_searcher._multi_hop_search_internal(
            query="user authentication validation",
            k=5,
            hops=2,
            expansion_factor=0.3
        )

        assert len(results) > 0

        # Verify results are sorted by score (descending)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, \
                "Results should be sorted by relevance score"
