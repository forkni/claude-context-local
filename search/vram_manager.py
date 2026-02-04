"""VRAM tier management for adaptive model selection based on GPU capabilities."""

import logging
from dataclasses import dataclass
from typing import Optional


logger = logging.getLogger(__name__)


@dataclass
class VRAMTier:
    """VRAM tier configuration for automatic feature adaptation.

    Attributes:
        name: Tier name (minimal, laptop, desktop, workstation, laptop_multimodel)
        min_vram_gb: Minimum VRAM in GB for this tier (inclusive)
        max_vram_gb: Maximum VRAM in GB for this tier (exclusive)
        recommended_model: Full model name from MODEL_REGISTRY
        multi_model_enabled: Whether multi-model routing should be enabled
        neural_reranking_enabled: Whether neural reranking should be enabled
        multi_model_pool: Pool type for multi-model ("full", "lightweight-speed")
        reranker_model: Reranker type ("full", "lightweight")
    """

    name: str
    min_vram_gb: float
    max_vram_gb: float
    recommended_model: str
    multi_model_enabled: bool
    neural_reranking_enabled: bool
    multi_model_pool: Optional[str] = None  # "full" or "lightweight-speed"
    reranker_model: Optional[str] = None  # "full" or "lightweight"


# VRAM tier definitions based on GPU capabilities
# RTX 3060/4060 (8GB) → laptop tier → BGE-M3 with lightweight multi-model option
# RTX 3090 (24GB) → desktop tier    → Qwen3-0.6B (full multi-model pool)
# RTX 4090 (24GB) → workstation tier → Qwen3-0.6B (full multi-model pool)
VRAM_TIERS: list[VRAMTier] = [
    VRAMTier(
        name="minimal",
        min_vram_gb=0,
        max_vram_gb=6,
        recommended_model="BAAI/bge-m3",  # Smallest viable model (1.07GB)
        multi_model_enabled=False,  # Too little VRAM for multi-model
        neural_reranking_enabled=False,  # Disable to conserve VRAM
        multi_model_pool=None,  # Single-model only
        reranker_model=None,  # Reranking disabled
    ),
    VRAMTier(
        name="laptop",
        min_vram_gb=6,
        max_vram_gb=10,
        recommended_model="BAAI/bge-m3",  # Base model for 8GB GPUs
        multi_model_enabled=True,  # Enable with lightweight pool
        neural_reranking_enabled=True,  # Lightweight reranker (0.3GB)
        multi_model_pool="lightweight-speed",  # Default to speed preset (1.65GB total)
        reranker_model="lightweight",  # Use gte-reranker-modernbert-base
    ),
    VRAMTier(
        name="desktop",
        min_vram_gb=10,
        max_vram_gb=18,
        recommended_model="Qwen/Qwen3-Embedding-0.6B",  # Keep 0.6B for OOM prevention
        multi_model_enabled=True,
        neural_reranking_enabled=True,
        multi_model_pool="full",  # Full 3-model pool (6.8GB)
        reranker_model="full",  # Full bge-reranker-v2-m3 (1.5GB)
    ),
    VRAMTier(
        name="workstation",
        min_vram_gb=18,
        max_vram_gb=999,  # No upper limit
        recommended_model="Qwen/Qwen3-Embedding-0.6B",  # Keep 0.6B for OOM prevention
        multi_model_enabled=True,
        neural_reranking_enabled=True,
        multi_model_pool="full",  # Full 3-model pool (6.8GB)
        reranker_model="full",  # Full bge-reranker-v2-m3 (1.5GB)
    ),
]


class VRAMTierManager:
    """Auto-detect GPU VRAM and configure features accordingly.

    This manager detects available GPU VRAM and selects appropriate
    embedding models and feature enablement based on hardware capabilities.

    Example:
        >>> manager = VRAMTierManager()
        >>> tier = manager.detect_tier()
        >>> print(f"Tier: {tier.name}, Model: {tier.recommended_model}")
        Tier: desktop, Model: Qwen/Qwen3-Embedding-0.6B
    """

    def __init__(self) -> None:
        """Initialize VRAMTierManager."""
        self._detected_tier: Optional[VRAMTier] = None

    def detect_tier(self) -> VRAMTier:
        """Detect VRAM tier based on available GPU memory.

        Returns:
            VRAMTier object with configuration for detected hardware.

        Note:
            This method caches the result on first call. Subsequent calls
            return the cached tier without re-detection.
        """
        if self._detected_tier:
            return self._detected_tier

        available_gb = self._get_available_vram_gb()

        logger.info(f"Detected {available_gb:.1f}GB total VRAM")

        # Find matching tier
        for tier in VRAM_TIERS:
            if tier.min_vram_gb <= available_gb < tier.max_vram_gb:
                self._detected_tier = tier
                logger.info(
                    f"Selected tier: {tier.name} "
                    f"(recommended model: {tier.recommended_model})"
                )
                return tier

        # Fallback to minimal tier
        self._detected_tier = VRAM_TIERS[0]
        logger.warning(f"No matching tier for {available_gb:.1f}GB, using minimal tier")
        return self._detected_tier

    def _get_available_vram_gb(self) -> float:
        """Get total available VRAM in GB.

        Returns:
            Total VRAM in GB, or 0.0 if no GPU available.
        """
        try:
            import torch

            if not torch.cuda.is_available():
                logger.warning("CUDA not available, using CPU mode")
                return 0.0

            props = torch.cuda.get_device_properties(0)
            vram_gb = props.total_memory / (1024**3)
            return vram_gb

        except ImportError:
            logger.warning("PyTorch not available, cannot detect VRAM")
            return 0.0
        except Exception as e:
            logger.error(f"Error detecting VRAM: {e}")
            return 0.0

    def get_model_for_tier(self, tier_name: str) -> str:
        """Get recommended model for a specific tier name.

        Args:
            tier_name: Tier name (minimal, laptop, desktop, workstation)

        Returns:
            Full model name from MODEL_REGISTRY

        Raises:
            ValueError: If tier_name is not found
        """
        for tier in VRAM_TIERS:
            if tier.name == tier_name:
                return tier.recommended_model

        raise ValueError(
            f"Unknown tier: {tier_name}. Valid tiers: {[t.name for t in VRAM_TIERS]}"
        )

    def should_enable_multi_model(self) -> bool:
        """Check if multi-model routing should be enabled.

        Returns:
            True if current tier supports multi-model routing
        """
        tier = self.detect_tier()
        return tier.multi_model_enabled

    def should_enable_neural_reranking(self) -> bool:
        """Check if neural reranking should be enabled.

        Returns:
            True if current tier supports neural reranking
        """
        tier = self.detect_tier()
        return tier.neural_reranking_enabled
