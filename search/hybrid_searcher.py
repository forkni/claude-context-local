"""Hybrid search orchestrator combining BM25 + dense search with GPU awareness."""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import torch
except ImportError:
    torch = None

from utils.deprecation import deprecated

from .bm25_index import BM25Index
from .filters import FilterEngine
from .gpu_monitor import GPUMemoryMonitor
from .index_sync import IndexSynchronizer
from .indexer import CodeIndexManager
from .multi_hop_searcher import MultiHopSearcher
from .neural_reranker import NeuralReranker
from .reranker import RRFReranker, SearchResult
from .reranking_engine import RerankingEngine
from .result_factory import ResultFactory


# Helper function to access config via ServiceLocator (avoids circular imports)
def _get_config_via_service_locator():
    """Get SearchConfig via ServiceLocator to avoid circular dependencies."""
    from mcp_server.services import ServiceLocator

    return ServiceLocator.instance().get_config()


class HybridSearcher:
    """Orchestrates BM25 + dense search with GPU awareness and parallel execution."""

    def __init__(
        self,
        storage_dir: str,
        embedder=None,
        bm25_weight: float = 0.4,
        dense_weight: float = 0.6,
        rrf_k: int = 60,
        max_workers: int = 2,
        bm25_use_stopwords: bool = True,
        bm25_use_stemming: bool = True,
        project_id: str = None,
    ):
        """
        Initialize hybrid searcher.

        Args:
            storage_dir: Directory for storing indices
            embedder: CodeEmbedder instance for semantic search (optional)
            bm25_weight: Weight for BM25 results (0.0 to 1.0)
            dense_weight: Weight for dense vector results (0.0 to 1.0)
            rrf_k: RRF parameter for reranking
            max_workers: Maximum thread pool workers for parallel execution
            bm25_use_stopwords: Whether BM25 should filter stopwords
            bm25_use_stemming: Whether BM25 should use Snowball stemming
            project_id: Project identifier for graph storage
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Store embedder for semantic search
        self.embedder = embedder

        # Store project_id for graph storage
        self.project_id = project_id

        # Weights
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

        # BM25 configuration
        self.bm25_use_stopwords = bm25_use_stopwords
        self.bm25_use_stemming = bm25_use_stemming

        # Components - use existing storage structure
        self._logger = logging.getLogger(__name__)

        # BM25 index gets its own subdirectory
        self._logger.info(
            f"[INIT] Creating BM25Index at: {self.storage_dir / 'bm25'} "
            f"(stopwords={bm25_use_stopwords}, stemming={bm25_use_stemming})"
        )
        try:
            self.bm25_index = BM25Index(
                str(self.storage_dir / "bm25"),
                use_stopwords=bm25_use_stopwords,
                use_stemming=bm25_use_stemming,
            )
            self._logger.info("[INIT] BM25Index created successfully")
        except Exception as e:
            self._logger.error(f"[INIT] Failed to create BM25Index: {e}")
            raise

        # Try to load existing BM25 index
        self._logger.info(f"[INIT] BM25 storage path: {self.storage_dir / 'bm25'}")
        bm25_loaded = self.bm25_index.load()
        if bm25_loaded:
            self._logger.info(
                f"[INIT] Loaded existing BM25 index with {self.bm25_index.size} documents"
            )
        else:
            self._logger.info("[INIT] No existing BM25 index found, starting fresh")
            # Log what files we're looking for
            bm25_dir = self.storage_dir / "bm25"
            self._logger.debug(f"[INIT] BM25 directory exists: {bm25_dir.exists()}")
            if bm25_dir.exists():
                files = list(bm25_dir.iterdir())
                self._logger.debug(
                    f"[INIT] BM25 files found: {[f.name for f in files]}"
                )

        # Dense index uses the main storage directory where existing indices are stored
        self._logger.info(f"[INIT] Initializing dense index at: {self.storage_dir}")
        self.dense_index = CodeIndexManager(
            str(self.storage_dir), project_id=project_id
        )
        # Dense index loads automatically in its __init__
        dense_count = self.dense_index.index.ntotal if self.dense_index.index else 0
        if dense_count > 0:
            self._logger.info(
                f"[INIT] Loaded existing dense index with {dense_count} vectors"
            )
        else:
            self._logger.info("[INIT] No existing dense index found, starting fresh")

        # Log final initialization status
        total_bm25 = self.bm25_index.size
        self._logger.info(
            f"[INIT] HybridSearcher initialized - BM25: {total_bm25} docs, Dense: {dense_count} vectors"
        )
        self._logger.info(
            f"[INIT] Ready status: BM25={not self.bm25_index.is_empty}, Dense={dense_count > 0}, Overall={self.is_ready}"
        )

        # Check for index mismatch (early warning system)
        if isinstance(total_bm25, int) and isinstance(dense_count, int):
            if abs(total_bm25 - dense_count) > 10:
                self._logger.warning(
                    f"[INIT] INDEX MISMATCH DETECTED: BM25={total_bm25}, Dense={dense_count}. "
                    f"Consider re-indexing to synchronize indices."
                )

        self.reranker = RRFReranker(k=rrf_k)
        self.gpu_monitor = GPUMemoryMonitor()

        # Reranking engine (coordinates embedding-based and neural reranking)
        self.reranking_engine = RerankingEngine(
            embedder=embedder, metadata_store=self.dense_index.metadata_store
        )

        # Index synchronizer (manages index persistence and synchronization)
        self.index_sync = IndexSynchronizer(
            storage_dir=self.storage_dir,
            bm25_index=self.bm25_index,
            dense_index=self.dense_index,
            bm25_use_stopwords=bm25_use_stopwords,
            bm25_use_stemming=bm25_use_stemming,
            project_id=project_id,
        )

        # Multi-hop searcher (handles iterative search expansion)
        self.multi_hop_searcher = MultiHopSearcher(
            embedder=embedder,
            dense_index=self.dense_index,
            single_hop_callback=self._single_hop_search,
            rerank_callback=self._rerank_by_query,
            logger=self._logger,
        )

        # Threading
        self.max_workers = max_workers
        self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._shutdown_lock = threading.Lock()
        self._is_shutdown = False

        # Performance tracking
        self._search_stats = {
            "total_searches": 0,
            "bm25_time": 0.0,
            "dense_time": 0.0,
            "rerank_time": 0.0,
            "parallel_efficiency": 0.0,
        }

        # Dimension validation (safety check)
        self._validate_dimensions()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    @deprecated(
        replacement="self.reranking_engine.should_enable_neural_reranking()",
        version="0.7.0",
    )
    def _should_enable_neural_reranking(self) -> bool:
        """Check if VRAM is sufficient for neural reranking.

        .. deprecated::
            Use :meth:`reranking_engine.should_enable_neural_reranking` instead.
            This wrapper method may be removed in a future release.

        Delegates to reranking_engine for actual implementation.
        """
        return self.reranking_engine.should_enable_neural_reranking()

    def shutdown(self):
        """Shutdown the thread pool and cleanup resources."""
        with self._shutdown_lock:
            if not self._is_shutdown:
                self._thread_pool.shutdown(wait=True)
                # Cleanup reranking engine (which handles neural reranker cleanup)
                self.reranking_engine.shutdown()
                self._is_shutdown = True
                self._logger.info("HybridSearcher shut down")

    def _validate_dimensions(self):
        """Validate that index and embedder dimensions match."""
        if self.dense_index.index is not None and self.embedder is not None:
            try:
                index_dim = self.dense_index.index.d
                model_info = self.embedder.get_model_info()
                embedder_dim = model_info.get("embedding_dimension")

                if embedder_dim and index_dim != embedder_dim:
                    raise ValueError(
                        f"FATAL: Dimension mismatch between index ({index_dim}d) "
                        f"and embedder ({embedder_dim}d for {self.embedder.model_name}). "
                        f"This indicates a bug in model routing. "
                        f"The index was likely loaded for a different model."
                    )
            except (AttributeError, KeyError) as e:
                self._logger.debug(f"Could not validate dimensions: {e}")

    @property
    def is_ready(self) -> bool:
        """Check if both indices are ready."""
        bm25_ready = not self.bm25_index.is_empty
        dense_ready = (
            self.dense_index.index is not None and self.dense_index.index.ntotal > 0
        )

        self._logger.debug(
            f"[IS_READY] BM25 ready: {bm25_ready} (size: {self.bm25_index.size})"
        )
        self._logger.debug(
            f"[IS_READY] Dense ready: {dense_ready} (vectors: {self.dense_index.index.ntotal if self.dense_index.index else 0})"
        )

        is_ready = bm25_ready and dense_ready
        self._logger.debug(f"[IS_READY] Overall ready: {is_ready}")

        return is_ready

    @property
    def stats(self) -> Dict[str, Any]:
        """Get search performance statistics."""
        stats = self._search_stats.copy()

        # Add index stats
        stats.update(
            {
                "bm25_stats": self.bm25_index.get_stats(),
                "dense_stats": {
                    "total_vectors": (
                        self.dense_index.index.ntotal if self.dense_index.index else 0
                    ),
                    "on_gpu": self.dense_index.is_on_gpu,
                },
                "gpu_memory": self.gpu_monitor.get_available_memory(),
            }
        )

        return stats

    @property
    def index_synchronizer(self) -> IndexSynchronizer:
        """Access the index synchronizer for advanced index management.

        Returns:
            IndexSynchronizer instance managing BM25/dense index coordination.

        Note:
            For most use cases, use the delegated methods (save_indices,
            load_indices, etc.) which provide a simpler API. This property
            is for advanced users who need direct access to index sync functionality.

        Example:
            >>> searcher.index_synchronizer.validate_index_sync()
            >>> searcher.index_synchronizer.resync_bm25_from_dense()
        """
        return self.index_sync

    @property
    def neural_reranker(self) -> Optional[NeuralReranker]:
        """Access the neural reranker instance (backward compatibility).

        Returns:
            NeuralReranker instance from reranking_engine, or None if not initialized.

        Note:
            This property delegates to reranking_engine.neural_reranker.
            The neural reranker is lazily initialized when first needed.
        """
        return self.reranking_engine.neural_reranker

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics in the format expected by MCP server."""
        bm25_count = self.bm25_index.size
        dense_count = self.dense_index.index.ntotal if self.dense_index.index else 0
        total_chunks = max(bm25_count, dense_count)  # Use the higher count as total

        return {
            "total_chunks": total_chunks,
            "bm25_documents": bm25_count,
            "dense_vectors": dense_count,
            "synced": bm25_count == dense_count,
            "is_ready": self.is_ready,
            "bm25_ready": not self.bm25_index.is_empty,
            "dense_ready": dense_count > 0,
        }

    def get_index_size(self) -> int:
        """Get total index size (compatible with incremental indexer interface)."""
        bm25_count = self.bm25_index.size
        dense_count = self.dense_index.index.ntotal if self.dense_index.index else 0
        return max(bm25_count, dense_count)  # Return the higher count

    def get_by_chunk_id(self, chunk_id: str) -> Optional[SearchResult]:
        """
        Direct lookup by chunk_id (unambiguous, no search needed).

        Enables O(1) symbol lookups using chunk_id from previous results.

        Args:
            chunk_id: Format "file.py:10-20:function:name"

        Returns:
            SearchResult if found, None otherwise
        """
        # Get metadata from dense index
        metadata = self.dense_index.get_chunk_by_id(chunk_id)
        if not metadata:
            return None

        # Delegate to ResultFactory for SearchResult creation
        return ResultFactory.from_direct_lookup(chunk_id, metadata)

    def index_documents(
        self,
        documents: List[str],
        doc_ids: List[str],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Dict]] = None,
    ) -> None:
        """Index documents in both BM25 and dense indices."""
        if len(documents) != len(doc_ids) or len(documents) != len(embeddings):
            raise ValueError("All input lists must have the same length")

        self._logger.info(f"[INDEX_DOCUMENTS] Called with {len(documents)} documents")

        # Index in BM25 (CPU)
        self._logger.info("[BM25] Starting BM25 indexing...")
        start_time = time.time()
        bm25_size_before = self.bm25_index.size
        self._logger.info(f"[BM25] Before indexing - size: {bm25_size_before}")

        self.bm25_index.index_documents(documents, doc_ids, metadata)

        bm25_time = time.time() - start_time
        bm25_size_after = self.bm25_index.size
        self._logger.info(f"[BM25] After indexing - size: {bm25_size_after}")

        self._logger.debug(
            f"[BM25] Indexing completed: {bm25_size_before} -> {bm25_size_after} documents ({bm25_time:.2f}s)"
        )
        self._logger.debug(f"[BM25] Index directory: {self.bm25_index.storage_dir}")
        self._logger.debug(
            f"[BM25] Index files will be saved as: {[str(p) for p in [self.bm25_index.index_path, self.bm25_index.docs_path, self.bm25_index.metadata_path]]}"
        )

        # Verify BM25 indexing worked
        if bm25_size_after == bm25_size_before:
            self._logger.error("[BM25] ERROR: No documents were indexed!")
            self._logger.debug(f"[BM25] Documents provided: {len(documents)}")
            self._logger.debug(
                f"[BM25] First document: {documents[0][:200] if documents else 'EMPTY'}"
            )

        # Index in dense (potentially GPU)
        start_time = time.time()
        # Convert embeddings to EmbeddingResult format
        import numpy as np

        from embeddings.embedder import EmbeddingResult

        embedding_results = []
        for _i, (chunk_id, embedding) in enumerate(
            zip(doc_ids, embeddings, strict=False)
        ):
            result = EmbeddingResult(
                embedding=np.array(embedding, dtype=np.float32),
                chunk_id=chunk_id,
                metadata=metadata.get(chunk_id, {}) if metadata else {},
            )
            embedding_results.append(result)

        self.dense_index.add_embeddings(embedding_results)
        dense_time = time.time() - start_time

        self._logger.info(
            f"Hybrid indexing complete: BM25 {bm25_time:.2f}s, Dense {dense_time:.2f}s"
        )

    def search(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search using configurable approach (hybrid, semantic-only, or BM25-only).

        Automatically uses multi-hop search if enabled in config, discovering
        interconnected code relationships beyond direct matches.

        Args:
            query: Search query
            k: Number of results to return
            search_mode: Search mode - "hybrid", "semantic", or "bm25"
            use_parallel: Whether to run BM25 and dense search in parallel (hybrid mode only)
            min_bm25_score: Minimum BM25 score threshold
            filters: Optional filters for dense search

        Returns:
            Search results (reranked for hybrid mode, direct for single modes)
        """
        # Check if indices are ready based on search mode
        if search_mode == "bm25":
            if self.bm25_index.is_empty:
                self._logger.warning("BM25 search requested but BM25 index is empty")
                return []
        elif search_mode == "semantic":
            if not self.dense_index.index or self.dense_index.index.ntotal == 0:
                self._logger.warning(
                    "Semantic search requested but dense index is empty"
                )
                return []
        else:  # hybrid
            if not self.is_ready:
                self._logger.warning("Hybrid search not ready - indices may be empty")
                return []

        # Check if multi-hop search is enabled
        # Use ServiceLocator helper instead of inline import
        config = _get_config_via_service_locator()

        if config.multi_hop.enabled:
            # Use multi-hop search for discovering related code
            return self.multi_hop_searcher.search(
                query=query,
                k=k,
                search_mode=search_mode,
                hops=config.multi_hop.hop_count,
                expansion_factor=config.multi_hop.expansion,
                use_parallel=use_parallel,
                min_bm25_score=min_bm25_score,
                filters=filters,
            )

        # Single-hop search (direct matching only)
        return self._single_hop_search(
            query=query,
            k=k,
            search_mode=search_mode,
            use_parallel=use_parallel,
            min_bm25_score=min_bm25_score,
            filters=filters,
        )

    def _single_hop_search(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
        query_embedding: Optional[np.ndarray] = None,
    ) -> List[SearchResult]:
        """
        Internal single-hop search implementation (direct query matching).

        Args:
            query: Search query
            k: Number of results to return
            search_mode: Search mode - "hybrid", "semantic", or "bm25"
            use_parallel: Whether to run BM25 and dense search in parallel
            min_bm25_score: Minimum BM25 score threshold
            filters: Optional filters for dense search
            query_embedding: Pre-computed query embedding (optional, for caching)

        Returns:
            Search results from single-hop search
        """
        self._logger.debug(f"{search_mode.title()} search for: '{query}' (k={k})")

        start_time = time.time()

        # Handle different search modes
        if search_mode == "bm25":
            # BM25-only search
            bm25_results = self._search_bm25(query, k, min_bm25_score)
            # Convert BM25 results to SearchResult format
            final_results = self._convert_bm25_to_search_results(bm25_results)
            rerank_time = 0.0  # No reranking for single mode

        elif search_mode == "semantic":
            # Dense-only search
            dense_results = self._search_dense(query, k, filters, query_embedding)
            # Convert dense results to SearchResult format
            final_results = self._convert_dense_to_search_results(dense_results)
            rerank_time = 0.0  # No reranking for single mode

        else:  # hybrid mode
            search_k = k * 2  # Get more results for better reranking

            if use_parallel and not self._is_shutdown:
                # Parallel execution
                bm25_results, dense_results = self._parallel_search(
                    query, search_k, min_bm25_score, filters, query_embedding
                )
            else:
                # Sequential execution
                bm25_results, dense_results = self._sequential_search(
                    query, search_k, min_bm25_score, filters, query_embedding
                )

            # Rerank results
            rerank_start = time.time()
            self._logger.debug(
                f"[RERANK] Using weights: BM25={self.bm25_weight}, Dense={self.dense_weight}, "
                f"BM25_results={len(bm25_results)}, Dense_results={len(dense_results)}"
            )
            final_results = self.reranker.rerank_simple(
                bm25_results=bm25_results,
                dense_results=dense_results,
                max_results=k,
                bm25_weight=self.bm25_weight,
                dense_weight=self.dense_weight,
            )
            rerank_time = time.time() - rerank_start
            self._logger.debug(
                f"[RERANK] Produced {len(final_results)} results in {rerank_time:.3f}s"
            )

            # Neural reranking (Quality First mode) - delegate to reranking_engine
            if len(final_results) > 0:
                final_results = self.reranking_engine.apply_neural_reranking(
                    query, final_results, k, context="search"
                )

        # Update statistics
        total_time = time.time() - start_time
        self._search_stats["total_searches"] += 1
        self._search_stats["rerank_time"] += rerank_time

        if use_parallel:
            parallel_time = max(
                self._search_stats.get("last_bm25_time", 0),
                self._search_stats.get("last_dense_time", 0),
            )
            sequential_time = self._search_stats.get(
                "last_bm25_time", 0
            ) + self._search_stats.get("last_dense_time", 0)
            if sequential_time > 0:
                efficiency = 1.0 - (parallel_time / sequential_time)
                self._search_stats["parallel_efficiency"] = efficiency

        # Mode-specific logging
        if search_mode == "bm25":
            self._logger.debug(
                f"BM25 search complete: {len(final_results)} results, "
                f"Total time: {total_time:.3f}s"
            )
        elif search_mode == "semantic":
            self._logger.debug(
                f"Semantic search complete: {len(final_results)} results, "
                f"Total time: {total_time:.3f}s"
            )
        else:  # hybrid
            self._logger.debug(
                f"Hybrid search complete: {len(final_results)} results, "
                f"BM25: {len(bm25_results)}, Dense: {len(dense_results)}, "
                f"Total time: {total_time:.3f}s"
            )

        return final_results

    def find_similar_to_chunk(
        self, chunk_id: str, k: int = 5, rerank: bool = False
    ) -> List:
        """
        Find chunks similar to a given chunk using dense semantic search.

        Args:
            chunk_id: The ID of the reference chunk
            k: Number of similar chunks to return
            rerank: Whether to apply neural reranking (default: False)

        Returns:
            List of SearchResult objects with similar chunks
        """
        # Fetch more candidates when reranking to improve quality
        fetch_k = k * 2 if rerank else k
        similar_chunks = self.dense_index.get_similar_chunks(chunk_id, fetch_k)

        # Convert to SearchResult format expected by MCP tool
        # Import here to avoid circular dependency
        from .searcher import SearchResult

        results = []
        for cid, similarity, metadata in similar_chunks:
            result = SearchResult(
                chunk_id=cid,
                similarity_score=similarity,
                content_preview=metadata.get("content_preview", ""),
                file_path=metadata.get("file_path", ""),
                relative_path=metadata.get("relative_path", ""),
                folder_structure=metadata.get("folder_structure", []),
                chunk_type=metadata.get("chunk_type", "unknown"),
                name=metadata.get("name"),
                parent_name=metadata.get("parent_name"),
                start_line=metadata.get("start_line", 0),
                end_line=metadata.get("end_line", 0),
                docstring=metadata.get("docstring"),
                tags=metadata.get("tags", []),
                context_info={},
                metadata={"content_preview": metadata.get("content_preview", "")},
            )
            results.append(result)

        # Apply neural reranking if requested and available
        if rerank and len(results) > 0:
            # Get reference chunk content to use as "query" for reranking
            ref_metadata = self.dense_index.get_chunk_by_id(chunk_id)
            query_content = (
                ref_metadata.get("content_preview", "") if ref_metadata else ""
            )

            if query_content:
                self._logger.debug(
                    f"[RERANK-SIMILAR] Reranking {len(results)} candidates "
                    f"using reference chunk as query (length: {len(query_content)} chars)"
                )
                # Delegate to reranking_engine for lifecycle + reranking
                results = self.reranking_engine.apply_neural_reranking(
                    query_content, results, k, context="similarity"
                )
            else:
                self._logger.warning(
                    f"[RERANK-SIMILAR] No content found for reference chunk {chunk_id}, "
                    "skipping reranking"
                )

        return results[:k]

    @deprecated(replacement="self.multi_hop_searcher.search()", version="0.7.0")
    def _multi_hop_search_internal(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        hops: int = 2,
        expansion_factor: float = 0.3,
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List:
        """
        Internal multi-hop search implementation.

        .. deprecated::
            Use :meth:`multi_hop_searcher.search` instead.
            This wrapper method may be removed in a future release.

        Delegates to multi_hop_searcher for actual implementation.

        Args:
            query: Search query
            k: Number of final results to return
            search_mode: Search mode - "hybrid", "semantic", or "bm25"
            hops: Number of search hops (default: 2)
            expansion_factor: Fraction of k to expand per hop (default: 0.3)
            use_parallel: Whether to use parallel search
            min_bm25_score: Minimum BM25 score threshold
            filters: Optional filters for search

        Returns:
            List of SearchResult objects with discovered related code
        """
        return self.multi_hop_searcher.search(
            query=query,
            k=k,
            search_mode=search_mode,
            hops=hops,
            expansion_factor=expansion_factor,
            use_parallel=use_parallel,
            min_bm25_score=min_bm25_score,
            filters=filters,
        )

    @deprecated(replacement="self.reranking_engine.rerank_by_query()", version="0.7.0")
    def _rerank_by_query(
        self,
        query: str,
        results: List,
        k: int,
        search_mode: str = "hybrid",
        query_embedding: Optional[np.ndarray] = None,
    ) -> List:
        """
        Re-rank results by computing fresh relevance scores against the original query.

        .. deprecated::
            Use :meth:`reranking_engine.rerank_by_query` instead.
            This wrapper method may be removed in a future release.

        Delegates to reranking_engine for actual implementation.

        Args:
            query: Original search query
            results: List of SearchResult objects to re-rank
            k: Number of top results to return
            search_mode: Search mode for re-ranking strategy
            query_embedding: Pre-computed query embedding (optional)

        Returns:
            Top k results sorted by query relevance
        """
        # Delegate to reranking_engine (neural_reranker access via property)
        return self.reranking_engine.rerank_by_query(
            query, results, k, search_mode, query_embedding
        )

    def _parallel_search(
        self,
        query: str,
        k: int,
        min_bm25_score: float,
        filters: Optional[Dict[str, Any]],
        query_embedding: Optional[np.ndarray] = None,
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """Execute BM25 and dense search in parallel using shared thread pool."""
        try:
            # Reuse existing thread pool instead of creating new one per search
            # This avoids ~1-2ms overhead of ThreadPoolExecutor creation
            bm25_future = self._thread_pool.submit(
                self._search_bm25, query, k, min_bm25_score, filters
            )
            dense_future = self._thread_pool.submit(
                self._search_dense, query, k, filters, query_embedding
            )

            # Wait for results with timeout to prevent deadlocks
            bm25_results = bm25_future.result(timeout=30.0)
            dense_results = dense_future.result(timeout=30.0)

            return bm25_results, dense_results

        except Exception as e:
            self._logger.warning(
                f"Parallel search failed, falling back to sequential: {e}"
            )
            return self._sequential_search(query, k, min_bm25_score, filters)

    def _sequential_search(
        self,
        query: str,
        k: int,
        min_bm25_score: float,
        filters: Optional[Dict[str, Any]],
        query_embedding: Optional[np.ndarray] = None,
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """Execute BM25 and dense search sequentially."""
        bm25_results = self._search_bm25(query, k, min_bm25_score, filters)
        dense_results = self._search_dense(query, k, filters, query_embedding)
        return bm25_results, dense_results

    def _search_bm25(
        self, query: str, k: int, min_score: float, filters: Optional[Dict] = None
    ) -> List[Tuple]:
        """Search using BM25 index with optional filtering."""
        start_time = time.time()
        try:
            # Get more results if filtering, to ensure enough after filter
            # Use higher multiplier for directory filters (can exclude 50%+ of results)
            if filters and ("include_dirs" in filters or "exclude_dirs" in filters):
                search_k = k * 5
            elif filters:
                search_k = k * 3
            else:
                search_k = k
            results = self.bm25_index.search(query, search_k, min_score)

            # Apply filters post-search
            if filters and results:
                filtered_results = []
                for result in results:
                    # BM25 results are (chunk_id, score, metadata)
                    if len(result) >= 3:
                        _chunk_id, _score, metadata = result[0], result[1], result[2]
                    else:
                        # Skip malformed results
                        continue

                    if FilterEngine.from_dict(filters).matches(metadata):
                        filtered_results.append(result)
                        if len(filtered_results) >= k:
                            break
                results = filtered_results
            else:
                results = results[:k]

            search_time = time.time() - start_time

            self._search_stats["bm25_time"] += search_time
            self._search_stats["last_bm25_time"] = search_time

            self._logger.debug(
                f"BM25 search: {len(results)} results in {search_time:.3f}s"
            )
            return results

        except Exception as e:
            self._logger.error(f"BM25 search failed: {e}")
            return []

    @deprecated(
        replacement="FilterEngine.from_dict(filters).matches(metadata)", version="0.7.0"
    )
    def _matches_bm25_filters(self, metadata: Dict, filters: Dict) -> bool:
        """Check if BM25 result metadata matches filters.

        .. deprecated::
            Use :meth:`FilterEngine.from_dict(filters).matches(metadata)` instead.
            This wrapper method may be removed in a future release.

        Uses FilterEngine for unified filter logic across the codebase.
        """
        return FilterEngine.from_dict(filters).matches(metadata)

    def _search_dense(
        self,
        query: str,
        k: int,
        filters: Optional[Dict],
        query_embedding: Optional[np.ndarray] = None,
    ) -> List[Tuple]:
        """Search using dense vector index."""
        start_time = time.time()
        try:
            # Only compute embedding if not provided (caching optimization)
            if query_embedding is None:
                # Use stored embedder or create one if not provided
                if self.embedder is None:
                    self._logger.warning(
                        "No embedder provided to HybridSearcher, creating new instance"
                    )
                    from pathlib import Path

                    from embeddings.embedder import CodeEmbedder

                    # Use same cache directory as main embedder
                    cache_dir = Path.home() / ".claude_code_search" / "models"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    self.embedder = CodeEmbedder(cache_dir=str(cache_dir))
                    self._logger.info(
                        "Created new CodeEmbedder instance for semantic search"
                    )

                query_embedding = self.embedder.embed_query(query)

            # Search in dense index
            results = self.dense_index.search(query_embedding, k, filters)

            search_time = time.time() - start_time
            self._search_stats["dense_time"] += search_time
            self._search_stats["last_dense_time"] = search_time

            self._logger.debug(
                f"Dense search: {len(results)} results in {search_time:.3f}s"
            )
            return results

        except Exception as e:
            self._logger.error(f"Dense search failed: {e}")
            import traceback

            self._logger.error(
                f"Dense search exception details: {traceback.format_exc()}"
            )
            return []

    @deprecated(
        replacement="ResultFactory.from_bm25_results()",
        version="0.7.0",
    )
    def _convert_bm25_to_search_results(
        self, bm25_results: List[Tuple]
    ) -> List[SearchResult]:
        """Convert BM25 search results to SearchResult format.

        .. deprecated::
            Use :meth:`ResultFactory.from_bm25_results` instead.
            This wrapper method may be removed in a future release.
        """
        return ResultFactory.from_bm25_results(bm25_results)

    @deprecated(
        replacement="ResultFactory.from_dense_results()",
        version="0.7.0",
    )
    def _convert_dense_to_search_results(
        self, dense_results: List[Tuple]
    ) -> List[SearchResult]:
        """Convert dense search results to SearchResult format.

        .. deprecated::
            Use :meth:`ResultFactory.from_dense_results` instead.
            This wrapper method may be removed in a future release.
        """
        return ResultFactory.from_dense_results(dense_results)

    def get_search_mode_stats(self) -> Dict[str, Any]:
        """Get statistics about search mode performance."""
        total_searches = self._search_stats["total_searches"]
        if total_searches == 0:
            return {"message": "No searches performed yet"}

        avg_bm25_time = self._search_stats["bm25_time"] / total_searches
        avg_dense_time = self._search_stats["dense_time"] / total_searches
        avg_rerank_time = self._search_stats["rerank_time"] / total_searches

        return {
            "total_searches": total_searches,
            "average_times": {
                "bm25": avg_bm25_time,
                "dense": avg_dense_time,
                "reranking": avg_rerank_time,
                "total": avg_bm25_time + avg_dense_time + avg_rerank_time,
            },
            "parallel_efficiency": self._search_stats.get("parallel_efficiency", 0.0),
            "gpu_utilization": self.gpu_monitor.get_available_memory(),
            "search_distribution": {
                "bm25_contribution": self.bm25_weight,
                "dense_contribution": self.dense_weight,
            },
        }

    def optimize_weights(
        self, test_queries: List[str], ground_truth: Optional[List[List[str]]] = None
    ) -> Dict[str, float]:
        """
        Optimize BM25/dense weights based on test queries.

        Args:
            test_queries: List of test queries
            ground_truth: Optional ground truth results for each query

        Returns:
            Optimized weights
        """
        self._logger.info(f"Optimizing weights with {len(test_queries)} test queries")

        weight_combinations = [
            (0.2, 0.8),
            (0.3, 0.7),
            (0.4, 0.6),
            (0.5, 0.5),
            (0.6, 0.4),
            (0.7, 0.3),
            (0.8, 0.2),
        ]

        best_weights = (self.bm25_weight, self.dense_weight)
        best_score = 0.0

        for bm25_w, dense_w in weight_combinations:
            # Temporarily set weights
            orig_bm25_w, orig_dense_w = self.bm25_weight, self.dense_weight
            self.bm25_weight, self.dense_weight = bm25_w, dense_w

            total_score = 0.0
            for _i, query in enumerate(test_queries):
                results = self.search(query, k=10, use_parallel=False)

                # Score based on result quality metrics
                if results:
                    analysis = self.reranker.analyze_fusion_quality(results)
                    score = (
                        analysis["diversity_score"] * 0.4
                        + analysis["coverage_balance"] * 0.3
                        + analysis["high_quality_ratio"] * 0.3
                    )
                    total_score += score

            avg_score = total_score / len(test_queries) if test_queries else 0.0

            if avg_score > best_score:
                best_score = avg_score
                best_weights = (bm25_w, dense_w)

            # Restore original weights
            self.bm25_weight, self.dense_weight = orig_bm25_w, orig_dense_w

        # Set optimal weights
        self.bm25_weight, self.dense_weight = best_weights

        self._logger.info(
            f"Optimized weights: BM25={self.bm25_weight:.2f}, "
            f"Dense={self.dense_weight:.2f} (score: {best_score:.3f})"
        )

        return {
            "bm25_weight": self.bm25_weight,
            "dense_weight": self.dense_weight,
            "optimization_score": best_score,
            "tested_combinations": len(weight_combinations),
        }

    def save_indices(self) -> None:
        """Save both BM25 and dense indices. Delegates to IndexSynchronizer."""
        self.index_sync.save_indices()
        # Return value ignored for backward compatibility (was None)

    def validate_index_sync(self) -> bool:
        """Validate BM25 and Dense indices are synchronized. Delegates to IndexSynchronizer."""
        return self.index_sync.validate_index_sync()

    def resync_bm25_from_dense(self) -> int:
        """Rebuild BM25 index from dense index metadata. Delegates to IndexSynchronizer."""
        count = self.index_sync.resync_bm25_from_dense()
        # Sync modified bm25_index reference back
        self.bm25_index = self.index_sync.bm25_index
        return count

    def load_indices(self) -> bool:
        """Load both BM25 and dense indices. Delegates to IndexSynchronizer."""
        return self.index_sync.load_indices()

    def add_embeddings(self, embedding_results) -> None:
        """
        Add embeddings to both BM25 and dense indices.
        Compatible with incremental indexer interface.

        Args:
            embedding_results: List of EmbeddingResult objects
        """
        if not embedding_results:
            self._logger.debug("[ADD_EMBEDDINGS] No embedding results provided")
            return

        self._logger.info(
            f"[ADD_EMBEDDINGS] Called with {len(embedding_results)} results"
        )
        self._logger.debug(f"[ADD_EMBEDDINGS] Storage directory: {self.storage_dir}")
        self._logger.debug(
            f"[ADD_EMBEDDINGS] BM25 index path: {self.storage_dir / 'bm25'}"
        )
        self._logger.debug(f"[ADD_EMBEDDINGS] Dense index path: {self.storage_dir}")

        # Extract data for both indices
        documents = []
        doc_ids = []
        embeddings = []
        metadata = {}

        for result in embedding_results:
            chunk_id = result.chunk_id
            doc_ids.append(chunk_id)

            # Extract text content for BM25 (from metadata or content)
            content = result.metadata.get("content", "")
            if not content:
                # Fallback: try other content fields
                content = (
                    result.metadata.get("content_preview", "")
                    or result.metadata.get("raw_content", "")
                    or ""
                )
            documents.append(content)

            # Embeddings for dense index
            if hasattr(result.embedding, "tolist"):
                embeddings.append(result.embedding.tolist())
            else:
                embeddings.append(list(result.embedding))

            # Metadata for both indices
            metadata[chunk_id] = result.metadata

        # Log data extraction
        self._logger.debug(f"[ADD_EMBEDDINGS] Extracted {len(documents)} documents")
        self._logger.debug(
            f"[ADD_EMBEDDINGS] First doc sample: {documents[0][:100] if documents else 'EMPTY'}..."
        )

        # Index in both systems using existing method
        try:
            # Log before calling index_documents
            self._logger.info(
                f"[ADD_EMBEDDINGS] Calling index_documents with {len(documents)} docs"
            )

            self.index_documents(documents, doc_ids, embeddings, metadata)

            self._logger.info(
                f"[ADD_EMBEDDINGS] Successfully added {len(embedding_results)} embeddings to hybrid index"
            )
            self._logger.debug(
                f"[ADD_EMBEDDINGS] BM25 index size after adding: {self.bm25_index.size}"
            )
            self._logger.debug(
                f"[ADD_EMBEDDINGS] Dense index size after adding: {self.dense_index.index.ntotal if self.dense_index.index else 0}"
            )

        except Exception as e:
            self._logger.error(
                f"[ADD_EMBEDDINGS] Failed to add embeddings to hybrid index: {e}"
            )
            raise

    def clear_index(self) -> None:
        """Clear both BM25 and dense indices. Delegates to IndexSynchronizer."""
        self.index_sync.clear_index()
        # Sync modified index references back
        self.bm25_index = self.index_sync.bm25_index
        self.dense_index = self.index_sync.dense_index
        # Update reranking_engine's metadata_store reference
        self.reranking_engine.metadata_store = self.dense_index.metadata_store

    def remove_file_chunks(self, file_path: str, project_name: str) -> int:
        """Remove chunks for a specific file from both indices. Delegates to IndexSynchronizer."""
        return self.index_sync.remove_file_chunks(file_path, project_name)

    def remove_multiple_files(self, file_paths: set, project_name: str) -> int:
        """Remove chunks for multiple files from both indices. Delegates to IndexSynchronizer."""
        return self.index_sync.remove_multiple_files(file_paths, project_name)

    @deprecated(replacement="self.save_indices()", version="0.7.0")
    def save_index(self) -> None:
        """Save both BM25 and dense indices to disk.

        .. deprecated::
            Use :meth:`save_indices` instead (note the plural form).
            This method may be removed in a future release.

        Delegates to IndexSynchronizer.
        """
        self.index_sync.save_indices()

    def _verify_bm25_files(self):
        """Verify BM25 files exist and are non-empty. Delegates to IndexSynchronizer."""
        self.index_sync._verify_bm25_files()
