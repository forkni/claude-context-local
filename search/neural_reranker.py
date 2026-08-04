"""Neural cross-encoder reranker for semantic scoring."""

import abc
import contextlib
import logging
import os
import threading
from typing import TYPE_CHECKING

import torch


if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder
    from transformers import AutoModel, PreTrainedModel


# Reranker model registry
# Maps reranker type to model name for environment/menu configuration
RERANKER_MODELS = {
    "full": "BAAI/bge-reranker-v2-m3",  # ~1.5GB VRAM, discriminative cross-encoder
    "lightweight": "Alibaba-NLP/gte-reranker-modernbert-base",  # ~0.3GB VRAM, efficient
    "generative": "Qwen/Qwen3-Reranker-0.6B",  # ~1.5GB VRAM, +8.7 pts over BGE (generative)
    "jina-v3": "jinaai/jina-reranker-v3",  # ~1.5GB VRAM, code-optimized listwise (CoIR 70.64)
}

# Generative rerankers (auto-detected by model name)
GENERATIVE_RERANKERS = {"Qwen/Qwen3-Reranker-0.6B"}

# Jina v3 rerankers (listwise architecture)
JINA_V3_RERANKERS = {"jinaai/jina-reranker-v3"}


def _resolve_single_token_id(tokenizer: "AutoModel", text: str) -> int:
    """Resolve a text string to a single token ID, trying variants.

    Args:
        tokenizer: HuggingFace tokenizer instance
        text: Token text to resolve (e.g., "Yes", "No")

    Returns:
        Single token ID

    Raises:
        RuntimeError: If text cannot be resolved to a single token
    """
    # Official Qwen3-Reranker recipe resolves yes/no via a direct vocabulary
    # lookup (convert_tokens_to_ids), not encode(); prefer that exact lookup
    # and fall back to encode()-based variants for tokenizers whose raw vocab
    # entry differs (e.g. a leading-space or sentencepiece marker form).
    direct_id = tokenizer.convert_tokens_to_ids(text)
    if direct_id is not None and direct_id != tokenizer.unk_token_id:
        return direct_id
    for variant in [text, f" {text}"]:
        ids = tokenizer.encode(variant, add_special_tokens=False)
        if len(ids) == 1:
            return ids[0]
    raise RuntimeError(
        f"Cannot resolve '{text}' to a single token via convert_tokens_to_ids "
        f"or encode() variants ('{text}', ' {text}'). "
        f"Tokenizer: {type(tokenizer).__name__}. "
        f"Verify the model supports single-token Yes/No classification."
    )


def _build_rerank_document(candidate, max_chars: int) -> str:
    """Full chunk text with structural context, capped to the reranker's budget.

    Fallback chain, highest fidelity first: ``bm25_text`` (full raw chunk
    source, persisted per-chunk so ``resync_bm25_from_dense`` can rebuild BM25
    from dense authority — see ``hybrid_searcher.py``) -> ``content_preview``
    (legacy ≤200-char snippet) -> ``chunk_id`` (last resort when metadata is
    entirely empty). Deliberately skips ``metadata["content"]``: on BM25-won
    candidates that key holds the path/symbol-*augmented* BM25 document (see
    ``search/tokenization.py:augment_bm25_document``), not clean source, and
    it is absent on dense-won and expansion candidates.

    Prepends ``ID: {chunk_id}\\n`` so both reranker classes see the same
    structural context (file path + symbol name) that helps distinguish
    methods from their containing classes.

    Args:
        candidate: SearchResult with ``.chunk_id`` and ``.metadata``
        max_chars: Maximum length of the document body (header excluded)

    Returns:
        ``"ID: {chunk_id}\\n{body}"``, body truncated to ``max_chars``

    Note: the ``ID:`` header is prepended *after* truncation, so it is never
    counted against ``max_chars`` — the real per-document payload handed to
    the reranker is ``max_chars`` plus header length. Harmless at today's
    values, but any future packed-sequence budget arithmetic (see
    ``JinaRerankerV3.__init__`` and ADR-0011) should account for it.
    """
    body = candidate.metadata.get("bm25_text") or candidate.metadata.get(
        "content_preview", ""
    )
    if not body:
        body = candidate.chunk_id
    if len(body) > max_chars:
        body = body[:max_chars]
    return f"ID: {candidate.chunk_id}\n{body}"


