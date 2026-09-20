"""Unit tests for JinaRerankerV3 and factory integration."""

from unittest.mock import MagicMock, patch

import pytest
import torch

from search.neural_reranker import (
    JINA_LISTWISE_RERANKERS,
    JinaRerankerV3,
    _packed_block_length,
    _simulate_listwise_blocks,
    create_reranker,
    derive_listwise_doc_budget,
    derive_listwise_model_max_length,
)
from search.reranker import SearchResult


class _FakeV3Model:
    """Real method (not a MagicMock) with v3's actual rerank() signature.

    A MagicMock can't catch the kwargs-TypeError bug this file guards against
    (it accepts any kwargs), so the length-kwargs resolver needs an object
    with a real, introspectable signature to test against.
    """

    def __init__(self):
        self.last_kwargs = None

    def rerank(
        self,
        query,
        documents,
        top_n=None,
        return_embeddings=False,
        max_doc_length=2048,
        max_query_length=512,
    ):
        self.last_kwargs = {
            "top_n": top_n,
            "return_embeddings": return_embeddings,
            "max_doc_length": max_doc_length,
            "max_query_length": max_query_length,
        }
        return [
            {"index": i, "relevance_score": 1.0 - i * 0.1, "document": doc}
            for i, doc in enumerate(documents)
        ]


class _FakeV35Model:
    """v3.5's actual rerank() signature — no max_doc_length/max_query_length
    params (both are hardcoded internally to 8192/1024). Passing either kwarg
    must raise TypeError; see test_v35_fake_rejects_length_kwargs.
    """

    def __init__(self):
        self.last_kwargs = None

    def rerank(self, query, documents, top_n=None, return_embeddings=False):
        self.last_kwargs = {
            "top_n": top_n,
            "return_embeddings": return_embeddings,
        }
        return [
            {"index": i, "relevance_score": 1.0 - i * 0.1, "document": doc}
            for i, doc in enumerate(documents)
        ]


class _FakeTokenizer:
    """Character-length token model: one token per character (id = ord(char)),
    truncated to ``max_length`` when requested. Deterministic and
    dependency-free, so window-bounding tests can size documents precisely by
    character count instead of needing a real tokenizer. ``decode`` inverts
    ``__call__`` exactly (``chr(id)``), so ADR-0077's truncate-and-decode
    solver round-trips predictably: a cap of N tokens decodes back to the
    document's first N characters.
    """

    def __init__(self, model_max_length: int = 131072):
        self.model_max_length = model_max_length

    def __call__(self, text, truncation=True, max_length=None):
        ids = [ord(c) for c in text]
        if truncation and max_length is not None:
            ids = ids[:max_length]
        return {"input_ids": ids}

    def decode(self, ids, skip_special_tokens=True):
        return "".join(chr(i) for i in ids)


class _FakeV3ModelWithTokenizer(_FakeV3Model):
    """_FakeV3Model plus the tokenizer surface ``_attempt_rerank`` mutates
    (``_ensure_tokenizer`` / ``_tokenizer.model_max_length``) -- a separate
    subclass rather than a change to ``_FakeV3Model`` itself, so every
    existing test built on the tokenizer-less fake keeps exercising the
    ``can_bound_window=False`` path unchanged (see test hazard #1 in the
    companion plan for docs/adr/0076-bound-the-listwise-packed-window-by-tokens.md).
    """

    def __init__(self):
        super().__init__()
        self._tokenizer = _FakeTokenizer()
        # Captured value of model_max_length while a rerank() call is in
        # flight, so tests can observe the mutation without reaching into
        # JinaRerankerV3 internals.
        self.model_max_length_during_call = None

    def _ensure_tokenizer(self):
        pass  # already constructed in __init__; nothing lazy to do

    def rerank(
        self,
        query,
        documents,
        top_n=None,
        return_embeddings=False,
        max_doc_length=2048,
        max_query_length=512,
    ):
        self.model_max_length_during_call = self._tokenizer.model_max_length
        return super().rerank(
            query,
            documents,
            top_n=top_n,
            return_embeddings=return_embeddings,
            max_doc_length=max_doc_length,
            max_query_length=max_query_length,
        )


