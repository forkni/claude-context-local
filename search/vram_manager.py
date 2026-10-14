"""VRAM tier table: which embedder and reranker each GPU size gets.

``search/index_probe.py`` maps a measured GPU to a tier with ``_tier_for``;
the per-process VRAM cap and batch sizing live in ``embeddings/vram_budget.py``.
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
        reranker_model: Reranker type ("full", "lightweight")
    """

    name: str
    min_vram_gb: float
    max_vram_gb: float
    recommended_model: str
    neural_reranking_enabled: bool
    reranker_model: str | None = None  # "full" or "lightweight"


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
        reranker_model=None,  # Reranking disabled
    ),
    VRAMTier(
        name="laptop",
        min_vram_gb=6,
        max_vram_gb=10,
        recommended_model="codefuse-ai/F2LLM-v2-330M",  # 8GB GPUs: 4.24GB peak with gte (ADR-0084)
        neural_reranking_enabled=True,  # Lightweight reranker (0.3GB)
        reranker_model="lightweight",  # Use gte-reranker-modernbert-base
    ),
    VRAMTier(
        name="desktop",
        min_vram_gb=10,
        max_vram_gb=18,
        recommended_model="Qwen/Qwen3-Embedding-0.6B",  # 1024d, ~1.1GB VRAM
        neural_reranking_enabled=True,
        reranker_model="full",
    ),
    VRAMTier(
        name="workstation",
        min_vram_gb=18,
        max_vram_gb=999,  # No upper limit
        recommended_model="Qwen/Qwen3-Embedding-0.6B",  # 1024d, ~1.1GB VRAM; baseline MRR 0.94
        neural_reranking_enabled=True,
        reranker_model="full",
    ),
]
