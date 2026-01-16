"""Unit tests for VRAM tier management and adaptive model selection."""

from unittest.mock import MagicMock, patch

import pytest

from search.vram_manager import VRAM_TIERS, VRAMTierManager


class TestVRAMTiers:
    """Test VRAM tier definitions."""

    def test_tier_count(self):
        """Test that we have 4 tiers defined."""
        assert len(VRAM_TIERS) == 4

    def test_tier_names(self):
        """Test tier names are correct."""
        names = [tier.name for tier in VRAM_TIERS]
        assert names == ["minimal", "laptop", "desktop", "workstation"]

    def test_tier_ranges_no_gaps(self):
        """Test that tier ranges cover all VRAM values without gaps."""
        # Sort by min_vram_gb
        sorted_tiers = sorted(VRAM_TIERS, key=lambda t: t.min_vram_gb)

        # First tier should start at 0
        assert sorted_tiers[0].min_vram_gb == 0

        # Check for gaps between tiers
        for i in range(len(sorted_tiers) - 1):
            current_max = sorted_tiers[i].max_vram_gb
            next_min = sorted_tiers[i + 1].min_vram_gb
            assert current_max == next_min, (
                f"Gap between {sorted_tiers[i].name} and {sorted_tiers[i + 1].name}"
            )

    def test_recommended_models(self):
        """Test that each tier has a recommended model."""
        for tier in VRAM_TIERS:
            # Models can be BGE-M3 or Qwen variants
            assert tier.recommended_model in [
                "BAAI/bge-m3",
                "Qwen/Qwen3-Embedding-0.6B",
                "Qwen/Qwen3-Embedding-4B",
            ]
            assert len(tier.recommended_model) > 5

    def test_feature_enablement_progression(self):
        """Test that features are enabled progressively with higher tiers."""
        minimal = VRAM_TIERS[0]
        laptop = VRAM_TIERS[1]
        desktop = VRAM_TIERS[2]
        workstation = VRAM_TIERS[3]

        # Minimal tier has everything disabled
        assert minimal.multi_model_enabled is False
        assert minimal.neural_reranking_enabled is False
        assert minimal.multi_model_pool is None
        assert minimal.reranker_model is None

        # Laptop tier: lightweight multi-model for 8GB GPUs
        assert laptop.multi_model_enabled is True  # Enabled with lightweight pool
        assert laptop.neural_reranking_enabled is True  # Lightweight reranker
        assert laptop.multi_model_pool == "lightweight-speed"  # Default speed preset
        assert laptop.reranker_model == "lightweight"  # gte-reranker-modernbert

        # Higher tiers enable full multi-model pool
        assert desktop.multi_model_enabled is True
        assert desktop.neural_reranking_enabled is True
        assert desktop.multi_model_pool == "full"
        assert desktop.reranker_model == "full"
        assert workstation.multi_model_enabled is True
        assert workstation.neural_reranking_enabled is True
        assert workstation.multi_model_pool == "full"
        assert workstation.reranker_model == "full"