class _FakeV35ModelWithTokenizer(_FakeV35Model):
    """_FakeV35Model plus a tokenizer surface -- proves the v3.5 gate keys
    off ``_resolve_length_kwargs`` being empty, not off tokenizer presence
    alone (a model that merely *has* ``_ensure_tokenizer`` must still be
    left untouched when it declares neither length pin).
    """

    def __init__(self):
        super().__init__()
        self._tokenizer = _FakeTokenizer()

    def _ensure_tokenizer(self):
        pass


class TestJinaRerankerV3:
    """Tests for JinaRerankerV3 class."""

    def test_lazy_loading(self):
        """Model should not load until first use."""
        reranker = JinaRerankerV3()
        assert reranker._model is None
        assert not reranker.is_loaded()

    def test_dtype_defaults_to_auto(self):
        """Default dtype must stay "auto" (checkpoint default, bf16) — the
        fp32 determinism option is opt-in with zero default behavior change."""
        reranker = JinaRerankerV3()
        assert reranker.dtype == "auto"

    def test_dtype_stored_when_valid(self):
        for dtype in ("auto", "fp32", "bf16", "fp16"):
            assert JinaRerankerV3(dtype=dtype).dtype == dtype

    def test_invalid_dtype_raises_at_construction(self):
        """Bad dtype values must fail fast, not at first (lazy) model load."""
        with pytest.raises(ValueError, match="Unsupported reranker dtype"):
            JinaRerankerV3(dtype="float64")

    def test_dtype_map_resolves_to_torch_dtypes(self):
        """DTYPE_MAP is what _load_or_fetch passes to from_pretrained (and to
        the post-load .to() cast covering the TypeError fallback path)."""
        assert JinaRerankerV3.DTYPE_MAP["auto"] == "auto"
        assert JinaRerankerV3.DTYPE_MAP["fp32"] is torch.float32
        assert JinaRerankerV3.DTYPE_MAP["bf16"] is torch.bfloat16
        assert JinaRerankerV3.DTYPE_MAP["fp16"] is torch.float16

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
    @patch("transformers.AutoConfig.from_pretrained")
    def test_cleanup_releases_resources(self, mock_config_class, mock_model_class):
        """Cleanup should release model and tokenizer."""
        mock_config_class.return_value = MagicMock()
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

    def test_pins_length_limits_when_model_declares_them(self):
        """max_doc_length/max_query_length must be explicit on checkpoints that
        declare them (v3) — our doc_max_chars (chars) is the intended binding
        truncation and must be reconciled with jina's token-level truncation."""
        fake_model = _FakeV3Model()
        reranker = JinaRerankerV3()
        reranker._model = fake_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        reranker.rerank("test query", candidates, top_k=1)

        assert fake_model.last_kwargs["max_doc_length"] == 2048
        assert fake_model.last_kwargs["max_query_length"] == 512

    def test_omits_length_limits_when_model_does_not_declare_them(self):
        """v3.5's rerank() has no max_doc_length/max_query_length params —
        passing them raises TypeError (test_v35_fake_rejects_length_kwargs).
        Regression test for the actual v3.5 adoption blocker."""
        fake_model = _FakeV35Model()
        reranker = JinaRerankerV3()
        reranker._model = fake_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        # Must not raise TypeError.
        results = reranker.rerank("test query", candidates, top_k=1)

        assert len(results) == 1
        assert "max_doc_length" not in fake_model.last_kwargs
        assert "max_query_length" not in fake_model.last_kwargs

    def test_v35_fake_rejects_length_kwargs(self):
        """Guard for the fixture itself: if _FakeV35Model were ever
        "simplified" back into a MagicMock,
        test_omits_length_limits_when_model_does_not_declare_them would pass
        for the wrong reason (a MagicMock accepts any kwargs). Locks in that
        the fake actually reproduces v3.5's TypeError."""
        fake_model = _FakeV35Model()
        with pytest.raises(TypeError):
            fake_model.rerank("q", ["d"], max_doc_length=2048)

    def test_resolve_length_kwargs_is_memoized_and_resets_on_cleanup(self):
        """Signature introspection should run once per load, not per rerank
        call, and must re-introspect after a cleanup()/reload cycle (e.g. a
        config swap from v3 to v3.5)."""
        fake_v3 = _FakeV3Model()
        reranker = JinaRerankerV3()

        first = reranker._resolve_length_kwargs(fake_v3)
        second = reranker._resolve_length_kwargs(fake_v3)
        assert first == {"max_doc_length": 2048, "max_query_length": 512}
        assert second is first  # memoized, same dict object

        reranker._cleanup_extra()
        fake_v35 = _FakeV35Model()
        third = reranker._resolve_length_kwargs(fake_v35)
        assert third == {}
        assert third is not first

    def test_resolve_length_kwargs_handles_unintrospectable_callable(self):
        """A model whose rerank() can't be introspected must degrade to
        omitting the length pins, not crash."""
        fake_model = _FakeV3Model()
        reranker = JinaRerankerV3()

        with patch(
            "search.neural_reranker.inspect.signature",
            side_effect=ValueError("no signature found"),
        ):
            result = reranker._resolve_length_kwargs(fake_model)

        assert result == {}

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


