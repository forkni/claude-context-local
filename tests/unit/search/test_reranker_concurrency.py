"""Concurrency tests for reranker inference locks.

Part 1 of docs/adr/0008-reindex-search-rwlock.md: each reranker's inference
region (the HF fast-tokenizer / CrossEncoder / listwise-model borrow) must be
serialized by a per-instance ``_infer_lock`` so concurrent ``rerank()`` calls
from sibling searches cannot race each other. Before the fix, two concurrent
calls into the shared Jina fast-tokenizer raised "Already borrowed" (Error B
in _archive/ERROR_LOG.md). These tests reproduce the concurrent-call shape
against a mocked model/tokenizer and assert the guarded region never sees
more than one thread inside it at a time.
"""

import threading
import time
from unittest.mock import MagicMock

import torch

from search.neural_reranker import GenerativeReranker, JinaRerankerV3, NeuralReranker
from search.reranker import SearchResult


N_THREADS = 6


def _make_candidates(n: int = 3) -> list:
    return [
        SearchResult(
            chunk_id=f"chunk_{i}",
            score=1.0,
            metadata={"content_preview": f"code {i}"},
        )
        for i in range(n)
    ]


class _ConcurrencyProbe:
    """Tracks whether more than one thread is ever inside the guarded region."""

    def __init__(self):
        self._lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.calls = 0

    def enter(self):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.calls += 1

    def exit(self):
        with self._lock:
            self.active -= 1


def _run_concurrent_reranks(reranker, n_threads: int = N_THREADS):
    """Fire ``n_threads`` concurrent ``.rerank()`` calls at the same instance.

    Uses a barrier so all threads reach the call site together, widening the
    race window as much as possible from pure-Python threads.
    """
    barrier = threading.Barrier(n_threads)
    errors: list[Exception] = []

    def worker():
        barrier.wait()
        try:
            reranker.rerank("query", _make_candidates(), top_k=3)
        except Exception as e:  # noqa: BLE001 - capture for the assertion below
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert all(not t.is_alive() for t in threads), "a worker thread hung"
    return errors


class TestNeuralRerankerConcurrency:
    """CrossEncoder.predict() borrow — NeuralReranker._infer_lock."""

    def test_concurrent_rerank_serializes_predict(self):
        probe = _ConcurrencyProbe()

        def fake_predict(pairs, batch_size=16, show_progress_bar=False):
            probe.enter()
            try:
                time.sleep(0.02)  # widen the race window
                return [0.5] * len(pairs)
            finally:
                probe.exit()

        mock_model = MagicMock()
        mock_model.predict.side_effect = fake_predict

        reranker = NeuralReranker()
        reranker._model = mock_model  # bypass lazy load; only _infer_lock under test

        errors = _run_concurrent_reranks(reranker)

        assert errors == [], f"rerank() raised under concurrency: {errors}"
        assert probe.calls == N_THREADS
        assert probe.max_active == 1, (
            "predict() was entered concurrently — _infer_lock did not serialize"
        )


class TestJinaRerankerV3Concurrency:
    """Jina listwise model.rerank() borrow — JinaRerankerV3._infer_lock.

    This is the exact code path behind the logged "Already borrowed" panic:
    jina-reranker-v3 is the active reranker (search_config.json default).
    """

    def test_concurrent_rerank_serializes_model_rerank(self):
        probe = _ConcurrencyProbe()

        def fake_rerank(query, documents, top_n=10):
            probe.enter()
            try:
                time.sleep(0.02)
                return [
                    {"index": i, "relevance_score": 0.9 - i * 0.1, "document": doc}
                    for i, doc in enumerate(documents)
                ]
            finally:
                probe.exit()

        mock_model = MagicMock()
        mock_model.rerank.side_effect = fake_rerank

        reranker = JinaRerankerV3()
        reranker._model = mock_model  # bypass lazy load; only _infer_lock under test

        errors = _run_concurrent_reranks(reranker)

        assert errors == [], f"rerank() raised under concurrency: {errors}"
        assert probe.calls == N_THREADS
        assert probe.max_active == 1, (
            "model.rerank() was entered concurrently — _infer_lock did not serialize"
        )


class TestGenerativeRerankerConcurrency:
    """HF fast-tokenizer borrow — GenerativeReranker._infer_lock.

    Probes the tokenizer __call__ specifically: per the code comment at
    neural_reranker.py (GenerativeReranker.rerank), "the fast-tokenizer
    borrow happens in the tokenizer(...) call itself, not just the model
    forward pass" — this is the exact operation that panics with
    "Already borrowed" under concurrent unsynchronized access.
    """

    def test_concurrent_rerank_serializes_tokenizer_call(self):
        probe = _ConcurrencyProbe()
        seq_len = 8
        vocab_size = 200
        yes_id, no_id = 50, 51

        class MockTokenizer:
            def encode(self, text, **kwargs):
                return [yes_id] if text in ("yes", " yes") else [no_id]

            def __call__(self, prompts, **kwargs):
                probe.enter()
                try:
                    time.sleep(0.02)  # widen the race window
                    n = len(prompts) if isinstance(prompts, list) else 1

                    class TensorDict(dict):
                        def to(self, device):
                            return self

                    return TensorDict(
                        {
                            "input_ids": torch.ones(n, seq_len, dtype=torch.long),
                            "attention_mask": torch.ones(n, seq_len, dtype=torch.long),
                        }
                    )
                finally:
                    probe.exit()

        class MockModel:
            def to(self, device):
                return self

            def __call__(self, **inputs):
                batch = inputs["attention_mask"].shape[0]
                logits = torch.zeros(batch, seq_len, vocab_size)
                logits[:, -1, yes_id] = 1.0
                logits[:, -1, no_id] = 1.0

                class Outputs:
                    pass

                out = Outputs()
                out.logits = logits
                return out

        reranker = GenerativeReranker(device="cpu")
        # Bypass _ensure_loaded()'s (unguarded) lazy load; only _infer_lock is under test.
        reranker._model = MockModel()
        reranker._tokenizer = MockTokenizer()

        errors = _run_concurrent_reranks(reranker)

        assert errors == [], f"rerank() raised under concurrency: {errors}"
        assert probe.calls == N_THREADS
        assert probe.max_active == 1, (
            "tokenizer(...) was entered concurrently — _infer_lock did not serialize"
        )
