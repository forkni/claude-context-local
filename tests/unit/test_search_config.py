"""Tests for search configuration system."""

import os
import json
import tempfile
import pytest
from unittest.mock import patch

from search.config import SearchConfig, SearchConfigManager, get_search_config


class TestSearchConfig:
    """Test SearchConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SearchConfig()

        assert config.default_search_mode == "hybrid"
        assert config.enable_hybrid_search is True
        assert config.bm25_weight == 0.4
        assert config.dense_weight == 0.6
        assert config.use_parallel_search is True

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        config = SearchConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict['default_search_mode'] == "hybrid"
        assert config_dict['enable_hybrid_search'] is True

    def test_from_dict_creation(self):
        """Test creation from dictionary."""
        data = {
            "default_search_mode": "semantic",
            "bm25_weight": 0.3,
            "dense_weight": 0.7
        }

        config = SearchConfig.from_dict(data)
        assert config.default_search_mode == "semantic"
        assert config.bm25_weight == 0.3
        assert config.dense_weight == 0.7
        assert config.enable_hybrid_search is True  # Default value


class TestSearchConfigManager:
    """Test SearchConfigManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

    def test_load_default_config(self):
        """Test loading default configuration."""
        manager = SearchConfigManager(self.config_file)
        config = manager.load_config()

        assert isinstance(config, SearchConfig)
        assert config.default_search_mode == "hybrid"

    def test_load_from_file(self):
        """Test loading configuration from file."""
        # Create test config file
        test_config = {
            "default_search_mode": "bm25",
            "bm25_weight": 0.5,
            "enable_hybrid_search": False
        }

        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)

        # Load config
        manager = SearchConfigManager(self.config_file)
        config = manager.load_config()

        assert config.default_search_mode == "bm25"
        assert config.bm25_weight == 0.5
        assert config.enable_hybrid_search is False

    def test_environment_overrides(self):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            'CLAUDE_SEARCH_MODE': 'semantic',
            'CLAUDE_ENABLE_HYBRID': 'false',
            'CLAUDE_BM25_WEIGHT': '0.8'
        }):
            manager = SearchConfigManager(self.config_file)
            config = manager.load_config()

            assert config.default_search_mode == "semantic"
            assert config.enable_hybrid_search is False
            assert config.bm25_weight == 0.8

    def test_save_config(self):
        """Test saving configuration."""
        config = SearchConfig()
        config.default_search_mode = "bm25"
        config.bm25_weight = 0.7

        manager = SearchConfigManager(self.config_file)
        manager.save_config(config)

        # Verify file was created
        assert os.path.exists(self.config_file)

        # Verify content
        with open(self.config_file, 'r') as f:
            saved_data = json.load(f)

        assert saved_data['default_search_mode'] == "bm25"
        assert saved_data['bm25_weight'] == 0.7

    def test_auto_mode_detection(self):
        """Test automatic search mode detection."""
        # Create config with auto mode
        test_config = {"default_search_mode": "auto"}
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)

        manager = SearchConfigManager(self.config_file)

        # Text-heavy query should suggest BM25
        mode = manager.get_search_mode_for_query("find error message text")
        assert mode == "bm25"

        # Code structure query should suggest semantic
        mode = manager.get_search_mode_for_query("find class definition")
        assert mode == "semantic"

        # Generic query should default to hybrid
        mode = manager.get_search_mode_for_query("database connection")
        assert mode == "hybrid"

    def test_explicit_mode_override(self):
        """Test explicit mode override."""
        # Create config with auto mode
        test_config = {"default_search_mode": "auto"}
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)

        manager = SearchConfigManager(self.config_file)

        # Explicit mode should override auto-detection
        mode = manager.get_search_mode_for_query("find error message", explicit_mode="semantic")
        assert mode == "semantic"

        # Auto mode should fall back to detection
        mode = manager.get_search_mode_for_query("find error message", explicit_mode="auto")
        assert mode == "bm25"


def test_global_config_functions():
    """Test global configuration functions."""
    config = get_search_config()
    assert isinstance(config, SearchConfig)

    # Test helper functions
    from search.config import is_hybrid_search_enabled, get_default_search_mode

    assert isinstance(is_hybrid_search_enabled(), bool)
    assert get_default_search_mode() in ["hybrid", "semantic", "bm25", "auto"]