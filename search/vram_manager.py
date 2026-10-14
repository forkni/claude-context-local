"""VRAM tier table: what each GPU size gets (models, reranker, batch bounds).

``tier_for`` maps a measured GPU to its row.  ``search/index_probe.py`` reads
the model, reranker and batch columns when it writes a config; the per-process
VRAM cap and the dynamic batch sizer live in ``embeddings/vram_budget.py`` and
read only the ``sizer_*`` columns.
"""

from dataclasses import dataclass


@dataclass
class VRAMTier:
    """VRAM tier configuration for automatic feature adaptation.

    Attributes:
        name: Tier name (minimal, laptop, desktop, workstation)
        min_vram_gb: Minimum VRAM in GB for this tier (inclusive)
        max_vram_gb: Maximum VRAM in GB for this tier (exclusive)
        recommended_model: Full model name from MODEL_REGISTRY
        neural_reranking_enabled: Whether neural reranking should be enabled
        embed_batch_size: Fallback embedding batch when dynamic sizing is off
        dynamic_batch_max: Ceiling the probe writes to ``performance.dynamic_batch_max``
        reranker_model: Reranker type ("full", "lightweight")
        sizer_max_batch: ``calculate_optimal_batch_size`` clamps its ceiling down to
            this (None = no tier clamp)
        sizer_min_batch: ``calculate_optimal_batch_size`` clamps its floor down to
            this (None = no tier clamp)
    """

    name: str
    min_vram_gb: float
    max_vram_gb: float
    recommended_model: str
    neural_reranking_enabled: bool
    embed_batch_size: int
    dynamic_batch_max: int
    reranker_model: str | None = None  # "full" or "lightweight"
    sizer_max_batch: int | None = None
    sizer_min_batch: int | None = None


# VRAM tier definitions based on GPU capabilities
# RTX 3060/4060 (8GB) → laptop tier → F2LLM-v2-330M (ADR-0084; BGE-M3 before 2026-10-08)
# RTX 3060 12GB (12GB) → desktop tier → Qwen3-0.6B
# RTX 3090/4090 (24GB) → workstation tier → Qwen3-0.6B (single-model + reranker, ~2.5GB)
VRAM_TIERS: list[VRAMTier] = [
    VRAMTier(
        name="minimal",
        min_vram_gb=0,
        max_vram_gb=6,
        recommended_model="codefuse-ai/F2LLM-v2-330M",  # 0.67GB weights, MTEB-Code 75.74 (ADR-0084)
        neural_reranking_enabled=False,  # Disable to conserve VRAM
        embed_batch_size=32,
        dynamic_batch_max=96,
        reranker_model=None,  # Reranking disabled
        sizer_max_batch=16,
        sizer_min_batch=2,
    ),
    VRAMTier(
        name="laptop",
        min_vram_gb=6,
        max_vram_gb=10,
        recommended_model="codefuse-ai/F2LLM-v2-330M",  # 8GB GPUs: 4.24GB peak with gte (ADR-0084)
        neural_reranking_enabled=True,  # Lightweight reranker (0.3GB)
        embed_batch_size=64,
        dynamic_batch_max=192,
        reranker_model="lightweight",  # Use gte-reranker-modernbert-base
        sizer_max_batch=32,
        sizer_min_batch=4,
    ),
    VRAMTier(
        name="desktop",
        min_vram_gb=10,
        max_vram_gb=18,
        recommended_model="Qwen/Qwen3-Embedding-0.6B",  # 1024d, ~1.1GB VRAM
        neural_reranking_enabled=True,
        embed_batch_size=128,
        dynamic_batch_max=384,
        reranker_model="full",
    ),
    VRAMTier(
        name="workstation",
        min_vram_gb=18,
        max_vram_gb=999,  # No upper limit
        recommended_model="Qwen/Qwen3-Embedding-0.6B",  # 1024d, ~1.1GB VRAM; baseline MRR 0.94
        neural_reranking_enabled=True,
        embed_batch_size=256,
        dynamic_batch_max=512,
        reranker_model="full",
    ),
]


def tier_for(vram_total_gb: float) -> VRAMTier:
    """Row whose ``[min_vram_gb, max_vram_gb)`` band holds the GPU; minimal if none does."""
    for tier in VRAM_TIERS:
        if tier.min_vram_gb <= vram_total_gb < tier.max_vram_gb:
            return tier
    return VRAM_TIERS[0]