class BaseReranker(abc.ABC):
    """Abstract base owning shared lifecycle for all reranker implementations.

    Three methods — ``is_loaded``, ``get_vram_usage``, and ``cleanup`` — are
    byte-identical across ``NeuralReranker``, ``GenerativeReranker``, and
    ``JinaRerankerV3``.  This class is the single owner; concrete classes
    inherit them rather than copying them.

    Concrete classes must:

    * Set ``self._model = None`` and ``self._logger`` in ``__init__``.
    * Declare ``self.device`` in ``__init__``.
    * Override ``_CLEANUP_LOG_MSG`` with the class-specific log string.
    * Override ``_cleanup_extra()`` to release resources beyond ``self._model``
      (e.g. ``GenerativeReranker`` also deletes its tokenizer).
    * Implement ``rerank()``.
    """

    # Subclasses override this string for the cleanup log message.
    _CLEANUP_LOG_MSG: str = "Cleaning up reranker model"

    # Declared here so type checkers know the base methods can access these;
    # concrete __init__ methods set the actual values.
    _model: object | None
    _logger: logging.Logger

    @abc.abstractmethod
    def rerank(self, query: str, candidates: list, top_k: int = 10) -> list:
        """Rerank candidates by relevance to *query* and return the top *top_k*."""

    # ------------------------------------------------------------------
    # Shared lifecycle — single implementation, all three classes inherit
    # ------------------------------------------------------------------

    def is_loaded(self) -> bool:
        """Return ``True`` if model weights are loaded in memory."""
        return self._model is not None

    def get_vram_usage(self) -> float:
        """Return current VRAM usage in MB, or 0.0 if unloaded or no GPU."""
        if not self.is_loaded() or not torch.cuda.is_available():
            return 0.0
        return torch.cuda.memory_allocated() / (1024 * 1024)

    def _cleanup_extra(self) -> None:
        """Release resources beyond ``self._model``.

        Default is a no-op.  ``GenerativeReranker`` overrides this to also
        delete ``self._tokenizer``.
        """
        return  # No-op default; override in subclasses that hold extra resources.

    def cleanup(self) -> None:
        """Release GPU memory and model resources."""
        if self._model is not None:
            self._logger.info(self._CLEANUP_LOG_MSG)
            del self._model
            self._model = None
            self._cleanup_extra()
            import gc

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


