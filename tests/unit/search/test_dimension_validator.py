"""Unit tests for dimension validation utilities."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from search.dimension_validator import (
    DimensionMismatchError,
    read_index_metadata,
    validate_embedder_index_compatibility,
)


class TestReadIndexMetadata:
    """Tests for read_index_metadata function."""

    def test_reads_project_info_successfully(self):
        """Test reading valid project_info.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_info = {
                "embedding_model": "BAAI/bge-m3",
                "model_dimension": 1024,
            }
            with open(project_dir / "project_info.json", "w") as f:
                json.dump(project_info, f)

            result = read_index_metadata(project_dir)

            assert result["embedding_model"] == "BAAI/bge-m3"
            assert result["model_dimension"] == 1024

    def test_returns_none_when_file_missing(self):
        """Test returns None when project_info.json doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = read_index_metadata(Path(tmpdir))
            assert result is None

    def test_handles_index_subdirectory(self):
        """Test reading from parent when storage_dir is 'index' subdir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            index_dir = project_dir / "index"
            index_dir.mkdir()

            project_info = {
                "embedding_model": "BAAI/bge-m3",
                "model_dimension": 1024,
            }
            with open(project_dir / "project_info.json", "w") as f:
                json.dump(project_info, f)

            result = read_index_metadata(index_dir)

            assert result["embedding_model"] == "BAAI/bge-m3"

    def test_handles_malformed_json(self):
        """Test graceful handling of malformed JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            with open(project_dir / "project_info.json", "w") as f:
                f.write("{ invalid json")

            result = read_index_metadata(project_dir)
            assert result is None

    def test_handles_missing_fields(self):
        """Test handling of project_info with missing fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_info = {"other_field": "value"}
            with open(project_dir / "project_info.json", "w") as f:
                json.dump(project_info, f)

            result = read_index_metadata(project_dir)

            assert result["embedding_model"] is None
            assert result["model_dimension"] is None


