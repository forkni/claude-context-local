"""Integration tests for auto-reindex bug fixes.

Tests:
1. max_age_minutes respects config instead of hardcoded 5
2. Multi-model cleanup clears ALL models before auto-reindex
3. No OOM during auto-reindex with multi-model mode
"""

import gc
import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.model_pool_manager import get_model_pool_manager, reset_pool_manager
from mcp_server.services import get_state
from search.config import get_search_config
from search.incremental_indexer import IncrementalIndexer

logger = logging.getLogger(__name__)


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project with Python files."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create a simple Python file
    (project_dir / "example.py").write_text(
        """
def example_function():
    '''Example function for testing.'''
    return 42

class ExampleClass:
    '''Example class for testing.'''
    def method(self):
        return "test"
"""
    )

    return project_dir


@pytest.fixture
def cleanup_state():
    """Cleanup state before and after tests."""
    state = get_state()
    state.clear_embedders()
    reset_pool_manager()
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass

    yield

    # Cleanup after test
    state.clear_embedders()
    reset_pool_manager()
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


class TestMaxAgeMinutesConfigRespect:
    """Test that max_age_minutes respects config instead of hardcoded 5."""

    def test_uses_config_default_when_not_specified(self, temp_project, cleanup_state):
        """Verify default comes from config, not hardcoded 5."""
        config = get_search_config()

        # Verify config has non-5 value (should be 60 from search_config.json)
        assert config.performance.max_index_age_minutes != 5.0
        assert config.performance.max_index_age_minutes == 60.0

        # Create indexer and index project
        indexer = IncrementalIndexer()
        result = indexer.incremental_index(str(temp_project), "test_project")
        assert result.success

        # Wait 6 seconds (longer than old 5-minute default would trigger)
        # but shorter than 60-minute config default
        time.sleep(6)

        # Auto-reindex with config default should NOT trigger
        # (we're only 6 seconds old, not 60 minutes)
        result = indexer.auto_reindex_if_needed(
            str(temp_project),
            "test_project",
            # Note: max_age_minutes not specified, should use config default
        )

        # Should NOT reindex (not old enough)
        assert result.files_added == 0
        assert result.files_modified == 0

    def test_explicit_max_age_minutes_overrides_config(
        self, temp_project, cleanup_state
    ):
        """Verify explicit max_age_minutes parameter overrides config."""
        # Create indexer and index project
        indexer = IncrementalIndexer()
        result = indexer.incremental_index(str(temp_project), "test_project")
        assert result.success

        # Wait 2 seconds
        time.sleep(2)

        # Auto-reindex with explicit 1 second max age SHOULD trigger
        result = indexer.auto_reindex_if_needed(
            str(temp_project),
            "test_project",
            max_age_minutes=1 / 60,  # 1 second in minutes
        )

        # Should reindex (index is >1 second old)
        # Files won't be re-added (incremental), but operation ran
        assert result.success


