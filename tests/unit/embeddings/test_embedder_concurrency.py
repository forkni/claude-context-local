"""Concurrency tests for CodeEmbedder lifecycle race conditions.

Tests that cleanup() and embed_query() cannot produce AttributeError when
racing across threads, and that state.clear_embedders() properly invalidates
downstream references (searcher).
"""

import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from embeddings.embedder import CodeEmbedder  # noqa: E402


def _make_embedder_with_mock_loader() -> tuple[CodeEmbedder, MagicMock]:
    """Create a CodeEmbedder whose ModelLoader is fully mocked (no GPU needed)."""
    fake_model = MagicMock()
    fake_model.encode.return_value = np.zeros((1, 4), dtype=np.float32)
    fake_model.get_sentence_embedding_dimension.return_value = 4

    fake_loader = MagicMock()
    fake_loader.load.return_value = (fake_model, "cpu")
    fake_loader.model_vram_usage = {}

    with (
        patch(
            "embeddings.model_loader.ModelLoader._should_use_onnx", return_value=False
        ),
        patch("embeddings.embedder.ModelLoader") as mock_loader,
        patch("embeddings.embedder.ModelCacheManager"),
        patch("embeddings.embedder.set_vram_limit"),
        patch("embeddings.embedder._get_config_via_service_locator", return_value=None),
    ):
        mock_loader.return_value = fake_loader
        emb = CodeEmbedder(model_name="BAAI/bge-m3")

    emb._model_loader = fake_loader
    return emb, fake_model


class TestEmbedderConcurrencyRace:
    """Verify the cleanup/encode race cannot produce AttributeError."""

    def test_no_attribute_error_on_concurrent_cleanup_and_embed(self):
        """Thread A loops embed_query while thread B calls cleanup().

        Pre-fix: AttributeError: 'NoneType' object has no attribute 'load'.
        Post-fix: either success or RuntimeError("cleaned up"), never AttributeError.
        """
        emb, fake_model = _make_embedder_with_mock_loader()

        # Slow down encode slightly so the race window is large enough to hit
        def slow_encode(texts, **kwargs):
            time.sleep(0.001)
            return np.zeros((len(texts), 4), dtype=np.float32)

        fake_model.encode.side_effect = slow_encode

        # Prime: load model so it's in the hot path
        _ = emb.model

        attribute_errors: list[Exception] = []
        stop_event = threading.Event()

        def embed_worker():
            for _ in range(100):
                if stop_event.is_set():
                    break
                try:
                    emb.embed_query("test query")
                except AttributeError as e:
                    attribute_errors.append(e)
                    stop_event.set()
                except RuntimeError:
                    pass  # cleaned-up error is expected after cleanup runs

        def cleanup_worker():
            time.sleep(0.01)  # let embed start first
            emb.cleanup()

        t_embed = threading.Thread(target=embed_worker)
        t_cleanup = threading.Thread(target=cleanup_worker)
        t_embed.start()
        t_cleanup.start()
        t_embed.join(timeout=5)
        t_cleanup.join(timeout=5)

        assert not attribute_errors, (
            f"AttributeError leaked through lifecycle lock: {attribute_errors}"
        )

    def test_cleanup_then_access_raises_runtime_error(self):
        """After cleanup(), accessing .model raises RuntimeError with clear message."""
        emb, _ = _make_embedder_with_mock_loader()
        _ = emb.model  # load
        emb.cleanup()

        with pytest.raises(RuntimeError, match="cleaned up"):
            _ = emb.model

    def test_cleanup_then_embed_raises_runtime_error(self):
        """After cleanup(), embed_query raises RuntimeError (not AttributeError)."""
        emb, _ = _make_embedder_with_mock_loader()
        _ = emb.model  # load
        emb.cleanup()

        with pytest.raises(RuntimeError, match="cleaned up"):
            emb.embed_query("some query")

    def test_double_cleanup_is_idempotent(self):
        """Calling cleanup() twice must not raise."""
        emb, _ = _make_embedder_with_mock_loader()
        _ = emb.model
        emb.cleanup()
        emb.cleanup()  # must not raise

    def test_lifecycle_lock_is_rlock(self):
        """_lifecycle_lock must be an RLock (reentrant) so cleanup() from __exit__
        does not deadlock when cleanup() itself acquires the lock."""
        emb, _ = _make_embedder_with_mock_loader()
        assert isinstance(emb._lifecycle_lock, type(threading.RLock()))


class TestStateClearEmbeddersInvalidatesSearcher:
    """Verify state.clear_embedders() sets state.searcher = None (change D)."""

    def test_clear_embedders_nulls_searcher(self):
        """clear_embedders() must reset searcher so no stale embedder ref is used."""
        from mcp_server.state import ApplicationState

        state = ApplicationState()
        fake_embedder = MagicMock()
        fake_embedder.cleanup = MagicMock()
        state.set_embedder("bge_m3", fake_embedder)
        state.searcher = MagicMock()  # simulate a loaded searcher

        state.clear_embedders()

        assert state.searcher is None, (
            "clear_embedders() must null state.searcher to prevent stale embedder refs"
        )
        assert state.embedders == {}

    def test_clear_embedders_calls_cleanup_on_each(self):
        """cleanup() must be called for every embedder in the pool."""
        from mcp_server.state import ApplicationState

        state = ApplicationState()
        e1, e2 = MagicMock(), MagicMock()
        e1.cleanup = MagicMock()
        e2.cleanup = MagicMock()
        state.set_embedder("model_a", e1)
        state.set_embedder("model_b", e2)

        state.clear_embedders()

        e1.cleanup.assert_called_once()
        e2.cleanup.assert_called_once()
