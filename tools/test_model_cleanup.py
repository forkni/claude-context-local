"""Simple test to verify model cleanup between operations."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def get_vram_usage():
    """Get VRAM usage in GB."""
    try:
        import torch
        if torch.cuda.is_available():
            reserved = torch.cuda.memory_reserved(0) / 1e9
            return reserved
        return 0
    except:
        return 0

def test_cleanup_cycle():
    """Test loading and unloading models."""
    from mcp_server.server import search_code, _embedders, _cleanup_previous_resources

    logger.info("="*60)
    logger.info("MODEL CLEANUP VERIFICATION TEST")
    logger.info("="*60)

    # Baseline
    logger.info("\n[BASELINE] No models loaded")
    logger.info(f"Models in pool: {list(_embedders.keys())}")
    logger.info(f"VRAM: {get_vram_usage():.1f} GB")

    # Test 1: Load CodeRankEmbed
    logger.info("\n[TEST 1] Loading CodeRankEmbed...")
    search_code("Merkle tree change detection", k=1)
    logger.info(f"Models in pool: {list(_embedders.keys())}")
    logger.info(f"VRAM: {get_vram_usage():.1f} GB")

    # Cleanup 1
    logger.info("\n[CLEANUP 1] Unloading all models...")
    models_before = list(_embedders.keys())
    _cleanup_previous_resources()
    logger.info(f"Cleaned up: {models_before}")
    logger.info(f"Models in pool: {list(_embedders.keys())}")

    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.info("Cleared GPU cache")

    logger.info(f"VRAM: {get_vram_usage():.1f} GB")

    # Test 2: Load Qwen3
    logger.info("\n[TEST 2] Loading Qwen3...")
    search_code("error handling patterns", k=1, model_key="qwen3")
    logger.info(f"Models in pool: {list(_embedders.keys())}")
    logger.info(f"VRAM: {get_vram_usage():.1f} GB")

    # Cleanup 2
    logger.info("\n[CLEANUP 2] Unloading all models...")
    models_before = list(_embedders.keys())
    _cleanup_previous_resources()
    logger.info(f"Cleaned up: {models_before}")
    logger.info(f"Models in pool: {list(_embedders.keys())}")

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.info("Cleared GPU cache")

    logger.info(f"VRAM: {get_vram_usage():.1f} GB")

    # Test 3: Load BGE-M3
    logger.info("\n[TEST 3] Loading BGE-M3...")
    search_code("configuration loading", k=1, use_routing=False)
    logger.info(f"Models in pool: {list(_embedders.keys())}")
    logger.info(f"VRAM: {get_vram_usage():.1f} GB")

    # Final cleanup
    logger.info("\n[FINAL CLEANUP] Unloading all models...")
    models_before = list(_embedders.keys())
    _cleanup_previous_resources()
    logger.info(f"Cleaned up: {models_before}")
    logger.info(f"Models in pool: {list(_embedders.keys())}")

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.info("Cleared GPU cache")

    logger.info(f"VRAM: {get_vram_usage():.1f} GB")

    logger.info("\n" + "="*60)
    logger.info("✓ CLEANUP TEST COMPLETE")
    logger.info("="*60)

if __name__ == "__main__":
    test_cleanup_cycle()
