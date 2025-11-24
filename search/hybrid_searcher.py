"""Hybrid search orchestrator combining BM25 + dense search with GPU awareness."""

import concurrent.futures
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import torch
except ImportError:
    torch = None

from .bm25_index import BM25Index
from .filters import matches_directory_filter
from .indexer import CodeIndexManager
from .reranker import RRFReranker, SearchResult


class GPUMemoryMonitor:
    """Monitor GPU memory usage for optimal batch sizing."""

    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def get_available_memory(self) -> Dict[str, int]:
        """Get available memory in bytes."""
        memory_info = {"gpu_available": 0, "gpu_total": 0, "gpu_utilization": 0.0}

        if torch and torch.cuda.is_available():
            try:
                device = torch.cuda.current_device()
                gpu_memory = torch.cuda.mem_get_info(device)
                memory_info["gpu_available"] = gpu_memory[0]
                memory_info["gpu_total"] = gpu_memory[1]
                memory_info["gpu_utilization"] = 1.0 - (gpu_memory[0] / gpu_memory[1])
            except Exception as e:
                self._logger.warning(f"Failed to get GPU memory info: {e}")

        return memory_info

    def can_use_gpu(self, required_memory: int = 1024 * 1024 * 1024) -> bool:
        """Check if GPU can be used for operations."""
        if not torch or not torch.cuda.is_available():
            return False

        memory_info = self.get_available_memory()
        return memory_info["gpu_available"] > required_memory

    def estimate_batch_memory(self, batch_size: int, embedding_dim: int = 768) -> int:
        """Estimate memory usage for a batch."""
        # float32 = 4 bytes, plus overhead
        return batch_size * embedding_dim * 4 * 2  # 2x safety margin


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
            project_id: Project identifier for graph storage (Phase 1: Python call graphs)
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Store embedder for semantic search
        self.embedder = embedder

        # Store project_id for graph storage (Phase 1)
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

        self.reranker = RRFReranker(k=rrf_k)
        self.gpu_monitor = GPUMemoryMonitor()

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def shutdown(self):
        """Shutdown the thread pool and cleanup resources."""
        with self._shutdown_lock:
            if not self._is_shutdown:
                self._thread_pool.shutdown(wait=True)
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
                    "on_gpu": getattr(self.dense_index, "_on_gpu", False),
                },
                "gpu_memory": self.gpu_monitor.get_available_memory(),
            }
        )

        return stats

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics in the format expected by MCP server."""
        bm25_count = self.bm25_index.size
        dense_count = self.dense_index.index.ntotal if self.dense_index.index else 0
        total_chunks = max(bm25_count, dense_count)  # Use the higher count as total

        return {
            "total_chunks": total_chunks,
            "bm25_documents": bm25_count,
            "dense_vectors": dense_count,
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

        Phase 1.1 Feature: Enables O(1) symbol lookups using chunk_id from previous results.

        Args:
            chunk_id: Format "file.py:10-20:function:name"

        Returns:
            SearchResult if found, None otherwise
        """
        # Get metadata from dense index
        metadata = self.dense_index.get_chunk_by_id(chunk_id)
        if not metadata:
            return None

        # Normalize metadata to ensure 'file' key exists
        # (metadata may have 'file_path' or 'relative_path' instead)
        if "file" not in metadata:
            metadata["file"] = metadata.get(
                "file_path", metadata.get("relative_path", "")
            )

        # Create SearchResult with score 1.0 (exact match)
        # Use the reranker's SearchResult format: (chunk_id, score, metadata, source, rank)
        result = SearchResult(
            chunk_id=chunk_id,
            score=1.0,
            metadata=metadata,
            source="direct_lookup",
            rank=0,
        )

        return result

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
        from .config import get_search_config

        config = get_search_config()

        if config.enable_multi_hop:
            # Use multi-hop search for discovering related code
            return self._multi_hop_search_internal(
                query=query,
                k=k,
                search_mode=search_mode,
                hops=config.multi_hop_count,
                expansion_factor=config.multi_hop_expansion,
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
            dense_results = self._search_dense(query, k, filters)
            # Convert dense results to SearchResult format
            final_results = self._convert_dense_to_search_results(dense_results)
            rerank_time = 0.0  # No reranking for single mode

        else:  # hybrid mode
            search_k = k * 2  # Get more results for better reranking

            if use_parallel and not self._is_shutdown:
                # Parallel execution
                bm25_results, dense_results = self._parallel_search(
                    query, search_k, min_bm25_score, filters
                )
            else:
                # Sequential execution
                bm25_results, dense_results = self._sequential_search(
                    query, search_k, min_bm25_score, filters
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

    def find_similar_to_chunk(self, chunk_id: str, k: int = 5) -> List:
        """
        Find chunks similar to a given chunk using dense semantic search.

        Args:
            chunk_id: The ID of the reference chunk
            k: Number of similar chunks to return

        Returns:
            List of SearchResult objects with similar chunks
        """
        from .searcher import SearchResult

        # Use dense index for semantic similarity
        similar_chunks = self.dense_index.get_similar_chunks(chunk_id, k)

        # Convert to SearchResult format expected by MCP tool
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
            )
            results.append(result)

        return results

    def _validate_multi_hop_params(
        self, hops: int, expansion_factor: float
    ) -> Tuple[int, float]:
        """
        Validate and sanitize multi-hop search parameters.

        Args:
            hops: Number of search hops requested
            expansion_factor: Expansion factor per hop

        Returns:
            Tuple of (validated_hops, validated_expansion_factor)
        """
        validated_hops = hops
        validated_expansion = expansion_factor

        if hops < 1:
            self._logger.warning(f"Invalid hops={hops}, using 1")
            validated_hops = 1

        if expansion_factor < 0 or expansion_factor > 2.0:
            self._logger.warning(
                f"Invalid expansion_factor={expansion_factor}, using 0.3"
            )
            validated_expansion = 0.3

        return validated_hops, validated_expansion

    def _expand_from_initial_results(
        self,
        initial_results: List,
        all_chunk_ids: set,
        all_results: Dict,
        expansion_k: int,
        hops: int,
        k: int,
    ) -> Dict[int, float]:
        """
        Expand search results by finding similar chunks for each initial result.

        Args:
            initial_results: Results from initial search (hop 1)
            all_chunk_ids: Set of already discovered chunk IDs (modified in-place)
            all_results: Dict of chunk_id -> result (modified in-place)
            expansion_k: Number of similar chunks to find per result
            hops: Total number of hops to perform
            k: Original k value for limiting expansion sources

        Returns:
            Dict mapping hop number to duration in seconds
        """
        from .reranker import SearchResult as RerankerSearchResult

        expansion_timings = {}

        for hop in range(2, hops + 1):
            hop_start = time.time()
            hop_discovered = 0

            # Expand from top initial results only (not from previously expanded)
            source_results = initial_results[:k]

            for result in source_results:
                try:
                    # Find similar chunks to this result
                    similar_chunks = self.find_similar_to_chunk(
                        chunk_id=result.chunk_id,
                        k=expansion_k,
                    )

                    # Add new chunks
                    for sim_result in similar_chunks:
                        chunk_id = sim_result.chunk_id
                        if chunk_id not in all_chunk_ids:
                            all_chunk_ids.add(chunk_id)
                            # Convert to reranker.SearchResult format
                            reranker_result = RerankerSearchResult(
                                chunk_id=chunk_id,
                                score=sim_result.similarity_score,
                                metadata=sim_result.__dict__,
                                source="multi_hop",
                            )
                            all_results[chunk_id] = reranker_result
                            hop_discovered += 1

                except Exception as e:
                    self._logger.warning(
                        f"[MULTI_HOP] Failed to find similar chunks for {result.chunk_id}: {e}"
                    )
                    continue

            expansion_timings[hop] = time.time() - hop_start

            self._logger.info(
                f"[MULTI_HOP] Hop {hop}: Discovered {hop_discovered} new chunks "
                f"(total: {len(all_results)}, {expansion_timings[hop] * 1000:.1f}ms)"
            )

        return expansion_timings

    def _apply_post_expansion_filters(
        self,
        all_results: Dict,
        initial_results_count: int,
        filters: Optional[Dict[str, Any]],
    ) -> Dict:
        """
        Apply filters to expanded results.

        Args:
            all_results: Dict of chunk_id -> result
            initial_results_count: Number of initial results (before expansion)
            filters: Optional filters to apply

        Returns:
            Filtered results dict
        """
        if not filters or len(all_results) <= initial_results_count:
            return all_results

        filtered_results = {}
        for chunk_id, result in all_results.items():
            # Get metadata from dense index
            metadata_entry = self.dense_index.metadata_db.get(chunk_id)
            if metadata_entry:
                metadata = metadata_entry.get("metadata", {})
                if self.dense_index._matches_filters(metadata, filters):
                    filtered_results[chunk_id] = result
            else:
                # Keep results without metadata (shouldn't happen)
                filtered_results[chunk_id] = result

        removed_count = len(all_results) - len(filtered_results)
        self._logger.info(
            f"[MULTI_HOP] Applied filters: {len(filtered_results)} results remain "
            f"({removed_count} removed)"
        )

        return filtered_results

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

        Discovers interconnected code relationships by:
        1. Initial query-based search (Hop 1)
        2. Finding similar chunks for each result (Hop 2+)
        3. Re-ranking all discovered chunks by query relevance

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
        # Validate parameters
        hops, expansion_factor = self._validate_multi_hop_params(hops, expansion_factor)

        # Initialize timing tracker
        timings = {
            "total": time.time(),
            "hop_1": 0,
            "expansion": {},
            "rerank": 0,
        }

        self._logger.info(
            f"[MULTI_HOP] Starting {hops}-hop search for '{query}' "
            f"(k={k}, expansion={expansion_factor}, mode={search_mode})"
        )

        # Hop 1: Initial query-based search
        from .config import SearchConfigManager

        config = SearchConfigManager().load_config()
        initial_k = int(k * config.multi_hop_initial_k_multiplier)

        hop1_start = time.time()
        initial_results = self._single_hop_search(
            query=query,
            k=initial_k,
            search_mode=search_mode,
            use_parallel=use_parallel,
            min_bm25_score=min_bm25_score,
            filters=filters,
        )
        timings["hop_1"] = time.time() - hop1_start

        if not initial_results:
            self._logger.info("[MULTI_HOP] No initial results found")
            return []

        self._logger.info(
            f"[MULTI_HOP] Hop 1: Found {len(initial_results)} initial results "
            f"({timings['hop_1'] * 1000:.1f}ms)"
        )

        # Track all discovered chunks
        all_chunk_ids = {r.chunk_id for r in initial_results}
        all_results = {r.chunk_id: r for r in initial_results}

        # If only 1 hop requested, return initial results
        if hops == 1:
            return initial_results[:k]

        # Hop 2+: Expand from initial results
        expansion_k = max(1, int(k * expansion_factor))
        timings["expansion"] = self._expand_from_initial_results(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=expansion_k,
            hops=hops,
            k=k,
        )

        # Apply filters to expanded results
        all_results = self._apply_post_expansion_filters(
            all_results=all_results,
            initial_results_count=len(initial_results),
            filters=filters,
        )

        # Re-rank all discovered results by query relevance
        self._logger.info(
            f"[MULTI_HOP] Re-ranking {len(all_results)} total chunks by query relevance"
        )

        rerank_start = time.time()
        final_results = self._rerank_by_query(
            query=query,
            results=list(all_results.values()),
            k=k,
            search_mode=search_mode,
        )

        timings["rerank"] = time.time() - rerank_start

        # Final summary
        timings["total"] = time.time() - timings["total"]
        expansion_time = (
            sum(timings["expansion"].values()) if timings["expansion"] else 0
        )

        self._logger.info(
            f"[MULTI_HOP] Complete: {len(final_results)} results | "
            f"Total={timings['total'] * 1000:.0f}ms "
            f"(Hop1={timings['hop_1'] * 1000:.0f}ms, "
            f"Expansion={expansion_time * 1000:.0f}ms, "
            f"Rerank={timings['rerank'] * 1000:.0f}ms)"
        )

        return final_results

    def _rerank_by_query(
        self, query: str, results: List, k: int, search_mode: str = "hybrid"
    ) -> List:
        """
        Re-rank results by computing fresh relevance scores against the original query.

        Args:
            query: Original search query
            results: List of SearchResult objects to re-rank
            k: Number of top results to return
            search_mode: Search mode for re-ranking strategy

        Returns:
            Top k results sorted by query relevance
        """
        if not results:
            return []

        # For semantic/hybrid modes: re-score using dense similarity
        if search_mode in ("semantic", "hybrid") and self.embedder:
            try:
                # Get query embedding
                query_embedding = self.embedder.embed_query(query)

                # Re-score each result by cosine similarity to query
                import numpy as np

                for result in results:
                    # Get chunk embedding from dense index
                    # reranker.SearchResult now uses chunk_id
                    chunk_id = result.chunk_id
                    chunk_metadata = self.dense_index.metadata_db.get(chunk_id)
                    if chunk_metadata and "embedding" in chunk_metadata:
                        chunk_emb = np.array(chunk_metadata["embedding"])
                        # Compute cosine similarity
                        similarity = np.dot(query_embedding, chunk_emb) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(chunk_emb)
                        )
                        # reranker.SearchResult uses score, not similarity_score
                        result.score = float(similarity)
                    # Keep original score if embedding not found

            except Exception as e:
                self._logger.warning(
                    f"[MULTI_HOP] Failed to re-score with embeddings: {e}, "
                    "keeping original scores"
                )

        # Sort by score (descending)
        # reranker.SearchResult uses score, not similarity_score
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

        return sorted_results[:k]

    def _parallel_search(
        self,
        query: str,
        k: int,
        min_bm25_score: float,
        filters: Optional[Dict[str, Any]],
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """Execute BM25 and dense search in parallel."""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both searches
                bm25_future = executor.submit(
                    self._search_bm25, query, k, min_bm25_score, filters
                )
                dense_future = executor.submit(self._search_dense, query, k, filters)

                # Wait for results
                bm25_results = bm25_future.result()
                dense_results = dense_future.result()

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
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """Execute BM25 and dense search sequentially."""
        bm25_results = self._search_bm25(query, k, min_bm25_score, filters)
        dense_results = self._search_dense(query, k, filters)
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

                    if self._matches_bm25_filters(metadata, filters):
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

    def _matches_bm25_filters(self, metadata: Dict, filters: Dict) -> bool:
        """Check if BM25 result metadata matches filters."""
        for key, value in filters.items():
            if key == "include_dirs" or key == "exclude_dirs":
                # Directory filtering - handled together
                include_dirs = filters.get("include_dirs")
                exclude_dirs = filters.get("exclude_dirs")
                relative_path = metadata.get("relative_path", "")
                if not matches_directory_filter(
                    relative_path, include_dirs, exclude_dirs
                ):
                    return False
                # Skip further processing of these keys
                continue
            elif key == "file_pattern":
                # Pattern matching for file paths (substring match)
                patterns = value if isinstance(value, list) else [value]
                relative_path = metadata.get("relative_path", "")
                if not any(pattern in relative_path for pattern in patterns):
                    return False
            elif key == "chunk_type":
                # Exact match for chunk type
                if metadata.get("chunk_type") != value:
                    return False
            elif key == "tags":
                # Tag intersection
                chunk_tags = set(metadata.get("tags", []))
                required_tags = set(value if isinstance(value, list) else [value])
                if not required_tags.intersection(chunk_tags):
                    return False
        return True

    def _search_dense(self, query: str, k: int, filters: Optional[Dict]) -> List[Tuple]:
        """Search using dense vector index."""
        start_time = time.time()
        try:
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

    def _convert_bm25_to_search_results(
        self, bm25_results: List[Tuple]
    ) -> List[SearchResult]:
        """Convert BM25 search results to SearchResult format."""
        search_results = []
        for i, (chunk_id, score, metadata) in enumerate(bm25_results):
            search_result = SearchResult(
                chunk_id=chunk_id, score=score, metadata=metadata, source="bm25", rank=i
            )
            search_results.append(search_result)
        return search_results

    def _convert_dense_to_search_results(
        self, dense_results: List[Tuple]
    ) -> List[SearchResult]:
        """Convert dense search results to SearchResult format."""
        search_results = []
        for i, (chunk_id, score, metadata) in enumerate(dense_results):
            search_result = SearchResult(
                chunk_id=chunk_id,
                score=score,
                metadata=metadata,
                source="semantic",
                rank=i,
            )
            search_results.append(search_result)
        return search_results

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
        """Save both BM25 and dense indices."""
        try:
            self._logger.info("[SAVE] Starting save operation")

            # Log comprehensive state before save
            bm25_dir = self.storage_dir / "bm25"
            dense_size = self.dense_index.index.ntotal if self.dense_index.index else 0

            self._logger.info("[SAVE] === PRE-SAVE STATE ===")
            self._logger.info(f"[SAVE] BM25 directory exists: {bm25_dir.exists()}")
            self._logger.info(
                f"[SAVE] BM25 index size: {self.bm25_index.size} documents"
            )
            self._logger.info(
                f"[SAVE] BM25 has index: {self.bm25_index._bm25 is not None}"
            )
            self._logger.info(
                f"[SAVE] BM25 tokenized docs: {len(self.bm25_index._tokenized_docs)}"
            )
            self._logger.info(f"[SAVE] Dense index size: {dense_size} vectors")
            self._logger.info(
                f"[SAVE] Dense has index: {self.dense_index.index is not None}"
            )
            self._logger.info(f"[SAVE] Overall ready state: {self.is_ready}")
            self._logger.info("[SAVE] === END PRE-SAVE STATE ===")

            # Log BM25 state before save (keep original logging for compatibility)
            self._logger.info(f"[SAVE] BM25 size before save: {self.bm25_index.size}")

            # Save BM25 index
            if hasattr(self.bm25_index, "save"):
                self._logger.info("[SAVE] Calling BM25 index save...")
                self.bm25_index.save()
                self._logger.info("[SAVE] BM25 index save completed")
            else:
                self._logger.warning("[SAVE] BM25 index does not support saving")

            # Save dense index
            if hasattr(self.dense_index, "save_index"):
                self._logger.info("[SAVE] Calling dense index save_index...")
                self.dense_index.save_index()
                self._logger.info("[SAVE] Dense index save completed")
            elif hasattr(self.dense_index, "save"):
                self._logger.info("[SAVE] Calling dense index save...")
                self.dense_index.save()
                self._logger.info("[SAVE] Dense index save completed")
            else:
                self._logger.warning("[SAVE] Dense index does not support saving")

            # Verify files after save
            self._verify_bm25_files()

            # Log comprehensive state after save
            bm25_dir = self.storage_dir / "bm25"
            dense_size_after = (
                self.dense_index.index.ntotal if self.dense_index.index else 0
            )

            self._logger.info("[SAVE] === POST-SAVE STATE ===")
            self._logger.info(f"[SAVE] BM25 directory exists: {bm25_dir.exists()}")
            if bm25_dir.exists():
                files = list(bm25_dir.iterdir())
                self._logger.info(f"[SAVE] BM25 files: {[f.name for f in files]}")
            self._logger.info(
                f"[SAVE] BM25 index size: {self.bm25_index.size} documents"
            )
            self._logger.info(
                f"[SAVE] BM25 has index: {self.bm25_index._bm25 is not None}"
            )
            self._logger.info(f"[SAVE] Dense index size: {dense_size_after} vectors")
            self._logger.info(
                f"[SAVE] Dense has index: {self.dense_index.index is not None}"
            )
            self._logger.info(f"[SAVE] Overall ready state: {self.is_ready}")
            self._logger.info("[SAVE] === END POST-SAVE STATE ===")

            self._logger.info("[SAVE] Hybrid indices saved successfully")
        except Exception as e:
            self._logger.error(f"[SAVE] Failed to save indices: {e}")
            raise

    def load_indices(self) -> bool:
        """Load both BM25 and dense indices."""
        try:
            bm25_loaded = self.bm25_index.load()
            dense_loaded = self.dense_index.load()

            success = bm25_loaded and dense_loaded
            if success:
                self._logger.info("Hybrid indices loaded successfully")
            else:
                self._logger.warning(
                    f"Index loading partial: BM25={bm25_loaded}, Dense={dense_loaded}"
                )

            return success

        except Exception as e:
            self._logger.error(f"Failed to load indices: {e}")
            return False

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
        """
        Clear both BM25 and dense indices.
        Compatible with incremental indexer interface.
        """
        self._logger.info("Clearing hybrid indices")

        try:
            # Clear BM25 index by recreating it with same configuration
            self.bm25_index = BM25Index(
                str(self.storage_dir / "bm25"),
                use_stopwords=self.bm25_use_stopwords,
                use_stemming=self.bm25_use_stemming,
            )

            # Clear dense index by recreating it (preserve project_id for graph storage)
            self.dense_index = CodeIndexManager(
                str(self.storage_dir), project_id=self.project_id
            )

            self._logger.info("Successfully cleared hybrid indices")
        except Exception as e:
            self._logger.error(f"Failed to clear hybrid indices: {e}")
            raise

    def remove_file_chunks(self, file_path: str, project_name: str) -> int:
        """
        Remove chunks for a specific file from both indices.
        Compatible with incremental indexer interface.

        Args:
            file_path: Relative path of the file
            project_name: Name of the project

        Returns:
            Number of chunks removed
        """
        self._logger.debug(f"Removing chunks for file: {file_path}")

        try:
            removed_count = 0

            # Remove from dense index
            if hasattr(self.dense_index, "remove_file_chunks"):
                removed_dense = self.dense_index.remove_file_chunks(
                    file_path, project_name
                )
                removed_count += removed_dense
                self._logger.debug(f"Removed {removed_dense} chunks from dense index")

            # Remove from BM25 index
            if hasattr(self.bm25_index, "remove_file_chunks"):
                removed_bm25 = self.bm25_index.remove_file_chunks(
                    file_path, project_name
                )
                removed_count += removed_bm25
                self._logger.debug(f"Removed {removed_bm25} chunks from BM25 index")
            else:
                self._logger.warning("BM25 index does not support file chunk removal")

            self._logger.info(
                f"Removed {removed_count} total chunks for file: {file_path}"
            )
            return removed_count

        except Exception as e:
            self._logger.error(f"Failed to remove chunks for file {file_path}: {e}")
            return 0

    def remove_multiple_files(self, file_paths: set, project_name: str) -> int:
        """
        Remove chunks for multiple files from both indices in a single pass.
        Much faster than calling remove_file_chunks repeatedly.

        IMPORTANT: This method properly removes chunks from both FAISS and BM25 indices,
        preventing index corruption.

        Args:
            file_paths: Set of file paths to remove
            project_name: Name of the project

        Returns:
            Total number of chunks removed
        """
        self._logger.info(
            f"Batch removing chunks for {len(file_paths)} files from hybrid indices"
        )

        removed_count = 0
        dense_failed = False
        bm25_failed = False

        # Remove from dense index
        if hasattr(self.dense_index, "remove_multiple_files"):
            try:
                removed_dense = self.dense_index.remove_multiple_files(
                    file_paths, project_name
                )
                removed_count += removed_dense
                self._logger.info(
                    f"Batch removed {removed_dense} chunks from dense (FAISS) index"
                )
            except Exception as e:
                self._logger.error(f"Failed to batch remove from dense index: {e}")
                import traceback

                self._logger.error(traceback.format_exc())
                dense_failed = True

        # Remove from BM25 index
        if hasattr(self.bm25_index, "remove_multiple_files"):
            try:
                removed_bm25 = self.bm25_index.remove_multiple_files(
                    file_paths, project_name
                )
                removed_count += removed_bm25
                self._logger.info(
                    f"Batch removed {removed_bm25} chunks from BM25 index"
                )
            except Exception as e:
                self._logger.error(f"Failed to batch remove from BM25 index: {e}")
                import traceback

                self._logger.error(traceback.format_exc())
                bm25_failed = True
        else:
            self._logger.warning("BM25 index does not support batch file chunk removal")

        # If both failed, raise exception to trigger error recovery
        if dense_failed and bm25_failed:
            raise RuntimeError(
                "Batch removal failed for both dense and BM25 indices. "
                "Indices may be in corrupted state."
            )

        self._logger.info(
            f"Batch removed {removed_count} total chunks for {len(file_paths)} files"
        )
        return removed_count

    def save_index(self) -> None:
        """
        Save both BM25 and dense indices to disk.
        Compatible with incremental indexer interface.
        """
        self._logger.info("Saving hybrid indices")

        try:
            # Save both indices
            self.save_indices()
            self._logger.info("Successfully saved hybrid indices")
        except Exception as e:
            self._logger.error(f"Failed to save hybrid indices: {e}")
            raise

    def _verify_bm25_files(self):
        """Verify BM25 files exist and are non-empty."""
        bm25_dir = Path(self.bm25_index.storage_dir)
        expected_files = ["bm25.index", "bm25_docs.json", "bm25_metadata.json"]

        self._logger.info(f"[VERIFY] Checking BM25 files in: {bm25_dir}")

        for filename in expected_files:
            filepath = bm25_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                if size == 0:
                    self._logger.error(f"[VERIFY] {filename} exists but is EMPTY")
                else:
                    self._logger.info(f"[VERIFY] {filename}: {size} bytes")
            else:
                self._logger.error(f"[VERIFY] {filename} does NOT exist")

        # Log overall BM25 directory status
        if bm25_dir.exists():
            files = list(bm25_dir.iterdir())
            self._logger.info(
                f"[VERIFY] BM25 files after save: {[f.name for f in files]}"
            )
            for f in files:
                self._logger.info(f"[VERIFY] {f.name}: {f.stat().st_size} bytes")
        else:
            self._logger.error("[VERIFY] BM25 directory does not exist after save!")