class NeuralReranker(BaseReranker):
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
        device: str | None = None,
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
        self._load_lock = threading.Lock()
        # Serializes inference calls (predict()) — separate from _load_lock, which
        # only guards the one-time model load. CrossEncoder.predict is not documented
        # as thread-safe under concurrent calls; this mirrors CodeEmbedder's
        # _lifecycle_lock pattern (embeddings/embedder.py). Lock ordering is always
        # _infer_lock -> _load_lock (resolve self.model before acquiring _infer_lock),
        # never the reverse.
        self._infer_lock = threading.Lock()
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
            with self._load_lock:
                if self._model is None:
                    # Re-apply VRAM cap before loading reranker weights — embedder and
                    # other processes may have changed free VRAM since server startup.
                    try:
                        from embeddings.embedder import set_vram_limit
                        from search.config import get_search_config as _gsc

                        set_vram_limit(_gsc().performance.vram_limit_fraction)
                    except Exception as e:  # noqa: BLE001 - resilience: VRAM cap re-apply non-fatal, model load continues
                        self._logger.debug(
                            "VRAM cap re-apply skipped (non-fatal): %s", e
                        )
                    self._logger.info(f"Loading reranker model: {self.model_name}")
                    from sentence_transformers import CrossEncoder

                    self._model = CrossEncoder(
                        self.model_name,
                        device=self.device,
                        max_length=512,
                    )
                    self._logger.info(f"Reranker loaded on {self.device}")
        return self._model

    def _apply_rerank_score(self, candidate, score: float) -> None:
        candidate.metadata["original_score"] = candidate.score
        candidate.metadata["reranker_score"] = float(score)
        candidate.score = float(score)

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
            top_k: Unused for scoring — kept for BaseReranker signature parity
                (see JinaRerankerV3.rerank's docstring for why). ``model.predict``
                already scores every candidate in one call (batch_size only
                controls internal batching, not an early exit), so truncating
                to top_k here first would only starve rerank_by_query's
                dedupe_split_blocks backfill for free.

        Returns:
            Full ranked list of SearchResult objects with reranker_score in metadata
        """
        if not candidates:
            return []

        pairs = []
        for candidate in candidates:
            content = (
                candidate.metadata.get("content_preview", "") or candidate.chunk_id
            )
            pairs.append((query, content))

        model = self.model  # resolve (lazy load under _load_lock) before _infer_lock
        try:
            with self._infer_lock:
                scores = model.predict(
                    pairs,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                )
        finally:
            # Pool-wide policy: release cached-but-unused CUDA allocator blocks after
            # every rerank() call, on both success and failure. Originally added only to
            # JinaRerankerV3 (whose variable-length listwise context caused torch_reserved
            # to grow monotonically 8.3GB->13.5GB across searches on an RTX 4090 while
            # torch_allocated stayed flat); applied here too for pool-wide consistency.
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        scored_candidates = list(zip(candidates, scores, strict=True))
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        results = []
        for candidate, score in scored_candidates:
            self._apply_rerank_score(candidate, score)
            results.append(candidate)

        self._logger.debug(
            f"Reranked {len(candidates)} candidates → {len(results)} results"
        )
        return results

    def rerank_batch(
        self,
        batch: list[tuple[str, list]],  # list of (query, candidates)
        top_k: int = 10,
    ) -> list[list]:
        """Rerank multiple (query, candidates) pairs in a single forward pass.

        Flattens all (query, doc) pairs across all queries into one
        CrossEncoder.predict call, then splits results back by original offsets.
        Under concurrent load this is significantly cheaper than N separate
        rerank() calls because the GPU sees one large batch instead of N small ones.

        Warning:
            Scoring mutates each candidate in-place (``metadata["original_score"]``,
            ``metadata["reranker_score"]``, ``score``). Callers must not share a
            single candidate object across multiple batch entries — the second
            mutation would overwrite ``original_score`` with the first entry's
            reranker score rather than the true pre-rerank score.

        Args:
            batch: List of (query_str, candidates_list) tuples.
            top_k: Number of results to return per query.

        Returns:
            List of reranked candidate lists, one per input query.
        """
        if not batch:
            return []

        all_pairs: list[tuple[str, str]] = []
        offsets: list[int] = []

        for query, candidates in batch:
            offsets.append(len(all_pairs))
            for candidate in candidates:
                content = (
                    candidate.metadata.get("content_preview", "") or candidate.chunk_id
                )
                all_pairs.append((query, content))

        if not all_pairs:
            return [[] for _ in batch]

        model = self.model  # resolve (lazy load under _load_lock) before _infer_lock
        try:
            with self._infer_lock:
                all_scores = model.predict(
                    all_pairs,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                )
        finally:
            # See rerank() above: pool-wide policy, release after every call.
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        results = []
        for i, (_, candidates) in enumerate(batch):
            start = offsets[i]
            end = offsets[i + 1] if i + 1 < len(offsets) else len(all_pairs)
            scores = all_scores[start:end]
            scored = sorted(
                zip(candidates, scores, strict=True), key=lambda x: x[1], reverse=True
            )
            query_results = []
            for candidate, score in scored[:top_k]:
                self._apply_rerank_score(candidate, score)
                query_results.append(candidate)
            results.append(query_results)

        return results

    # Lifecycle methods (is_loaded, get_vram_usage, cleanup) are owned by BaseReranker.


# Qwen3-Reranker official prompt template (arXiv:2506.05176, "Qwen3 Embedding" tech
# report, §2 "Reranking Models"). Qwen3-Reranker models are fine-tuned specifically on
# this chat-wrapped <Instruct>/<Query>/<Document> format with lowercase "yes"/"no"
# target tokens. An ad-hoc prompt (no chat wrapper, capitalized Yes/No) is off-distribution
# for the model and produces poorly-calibrated, sometimes inverted relevance scores —
# verified empirically: on a real query the official template restored the correct top
# candidates that the ad-hoc prompt had buried below unrelated results.
_QWEN_RERANK_DEFAULT_INSTRUCTION = (
    "Given a code search query, retrieve relevant code that answers the query"
)
_QWEN_RERANK_SYSTEM_PREFIX = (
    "<|im_start|>system\n"
    "Judge whether the Document meets the requirements based on the Query and the "
    'Instruct provided. Note that the answer can only be "yes" or "no".<|im_end|>\n'
    "<|im_start|>user\n"
)
_QWEN_RERANK_ASSISTANT_SUFFIX = (
    "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
)


class GenerativeReranker(BaseReranker):
    """Qwen3-style generative reranker using yes/no token probability.

    Uses the official Qwen3-Reranker instruct template (chat-wrapped
    <Instruct>/<Query>/<Document> fields, lowercase yes/no target tokens; see
    arXiv:2506.05176 §2). This reranker leverages the full LLM "world knowledge" for
    relevance scoring, achieving +8.7 points over discriminative cross-encoders on the
    MTEB-R benchmark.

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
        device: str | None = None,
        instruction: str | None = None,
        batch_size: int = 16,
        doc_max_chars: int = 4000,
    ):
        """Initialize GenerativeReranker with lazy loading.

        Args:
            model_name: HuggingFace model ID for generative reranker
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
            instruction: Task instruction inserted into the official Qwen3-Reranker
                <Instruct> field (Qwen3-Reranker is "Instruction Aware" per the model's
                technical report). ``None`` uses the default code-retrieval instruction;
                pass ``""`` explicitly to send an empty instruction.
            batch_size: Number of prompts per forward pass. Chunking keeps the
                logits tensor bounded regardless of candidate-pool size (see rerank()).
            doc_max_chars: Maximum document body length fed to the prompt (see
                ``_build_rerank_document``). Pointwise architecture — cost scales
                with ``batch_size * doc_max_chars`` per forward pass, so this can
                afford a larger budget than the listwise ``JinaRerankerV3``.
        """
        self.model_name = model_name
        self.instruction = (
            instruction if instruction is not None else _QWEN_RERANK_DEFAULT_INSTRUCTION
        )
        self.batch_size = batch_size
        self.doc_max_chars = doc_max_chars
        self._model = None
        self._tokenizer = None
        # Resolved once in _ensure_loaded() and reused by rerank()'s autocast call so
        # the weight dtype and the autocast compute dtype never disagree (autocast's
        # CUDA default is float16, which would silently undo a bf16 weight load).
        self._autocast_dtype: torch.dtype | None = None
        # Incremented on every fallback-to-original-order path (OOM/RuntimeError/
        # ValueError during inference, or unresolvable yes/no token). A benchmark run
        # with fallback_count > 0 produced RRF-order results for at least one batch and
        # must be discarded — see rerank()'s except block.
        self.fallback_count = 0
        # Serializes the tokenize+forward inference region — this class has no
        # _load_lock (its lazy load via _ensure_loaded() is unguarded, a pre-existing
        # gap out of scope here); _infer_lock still prevents concurrent callers from
        # borrowing the shared HF fast tokenizer at the same time (see rerank()).
        self._infer_lock = threading.Lock()
        self._logger = logging.getLogger(__name__)

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

    def _ensure_loaded(self) -> None:
        """Lazy load model and tokenizer on first access."""
        if self._model is None:
            # Re-apply VRAM cap before loading generative reranker weights.
            try:
                from embeddings.embedder import set_vram_limit
                from search.config import get_search_config as _gsc

                set_vram_limit(_gsc().performance.vram_limit_fraction)
            except Exception as e:  # noqa: BLE001 - resilience: VRAM cap re-apply non-fatal, model load continues
                self._logger.debug("VRAM cap re-apply skipped (non-fatal): %s", e)
            self._logger.info(f"Loading generative reranker: {self.model_name}")
            from transformers import AutoModelForCausalLM, AutoTokenizer

            # bfloat16 is Qwen3's native training dtype; fp16 can overflow at 4B.
            # Resolved once and reused by rerank()'s autocast call (see __init__).
            if self.device == "cuda":
                self._autocast_dtype = (
                    torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                )
            else:
                self._autocast_dtype = torch.float32

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, trust_remote_code=True
            )
            # Qwen's own reference implementation left-pads so the last sequence
            # position is the last real token for every row (see rerank()'s
            # logits_to_keep=1 read of logits[:, -1, :]).
            self._tokenizer.padding_side = "left"
            # Truncate from the left (start) of the tokenized prompt so the
            # assistant suffix (<|im_end|>...<think>...) that logits[:, -1, :]
            # reads always survives — right truncation would eat it whenever a
            # prompt exceeds max_length.
            self._tokenizer.truncation_side = "left"

            load_kwargs = {
                "torch_dtype": self._autocast_dtype,
                "trust_remote_code": True,
            }
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name, **load_kwargs
            ).to(self.device)
            self._logger.info(
                f"Generative reranker loaded on {self.device} "
                f"(dtype={self._autocast_dtype})"
            )

    @property
    def model(self) -> "AutoModel":
        """Get the generative reranker model (lazy loaded)."""
        self._ensure_loaded()
        return self._model

    @property
    def tokenizer(self) -> "AutoModel":
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

        Uses batched inference for O(1) forward passes instead of O(N).
        Falls back to returning candidates in original order on failure.

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

        # Resolve token IDs with validation and graceful fallback.
        # Lowercase "yes"/"no" per the official Qwen3-Reranker template (arXiv:2506.05176)
        # — the model was fine-tuned on these exact target tokens.
        try:
            yes_token_id = _resolve_single_token_id(tokenizer, "yes")
            no_token_id = _resolve_single_token_id(tokenizer, "no")
        except RuntimeError as e:
            self.fallback_count += 1
            self._logger.error(
                f"Token resolution failed: {e}. Returning candidates in original order."
            )
            results = []
            for candidate in candidates[:top_k]:
                candidate.metadata["original_score"] = candidate.score
                candidate.metadata["reranker_score"] = candidate.score
                results.append(candidate)
            return results

        # Build all prompts using the official Qwen3-Reranker instruct template
        # (chat-wrapped <Instruct>/<Query>/<Document> fields; see module-level constants).
        prompts = []
        for candidate in candidates:
            content = _build_rerank_document(candidate, self.doc_max_chars)
            prompt = (
                f"{_QWEN_RERANK_SYSTEM_PREFIX}"
                f"<Instruct>: {self.instruction}\n<Query>: {query}\n<Document>: {content}"
                f"{_QWEN_RERANK_ASSISTANT_SUFFIX}"
            )
            prompts.append(prompt)

        # Batched inference with graceful fallback. _infer_lock covers the whole
        # tokenize->forward region: the fast-tokenizer borrow happens in the
        # tokenizer(...) call itself, not just the model forward pass. Chunked into
        # self.batch_size-sized groups so the logits tensor stays bounded regardless
        # of candidate-pool size or max_length (top_k_candidates=30 at 4B would
        # otherwise produce a single [30, max_length, vocab] multi-GiB forward pass
        # on top of ~8 GB of weights).
        scores: list[float] = []
        try:
            with self._infer_lock:
                for start in range(0, len(prompts), self.batch_size):
                    batch_prompts = prompts[start : start + self.batch_size]
                    inputs = tokenizer(
                        batch_prompts,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=2048,
                    ).to(self.device)

                    with torch.no_grad():
                        autocast_kwargs = {"device_type": "cuda"}
                        if self._autocast_dtype is not None:
                            autocast_kwargs["dtype"] = self._autocast_dtype
                        if self.device == "cuda":
                            with torch.autocast(**autocast_kwargs):
                                outputs = model(**inputs, logits_to_keep=1)
                        else:
                            outputs = model(**inputs, logits_to_keep=1)

                        # With left padding + logits_to_keep=1, position -1 is the last
                        # real token for every row (Qwen's own reference implementation
                        # relies on the same invariant). Shrinks the logits tensor from
                        # [B, seq, vocab] to [B, 1, vocab] — arithmetically identical to
                        # the attention_mask-indexed lookup this replaces, just bounded.
                        last_logits = outputs.logits[:, -1, :]

                        # Softmax over [yes, no] token logits to get P(Yes)
                        yn_logits = last_logits[:, [yes_token_id, no_token_id]]
                        probs = torch.softmax(yn_logits, dim=1)
                        scores.extend(
                            probs[:, 0].cpu().tolist()
                        )  # P(Yes) per candidate

        except (torch.cuda.OutOfMemoryError, RuntimeError, ValueError) as e:
            self.fallback_count += 1
            self._logger.error(
                f"Batched inference failed ({type(e).__name__}): {e}. "
                "Returning candidates in original order."
            )
            # Graceful fallback: return top_k candidates with original scores preserved
            results = []
            for candidate in candidates[:top_k]:
                candidate.metadata["original_score"] = candidate.score
                candidate.metadata["reranker_score"] = candidate.score
                results.append(candidate)
            return results
        finally:
            # Pool-wide policy (see NeuralReranker.rerank() above): release cached-but-
            # unused CUDA allocator blocks after every call, on both success and failure.
            # `finally` runs even though the except branch above returns early.
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        # Pair candidates with scores and sort
        scored_candidates = list(zip(candidates, scores, strict=True))
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Return top_k results with updated metadata and score
        results = []
        for candidate, score in scored_candidates[:top_k]:
            candidate.metadata["original_score"] = candidate.score
            candidate.metadata["reranker_score"] = float(score)
            candidate.score = float(score)
            results.append(candidate)

        self._logger.debug(
            f"Reranked {len(candidates)} candidates → {len(results)} results"
        )
        return results

    _CLEANUP_LOG_MSG = "Cleaning up generative reranker model"

    def _cleanup_extra(self) -> None:
        """Also release the tokenizer held by GenerativeReranker."""
        del self._tokenizer
        self._tokenizer = None

    # is_loaded, get_vram_usage, cleanup are owned by BaseReranker.


