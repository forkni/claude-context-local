"""Hybrid search orchestrator combining BM25 + dense search with GPU awareness."""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np

if TYPE_CHECKING:
    from .config import SearchConfig

try:
    import torch
except ImportError:
    torch = None

from graph.graph_storage import CodeGraphStorage

from .bm25_index import BM25Index
from .ego_graph_retriever import EgoGraphRetriever
from .gpu_monitor import GPUMemoryMonitor
from .index_sync import IndexSynchronizer
from .indexer import CodeIndexManager
from .multi_hop_searcher import MultiHopSearcher
from .neural_reranker import NeuralReranker
from .reranker import RRFReranker, SearchResult
from .reranking_engine import RerankingEngine
from .result_factory import ResultFactory
from .search_executor import SearchExecutor
from .weight_optimizer import WeightOptimizer


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
        config=None,
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
            config: SearchConfig instance for mmap storage and other settings
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Store embedder for semantic search
        self.embedder = embedder

        # Store project_id for graph storage
        self.project_id = project_id

        # Store config for index synchronizer
        self.config = config

        # Weights
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

        # BM25 configuration
        self.bm25_use_stopwords = bm25_use_stopwords
        self.bm25_use_stemming = bm25_use_stemming

        # Components - use existing storage structure
        self._logger = logging.getLogger(__name__)

        # In-memory metadata cache for multi-hop operations (find_connections)
        # Avoids repeated SQLite lookups during graph traversal
        self._metadata_cache: Dict[str, Optional[SearchResult]] = {}
        self._cache_max_size = 1000  # Limit cache size to prevent memory bloat
        self._cache_hits = 0
        self._cache_misses = 0

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

        # Dense index uses the main storage directory where existing indices are stored
        self._logger.info(f"[INIT] Initializing dense index at: {self.storage_dir}")
        self.dense_index = CodeIndexManager(
            str(self.storage_dir),
            embedder=embedder,
            project_id=project_id,
            config=config,
        )

        # Load both indices in parallel for faster startup
        self._logger.info(f"[INIT] BM25 storage path: {self.storage_dir / 'bm25'}")
        bm25_loaded, dense_count = self._load_indices_parallel()

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
            config=self.config,
            embedder=embedder,
        )

        # Search executor (handles core search execution logic)
        self.search_executor = SearchExecutor(
            bm25_index=self.bm25_index,
            dense_index=self.dense_index,
            embedder=embedder,
            reranker=self.reranker,
            reranking_engine=self.reranking_engine,
            gpu_monitor=self.gpu_monitor,
            bm25_weight=bm25_weight,
            dense_weight=dense_weight,
            max_workers=max_workers,
            logger=self._logger,
        )

        # Multi-hop searcher (handles iterative search expansion)
        self.multi_hop_searcher = MultiHopSearcher(
            embedder=embedder,
            dense_index=self.dense_index,
            single_hop_callback=self._single_hop_search,
            reranking_engine=self.reranking_engine,
            logger=self._logger,
        )

        # Ego-graph retrieval (RepoGraph-style k-hop expansion)
        # Initialize graph storage if project_id is provided
        self.graph_storage = None
        self.ego_graph_retriever = None
        if project_id:
            try:
                # Graph storage in parent of storage_dir (same as graph_integration.py)
                graph_dir = self.storage_dir.parent
                self.graph_storage = CodeGraphStorage(
                    project_id=project_id, storage_dir=graph_dir
                )
                self.ego_graph_retriever = EgoGraphRetriever(self.graph_storage)
                self._logger.info(
                    f"[INIT] Ego-graph retrieval initialized for project: {project_id}"
                )
            except Exception as e:
                self._logger.warning(
                    f"[INIT] Failed to initialize ego-graph retrieval: {e}. "
                    "Ego-graph expansion will be disabled."
                )
                self.graph_storage = None
                self.ego_graph_retriever = None

        # Backward compatibility
        self.max_workers = max_workers
        self._shutdown_lock = threading.Lock()
        self._is_shutdown = False

        # Dimension validation (safety check)
        self._validate_dimensions()

    def _load_bm25_index(self) -> bool:
        """Load BM25 index and return success status.

        Returns:
            bool: True if index was loaded, False if starting fresh
        """
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
        return bm25_loaded

    def _load_dense_index(self) -> int:
        """Load dense index and return vector count.

        Returns:
            int: Number of vectors in the loaded index, 0 if starting fresh
        """
        # Dense index loads automatically in its __init__
        dense_count = self.dense_index.index.ntotal if self.dense_index.index else 0
        if dense_count > 0:
            self._logger.info(
                f"[INIT] Loaded existing dense index with {dense_count} vectors"
            )
        else:
            self._logger.info("[INIT] No existing dense index found, starting fresh")
        return dense_count

    def _load_indices_parallel(self) -> tuple[bool, int]:
        """Load BM25 and dense indices in parallel using ThreadPoolExecutor.

        Returns:
            tuple: (bm25_loaded: bool, dense_count: int)
        """
        self._logger.info("[INIT] Loading indices in parallel...")
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both load operations
            bm25_future = executor.submit(self._load_bm25_index)
            dense_future = executor.submit(self._load_dense_index)

            # Wait for both to complete and get results
            bm25_loaded = bm25_future.result()
            dense_count = dense_future.result()

        self._logger.info("[INIT] Parallel index loading complete")
        return bm25_loaded, dense_count

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def shutdown(self):
        """Shutdown the thread pool and cleanup resources."""
        with self._shutdown_lock:
            if not self._is_shutdown:
                # Delegate thread pool shutdown to SearchExecutor
                self.search_executor.shutdown()
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
        # Delegate to SearchExecutor for core stats
        stats = self.search_executor.stats

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

        Uses in-memory cache to avoid repeated SQLite lookups during
        multi-hop operations like find_connections (2-5x speedup).

        Args:
            chunk_id: Format "file.py:10-20:function:name"

        Returns:
            SearchResult if found, None otherwise
        """
        # Fast path: Check in-memory cache first
        if chunk_id in self._metadata_cache:
            self._cache_hits += 1
            return self._metadata_cache[chunk_id]

        # Slow path: Load from SQLite
        self._cache_misses += 1
        metadata = self.dense_index.get_chunk_by_id(chunk_id)
        if not metadata:
            # Cache None results to avoid repeated failed lookups
            self._metadata_cache[chunk_id] = None
            self._evict_cache_if_needed()
            return None

        # Delegate to ResultFactory for SearchResult creation
        result = ResultFactory.from_direct_lookup(chunk_id, metadata)

        # Store in cache for future lookups
        self._metadata_cache[chunk_id] = result
        self._evict_cache_if_needed()

        return result

    def _evict_cache_if_needed(self):
        """Evict oldest cache entries if cache exceeds max size.

        Uses simple FIFO eviction strategy. More sophisticated LRU could
        be implemented if needed, but FIFO is sufficient for most use cases.
        """
        if len(self._metadata_cache) > self._cache_max_size:
            # Evict oldest 20% of entries
            num_to_evict = self._cache_max_size // 5
            keys_to_remove = list(self._metadata_cache.keys())[:num_to_evict]
            for key in keys_to_remove:
                del self._metadata_cache[key]
            self._logger.debug(
                f"Evicted {num_to_evict} entries from metadata cache "
                f"(size: {len(self._metadata_cache)}/{self._cache_max_size})"
            )

    def get_cache_stats(self) -> Dict[str, int]:
        """Get metadata cache statistics.

        Returns:
            Dict with cache_hits, cache_misses, hit_rate_pct, cache_size
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        )

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_pct": round(hit_rate, 2),
            "cache_size": len(self._metadata_cache),
            "cache_max_size": self._cache_max_size,
        }

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
        config: Optional["SearchConfig"] = None,
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
            config: Optional SearchConfig override (for ego-graph settings, etc.)

        Returns:
            Search results (reranked for hybrid mode, direct for single modes)
        """
        # Reset session-level OOM tracking at start of new search
        if hasattr(self, "reranking_engine") and self.reranking_engine:
            self.reranking_engine.reset_session_state()

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
        # Allow config override (for ego-graph settings from MCP)
        effective_config = (
            config if config is not None else _get_config_via_service_locator()
        )

        # Get initial search results (multi-hop or single-hop)
        if effective_config.multi_hop.enabled:
            # Use multi-hop search for discovering related code
            results = self.multi_hop_searcher.search(
                query=query,
                k=k,
                search_mode=search_mode,
                hops=effective_config.multi_hop.hop_count,
                expansion_factor=effective_config.multi_hop.expansion,
                use_parallel=use_parallel,
                min_bm25_score=min_bm25_score,
                filters=filters,
            )
        else:
            # Single-hop search (direct matching only)
            results = self._single_hop_search(
                query=query,
                k=k,
                search_mode=search_mode,
                use_parallel=use_parallel,
                min_bm25_score=min_bm25_score,
                filters=filters,
            )

        # Apply ego-graph expansion if enabled
        if effective_config.ego_graph.enabled and self.ego_graph_retriever and results:
            results = self._apply_ego_graph_expansion(
                results, effective_config.ego_graph, k
            )

        return results

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

        Delegates to SearchExecutor. Used as callback by MultiHopSearcher.

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
        return self.search_executor.execute_single_hop(
            query=query,
            k=k,
            search_mode=search_mode,
            use_parallel=use_parallel,
            min_bm25_score=min_bm25_score,
            filters=filters,
            query_embedding=query_embedding,
        )

    def _apply_ego_graph_expansion(
        self, results: List[SearchResult], ego_config, original_k: int
    ) -> List[SearchResult]:
        """Apply ego-graph expansion to search results.

        Expands search results by retrieving k-hop graph neighbors,
        providing richer context like callers, callees, and related code.

        Args:
            results: Initial search results
            ego_config: EgoGraphConfig instance
            original_k: Original k parameter for search

        Returns:
            Expanded search results (anchors + neighbors)
        """
        if not results:
            return results

        try:
            # Convert SearchResults to format needed by ego_graph_retriever
            search_results_dict = [
                {"chunk_id": r.chunk_id, "score": r.score} for r in results
            ]

            # Expand via ego-graph
            expanded_chunk_ids, ego_graphs = (
                self.ego_graph_retriever.expand_search_results(
                    search_results_dict, ego_config
                )
            )

            if not expanded_chunk_ids:
                return results

            # Track which chunks are neighbors (not original anchors)
            original_chunk_ids = {r.chunk_id for r in results}
            neighbor_chunk_ids = set(expanded_chunk_ids) - original_chunk_ids

            # Retrieve metadata for neighbor chunks
            neighbor_results = []
            for chunk_id in neighbor_chunk_ids:
                try:
                    metadata = self.dense_index.get_chunk_by_id(chunk_id)
                    if metadata:
                        # Create SearchResult for neighbor (score=0 as it's context)
                        # Uses reranker.py SearchResult with correct fields
                        neighbor_result = SearchResult(
                            chunk_id=chunk_id,
                            score=0.0,  # Neighbors are context, no similarity score
                            metadata=metadata,  # All metadata stored in dict
                            source="ego_graph",  # Mark as ego-graph neighbor
                            rank=0,  # Default rank
                        )
                        neighbor_results.append(neighbor_result)
                except Exception as e:
                    self._logger.debug(
                        f"Failed to retrieve metadata for {chunk_id}: {e}"
                    )
                    continue

            # Combine original results (with scores) + neighbor results (context)
            # Original results first (sorted by score), then neighbors
            combined_results = results + neighbor_results

            self._logger.info(
                f"Ego-graph expansion: {len(results)} anchors -> "
                f"{len(combined_results)} total ({len(neighbor_results)} neighbors added)"
            )

            return combined_results

        except Exception as e:
            self._logger.warning(
                f"Ego-graph expansion failed: {e}. Returning original results."
            )
            return results

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

    def get_search_mode_stats(self) -> Dict[str, Any]:
        """Get statistics about search mode performance."""
        stats = self.search_executor.stats
        total_searches = stats["total_searches"]
        if total_searches == 0:
            return {"message": "No searches performed yet"}

        avg_bm25_time = stats["bm25_time"] / total_searches
        avg_dense_time = stats["dense_time"] / total_searches
        avg_rerank_time = stats["rerank_time"] / total_searches

        return {
            "total_searches": total_searches,
            "average_times": {
                "bm25": avg_bm25_time,
                "dense": avg_dense_time,
                "reranking": avg_rerank_time,
                "total": avg_bm25_time + avg_dense_time + avg_rerank_time,
            },
            "parallel_efficiency": stats.get("parallel_efficiency", 0.0),
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

        Delegates to WeightOptimizer for grid search over weight combinations.

        Args:
            test_queries: List of test queries
            ground_truth: Optional ground truth results for each query

        Returns:
            Optimized weights dict with keys:
                - bm25_weight: Optimal BM25 weight
                - dense_weight: Optimal dense weight
                - optimization_score: Best score achieved
                - tested_combinations: Number of combinations tested
        """
        # Create optimizer with callbacks
        optimizer = WeightOptimizer(
            search_callback=lambda q, k: self.search(q, k=k, use_parallel=False),
            analyze_callback=self.reranker.analyze_fusion_quality,
            set_weights_callback=lambda b, d: setattr(self, "bm25_weight", b)
            or setattr(self, "dense_weight", d),
            get_weights_callback=lambda: (self.bm25_weight, self.dense_weight),
            logger=self._logger,
        )

        # Delegate to optimizer
        return optimizer.optimize(test_queries, ground_truth=ground_truth)

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

        # Update SearchExecutor references to new indices
        self.search_executor.bm25_index = self.bm25_index
        self.search_executor.dense_index = self.dense_index

        # Update MultiHopSearcher reference to new dense index
        self.multi_hop_searcher.dense_index = self.dense_index

    def remove_file_chunks(self, file_path: str, project_name: str) -> int:
        """Remove chunks for a specific file from both indices. Delegates to IndexSynchronizer."""
        return self.index_sync.remove_file_chunks(file_path, project_name)

    def remove_multiple_files(self, file_paths: set, project_name: str) -> int:
        """Remove chunks for multiple files from both indices. Delegates to IndexSynchronizer."""
        return self.index_sync.remove_multiple_files(file_paths, project_name)

    def _verify_bm25_files(self):
        """Verify BM25 files exist and are non-empty. Delegates to IndexSynchronizer."""
        self.index_sync._verify_bm25_files()
