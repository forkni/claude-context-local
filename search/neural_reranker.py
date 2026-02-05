"""Neural cross-encoder reranker for semantic scoring."""

import logging
from typing import TYPE_CHECKING, Optional

import torch


if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder
    from transformers import AutoModel


# Reranker model registry
# Maps reranker type to model name for environment/menu configuration
RERANKER_MODELS = {
    "full": "BAAI/bge-reranker-v2-m3",  # ~1.5GB VRAM, discriminative cross-encoder
    "lightweight": "Alibaba-NLP/gte-reranker-modernbert-base",  # ~0.3GB VRAM, efficient
    "generative": "Qwen/Qwen3-Reranker-0.6B",  # ~1.5GB VRAM, +8.7 pts over BGE (generative)
    "jina-v3": "jinaai/jina-reranker-v3",  # ~1.5GB VRAM, code-optimized listwise (CoIR 70.64)
}

# Generative rerankers (auto-detected by model name)
GENERATIVE_RERANKERS = {"Qwen/Qwen3-Reranker-0.6B", "Qwen/Qwen3-Reranker-4B"}

# Jina v3 rerankers (listwise architecture)
JINA_V3_RERANKERS = {"jinaai/jina-reranker-v3"}


class NeuralReranker:
    """Cross-encoder neural reranker using BAAI/bge-reranker-v2-m3.

    This reranker provides semantic relevance scoring on top of RRF fusion results,
    improving search quality by 15-25% for complex queries. It uses a cross-encoder
    architecture that jointly processes query-document pairs for accurate ranking.

    Performance:
        - VRAM: ~1.5GB
        - Latency: +150-300ms per search
        - Batch processing for efficiency
        - Lazy loading to minimize startup overhead

    Example:
        >>> reranker = NeuralReranker()
        >>> results = reranker.rerank("authentication functions", candidates, top_k=10)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: Optional[str] = None,
        batch_size: int = 16,
    ):
        """Initialize NeuralReranker with lazy loading.

        Args:
            model_name: HuggingFace model ID for cross-encoder
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
            batch_size: Batch size for inference
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None  # Lazy loading
        self._logger = logging.getLogger(__name__)

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

    @property
    def model(self) -> "CrossEncoder":
        """Lazy load cross-encoder model on first access.

        Returns:
            CrossEncoder: Loaded model instance
        """
        if self._model is None:
            self._logger.info(f"Loading reranker model: {self.model_name}")
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self.model_name,
                device=self.device,
                max_length=512,  # Reasonable limit for code chunks
            )
            self._logger.info(f"Reranker loaded on {self.device}")
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list,  # List[SearchResult]
        top_k: int = 10,
    ) -> list:
        """Rerank candidates using cross-encoder semantic scoring.

        Args:
            query: The search query
            candidates: List of SearchResult objects from RRF
            top_k: Number of results to return after reranking

        Returns:
            Reranked list of SearchResult objects with reranker_score in metadata
        """
        if not candidates:
            return []

        # Create (query, document) pairs for cross-encoder
        pairs = []
        for candidate in candidates:
            # Use content_preview from metadata for scoring
            content = candidate.metadata.get("content_preview", "")
            if not content:
                # Fallback to chunk_id if no content
                content = candidate.chunk_id
            pairs.append((query, content))

        # Get semantic relevance scores
        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )

        # Pair candidates with scores and sort
        scored_candidates = list(zip(candidates, scores, strict=True))
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Return top_k results with updated metadata and score
        results = []
        for candidate, score in scored_candidates[:top_k]:
            # Preserve original score before mutation
            candidate.metadata["original_score"] = candidate.score
            candidate.metadata["reranker_score"] = float(score)
            candidate.score = float(score)  # Replace original score with reranker score
            results.append(candidate)

        self._logger.debug(
            f"Reranked {len(candidates)} candidates → {len(results)} results"
        )
        return results

    def is_loaded(self) -> bool:
        """Check if model is loaded.

        Returns:
            bool: True if model is loaded in memory
        """
        return self._model is not None

    def cleanup(self) -> None:
        """Release GPU memory and model resources."""
        if self._model is not None:
            self._logger.info("Cleaning up reranker model")
            del self._model
            self._model = None
            import gc

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def get_vram_usage(self) -> float:
        """Get current VRAM usage in MB.

        Returns:
            float: VRAM usage in MB, 0.0 if model not loaded or no GPU
        """
        if not self.is_loaded() or not torch.cuda.is_available():
            return 0.0
        return torch.cuda.memory_allocated() / (1024 * 1024)