class TestDeriveListwiseModelMaxLength:
    """Pure-function tests for the M-derivation -- ADR-0076's split backstop,
    demoted by ADR-0077 (docs/adr/0076-bound-the-listwise-packed-window-by-tokens.md,
    docs/adr/0077-single-block-listwise-invariant.md).

    ``derive_listwise_model_max_length`` / ``_simulate_listwise_blocks`` /
    ``_packed_block_length`` need only doc lengths, query length, and budget
    -- no tokenizer or model involved, per test hazard #1 in the companion
    plan (``_FakeV3Model`` has no ``_tokenizer``). The old soft top-k
    invariant (and its ``top_k``/``logger`` params) was removed under
    ADR-0077: multi-block splitting is now only reached as a backstop after
    the single-block truncation solver (``derive_listwise_doc_budget``,
    below) under- or over-shoots, so there is no "un-degraded top-k slice"
    left to protect here -- the invariant lives upstream instead.
    """

    def test_dense_docs_produce_multiple_blocks(self):
        """30 docs at ~1000 tokens each vastly exceed an 8192 budget -- the
        derived M must force more than one block."""
        doc_lengths = [1000] * 30
        m = derive_listwise_model_max_length(
            doc_lengths, query_length=20, budget=8192, max_doc_length=2048
        )
        blocks = _simulate_listwise_blocks(doc_lengths, 20, m, 2048)
        assert len(blocks) > 1

    def test_sparse_docs_produce_a_single_block(self):
        """A handful of short docs comfortably fits an 8192 budget in one
        block -- no behaviour change vs. today on the unsplit Python canon."""
        doc_lengths = [100] * 5
        m = derive_listwise_model_max_length(
            doc_lengths, query_length=20, budget=8192, max_doc_length=2048
        )
        blocks = _simulate_listwise_blocks(doc_lengths, 20, m, 2048)
        assert len(blocks) == 1

    def test_every_simulated_block_fits_the_budget(self):
        """Regardless of corpus shape, every simulated block at the derived
        M must pack within budget tokens."""
        doc_lengths = [1500, 200, 1800, 50, 1999, 300, 1700, 20, 1600, 900]
        query_length, budget, max_doc_length = 64, 4096, 2048
        m = derive_listwise_model_max_length(
            doc_lengths, query_length, budget, max_doc_length
        )
        blocks = _simulate_listwise_blocks(doc_lengths, query_length, m, max_doc_length)
        assert blocks  # sanity: simulation produced something to check
        for block in blocks:
            assert _packed_block_length(block, query_length) <= budget

    def test_never_drops_below_the_floor(self):
        """Even a pathologically small budget -- too small to fit even one
        document plus overhead -- must not push M below the absolute floor
        (2q + max_doc_length + 1, one document's worth of headroom)."""
        doc_lengths = [2048] * 50
        query_length, budget, max_doc_length = 512, 2048, 2048
        m = derive_listwise_model_max_length(
            doc_lengths, query_length, budget, max_doc_length
        )
        floor = 2 * query_length + max_doc_length + 1
        assert m >= floor