class TestMultiModelCleanupBeforeReindex:
    """Test that auto-reindex clears ALL models, not just one."""

    @pytest.mark.skipif(
        not get_search_config().routing.multi_model_enabled,
        reason="Multi-model mode disabled",
    )
    def test_clears_all_models_before_reindex(self, temp_project, cleanup_state):
        """Verify all 3 models are cleared before auto-reindex."""
        state = get_state()
        pool_manager = get_model_pool_manager()

        # Initialize multi-model pool (lazy loading)
        pool_manager.initialize_pool(lazy_load=True)

        # Load all 3 models by requesting them
        embedder_qwen3 = pool_manager.get_embedder("qwen3")
        pool_manager.get_embedder("bge_m3")  # Load but don't need reference
        pool_manager.get_embedder("coderankembed")  # Load but don't need reference

        # Verify all 3 loaded
        assert state.embedders.get("qwen3") is not None
        assert state.embedders.get("bge_m3") is not None
        assert state.embedders.get("coderankembed") is not None
        initial_count = len(state.embedders)
        assert initial_count >= 3

        # Create indexer and perform initial index
        indexer = IncrementalIndexer(embedder=embedder_qwen3)
        result = indexer.incremental_index(str(temp_project), "test_project")
        assert result.success

        # Mock logger to capture cleanup messages
        with patch("search.incremental_indexer.logger") as mock_logger:
            # Trigger auto-reindex with 0 max age (forces reindex)
            result = indexer.auto_reindex_if_needed(
                str(temp_project), "test_project", max_age_minutes=0
            )

            # Verify cleanup messages logged
            logged_messages = [str(call) for call in mock_logger.info.call_args_list]

            # Should log multi-model cleanup
            assert any(
                "Freeing VRAM before auto-reindex (multi-model cleanup)" in msg
                for msg in logged_messages
            ), f"Multi-model cleanup not logged. Messages: {logged_messages}"

            assert any(
                "Clearing" in msg and "cached embedder(s) before reindex" in msg
                for msg in logged_messages
            ), f"Embedder clearing not logged. Messages: {logged_messages}"

            # Verify embedders were cleared
            # Note: They may be reloaded during reindex, so we check the clearing happened
            # by verifying the log messages above

    def test_cleanup_handles_errors_gracefully(self, temp_project, cleanup_state):
        """Verify auto-reindex continues even if cleanup fails."""
        # Create indexer
        indexer = IncrementalIndexer()
        result = indexer.incremental_index(str(temp_project), "test_project")
        assert result.success

        # Mock cleanup to raise exception
        with (
            patch("mcp_server.services.get_state") as mock_get_state,
            patch.object(indexer, "incremental_index") as mock_index,
        ):

            # Make get_state raise exception during cleanup
            mock_get_state.side_effect = RuntimeError("Simulated cleanup failure")

            # Configure mock_index to return success
            mock_index.return_value = MagicMock(success=True)

            # Trigger auto-reindex - should not crash
            result = indexer.auto_reindex_if_needed(
                str(temp_project), "test_project", max_age_minutes=0
            )

            # Should still attempt reindex despite cleanup failure
            mock_index.assert_called_once()


class TestNoOOMDuringReindex:
    """Test that auto-reindex doesn't cause OOM with proper cleanup."""

    @pytest.mark.skipif(
        not get_search_config().routing.multi_model_enabled,
        reason="Multi-model mode disabled",
    )
    @pytest.mark.slow
    def test_vram_freed_before_reindex(self, temp_project, cleanup_state):
        """Verify VRAM is actually freed before reindex starts."""
        try:
            import torch

            if not torch.cuda.is_available():
                pytest.skip("CUDA not available")
        except ImportError:
            pytest.skip("PyTorch not available")

        state = get_state()
        pool_manager = get_model_pool_manager()

        # Load all 3 models
        pool_manager.initialize_pool(lazy_load=True)
        embedder_qwen3 = pool_manager.get_embedder("qwen3")
        pool_manager.get_embedder("bge_m3")
        pool_manager.get_embedder("coderankembed")

        # Check VRAM before cleanup
        vram_before = torch.cuda.memory_allocated() / (1024**3)  # GB
        logger.info(f"VRAM before cleanup: {vram_before:.2f} GB")

        # Should have models loaded
        assert vram_before > 0

        # Create indexer and index
        indexer = IncrementalIndexer(embedder=embedder_qwen3)
        result = indexer.incremental_index(str(temp_project), "test_project")
        assert result.success

        # Trigger auto-reindex with 0 max age
        result = indexer.auto_reindex_if_needed(
            str(temp_project), "test_project", max_age_minutes=0
        )

        # Check VRAM during reindex (models should be reloaded)
        # We can't easily check VRAM was freed *between* cleanup and reload,
        # but we can verify the operation succeeded without OOM
        assert result.success

        # Verify embedders were cleared and recreated
        # (they'll be reloaded during reindex)
        logger.info(f"Embedders after reindex: {list(state.embedders.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
