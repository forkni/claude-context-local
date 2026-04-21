"""Unit tests for get_model_key_from_name cross-pool lookup and get_embedder opt-in.

Covers the fix for: index built with a model from pool A is silently discarded
when the active pool switches to pool B (dimension mismatch → forced reindex).
"""

from unittest.mock import MagicMock, patch

from search.config import (
    ALL_POOL_MODELS,
    MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pool_manager_with_active_pool(pool: dict[str, str]):
    """Return a ModelPoolManager whose get_pool_config() returns *pool*."""
    from mcp_server.model_pool_manager import ModelPoolManager

    mgr = ModelPoolManager()
    mgr._cached_pool_config = pool
    return mgr


# ---------------------------------------------------------------------------
# Tests: get_model_key_from_name
# ---------------------------------------------------------------------------


class TestGetModelKeyFromName:
    """Reverse-lookup from full model name to pool key."""

    def test_active_pool_fast_path(self):
        """Model in the active pool resolves without cross-pool log."""
        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with patch.object(mpm, "_model_pool_manager", mgr):
            key = mpm.get_model_key_from_name("BAAI/bge-m3")
        assert key == "bge_m3"

    def test_cross_pool_resolves_bge_code(self, caplog):
        """bge-code-v1 is mapped to 'bge_code' even when active pool is lightweight-speed."""
        import logging

        from mcp_server import model_pool_manager as mpm

        # Active pool = lightweight-speed (does not contain bge_code)
        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            caplog.at_level(logging.INFO, logger="mcp_server.model_pool_manager"),
        ):
            key = mpm.get_model_key_from_name("BAAI/bge-code-v1")

        assert key == "bge_code", (
            "bge-code-v1 should resolve via cross-pool fallback even when active "
            "pool is lightweight-speed"
        )
        assert any("[CROSS_POOL]" in rec.message for rec in caplog.records), (
            "Cross-pool resolution should emit an INFO log containing '[CROSS_POOL]'"
        )

    def test_cross_pool_resolves_qwen3(self):
        """qwen3 model maps correctly when active pool is lightweight-speed."""
        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with patch.object(mpm, "_model_pool_manager", mgr):
            key = mpm.get_model_key_from_name("Qwen/Qwen3-Embedding-0.6B")
        assert key == "qwen3"

    def test_unknown_model_returns_none(self):
        """A model not registered in any pool returns None (no crash)."""
        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with patch.object(mpm, "_model_pool_manager", mgr):
            key = mpm.get_model_key_from_name("some/nonexistent-model-v99")
        assert key is None

    def test_all_pool_models_contains_both_pools(self):
        """ALL_POOL_MODELS is the union of both pool dicts (sanity check)."""
        assert "bge_code" in ALL_POOL_MODELS
        assert "qwen3" in ALL_POOL_MODELS
        assert "gte_modernbert" in ALL_POOL_MODELS
        assert "bge_m3" in ALL_POOL_MODELS


# ---------------------------------------------------------------------------
# Tests: get_embedder cross-pool opt-in
# ---------------------------------------------------------------------------


class TestGetEmbedderCrossPool:
    """get_embedder(allow_cross_pool=True) loads models outside the active pool."""

    def _make_fake_embedder(self, model_name: str):
        emb = MagicMock()
        emb.model_name = model_name
        return emb

    def test_cross_pool_opt_in_loads_bge_code(self, caplog):
        """With allow_cross_pool=True, bge_code loads even when pool=lightweight-speed."""
        import logging

        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        fake_embedder = self._make_fake_embedder("BAAI/bge-code-v1")

        state_mock = MagicMock()
        state_mock.embedders = {}

        def set_embedder(key, emb):
            state_mock.embedders[key] = emb

        state_mock.set_embedder.side_effect = set_embedder

        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            patch("mcp_server.model_pool_manager.get_state", return_value=state_mock),
            patch(
                "mcp_server.model_pool_manager.CodeEmbedder",
                return_value=fake_embedder,
            ) as mock_embedder_cls,
            patch("mcp_server.model_pool_manager.get_storage_dir") as mock_storage,
            caplog.at_level(logging.WARNING, logger="mcp_server.model_pool_manager"),
        ):
            mock_storage.return_value = MagicMock()
            mock_storage.return_value.__truediv__ = lambda self, other: MagicMock()
            result = mpm.get_embedder("bge_code", allow_cross_pool=True)

        mock_embedder_cls.assert_called_once()
        call_kwargs = mock_embedder_cls.call_args
        assert call_kwargs.kwargs.get("model_name") == "BAAI/bge-code-v1" or (
            call_kwargs.args and call_kwargs.args[0] == "BAAI/bge-code-v1"
        ), "CodeEmbedder should be constructed with bge-code-v1 model name"
        assert result is fake_embedder
        assert any("[CROSS_POOL]" in rec.message for rec in caplog.records)

    def test_cross_pool_disabled_by_default_falls_back(self):
        """Without allow_cross_pool, requesting bge_code in lightweight pool falls back."""
        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        fake_gte = self._make_fake_embedder("Alibaba-NLP/gte-modernbert-base")
        fake_bge_m3 = self._make_fake_embedder("BAAI/bge-m3")

        state_mock = MagicMock()
        state_mock.multi_model_enabled = True
        # Simulate gte_modernbert already loaded
        state_mock.embedders = {"gte_modernbert": fake_gte, "bge_m3": fake_bge_m3}

        def set_embedder(key, emb):
            state_mock.embedders[key] = emb

        state_mock.set_embedder.side_effect = set_embedder

        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            patch("mcp_server.model_pool_manager.get_state", return_value=state_mock),
            patch("mcp_server.model_pool_manager.get_storage_dir") as mock_storage,
        ):
            mock_storage.return_value = MagicMock()
            mock_storage.return_value.__truediv__ = lambda self, other: MagicMock()
            result = mpm.get_embedder("bge_code", allow_cross_pool=False)

        # Should fall back to first active-pool key, not load bge_code
        assert result.model_name in (
            "Alibaba-NLP/gte-modernbert-base",
            "BAAI/bge-m3",
        ), "Without cross-pool, should use an active-pool model"
        assert result.model_name != "BAAI/bge-code-v1"