class TestDeriveListwiseDocBudget:
    """Pure-function tests for the ADR-0077 single-block truncation solver.

    ``derive_listwise_doc_budget`` is the uniform per-document token cap
    that, applied to every document, guarantees the packed window fits one
    listwise block -- the mechanism the single-block invariant is built on.
    """

    def test_short_docs_are_never_capped_below_their_own_length(self):
        """When every document already fits comfortably, the solver must not
        trim anything -- the cap should be >= the longest document."""
        doc_lengths = [50, 80, 120, 60]
        cap = derive_listwise_doc_budget(doc_lengths, query_length=20, budget=8192)
        assert cap >= max(doc_lengths)

    def test_dense_docs_are_capped_below_their_own_length(self):
        """30 docs at 1000 tokens each vastly exceed an 8192 budget -- the
        solver must lower the cap below 1000 so the packed set fits."""
        doc_lengths = [1000] * 30
        cap = derive_listwise_doc_budget(doc_lengths, query_length=20, budget=8192)
        assert cap < 1000
        packed = sum(min(length, cap) for length in doc_lengths)
        assert (
            _packed_block_length([min(length, cap) for length in doc_lengths], 20)
            <= 8192
        )
        assert packed > 0  # sanity: not degenerately zeroed out

    def test_only_long_documents_are_trimmed_uniform_cap(self):
        """A mix of long and short documents: short ones must be left
        untouched by the uniform cap while long ones get trimmed to it."""
        doc_lengths = [50, 3000, 80, 4000, 60]
        cap = derive_listwise_doc_budget(doc_lengths, query_length=20, budget=2048)
        trimmed = [min(length, cap) for length in doc_lengths]
        assert trimmed[0] == doc_lengths[0]  # 50, short -- untouched
        assert trimmed[2] == doc_lengths[2]  # 80, short -- untouched
        assert trimmed[1] == cap  # 3000, long -- trimmed to cap
        assert trimmed[3] == cap  # 4000, long -- trimmed to cap

    def test_cap_monotonically_increases_with_budget(self):
        """More budget must never produce a smaller (or worse) cap -- the
        binary search relies on packed() being monotonic in the cap."""
        doc_lengths = [1200] * 15
        small = derive_listwise_doc_budget(doc_lengths, query_length=20, budget=4096)
        large = derive_listwise_doc_budget(doc_lengths, query_length=20, budget=16384)
        assert large >= small

    def test_zero_when_overhead_alone_exceeds_budget(self):
        """A pathologically tiny budget that can't even cover the fixed +
        per-document + query overhead must return 0, signalling the caller
        to fall back to a lighter representation or the split backstop."""
        doc_lengths = [500] * 50
        cap = derive_listwise_doc_budget(doc_lengths, query_length=2000, budget=128)
        assert cap == 0

    def test_empty_doc_lengths_returns_zero(self):
        assert derive_listwise_doc_budget([], query_length=20, budget=8192) == 0