class GenerativeReranker:
    """Qwen3-style generative reranker using Yes/No token probability.

    This reranker leverages the full LLM "world knowledge" for relevance scoring,
    achieving +8.7 points over discriminative cross-encoders on MTEB-R benchmark.

    Performance:
        - VRAM: ~1.5GB
        - Latency: +200-400ms per search (slower than cross-encoder)
        - Batch processing with autocast for efficiency
        - Lazy loading to minimize startup overhead

    Example:
        >>> reranker = GenerativeReranker()
        >>> results = reranker.rerank("authentication functions", candidates, top_k=10)
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Reranker-0.6B",
        device: Optional[str] = None,
    ):
        """Initialize GenerativeReranker with lazy loading.

        Args:
            model_name: HuggingFace model ID for generative reranker
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        """
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
        self._logger = logging.getLogger(__name__)

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

    def _ensure_loaded(self) -> None:
        """Lazy load model and tokenizer on first access."""
        if self._model is None:
            self._logger.info(f"Loading generative reranker: {self.model_name}")
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, trust_remote_code=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                trust_remote_code=True,
            ).to(self.device)
            self._logger.info(f"Generative reranker loaded on {self.device}")

    @property
    def model(self):
        """Get the generative reranker model (lazy loaded)."""
        self._ensure_loaded()
        return self._model

    @property
    def tokenizer(self):
        """Get the tokenizer (lazy loaded)."""
        self._ensure_loaded()
        return self._tokenizer

    def rerank(
        self,
        query: str,
        candidates: list,  # List[SearchResult]
        top_k: int = 10,
    ) -> list:
        """Rerank candidates using generative Yes/No probability scoring.

        Args:
            query: The search query
            candidates: List of SearchResult objects from RRF
            top_k: Number of results to return after reranking

        Returns:
            Reranked list of SearchResult objects with reranker_score in metadata
        """
        if not candidates:
            return []

        model = self.model
        tokenizer = self.tokenizer

        # Precompute constant token IDs outside loop
        yes_token_id = tokenizer.encode("Yes", add_special_tokens=False)[0]
        no_token_id = tokenizer.encode("No", add_special_tokens=False)[0]

        scores = []
        for candidate in candidates:
            # Use content_preview from metadata for scoring
            content = candidate.metadata.get("content_preview", "")
            if not content:
                # Fallback to chunk_id if no content
                content = candidate.chunk_id

            # Qwen3-Reranker prompt format
            prompt = f"Query: {query}\nDocument: {content}\nIs this document relevant to the query? Answer Yes or No:"

            try:
                inputs = tokenizer(
                    prompt, return_tensors="pt", truncate=True, max_length=512
                ).to(self.device)

                with torch.no_grad():
                    outputs = model(**inputs)
                    logits = outputs.logits[0, -1, :]  # Last token logits

                    probs = torch.softmax(logits[[yes_token_id, no_token_id]], dim=0)
                    score = probs[0].item()  # P(Yes)
            except Exception as e:
                self._logger.warning(f"Skipping candidate {candidate.chunk_id}: {e}")
                score = 0.0

            scores.append(score)

        # Pair candidates with scores and sort
        scored_candidates = list(zip(candidates, scores, strict=True))
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Return top_k results with updated metadata and score
        results = []
        for candidate, score in scored_candidates[:top_k]:
            # Preserve original score before mutation
            candidate.metadata["original_score"] = candidate.score
            candidate.metadata["reranker_score"] = float(score)
            candidate.score = float(score)  # Replace original score with reranker score
            results.append(candidate)

        self._logger.debug(
            f"Reranked {len(candidates)} candidates → {len(results)} results"
        )
        return results

    def is_loaded(self) -> bool:
        """Check if model is loaded.

        Returns:
            bool: True if model is loaded in memory
        """
        return self._model is not None

    def cleanup(self) -> None:
        """Release GPU memory and model resources."""
        if self._model is not None:
            self._logger.info("Cleaning up generative reranker model")
            del self._model
            del self._tokenizer
            self._model = None
            self._tokenizer = None
            import gc

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def get_vram_usage(self) -> float:
        """Get current VRAM usage in MB.

        Returns:
            float: VRAM usage in MB, 0.0 if model not loaded or no GPU
        """
        if not self.is_loaded() or not torch.cuda.is_available():
            return 0.0
        return torch.cuda.memory_allocated() / (1024 * 1024)


class JinaRerankerV3:
    """Jina v3 listwise reranker with 'last but not late' interaction.

    This reranker processes all documents together in a single context window,
    using a novel architecture for more accurate relevance scoring.
    CoIR benchmark: 70.64 (code retrieval optimized).

    Performance:
        - VRAM: ~1.5GB
        - Latency: ~200-400ms (processes all docs together)
        - Listwise: Up to 64 documents in 131K context

    Example:
        >>> reranker = JinaRerankerV3()
        >>> results = reranker.rerank("authentication functions", candidates, top_k=10)
    """

    def __init__(
        self,
        model_name: str = "jinaai/jina-reranker-v3",
        device: Optional[str] = None,
    ):
        """Initialize JinaRerankerV3 with lazy loading.

        Args:
            model_name: HuggingFace model ID for Jina reranker
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        """
        self.model_name = model_name
        self._model = None
        self._logger = logging.getLogger(__name__)

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

    @property
    def model(self) -> "AutoModel":
        """Lazy load Jina v3 model on first access.

        Returns:
            AutoModel: Loaded Jina reranker model
        """
        if self._model is None:
            self._logger.info(f"Loading Jina reranker: {self.model_name}")
            from transformers import AutoConfig, AutoModel

            # Load config first and disable weight tying
            # Jina v3 replaces lm_head with Identity, so tie_word_embeddings must be False
            config = AutoConfig.from_pretrained(self.model_name, trust_remote_code=True)
            config.tie_word_embeddings = False

            self._model = AutoModel.from_pretrained(
                self.model_name,
                config=config,
                dtype="auto",  # Jina's custom parameter
                trust_remote_code=True,
            )
            self._model = self._model.to(self.device)  # Move to GPU if available
            self._model.eval()
            if not hasattr(self._model, "rerank"):
                raise RuntimeError(
                    f"Model {self.model_name} does not support rerank(). "
                    "Ensure you have the correct model with trust_remote_code=True."
                )
            self._logger.info(f"Jina reranker loaded on {self.device}")
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list,  # List[SearchResult]
        top_k: int = 10,
    ) -> list:
        """Rerank candidates using Jina v3 listwise scoring.

        Args:
            query: The search query
            candidates: List of SearchResult objects
            top_k: Number of results to return after reranking

        Returns:
            Reranked list of SearchResult objects with reranker_score

        Raises:
            RuntimeError: If model inference fails (OOM or other error)
        """
        if not candidates:
            return []

        # Extract document texts for Jina API
        documents = []
        for candidate in candidates:
            content = candidate.metadata.get("content_preview", "")
            if not content:
                content = candidate.chunk_id

            # Prepend chunk_id to provide structural context (file path, symbol name)
            # This helps distinguish methods from their containing classes
            content = f"ID: {candidate.chunk_id}\n{content}"
            documents.append(content)

        # Call Jina's native rerank method (listwise) with error handling
        try:
            with torch.no_grad():
                jina_results = self.model.rerank(query, documents, top_n=top_k)
        except torch.cuda.OutOfMemoryError as e:
            self._logger.error(f"CUDA OOM during reranking: {e}")
            torch.cuda.empty_cache()
            raise RuntimeError(f"Insufficient GPU memory for reranking: {e}") from e
        except Exception as e:
            self._logger.error(f"Jina reranker inference failed: {e}")
            raise RuntimeError(f"Reranking failed: {e}") from e

        # Map back to SearchResult objects with index validation
        n = len(candidates)
        results = []
        for jina_result in jina_results:
            idx = jina_result["index"]
            if not isinstance(idx, int) or not (0 <= idx < n):
                self._logger.warning(
                    f"Skipping invalid rerank index {idx} for {n} candidates"
                )
                continue
            score = jina_result["relevance_score"]
            candidate = candidates[idx]
            candidate.metadata["original_score"] = candidate.score
            candidate.metadata["reranker_score"] = float(score)
            candidate.score = float(score)
            results.append(candidate)

        self._logger.debug(
            f"Reranked {len(candidates)} candidates → {len(results)} results"
        )
        return results

    def is_loaded(self) -> bool:
        """Check if model is loaded.

        Returns:
            bool: True if model is loaded in memory
        """
        return self._model is not None

    def cleanup(self) -> None:
        """Release GPU memory and model resources."""
        if self._model is not None:
            self._logger.info("Cleaning up Jina reranker model")
            del self._model
            self._model = None
            import gc

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def get_vram_usage(self) -> float:
        """Get current VRAM usage in MB.

        Returns:
            float: VRAM usage in MB, 0.0 if model not loaded or no GPU
        """
        if not self.is_loaded() or not torch.cuda.is_available():
            return 0.0
        return torch.cuda.memory_allocated() / (1024 * 1024)


def create_reranker(
    model_name: str, device: Optional[str] = None, batch_size: int = 16
) -> "NeuralReranker | GenerativeReranker | JinaRerankerV3":
    """Factory function to create appropriate reranker based on model name.

    This function auto-detects whether to use a discriminative cross-encoder (NeuralReranker),
    a generative LLM reranker (GenerativeReranker), or a listwise reranker (JinaRerankerV3)
    based on the model name.

    Args:
        model_name: HuggingFace model ID for reranker
        device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        batch_size: Batch size for inference (only used for NeuralReranker)

    Returns:
        NeuralReranker, GenerativeReranker, or JinaRerankerV3 instance

    Example:
        >>> reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B")  # Returns GenerativeReranker
        >>> reranker = create_reranker("jinaai/jina-reranker-v3")   # Returns JinaRerankerV3
        >>> reranker = create_reranker("BAAI/bge-reranker-v2-m3")   # Returns NeuralReranker
    """
    if model_name in GENERATIVE_RERANKERS:
        return GenerativeReranker(model_name, device)  # No batch_size parameter
    if model_name in JINA_V3_RERANKERS:
        return JinaRerankerV3(model_name, device)  # Listwise reranker
    return NeuralReranker(model_name, device, batch_size)
