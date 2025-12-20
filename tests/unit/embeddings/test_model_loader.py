"""Tests for ModelLoader."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from embeddings.model_cache import ModelCacheManager
from embeddings.model_loader import ModelLoader


class TestModelLoader:
    """Test suite for ModelLoader class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def model_config_basic(self):
        """Basic model config."""
        return {
            "model_type": "bert",
            "architectures": ["BertModel"],
            "dimension": 768,
        }

    @pytest.fixture
    def cache_manager(self, temp_cache_dir, model_config_basic):
        """Create a mock cache manager for testing."""
        return ModelCacheManager(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: model_config_basic,
        )

    @pytest.fixture
    def model_loader(self, temp_cache_dir, cache_manager, model_config_basic):
        """Create a basic model loader for testing."""
        return ModelLoader(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            device="auto",
            cache_manager=cache_manager,
            model_config_getter=lambda: model_config_basic,
        )

    def test_initialization(self, temp_cache_dir, cache_manager, model_config_basic):
        """Test model loader initialization."""
        loader = ModelLoader(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            device="cuda",
            cache_manager=cache_manager,
            model_config_getter=lambda: model_config_basic,
        )
        assert loader.model_name == "BAAI/bge-m3"
        assert loader.cache_dir == str(temp_cache_dir)
        assert loader.device == "cuda"
        assert loader._cache_manager == cache_manager

    @patch("embeddings.model_loader.torch")
    def test_log_gpu_memory_no_cuda(self, mock_torch, model_loader):
        """Test GPU memory logging when CUDA not available."""
        mock_torch.cuda.is_available.return_value = False
        # Should not raise exception
        model_loader.log_gpu_memory("TEST_STAGE")

    @patch("embeddings.model_loader.torch")
    def test_log_gpu_memory_with_cuda(self, mock_torch, model_loader, caplog):
        """Test GPU memory logging with CUDA available."""
        # Set caplog to capture INFO level
        caplog.set_level("INFO", logger="embeddings.model_loader")

        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.memory_allocated.return_value = 1024**3  # 1 GB
        mock_torch.cuda.memory_reserved.return_value = 2 * 1024**3  # 2 GB

        # Mock device properties
        mock_props = Mock()
        mock_props.total_memory = 8 * 1024**3  # 8 GB
        mock_torch.cuda.get_device_properties.return_value = mock_props

        model_loader.log_gpu_memory("TEST_STAGE")

        # Check that logging occurred
        assert "TEST_STAGE" in caplog.text
        assert "Allocated=1.00GB" in caplog.text

    @patch("embeddings.model_loader.torch", None)
    def test_get_torch_dtype_no_torch(self, model_loader):
        """Test dtype selection when torch not available."""
        dtype = model_loader.get_torch_dtype()
        assert dtype is None

    @patch("embeddings.model_loader.torch")
    @patch("embeddings.model_loader._get_config_via_service_locator")
    def test_get_torch_dtype_cpu(self, mock_config_func, mock_torch, model_loader):
        """Test dtype selection for CPU."""
        mock_torch.cuda.is_available.return_value = False
        dtype = model_loader.get_torch_dtype()
        assert dtype is None

    @patch("embeddings.model_loader.torch")
    @patch("embeddings.model_loader._get_config_via_service_locator")
    def test_get_torch_dtype_fp16_disabled(
        self, mock_config_func, mock_torch, model_loader
    ):
        """Test dtype selection when fp16 disabled."""
        mock_torch.cuda.is_available.return_value = True

        # Mock config with fp16 disabled
        mock_config = Mock()
        mock_config.performance.enable_fp16 = False
        mock_config_func.return_value = mock_config

        dtype = model_loader.get_torch_dtype()
        assert dtype is None

    @patch("embeddings.model_loader.torch")
    @patch("embeddings.model_loader._get_config_via_service_locator")
    def test_get_torch_dtype_fp16_enabled(
        self, mock_config_func, mock_torch, model_loader
    ):
        """Test dtype selection when fp16 enabled."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.float16 = "mock_fp16"
        mock_torch.cuda.is_bf16_supported.return_value = False

        # Mock config with fp16 enabled, bf16 not preferred
        mock_config = Mock()
        mock_config.performance.enable_fp16 = True
        mock_config.performance.prefer_bf16 = False
        mock_config_func.return_value = mock_config

        dtype = model_loader.get_torch_dtype()
        assert dtype == "mock_fp16"

    @patch("embeddings.model_loader.torch")
    @patch("embeddings.model_loader._get_config_via_service_locator")
    def test_get_torch_dtype_bf16_supported(
        self, mock_config_func, mock_torch, model_loader
    ):
        """Test dtype selection when bf16 supported."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.bfloat16 = "mock_bf16"
        mock_torch.cuda.is_bf16_supported.return_value = True

        # Mock config with fp16 enabled and bf16 preferred
        mock_config = Mock()
        mock_config.performance.enable_fp16 = True
        mock_config.performance.prefer_bf16 = True
        mock_config_func.return_value = mock_config

        dtype = model_loader.get_torch_dtype()
        assert dtype == "mock_bf16"

    @patch("embeddings.model_loader.torch", None)
    def test_resolve_device_no_torch(self, model_loader):
        """Test device resolution when torch not available."""
        device = model_loader.resolve_device("auto")
        assert device == "cpu"

    @patch("embeddings.model_loader.torch")
    def test_resolve_device_auto_cuda(self, mock_torch, model_loader):
        """Test device resolution auto selects CUDA."""
        mock_torch.cuda.is_available.return_value = True
        device = model_loader.resolve_device("auto")
        assert device == "cuda"

    @patch("embeddings.model_loader.torch")
    def test_resolve_device_auto_mps(self, mock_torch, model_loader):
        """Test device resolution auto selects MPS."""
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True
        device = model_loader.resolve_device("auto")
        assert device == "mps"

    @patch("embeddings.model_loader.torch")
    def test_resolve_device_auto_cpu(self, mock_torch, model_loader):
        """Test device resolution auto selects CPU."""
        mock_torch.cuda.is_available.return_value = False
        # Mock MPS not available
        try:
            mock_torch.backends.mps.is_available.return_value = False
        except AttributeError:
            pass
        device = model_loader.resolve_device("auto")
        assert device == "cpu"

    @patch("embeddings.model_loader.torch")
    def test_resolve_device_explicit_cuda_available(self, mock_torch, model_loader):
        """Test explicit CUDA device when available."""
        mock_torch.cuda.is_available.return_value = True
        device = model_loader.resolve_device("cuda")
        assert device == "cuda"

    @patch("embeddings.model_loader.torch")
    def test_resolve_device_explicit_cuda_unavailable(self, mock_torch, model_loader):
        """Test explicit CUDA device falls back to CPU when unavailable."""
        mock_torch.cuda.is_available.return_value = False
        device = model_loader.resolve_device("cuda")
        assert device == "cpu"

    @patch("embeddings.model_loader.torch")
    def test_resolve_device_explicit_mps_available(self, mock_torch, model_loader):
        """Test explicit MPS device when available."""
        mock_torch.backends.mps.is_available.return_value = True
        device = model_loader.resolve_device("mps")
        assert device == "mps"

    @patch("embeddings.model_loader.torch")
    def test_resolve_device_explicit_mps_unavailable(self, mock_torch, model_loader):
        """Test explicit MPS device falls back to CPU when unavailable."""
        # Mock MPS not available
        try:
            mock_torch.backends.mps.is_available.return_value = False
        except AttributeError:
            pass
        device = model_loader.resolve_device("mps")
        assert device == "cpu"

    @patch("embeddings.model_loader.SentenceTransformer", None)
    def test_load_no_sentence_transformer(self, model_loader):
        """Test load raises ImportError when sentence-transformers not installed."""
        with pytest.raises(ImportError, match="sentence-transformers not found"):
            model_loader.load()

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.model_loader.torch")
    def test_load_corrupted_cache_cleanup_success(
        self, mock_torch, mock_st, model_loader, temp_cache_dir, caplog
    ):
        """Test load with corrupted cache that's fixed by cleanup."""
        # Set caplog to capture INFO level
        caplog.set_level("INFO", logger="embeddings.model_loader")

        # Setup cache manager to report corrupted cache, then valid after cleanup
        model_loader._cache_manager.validate_cache = Mock(
            side_effect=[
                (False, "Incomplete downloads detected"),  # First call
                (True, "Valid after cleanup"),  # Second call after cleanup
            ]
        )
        model_loader._cache_manager.get_model_cache_path = Mock(
            return_value=temp_cache_dir / "models--BAAI--bge-m3"
        )
        model_loader._cache_manager.check_incomplete_downloads = Mock(
            return_value=(True, "Found 1 incomplete download")
        )
        model_loader._cache_manager.cleanup_incomplete_downloads = Mock(
            return_value=(1, ["blob123.incomplete"])
        )
        model_loader._cache_manager.find_local_model_dir = Mock(
            return_value=temp_cache_dir
            / "models--BAAI--bge-m3"
            / "snapshots"
            / "abc123"
        )
        model_loader._cache_manager.ensure_split_cache_symlink = Mock(return_value=True)

        # Create cache directory
        (temp_cache_dir / "models--BAAI--bge-m3").mkdir(parents=True, exist_ok=True)

        # Mock torch - disable CUDA and MPS for consistent device resolution
        mock_torch.cuda.is_available.return_value = False
        # Mock MPS not available
        try:
            mock_torch.backends.mps.is_available.return_value = False
        except AttributeError:
            pass

        # Mock SentenceTransformer
        mock_model = Mock()
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        model, device = model_loader.load()

        assert model == mock_model
        assert device == "cpu"
        assert "[CLEANUP SUCCESS]" in caplog.text
        assert "[RECOVERY SUCCESS]" in caplog.text

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.model_loader.torch")
    @patch("embeddings.model_loader.shutil")
    def test_load_corrupted_cache_delete_and_redownload(
        self, mock_shutil, mock_torch, mock_st, model_loader, temp_cache_dir, caplog
    ):
        """Test load with corrupted cache that requires deletion and redownload."""
        # Setup cache manager to report corrupted cache
        cache_path = temp_cache_dir / "models--BAAI--bge-m3"
        model_loader._cache_manager.validate_cache = Mock(
            return_value=(False, "Missing config.json")
        )
        model_loader._cache_manager.get_model_cache_path = Mock(return_value=cache_path)
        model_loader._cache_manager.check_incomplete_downloads = Mock(
            return_value=(False, "No incomplete downloads")
        )
        model_loader._cache_manager.ensure_split_cache_symlink = Mock(return_value=True)

        # Create cache directory
        cache_path.mkdir(parents=True, exist_ok=True)

        # Mock torch - disable CUDA and MPS for consistent device resolution
        mock_torch.cuda.is_available.return_value = False
        # Mock MPS not available
        try:
            mock_torch.backends.mps.is_available.return_value = False
        except AttributeError:
            pass

        # Mock SentenceTransformer
        mock_model = Mock()
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        model, device = model_loader.load()

        assert model == mock_model
        assert device == "cpu"
        # Verify cache was deleted
        mock_shutil.rmtree.assert_called_once_with(cache_path)
        assert "[CACHE CORRUPTED]" in caplog.text
        assert "[AUTO-RECOVERY]" in caplog.text

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.model_loader.torch")
    def test_load_valid_cache(
        self, mock_torch, mock_st, model_loader, temp_cache_dir, caplog
    ):
        """Test load with valid cache."""
        # Set caplog to capture INFO level
        caplog.set_level("INFO", logger="embeddings.model_loader")

        # Setup cache manager to report valid cache
        snapshot_path = temp_cache_dir / "models--BAAI--bge-m3" / "snapshots" / "abc123"
        model_loader._cache_manager.validate_cache = Mock(
            return_value=(True, "Valid cache")
        )
        model_loader._cache_manager.find_local_model_dir = Mock(
            return_value=snapshot_path
        )
        model_loader._cache_manager.ensure_split_cache_symlink = Mock(return_value=True)

        # Mock torch - disable CUDA and MPS for consistent device resolution
        mock_torch.cuda.is_available.return_value = False
        # Mock MPS not available
        try:
            mock_torch.backends.mps.is_available.return_value = False
        except AttributeError:
            pass

        # Mock SentenceTransformer
        mock_model = Mock()
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        model, device = model_loader.load()

        assert model == mock_model
        assert device == "cpu"
        assert "[VALIDATED CACHE]" in caplog.text

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.model_loader.torch")
    def test_load_with_mrl_truncate_dim(
        self, mock_torch, mock_st, model_loader, caplog
    ):
        """Test load with Matryoshka MRL truncate_dim support."""
        # Set caplog to capture INFO level
        caplog.set_level("INFO", logger="embeddings.model_loader")

        # Setup model config with truncate_dim
        model_loader._get_model_config = lambda: {
            "dimension": 2560,
            "truncate_dim": 1024,
        }

        # Setup cache manager
        model_loader._cache_manager.validate_cache = Mock(
            return_value=(True, "Valid cache")
        )
        model_loader._cache_manager.find_local_model_dir = Mock(return_value=None)
        model_loader._cache_manager.ensure_split_cache_symlink = Mock(return_value=True)

        # Mock torch - disable CUDA and MPS for consistent device resolution
        mock_torch.cuda.is_available.return_value = False
        # Mock MPS not available
        try:
            mock_torch.backends.mps.is_available.return_value = False
        except AttributeError:
            pass

        # Mock SentenceTransformer
        mock_model = Mock()
        mock_model.device = "cpu"
        mock_st.return_value = mock_model

        model, device = model_loader.load()

        assert model == mock_model
        assert (
            "Matryoshka MRL enabled: truncating output to 1024 dimensions"
            in caplog.text
        )
        # Verify truncate_dim was passed to constructor
        mock_st.assert_called_once()
        call_kwargs = mock_st.call_args[1]
        assert call_kwargs["truncate_dim"] == 1024

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.model_loader.torch")
    def test_load_fallback_on_cache_load_failure(
        self, mock_torch, mock_st, model_loader, temp_cache_dir, caplog
    ):
        """Test load falls back to network download when cache load fails."""
        # Set caplog to capture INFO level
        caplog.set_level("INFO", logger="embeddings.model_loader")

        # Setup cache manager to report valid cache
        snapshot_path = temp_cache_dir / "models--BAAI--bge-m3" / "snapshots" / "abc123"
        model_loader._cache_manager.validate_cache = Mock(
            return_value=(True, "Valid cache")
        )
        model_loader._cache_manager.find_local_model_dir = Mock(
            return_value=snapshot_path
        )
        model_loader._cache_manager.ensure_split_cache_symlink = Mock(return_value=True)

        # Mock torch - disable CUDA and MPS for consistent device resolution
        mock_torch.cuda.is_available.return_value = False
        # Mock MPS not available
        try:
            mock_torch.backends.mps.is_available.return_value = False
        except AttributeError:
            pass

        # Mock SentenceTransformer to fail on first call, succeed on second
        mock_model = Mock()
        mock_model.device = "cpu"
        mock_st.side_effect = [
            RuntimeError("Cache load failed"),
            mock_model,  # Fallback succeeds
        ]

        model, device = model_loader.load()

        assert model == mock_model
        assert device == "cpu"
        assert "[CACHE LOAD FAILED]" in caplog.text
        assert "[FALLBACK SUCCESS]" in caplog.text

    @patch("embeddings.model_loader.SentenceTransformer")
    def test_load_raises_on_all_failures(self, mock_st, model_loader):
        """Test load raises RuntimeError when all recovery attempts fail."""
        # Setup cache manager to report invalid cache
        model_loader._cache_manager.validate_cache = Mock(
            return_value=(False, "Cache not found")
        )
        model_loader._cache_manager.get_model_cache_path = Mock(return_value=None)

        # Mock SentenceTransformer to always fail
        mock_st.side_effect = RuntimeError("Network download failed")

        with pytest.raises(RuntimeError, match="MODEL DOWNLOAD FAILED"):
            model_loader.load()

    def test_model_vram_usage_property(self, model_loader):
        """Test model_vram_usage property."""
        model_loader._model_vram_usage["test-model"] = 123.4
        assert model_loader.model_vram_usage == {"test-model": 123.4}