class TestVRAMTierManager:
    """Test VRAMTierManager functionality."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = VRAMTierManager()
        assert manager._detected_tier is None

    def test_detect_tier_minimal(self):
        """Test tier detection for minimal VRAM (< 6GB)."""
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                # Mock GPU with 4GB VRAM
                mock_props = MagicMock()
                mock_props.total_memory = 4 * (1024**3)  # 4GB
                mock_get_props.return_value = mock_props

                manager = VRAMTierManager()
                tier = manager.detect_tier()

                assert tier.name == "minimal"
                assert tier.recommended_model == "BAAI/bge-m3"
                assert tier.multi_model_enabled is False
                assert tier.neural_reranking_enabled is False

    def test_detect_tier_laptop(self):
        """Test tier detection for laptop VRAM (6-10GB)."""
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                # Mock GPU with 8GB VRAM (RTX 4060)
                mock_props = MagicMock()
                mock_props.total_memory = 8 * (1024**3)  # 8GB
                mock_get_props.return_value = mock_props

                manager = VRAMTierManager()
                tier = manager.detect_tier()

                assert tier.name == "laptop"
                assert tier.recommended_model == "BAAI/bge-m3"
                assert tier.multi_model_enabled is True  # Enabled with lightweight pool
                assert tier.neural_reranking_enabled is True
                assert tier.multi_model_pool == "lightweight-speed"  # Default preset
                assert tier.reranker_model == "lightweight"

    def test_detect_tier_desktop(self):
        """Test tier detection for desktop VRAM (10-18GB)."""
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                # Mock GPU with 12GB VRAM (RTX 3060)
                mock_props = MagicMock()
                mock_props.total_memory = 12 * (1024**3)  # 12GB
                mock_get_props.return_value = mock_props

                manager = VRAMTierManager()
                tier = manager.detect_tier()

                assert tier.name == "desktop"
                assert tier.recommended_model == "Qwen/Qwen3-Embedding-0.6B"
                assert tier.multi_model_enabled is True
                assert tier.neural_reranking_enabled is True

    def test_detect_tier_workstation(self):
        """Test tier detection for workstation VRAM (18+GB)."""
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                # Mock GPU with 24GB VRAM (RTX 4090)
                mock_props = MagicMock()
                mock_props.total_memory = 24 * (1024**3)  # 24GB
                mock_get_props.return_value = mock_props

                manager = VRAMTierManager()
                tier = manager.detect_tier()

                assert tier.name == "workstation"
                assert tier.recommended_model == "Qwen/Qwen3-Embedding-0.6B"
                assert tier.multi_model_enabled is True
                assert tier.neural_reranking_enabled is True

    def test_detect_tier_caching(self):
        """Test that tier detection is cached."""
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                mock_props = MagicMock()
                mock_props.total_memory = 12 * (1024**3)
                mock_get_props.return_value = mock_props

                manager = VRAMTierManager()

                # First call should detect
                tier1 = manager.detect_tier()
                assert mock_get_props.call_count == 1

                # Second call should use cache
                tier2 = manager.detect_tier()
                assert mock_get_props.call_count == 1  # No additional calls

                # Results should be identical
                assert tier1 == tier2

    def test_no_cuda_available(self):
        """Test behavior when CUDA is not available."""
        with patch("torch.cuda.is_available", return_value=False):
            manager = VRAMTierManager()
            tier = manager.detect_tier()

            # Should fall back to minimal tier
            assert tier.name == "minimal"
            assert tier.recommended_model == "BAAI/bge-m3"

    def test_torch_not_available(self):
        """Test behavior when PyTorch is not installed."""
        # Mock import error for torch
        with patch.dict("sys.modules", {"torch": None}):
            manager = VRAMTierManager()
            tier = manager.detect_tier()

            # Should fall back to minimal tier
            assert tier.name == "minimal"

    def test_get_model_for_tier(self):
        """Test getting model for specific tier."""
        manager = VRAMTierManager()

        assert manager.get_model_for_tier("minimal") == "BAAI/bge-m3"
        assert manager.get_model_for_tier("laptop") == "BAAI/bge-m3"
        assert manager.get_model_for_tier("desktop") == "Qwen/Qwen3-Embedding-0.6B"
        assert manager.get_model_for_tier("workstation") == "Qwen/Qwen3-Embedding-0.6B"

    def test_get_model_for_invalid_tier(self):
        """Test getting model for invalid tier name."""
        manager = VRAMTierManager()

        with pytest.raises(ValueError, match="Unknown tier"):
            manager.get_model_for_tier("invalid")

    def test_should_enable_multi_model(self):
        """Test multi-model enablement check."""
        # Mock laptop tier (multi-model enabled with lightweight pool)
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                mock_props = MagicMock()
                mock_props.total_memory = 8 * (1024**3)
                mock_get_props.return_value = mock_props

                manager = VRAMTierManager()
                assert (
                    manager.should_enable_multi_model() is True
                )  # Enabled with lightweight

        # Mock minimal tier (multi-model disabled)
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                mock_props = MagicMock()
                mock_props.total_memory = 4 * (1024**3)
                mock_get_props.return_value = mock_props

                manager2 = VRAMTierManager()
                assert manager2.should_enable_multi_model() is False

    def test_should_enable_neural_reranking(self):
        """Test neural reranking enablement check."""
        # Mock laptop tier (reranking enabled)
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                mock_props = MagicMock()
                mock_props.total_memory = 8 * (1024**3)
                mock_get_props.return_value = mock_props

                manager = VRAMTierManager()
                assert manager.should_enable_neural_reranking() is True

        # Mock minimal tier (reranking disabled)
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                mock_props = MagicMock()
                mock_props.total_memory = 4 * (1024**3)
                mock_get_props.return_value = mock_props

                manager2 = VRAMTierManager()
                assert manager2.should_enable_neural_reranking() is False

    def test_boundary_conditions(self):
        """Test tier detection at boundary VRAM values."""
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                mock_props = MagicMock()
                mock_get_props.return_value = mock_props

                # Test 6GB exactly (should be laptop, not minimal)
                mock_props.total_memory = 6 * (1024**3)
                manager1 = VRAMTierManager()
                assert manager1.detect_tier().name == "laptop"

                # Test 10GB exactly (should be desktop, not laptop)
                mock_props.total_memory = 10 * (1024**3)
                manager2 = VRAMTierManager()
                assert manager2.detect_tier().name == "desktop"

                # Test 18GB exactly (should be workstation, not desktop)
                mock_props.total_memory = 18 * (1024**3)
                manager3 = VRAMTierManager()
                assert manager3.detect_tier().name == "workstation"

    def test_realistic_gpu_vram(self):
        """Test with realistic GPU VRAM values."""
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.get_device_properties") as mock_get_props:
                mock_props = MagicMock()
                mock_get_props.return_value = mock_props

                # RTX 4060 (8GB)
                mock_props.total_memory = 8 * (1024**3)
                manager_4060 = VRAMTierManager()
                tier_4060 = manager_4060.detect_tier()
                assert tier_4060.name == "laptop"
                assert tier_4060.recommended_model == "BAAI/bge-m3"

                # RTX 3090 (24GB)
                mock_props.total_memory = 24 * (1024**3)
                manager_3090 = VRAMTierManager()
                tier_3090 = manager_3090.detect_tier()
                assert tier_3090.name == "workstation"
                assert tier_3090.recommended_model == "Qwen/Qwen3-Embedding-0.6B"

                # RTX 4090 (24GB)
                mock_props.total_memory = 24 * (1024**3)
                manager_4090 = VRAMTierManager()
                tier_4090 = manager_4090.detect_tier()
                assert tier_4090.name == "workstation"
                assert tier_4090.recommended_model == "Qwen/Qwen3-Embedding-0.6B"
