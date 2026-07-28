"""Unit tests for JinaRerankerV3 and factory integration."""

from unittest.mock import MagicMock, patch

import torch

from search.neural_reranker import (
    JINA_V3_RERANKERS,
    JinaRerankerV3,
    create_reranker,
)
from search.reranker import SearchResult


class TestJinaRerankerV3:
    """Tests for JinaRerankerV3 class."""

    def test_lazy_loading(self):
        """Model should not load until first use."""
        reranker = JinaRerankerV3()
        assert reranker._model is None
        assert not reranker.is_loaded()

    def test_rerank_empty_candidates(self):
        """Empty candidates should return empty list."""
        reranker = JinaRerankerV3()
        result = reranker.rerank("query", [])
        assert result == []

    def test_rerank_maps_scores_correctly(self):
        """Reranking should map Jina scores back to SearchResult objects."""
        # Setup mock model with rerank method
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 1, "relevance_score": 0.95, "document": "code b"},
            {"index": 0, "relevance_score": 0.85, "document": "code a"},
        ]

        reranker = JinaRerankerV3()
        # Directly set the model to bypass lazy loading
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            ),
            SearchResult(
                chunk_id="b", score=0.8, metadata={"content_preview": "code b"}
            ),
        ]

        results = reranker.rerank("find function", candidates, top_k=2)

        assert len(results) == 2
        # Results should be in order returned by Jina (b first, higher score)
        assert results[0].chunk_id == "b"
        assert results[0].score == 0.95
        assert results[0].metadata["reranker_score"] == 0.95
        assert results[1].chunk_id == "a"
        assert results[1].score == 0.85

    def test_rerank_uses_content_preview(self):
        """Reranking should use content_preview from metadata."""
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 0, "relevance_score": 0.9, "document": "code a"}
        ]

        reranker = JinaRerankerV3()
        # Directly set the model to bypass lazy loading
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]

        reranker.rerank("test query", candidates, top_k=1)

        # Verify rerank was called with content_preview (with ID prefix)
        mock_model.rerank.assert_called_once()
        call_args = mock_model.rerank.call_args
        assert call_args[0][0] == "test query"  # Query
        assert call_args[0][1] == ["ID: a\ncode a"]  # Documents with ID prefix

    def test_rerank_prefers_bm25_text_over_content_preview(self):
        """Reranking should use the full bm25_text when present, not the ≤200-char preview."""
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 0, "relevance_score": 0.9, "document": "full source"}
        ]

        reranker = JinaRerankerV3()
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a",
                score=1.0,
                metadata={"bm25_text": "full source", "content_preview": "code a"},
            )
        ]

        reranker.rerank("test query", candidates, top_k=1)

        call_args = mock_model.rerank.call_args
        assert call_args[0][1] == ["ID: a\nfull source"]

    def test_rerank_truncates_document_to_doc_max_chars(self):
        """Body must be capped to doc_max_chars — listwise cost scales with total context."""
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 0, "relevance_score": 0.9, "document": "x" * 50}
        ]

        reranker = JinaRerankerV3(doc_max_chars=50)
        reranker._model = mock_model

        candidates = [
            SearchResult(chunk_id="a", score=1.0, metadata={"bm25_text": "x" * 5000})
        ]

        reranker.rerank("test query", candidates, top_k=1)

        call_args = mock_model.rerank.call_args
        assert call_args[0][1] == [f"ID: a\n{'x' * 50}"]

    def test_doc_max_chars_defaults_to_1000(self):
        reranker = JinaRerankerV3()
        assert reranker.doc_max_chars == 1000

    def test_rerank_fallback_to_chunk_id(self):
        """Should use chunk_id when content_preview is missing."""
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 0, "relevance_score": 0.9, "document": "chunk_a"}
        ]

        reranker = JinaRerankerV3()
        # Directly set the model to bypass lazy loading
        reranker._model = mock_model

        candidates = [
            SearchResult(chunk_id="chunk_a", score=1.0, metadata={})  # No content
        ]

        reranker.rerank("test query", candidates, top_k=1)

        # Verify rerank was called with chunk_id as fallback (with ID prefix)
        call_args = mock_model.rerank.call_args
        assert call_args[0][1] == ["ID: chunk_a\nchunk_a"]  # ID prefix + chunk_id

    @patch("transformers.AutoModel.from_pretrained")
    def test_cleanup_releases_resources(self, mock_model_class):
        """Cleanup should release model and tokenizer."""
        mock_model_class.return_value = MagicMock()

        reranker = JinaRerankerV3()
        _ = reranker.model  # Trigger loading
        assert reranker.is_loaded()

        reranker.cleanup()
        assert not reranker.is_loaded()
        assert reranker._model is None

    def test_device_auto_detection(self):
        """Device should be auto-detected when not specified."""
        reranker = JinaRerankerV3()
        if torch.cuda.is_available():
            assert reranker.device == "cuda"
        else:
            assert reranker.device == "cpu"

    def test_custom_device(self):
        """Custom device should be respected."""
        reranker = JinaRerankerV3(device="cpu")
        assert reranker.device == "cpu"

    def test_vram_usage_when_not_loaded(self):
        """VRAM usage should be 0 when model not loaded."""
        reranker = JinaRerankerV3()
        assert reranker.get_vram_usage() == 0.0

    def test_rerank_handles_numpy_indices(self):
        """Should handle numpy.int64 indices from Jina model."""
        import numpy as np

        mock_model = MagicMock()
        # Jina returns numpy.int64 indices, not Python int
        mock_model.rerank.return_value = [
            {"index": np.int64(1), "relevance_score": 0.95, "document": "code b"},
            {"index": np.int64(0), "relevance_score": 0.85, "document": "code a"},
        ]

        reranker = JinaRerankerV3()
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            ),
            SearchResult(
                chunk_id="b", score=0.8, metadata={"content_preview": "code b"}
            ),
        ]

        results = reranker.rerank("test query", candidates, top_k=2)

        # Should successfully map numpy.int64 indices to candidates
        assert len(results) == 2
        assert results[0].chunk_id == "b"
        assert results[0].score == 0.95
        assert results[1].chunk_id == "a"
        assert results[1].score == 0.85

    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.empty_cache")
    def test_rerank_releases_cuda_cache_on_success(
        self, mock_empty_cache, mock_is_available
    ):
        """Regression: successful rerank() must release cached allocator blocks.

        Jina's listwise architecture concatenates all candidates into one
        variable-length forward pass per call, so the CUDA caching allocator's
        reserved memory grows unboundedly across searches unless released after
        every call (unlike GTE/BGE's small, uniform pairwise batches). Verified
        on real hardware (RTX 4090): torch_reserved climbed 8.3GB -> 13.5GB over
        4 searches with this call missing; flat at 2.26GB with it present.
        """
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 0, "relevance_score": 0.9, "document": "code a"}
        ]
        reranker = JinaRerankerV3()
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        reranker.rerank("test query", candidates, top_k=1)

        mock_empty_cache.assert_called_once()

    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.empty_cache")
    def test_rerank_releases_cuda_cache_on_failure(
        self, mock_empty_cache, mock_is_available
    ):
        """Regression: a failed rerank() must still release cached blocks (finally)."""
        mock_model = MagicMock()
        mock_model.rerank.side_effect = RuntimeError("inference failed")
        reranker = JinaRerankerV3()
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]

        import pytest

        with pytest.raises(RuntimeError, match="Reranking failed"):
            reranker.rerank("test query", candidates, top_k=1)

        mock_empty_cache.assert_called_once()

    @patch("transformers.AutoModel.from_pretrained")
    @patch("transformers.AutoConfig.from_pretrained")
    def test_model_property_resets_on_validation_failure(
        self, mock_config_class, mock_from_pretrained
    ):
        """Model should be reset to None if rerank attribute check fails."""
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Return a model WITHOUT rerank method (but with to/eval)
        mock_model = MagicMock(spec=["to", "eval"])  # Has to/eval but NOT rerank
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = mock_model
        mock_from_pretrained.return_value = mock_model

        reranker = JinaRerankerV3()

        import pytest

        with pytest.raises(RuntimeError, match="does not support rerank"):
            _ = reranker.model

        # Critical: _model should be None so next access retries
        assert reranker._model is None

    def test_rerank_returns_full_ranked_list_not_truncated_to_top_k(self):
        """Regression: must not truncate to top_k before returning.

        rerank_by_query's dedupe_split_blocks backfills collapsed split_block
        fragments from the tail of the ranked list — truncating to top_k here
        first (top_n=top_k) starves that backfill, silently returning fewer
        than k results with no replacement. Scoring is already computed for
        every candidate in the same listwise forward pass, so returning all
        of them costs nothing extra.
        """
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 2, "relevance_score": 0.9, "document": "c"},
            {"index": 1, "relevance_score": 0.8, "document": "b"},
            {"index": 0, "relevance_score": 0.7, "document": "a"},
        ]
        reranker = JinaRerankerV3()
        reranker._model = mock_model

        candidates = [
            SearchResult(chunk_id=cid, score=1.0, metadata={"content_preview": cid})
            for cid in ("a", "b", "c")
        ]

        results = reranker.rerank("test query", candidates, top_k=1)

        assert len(results) == 3
        call_kwargs = mock_model.rerank.call_args.kwargs
        assert call_kwargs["top_n"] is None

    def test_rerank_passes_explicit_length_limits_to_model(self):
        """max_doc_length/max_query_length must be explicit, not left to jina's
        internal defaults — our doc_max_chars (chars) is the intended binding
        truncation and must be reconciled with jina's token-level truncation."""
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 0, "relevance_score": 0.9, "document": "code a"}
        ]
        reranker = JinaRerankerV3()
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        reranker.rerank("test query", candidates, top_k=1)

        call_kwargs = mock_model.rerank.call_args.kwargs
        assert call_kwargs["max_doc_length"] == 2048
        assert call_kwargs["max_query_length"] == 512

    def test_never_hand_builds_the_sandwich_prompt(self):
        """Lock-in for the paper's sandwich template (arXiv 2509.25085v4 sec 3.2):
        query-at-start -> passages-in-middle -> query-at-end, with the
        <|embed_token|>/<|rerank_token|> position markers. This module must keep
        delegating prompt construction to the model's own
        ``format_docs_prompts_func`` (via ``model.rerank()``) and never assemble
        the prompt string itself — hand-rolling it here would silently drift
        from the model's trained template on the next refactor.
        """
        import inspect

        import search.neural_reranker as neural_reranker_module

        source = inspect.getsource(neural_reranker_module)
        for marker in (
            "<passage id=",
            "<|embed_token|>",
            "<|rerank_token|>",
            "<query>",
        ):
            assert marker not in source, (
                f"Found sandwich-template literal {marker!r} in neural_reranker.py — "
                "prompt construction must stay delegated to the model's own "
                "format_docs_prompts_func, not hand-rolled here."
            )


class TestCreateRerankerFactoryJina:
    """Tests for create_reranker factory with Jina models."""

    def test_creates_jina_v3_reranker(self):
        """Should create JinaRerankerV3 for Jina v3 model."""
        reranker = create_reranker("jinaai/jina-reranker-v3")
        assert isinstance(reranker, JinaRerankerV3)
        assert reranker.model_name == "jinaai/jina-reranker-v3"

    def test_device_passed_to_jina_reranker(self):
        """Device parameter should be passed through to JinaRerankerV3."""
        reranker = create_reranker("jinaai/jina-reranker-v3", device="cpu")
        assert reranker.device == "cpu"

    def test_all_jina_models_in_registry(self):
        """All models in JINA_V3_RERANKERS should create JinaRerankerV3."""
        for model_name in JINA_V3_RERANKERS:
            reranker = create_reranker(model_name)
            assert isinstance(reranker, JinaRerankerV3)
            assert reranker.model_name == model_name