class TestValidateEmbedderIndexCompatibility:
    """Tests for validate_embedder_index_compatibility function."""

    def test_compatible_dimensions_pass(self):
        """Test that matching dimensions return True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_info = {
                "embedding_model": "BAAI/bge-m3",
                "model_dimension": 1024,
            }
            with open(project_dir / "project_info.json", "w") as f:
                json.dump(project_info, f)

            embedder = Mock()
            embedder.get_model_info.return_value = {"embedding_dimension": 1024}
            embedder.model_name = "BAAI/bge-m3"

            is_valid, error = validate_embedder_index_compatibility(
                embedder, project_dir, raise_on_mismatch=False
            )

            assert is_valid is True
            assert error is None

    def test_incompatible_dimensions_detected(self):
        """Test that mismatched dimensions return False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_info = {
                "embedding_model": "BAAI/bge-m3",
                "model_dimension": 1024,
            }
            with open(project_dir / "project_info.json", "w") as f:
                json.dump(project_info, f)

            embedder = Mock()
            embedder.get_model_info.return_value = {"embedding_dimension": 768}
            embedder.model_name = "Alibaba-NLP/gte-modernbert-base"

            is_valid, error = validate_embedder_index_compatibility(
                embedder, project_dir, raise_on_mismatch=False
            )

            assert is_valid is False
            assert "DIMENSION MISMATCH" in error
            assert "768d" in error
            assert "1024d" in error

    def test_raises_on_mismatch_when_enabled(self):
        """Test that DimensionMismatchError is raised when enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_info = {
                "embedding_model": "BAAI/bge-m3",
                "model_dimension": 1024,
            }
            with open(project_dir / "project_info.json", "w") as f:
                json.dump(project_info, f)

            embedder = Mock()
            embedder.get_model_info.return_value = {"embedding_dimension": 768}
            embedder.model_name = "Alibaba-NLP/gte-modernbert-base"

            with pytest.raises(DimensionMismatchError) as exc_info:
                validate_embedder_index_compatibility(
                    embedder, project_dir, raise_on_mismatch=True
                )

            assert exc_info.value.embedder_dim == 768
            assert exc_info.value.index_dim == 1024
            assert exc_info.value.embedder_model == "Alibaba-NLP/gte-modernbert-base"
            assert exc_info.value.index_model == "BAAI/bge-m3"

    def test_no_existing_index_passes(self):
        """Test that missing index returns True (new index will be created)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embedder = Mock()
            embedder.get_model_info.return_value = {"embedding_dimension": 768}
            embedder.model_name = "test-model"

            is_valid, error = validate_embedder_index_compatibility(
                embedder, Path(tmpdir), raise_on_mismatch=True
            )

            assert is_valid is True
            assert error is None

    def test_none_embedder_passes(self):
        """Test that None embedder returns True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, error = validate_embedder_index_compatibility(
                None, Path(tmpdir), raise_on_mismatch=True
            )

            assert is_valid is True
            assert error is None

    def test_embedder_without_dimension_passes(self):
        """Test that embedder without dimension info returns True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_info = {
                "embedding_model": "BAAI/bge-m3",
                "model_dimension": 1024,
            }
            with open(project_dir / "project_info.json", "w") as f:
                json.dump(project_info, f)

            embedder = Mock()
            embedder.get_model_info.return_value = {}  # No dimension key
            embedder.model_name = "test-model"

            is_valid, error = validate_embedder_index_compatibility(
                embedder, project_dir, raise_on_mismatch=True
            )

            assert is_valid is True
            assert error is None

    def test_embedder_get_model_info_raises_exception(self):
        """Test graceful handling when get_model_info raises exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            embedder = Mock()
            embedder.get_model_info.side_effect = Exception("Model info error")

            is_valid, error = validate_embedder_index_compatibility(
                embedder, Path(tmpdir), raise_on_mismatch=True
            )

            assert is_valid is True
            assert error is None

    def test_index_without_dimension_passes(self):
        """Test that index without dimension info returns True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_info = {
                "embedding_model": "BAAI/bge-m3"
                # No model_dimension field
            }
            with open(project_dir / "project_info.json", "w") as f:
                json.dump(project_info, f)

            embedder = Mock()
            embedder.get_model_info.return_value = {"embedding_dimension": 768}
            embedder.model_name = "test-model"

            is_valid, error = validate_embedder_index_compatibility(
                embedder, project_dir, raise_on_mismatch=True
            )

            assert is_valid is True
            assert error is None

    def test_different_models_same_dimension_passes(self):
        """Test that different models with same dimension pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_info = {
                "embedding_model": "BAAI/bge-m3",
                "model_dimension": 1024,
            }
            with open(project_dir / "project_info.json", "w") as f:
                json.dump(project_info, f)

            embedder = Mock()
            embedder.get_model_info.return_value = {"embedding_dimension": 1024}
            embedder.model_name = "Qwen/Qwen3-Embedding-0.6B"  # Different model

            is_valid, error = validate_embedder_index_compatibility(
                embedder, project_dir, raise_on_mismatch=False
            )

            assert is_valid is True
            assert error is None


class TestDimensionMismatchErrorAttributes:
    """Tests for DimensionMismatchError exception attributes."""

    def test_error_attributes_stored_correctly(self):
        """Test that error attributes are stored correctly."""
        error = DimensionMismatchError(
            "Test error",
            embedder_dim=768,
            index_dim=1024,
            embedder_model="model-a",
            index_model="model-b",
        )

        assert error.embedder_dim == 768
        assert error.index_dim == 1024
        assert error.embedder_model == "model-a"
        assert error.index_model == "model-b"
        assert str(error) == "Test error"

    def test_error_with_none_attributes(self):
        """Test error with None attributes."""
        error = DimensionMismatchError("Test error")

        assert error.embedder_dim is None
        assert error.index_dim is None
        assert error.embedder_model is None
        assert error.index_model is None

    def test_error_is_configuration_error_subclass(self):
        """Test that DimensionMismatchError is a ConfigurationError."""
        from search.exceptions import ConfigurationError

        error = DimensionMismatchError("Test")
        assert isinstance(error, ConfigurationError)
