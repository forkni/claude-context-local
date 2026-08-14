"""Unit tests for GenerativeReranker and create_reranker factory."""

from unittest.mock import MagicMock, patch

import pytest
import torch

from search.neural_reranker import (
    GENERATIVE_RERANKERS,
    GenerativeReranker,
    NeuralReranker,
    create_reranker,
)
from search.reranker import SearchResult


class TestGenerativeReranker:
    """Tests for GenerativeReranker class."""

    def test_lazy_loading(self):
        """Model should not load until first use."""
        reranker = GenerativeReranker()
        assert reranker._model is None
        assert reranker._tokenizer is None
        assert not reranker.is_loaded()

    def test_rerank_empty_candidates(self):
        """Empty candidates should return empty list."""
        reranker = GenerativeReranker()
        result = reranker.rerank("query", [])
        assert result == []

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_adds_score_metadata(self, mock_tokenizer_class, mock_model_class):
        """Reranking should add reranker_score to metadata (batched inference)."""
        seq_len = 10
        vocab_size = 1000
        batch_size = 2
        yes_id, no_id = 100, 101

        # Logits: shape [batch, seq_len, vocab_size]
        logits_tensor = torch.zeros(batch_size, seq_len, vocab_size)
        logits_tensor[0, -1, yes_id] = 2.0  # Candidate 0: P(Yes) high
        logits_tensor[0, -1, no_id] = 0.5
        logits_tensor[1, -1, yes_id] = 0.5  # Candidate 1: P(Yes) lower
        logits_tensor[1, -1, no_id] = 2.0

        # Mock tokenizer (lowercase "yes"/"no" per the official Qwen3-Reranker template)
        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                # Force the fallback to encode()-based resolution in these tests —
                # the encode() variants below set up the yes/no distinction.
                return None

            def encode(self, text, **kwargs):
                return [yes_id] if text in ("yes", " yes") else [no_id]

            def __call__(self, prompts, **kwargs):
                n = len(prompts) if isinstance(prompts, list) else 1
                mock_inputs = {
                    "input_ids": torch.ones(n, seq_len, dtype=torch.long),
                    "attention_mask": torch.ones(n, seq_len, dtype=torch.long),
                }

                # Add .to() method that returns self
                class TensorDict(dict):
                    def to(self, device):
                        return self

                return TensorDict(mock_inputs)

        # Mock model
        class MockModel:
            def to(self, device):
                return self

            def __call__(self, **inputs):
                class Outputs:
                    logits = logits_tensor

                return Outputs()

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MockModel()

        reranker = GenerativeReranker(device="cpu")
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
        assert "reranker_score" in results[0].metadata
        assert isinstance(results[0].metadata["reranker_score"], float)
        assert 0.0 <= results[0].metadata["reranker_score"] <= 1.0
        # First result should have higher score (candidate "a" has high Yes logit)
        assert results[0].chunk_id == "a"
        assert (
            results[0].metadata["reranker_score"]
            > results[1].metadata["reranker_score"]
        )

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_uses_official_qwen3_template(
        self, mock_tokenizer_class, mock_model_class
    ):
        """Regression: prompts must use the official Qwen3-Reranker instruct template.

        Root-cause regression test for the bug where an ad-hoc "Query: ...\\nDocument:
        ..." prompt with capitalized Yes/No tokens was off-distribution for the
        fine-tuned model and produced inverted/poorly-calibrated relevance scores
        (see arXiv:2506.05176 §2 "Reranking Models"). Captures the exact prompts sent
        to the tokenizer and asserts on the required structural markers.
        """
        seq_len = 10
        vocab_size = 1000
        yes_id, no_id = 100, 101
        logits_tensor = torch.zeros(1, seq_len, vocab_size)
        logits_tensor[0, -1, yes_id] = 2.0
        logits_tensor[0, -1, no_id] = 0.5

        captured_prompts = []

        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                # Force the fallback to encode()-based resolution in these tests —
                # the encode() variants below set up the yes/no distinction.
                return None

            def encode(self, text, **kwargs):
                return [yes_id] if text in ("yes", " yes") else [no_id]

            def __call__(self, prompts, **kwargs):
                captured_prompts.extend(prompts)
                n = len(prompts)
                mock_inputs = {
                    "input_ids": torch.ones(n, seq_len, dtype=torch.long),
                    "attention_mask": torch.ones(n, seq_len, dtype=torch.long),
                }

                class TensorDict(dict):
                    def to(self, device):
                        return self

                return TensorDict(mock_inputs)

        class MockModel:
            def to(self, device):
                return self

            def __call__(self, **inputs):
                class Outputs:
                    logits = logits_tensor

                return Outputs()

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MockModel()

        reranker = GenerativeReranker(device="cpu")
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        reranker.rerank("find function", candidates, top_k=1)

        assert len(captured_prompts) == 1
        prompt = captured_prompts[0]
        assert "<|im_start|>system" in prompt
        assert "<|im_start|>user" in prompt
        assert "<|im_start|>assistant" in prompt
        assert "<Instruct>:" in prompt
        assert "<Query>: find function" in prompt
        # Document body carries the ID: {chunk_id} structural-context prefix
        # (parity with JinaRerankerV3 — see _build_rerank_document).
        assert "<Document>: ID: a\ncode a" in prompt
        assert "<think>" in prompt
        # The ad-hoc prompt this replaces never appears in the official template.
        assert "Is this document relevant to the query? Answer Yes or No:" not in prompt

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_cleanup_releases_resources(self, mock_tokenizer_class, mock_model_class):
        """Cleanup should release model and tokenizer."""
        mock_tokenizer_class.return_value = MagicMock()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker()
        _ = reranker.model  # Trigger loading
        assert reranker.is_loaded()

        reranker.cleanup()
        assert not reranker.is_loaded()
        assert reranker._model is None
        assert reranker._tokenizer is None

    def test_device_auto_detection(self):
        """Device should be auto-detected when not specified."""
        reranker = GenerativeReranker()
        if torch.cuda.is_available():
            assert reranker.device == "cuda"
        else:
            assert reranker.device == "cpu"

    def test_custom_device(self):
        """Custom device should be respected."""
        reranker = GenerativeReranker(device="cpu")
        assert reranker.device == "cpu"

    def test_vram_usage_when_not_loaded(self):
        """VRAM usage should be 0 when model not loaded."""
        reranker = GenerativeReranker()
        assert reranker.get_vram_usage() == 0.0

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_fallback_on_error(self, mock_tokenizer_class, mock_model_class):
        """Should return candidates in original order on inference failure."""

        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                return None

            def encode(self, text, **kwargs):
                return [100] if text in ("yes", " yes") else [101]

            def __call__(self, prompts, **kwargs):
                raise RuntimeError("Simulated tokenization failure")

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cpu")
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            ),
            SearchResult(
                chunk_id="b", score=0.8, metadata={"content_preview": "code b"}
            ),
        ]

        results = reranker.rerank("query", candidates, top_k=2)

        # Should return candidates with original scores preserved
        assert len(results) == 2
        assert results[0].chunk_id == "a"
        assert results[0].metadata["original_score"] == 1.0
        assert results[0].metadata["reranker_score"] == 1.0
        assert results[1].chunk_id == "b"
        assert results[1].metadata["original_score"] == 0.8
        assert results[1].metadata["reranker_score"] == 0.8

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_fallback_on_token_resolution_failure(
        self, mock_tokenizer_class, mock_model_class
    ):
        """Should return original scores when tokenizer can't resolve yes/no tokens."""

        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                return None

            def encode(self, text, **kwargs):
                # Always return multi-token for both "yes"/" yes" and "no"/" no"
                return [10, 20]  # Multi-token

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cpu")
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            ),
            SearchResult(
                chunk_id="b", score=0.8, metadata={"content_preview": "code b"}
            ),
        ]

        results = reranker.rerank("query", candidates, top_k=2)

        # Should return candidates with original scores preserved (fallback)
        assert len(results) == 2
        assert results[0].chunk_id == "a"
        assert results[0].metadata["original_score"] == 1.0
        assert results[0].metadata["reranker_score"] == 1.0
        assert results[1].chunk_id == "b"
        assert results[1].metadata["original_score"] == 0.8
        assert results[1].metadata["reranker_score"] == 0.8

    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.empty_cache")
    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_releases_cuda_cache_on_success(
        self,
        mock_tokenizer_class,
        mock_model_class,
        mock_empty_cache,
        mock_is_available,
    ):
        """Regression: successful rerank() must release cached allocator blocks.

        Pool-wide policy (measured evidence in JinaRerankerV3.rerank()): release
        cached-but-unused CUDA allocator blocks after every call, for every reranker
        class in the pool — not just Jina. Previously this class only called
        empty_cache() on the OOM/failure branch; now it fires via `finally` on both
        success and failure.
        """
        seq_len = 10
        vocab_size = 1000
        yes_id, no_id = 100, 101
        logits_tensor = torch.zeros(1, seq_len, vocab_size)
        logits_tensor[0, -1, yes_id] = 2.0
        logits_tensor[0, -1, no_id] = 0.5

        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                # Force the fallback to encode()-based resolution in these tests —
                # the encode() variants below set up the yes/no distinction.
                return None

            def encode(self, text, **kwargs):
                return [yes_id] if text in ("yes", " yes") else [no_id]

            def __call__(self, prompts, **kwargs):
                n = len(prompts) if isinstance(prompts, list) else 1
                mock_inputs = {
                    "input_ids": torch.ones(n, seq_len, dtype=torch.long),
                    "attention_mask": torch.ones(n, seq_len, dtype=torch.long),
                }

                class TensorDict(dict):
                    def to(self, device):
                        return self

                return TensorDict(mock_inputs)

        class MockModel:
            def to(self, device):
                return self

            def __call__(self, **inputs):
                class Outputs:
                    logits = logits_tensor

                return Outputs()

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MockModel()

        reranker = GenerativeReranker(device="cpu")
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        reranker.rerank("find function", candidates, top_k=1)

        mock_empty_cache.assert_called_once()

    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.empty_cache")
    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_releases_cuda_cache_on_failure(
        self,
        mock_tokenizer_class,
        mock_model_class,
        mock_empty_cache,
        mock_is_available,
    ):
        """Regression: a failed rerank() must still release cached blocks (finally).

        Reuses the tokenization-failure scenario from test_rerank_fallback_on_error.
        Before this fix, empty_cache() was called explicitly inside the except branch;
        now it's called once via `finally`, so the count must stay exactly 1 — not 2.
        """

        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                return None

            def encode(self, text, **kwargs):
                return [100] if text in ("yes", " yes") else [101]

            def __call__(self, prompts, **kwargs):
                raise RuntimeError("Simulated tokenization failure")

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cpu")
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]

        results = reranker.rerank("query", candidates, top_k=1)

        assert len(results) == 1  # graceful fallback still returns results
        mock_empty_cache.assert_called_once()

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_chunks_forward_passes_by_batch_size(
        self, mock_tokenizer_class, mock_model_class
    ):
        """5 candidates at batch_size=2 must run 3 forward passes (2, 2, 1), not 1.

        Regression for the unbounded single-batch forward that would build a
        [top_k_candidates, seq_len, vocab] logits tensor in one shot (~4.35 GiB at
        4B/512/151936) — see GenerativeReranker.rerank()'s batch-chunking loop.
        """
        seq_len = 10
        vocab_size = 1000
        yes_id, no_id = 100, 101
        call_batch_sizes = []

        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                # Force the fallback to encode()-based resolution in these tests —
                # the encode() variants below set up the yes/no distinction.
                return None

            def encode(self, text, **kwargs):
                return [yes_id] if text in ("yes", " yes") else [no_id]

            def __call__(self, prompts, **kwargs):
                n = len(prompts)
                mock_inputs = {
                    "input_ids": torch.ones(n, seq_len, dtype=torch.long),
                    "attention_mask": torch.ones(n, seq_len, dtype=torch.long),
                }

                class TensorDict(dict):
                    def to(self, device):
                        return self

                return TensorDict(mock_inputs)

        class MockModel:
            def to(self, device):
                return self

            def __call__(self, **inputs):
                n = inputs["input_ids"].shape[0]
                call_batch_sizes.append(n)
                logits_tensor = torch.zeros(n, seq_len, vocab_size)
                logits_tensor[:, -1, yes_id] = 2.0
                logits_tensor[:, -1, no_id] = 0.5

                class Outputs:
                    logits = logits_tensor

                return Outputs()

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MockModel()

        reranker = GenerativeReranker(device="cpu", batch_size=2)
        candidates = [
            SearchResult(
                chunk_id=f"c{i}", score=1.0, metadata={"content_preview": f"code {i}"}
            )
            for i in range(5)
        ]

        results = reranker.rerank("find function", candidates, top_k=5)

        assert call_batch_sizes == [2, 2, 1]
        assert len(results) == 5
        assert reranker.fallback_count == 0

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_ensure_loaded_sets_left_padding(
        self, mock_tokenizer_class, mock_model_class
    ):
        """Tokenizer must be switched to left padding so logits[:, -1, :] is valid.

        Qwen's own reference implementation left-pads so the last sequence position
        is the last real token for every row when logits_to_keep=1 is used.
        """
        mock_tokenizer_class.return_value = MagicMock()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cpu")
        _ = reranker.tokenizer  # triggers _ensure_loaded

        assert reranker._tokenizer.padding_side == "left"

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_ensure_loaded_sets_left_truncation(
        self, mock_tokenizer_class, mock_model_class
    ):
        """Truncation must eat the prompt head, never the assistant suffix.

        logits[:, -1, :] reads the last sequence position; right truncation would
        risk cutting off the "<|im_start|>assistant\\n<think>...</think>\\n\\n"
        suffix that position depends on once documents approach max_length.
        """
        mock_tokenizer_class.return_value = MagicMock()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cpu")
        _ = reranker.tokenizer  # triggers _ensure_loaded

        assert reranker._tokenizer.truncation_side == "left"

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_passes_logits_to_keep_one(
        self, mock_tokenizer_class, mock_model_class
    ):
        """Forward call must pass logits_to_keep=1 to bound the logits tensor size."""
        seq_len = 10
        vocab_size = 1000
        yes_id, no_id = 100, 101
        captured_kwargs = {}

        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                # Force the fallback to encode()-based resolution in these tests —
                # the encode() variants below set up the yes/no distinction.
                return None

            def encode(self, text, **kwargs):
                return [yes_id] if text in ("yes", " yes") else [no_id]

            def __call__(self, prompts, **kwargs):
                n = len(prompts)
                mock_inputs = {
                    "input_ids": torch.ones(n, seq_len, dtype=torch.long),
                    "attention_mask": torch.ones(n, seq_len, dtype=torch.long),
                }

                class TensorDict(dict):
                    def to(self, device):
                        return self

                return TensorDict(mock_inputs)

        class MockModel:
            def to(self, device):
                return self

            def __call__(self, **inputs):
                captured_kwargs.update(inputs)
                logits_tensor = torch.zeros(1, seq_len, vocab_size)
                logits_tensor[0, -1, yes_id] = 2.0
                logits_tensor[0, -1, no_id] = 0.5

                class Outputs:
                    logits = logits_tensor

                return Outputs()

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MockModel()

        reranker = GenerativeReranker(device="cpu")
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]
        reranker.rerank("find function", candidates, top_k=1)

        assert captured_kwargs.get("logits_to_keep") == 1

    @patch("torch.cuda.is_bf16_supported", return_value=True)
    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_ensure_loaded_selects_bfloat16_when_supported(
        self, mock_tokenizer_class, mock_model_class, mock_bf16_supported
    ):
        """CUDA + bf16-capable hardware must resolve to torch.bfloat16, not fp16.

        fp16 can overflow at 4B; Qwen3 is trained in bf16. Also asserts the weight
        dtype passed to from_pretrained agrees with the resolved autocast dtype.
        """
        mock_tokenizer_class.return_value = MagicMock()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cuda")
        _ = reranker.model  # triggers _ensure_loaded

        assert reranker._autocast_dtype == torch.bfloat16
        assert mock_model_class.call_args.kwargs["torch_dtype"] == torch.bfloat16

    @patch("torch.cuda.is_bf16_supported", return_value=False)
    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_ensure_loaded_falls_back_to_fp16_when_bf16_unsupported(
        self, mock_tokenizer_class, mock_model_class, mock_bf16_supported
    ):
        """CUDA without bf16 support must fall back to float16 (not silently bf16)."""
        mock_tokenizer_class.return_value = MagicMock()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cuda")
        _ = reranker.model

        assert reranker._autocast_dtype == torch.float16
        assert mock_model_class.call_args.kwargs["torch_dtype"] == torch.float16

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_fallback_count_increments_on_inference_error(
        self, mock_tokenizer_class, mock_model_class
    ):
        """fallback_count must track every fallback-to-original-order path.

        A benchmark run with fallback_count > 0 produced RRF-order results for at
        least one batch and must be discarded (plan Verification step 5).
        """

        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                return None

            def encode(self, text, **kwargs):
                return [100] if text in ("yes", " yes") else [101]

            def __call__(self, prompts, **kwargs):
                raise RuntimeError("Simulated tokenization failure")

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cpu")
        assert reranker.fallback_count == 0
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]

        reranker.rerank("query", candidates, top_k=1)
        assert reranker.fallback_count == 1

        reranker.rerank("query", candidates, top_k=1)
        assert reranker.fallback_count == 2

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_fallback_count_increments_on_token_resolution_failure(
        self, mock_tokenizer_class, mock_model_class
    ):
        """fallback_count must also increment on the token-resolution fallback path."""

        class MockTokenizer:
            def convert_tokens_to_ids(self, text):
                return None

            def encode(self, text, **kwargs):
                return [10, 20]  # always multi-token

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cpu")
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]

        reranker.rerank("query", candidates, top_k=1)
        assert reranker.fallback_count == 1


