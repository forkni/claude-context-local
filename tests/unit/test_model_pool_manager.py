"""Unit tests for get_model_key_from_name cross-pool lookup and get_embedder opt-in.

Covers the fix for: index built with a model from pool A is silently discarded
when the active pool switches to pool B (dimension mismatch → forced reindex).

Also covers Block B (explicit override), Block C (multi-model lazy load), and the
_load_pool_embedder private helper that deduplicates all three lazy-load blocks.
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

    def test_cross_pool_resolves_coderankembed(self, caplog):
        """coderankembed is mapped to 'coderankembed' even when active pool is lightweight-speed."""
        import logging

        from mcp_server import model_pool_manager as mpm

        # Active pool = lightweight-speed (does not contain coderankembed)
        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            caplog.at_level(logging.INFO, logger="mcp_server.model_pool_manager"),
        ):
            key = mpm.get_model_key_from_name("nomic-ai/CodeRankEmbed")

        assert key == "coderankembed", (
            "CodeRankEmbed should resolve via cross-pool fallback even when active "
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
        assert key == "qwen3_0.6b"

    def test_unknown_model_returns_none(self):
        """A model not registered in any pool returns None (no crash)."""
        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with patch.object(mpm, "_model_pool_manager", mgr):
            key = mpm.get_model_key_from_name("some/nonexistent-model-v99")
        assert key is None

    def test_all_pool_models_contains_both_pools(self):
        """ALL_POOL_MODELS is the union of both pool dicts (sanity check)."""
        assert "coderankembed" in ALL_POOL_MODELS
        assert "qwen3_0.6b" in ALL_POOL_MODELS
        assert "gte_modernbert" in ALL_POOL_MODELS
        assert "bge_m3" in ALL_POOL_MODELS


class TestGetModelNameFromKey:
    """Forward-lookup from pool key to full model name."""

    def test_active_pool_fast_path(self):
        """Key in the active pool resolves without cross-pool log."""
        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with patch.object(mpm, "_model_pool_manager", mgr):
            name = mpm.get_model_name_from_key("bge_m3")
        assert name == "BAAI/bge-m3"

    def test_cross_pool_resolves_qwen3(self, caplog):
        """qwen3_0.6b resolves when active pool is lightweight-speed."""
        import logging

        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            caplog.at_level(logging.INFO, logger="mcp_server.model_pool_manager"),
        ):
            name = mpm.get_model_name_from_key("qwen3_0.6b")

        assert name == "Qwen/Qwen3-Embedding-0.6B"
        assert any("[CROSS_POOL]" in rec.message for rec in caplog.records)

    def test_cross_pool_resolves_coderankembed(self, caplog):
        """coderankembed resolves when active pool is lightweight-speed."""
        import logging

        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            caplog.at_level(logging.INFO, logger="mcp_server.model_pool_manager"),
        ):
            name = mpm.get_model_name_from_key("coderankembed")

        assert name == "nomic-ai/CodeRankEmbed"
        assert any("[CROSS_POOL]" in rec.message for rec in caplog.records)

    def test_unknown_key_returns_none(self):
        """A key not in any pool returns None."""
        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with patch.object(mpm, "_model_pool_manager", mgr):
            name = mpm.get_model_name_from_key("nonexistent_key_v99")
        assert name is None


class TestGetEmbedderCrossPool:
    """get_embedder(allow_cross_pool=True) loads models outside the active pool."""

    def _make_fake_embedder(self, model_name: str):
        emb = MagicMock()
        emb.model_name = model_name
        return emb

    def test_cross_pool_opt_in_loads_coderankembed(self, caplog):
        """With allow_cross_pool=True, coderankembed loads even when pool=lightweight-speed."""
        import logging

        from mcp_server import model_pool_manager as mpm

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        fake_embedder = self._make_fake_embedder("nomic-ai/CodeRankEmbed")

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
            result = mpm.get_embedder("coderankembed", allow_cross_pool=True)

        mock_embedder_cls.assert_called_once()
        call_kwargs = mock_embedder_cls.call_args
        assert call_kwargs.kwargs.get("model_name") == "nomic-ai/CodeRankEmbed" or (
            call_kwargs.args and call_kwargs.args[0] == "nomic-ai/CodeRankEmbed"
        ), "CodeEmbedder should be constructed with nomic-ai/CodeRankEmbed model name"
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


# ---------------------------------------------------------------------------
# Tests: Block B (explicit override) and Block C (multi-model lazy load)
# ---------------------------------------------------------------------------


class TestGetEmbedderOverride:
    """Block B of get_embedder: explicit model_key in active pool loads it directly."""

    def _make_fake_embedder(self, model_name: str):
        emb = MagicMock()
        emb.model_name = model_name
        return emb

    def _make_state_mock(self, embedders=None, *, multi_model_enabled=True):
        state_mock = MagicMock()
        state_mock.multi_model_enabled = multi_model_enabled
        state_mock.embedders = embedders if embedders is not None else {}

        def set_embedder(key, emb):
            state_mock.embedders[key] = emb

        state_mock.set_embedder.side_effect = set_embedder
        return state_mock

    def _patch_storage(self, mock_storage):
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.__truediv__ = lambda self, other: MagicMock()

    def test_override_explicit_model_key_loads_and_returns(self, caplog):
        """Block B: explicit model_key in active pool constructs, registers, and returns it."""
        import logging

        from mcp_server import model_pool_manager as mpm

        pool = MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED
        mgr = _make_pool_manager_with_active_pool(pool)
        first_key = next(iter(pool.keys()))
        fake_model = self._make_fake_embedder(pool[first_key])
        state_mock = self._make_state_mock()

        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            patch("mcp_server.model_pool_manager.get_state", return_value=state_mock),
            patch(
                "mcp_server.model_pool_manager.CodeEmbedder", return_value=fake_model
            ) as mock_cls,
            patch("mcp_server.model_pool_manager.get_storage_dir") as mock_storage,
            caplog.at_level(logging.INFO, logger="mcp_server.model_pool_manager"),
        ):
            self._patch_storage(mock_storage)
            result = mpm.get_embedder(first_key)

        mock_cls.assert_called_once()
        assert result is fake_model
        assert any("[OVERRIDE]" in rec.message for rec in caplog.records)
        assert any("explicit override" in rec.message for rec in caplog.records)

    def test_override_falls_back_to_pool_model_on_load_failure(self):
        """Block B: CodeEmbedder raises → falls back to an already-loaded pool model."""
        from mcp_server import model_pool_manager as mpm

        pool = MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED
        mgr = _make_pool_manager_with_active_pool(pool)
        first_key = next(iter(pool.keys()))
        request_key = next(k for k in pool if k != first_key)  # any non-first key
        fake_first = self._make_fake_embedder(pool[first_key])
        state_mock = self._make_state_mock({first_key: fake_first})

        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            patch("mcp_server.model_pool_manager.get_state", return_value=state_mock),
            patch(
                "mcp_server.model_pool_manager.CodeEmbedder",
                side_effect=RuntimeError("GPU OOM"),
            ),
            patch("mcp_server.model_pool_manager.get_storage_dir") as mock_storage,
        ):
            self._patch_storage(mock_storage)
            result = mpm.get_embedder(request_key)

        # Falls back to the first pool key, which is already loaded
        assert result is fake_first

    def test_override_raises_when_no_fallback_available(self):
        """Block B: CodeEmbedder raises and no pool model is loaded → propagates."""
        import pytest

        from mcp_server import model_pool_manager as mpm

        pool = MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED
        mgr = _make_pool_manager_with_active_pool(pool)
        first_key = next(iter(pool.keys()))
        request_key = next(k for k in pool if k != first_key)
        state_mock = self._make_state_mock()  # empty embedders — no fallback

        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            patch("mcp_server.model_pool_manager.get_state", return_value=state_mock),
            patch(
                "mcp_server.model_pool_manager.CodeEmbedder",
                side_effect=RuntimeError("no GPU"),
            ),
            patch("mcp_server.model_pool_manager.get_storage_dir") as mock_storage,
            pytest.raises(RuntimeError, match="no GPU"),
        ):
            self._patch_storage(mock_storage)
            mpm.get_embedder(request_key)

    def test_multimodel_first_load_emits_first_use_log(self, caplog):
        """Block C: cold-start (empty embedders, model_key=None) emits [FIRST USE] and 'Ready' log."""
        import logging

        from mcp_server import model_pool_manager as mpm

        pool = MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED
        mgr = _make_pool_manager_with_active_pool(pool)
        first_key = next(iter(pool.keys()))
        fake_model = MagicMock()
        state_mock = self._make_state_mock(
            multi_model_enabled=True
        )  # empty → cold start

        mock_config = MagicMock()
        mock_config.embedding.model_name = pool[first_key]  # maps to first_key

        with (
            patch.object(mpm, "_model_pool_manager", mgr),
            patch("mcp_server.model_pool_manager.get_state", return_value=state_mock),
            patch("mcp_server.model_pool_manager.get_config", return_value=mock_config),
            patch(
                "mcp_server.model_pool_manager.CodeEmbedder", return_value=fake_model
            ),
            patch("mcp_server.model_pool_manager.get_storage_dir") as mock_storage,
            caplog.at_level(logging.INFO, logger="mcp_server.model_pool_manager"),
        ):
            self._patch_storage(mock_storage)
            result = mpm.get_embedder()  # model_key=None → resolves from config

        assert result is fake_model
        assert any("[FIRST USE]" in rec.message for rec in caplog.records), (
            "Cold-start load should emit a [FIRST USE] log"
        )
        assert any(
            "Ready for fast searches" in rec.message for rec in caplog.records
        ), "Cold-start success should log 'Ready for fast searches'"


# ---------------------------------------------------------------------------
# Tests: _load_pool_embedder private helper
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tests: get_pool_config() single-model mode
# ---------------------------------------------------------------------------


class TestGetPoolConfigSingleModelMode:
    """get_pool_config() must return a single-entry pool when multi_model_enabled=False.

    Regression guard for: stale multi_model_pool config value (e.g. "lightweight-speed"
    left over from another machine) causing the active pool to exclude the actual
    operational model, which triggers spurious [CROSS_POOL] INFO/WARNING logs on every
    search request even though search is functionally correct.
    """

    def _make_config(
        self,
        *,
        multi_model_enabled: bool,
        default_model: str = "qwen3_0.6b",
        multi_model_pool: str | None = "lightweight-speed",
        embedding_model: str = "Qwen/Qwen3-Embedding-0.6B",
    ):
        cfg = MagicMock()
        cfg.routing.multi_model_enabled = multi_model_enabled
        cfg.routing.default_model = default_model
        cfg.routing.multi_model_pool = multi_model_pool
        cfg.embedding.model_name = embedding_model
        return cfg

    def test_single_model_mode_returns_single_entry_pool(self):
        """Single-model mode: pool contains exactly {default_model: embedding.model_name}."""
        from mcp_server.model_pool_manager import ModelPoolManager

        mgr = ModelPoolManager()
        cfg = self._make_config(multi_model_enabled=False)

        with patch("search.config.get_search_config", return_value=cfg):
            pool = mgr.get_pool_config()

        assert pool == {"qwen3_0.6b": "Qwen/Qwen3-Embedding-0.6B"}, (
            "Single-model pool must contain exactly the configured model "
            "so reverse-lookups never trip the cross-pool path"
        )

    def test_single_model_mode_ignores_stale_lightweight_speed_preset(self):
        """Stale multi_model_pool='lightweight-speed' must not affect single-model pool."""
        from mcp_server.model_pool_manager import ModelPoolManager

        mgr = ModelPoolManager()
        cfg = self._make_config(
            multi_model_enabled=False,
            multi_model_pool="lightweight-speed",  # stale laptop value
        )

        with patch("search.config.get_search_config", return_value=cfg):
            pool = mgr.get_pool_config()

        assert "gte_modernbert" not in pool, (
            "gte_modernbert must not appear in single-model pool"
        )
        assert "bge_m3" not in pool, "bge_m3 must not appear in single-model pool"
        assert "qwen3_0.6b" in pool, "active single model must be present"

    def test_multi_model_mode_still_uses_pool_preset_unchanged(self):
        """multi_model_enabled=True must keep the existing pool-preset logic intact."""
        from mcp_server.model_pool_manager import ModelPoolManager
        from search.config import MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED

        mgr = ModelPoolManager()
        cfg = self._make_config(
            multi_model_enabled=True,
            multi_model_pool="lightweight-speed",
        )

        with patch("search.config.get_search_config", return_value=cfg):
            pool = mgr.get_pool_config()

        assert pool == MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED, (
            "Multi-model mode must still return the configured pool preset unchanged"
        )

    def test_single_model_mode_unknown_model_no_crash(self):
        """Unknown model name in single-model mode falls back gracefully — no crash."""
        from mcp_server.model_pool_manager import ModelPoolManager

        mgr = ModelPoolManager()
        cfg = self._make_config(
            multi_model_enabled=False,
            default_model="custom_model",
            embedding_model="my-org/custom-embedding-model-v1",
        )

        with patch("search.config.get_search_config", return_value=cfg):
            pool = mgr.get_pool_config()

        assert pool == {"custom_model": "my-org/custom-embedding-model-v1"}, (
            "Unknown model still produces a valid pool mapping — no crash"
        )


class TestLoadPoolEmbedderHelper:
    """Direct tests for the _load_pool_embedder private method."""

    def test_idempotent_returns_cached_without_reconstructing(self):
        """Already-loaded model_key returns the cached instance; CodeEmbedder not called."""
        from pathlib import Path

        existing = MagicMock()
        state_mock = MagicMock()
        state_mock.embedders = {"bge_m3": existing}

        mgr = _make_pool_manager_with_active_pool(MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED)
        with patch("mcp_server.model_pool_manager.CodeEmbedder") as mock_cls:
            result = mgr._load_pool_embedder(
                state_mock,
                "bge_m3",
                "BAAI/bge-m3",
                Path("/tmp/models"),
                allow_fallback=False,
                exc_info=False,
            )

        mock_cls.assert_not_called()
        assert result is existing
