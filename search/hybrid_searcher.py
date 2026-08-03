"""Hybrid search orchestrator combining BM25 + dense search with GPU awareness."""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, cast

import numpy as np


if TYPE_CHECKING:
    from embeddings.embedder import CodeEmbedder, EmbeddingResult

    from .config import EgoGraphConfig, ParentRetrievalConfig, SearchConfig

from embeddings.chunk_metadata import ChunkMetadata


try:
    import torch
except ImportError:
    torch = None

from graph.graph_storage import CodeGraphStorage
from mcp_server.utils.config_helpers import (
    get_config_via_service_locator as _get_config_via_service_locator,
)
from search.config import SearchMode
from search.graph_integration import GraphIntegration
from utils.observability import traced_block
from utils.otel_attributes import (
    ATTR_CAPTURE_QUERY,
    ATTR_K,
    ATTR_RESULT_COUNT,
    ATTR_SEARCH_MODE,
)
from utils.timing import timer

from .base_searcher import BaseSearcher
from .bm25_index import BM25Index
from .chunk_id import dedupe_results
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
from .tokenization import augment_bm25_document
from .types import RetrievalRequest


class HybridSearcher(BaseSearcher):
    """Orchestrates BM25 + dense search with GPU awareness and parallel execution."""

    def __init__(
        self,
        storage_dir: str,
        embedder: Optional["CodeEmbedder"] = None,
        rrf_k: int = 60,
        max_workers: int = 2,
        bm25_use_stopwords: bool = True,
        bm25_use_stemming: bool = True,
        bm25_tokenizer: str = "legacy",
        bm25_k1: float = 1.5,
        bm25_b: float = 0.75,
        project_id: str | None = None,
        config: Optional["SearchConfig"] = None,
        load_existing: bool = True,
    ):
        """
        Initialize hybrid searcher.

        Args:
            storage_dir: Directory for storing indices
            embedder: CodeEmbedder instance for semantic search (optional)
            rrf_k: RRF parameter for reranking
            max_workers: Maximum thread pool workers for parallel execution
            bm25_use_stopwords: Whether BM25 should filter stopwords
            bm25_use_stemming: Whether BM25 should use Snowball stemming
            bm25_tokenizer: BM25 tokenizer variant (legacy/whole/additive)
            bm25_k1: Okapi BM25 term-frequency saturation parameter
            bm25_b: Okapi BM25 document-length normalization parameter
            project_id: Project identifier for graph storage
            config: SearchConfig instance for mmap storage and other settings
            load_existing: When False, skip reading the on-disk BM25 index
                (#reindex-log-audit-2026-07-30). Set this for a searcher that
                exists only as a write target for a force-full reindex — the
                caller is about to call clear_hybrid_indices(), so loading the
                stale index first only costs time and emits spurious BM25
                version/tokenizer mismatch warnings for data being discarded.
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

        # BM25 configuration
        self.bm25_use_stopwords = bm25_use_stopwords
        self.bm25_use_stemming = bm25_use_stemming
        self.bm25_tokenizer = bm25_tokenizer
        self.bm25_k1 = bm25_k1
        self.bm25_b = bm25_b

        # Override logger with module-specific logger (set by BaseSearcher)
        self._logger = logging.getLogger(__name__)

        # BM25 index gets its own subdirectory
        self._logger.info(
            f"[INIT] Creating BM25Index at: {self.storage_dir / 'bm25'} "
            f"(stopwords={bm25_use_stopwords}, stemming={bm25_use_stemming}, "
            f"tokenizer={bm25_tokenizer})"
        )
        try:
            self.bm25_index = BM25Index(
                str(self.storage_dir / "bm25"),
                use_stopwords=bm25_use_stopwords,
                use_stemming=bm25_use_stemming,
                tokenizer=bm25_tokenizer,
                k1=bm25_k1,
                b=bm25_b,
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
        )

        # Load both indices in parallel for faster startup — unless the caller
        # told us this searcher is a write-only target (load_existing=False),
        # in which case loading the stale on-disk BM25 index would only cost
        # time and log spurious mismatch warnings for an index about to be
        # cleared. The dense count still reflects reality: CodeIndexManager
        # loads the FAISS index unconditionally in its own __init__ above.
        if load_existing:
            self._logger.info(f"[INIT] BM25 storage path: {self.storage_dir / 'bm25'}")
            bm25_loaded, dense_count = self._load_indices_parallel()
        else:
            self._logger.info(
                "[INIT] load_existing=False — skipping BM25 index load "
                "(write-only searcher for a pending force-full reindex)"
            )
            dense_count = self.dense_index.index.ntotal if self.dense_index.index else 0

        # Log final initialization status
        total_bm25 = self.bm25_index.size
        self._logger.info(
            f"[INIT] HybridSearcher initialized - BM25: {total_bm25} docs, Dense: {dense_count} vectors"
        )
        self._logger.info(
            f"[INIT] Ready status: BM25={not self.bm25_index.is_empty}, Dense={dense_count > 0}, Overall={self.is_ready}"
        )

        # Check for index mismatch (early warning system) — skip when this is a
        # write-only searcher (load_existing=False): BM25 is deliberately unloaded
        # above, so total_bm25=0 vs dense_count>0 is expected, not a real mismatch.
        if (
            load_existing
            and isinstance(total_bm25, int)
            and isinstance(dense_count, int)
            and abs(total_bm25 - dense_count) > 10
        ):
            self._logger.warning(
                f"[INIT] INDEX MISMATCH DETECTED: BM25={total_bm25}, Dense={dense_count}. "
                f"Consider re-indexing to synchronize indices."
            )

        # Initialize search components (reranker, search executor, multi-hop)
        self._init_search_components(
            embedder=embedder,
            rrf_k=rrf_k,
            max_workers=max_workers,
            bm25_use_stopwords=bm25_use_stopwords,
            bm25_use_stemming=bm25_use_stemming,
            bm25_tokenizer=bm25_tokenizer,
            bm25_k1=bm25_k1,
            bm25_b=bm25_b,
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
        max_workers: int,
        bm25_use_stopwords: bool,
        bm25_use_stemming: bool,
        bm25_tokenizer: str,
        bm25_k1: float,
        bm25_b: float,
        project_id: str | None,
    ) -> None:
        """Initialize search execution components.

        Creates reranker, GPU monitor, reranking engine, index synchronizer,
        search executor, and multi-hop searcher with proper configuration.

        Args:
            embedder: CodeEmbedder instance
            rrf_k: RRF parameter for reranking
            max_workers: Maximum thread pool workers
            bm25_use_stopwords: Whether BM25 uses stopwords
            bm25_use_stemming: Whether BM25 uses stemming
            bm25_tokenizer: BM25 tokenizer variant (legacy/whole/additive)
            bm25_k1: Okapi BM25 term-frequency saturation parameter
            bm25_b: Okapi BM25 document-length normalization parameter
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
            bm25_tokenizer=bm25_tokenizer,
            bm25_k1=bm25_k1,
            bm25_b=bm25_b,
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
        self._graph: GraphIntegration | None = None
        self.ego_graph_retriever = None

        if project_id:
            try:
                # Reuse the CodeGraphStorage already loaded by CodeIndexManager
                # (via dense_index.graph_storage) to avoid a second JSON deserialize.
                existing_storage = getattr(self.dense_index, "graph_storage", None)
                if existing_storage is not None:
                    self._graph_storage = existing_storage
                    self._logger.debug(
                        "[INIT] Reusing graph storage from dense_index (skipped duplicate load)"
                    )
                else:
                    # Fallback: load independently (e.g., CodeIndexManager had no project_id)
                    graph_dir = self.storage_dir.parent
                    self._graph_storage = CodeGraphStorage(
                        project_id=project_id, storage_dir=graph_dir
                    )
                self._graph = GraphIntegration.from_storage(self._graph_storage)
                # pyrefly: ignore [bad-argument-type]
                self.ego_graph_retriever = EgoGraphRetriever(self._graph_storage)
                self._logger.info(
                    f"[INIT] Ego-graph retrieval initialized for project: {project_id}"
                )
            except Exception as e:  # noqa: BLE001 - resilience: optional ego-graph init, feature disabled on failure
                self._logger.warning(
                    f"[INIT] Failed to initialize ego-graph retrieval: {e}. "
                    "Ego-graph expansion will be disabled.",
                    exc_info=True,
                )
                self._graph_storage = None
                self._graph = None
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
        self._graph = (
            GraphIntegration.from_storage(value) if value is not None else None
        )

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

    @property
    def neural_reranker(self) -> NeuralReranker | None:
        """Access the neural reranker instance (backward compatibility).

        Returns:
            NeuralReranker instance from reranking_engine, or None if not initialized.

        Note:
            This property delegates to reranking_engine.neural_reranker.
            The neural reranker is lazily initialized when first needed.
        """
        # pyrefly: ignore [bad-return]
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

    def get_by_chunk_id(
        self, chunk_id: str, warn_on_miss: bool = True
    ) -> SearchResult | None:
        """
        Direct lookup by chunk_id (unambiguous, no search needed).

        Uses in-memory cache to avoid repeated SQLite lookups during
        multi-hop operations like find_connections (2-5x speedup).

        Args:
            chunk_id: Format "file.py:10-20:function:name"
            warn_on_miss: Whether to log a WARNING when the lookup misses.
                Pass False for speculative probes (e.g. edge-recovery ladders)
                where a miss is expected control flow, not a defect.

        Returns:
            SearchResult if found, None otherwise
        """
        # Fast path: Check in-memory cache first
        if chunk_id in self._metadata_cache:
            self._cache_hits += 1
            return self._metadata_cache[chunk_id]

        # Slow path: Load from SQLite
        self._cache_misses += 1
        metadata = self.dense_index.get_chunk_by_id(chunk_id, warn_on_miss=warn_on_miss)
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
                metadata=cast(
                    ChunkMetadata, metadata.get(chunk_id, {}) if metadata else {}
                ),
            )
            embedding_results.append(result)

        self.dense_index.add_embeddings(embedding_results)
        dense_time = time.time() - start_time

        self._logger.info(
            f"Hybrid indexing complete: BM25 {bm25_time:.2f}s, Dense {dense_time:.2f}s"
        )

    # pyrefly: ignore [bad-override]
    def search(
        self,
        query: str,
        k: int = 4,
        search_mode: str | SearchMode = SearchMode.HYBRID,
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filters: dict[str, Any] | None = None,
        config: Optional["SearchConfig"] = None,
        bm25_weight: float | None = None,
        dense_weight: float | None = None,
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
        # Normalize to the enum once at the boundary. Unknown strings have
        # always fallen through every dispatch else-branch to hybrid; keep that.
        try:
            search_mode = SearchMode(search_mode)
        except ValueError:
            search_mode = SearchMode.HYBRID

        # Reset session-level OOM tracking at start of new search
        if hasattr(self, "reranking_engine") and self.reranking_engine:
            self.reranking_engine.reset_session_state()

        with traced_block(
            "search.hybrid", **{ATTR_SEARCH_MODE: search_mode, ATTR_K: k}
        ) as span:
            # Check if indices are ready based on search mode
            if search_mode == SearchMode.BM25:
                if self.bm25_index.is_empty:
                    self._logger.warning(
                        "BM25 search requested but BM25 index is empty"
                    )
                    span.set_attribute(ATTR_RESULT_COUNT, 0)
                    return []
            elif search_mode == SearchMode.SEMANTIC:
                if not self.dense_index.index or self.dense_index.index.ntotal == 0:
                    self._logger.warning(
                        "Semantic search requested but dense index is empty"
                    )
                    span.set_attribute(ATTR_RESULT_COUNT, 0)
                    return []
            else:  # hybrid
                if not self.is_ready:
                    self._logger.warning(
                        "Hybrid search not ready - indices may be empty"
                    )
                    span.set_attribute(ATTR_RESULT_COUNT, 0)
                    return []

            # Check if multi-hop search is enabled
            # Use ServiceLocator helper instead of inline import
            # Allow config override (for ego-graph settings from MCP)
            effective_config = (
                config if config is not None else _get_config_via_service_locator()
            )

            if effective_config.observability.capture_query_text:
                span.set_attribute(ATTR_CAPTURE_QUERY, query)

            # Resolve weights once, here: explicit kwarg wins, else the
            # effective config's defaults. Resolving from config (not an
            # instance field — HybridSearcher no longer keeps one) means the
            # two values placed on the request below cannot disagree by
            # construction. See ADR-0018.
            eff_bm25_weight = (
                bm25_weight
                if bm25_weight is not None
                else effective_config.search_mode.bm25_weight
            )
            eff_dense_weight = (
                dense_weight
                if dense_weight is not None
                else effective_config.search_mode.dense_weight
            )

            request = RetrievalRequest(
                query=query,
                k=k,
                search_mode=search_mode,
                bm25_weight=eff_bm25_weight,
                dense_weight=eff_dense_weight,
                min_bm25_score=min_bm25_score,
                use_parallel=use_parallel,
                filters=filters,
                config=effective_config,
            )

            # Get initial search results (multi-hop or single-hop)
            if effective_config.multi_hop.enabled:
                # Use multi-hop search for discovering related code
                results = self.multi_hop_searcher.search(
                    request,
                    hops=effective_config.multi_hop.hop_count,
                    expansion_factor=effective_config.multi_hop.expansion,
                    edge_weights=effective_config.multi_hop.edge_weights,
                )
            else:
                # Single-hop search (direct matching only)
                results = self._single_hop_search(request)

            # Apply ego-graph expansion if enabled
            if (
                effective_config.ego_graph.enabled
                and self.ego_graph_retriever
                and results
            ):
                # timer() at the call site (not @timed on the method): a
                # decorator changes the chunk kind to decorated_definition,
                # breaking golden-dataset chunk IDs that reference this method
                with timer("ego_expansion"):
                    results = self._apply_ego_graph_expansion(
                        results, effective_config.ego_graph, k, query
                    )

            # Apply parent expansion if enabled (limit to primary k results to prevent bloat)
            if effective_config.parent_retrieval.enabled and results:
                results = self._apply_parent_expansion(
                    results,
                    effective_config.parent_retrieval,
                    max_results_to_expand=k,
                )

            # Post-expansion neural reranking: unify scoring across primary + ego results
            if (
                effective_config.reranker.single_pass
                and self.reranking_engine
                and results
            ):
                # Q3 single-pass: THE one listwise pass over the final merged
                # pool (hop-1 + multi-hop + ego expansion). Earlier per-stage
                # passes were skipped; truncate to k here (rerank_by_query
                # dedups split_block fragments before the cut).
                results = self.reranking_engine.rerank_by_query(
                    query=query,
                    results=results,
                    k=k,
                    search_mode=search_mode,
                    config=effective_config,
                )
            elif (
                effective_config.ego_graph.enabled
                and self.reranking_engine
                and len(results) > k
            ):
                # Default path: only runs when ego-graph added results, putting
                # all on the same cross-encoder scale
                results = self.reranking_engine.rerank_by_query(
                    query=query,
                    results=results,
                    k=len(results),  # Keep all results, just re-score and re-sort
                    search_mode=search_mode,
                    config=effective_config,
                )

            # Safety-net dedup for paths that bypass rerank_by_query (e.g.
            # single-hop with no ego growth): split_block fragments of one
            # function must not occupy multiple final slots. Idempotent when
            # rerank_by_query already deduped upstream.
            if effective_config.reranker.dedupe_split_blocks and results:
                results = dedupe_results(results)

            span.set_attribute(ATTR_RESULT_COUNT, len(results))
            return results

    def _single_hop_search(
        self,
        request: RetrievalRequest,
        query_embedding: np.ndarray | None = None,
    ) -> list[SearchResult]:
        """
        Internal single-hop search implementation (direct query matching).

        Delegates to SearchExecutor. Used as callback by MultiHopSearcher.

        Args:
            request: The RetrievalRequest this leg executes against.
            query_embedding: Pre-computed query embedding (optional, for caching)

        Returns:
            Search results from single-hop search
        """
        return self.search_executor.execute_single_hop(
            request, query_embedding=query_embedding
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
                # pyrefly: ignore [missing-attribute]
                self.ego_graph_retriever.expand_search_results(
                    search_results_dict, ego_config
                )
            )

            if not expanded_chunk_ids:
                return results

            # Score neighbors (embedding similarity + anchor-score decay)
            neighbor_results = self.ego_graph_retriever.score_neighbors(  # pyrefly: ignore [missing-attribute]
                results,
                ego_graphs,
                expanded_chunk_ids,
                query,
                ego_config,
                dense_index=self.dense_index,
                embedder=self.embedder,
            )

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

        except Exception as e:  # noqa: BLE001 - resilience: optional ego-graph expansion, return unexpanded results
            self._logger.warning(
                f"Ego-graph expansion failed: {e}. Returning original results.",
                exc_info=True,
            )
            return results

    def _apply_parent_expansion(
        self,
        results: list[SearchResult],
        config: "ParentRetrievalConfig",
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
                        if not config.include_parent_content:
                            metadata = {
                                k: v for k, v in metadata.items() if k != "content"
                            }
                        parent_results.append(
                            ResultFactory.from_expansion(
                                parent_id, 0.0, metadata, "parent_expansion"
                            )
                        )
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

        except Exception as e:  # noqa: BLE001 - resilience: optional parent expansion, return unexpanded results
            self._logger.warning(
                f"Parent expansion failed: {e}. Returning original results.",
                exc_info=True,
            )
            return results

    def find_similar_to_chunk(
        self,
        chunk_id: str,
        k: int = 5,
        rerank: bool = False,
        exclude_same_file: bool = False,
    ) -> list:
        """
        Find chunks similar to a given chunk using dense semantic search.

        Args:
            chunk_id: The ID of the reference chunk
            k: Number of similar chunks to return
            rerank: Whether to apply neural reranking (default: False)
            exclude_same_file: Drop candidates from the reference chunk's own
                file. Caller-supplied intent (cross-file analogues vs same-file
                siblings) — default False preserves existing behaviour.

        Returns:
            List of SearchResult objects with similar chunks
        """
        # Fetch more candidates when reranking to improve quality
        fetch_k = k * 2 if rerank else k
        similar_chunks = self.dense_index.get_similar_chunks(
            chunk_id, fetch_k, exclude_same_file=exclude_same_file
        )

        results = ResultFactory.from_similarity_results(similar_chunks)

        # Resolve once, same as HybridSearcher.search(): the config given at
        # construction, else the service-locator default (ADR-0018).
        effective_config = (
            self.config
            if self.config is not None
            else _get_config_via_service_locator()
        )

        # Apply neural reranking if requested and available
        if rerank and results:
            ref_metadata = self.dense_index.get_chunk_by_id(chunk_id)
            query_content = (
                ref_metadata.get("content_preview", "") if ref_metadata else ""
            )

            if query_content:
                self._logger.debug(
                    f"[RERANK-SIMILAR] Reranking {len(results)} candidates "
                    f"using reference chunk as query (length: {len(query_content)} chars)"
                )
                # Save original vector similarity scores — reranker overwrites .score
                # with the neural relevance score.
                similarity_by_id = {r.chunk_id: r.score for r in results}
                reranked = self.reranking_engine.apply_neural_reranking(
                    query_content,
                    results,
                    k,
                    context="similarity",
                    config=effective_config,
                )
                # Attach neural reranker_score to metadata; restore original vector
                # similarity as .score so downstream formatters display it consistently.
                for rr in reranked:
                    neural = rr.score
                    rr.score = similarity_by_id.get(rr.chunk_id, neural)
                    rr.metadata = {**(rr.metadata or {}), "reranker_score": neural}
                results = reranked
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

        # No per-call config here (this reports aggregate stats, not one
        # request) — resolve the same way HybridSearcher.search() does: the
        # config given at construction, else the service-locator default.
        effective_config = (
            self.config
            if self.config is not None
            else _get_config_via_service_locator()
        )

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
                "bm25_contribution": effective_config.search_mode.bm25_weight,
                "dense_contribution": effective_config.search_mode.dense_weight,
            },
        }

    def save_indices(self) -> None:
        """Save BM25, dense indices, and call graph. Delegates to IndexSynchronizer.

        The call graph save happens inside index_sync.save_indices() (via
        CodeIndexManager.save_index() -> GraphIntegration.save()) on the same
        CodeGraphStorage object as self._graph_storage (aliased at __init__ -
        see the "Reuse the CodeGraphStorage" comment above). A second explicit
        save here would just re-serialize the identical graph a moment later.
        """
        self.index_sync.save_indices()

    def validate_index_sync(self) -> bool:
        """Validate BM25 and Dense indices are synchronized. Delegates to IndexSynchronizer."""
        return self.index_sync.validate_index_sync()

    def resync_bm25_from_dense(self) -> int:
        """Rebuild BM25 index from dense index metadata. Delegates to IndexSynchronizer."""
        count = self.index_sync.resync_bm25_from_dense()
        # Sync modified bm25_index reference back
        self.bm25_index = self.index_sync.bm25_index
        return count

    def resync_if_desynced(self, log_prefix: str = "INCREMENTAL") -> tuple[bool, int]:
        """Auto-sync BM25 if >10% desync detected. Delegates to IndexSynchronizer."""
        result = self.index_sync.resync_if_desynced(log_prefix)
        # Sync modified bm25_index reference back (resync rebuilds the BM25 ref)
        self.bm25_index = self.index_sync.bm25_index
        return result

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
        documents: list[str] = []
        doc_ids = []
        embeddings = []
        metadata = {}

        for result in embedding_results:
            chunk_id = result.chunk_id
            doc_ids.append(chunk_id)

            # Extract text content for BM25 (from metadata or content)
            content = str(result.metadata.get("content") or "")
            if not content:
                # Fallback: try other content fields
                content = str(
                    result.metadata.get("content_preview")
                    or result.metadata.get("raw_content")
                    or ""
                )
            # BM25 documents get path/symbol augmentation at build time while
            # bm25_text below stays raw — resync_bm25_from_dense re-augments
            # from the raw text, so augmentation is applied exactly once no
            # matter how often the BM25 index is rebuilt.
            documents.append(augment_bm25_document(chunk_id, content))

            # Embeddings for dense index
            if hasattr(result.embedding, "tolist"):
                embeddings.append(result.embedding.tolist())
            else:
                embeddings.append(list(result.embedding))

            # Strip full `content` before persisting to MetadataStore (#55).
            # Full text is stored in bm25/_documents (populated above) and is not
            # needed at query time — content_preview (≤200 chars) covers snippet
            # display, and BM25 reconstructs text from its own _documents list.
            # Saves ~6 KB/chunk × 1755 chunks ≈ 10 MB of MetadataStore bloat.
            # Exception: persist a `bm25_text` field so resync_bm25_from_dense can
            # rebuild BM25 from dense authority when desync is detected.
            persisted_metadata = {
                k: v for k, v in result.metadata.items() if k != "content"
            }
            if content:
                persisted_metadata["bm25_text"] = content
            metadata[chunk_id] = persisted_metadata

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

            # Populate call graph via the GraphIntegration seam
            if self._graph is not None:
                self._graph.populate_from_embeddings(embedding_results)

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
            self._logger.debug("Closed reranking_engine metadata store before clear")

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

        # Update graph_storage reference to match new dense_index (prevents stale references).
        # NOTE: must be an explicit `is not None` check, not truthiness — GraphIntegration
        # defines __len__ (node count) but not __bool__, so a freshly-cleared, still-empty
        # graph is falsy and would silently skip this re-sync, leaving self._graph/_graph_storage
        # pointed at the orphaned pre-clear storage object for the rest of the reindex.
        if hasattr(self.dense_index, "_graph") and self.dense_index._graph is not None:
            self._graph_storage = self.dense_index._graph.storage
            self._graph = GraphIntegration.from_storage(self._graph_storage)
            # Re-wire the other two consumers bound at __init__ time
            # (_init_graph_components:337, :215-216). Without this they keep
            # pointing at the old, emptied CodeGraphStorage for the rest of
            # the process's life — silently zeroing ego-graph expansion and
            # degrading graph/hybrid multi-hop search until a restart.
            # ego_graph_retriever is reconstructed rather than patched in
            # place: EgoGraphRetriever.__init__ also builds a GraphView that
            # holds its own storage reference, so patching only `.graph`
            # would leave the PPR path reading the stale object. Rebuilding
            # also drops _centrality_scores, computed against the pre-clear
            # graph and re-injected per request anyway.
            if self._graph_storage is not None:
                self.ego_graph_retriever = EgoGraphRetriever(self._graph_storage)
            else:
                self.ego_graph_retriever = None
            self.multi_hop_searcher.graph_storage = self._graph_storage
            self._logger.debug(
                "[CLEAR] Updated graph_storage reference after clear_index()"
            )

        # Evict the metadata cache: stale entries (including cached-None lookups)
        # from before the clear would otherwise survive and return wrong results
        # after re-indexing the same file paths (#44).
        self._metadata_cache.clear()
        self._logger.debug("[CLEAR] Metadata cache cleared after clear_index()")

    def remove_files(self, file_paths: set[str], project_name: str) -> int:
        """Remove chunks for one or more files. Delegates to IndexSynchronizer."""
        removed = self.index_sync.remove_files(file_paths, project_name)
        # Evict all cache entries — removed chunk ids could be reused after
        # re-indexing the same file; a cached-None or stale hit would be wrong (#44).
        if removed > 0:
            self._metadata_cache.clear()
        return removed

    def _verify_bm25_files(self) -> None:
        """Verify BM25 files exist and are non-empty. Delegates to IndexSynchronizer."""
        self.index_sync._verify_bm25_files()
