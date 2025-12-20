"""Tests for configuration synchronization between UI, MCP tools, and ApplicationState."""

import json
import os
import tempfile
from unittest.mock import patch

from mcp_server.state import get_state, reset_state
from search.config import SearchConfig, SearchConfigManager


class TestMultiModelEnabledPersistence:
    """Test multi_model_enabled field in SearchConfig."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

    def test_multi_model_enabled_default_true(self):
        """Test default value is True."""
        config = SearchConfig()
        assert config.routing.multi_model_enabled is True

    def test_multi_model_enabled_persistence(self):
        """Test multi_model_enabled saves and loads from file."""
        # Clear env var to test file persistence only
        with patch.dict(os.environ, {}, clear=True):
            manager = SearchConfigManager(self.config_file)
            config = manager.load_config()

            # Change value
            config.routing.multi_model_enabled = False
            manager.save_config(config)

            # Reload and verify
            manager._config = None  # Clear cache
            loaded = manager.load_config()
            assert loaded.routing.multi_model_enabled is False

    def test_env_override_multi_model(self):
        """Test environment variable overrides config file."""
        # Create config with multi_model_enabled=True
        test_config = {"multi_model_enabled": True}
        with open(self.config_file, "w") as f:
            json.dump(test_config, f)

        # Override via env
        with patch.dict(os.environ, {"CLAUDE_MULTI_MODEL_ENABLED": "false"}):
            manager = SearchConfigManager(self.config_file)
            config = manager.load_config()
            assert config.routing.multi_model_enabled is False

    def test_multi_model_env_values(self):
        """Test various environment variable values."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("enabled", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"CLAUDE_MULTI_MODEL_ENABLED": env_value}):
                manager = SearchConfigManager(self.config_file)
                config = manager.load_config()
                assert (
                    config.routing.multi_model_enabled == expected
                ), f"Failed for env_value={env_value}"


class TestApplicationStateSyncFromConfig:
    """Test ApplicationState.sync_from_config() method."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_state()
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

    def test_sync_from_config_basic(self):
        """Test basic sync from config."""
        # Clear env var to test config-only sync
        with patch.dict(os.environ, {}, clear=True):
            config = SearchConfig()
            config.routing.multi_model_enabled = False

            state = get_state()
            state.sync_from_config(config)

            assert state.multi_model_enabled is False

    def test_sync_env_overrides_config(self):
        """Test environment variable overrides config during sync."""
        config = SearchConfig()
        config.routing.multi_model_enabled = True

        with patch.dict(os.environ, {"CLAUDE_MULTI_MODEL_ENABLED": "false"}):
            state = get_state()
            state.sync_from_config(config)
            assert state.multi_model_enabled is False

    def test_sync_config_used_when_no_env(self):
        """Test config value used when no env var set."""
        config = SearchConfig()
        config.routing.multi_model_enabled = False

        # Ensure no env var is set
        with patch.dict(os.environ, {}, clear=True):
            state = get_state()
            state.sync_from_config(config)
            assert state.multi_model_enabled is False

    def test_sync_various_env_values(self):
        """Test sync with various environment variable values."""
        config = SearchConfig()
        config.routing.multi_model_enabled = False  # Config says False

        test_cases = [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("0", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"CLAUDE_MULTI_MODEL_ENABLED": env_value}):
                state = get_state()
                state.sync_from_config(config)
                assert (
                    state.multi_model_enabled == expected
                ), f"Failed for env_value={env_value}"


class TestSearchModeConfigPersistence:
    """Test search mode and weights persistence."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

    def test_search_mode_persistence(self):
        """Test default_search_mode saves and loads."""
        manager = SearchConfigManager(self.config_file)
        config = manager.load_config()

        # Change search mode
        config.search_mode.default_mode = "bm25"
        manager.save_config(config)

        # Reload and verify
        manager._config = None
        loaded = manager.load_config()
        assert loaded.search_mode.default_mode == "bm25"

    def test_weights_persistence(self):
        """Test BM25 and Dense weights save and load."""
        manager = SearchConfigManager(self.config_file)
        config = manager.load_config()

        # Change weights
        config.search_mode.bm25_weight = 0.3
        config.search_mode.dense_weight = 0.7
        manager.save_config(config)

        # Reload and verify
        manager._config = None
        loaded = manager.load_config()
        assert loaded.search_mode.bm25_weight == 0.3
        assert loaded.search_mode.dense_weight == 0.7

    def test_all_settings_together(self):
        """Test all config settings persist together."""
        # Clear env vars to test file persistence only
        with patch.dict(os.environ, {}, clear=True):
            manager = SearchConfigManager(self.config_file)
            config = manager.load_config()

            # Change all settings
            config.search_mode.default_mode = "semantic"
            config.search_mode.bm25_weight = 0.5
            config.search_mode.dense_weight = 0.5
            config.routing.multi_model_enabled = False
            manager.save_config(config)

            # Reload and verify all
            manager._config = None
            loaded = manager.load_config()
            assert loaded.search_mode.default_mode == "semantic"
            assert loaded.search_mode.bm25_weight == 0.5
            assert loaded.search_mode.dense_weight == 0.5
            assert loaded.routing.multi_model_enabled is False