class TestBuildRerankDocument:
    """Tests for _build_rerank_document helper (shared by both reranker classes)."""

    def test_prefers_bm25_text_over_content_preview(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="a",
            score=1.0,
            metadata={"bm25_text": "full source", "content_preview": "code a"},
        )
        result = _build_rerank_document(candidate, max_chars=1000)
        assert result == "ID: a\nfull source"

    def test_falls_back_to_content_preview_when_no_bm25_text(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
        )
        result = _build_rerank_document(candidate, max_chars=1000)
        assert result == "ID: a\ncode a"

    def test_falls_back_to_chunk_id_when_metadata_empty(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(chunk_id="chunk_a", score=1.0, metadata={})
        result = _build_rerank_document(candidate, max_chars=1000)
        assert result == "ID: chunk_a\nchunk_a"

    def test_id_prefix_present(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="pkg/mod.py::func", score=1.0, metadata={"bm25_text": "x"}
        )
        result = _build_rerank_document(candidate, max_chars=1000)
        assert result.startswith("ID: pkg/mod.py::func\n")

    def test_body_truncated_to_max_chars_header_intact(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="a", score=1.0, metadata={"bm25_text": "x" * 5000}
        )
        result = _build_rerank_document(candidate, max_chars=100)
        header, _, body = result.partition("\n")
        assert header == "ID: a"
        assert len(body) == 100
        assert body == "x" * 100

    def test_body_under_max_chars_not_padded(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="a", score=1.0, metadata={"bm25_text": "short"}
        )
        result = _build_rerank_document(candidate, max_chars=1000)
        assert result == "ID: a\nshort"


class TestBuildRerankDocumentSignatureHead:
    """A4 pilot: mode="signature_head" composition + mode="full" byte-identity."""

    @staticmethod
    def _legacy_build(candidate, max_chars):
        """The pre-A4 builder algorithm, verbatim — byte-identity reference."""
        body = candidate.metadata.get("bm25_text") or candidate.metadata.get(
            "content_preview", ""
        )
        if not body:
            body = candidate.chunk_id
        if len(body) > max_chars:
            body = body[:max_chars]
        return f"ID: {candidate.chunk_id}\n{body}"

    def test_full_mode_byte_identical_to_legacy_builder(self):
        """mode="full" (explicit and default) must be character-identical to
        the pre-A4 algorithm across the fallback chain and truncation."""
        from search.neural_reranker import _build_rerank_document

        cases = [
            SearchResult(
                chunk_id="a.py:1-10:function:f",
                score=1.0,
                metadata={"bm25_text": "def f():\n    pass", "content_preview": "p"},
            ),
            SearchResult(
                chunk_id="b", score=1.0, metadata={"content_preview": "preview only"}
            ),
            SearchResult(chunk_id="empty_meta", score=1.0, metadata={}),
            SearchResult(
                chunk_id="long", score=1.0, metadata={"bm25_text": "y" * 5000}
            ),
        ]
        for candidate in cases:
            expected = self._legacy_build(candidate, 100)
            assert _build_rerank_document(candidate, max_chars=100) == expected
            assert (
                _build_rerank_document(candidate, max_chars=100, mode="full")
                == expected
            )

    def test_signature_head_composes_all_sections(self):
        from search.neural_reranker import _build_rerank_document

        source = "\n".join(f"line{i}" for i in range(20))
        candidate = SearchResult(
            chunk_id="pkg/mod.py:1-40:function:f",
            score=1.0,
            metadata={
                "bm25_text": source,
                "relative_path": "pkg/mod.py",
                "parent_name": "MyClass",
                "docstring": "Does the thing.",
            },
        )
        result = _build_rerank_document(
            candidate, max_chars=4000, mode="signature_head"
        )
        header, _, body = result.partition("\n")
        assert header == "ID: pkg/mod.py:1-40:function:f"
        expected_head = "\n".join(f"line{i}" for i in range(12))
        assert (
            body
            == f"path: pkg/mod.py | parent: MyClass\nDoes the thing.\n{expected_head}"
        )

    def test_signature_head_caps_head_lines_at_12(self):
        from search.neural_reranker import _build_rerank_document

        source = "\n".join(f"line{i}" for i in range(30))
        candidate = SearchResult(
            chunk_id="a", score=1.0, metadata={"bm25_text": source}
        )
        result = _build_rerank_document(
            candidate, max_chars=4000, mode="signature_head"
        )
        _, _, body = result.partition("\n")
        assert "line11" in body
        assert "line12" not in body

    def test_signature_head_caps_docstring_at_300(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="a",
            score=1.0,
            metadata={"docstring": "d" * 500, "bm25_text": "code"},
        )
        result = _build_rerank_document(
            candidate, max_chars=4000, mode="signature_head"
        )
        _, _, body = result.partition("\n")
        assert body == "d" * 300 + "\ncode"

    def test_signature_head_missing_parent_omits_parent_segment(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="a",
            score=1.0,
            metadata={"relative_path": "x.py", "bm25_text": "code"},
        )
        result = _build_rerank_document(
            candidate, max_chars=4000, mode="signature_head"
        )
        _, _, body = result.partition("\n")
        assert body == "path: x.py\ncode"

    def test_signature_head_missing_path_and_parent_omits_context_line(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="a", score=1.0, metadata={"bm25_text": "code"}
        )
        result = _build_rerank_document(
            candidate, max_chars=4000, mode="signature_head"
        )
        assert result == "ID: a\ncode"

    def test_signature_head_falls_back_to_content_preview(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="a", score=1.0, metadata={"content_preview": "preview"}
        )
        result = _build_rerank_document(
            candidate, max_chars=4000, mode="signature_head"
        )
        assert result == "ID: a\npreview"

    def test_signature_head_empty_metadata_falls_back_to_chunk_id(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(chunk_id="chunk_x", score=1.0, metadata={})
        result = _build_rerank_document(
            candidate, max_chars=4000, mode="signature_head"
        )
        assert result == "ID: chunk_x\nchunk_x"

    def test_signature_head_composed_body_truncated_to_max_chars(self):
        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(
            chunk_id="a",
            score=1.0,
            metadata={
                "relative_path": "pkg/mod.py",
                "docstring": "d" * 300,
                "bm25_text": "c" * 500,
            },
        )
        result = _build_rerank_document(candidate, max_chars=50, mode="signature_head")
        header, _, body = result.partition("\n")
        assert header == "ID: a"
        assert len(body) == 50
        assert body.startswith("path: pkg/mod.py")

    def test_unknown_mode_raises_value_error(self):
        import pytest

        from search.neural_reranker import _build_rerank_document

        candidate = SearchResult(chunk_id="a", score=1.0, metadata={})
        with pytest.raises(ValueError, match="doc_representation_mode"):
            _build_rerank_document(candidate, max_chars=100, mode="signature")


class TestTokenIdValidation:
    """Tests for _resolve_single_token_id helper."""

    def test_prefers_convert_tokens_to_ids(self):
        """Official Qwen3-Reranker recipe: a direct vocab hit wins over encode()."""
        from search.neural_reranker import _resolve_single_token_id

        mock_tokenizer = MagicMock()
        mock_tokenizer.unk_token_id = 0
        mock_tokenizer.convert_tokens_to_ids.return_value = 99

        result = _resolve_single_token_id(mock_tokenizer, "yes")
        assert result == 99
        mock_tokenizer.encode.assert_not_called()

    def test_falls_back_to_encode_when_convert_returns_none(self):
        """A tokenizer with no direct vocab entry falls back to encode() variants."""
        from search.neural_reranker import _resolve_single_token_id

        mock_tokenizer = MagicMock()
        mock_tokenizer.convert_tokens_to_ids.return_value = None
        mock_tokenizer.encode.return_value = [42]

        result = _resolve_single_token_id(mock_tokenizer, "Yes")
        assert result == 42

    def test_falls_back_to_encode_when_convert_returns_unk(self):
        """convert_tokens_to_ids resolving to the UNK token must not be trusted."""
        from search.neural_reranker import _resolve_single_token_id

        mock_tokenizer = MagicMock()
        mock_tokenizer.unk_token_id = 0
        mock_tokenizer.convert_tokens_to_ids.return_value = 0
        mock_tokenizer.encode.return_value = [42]

        result = _resolve_single_token_id(mock_tokenizer, "yes")
        assert result == 42

    def test_tries_space_variant(self):
        """Should try ' Yes' if 'Yes' produces multiple tokens."""
        from search.neural_reranker import _resolve_single_token_id

        mock_tokenizer = MagicMock()
        mock_tokenizer.convert_tokens_to_ids.return_value = None
        # "Yes" -> 2 tokens, " Yes" -> 1 token
        mock_tokenizer.encode.side_effect = lambda text, **kw: (
            [10, 20] if text == "Yes" else [42]
        )

        result = _resolve_single_token_id(mock_tokenizer, "Yes")
        assert result == 42
        assert mock_tokenizer.encode.call_count == 2

    def test_raises_on_multi_token(self):
        """Should raise RuntimeError if neither variant is single-token."""
        import pytest

        from search.neural_reranker import _resolve_single_token_id

        mock_tokenizer = MagicMock()
        mock_tokenizer.convert_tokens_to_ids.return_value = None
        mock_tokenizer.encode.return_value = [10, 20]  # Always multi-token

        with pytest.raises(RuntimeError, match="Cannot resolve"):
            _resolve_single_token_id(mock_tokenizer, "Yes")


class TestCreateRerankerFactory:
    """Tests for create_reranker factory function."""

    def test_creates_generative_reranker_for_qwen3(self):
        """Should create GenerativeReranker for Qwen3 models."""
        reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B")
        assert isinstance(reranker, GenerativeReranker)
        assert reranker.model_name == "Qwen/Qwen3-Reranker-0.6B"

    def test_creates_discriminative_reranker_for_bge(self):
        """Should create NeuralReranker for BGE models."""
        reranker = create_reranker("BAAI/bge-reranker-v2-m3")
        assert isinstance(reranker, NeuralReranker)
        assert reranker.model_name == "BAAI/bge-reranker-v2-m3"

    def test_creates_discriminative_reranker_for_gte(self):
        """Should create NeuralReranker for GTE models."""
        reranker = create_reranker("Alibaba-NLP/gte-reranker-modernbert-base")
        assert isinstance(reranker, NeuralReranker)

    def test_discriminative_reranker_preserves_batch_size(self):
        """Discriminative rerankers should preserve batch size."""
        reranker = create_reranker("BAAI/bge-reranker-v2-m3", batch_size=16)
        assert reranker.batch_size == 16

    def test_device_passed_to_reranker(self):
        """Device parameter should be passed through."""
        reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B", device="cpu")
        assert reranker.device == "cpu"

    def test_all_generative_models_in_registry(self):
        """All models in GENERATIVE_RERANKERS should create GenerativeReranker."""
        for model_name in GENERATIVE_RERANKERS:
            reranker = create_reranker(model_name)
            assert isinstance(reranker, GenerativeReranker)
            assert reranker.model_name == model_name

    def test_generative_reranker_preserves_batch_size(self):
        """Regression: batch_size was previously silently dropped for GenerativeReranker.

        create_reranker's generative branch used to call
        GenerativeReranker(model_name, device) with no batch_size — this asserts the
        threaded-through value actually lands on the instance.
        """
        reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B", batch_size=4)
        assert isinstance(reranker, GenerativeReranker)
        assert reranker.batch_size == 4

    def test_instruction_passthrough_to_generative_reranker(self):
        """instruction must be threaded through create_reranker to GenerativeReranker."""
        reranker = create_reranker(
            "Qwen/Qwen3-Reranker-0.6B", instruction="custom instruction"
        )
        assert isinstance(reranker, GenerativeReranker)
        assert reranker.instruction == "custom instruction"

    def test_instruction_none_uses_default(self):
        """Omitting instruction must fall back to the model's built-in default."""
        from search.neural_reranker import _QWEN_RERANK_DEFAULT_INSTRUCTION

        reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B")
        assert isinstance(reranker, GenerativeReranker)
        assert reranker.instruction == _QWEN_RERANK_DEFAULT_INSTRUCTION

    def test_doc_max_chars_passthrough_to_generative_reranker(self):
        """doc_max_chars must land on GenerativeReranker (pointwise budget)."""
        reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B", doc_max_chars=2500)
        assert isinstance(reranker, GenerativeReranker)
        assert reranker.doc_max_chars == 2500

    def test_doc_max_chars_defaults_to_4000_for_generative_reranker(self):
        reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B")
        assert isinstance(reranker, GenerativeReranker)
        assert reranker.doc_max_chars == 4000

    def test_listwise_doc_max_chars_passthrough_to_jina(self):
        """listwise_doc_max_chars must land on JinaRerankerV3.doc_max_chars, not
        the generative doc_max_chars param — the two caps must not be swapped."""
        from search.neural_reranker import JinaRerankerV3

        reranker = create_reranker(
            "jinaai/jina-reranker-v3", listwise_doc_max_chars=500
        )
        assert isinstance(reranker, JinaRerankerV3)
        assert reranker.doc_max_chars == 500

    def test_listwise_doc_max_chars_defaults_to_1000_for_jina(self):
        from search.neural_reranker import JinaRerankerV3

        reranker = create_reranker("jinaai/jina-reranker-v3")
        assert isinstance(reranker, JinaRerankerV3)
        assert reranker.doc_max_chars == 1000

    def test_generative_doc_max_chars_does_not_affect_jina(self):
        """A caller passing only doc_max_chars must not leak it into jina's budget.

        Asserts JinaRerankerV3's listwise default (1000), not the generative
        pointwise default (4000, tested above) — despite both being named
        ``doc_max_chars`` on their respective constructors, they are
        independent caps (see docs/adr/0011-listwise-reranker-doc-cap.md).
        """
        from search.neural_reranker import JinaRerankerV3

        reranker = create_reranker("jinaai/jina-reranker-v3", doc_max_chars=9999)
        assert isinstance(reranker, JinaRerankerV3)
        assert reranker.doc_max_chars == 1000

    def test_listwise_dtype_passthrough_to_jina(self):
        """listwise_dtype must land on JinaRerankerV3.dtype (fp32 determinism arm)."""
        from search.neural_reranker import JinaRerankerV3

        reranker = create_reranker("jinaai/jina-reranker-v3", listwise_dtype="fp32")
        assert isinstance(reranker, JinaRerankerV3)
        assert reranker.dtype == "fp32"

    def test_listwise_dtype_defaults_to_auto_for_jina(self):
        from search.neural_reranker import JinaRerankerV3

        reranker = create_reranker("jinaai/jina-reranker-v3")
        assert isinstance(reranker, JinaRerankerV3)
        assert reranker.dtype == "auto"

    def test_listwise_dtype_ignored_for_non_jina_rerankers(self):
        """Non-listwise rerankers have no dtype knob — the factory must not
        forward listwise_dtype to them (bf16 non-determinism is a listwise,
        context-dependent-scoring problem; pointwise rerankers are unaffected)."""
        reranker = create_reranker("BAAI/bge-reranker-v2-m3", listwise_dtype="fp32")
        assert not hasattr(reranker, "dtype")

    def test_doc_representation_mode_passthrough_to_generative_reranker(self):
        """doc_representation_mode must land on GenerativeReranker (A4 pilot)."""
        reranker = create_reranker(
            "Qwen/Qwen3-Reranker-0.6B", doc_representation_mode="signature_head"
        )
        assert isinstance(reranker, GenerativeReranker)
        assert reranker.doc_representation_mode == "signature_head"

    def test_doc_representation_mode_passthrough_to_jina(self):
        """doc_representation_mode must land on JinaRerankerV3 (A4 pilot)."""
        from search.neural_reranker import JinaRerankerV3

        reranker = create_reranker(
            "jinaai/jina-reranker-v3", doc_representation_mode="signature_head"
        )
        assert isinstance(reranker, JinaRerankerV3)
        assert reranker.doc_representation_mode == "signature_head"

    def test_doc_representation_mode_defaults_to_full(self):
        for model in ("Qwen/Qwen3-Reranker-0.6B", "jinaai/jina-reranker-v3"):
            reranker = create_reranker(model)
            assert reranker.doc_representation_mode == "full"

    def test_doc_representation_mode_ignored_for_cross_encoder(self):
        """NeuralReranker builds pairs from content_preview directly and never
        calls the document builder — the factory must not forward the mode."""
        reranker = create_reranker(
            "BAAI/bge-reranker-v2-m3", doc_representation_mode="signature_head"
        )
        assert not hasattr(reranker, "doc_representation_mode")


class TestGenerativeRerankerIntegration:
    """Integration-style tests for GenerativeReranker (no mocks)."""

    @pytest.mark.skipif(
        not torch.cuda.is_available(), reason="Requires GPU for realistic test"
    )
    def test_model_loading_flow(self):
        """Test the lazy loading flow (CPU fallback if no GPU)."""
        reranker = GenerativeReranker(device="cpu")  # Force CPU for test
        assert not reranker.is_loaded()

        # This would load the model in real scenario
        # We skip actual loading in unit tests
        assert reranker._model is None

    def test_prompt_format(self):
        """Verify the prompt format is correct."""
        reranker = GenerativeReranker()

        # We can't test actual model behavior without loading it,
        # but we can verify the structure is set up correctly
        assert hasattr(reranker, "model_name")
        assert hasattr(reranker, "_logger")
