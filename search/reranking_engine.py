"""Reranking engine for result quality improvement.

Coordinates both embedding-based reranking and neural reranking
for search result quality improvement.
"""

import logging
import time
from typing import List, Optional

import numpy as np

try:
    import torch
except ImportError:
    torch = None

from .neural_reranker import NeuralReranker


class RerankingEngine:
    """Coordinates embedding-based and neural reranking for search results."""

    def __init__(self, embedder, metadata_store):
        """
        Initialize the reranking engine.

        Args:
            embedder: CodeEmbedder instance for query embeddings
            metadata_store: MetadataStore for chunk metadata retrieval
        """
        self.embedder = embedder
        self.metadata_store = metadata_store
        self.neural_reranker: Optional[NeuralReranker] = None
        self._neural_reranking_enabled: Optional[bool] = None
        self._logger = logging.getLogger(__name__)

    def should_enable_neural_reranking(self) -> bool:
        """Check if VRAM is sufficient for neural reranking.

        Returns:
            bool: True if VRAM is sufficient and feature is enabled
        """
        try:
            from .config import get_search_config

            config = get_search_config()
            if not hasattr(config, "reranker") or not config.reranker.enabled:
                return False

            min_vram = config.reranker.min_vram_gb
            if not torch or not torch.cuda.is_available():
                self._logger.warning("Neural reranking disabled: No GPU available")
                return False

            available_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            # Account for already allocated memory
            allocated_gb = torch.cuda.memory_allocated() / (1024**3)
            free_gb = available_gb - allocated_gb

            if free_gb >= min_vram:
                self._logger.info(
                    f"Neural reranking enabled: {free_gb:.1f}GB available >= {min_vram}GB required"
                )
                return True
            else:
                self._logger.warning(
                    f"Neural reranking disabled: {free_gb:.1f}GB available < {min_vram}GB required"
                )
                return False
        except Exception as e:
            self._logger.warning(f"VRAM check failed, disabling neural reranking: {e}")
            return False

    def rerank_by_query(
        self,
        query: str,
        results: List,
        k: int,
        search_mode: str = "hybrid",
        query_embedding: Optional[np.ndarray] = None,
    ) -> List:
        """
        Re-rank results by computing fresh relevance scores against the original query.

        Args:
            query: Original search query
            results: List of SearchResult objects to re-rank
            k: Number of top results to return
            search_mode: Search mode for re-ranking strategy
            query_embedding: Pre-computed query embedding (optional)

        Returns:
            Top k results sorted by query relevance
        """
        if not results:
            return []

        # For semantic/hybrid modes: re-score using dense similarity
        if search_mode in ("semantic", "hybrid") and self.embedder:
            try:
                # Get query embedding (use cached if provided)
                if query_embedding is None:
                    query_embedding = self.embedder.embed_query(query)

                # Re-score each result by cosine similarity to query
                for result in results:
                    # Get chunk embedding from dense index
                    chunk_id = result.chunk_id
                    chunk_metadata = self.metadata_store.get(chunk_id)
                    if chunk_metadata and "embedding" in chunk_metadata:
                        chunk_emb = np.array(chunk_metadata["embedding"])
                        # Compute cosine similarity
                        similarity = np.dot(query_embedding, chunk_emb) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(chunk_emb)
                        )
                        result.score = float(similarity)
                    # Keep original score if embedding not found

            except Exception as e:
                self._logger.warning(
                    f"[RERANK] Failed to re-score with embeddings: {e}, "
                    "keeping original scores"
                )

        # Sort by score (descending)
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)

        # Neural reranking (Quality First mode)
        # Always re-check config to pick up runtime changes
        if len(sorted_results) > 0:
            should_enable = self.should_enable_neural_reranking()

            # Handle state transitions
            if should_enable and self.neural_reranker is None:
                # Initialize reranker (lazy load)
                from .config import get_search_config

                config = get_search_config()
                self.neural_reranker = NeuralReranker(
                    model_name=config.reranker.model_name,
                    batch_size=config.reranker.batch_size,
                )
                self._logger.debug("[RERANK] Neural reranker initialized")
            elif not should_enable and self.neural_reranker is not None:
                # Cleanup when disabled
                self.neural_reranker.cleanup()
                self.neural_reranker = None
                self._logger.debug("[RERANK] Neural reranker disabled and cleaned up")

            self._neural_reranking_enabled = should_enable

            # Proceed with reranking if enabled
            if self._neural_reranking_enabled and self.neural_reranker:
                neural_start = time.time()
                from .config import get_search_config

                config = get_search_config()
                rerank_count = min(
                    config.reranker.top_k_candidates, len(sorted_results)
                )
                sorted_results = self.neural_reranker.rerank(
                    query, sorted_results[:rerank_count], k
                )
                neural_time = time.time() - neural_start
                self._logger.debug(
                    f"[NEURAL_RERANK] Processed {rerank_count} candidates in {neural_time:.3f}s"
                )

        return sorted_results[:k]

    def shutdown(self) -> None:
        """Cleanup neural reranker resources."""
        if self.neural_reranker:
            self.neural_reranker.cleanup()
            self.neural_reranker = None
            self._logger.debug("Neural reranker cleaned up")