class TestFitSingleBlock:
    """Tests for the ADR-0077 truncate-then-verify solver
    (``JinaRerankerV3._fit_single_block``), exercised directly against
    ``_FakeTokenizer`` rather than through ``rerank()`` -- isolates the
    floor -> ``signature_head`` swap and the decode-and-verify path from
    OOM retry / model-loading machinery.
    """

    def test_short_docs_pass_through_untouched(self):
        reranker = JinaRerankerV3(listwise_packed_token_budget=8192)
        tokenizer = _FakeTokenizer()
        documents = ["short doc " * 3, "another short one"]
        result_docs, _model_max_length, block_count = reranker._fit_single_block(
            tokenizer,
            documents,
            None,
            query_length=20,
            budget=8192,
            max_doc_length=2048,
        )
        assert result_docs == documents
        assert block_count == 1
        # Docs passed through untouched, so the solved cap must not have
        # bound below the longest document's length.
        assert reranker.last_doc_token_cap >= max(len(d) for d in documents)

    def test_long_doc_is_truncated_and_decodes_to_a_prefix(self):
        """A document far longer than the derived cap must be truncated to
        exactly its first N characters -- proving the token-cap -> decode
        round-trip is exact under the character-per-token fake."""
        reranker = JinaRerankerV3(listwise_packed_token_budget=1024)
        tokenizer = _FakeTokenizer()
        long_doc = "x" * 5000
        result_docs, _model_max_length, block_count = reranker._fit_single_block(
            tokenizer,
            [long_doc],
            None,
            query_length=20,
            budget=1024,
            max_doc_length=2048,
        )
        assert len(result_docs) == 1
        assert result_docs[0] == long_doc[: len(result_docs[0])]
        assert len(result_docs[0]) < len(long_doc)
        assert block_count == 1
        # _FakeTokenizer is 1-char-per-token and decode/encode round-trips
        # exactly, so the recorded cap must equal the truncated length.
        assert reranker.last_doc_token_cap == len(result_docs[0])

    def test_header_inclusive_accounting_fits_under_budget(self):
        """The final packed length (fixed + per-doc overhead + doc tokens +
        2*query_length), recomputed over the TRUNCATED documents, must fit
        the budget -- the whole point of the solver, not just the raw
        pre-truncation doc cap."""
        reranker = JinaRerankerV3(listwise_packed_token_budget=2048)
        tokenizer = _FakeTokenizer()
        documents = ["y" * 3000, "z" * 3000, "short"]
        result_docs, _model_max_length, block_count = reranker._fit_single_block(
            tokenizer,
            documents,
            None,
            query_length=50,
            budget=2048,
            max_doc_length=2048,
        )
        final_lengths = [
            len(tokenizer(doc, truncation=True, max_length=2048)["input_ids"])
            for doc in result_docs
        ]
        assert _packed_block_length(final_lengths, 50) <= 2048
        assert block_count == 1
        assert reranker.last_doc_token_cap is not None

    def test_floor_swaps_to_fallback_documents(self):
        """When the solved cap for "full" documents falls below
        ``_LISTWISE_MIN_DOC_TOKEN_ALLOWANCE``, the solver must swap to
        ``fallback_documents`` (a lighter signature_head rendering) rather
        than truncate the full text into a sliver."""
        reranker = JinaRerankerV3(listwise_packed_token_budget=500)
        tokenizer = _FakeTokenizer()
        documents = ["f" * 1000 for _ in range(10)]
        fallback_documents = ["s" * 50 for _ in range(10)]
        result_docs, _model_max_length, block_count = reranker._fit_single_block(
            tokenizer,
            documents,
            fallback_documents,
            query_length=20,
            budget=500,
            max_doc_length=2048,
        )
        assert result_docs != documents
        for doc in result_docs:
            assert doc == "" or doc.startswith("s")
        assert block_count == 1
        # Recorded cap reflects the post-swap solve against the lighter
        # fallback_documents, not the original (too-narrow) full-text cap.
        assert reranker.last_doc_token_cap is not None

    def test_no_fallback_and_below_floor_degrades_to_split_backstop(self):
        """No ``fallback_documents`` provided (``doc_representation_mode``
        is already ``signature_head``, or the ``split`` escape hatch chose
        this path) and the solved cap can't fit even the truncated set into
        one block -- must not silently under-fill; degrades to the
        ADR-0076 split backstop (``block_count`` may exceed 1) with a
        logged warning rather than risking an OOM."""
        reranker = JinaRerankerV3(listwise_packed_token_budget=300)
        tokenizer = _FakeTokenizer()
        documents = ["f" * 1000 for _ in range(10)]
        with patch.object(reranker._logger, "warning") as mock_warning:
            _result_docs, _model_max_length, block_count = reranker._fit_single_block(
                tokenizer,
                documents,
                None,
                query_length=20,
                budget=300,
                max_doc_length=2048,
            )
        assert block_count >= 1
        mock_warning.assert_called_once()
        # Cap is recorded even on the degradation path -- it reflects the
        # attempted (too-narrow) solve, not a control input.
        assert reranker.last_doc_token_cap is not None


