"""Unit tests for the VRAM tier table (search/vram_manager.py)."""

import pytest

from search.config import MODEL_REGISTRY
from search.vram_manager import VRAM_TIERS, tier_for


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
            # Models can be F2LLM-330M, BGE-M3 or Qwen variants
            assert tier.recommended_model in [
                "codefuse-ai/F2LLM-v2-330M",
                "BAAI/bge-m3",
                "Qwen/Qwen3-Embedding-0.6B",
                "jinaai/jina-embeddings-v5-text-small-retrieval",
            ]
            assert len(tier.recommended_model) > 5
            assert tier.recommended_model in MODEL_REGISTRY

    def test_feature_enablement_progression(self):
        """Test that reranking is enabled progressively with higher tiers."""
        minimal = VRAM_TIERS[0]
        laptop = VRAM_TIERS[1]
        desktop = VRAM_TIERS[2]
        workstation = VRAM_TIERS[3]

        # Minimal tier has reranking disabled
        assert minimal.neural_reranking_enabled is False
        assert minimal.reranker_model is None

        # Laptop tier: lightweight reranker enabled
        assert laptop.neural_reranking_enabled is True
        assert laptop.reranker_model == "lightweight"

        # Higher tiers enable full reranker
        assert desktop.neural_reranking_enabled is True
        assert desktop.reranker_model == "full"
        assert workstation.neural_reranking_enabled is True
        assert workstation.reranker_model == "full"


class TestTierFor:
    """tier_for: the one band lookup every tier-dependent number goes through."""

    @pytest.mark.parametrize(
        ("vram_gb", "name"),
        [
            (0.0, "minimal"),
            (5.9, "minimal"),
            (6.0, "laptop"),
            (7.99, "laptop"),
            (10.0, "desktop"),
            (17.9, "desktop"),
            (18.0, "workstation"),
            (24.0, "workstation"),
        ],
    )
    def test_half_open_bands(self, vram_gb, name):
        assert tier_for(vram_gb).name == name

    def test_out_of_table_falls_back_to_minimal(self):
        assert tier_for(-1.0).name == "minimal"
        assert tier_for(5000.0).name == "minimal"

    def test_batch_columns_grow_with_vram(self):
        embed = [t.embed_batch_size for t in VRAM_TIERS]
        dynamic = [t.dynamic_batch_max for t in VRAM_TIERS]
        assert embed == sorted(embed) and dynamic == sorted(dynamic)
        assert all(t.embed_batch_size < t.dynamic_batch_max for t in VRAM_TIERS)

    def test_sizer_clamps_only_on_small_tiers(self):
        clamped = [t.name for t in VRAM_TIERS if t.sizer_max_batch is not None]
        assert clamped == ["minimal", "laptop"]
        for t in VRAM_TIERS:
            assert (t.sizer_min_batch is None) == (t.sizer_max_batch is None)
