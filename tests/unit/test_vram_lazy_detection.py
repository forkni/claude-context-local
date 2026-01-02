"""Unit tests for lazy VRAM tier detection (Phase 1 optimization).

Tests verify that VRAM detection is deferred to first model load instead of
happening at server startup, saving 50-200ms startup time.
"""

import logging
from unittest.mock import MagicMock, patch


def test_initialize_server_state_skips_vram_detection(caplog):
    """Verify VRAM detection is NOT called during server startup."""
    from mcp_server.resource_manager import initialize_server_state

    # Mock dependencies to avoid side effects
    with (
        patch("mcp_server.services.get_state") as mock_get_state,
        patch("search.config.get_config_manager") as mock_config_mgr,
        patch(
            "mcp_server.project_persistence.load_project_selection"
        ) as mock_load_proj,
        patch("mcp_server.storage_manager.get_storage_dir") as mock_storage,
        patch("mcp_server.cleanup_queue.CleanupQueue") as mock_cleanup,
        patch("search.vram_manager.VRAMTierManager") as mock_vram_mgr,
    ):
        # Setup mocks
        mock_state = MagicMock()
        mock_get_state.return_value = mock_state

        mock_config = MagicMock()
        mock_config_manager = MagicMock()
        mock_config_manager.load_config.return_value = mock_config
        mock_config_mgr.return_value = mock_config_manager

        mock_load_proj.return_value = None
        mock_storage.return_value = MagicMock()

        mock_cleanup_instance = MagicMock()
        mock_cleanup_instance.process.return_value = {"processed": 0, "failed": []}
        mock_cleanup.return_value = mock_cleanup_instance

        # Capture logs
        with caplog.at_level(logging.INFO):
            initialize_server_state()

        # CRITICAL ASSERTION: VRAMTierManager should NOT be instantiated during startup
        mock_vram_mgr.assert_not_called()

        # Verify deferred message in logs
        assert any(
            "VRAM tier detection deferred" in record.message
            for record in caplog.records
        ), "Expected log message about deferred VRAM detection not found"


def test_vram_detection_on_first_embedder_request():
    """Verify VRAM tier detected lazily on first get_embedder() call."""
    from mcp_server.model_pool_manager import get_embedder
    from search.vram_manager import VRAMTier

    # Mock dependencies
    with (
        patch("mcp_server.services.get_state") as mock_get_state,
        patch("mcp_server.storage_manager.get_storage_dir") as mock_storage,
        patch("mcp_server.services.get_config") as mock_get_config,
        patch("search.vram_manager.VRAMTierManager") as mock_vram_mgr_class,
        patch("mcp_server.model_pool_manager.CodeEmbedder") as mock_embedder_class,
    ):
        # Setup state with dict-like behavior for embedders
        mock_state = MagicMock()
        mock_state.multi_model_enabled = True
        embedders_dict = {}
        mock_state.embedders = embedders_dict

        # Mock set_embedder to actually update the dict
        def set_embedder_side_effect(key, embedder):
            embedders_dict[key] = embedder

        mock_state.set_embedder.side_effect = set_embedder_side_effect

        mock_get_state.return_value = mock_state

        mock_storage.return_value = MagicMock()

        # Setup config with Qwen3-4B (which triggers VRAM detection)
        mock_config = MagicMock()
        mock_config.embedding.model_name = "Qwen/Qwen3-Embedding-4B"
        mock_get_config.return_value = mock_config

        # Setup VRAM tier manager to return laptop tier (forces downgrade)
        mock_vram_mgr = MagicMock()
        mock_tier = VRAMTier(
            name="laptop",
            min_vram_gb=6,
            max_vram_gb=10,
            recommended_model="Qwen/Qwen3-Embedding-0.6B",
            multi_model_enabled=True,
            neural_reranking_enabled=True,
        )
        mock_vram_mgr.detect_tier.return_value = mock_tier
        mock_vram_mgr_class.return_value = mock_vram_mgr

        # Setup embedder mock
        mock_embedder = MagicMock()
        mock_embedder_class.return_value = mock_embedder

        # First get_embedder() call for qwen3
        embedder_result = get_embedder(model_key="qwen3")

        # CRITICAL ASSERTION: VRAMTierManager should be instantiated on first model load
        mock_vram_mgr_class.assert_called_once()
        mock_vram_mgr.detect_tier.assert_called_once()

        # Verify embedder was loaded with downgraded model (0.6B, not 4B)
        mock_embedder_class.assert_called_once()
        call_kwargs = mock_embedder_class.call_args.kwargs
        assert "Qwen3-Embedding-0.6B" in call_kwargs["model_name"]
        assert "4B" not in call_kwargs["model_name"]

        # Verify the returned embedder is correct
        assert embedder_result is mock_embedder


def test_vram_tier_cached_after_first_detection():
    """Verify second get_embedder() call doesn't re-detect VRAM."""
    from mcp_server.model_pool_manager import get_embedder
    from search.vram_manager import VRAMTier

    # Mock dependencies
    with (
        patch("mcp_server.services.get_state") as mock_get_state,
        patch("mcp_server.storage_manager.get_storage_dir") as mock_storage,
        patch("mcp_server.services.get_config") as mock_get_config,
        patch("search.vram_manager.VRAMTierManager") as mock_vram_mgr_class,
        patch("mcp_server.model_pool_manager.CodeEmbedder") as mock_embedder_class,
    ):
        # Setup state with dict-like behavior for embedders
        mock_state = MagicMock()
        mock_state.multi_model_enabled = True
        embedders_dict = {}
        mock_state.embedders = embedders_dict

        # Mock set_embedder to actually update the dict
        def set_embedder_side_effect(key, embedder):
            embedders_dict[key] = embedder

        mock_state.set_embedder.side_effect = set_embedder_side_effect

        mock_get_state.return_value = mock_state

        mock_storage.return_value = MagicMock()

        # Setup config with Qwen3-4B
        mock_config = MagicMock()
        mock_config.embedding.model_name = "Qwen/Qwen3-Embedding-4B"
        mock_get_config.return_value = mock_config

        # Setup VRAM tier manager
        mock_vram_mgr = MagicMock()
        mock_tier = VRAMTier(
            name="laptop",
            min_vram_gb=6,
            max_vram_gb=10,
            recommended_model="Qwen/Qwen3-Embedding-0.6B",
            multi_model_enabled=True,
            neural_reranking_enabled=True,
        )
        mock_vram_mgr.detect_tier.return_value = mock_tier
        mock_vram_mgr_class.return_value = mock_vram_mgr

        # Setup embedder mock
        mock_embedder = MagicMock()
        mock_embedder_class.return_value = mock_embedder

        # First call - should trigger VRAM detection
        result1 = get_embedder(model_key="qwen3")

        # FIRST CALL: VRAM should be detected
        assert mock_vram_mgr_class.call_count == 1
        assert mock_vram_mgr.detect_tier.call_count == 1

        # Reset mocks to clear call counts
        mock_vram_mgr_class.reset_mock()
        mock_vram_mgr.detect_tier.reset_mock()

        # Second call for same model - should use cached embedder
        result2 = get_embedder(model_key="qwen3")

        # CRITICAL ASSERTION: VRAM tier should NOT be re-detected on second call
        # The embedder is already loaded and cached in state.embedders
        mock_vram_mgr_class.assert_not_called()
        mock_vram_mgr.detect_tier.assert_not_called()

        # Both calls should return the same cached embedder
        assert result1 is result2
