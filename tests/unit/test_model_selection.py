"""Unit tests for multi-model support and model selection."""

import tempfile
from pathlib import Path

import pytest

from embeddings.embedder import CodeEmbedder
from search.config import (SearchConfig, SearchConfigManager, get_model_config,
                           get_model_registry)


class TestModelRegistry:
    """Test model registry and configuration."""

    def test_model_registry_contains_both_models(self):
        """Test that registry contains Gemma and BGE-M3."""
        registry = get_model_registry()
        assert "google/embeddinggemma-300m" in registry
        assert "BAAI/bge-m3" in registry

    def test_gemma_config(self):
        """Test Gemma model configuration."""
        config = get_model_config("google/embeddinggemma-300m")
        assert config is not None
        assert config["dimension"] == 768
        assert config["prompt_name"] == "Retrieval-document"
        assert config["vram_gb"] == "4-8"

    def test_bge_m3_config(self):
        """Test BGE-M3 model configuration."""
        config = get_model_config("BAAI/bge-m3")
        assert config is not None
        assert config["dimension"] == 1024
        assert config["prompt_name"] is None  # BGE-M3 doesn't use prompts
        assert config["vram_gb"] == "8-16"

    def test_unknown_model_returns_none(self):
        """Test that unknown model returns None."""
        config = get_model_config("unknown/model")
        assert config is None


class TestSearchConfigModelFields:
    """Test SearchConfig dataclass with model fields."""

    def test_default_config_uses_gemma(self):
        """Test that default config uses Gemma (backward compatibility)."""
        config = SearchConfig()
        assert config.embedding_model_name == "google/embeddinggemma-300m"
        assert config.model_dimension == 768

    def test_config_with_bge_m3(self):
        """Test creating config with BGE-M3."""
        config = SearchConfig(
            embedding_model_name="BAAI/bge-m3",
            model_dimension=1024,
        )
        assert config.embedding_model_name == "BAAI/bge-m3"
        assert config.model_dimension == 1024

    def test_config_to_dict(self):
        """Test config serialization."""
        config = SearchConfig(embedding_model_name="BAAI/bge-m3")
        config_dict = config.to_dict()
        assert "embedding_model_name" in config_dict
        assert config_dict["embedding_model_name"] == "BAAI/bge-m3"

    def test_config_from_dict(self):
        """Test config deserialization."""
        config_dict = {
            "embedding_model_name": "BAAI/bge-m3",
            "model_dimension": 1024,
            "default_search_mode": "hybrid",
        }
        config = SearchConfig.from_dict(config_dict)
        assert config.embedding_model_name == "BAAI/bge-m3"
        assert config.model_dimension == 1024


class TestSearchConfigManager:
    """Test SearchConfigManager with model persistence."""

    def test_config_manager_default_model(self):
        """Test that config manager loads default model."""
        import tempfile
        from pathlib import Path

        # Use temp config file to avoid loading user's real config
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test_config.json"
            mgr = SearchConfigManager(config_file=str(config_file))
            config = mgr.load_config()
            # Should default to Gemma when no config exists
            assert "gemma" in config.embedding_model_name.lower()

    def test_config_manager_save_and_load(self):
        """Test saving and loading model configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test_config.json"
            mgr = SearchConfigManager(config_file=str(config_file))

            # Load default
            config = mgr.load_config()
            original_model = config.embedding_model_name

            # Change to BGE-M3
            config.embedding_model_name = "BAAI/bge-m3"
            mgr.save_config(config)

            # Verify file was created
            assert config_file.exists()

            # Load in new manager instance
            mgr2 = SearchConfigManager(config_file=str(config_file))
            config2 = mgr2.load_config()
            assert config2.embedding_model_name == "BAAI/bge-m3"

    def test_environment_variable_override(self, monkeypatch):
        """Test that CLAUDE_EMBEDDING_MODEL env var works."""
        monkeypatch.setenv("CLAUDE_EMBEDDING_MODEL", "BAAI/bge-m3")

        mgr = SearchConfigManager()
        config = mgr.load_config()
        assert config.embedding_model_name == "BAAI/bge-m3"


class TestCodeEmbedderModelSupport:
    """Test CodeEmbedder multi-model support."""

    def test_default_model_is_gemma(self):
        """Test that default model is Gemma (backward compatibility)."""
        embedder = CodeEmbedder()
        assert "gemma" in embedder.model_name.lower()

    def test_embedder_with_bge_m3(self):
        """Test creating embedder with BGE-M3."""
        embedder = CodeEmbedder(model_name="BAAI/bge-m3")
        assert embedder.model_name == "BAAI/bge-m3"

    def test_get_supported_models(self):
        """Test getting list of supported models."""
        models = CodeEmbedder.get_supported_models()
        assert isinstance(models, dict)
        assert "google/embeddinggemma-300m" in models
        assert "BAAI/bge-m3" in models

    def test_model_config_detection_gemma(self):
        """Test automatic config detection for Gemma."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")
        config = embedder._get_model_config()

        assert config["dimension"] == 768
        assert config["prompt_name"] == "Retrieval-document"

    def test_model_config_detection_bge_m3(self):
        """Test automatic config detection for BGE-M3."""
        embedder = CodeEmbedder(model_name="BAAI/bge-m3")
        config = embedder._get_model_config()

        assert config["dimension"] == 1024
        assert config["prompt_name"] is None  # No prompts for BGE-M3

    def test_model_config_detection_unknown_model(self):
        """Test fallback config for unknown models."""
        embedder = CodeEmbedder(model_name="unknown/test-model")
        config = embedder._get_model_config()

        # Should fall back to defaults
        assert config["dimension"] == 768
        assert config["prompt_name"] is None

    def test_model_config_caching(self):
        """Test that model config is cached after first access."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")

        # First access
        config1 = embedder._get_model_config()
        # Second access should return cached version
        config2 = embedder._get_model_config()

        assert config1 is config2  # Same object reference


class TestModelDimensionValidation:
    """Test dimension validation in search configuration."""

    def test_gemma_dimension(self):
        """Test that Gemma uses 768 dimensions."""
        config = get_model_config("google/embeddinggemma-300m")
        assert config["dimension"] == 768

    def test_bge_m3_dimension(self):
        """Test that BGE-M3 uses 1024 dimensions."""
        config = get_model_config("BAAI/bge-m3")
        assert config["dimension"] == 1024

    def test_dimension_mismatch_detection(self):
        """Test that different models have different dimensions."""
        gemma_config = get_model_config("google/embeddinggemma-300m")
        bge_config = get_model_config("BAAI/bge-m3")

        assert gemma_config["dimension"] != bge_config["dimension"]
        assert gemma_config["dimension"] == 768
        assert bge_config["dimension"] == 1024


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_old_code_still_works(self):
        """Test that code not specifying model still works."""
        # This should default to Gemma
        embedder = CodeEmbedder()
        assert embedder.model_name == "google/embeddinggemma-300m"

    def test_config_without_model_fields(self):
        """Test that config works without new model fields."""
        # Old config dict without model fields
        old_config = {
            "default_search_mode": "hybrid",
            "bm25_weight": 0.4,
            "dense_weight": 0.6,
        }

        config = SearchConfig.from_dict(old_config)
        # Should use defaults for missing fields
        assert config.embedding_model_name == "google/embeddinggemma-300m"
        assert config.model_dimension == 768


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