class JinaRerankerV3(BaseReranker):
    """Jina v3 listwise reranker with 'last but not late' interaction.

    This reranker processes ALL candidates together in one shared context
    window (a single forward pass with full cross-document attention), scoring
    each document's embedding-marker position against the query's own
    embedding-marker position via cosine similarity of projected embeddings
    (arXiv 2509.25085v4 sec 3.1-3.2). The underlying model builds the prompt
    itself (``format_docs_prompts_func``, incl. its special embedding-marker
    tokens); this class must never construct that sandwich prompt by hand.

    Performance (measured at doc_max_chars=1000, SSCG gate run, 30-candidate
    pool, RTX 4090):
        - VRAM: ~13.2GB peak (reserved-memory ratchet across a session —
          see the ``empty_cache()`` policy note in ``rerank()``'s ``finally``)
        - Latency: ~4000ms/query at 30 candidates x ~1000-char documents
        - Listwise: released code uses ``block_size=125`` docs/forward pass;
          our 30-candidate pool fits in a single block/forward pass. Context-
          window occupancy is not the binding constraint though — raising
          doc_max_chars to 4000 measured peak_vram_reserved_gb 27.66 on this
          24GB card (WDDM spill to host RAM, no OOM) and ~3x latency with
          42-45/96 queries stalling past 8s. See
          docs/adr/0011-listwise-reranker-doc-cap.md.

    Example:
        >>> reranker = JinaRerankerV3()
        >>> results = reranker.rerank("authentication functions", candidates, top_k=10)
    """

    #: Accepted ``dtype`` values -> torch dtype ("auto" = checkpoint default, bf16).
    DTYPE_MAP: dict[str, "str | torch.dtype"] = {
        "auto": "auto",
        "fp32": torch.float32,
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
    }

    def __init__(
        self,
        model_name: str = "jinaai/jina-reranker-v3",
        device: str | None = None,
        doc_max_chars: int = 1000,
        dtype: str = "auto",
    ):
        """Initialize JinaRerankerV3 with lazy loading.

        Args:
            model_name: HuggingFace model ID for Jina reranker
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
            dtype: Weight dtype — "auto" (checkpoint default, bf16), "fp32",
                "bf16", or "fp16". bf16 listwise scoring is run-to-run
                non-deterministic at ranking boundaries (context-dependent
                scores + reduced mantissa); "fp32" doubles reranker VRAM
                (~2.4 GB for the 0.6B model) in exchange for reproducible
                scores.
            doc_max_chars: Maximum document body length per candidate (see
                ``_build_rerank_document``). Listwise architecture — ALL
                candidates share one context window, so cost does scale with
                ``top_k_candidates * doc_max_chars``. Context-window
                occupancy alone looks safe raising this to 4000 — the
                30-doc shared context only grows ~5.4K -> ~8.8K tokens of
                the 131K window, and 0% of docs hit the model's own
                2048-token per-doc ceiling at either cap — but that is not
                the binding resource: attention activation memory scales
                O(n^2) in the packed sequence length, and the paper's own
                Table 5 lists an "Effective Sequence Length" of 8,192 as a
                figure distinct from the 131K Context Length — the ~8.8K
                estimate at 4000 already crosses that tighter, governing
                budget while looking safe against the window alone. A
                4-run SSCG sweep at
                4000 measured peak_vram_reserved_gb 27.66 on a 24GB card (a
                WDDM shared-memory spill to host RAM — no OOM raised) with
                42-45/96 queries stalling past 8s (max 354.9s) and every
                quality metric flat-to-negative within the noise floor. See
                docs/adr/0011-listwise-reranker-doc-cap.md. 1000 chars
                truncates 45.7% of chunks in this index (40.3% of
                characters retained); 4000 truncates only 6.3% but is not
                worth the cost above. Aligned with
                ``GenerativeReranker.doc_max_chars`` in neither value nor
                rationale — that budget is pointwise and stays at 4000.
        """
        if dtype not in self.DTYPE_MAP:
            raise ValueError(
                f"Unsupported reranker dtype {dtype!r}; "
                f"expected one of {sorted(self.DTYPE_MAP)}"
            )
        self.model_name = model_name
        self.doc_max_chars = doc_max_chars
        self.dtype = dtype
        self._model = None
        self._logger = logging.getLogger(__name__)
        self._load_lock = threading.Lock()
        # Serializes model.rerank() calls — the underlying HF Rust fast tokenizer
        # panics with "Already borrowed" if two threads call it concurrently.
        # _load_lock guards the one-time load only; this is the separate inference
        # mutex (see NeuralReranker._infer_lock above for the general rationale).
        self._infer_lock = threading.Lock()

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

    @property
    def model(self) -> "AutoModel":
        """Lazy load Jina v3 model on first access.

        Thread-safe via double-checked locking: the fast-path check avoids
        lock contention once the model is loaded; the lock prevents two threads
        from both entering the slow init path simultaneously.

        Returns:
            AutoModel: Loaded Jina reranker model
        """
        if self._model is None:
            with self._load_lock:
                if self._model is None:  # re-check under lock
                    self._load_or_fetch()
        return self._model

    def _load_or_fetch(self) -> None:
        """Internal: load model from cache or HuggingFace. Called under _load_lock."""
        # Re-apply VRAM cap before loading Jina reranker weights.
        try:
            from embeddings.embedder import set_vram_limit
            from search.config import get_search_config as _gsc

            set_vram_limit(_gsc().performance.vram_limit_fraction)
        except Exception as e:  # noqa: BLE001 - resilience: VRAM cap re-apply non-fatal, model load continues
            self._logger.debug("VRAM cap re-apply skipped (non-fatal): %s", e)
        import transformers as _tf
        from huggingface_hub import try_to_load_from_cache
        from transformers import AutoConfig, AutoModel

        self._logger.info(f"Loading Jina reranker: {self.model_name}")

        # Use local_files_only when model is cached to skip HuggingFace HEAD
        # requests (eliminates ~3-4s of network latency per from_pretrained call)
        cached = try_to_load_from_cache(self.model_name, "config.json")
        local_only = isinstance(cached, str) and os.path.exists(cached)

        # Enable offline mode when cache is validated — prevents transformers from
        # making HTTP HEAD requests to huggingface.co on every from_pretrained call
        # (mirrors the pattern in embeddings/model_loader.py:358-363)
        if local_only:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            self._logger.debug(
                "[VALIDATED CACHE] Enabling offline mode for Jina reranker load."
            )

        def _load_config(local_files_only: bool) -> AutoConfig:
            # Checkpoint ships no lm_head tensor (verified: 312 safetensors keys,
            # zero lm_head.*) — leave tie_word_embeddings at its config default
            # (True) so transformers satisfies lm_head from the tied embedding
            # instead of allocating+randomly-initializing an untied 151936x1024
            # Linear (152M params ~= 311MB bf16, wasted since forward() replaces
            # lm_head with nn.Identity() anyway and never reads it). Untying was
            # previously believed to suppress the "lm_head.weight | MISSING" LOAD
            # REPORT; it does not — that report is a stdout print, silenced by
            # _load_model()'s redirect_stdout below regardless of tying.
            return AutoConfig.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )

        try:
            config = _load_config(local_only)
        except (OSError, ValueError):
            os.environ.pop("HF_HUB_OFFLINE", None)
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
            config = _load_config(False)
            local_only = False  # cache miss — fall through to network for model too

        def _load_model(cfg: AutoConfig, local_files_only: bool) -> "PreTrainedModel":
            # Suppress Jina's lm_head MISSING LOAD REPORT printed to stdout
            # (cosmetic: lm_head is replaced by nn.Identity() and is never
            # used during reranking; scoring uses the projector head instead).
            # Called under _load_lock already; redirect_stdout alone is sufficient.
            import io as _io

            with contextlib.redirect_stdout(_io.StringIO()):
                try:
                    return AutoModel.from_pretrained(
                        self.model_name,
                        config=cfg,
                        dtype=self.DTYPE_MAP[self.dtype],  # Jina's custom parameter
                        trust_remote_code=True,
                        local_files_only=local_files_only,
                    )
                except TypeError:
                    # dtype is Jina-specific; retry without it on older
                    # transformers (a non-"auto" request is re-applied via the
                    # explicit .to(dtype) cast after loading).
                    self._logger.warning(
                        f"dtype={self.dtype!r} not supported "
                        f"(transformers {_tf.__version__}), retrying without it"
                    )
                    return AutoModel.from_pretrained(
                        self.model_name,
                        config=cfg,
                        trust_remote_code=True,
                        local_files_only=local_files_only,
                    )

        try:
            self._model = _load_model(config, local_only)
        except (OSError, ValueError):
            # Cache stale/corrupt — retry over network
            os.environ.pop("HF_HUB_OFFLINE", None)
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
            self._logger.warning(
                "Local cache miss for Jina reranker, fetching from HuggingFace Hub"
            )
            config = _load_config(False)
            self._model = _load_model(config, False)

        if self.dtype != "auto":
            # Cast on CPU before the device move so the requested dtype holds
            # even when the TypeError fallback above dropped the load-time
            # dtype kwarg (no-op when from_pretrained already honored it).
            self._model = self._model.to(self.DTYPE_MAP[self.dtype])
        self._model = self._model.to(self.device)  # Move to GPU if available
        self._model.eval()

        if not hasattr(self._model, "rerank"):
            # Clean up invalid model before resetting
            del self._model
            self._model = None  # Reset so next access retries loading
            raise RuntimeError(
                f"Model {self.model_name} does not support rerank(). "
                "Ensure you have the correct model with trust_remote_code=True. "
                f"(transformers=={_tf.__version__}). "
                "If this persists, verify model compatibility with your transformers version."
            )

        # Pre-load tokenizer now to consolidate all HuggingFace Hub API calls
        # into this init window. Jina loads the tokenizer lazily on the first
        # rerank() call via _ensure_tokenizer(), which triggers a second round
        # of network requests (config.json, tokenizer_config.json, model tree)
        # after the model is already on GPU, adding ~1s to first-query latency.
        if hasattr(self._model, "_ensure_tokenizer"):
            try:
                self._model._ensure_tokenizer()
            except Exception as e:  # noqa: BLE001 - resilience: tokenizer pre-load optional, retried on first rerank
                self._logger.warning(
                    f"Tokenizer pre-load failed (will retry on first rerank): {e}"
                )

        self._logger.info(f"Jina reranker loaded on {self.device}")
        # Clean up offline env vars after load to avoid side effects on other code
        os.environ.pop("HF_HUB_OFFLINE", None)
        os.environ.pop("TRANSFORMERS_OFFLINE", None)

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
            top_k: Unused for the model call — kept for BaseReranker signature
                parity with NeuralReranker/GenerativeReranker. Jina scores every
                candidate in the same forward pass regardless (listwise), so
                the full ranked list is returned; callers already slice to the
                final k downstream (search_executor._run_rerank's own callers,
                rerank_by_query's ``[:k]``) and rerank_by_query's
                dedupe_split_blocks needs the full ranked list to backfill
                collapsed split_block fragments — truncating here first would
                starve that backfill.

        Returns:
            Full ranked list of SearchResult objects with reranker_score

        Raises:
            RuntimeError: If model inference fails (OOM or other error)
        """
        if not candidates:
            return []

        # Extract document texts for Jina API
        documents = [
            _build_rerank_document(candidate, self.doc_max_chars)
            for candidate in candidates
        ]

        # Call Jina's native rerank method (listwise) with error handling.
        # top_n=None returns every candidate ranked (see docstring above).
        # max_doc_length/max_query_length passed explicitly rather than
        # relying on jina's defaults (2048/512) — our doc_max_chars (chars)
        # is the binding truncation on this corpus; measured mean ~3.4
        # chars/token means even doc_max_chars=4000 stays well under 2048
        # tokens (0% of documents hit that ceiling at any cap tested). That
        # only rules out the per-doc token ceiling as the limit, though —
        # it does NOT mean 4000 is safe: attention activation memory scales
        # O(n^2) in the packed sequence and empirically spills VRAM well
        # before this ceiling (docs/adr/0011-listwise-reranker-doc-cap.md).
        model = self.model  # resolve (lazy load under _load_lock) before _infer_lock
        try:
            with self._infer_lock, torch.no_grad():
                jina_results = model.rerank(
                    query,
                    documents,
                    top_n=None,
                    max_doc_length=2048,
                    max_query_length=512,
                )
        except torch.cuda.OutOfMemoryError as e:
            self._logger.error(f"CUDA OOM during reranking: {e}")
            raise RuntimeError(f"Insufficient GPU memory for reranking: {e}") from e
        except Exception as e:
            self._logger.error(f"Jina reranker inference failed: {e}")
            raise RuntimeError(f"Reranking failed: {e}") from e
        finally:
            # Pool-wide policy: release cached-but-unused allocator blocks after every
            # rerank() call, on success, OOM, or any other failure — NeuralReranker and
            # GenerativeReranker do the same (see their rerank()/rerank_batch() methods).
            # This class is where the policy was discovered: Jina's listwise architecture
            # concatenates ALL candidate documents into one shared context per forward
            # pass, so sequence length — and therefore the CUDA allocator's block sizes —
            # varies with every query. Differently-sized blocks are rarely reused
            # call-to-call, so torch_reserved (cached-but-unallocated memory) ratchets
            # upward monotonically across searches even though torch_allocated (live
            # tensors) stays flat — confirmed via get_memory_status(): reserved grew
            # ~8.3GB -> 13.5GB over 4 searches on an RTX 4090 while allocated stayed
            # pinned at 2.25GB. Left unchecked this eventually exhausts VRAM and triggers
            # Windows WDDM's shared-memory (sysmem) fallback ("VRAM spillover"). GTE/BGE's
            # uniform, fixed-max_length=512 pairwise batches are far less likely to hit
            # this in practice, but release uniformly across the pool rather than
            # special-casing by measured risk.
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        # Map back to SearchResult objects with index validation
        n = len(candidates)
        results = []
        for jina_result in jina_results:
            # Coerce index to int (Jina returns numpy.int64, which isn't an int subclass in NumPy 2.x)
            try:
                idx = int(jina_result["index"])
            except (TypeError, ValueError):
                self._logger.warning(
                    f"Skipping non-numeric rerank index: {jina_result.get('index')}"
                )
                continue

            # Validate bounds
            if not (0 <= idx < n):
                self._logger.warning(
                    f"Skipping out-of-bounds rerank index {idx} for {n} candidates"
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

    _CLEANUP_LOG_MSG = "Cleaning up Jina reranker model"

    # is_loaded, get_vram_usage, cleanup are owned by BaseReranker.


def create_reranker(
    model_name: str,
    device: str | None = None,
    batch_size: int = 16,
    instruction: str | None = None,
    doc_max_chars: int = 4000,
    listwise_doc_max_chars: int = 1000,
    listwise_dtype: str = "auto",
) -> "NeuralReranker | GenerativeReranker | JinaRerankerV3":
    """Factory function to create appropriate reranker based on model name.

    This function auto-detects whether to use a discriminative cross-encoder (NeuralReranker),
    a generative LLM reranker (GenerativeReranker), or a listwise reranker (JinaRerankerV3)
    based on the model name.

    Args:
        model_name: HuggingFace model ID for reranker
        device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        batch_size: Batch size for inference (NeuralReranker and GenerativeReranker;
            JinaRerankerV3 does its own internal batching)
        instruction: Only used for GenerativeReranker — see its docstring.
        doc_max_chars: Only used for GenerativeReranker (pointwise — cost scales
            with batch_size, so it can afford a larger per-document budget).
        listwise_doc_max_chars: Only used for JinaRerankerV3 (listwise — ALL
            candidates share one context window, so cost is O(n^2) in the
            packed sequence via attention activation memory). Raising this
            from 1000 to 4000 clears the context-window and per-doc-token
            checks fine, but a 4-run SSCG sweep at 4000 measured
            peak_vram_reserved_gb 27.66 on a 24GB card (WDDM spill, no OOM),
            42-45/96 queries stalling past 8s, and no quality gain outside
            the noise floor — see
            docs/adr/0011-listwise-reranker-doc-cap.md. Not aligned with
            ``doc_max_chars`` above by default; the two budgets are
            independent on purpose.
        listwise_dtype: Only used for JinaRerankerV3 — weight dtype ("auto",
            "fp32", "bf16", "fp16"); see ``JinaRerankerV3.__init__``.

    Returns:
        NeuralReranker, GenerativeReranker, or JinaRerankerV3 instance

    Example:
        >>> reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B")  # Returns GenerativeReranker
        >>> reranker = create_reranker("jinaai/jina-reranker-v3")   # Returns JinaRerankerV3
        >>> reranker = create_reranker("BAAI/bge-reranker-v2-m3")   # Returns NeuralReranker
    """
    if model_name in GENERATIVE_RERANKERS:
        return GenerativeReranker(
            model_name,
            device,
            instruction=instruction,
            batch_size=batch_size,
            doc_max_chars=doc_max_chars,
        )
    if model_name in JINA_V3_RERANKERS:
        return JinaRerankerV3(
            model_name,
            device,
            doc_max_chars=listwise_doc_max_chars,
            dtype=listwise_dtype,
        )  # Listwise reranker
    return NeuralReranker(model_name, device, batch_size)
