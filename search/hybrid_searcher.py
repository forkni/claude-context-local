"""Hybrid search orchestrator combining BM25 + dense search with GPU awareness."""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import numpy as np


if TYPE_CHECKING:
    from embeddings.embedder import CodeEmbedder, EmbeddingResult

    from .config import EgoGraphConfig, SearchConfig

try:
    import torch
except ImportError:
    torch = None

from graph.graph_storage import CodeGraphStorage
from graph.relationship_types import RelationshipEdge, RelationshipType
from mcp_server.utils.config_helpers import (
    get_config_via_service_locator as _get_config_via_service_locator,
)
from search.graph_integration import SEMANTIC_TYPES

from .base_searcher import BaseSearcher
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


class HybridSearcher(BaseSearcher):
    """Orchestrates BM25 + dense search with GPU awareness and parallel execution."""

    def __init__(
        self,
        storage_dir: str,
        embedder: Optional["CodeEmbedder"] = None,
        bm25_weight: float = 0.35,
        dense_weight: float = 0.65,
        rrf_k: int = 60,
        max_workers: int = 2,
        bm25_use_stopwords: bool = True,
        bm25_use_stemming: bool = True,
        project_id: str | None = None,
        config: Optional["SearchConfig"] = None,
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
        # Initialize base searcher (cache management, dimension validation)
        super().__init__()

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

        # Override logger with module-specific logger (set by BaseSearcher)
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
        if isinstance(total_bm25, int) and isinstance(dense_count, int) and abs(total_bm25 - dense_count) > 10:
                self._logger.warning(
                    f"[INIT] INDEX MISMATCH DETECTED: BM25={total_bm25}, Dense={dense_count}. "
                    f"Consider re-indexing to synchronize indices."
                )

        # Initialize search components (reranker, search executor, multi-hop)
        self._init_search_components(
            embedder=embedder,
            rrf_k=rrf_k,
            bm25_weight=bm25_weight,
            dense_weight=dense_weight,
            max_workers=max_workers,
            bm25_use_stopwords=bm25_use_stopwords,
            bm25_use_stemming=bm25_use_stemming,
            project_id=project_id,
        )

        # Initialize graph components (ego-graph retrieval)
        self._init_graph_components(project_id=project_id)

        # Wire graph_storage into multi-hop searcher for graph expansion
        if self._graph_storage is not None:
            self.multi_hop_searcher.graph_storage = self._graph_storage

        # Backward compatibility
        self.max_workers = max_workers
        self._shutdown_lock = threading.Lock()
        self._is_shutdown = False

        # Dimension validation (safety check)
        self._validate_dimensions(self.dense_index.index, self.embedder)

    def _init_search_components(
        self,
        embedder: Optional["CodeEmbedder"],
        rrf_k: int,
        bm25_weight: float,
        dense_weight: float,
        max_workers: int,
        bm25_use_stopwords: bool,
        bm25_use_stemming: bool,
        project_id: str | None,
    ) -> None:
        """Initialize search execution components.

        Creates reranker, GPU monitor, reranking engine, index synchronizer,
        search executor, and multi-hop searcher with proper configuration.

        Args:
            embedder: CodeEmbedder instance
            rrf_k: RRF parameter for reranking
            bm25_weight: Weight for BM25 results
            dense_weight: Weight for dense vector results
            max_workers: Maximum thread pool workers
            bm25_use_stopwords: Whether BM25 uses stopwords
            bm25_use_stemming: Whether BM25 uses stemming
            project_id: Project identifier
        """
        # Reranker and GPU monitor
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

    def _init_graph_components(self, project_id: str | None) -> None:
        """Initialize graph storage and ego-graph retrieval components.

        Creates CodeGraphStorage and EgoGraphRetriever if project_id is provided.
        Logs warnings if initialization fails but continues (non-critical).

        Args:
            project_id: Project identifier for graph storage
        """
        # Initialize to None
        self._graph_storage = None
        self.ego_graph_retriever = None

        if project_id:
            try:
                # Graph storage in parent of storage_dir (same as graph_integration.py)
                graph_dir = self.storage_dir.parent
                self._graph_storage = CodeGraphStorage(
                    project_id=project_id, storage_dir=graph_dir
                )
                self.ego_graph_retriever = EgoGraphRetriever(self._graph_storage)
                self._logger.info(
                    f"[INIT] Ego-graph retrieval initialized for project: {project_id}"
                )
            except Exception as e:
                self._logger.warning(
                    f"[INIT] Failed to initialize ego-graph retrieval: {e}. "
                    "Ego-graph expansion will be disabled."
                )
                self._graph_storage = None
                self.ego_graph_retriever = None

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

    def __enter__(self) -> "HybridSearcher":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.shutdown()

    def close_metadata_connections(self) -> None:
        """Close all metadata store connections to release file locks."""
        if (
            self.dense_index is not None
            and hasattr(self.dense_index, "_metadata_store")
            and self.dense_index._metadata_store is not None
        ):
            self.dense_index._metadata_store.close()
            self._logger.debug("Closed dense_index metadata store")

    def shutdown(self) -> None:
        """Shutdown the thread pool and cleanup resources."""
        with self._shutdown_lock:
            if not self._is_shutdown:
                # Close metadata connections first to release file locks
                self.close_metadata_connections()
                # Delegate thread pool shutdown to SearchExecutor
                self.search_executor.shutdown()
                # Cleanup reranking engine (which handles neural reranker cleanup)
                self.reranking_engine.shutdown()
                self._is_shutdown = True
                self._logger.info("HybridSearcher shut down")

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
    def graph_storage(self) -> CodeGraphStorage | None:
        """Access graph storage for relationship queries.

        Returns:
            CodeGraphStorage instance or None if not available
        """
        return self._graph_storage

    @graph_storage.setter
    def graph_storage(self, value: CodeGraphStorage | None) -> None:
        """Set graph storage (primarily for testing).

        Args:
            value: CodeGraphStorage instance or None
        """
        self._graph_storage = value

    @property
    def stats(self) -> dict[str, Any]:
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

    def _set_hybrid_weights(self, bm25_weight: float, dense_weight: float) -> None:
        """Set both BM25 and dense weights atomically (for weight optimizer)."""
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

    @property
    def neural_reranker(self) -> NeuralReranker | None:
        """Access the neural reranker instance (backward compatibility).

        Returns:
            NeuralReranker instance from reranking_engine, or None if not initialized.

        Note:
            This property delegates to reranking_engine.neural_reranker.
            The neural reranker is lazily initialized when first needed.
        """
        return self.reranking_engine.neural_reranker

    def get_stats(self) -> dict[str, Any]:
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

    def get_by_chunk_id(self, chunk_id: str) -> SearchResult | None:
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

    def index_documents(
        self,
        documents: list[str],
        doc_ids: list[str],
        embeddings: list[list[float]],
        metadata: dict[str, dict] | None = None,
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
        k: int = 4,
        search_mode: str = "hybrid",
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filters: dict[str, Any] | None = None,
        config: Optional["SearchConfig"] = None,
    ) -> list[SearchResult]:
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
                edge_weights=effective_config.multi_hop.edge_weights,
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
                results, effective_config.ego_graph, k, query
            )

        # Apply parent expansion if enabled (limit to primary k results to prevent bloat)
        if effective_config.parent_retrieval.enabled and results:
            results = self._apply_parent_expansion(
                results, effective_config.parent_retrieval, max_results_to_expand=k
            )

        # Post-expansion neural reranking: unify scoring across primary + ego results
        # Only runs when ego-graph added results, putting all on same cross-encoder scale
        if (
            effective_config.ego_graph.enabled
            and self.reranking_engine
            and len(results) > k
        ):
            results = self.reranking_engine.rerank_by_query(
                query=query,
                results=results,
                k=len(results),  # Keep all results, just re-score and re-sort
                search_mode=search_mode,
            )

        return results

    def _single_hop_search(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filters: dict[str, Any] | None = None,
        query_embedding: np.ndarray | None = None,
    ) -> list[SearchResult]:
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
        self,
        results: list[SearchResult],
        ego_config: "EgoGraphConfig",
        original_k: int,
        query: str,
    ) -> list[SearchResult]:
        """Apply ego-graph expansion to search results.

        Expands search results by retrieving k-hop graph neighbors,
        providing richer context like callers, callees, and related code.

        Args:
            results: Initial search results
            ego_config: EgoGraphConfig instance
            original_k: Original k parameter for search
            query: Original search query (for similarity scoring of neighbors)

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

            # Build neighbor→anchor mapping for decay scoring
            # ego_graphs: dict[anchor_id, list[neighbor_ids]]
            neighbor_to_anchor = {}
            for anchor_id, neighbors in ego_graphs.items():
                for neighbor_id in neighbors:
                    if neighbor_id not in original_chunk_ids:
                        neighbor_to_anchor[neighbor_id] = anchor_id

            # Compute query embedding once for all neighbor scoring
            try:
                query_embedding = self.embedder.embed_query(query)
                query_embedding_available = True
            except Exception as e:
                self._logger.warning(
                    f"Failed to compute query embedding for ego-graph scoring: {e}. "
                    f"Falling back to fixed decay."
                )
                query_embedding = None
                query_embedding_available = False

            # Pre-compute anchor scores for relative scoring
            anchor_scores = {r.chunk_id: r.score for r in results}

            # Retrieve metadata for neighbor chunks
            neighbor_results = []
            for chunk_id in neighbor_chunk_ids:
                try:
                    metadata = self.dense_index.get_chunk_by_id(chunk_id)
                    if not metadata:
                        continue

                    # Similarity-based scoring: compute cosine similarity with query
                    if query_embedding_available:
                        try:
                            # Get neighbor's index position
                            chunk_ids_list = list(self.dense_index.chunk_ids)
                            idx = chunk_ids_list.index(chunk_id)
                            # Reconstruct neighbor embedding via FAISS
                            neighbor_embedding = (
                                self.dense_index._faiss_index.reconstruct(idx)
                            )
                            # Compute cosine similarity (embeddings are L2-normalized)
                            similarity = float(
                                np.dot(query_embedding, neighbor_embedding)
                            )
                            # Optional: filter very low relevance neighbors
                            if similarity < 0.15:
                                self._logger.debug(
                                    f"Filtering ego-graph neighbor {chunk_id}: "
                                    f"similarity={similarity:.3f} < 0.15"
                                )
                                continue
                            # Scale score relative to anchor (prevents neighbors from outranking anchors)
                            anchor_id = neighbor_to_anchor.get(chunk_id)
                            anchor_score = (
                                anchor_scores.get(anchor_id, 0.0) if anchor_id else 0.0
                            )
                            neighbor_score = anchor_score * similarity
                        except (ValueError, IndexError, AttributeError) as e:
                            # Fallback to decay if reconstruction fails
                            self._logger.debug(
                                f"Failed to reconstruct embedding for {chunk_id}: {e}. Using decay."
                            )
                            anchor_id = neighbor_to_anchor.get(chunk_id)
                            anchor_score = (
                                anchor_scores.get(anchor_id, 0.0) if anchor_id else 0.0
                            )
                            neighbor_score = anchor_score * 0.5
                    else:
                        # Fallback: fixed decay scoring
                        anchor_id = neighbor_to_anchor.get(chunk_id)
                        anchor_score = (
                            anchor_scores.get(anchor_id, 0.0) if anchor_id else 0.0
                        )
                        neighbor_score = anchor_score * 0.5

                    # Create SearchResult for neighbor with similarity score
                    neighbor_result = SearchResult(
                        chunk_id=chunk_id,
                        score=neighbor_score,  # Similarity-based or decay fallback
                        metadata=metadata,  # All metadata stored in dict
                        source="ego_graph",  # Mark as ego-graph neighbor
                        rank=0,  # Default rank
                    )
                    neighbor_results.append(neighbor_result)
                except (KeyError, TypeError) as e:
                    self._logger.debug(
                        f"Failed to retrieve metadata for {chunk_id}: {e}"
                    )
                    continue

            # Cap ego-graph neighbors to prevent token bloat
            max_ego = min(
                ego_config.max_neighbors_per_hop * ego_config.k_hops, original_k * 3
            )
            if len(neighbor_results) > max_ego:
                neighbor_results.sort(key=lambda r: r.score, reverse=True)
                self._logger.info(
                    f"Capping ego-graph neighbors: {len(neighbor_results)} -> {max_ego}"
                )
                neighbor_results = neighbor_results[:max_ego]

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

    def _apply_parent_expansion(
        self,
        results: list[SearchResult],
        config: "SearchConfig",
        max_results_to_expand: int = 0,
    ) -> list[SearchResult]:
        """Apply parent chunk expansion to search results.

        For each matched method/function, retrieves its enclosing class chunk
        to provide fuller context ("Match Small, Retrieve Big").

        Args:
            results: Initial search results
            config: ParentRetrievalConfig instance

        Returns:
            Expanded search results (original + parent chunks)
        """
        if not results or not config.enabled:
            return results

        try:
            # Track parent chunk_ids to retrieve (avoid duplicates)
            parent_chunk_ids: set = set()
            original_chunk_ids = {r.chunk_id for r in results}

            # Find parent_chunk_ids from result metadata (limit to primary results if specified)
            results_to_expand = (
                results[:max_results_to_expand]
                if max_results_to_expand > 0
                else results
            )
            for result in results_to_expand:
                parent_id = result.metadata.get("parent_chunk_id")
                if parent_id and parent_id not in original_chunk_ids:
                    parent_chunk_ids.add(parent_id)

            if not parent_chunk_ids:
                self._logger.debug("No parent chunks to retrieve")
                return results

            # Retrieve metadata for parent chunks
            parent_results = []
            for parent_id in parent_chunk_ids:
                try:
                    metadata = self.dense_index.get_chunk_by_id(parent_id)
                    if metadata:
                        parent_result = SearchResult(
                            chunk_id=parent_id,
                            score=0.0,  # Parents are context, no similarity score
                            metadata=metadata,
                            source="parent_expansion",  # Mark source
                            rank=0,
                        )
                        parent_results.append(parent_result)
                except (KeyError, TypeError) as e:
                    self._logger.debug(
                        f"Failed to retrieve parent chunk {parent_id}: {e}"
                    )
                    continue

            # Combine: original results first, then parent context
            combined_results = results + parent_results

            self._logger.info(
                f"Parent expansion: {len(results)} results -> "
                f"{len(combined_results)} total ({len(parent_results)} parents added)"
            )

            return combined_results

        except Exception as e:
            self._logger.warning(
                f"Parent expansion failed: {e}. Returning original results."
            )
            return results

    def find_similar_to_chunk(
        self, chunk_id: str, k: int = 5, rerank: bool = False
    ) -> list:
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

    def get_search_mode_stats(self) -> dict[str, Any]:
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
        self, test_queries: list[str], ground_truth: list[list[str]] | None = None
    ) -> dict[str, float]:
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
            set_weights_callback=self._set_hybrid_weights,
            get_weights_callback=lambda: (self.bm25_weight, self.dense_weight),
            logger=self._logger,
        )

        # Delegate to optimizer
        return optimizer.optimize(test_queries, ground_truth=ground_truth)

    def save_indices(self) -> None:
        """Save BM25, dense indices, and call graph. Delegates to IndexSynchronizer."""
        self.index_sync.save_indices()

        # Save call graph if populated
        if self._graph_storage is not None and len(self._graph_storage) > 0:
            try:
                self._logger.info(
                    f"[SAVE_INDICES] Saving call graph with {len(self._graph_storage)} nodes, "
                    f"{self._graph_storage.graph.number_of_edges()} edges"
                )
                self._graph_storage.save()
                self._logger.info("[SAVE_INDICES] Call graph saved successfully")
            except (OSError, RuntimeError) as e:
                self._logger.warning(f"[SAVE_INDICES] Failed to save call graph: {e}")

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

    def add_embeddings(self, embedding_results: list["EmbeddingResult"]) -> None:
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

            # Populate call graph with nodes and edges
            if self._graph_storage is not None:
                graph_nodes_added = 0
                graph_edges_added = 0
                relationship_edges_added = 0
                resolved_count = 0
                # Use canonical SEMANTIC_TYPES from graph_integration
                semantic_types = set(SEMANTIC_TYPES)

                # Build name resolution map for call target resolution
                # Maps symbol names to their chunk_ids for resolving call targets
                name_to_chunk_ids: dict[str, list[str]] = {}
                for result in embedding_results:
                    chunk_id = result.chunk_id
                    name = result.metadata.get("name")
                    if name:
                        if name not in name_to_chunk_ids:
                            name_to_chunk_ids[name] = []
                        name_to_chunk_ids[name].append(chunk_id)

                        # Also index by bare name for methods (ClassName.method → method)
                        if "." in name:
                            bare_name = name.split(".")[-1]
                            if bare_name not in name_to_chunk_ids:
                                name_to_chunk_ids[bare_name] = []
                            name_to_chunk_ids[bare_name].append(chunk_id)

                for result in embedding_results:
                    chunk_id = result.chunk_id
                    chunk_type = result.metadata.get("chunk_type")

                    # Only add semantic types
                    if chunk_type not in semantic_types:
                        continue

                    # Add node
                    self._graph_storage.add_node(
                        chunk_id=chunk_id,
                        name=result.metadata.get("name", "unknown"),
                        chunk_type=chunk_type,
                        file_path=result.metadata.get("file_path", ""),
                        language=result.metadata.get("language", "python"),
                    )
                    graph_nodes_added += 1

                    # Add call edges with resolution
                    calls = result.metadata.get("calls", [])
                    for call_dict in calls:
                        callee_name = call_dict.get("callee_name", "unknown")

                        # Try to resolve call target to full chunk_id
                        # Conservative approach with same-file preference and split_block disambiguation
                        resolved_target = None
                        candidates = name_to_chunk_ids.get(callee_name, [])
                        if len(candidates) == 1:
                            resolved_target = candidates[0]
                        elif len(candidates) > 1:
                            # Same-file preference
                            caller_file = result.metadata.get("file_path", "")
                            same_file = [c for c in candidates if caller_file in c]
                            if len(same_file) == 1:
                                resolved_target = same_file[0]
                            else:
                                # Split block disambiguation: all split_blocks → pick entry block (lowest start line)
                                split_blocks = [
                                    c for c in candidates if ":split_block:" in c
                                ]
                                if len(split_blocks) == len(candidates):

                                    def _start_line(cid: str) -> int:
                                        parts = cid.split(":")
                                        if len(parts) >= 2:
                                            try:
                                                return int(parts[1].split("-")[0])
                                            except (ValueError, IndexError):
                                                pass
                                        return 2**31  # Sentinel for sort ordering

                                    split_blocks.sort(key=_start_line)
                                    resolved_target = split_blocks[0]
                        if resolved_target:
                            resolved_count += 1

                        # Use resolved chunk_id if available, otherwise use bare name
                        self._graph_storage.add_call_edge(
                            caller_id=chunk_id,
                            callee_name=(
                                resolved_target if resolved_target else callee_name
                            ),
                            line_number=call_dict.get("line_number", 0),
                            is_method_call=call_dict.get("is_method_call", False),
                            is_resolved=resolved_target is not None,
                        )
                        graph_edges_added += 1

                    # Add relationship edges (inherits, imports, decorates, etc.)
                    relationships = result.metadata.get("relationships", [])
                    for rel_dict in relationships:
                        try:
                            # Reconstruct RelationshipEdge from dict
                            edge = RelationshipEdge(
                                source_id=rel_dict.get("source_id", chunk_id),
                                target_name=rel_dict.get("target_name", "unknown"),
                                relationship_type=RelationshipType(
                                    rel_dict.get("relationship_type", "calls")
                                ),
                                line_number=rel_dict.get("line_number", 0),
                                confidence=rel_dict.get("confidence", 1.0),
                                metadata=rel_dict.get("metadata", {}),
                            )

                            # Add to graph storage
                            self._graph_storage.add_relationship_edge(edge)
                            relationship_edges_added += 1

                        except (ValueError, KeyError, TypeError) as e:
                            self._logger.debug(
                                f"Failed to add relationship edge from {chunk_id}: {e}"
                            )

                self._logger.info(
                    f"[ADD_EMBEDDINGS] Populated graph: {graph_nodes_added} nodes, "
                    f"{graph_edges_added} call edges ({resolved_count} resolved, "
                    f"{graph_edges_added - resolved_count} phantom), "
                    f"{relationship_edges_added} relationship edges"
                )

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
        # CRITICAL: Close all metadata references BEFORE clearing to prevent reopening
        # The reranking_engine holds a reference to the same MetadataStore object.
        # If we don't close it, any access to reranking_engine.metadata_store.get()
        # will trigger _ensure_open() and REOPEN the database, preventing file deletion.
        if (
            hasattr(self, "reranking_engine")
            and self.reranking_engine is not None
            and hasattr(self.reranking_engine, "metadata_store")
            and self.reranking_engine.metadata_store is not None
        ):
                self.reranking_engine.metadata_store.close()
                self._logger.debug(
                    "Closed reranking_engine metadata store before clear"
                )

        # Now safe to clear
        self.index_sync.clear_index()

        # Sync modified index references back
        self.bm25_index = self.index_sync.bm25_index
        self.dense_index = self.index_sync.dense_index
        # Update reranking_engine's metadata_store reference to NEW store
        if hasattr(self, "reranking_engine") and self.reranking_engine is not None:
            self.reranking_engine.metadata_store = self.dense_index.metadata_store

        # Update SearchExecutor references to new indices
        self.search_executor.bm25_index = self.bm25_index
        self.search_executor.dense_index = self.dense_index

        # Update MultiHopSearcher reference to new dense index
        self.multi_hop_searcher.dense_index = self.dense_index

        # Update graph_storage reference to match new dense_index (prevents stale references)
        if hasattr(self.dense_index, "_graph") and self.dense_index._graph:
            self._graph_storage = self.dense_index._graph.storage
            self._logger.debug(
                "[CLEAR] Updated graph_storage reference after clear_index()"
            )

    def remove_file_chunks(self, file_path: str, project_name: str) -> int:
        """Remove chunks for a specific file from both indices. Delegates to IndexSynchronizer."""
        return self.index_sync.remove_file_chunks(file_path, project_name)

    def remove_multiple_files(self, file_paths: set, project_name: str) -> int:
        """Remove chunks for multiple files from both indices. Delegates to IndexSynchronizer."""
        return self.index_sync.remove_multiple_files(file_paths, project_name)

    def _verify_bm25_files(self) -> None:
        """Verify BM25 files exist and are non-empty. Delegates to IndexSynchronizer."""
        self.index_sync._verify_bm25_files()
