"""Tests for configuration synchronization between UI, MCP tools, and ApplicationState."""

import os
import tempfile
from unittest.mock import patch

from search.config import SearchConfigManager


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
            manager.save_config(config)

            # Reload and verify all
            manager._config = None
            loaded = manager.load_config()
            assert loaded.search_mode.default_mode == "semantic"
            assert loaded.search_mode.bm25_weight == 0.5
            assert loaded.search_mode.dense_weight == 0.5