class TestListwiseWindowBounding:
    """Integration-level tests for JinaRerankerV3's window-bounding
    mechanism: model_max_length mutation/restoration, the v3.5 gate, and
    the Tier-2 halved-budget OOM retry
    (docs/adr/0076-bound-the-listwise-packed-window-by-tokens.md).
    """

    def test_model_max_length_mutated_during_call_and_restored_after(self):
        fake_model = _FakeV3ModelWithTokenizer()
        original = fake_model._tokenizer.model_max_length
        reranker = JinaRerankerV3(listwise_packed_token_budget=8192)
        reranker._model = fake_model

        candidates = [
            SearchResult(
                chunk_id=str(i), score=1.0, metadata={"content_preview": "x" * 50}
            )
            for i in range(3)
        ]
        reranker.rerank("query", candidates, top_k=3)

        assert fake_model.model_max_length_during_call is not None
        assert fake_model.model_max_length_during_call < original
        assert fake_model._tokenizer.model_max_length == original
        assert reranker.last_block_count == 1
        # ADR-0077: derive_listwise_doc_budget's binary search never returns
        # above max(doc_lengths) (see its `hi = max(doc_lengths)` -- there is
        # no reason to solve for a cap larger than the longest document), so
        # three tiny "x"*50 documents at budget=8192 solve to a small cap
        # regardless of the floor -- the invariant engaged (block count 1)
        # without needing to trim anything meaningfully; the floor->
        # signature_head swap is covered separately by
        # TestFitSingleBlock.test_floor_swaps_to_fallback_documents.
        assert reranker.last_doc_token_cap is not None

    def test_model_max_length_restored_on_exception_path(self):
        """The tokenizer is shared, cached state on a long-lived model --
        a failed rerank() call must not leave model_max_length lowered."""
        fake_model = _FakeV3ModelWithTokenizer()
        original = fake_model._tokenizer.model_max_length

        # A bare `lambda *a, **k` would erase the named max_doc_length/
        # max_query_length params _resolve_length_kwargs introspects for,
        # making can_bound_window False -- which would skip model_max_length
        # mutation (and _fit_single_block) entirely, defeating this test's
        # own purpose. Keep the real signature so can_bound_window stays
        # True and the raise happens where the vendor call actually is.
        def _boom(
            query,
            documents,
            top_n=None,
            return_embeddings=False,
            max_doc_length=2048,
            max_query_length=512,
        ):
            raise RuntimeError("inference blew up")

        fake_model.rerank = _boom

        reranker = JinaRerankerV3(listwise_packed_token_budget=8192)
        reranker._model = fake_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        with pytest.raises(RuntimeError, match="Reranking failed"):
            reranker.rerank("query", candidates, top_k=1)

        assert fake_model._tokenizer.model_max_length == original
        # ADR-0077: last_block_count only gets assigned from a *returned*
        # _attempt_rerank call (rerank():1479), so it stays None here -- the
        # exception aborted before that line ran. last_doc_token_cap is
        # different: _fit_single_block sets it as a side effect INSIDE
        # _attempt_rerank, before the model.rerank() call that raised, so it
        # is populated even though the overall call failed. This is the
        # documented asymmetry (see JinaRerankerV3.__init__'s
        # last_doc_token_cap comment) -- last_doc_token_cap reflects the last
        # *attempted* solve, not only the last successful one.
        assert reranker.last_block_count is None
        assert reranker.last_doc_token_cap is not None

    def test_v35_gate_tokenizer_not_mutated_when_length_kwargs_empty(self):
        """v3.5's rerank() declares neither max_doc_length nor
        max_query_length, so _resolve_length_kwargs is empty and
        can_bound_window must be False even though this fake exposes a
        _tokenizer/_ensure_tokenizer surface -- proves the gate keys off
        length_kwargs emptiness, not tokenizer presence alone."""
        fake_model = _FakeV35ModelWithTokenizer()
        original = fake_model._tokenizer.model_max_length
        reranker = JinaRerankerV3(listwise_packed_token_budget=8192)
        reranker._model = fake_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        results = reranker.rerank("query", candidates, top_k=1)

        assert len(results) == 1
        assert fake_model._tokenizer.model_max_length == original
        assert reranker.last_block_count is None
        # can_bound_window is False for v3.5, so _fit_single_block never runs.
        assert reranker.last_doc_token_cap is None

    def test_oom_retries_once_at_half_budget_then_succeeds(self):
        reranker = JinaRerankerV3(listwise_packed_token_budget=8192)
        reranker._model = _FakeV3ModelWithTokenizer()

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        seen_budgets = []

        def fake_attempt(
            model,
            query,
            documents,
            length_kwargs,
            budget,
            top_k,
            can_bound_window,
            fallback_documents=None,
        ):
            seen_budgets.append(budget)
            if len(seen_budgets) == 1:
                raise torch.cuda.OutOfMemoryError("CUDA out of memory.")
            return (
                [{"index": 0, "relevance_score": 0.9, "document": documents[0]}],
                1,
            )

        with patch.object(reranker, "_attempt_rerank", side_effect=fake_attempt):
            results = reranker.rerank("query", candidates, top_k=1)

        assert len(results) == 1
        assert seen_budgets == [8192, 4096]

    def test_oom_exhausted_raises_runtime_error_matching_session_disable_string(self):
        """RerankingEngine._run_rerank detects OOM by string-matching "cuda"
        + "out of memory"/"oom" on str(e) -- the re-raised RuntimeError's
        message must preserve that verbatim, or the session-sticky disable
        backstop silently breaks."""
        reranker = JinaRerankerV3(listwise_packed_token_budget=8192)
        reranker._model = _FakeV3ModelWithTokenizer()

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        with (
            patch.object(
                reranker,
                "_attempt_rerank",
                side_effect=torch.cuda.OutOfMemoryError(
                    "CUDA out of memory. Tried to allocate 2.00 GiB"
                ),
            ),
            pytest.raises(
                RuntimeError, match="Insufficient GPU memory for reranking"
            ) as exc_info,
        ):
            reranker.rerank("query", candidates, top_k=1)

        message = str(exc_info.value).lower()
        assert "cuda" in message
        assert "out of memory" in message or "oom" in message

    def test_no_retry_when_window_cannot_be_bounded(self):
        """v3.5 (or any checkpoint whose rerank() declares neither length
        pin) has nothing a retry could change -- only one attempt should
        run even on OOM."""
        reranker = JinaRerankerV3(listwise_packed_token_budget=8192)
        reranker._model = _FakeV35Model()

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        seen_budgets = []

        def fake_attempt(
            model,
            query,
            documents,
            length_kwargs,
            budget,
            top_k,
            can_bound_window,
            fallback_documents=None,
        ):
            seen_budgets.append(budget)
            raise torch.cuda.OutOfMemoryError("CUDA out of memory.")

        with (
            patch.object(reranker, "_attempt_rerank", side_effect=fake_attempt),
            pytest.raises(RuntimeError, match="Insufficient GPU memory for reranking"),
        ):
            reranker.rerank("query", candidates, top_k=1)

        assert seen_budgets == [8192]

    def test_vendor_compute_single_batch_never_passes_truncation(self):
        """Guard against a future jinaai/jina-reranker-v3 republish silently
        changing _compute_single_batch to truncate its packed prompt.

        Today (cached revision 10fb694fc21f...) _compute_single_batch's
        tokenizer call passes no truncation=True, which is what makes a
        lowered model_max_length (see derive_listwise_model_max_length)
        only widen block count -- never silently drop content. No upstream
        revision is pinned anywhere in this repo (see the ADR's "Standing
        risk" section), so this is a real, not hypothetical, risk. Reads
        the cached trust_remote_code module straight off disk (no network
        call); skips rather than fails when it isn't cached locally.
        """
        import ast
        import glob
        import os

        from transformers.utils import HF_MODULES_CACHE

        candidates = glob.glob(
            os.path.join(
                HF_MODULES_CACHE,
                "transformers_modules",
                "jinaai",
                "jina_hyphen_reranker_hyphen_v3",
                "*",
                "modeling.py",
            )
        )
        if not candidates:
            pytest.skip(
                "jinaai/jina-reranker-v3 trust_remote_code module not cached locally"
            )

        with open(candidates[0], encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        method_source = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_compute_single_batch"
            ):
                method_source = ast.get_source_segment(source, node)
                break
        assert method_source is not None, (
            "_compute_single_batch not found in vendor modeling.py -- "
            "the vendor module's shape has changed; re-check this guard."
        )
        assert "truncation" not in method_source, (
            "jinaai/jina-reranker-v3's _compute_single_batch now references "
            "truncation -- a lowered model_max_length (see "
            "derive_listwise_model_max_length) could silently truncate the "
            "packed prompt instead of just widening block count. Re-derive "
            "the token-budget math in "
            "docs/adr/0076-bound-the-listwise-packed-window-by-tokens.md."
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
        """All models in JINA_LISTWISE_RERANKERS should create JinaRerankerV3."""
        for model_name in JINA_LISTWISE_RERANKERS:
            reranker = create_reranker(model_name)
            assert isinstance(reranker, JinaRerankerV3)
            assert reranker.model_name == model_name

    def test_listwise_packed_token_budget_passed_to_jina_reranker(self):
        """RerankerConfig.listwise_packed_token_budget must thread through
        the factory to JinaRerankerV3, not silently fall back to the
        default (docs/adr/0076-bound-the-listwise-packed-window-by-tokens.md)."""
        reranker = create_reranker(
            "jinaai/jina-reranker-v3", listwise_packed_token_budget=4096
        )
        assert reranker.listwise_packed_token_budget == 4096

    def test_listwise_packed_token_budget_defaults_to_8192(self):
        reranker = create_reranker("jinaai/jina-reranker-v3")
        assert reranker.listwise_packed_token_budget == 8192

    def test_listwise_window_fit_passed_to_jina_reranker(self):
        """RerankerConfig.listwise_window_fit must thread through the
        factory to JinaRerankerV3, not silently fall back to the default
        (docs/adr/0077-single-block-listwise-invariant.md)."""
        reranker = create_reranker(
            "jinaai/jina-reranker-v3", listwise_window_fit="split"
        )
        assert reranker.listwise_window_fit == "split"

    def test_listwise_window_fit_defaults_to_truncate(self):
        reranker = create_reranker("jinaai/jina-reranker-v3")
        assert reranker.listwise_window_fit == "truncate"
