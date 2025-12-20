"""Tests for ModelCacheManager."""

import json
import tempfile
from pathlib import Path

import pytest

from embeddings.model_cache import ModelCacheManager


class TestModelCacheManager:
    """Test suite for ModelCacheManager class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def model_config_basic(self):
        """Basic model config without trust_remote_code."""
        return {
            "model_type": "bert",
            "architectures": ["BertModel"],
            "trust_remote_code": False,
        }

    @pytest.fixture
    def model_config_trust_remote(self):
        """Model config with trust_remote_code enabled."""
        return {
            "model_type": "custom",
            "architectures": ["CustomModel"],
            "trust_remote_code": True,
        }

    @pytest.fixture
    def cache_manager(self, temp_cache_dir, model_config_basic):
        """Create a basic cache manager for testing."""
        return ModelCacheManager(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: model_config_basic,
        )

    def test_initialization(self, temp_cache_dir, model_config_basic):
        """Test cache manager initialization."""
        manager = ModelCacheManager(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: model_config_basic,
        )
        assert manager.model_name == "BAAI/bge-m3"
        assert manager.cache_dir == str(temp_cache_dir)
        assert manager._get_model_config() == model_config_basic

    def test_get_model_cache_path_org_format(self, cache_manager, temp_cache_dir):
        """Test cache path generation for org/model format."""
        cache_path = cache_manager.get_model_cache_path()
        expected = temp_cache_dir / "models--BAAI--bge-m3"
        assert cache_path == expected

    def test_get_model_cache_path_single_name(self, temp_cache_dir, model_config_basic):
        """Test cache path generation for single model name format."""
        manager = ModelCacheManager(
            model_name="bert-base-uncased",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: model_config_basic,
        )
        cache_path = manager.get_model_cache_path()
        expected = temp_cache_dir / "models--bert-base-uncased"
        assert cache_path == expected

    def test_get_model_cache_path_no_cache_dir(self, model_config_basic):
        """Test cache path returns None when cache_dir not set."""
        manager = ModelCacheManager(
            model_name="BAAI/bge-m3",
            cache_dir="",
            model_config_getter=lambda: model_config_basic,
        )
        assert manager.get_model_cache_path() is None

    def test_get_default_hf_cache_path(self, cache_manager):
        """Test default HuggingFace cache path generation."""
        default_path = cache_manager.get_default_hf_cache_path()
        expected = (
            Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-m3"
        )
        assert default_path == expected

    def test_check_config_at_location_nonexistent(self, cache_manager):
        """Test config check returns False for nonexistent location."""
        nonexistent = Path("/nonexistent/path")
        assert cache_manager.check_config_at_location(nonexistent) is False

    def test_check_config_at_location_valid(self, cache_manager, temp_cache_dir):
        """Test config check returns True for valid cache with config.json."""
        # Create cache structure
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create valid config.json
        config_path = snapshot_dir / "config.json"
        config_path.write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )

        assert cache_manager.check_config_at_location(model_dir) is True

    def test_check_config_at_location_no_snapshots(self, cache_manager, temp_cache_dir):
        """Test config check returns False when no snapshots exist."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        model_dir.mkdir(parents=True)
        (model_dir / "snapshots").mkdir()

        assert cache_manager.check_config_at_location(model_dir) is False

    def test_check_weights_at_location_safetensors(self, cache_manager, temp_cache_dir):
        """Test weights check returns True for safetensors format."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create model weights
        (snapshot_dir / "model.safetensors").write_text("dummy")

        assert cache_manager.check_weights_at_location(model_dir) is True

    def test_check_weights_at_location_pytorch(self, cache_manager, temp_cache_dir):
        """Test weights check returns True for pytorch format."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create model weights
        (snapshot_dir / "pytorch_model.bin").write_text("dummy")

        assert cache_manager.check_weights_at_location(model_dir) is True

    def test_check_weights_at_location_sharded(self, cache_manager, temp_cache_dir):
        """Test weights check returns True for sharded format."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create sharded index
        (snapshot_dir / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": {}})
        )

        assert cache_manager.check_weights_at_location(model_dir) is True

    def test_check_weights_at_location_none(self, cache_manager, temp_cache_dir):
        """Test weights check returns False when no weights exist."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # No weights files
        assert cache_manager.check_weights_at_location(model_dir) is False

    def test_check_cache_at_location_missing_config(
        self, cache_manager, temp_cache_dir
    ):
        """Test cache validation fails when config.json is missing."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create weights but no config
        (snapshot_dir / "model.safetensors").write_text("dummy")
        (snapshot_dir / "tokenizer.json").write_text("{}")

        valid, reason = cache_manager.check_cache_at_location(model_dir)
        assert valid is False
        assert "Missing config.json" in reason

    def test_check_cache_at_location_invalid_config_json(
        self, cache_manager, temp_cache_dir
    ):
        """Test cache validation fails when config.json is invalid JSON."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create invalid config.json
        (snapshot_dir / "config.json").write_text("not valid json")
        (snapshot_dir / "model.safetensors").write_text("dummy")
        (snapshot_dir / "tokenizer.json").write_text("{}")

        valid, reason = cache_manager.check_cache_at_location(model_dir)
        assert valid is False
        assert "Corrupted config.json" in reason

    def test_check_cache_at_location_missing_required_keys(
        self, cache_manager, temp_cache_dir
    ):
        """Test cache validation fails when config.json missing required keys."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create config without required keys
        (snapshot_dir / "config.json").write_text(json.dumps({"some_key": "value"}))
        (snapshot_dir / "model.safetensors").write_text("dummy")
        (snapshot_dir / "tokenizer.json").write_text("{}")

        valid, reason = cache_manager.check_cache_at_location(model_dir)
        assert valid is False
        assert "Invalid config.json" in reason
        assert "model_type" in reason or "architectures" in reason

    def test_check_cache_at_location_missing_weights(
        self, cache_manager, temp_cache_dir
    ):
        """Test cache validation fails when model weights are missing."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create config and tokenizer but no weights
        (snapshot_dir / "config.json").write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )
        (snapshot_dir / "tokenizer.json").write_text("{}")

        valid, reason = cache_manager.check_cache_at_location(model_dir)
        assert valid is False
        assert "Missing model weights" in reason

    def test_check_cache_at_location_missing_tokenizer(
        self, cache_manager, temp_cache_dir
    ):
        """Test cache validation fails when tokenizer files are missing."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create config and weights but no tokenizer
        (snapshot_dir / "config.json").write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )
        (snapshot_dir / "model.safetensors").write_text("dummy")

        valid, reason = cache_manager.check_cache_at_location(model_dir)
        assert valid is False
        assert "Missing tokenizer files" in reason

    def test_check_cache_at_location_valid_cache(self, cache_manager, temp_cache_dir):
        """Test cache validation passes for complete valid cache."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create complete cache
        (snapshot_dir / "config.json").write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )
        (snapshot_dir / "model.safetensors").write_text("dummy")
        (snapshot_dir / "tokenizer.json").write_text("{}")

        valid, reason = cache_manager.check_cache_at_location(model_dir)
        assert valid is True
        assert "Valid cache" in reason

    def test_check_cache_at_location_sharded_missing_shards(
        self, cache_manager, temp_cache_dir
    ):
        """Test cache validation fails for sharded model with missing shard files."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create index with missing shards
        (snapshot_dir / "config.json").write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )
        (snapshot_dir / "model.safetensors.index.json").write_text(
            json.dumps(
                {
                    "weight_map": {
                        "layer.0.weight": "model-00001-of-00002.safetensors",
                        "layer.1.weight": "model-00002-of-00002.safetensors",
                    }
                }
            )
        )
        (snapshot_dir / "tokenizer.json").write_text("{}")

        valid, reason = cache_manager.check_cache_at_location(model_dir)
        assert valid is False
        assert "Missing shard files" in reason

    def test_validate_cache_custom_valid(self, cache_manager, temp_cache_dir):
        """Test validate_cache returns True for valid custom cache."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create complete cache
        (snapshot_dir / "config.json").write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )
        (snapshot_dir / "model.safetensors").write_text("dummy")
        (snapshot_dir / "tokenizer.json").write_text("{}")

        valid, reason = cache_manager.validate_cache()
        assert valid is True
        assert "Valid cache" in reason

    def test_validate_cache_custom_invalid(self, cache_manager, temp_cache_dir):
        """Test validate_cache returns False for invalid custom cache."""
        # Don't create any cache files
        valid, reason = cache_manager.validate_cache()
        assert valid is False
        assert "Cache directory not found" in reason

    def test_check_incomplete_downloads_none(self, cache_manager, temp_cache_dir):
        """Test incomplete downloads check returns False when none exist."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        blobs_dir = model_dir / "blobs"
        blobs_dir.mkdir(parents=True)

        has_incomplete, message = cache_manager.check_incomplete_downloads()
        assert has_incomplete is False
        assert "No incomplete downloads" in message

    def test_check_incomplete_downloads_found(self, cache_manager, temp_cache_dir):
        """Test incomplete downloads check returns True when files exist."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        blobs_dir = model_dir / "blobs"
        blobs_dir.mkdir(parents=True)

        # Create incomplete download
        incomplete_file = blobs_dir / "blob123.incomplete"
        incomplete_file.write_text("x" * 1024 * 1024)  # 1 MB

        has_incomplete, message = cache_manager.check_incomplete_downloads()
        assert has_incomplete is True
        assert "Found 1 incomplete download" in message
        assert "1.0 MB" in message

    def test_cleanup_incomplete_downloads_none(self, cache_manager, temp_cache_dir):
        """Test cleanup returns 0 when no incomplete downloads exist."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        blobs_dir = model_dir / "blobs"
        blobs_dir.mkdir(parents=True)

        count, files = cache_manager.cleanup_incomplete_downloads()
        assert count == 0
        assert files == []

    def test_cleanup_incomplete_downloads_success(self, cache_manager, temp_cache_dir):
        """Test cleanup successfully removes incomplete downloads."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        blobs_dir = model_dir / "blobs"
        blobs_dir.mkdir(parents=True)

        # Create incomplete downloads
        incomplete1 = blobs_dir / "blob123.incomplete"
        incomplete2 = blobs_dir / "blob456.incomplete"
        incomplete1.write_text("x" * 1024 * 1024)  # 1 MB
        incomplete2.write_text("x" * 2 * 1024 * 1024)  # 2 MB

        count, files = cache_manager.cleanup_incomplete_downloads()
        assert count == 2
        assert len(files) == 2
        assert not incomplete1.exists()
        assert not incomplete2.exists()

    def test_is_cached_true(self, cache_manager, temp_cache_dir):
        """Test is_cached returns True for valid cache."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create complete cache
        (snapshot_dir / "config.json").write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )
        (snapshot_dir / "model.safetensors").write_text("dummy")
        (snapshot_dir / "tokenizer.json").write_text("{}")

        assert cache_manager.is_cached() is True

    def test_is_cached_false(self, cache_manager):
        """Test is_cached returns False for invalid cache."""
        assert cache_manager.is_cached() is False

    def test_find_local_model_dir_valid(self, cache_manager, temp_cache_dir):
        """Test find_local_model_dir returns snapshot path for valid cache."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create complete cache
        (snapshot_dir / "config.json").write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )
        (snapshot_dir / "model.safetensors").write_text("dummy")
        (snapshot_dir / "tokenizer.json").write_text("{}")

        local_dir = cache_manager.find_local_model_dir()
        assert local_dir == snapshot_dir

    def test_find_local_model_dir_invalid(self, cache_manager):
        """Test find_local_model_dir returns None for invalid cache."""
        local_dir = cache_manager.find_local_model_dir()
        assert local_dir is None

    def test_find_local_model_dir_multiple_snapshots(
        self, cache_manager, temp_cache_dir
    ):
        """Test find_local_model_dir returns latest snapshot when multiple exist."""
        import time

        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        snapshot1_dir = model_dir / "snapshots" / "abc123"
        snapshot2_dir = model_dir / "snapshots" / "def456"

        # Create first snapshot
        snapshot1_dir.mkdir(parents=True)
        (snapshot1_dir / "config.json").write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )
        (snapshot1_dir / "model.safetensors").write_text("dummy")
        (snapshot1_dir / "tokenizer.json").write_text("{}")

        time.sleep(0.1)  # Ensure different modification time

        # Create second snapshot (newer)
        snapshot2_dir.mkdir(parents=True)
        (snapshot2_dir / "config.json").write_text(
            json.dumps({"model_type": "bert", "architectures": ["BertModel"]})
        )
        (snapshot2_dir / "model.safetensors").write_text("dummy")
        (snapshot2_dir / "tokenizer.json").write_text("{}")

        local_dir = cache_manager.find_local_model_dir()
        assert local_dir == snapshot2_dir

    def test_ensure_split_cache_symlink_not_trust_remote(
        self, cache_manager, temp_cache_dir
    ):
        """Test ensure_split_cache_symlink returns False for non-trust_remote_code model."""
        # Basic model without trust_remote_code
        result = cache_manager.ensure_split_cache_symlink()
        assert result is False

    def test_ensure_split_cache_symlink_not_split_cache(
        self, temp_cache_dir, model_config_trust_remote
    ):
        """Test ensure_split_cache_symlink returns False when not split cache scenario."""
        manager = ModelCacheManager(
            model_name="custom/model",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: model_config_trust_remote,
        )

        # Create cache but not in split scenario
        model_dir = temp_cache_dir / "models--custom--model"
        snapshot_dir = model_dir / "snapshots" / "abc123"
        snapshot_dir.mkdir(parents=True)

        # Create complete cache in custom location (not split)
        (snapshot_dir / "config.json").write_text(
            json.dumps(
                {
                    "model_type": "custom",
                    "architectures": ["CustomModel"],
                    "trust_remote_code": True,
                }
            )
        )
        (snapshot_dir / "model.safetensors").write_text("dummy")
        (snapshot_dir / "tokenizer.json").write_text("{}")

        result = manager.ensure_split_cache_symlink()
        assert result is False

    def test_validate_cache_split_cache_scenario(
        self, temp_cache_dir, model_config_trust_remote
    ):
        """Test validate_cache detects valid split cache scenario."""
        manager = ModelCacheManager(
            model_name="custom/model",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: model_config_trust_remote,
        )

        # Create custom cache with config
        custom_dir = temp_cache_dir / "models--custom--model"
        custom_snapshot = custom_dir / "snapshots" / "abc123"
        custom_snapshot.mkdir(parents=True)
        (custom_snapshot / "config.json").write_text(
            json.dumps(
                {
                    "model_type": "custom",
                    "architectures": ["CustomModel"],
                    "trust_remote_code": True,
                }
            )
        )
        (custom_snapshot / "tokenizer.json").write_text("{}")

        # Create default cache with weights
        default_dir = (
            Path.home() / ".cache" / "huggingface" / "hub" / "models--custom--model"
        )
        default_snapshot = default_dir / "snapshots" / "abc123"
        default_snapshot.mkdir(parents=True, exist_ok=True)
        (default_snapshot / "model.safetensors").write_text("dummy")

        try:
            valid, reason = manager.validate_cache()
            assert valid is True
            assert "split cache" in reason.lower()
        finally:
            # Cleanup default cache
            if default_dir.exists():
                import shutil

                shutil.rmtree(default_dir)

    def test_empty_cache_directory(self, cache_manager, temp_cache_dir):
        """Test behavior with empty cache directory."""
        model_dir = temp_cache_dir / "models--BAAI--bge-m3"
        model_dir.mkdir()

        valid, reason = cache_manager.check_cache_at_location(model_dir)
        assert valid is False
        assert "No snapshots found" in reason
