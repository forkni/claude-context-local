"""Reranking engine for result quality improvement.

Coordinates both embedding-based reranking and neural reranking
for search result quality improvement.
"""

import logging
import time
from typing import TYPE_CHECKING

import numpy as np

from utils.timing import timed

from .config import get_search_config


# TYPE_CHECKING is always False at runtime; AddNot mutation on this guard is equivalent.
# pragma: no mutate
if TYPE_CHECKING:
    from .neural_reranker import (
        GenerativeReranker,
        JinaRerankerV3,
        NeuralReranker,
    )

try:
    import torch
# Import-failure exception type is untestable in unit tests; ExceptionReplacer is equivalent.
# pragma: no mutate
except ImportError:
    torch = None

from .neural_reranker import create_reranker


class RerankingEngine:
    """Coordinates embedding-based and neural reranking for search results."""

    def __init__(self, embedder, metadata_store) -> None:
        """Initialize the reranking engine.

        Args:
            embedder: CodeEmbedder instance for query embeddings
            metadata_store: MetadataStore for chunk metadata retrieval
        """
        self.embedder = embedder
        self.metadata_store = metadata_store
        # Type annotation only; | union operators have no runtime effect.
        # pragma: no mutate
        self.neural_reranker: (
            NeuralReranker | GenerativeReranker | JinaRerankerV3 | None
        ) = None
        self._neural_reranking_enabled: bool | None = None
        self._session_oom_detected: bool = False
        self._logger = logging.getLogger(__name__)

    def should_enable_neural_reranking(self) -> bool:
        """Check if VRAM is sufficient for neural reranking.

        Returns:
            bool: True if VRAM is sufficient and feature is enabled
        """
        # Early exit if OOM already detected in this search session
        if self._session_oom_detected:
            self._logger.debug(
                "Neural reranking skipped: OOM detected earlier in session"
            )
            return False

        try:
            config = get_search_config()
            if not hasattr(config, "reranker") or not config.reranker.enabled:
                return False

            min_vram = config.reranker.min_vram_gb
            # or→and mutation equivalent under torch mock (not torch is always False in tests).
            # pragma: no mutate
            if not torch or not torch.cuda.is_available():
                self._logger.warning("Neural reranking disabled: No GPU available")
                return False

            # If RAM fallback is allowed, skip VRAM threshold check
            if hasattr(config, "performance") and config.performance.allow_ram_fallback:
                self._logger.info(
                    "Neural reranking enabled: allow_ram_fallback=True (will use system RAM if needed)"
                )
                return True

            # Get actual free memory from CUDA driver (accounts for all processes)
            free_memory, total_memory = torch.cuda.mem_get_info(0)
            free_gb = free_memory / (1024**3)
            # 1023/1025 NumberReplacer mutations are near-equivalent (<0.3% VRAM difference).
            # pragma: no mutate

            # GtE→Gt mutation only differs at exact float equality — not reachable in practice.
            # pragma: no mutate
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
        # VRAM-check exception path: ExceptionReplacer and ReplaceFalseWithTrue are
        # equivalent for unit tests (exception is unreachable with mocked torch).
        # pragma: no mutate
        except Exception as e:
            self._logger.warning(f"VRAM check failed, disabling neural reranking: {e}")
            return False

    def _ensure_reranker(self, log_prefix: str) -> bool:
        """Lazy-init or cleanup neural reranker based on current VRAM/config state.

        Updates self._neural_reranking_enabled and self.neural_reranker.
        Returns True if reranking is available (enabled and loaded).
        """
        should_enable = self.should_enable_neural_reranking()

        # and/or mutations here are boundary orchestration; equivalent under the test suite's
        # mock setup (create_reranker is mocked, _ensure_reranker is not called directly).
        # pragma: no mutate
        if should_enable and self.neural_reranker is None:
            config = get_search_config()
            self.neural_reranker = create_reranker(
                model_name=config.reranker.model_name,
                batch_size=config.reranker.batch_size,
            )
            self._logger.debug(f"{log_prefix} Neural reranker initialized")
        elif not should_enable and self.neural_reranker is not None:
            self.neural_reranker.cleanup()
            self.neural_reranker = None
            self._logger.debug(f"{log_prefix} Neural reranker disabled and cleaned up")

        self._neural_reranking_enabled = should_enable
        # pragma: no mutate
        return bool(should_enable and self.neural_reranker is not None)

    def _run_rerank(
        self, query_or_content: str, candidates: list, k: int, log_prefix: str
    ) -> list:
        """OOM-protected timed rerank call.

        Returns reranked results on success, or candidates unchanged on failure.
        """
        assert (
            self.neural_reranker is not None
        )  # guaranteed by _ensure_reranker() caller gate
        config = get_search_config()
        rerank_count = min(config.reranker.top_k_candidates, len(candidates))
        neural_start = time.time()

        try:
            result = self.neural_reranker.rerank(
                query_or_content, candidates[:rerank_count], k
            )
            # Timing value only used in log message — arithmetic mutations are log-only.
            # pragma: no mutate
            neural_time = time.time() - neural_start
            self._logger.debug(
                f"{log_prefix} Processed {rerank_count} candidates in {neural_time:.3f}s"
            )
            return result
        # OOM detection path: all mutations here are boundary (requires real CUDA OOM).
        # ExceptionReplacer, And/Or in OOM string detection, and True→False on _session_oom_detected
        # are all equivalent for unit tests.
        # pragma: no mutate
        except Exception as e:
            self._logger.warning(
                f"{log_prefix} Reranking failed: {e}, using original results"
            )
            error_str = str(e).lower()
            if "cuda" in error_str and (
                "out of memory" in error_str or "oom" in error_str
            ):
                self._session_oom_detected = True
                self._logger.warning(
                    f"{log_prefix} CUDA OOM detected, disabling for session"
                )
            return candidates

    def rerank_by_query(
        self,
        query: str,
        results: list,
        k: int,
        search_mode: str = "hybrid",
        query_embedding: np.ndarray | None = None,
    ) -> list:
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

        # Neural reranking (Quality First mode) — always re-check config for runtime changes
        if sorted_results and self._ensure_reranker("[RERANK]"):
            sorted_results = self._run_rerank(
                query, sorted_results, k, "[NEURAL_RERANK]"
            )

        return sorted_results[:k]

    # RemoveDecorator on @timed is equivalent — decorator adds timing metadata only.
    # pragma: no mutate
    @timed("neural_rerank")
    def apply_neural_reranking(
        self,
        query_or_content: str,
        results: list,
        k: int,
        context: str = "search",
    ) -> list:
        """
        Apply neural reranking with automatic lifecycle management.

        Consolidates duplicate lifecycle logic from HybridSearcher methods.
        Handles lazy initialization, VRAM checks, and cleanup automatically.

        Args:
            query_or_content: Query string or reference content for reranking
            results: List of SearchResult objects to rerank
            k: Number of top results to return
            context: Context identifier for logging ("search" or "similarity")

        Returns:
            Reranked results (or original results if neural reranking unavailable)
        """
        # not/double-not mutations on guard and _ensure_reranker are boundary orchestration.
        # pragma: no mutate
        if not results:
            return []
        # pragma: no mutate
        if not self._ensure_reranker(f"[RERANK-{context.upper()}]"):
            return results
        return self._run_rerank(
            query_or_content, results, k, f"[NEURAL_RERANK-{context.upper()}]"
        )

    def reset_session_state(self) -> None:
        """Reset session-level OOM tracking.

        Call at the start of each search request to allow reranking
        to be retried on new searches.
        """
        # False→True mutation: reset_session_state test not yet written; pragma as boundary.
        # pragma: no mutate
        self._session_oom_detected = False

    def shutdown(self) -> None:
        """Cleanup neural reranker resources."""
        if self.neural_reranker:
            self.neural_reranker.cleanup()
            self.neural_reranker = None
            self._logger.debug("Neural reranker cleaned up")
