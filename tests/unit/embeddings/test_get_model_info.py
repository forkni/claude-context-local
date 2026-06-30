"""Regression tests for CodeEmbedder.get_model_info — embedding dimension lookup.

Verifies that get_model_info:
  - Prefers the new `get_embedding_dimension` method (sentence-transformers >=5)
    so the FutureWarning is never emitted.
  - Falls back to `get_sentence_embedding_dimension` when only the old name is
    present (ONNXEmbeddingModel, older ST versions).

Uses plain classes rather than MagicMock so that `hasattr` behaves correctly
(MagicMock auto-creates attributes for any name, masking the branch under test).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from embeddings.embedder import CodeEmbedder  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal fake model classes — no MagicMock to keep hasattr semantics honest
# ---------------------------------------------------------------------------


class _NewApiModel:
    """Simulates SentenceTransformer >=5 with only the new method name."""

    device = "cpu"
    max_seq_length = 512

    def get_embedding_dimension(self) -> int:
        return 768

    def get_sentence_embedding_dimension(self) -> int:
        raise AssertionError(
            "get_sentence_embedding_dimension must not be called when "
            "get_embedding_dimension is available — would emit FutureWarning"
        )


class _OldApiModel:
    """Simulates ONNXEmbeddingModel / older ST with only the old method name."""

    device = "cpu"
    max_seq_length = 256

    def get_sentence_embedding_dimension(self) -> int:
        return 1024


class _BothApiModel:
    """Exposes both names — new one should win."""

    device = "cuda:0"
    max_seq_length = 8192

    def get_embedding_dimension(self) -> int:
        return 384

    def get_sentence_embedding_dimension(self) -> int:
        raise AssertionError(
            "get_sentence_embedding_dimension must not be called when "
            "get_embedding_dimension is available"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bare_embedder(model_name: str = "test-model") -> CodeEmbedder:
    """Return a CodeEmbedder with all heavy machinery patched out."""
    fake_loader = MagicMock()
    fake_loader.load.return_value = (MagicMock(), "cpu")
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
        emb = CodeEmbedder(model_name=model_name)

    emb._model_loader = fake_loader
    return emb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetModelInfoDimension:
    """get_model_info picks the right dimension-retrieval method."""

    def test_prefers_new_api_when_present(self):
        """New `get_embedding_dimension` is called; old one is never touched."""
        emb = _make_bare_embedder()
        emb._model = _NewApiModel()  # type: ignore[assignment]

        info = emb.get_model_info()

        assert info["embedding_dimension"] == 768
        assert info["status"] == "loaded"
        assert info["model_name"] == "test-model"

    def test_falls_back_to_old_api_for_onnx(self):
        """ONNX wrapper (old name only) still works without raising AttributeError."""
        emb = _make_bare_embedder()
        emb._model = _OldApiModel()  # type: ignore[assignment]

        info = emb.get_model_info()

        assert info["embedding_dimension"] == 1024
        assert info["status"] == "loaded"

    def test_new_api_wins_when_both_present(self):
        """With both methods defined, the new one wins (no FutureWarning path)."""
        emb = _make_bare_embedder()
        emb._model = _BothApiModel()  # type: ignore[assignment]

        info = emb.get_model_info()

        assert info["embedding_dimension"] == 384

    def test_not_loaded_returns_sentinel(self):
        """Unloaded model returns the canonical sentinel dict."""
        emb = _make_bare_embedder()
        emb._model = None

        info = emb.get_model_info()

        assert info == {"status": "not_loaded"}
