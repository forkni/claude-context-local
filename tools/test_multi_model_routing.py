"""Multi-model routing validation test suite.

Tests different model combinations and validates routing decisions against ground truth.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Test queries from verification results (analysis/model_relevance_verification_results.md)
TEST_QUERIES = [
    {
        "query": "error handling patterns",
        "expected_route": "qwen3",
        "verification_winner": "Qwen3-0.6B",
        "reason": "Found actual error handling pattern implementation (BaseHandler class)"
    },
    {
        "query": "configuration loading system",
        "expected_route": "bge_m3",
        "verification_winner": "BGE-M3",
        "reason": "Found core workflow methods (load_config, _load_from_environment)"
    },
    {
        "query": "BM25 index implementation",
        "expected_route": "qwen3",
        "verification_winner": "Qwen3-0.6B",
        "reason": "Most complete coverage (BM25Index class + search methods + wrapper)"
    },
    {
        "query": "incremental indexing logic",
        "expected_route": "bge_m3",
        "verification_winner": "BGE-M3",
        "reason": "Found complete logic (_full_index method, result structure)"
    },
    {
        "query": "embedding generation workflow",
        "expected_route": "bge_m3",
        "verification_winner": "BGE-M3",
        "reason": "Found embed_chunks method which IS the embedding workflow"
    },
    {
        "query": "multi-hop search algorithm",
        "expected_route": "qwen3",
        "verification_winner": "Qwen3-0.6B",
        "reason": "Most comprehensive view (dispatcher + algorithm + helpers)"
    },
    {
        "query": "Merkle tree change detection",
        "expected_route": "coderankembed",
        "verification_winner": "CodeRankEmbed",
        "reason": "Found ChangeDetector class AND detect_changes algorithm"
    },
    {
        "query": "hybrid search RRF reranking",
        "expected_route": "coderankembed",
        "verification_winner": "CodeRankEmbed",
        "reason": "Found complete implementation (RRFReranker class + rerank algorithm)"
    }
]


def get_vram_usage() -> Tuple[float, float, float]:
    """Get current VRAM usage in GB.

    Returns:
        (total_gb, used_gb, available_gb)
    """
    try:
        import torch
        if torch.cuda.is_available():
            total = torch.cuda.get_device_properties(0).total_memory / 1e9
            allocated = torch.cuda.memory_allocated(0) / 1e9
            reserved = torch.cuda.memory_reserved(0) / 1e9
            available = total - reserved
            return (total, reserved, available)
        else:
            return (0, 0, 0)
    except ImportError:
        return (0, 0, 0)


def format_vram(total: float, used: float, available: float) -> str:
    """Format VRAM usage as string."""
    if total == 0:
        return "CUDA not available"
    util = (used / total * 100) if total > 0 else 0
    return f"{used:.1f} / {total:.1f} GB ({util:.1f}% utilized, {available:.1f} GB available)"


def test_model_combination(
    models: List[str],
    queries: List[Dict],
    project_path: str
) -> Dict:
    """Test a specific combination of models.

    Args:
        models: List of model keys to load (e.g., ["qwen3", "bge_m3"])
        queries: List of test query dictionaries
        project_path: Path to indexed project for testing

    Returns:
        Dictionary with test results
    """
    from mcp_server.server import (
        MODEL_POOL_CONFIG,
        _embedders,
        get_embedder,
        _current_project,
        get_storage_dir
    )
    from embeddings.embedder import CodeEmbedder
    from search.query_router import QueryRouter
    import torch

    test_name = " + ".join([m.upper() for m in models])
    logger.info(f"\n{'='*80}")
    logger.info(f"TEST: {test_name}")
    logger.info(f"{'='*80}")

    # Get baseline VRAM
    baseline_total, baseline_used, baseline_available = get_vram_usage()
    logger.info(f"[MEMORY] Baseline: {format_vram(baseline_total, baseline_used, baseline_available)}")

    results = {
        "test_name": test_name,
        "models": models,
        "vram_baseline": baseline_used,
        "vram_after_load": 0,
        "vram_peak": 0,
        "queries_tested": 0,
        "routing_correct": 0,
        "routing_accuracy": 0.0,
        "query_results": [],
        "errors": []
    }

    # Load models
    cache_dir = get_storage_dir() / 'models'
    cache_dir.mkdir(parents=True, exist_ok=True)

    loaded_models = {}
    for model_key in models:
        try:
            model_name = MODEL_POOL_CONFIG[model_key]
            logger.info(f"[LOAD] Loading {model_key} ({model_name})...")

            start_time = time.time()
            embedder = CodeEmbedder(model_name=model_name, cache_dir=str(cache_dir))
            # Force model load
            _ = embedder.model
            load_time = time.time() - start_time

            loaded_models[model_key] = embedder
            _embedders[model_key] = embedder

            total, used, available = get_vram_usage()
            logger.info(f"  ✓ Loaded in {load_time:.1f}s | VRAM: {format_vram(total, used, available)}")

        except Exception as e:
            error_msg = f"Failed to load {model_key}: {e}"
            logger.error(f"  ✗ {error_msg}")
            results["errors"].append(error_msg)
            return results

    # Record VRAM after loading
    total, used_after_load, available = get_vram_usage()
    results["vram_after_load"] = used_after_load
    results["vram_peak"] = used_after_load
    logger.info(f"[MEMORY] After loading: {format_vram(total, used_after_load, available)}")
    logger.info(f"[MEMORY] Models consumed: {used_after_load - baseline_used:.1f} GB\n")

    # Initialize router
    router = QueryRouter(enable_logging=False)

    # Test queries
    for i, query_data in enumerate(queries, 1):
        query = query_data["query"]
        expected = query_data["expected_route"]

        # Only test if expected model is loaded
        if expected not in models:
            continue

        logger.info(f"[QUERY {i}] \"{query}\"")
        logger.info(f"  Expected: {expected.upper()}")

        try:
            # Route query
            decision = router.route(query)

            # Check if routing matches expected
            correct = decision.model_key == expected
            status = "✓" if correct else "✗"

            logger.info(f"  Actual: {decision.model_key.upper()} {status}")
            logger.info(f"  Confidence: {decision.confidence:.2f}")
            logger.info(f"  Reason: {decision.reason}")

            # Track VRAM
            total, used, available = get_vram_usage()
            if used > results["vram_peak"]:
                results["vram_peak"] = used

            # Record result
            query_result = {
                "query": query,
                "expected_route": expected,
                "actual_route": decision.model_key,
                "confidence": decision.confidence,
                "correct": correct,
                "vram_used": used
            }
            results["query_results"].append(query_result)
            results["queries_tested"] += 1

            if correct:
                results["routing_correct"] += 1

            logger.info("")

        except Exception as e:
            error_msg = f"Query failed: {e}"
            logger.error(f"  ✗ {error_msg}\n")
            results["errors"].append(error_msg)

    # Calculate accuracy
    if results["queries_tested"] > 0:
        results["routing_accuracy"] = (results["routing_correct"] / results["queries_tested"]) * 100

    # Final VRAM
    total, used_final, available = get_vram_usage()
    logger.info(f"[MEMORY] Final: {format_vram(total, used_final, available)}")
    logger.info(f"[MEMORY] Peak during test: {format_vram(total, results['vram_peak'], total - results['vram_peak'])}")

    # Summary
    logger.info(f"\n[SUMMARY] {test_name}")
    logger.info(f"  Routing Accuracy: {results['routing_correct']}/{results['queries_tested']} ({results['routing_accuracy']:.1f}%)")
    logger.info(f"  VRAM Impact: +{used_after_load - baseline_used:.1f} GB (models), Peak: {results['vram_peak']:.1f} GB")

    # Cleanup models
    for model_key, embedder in loaded_models.items():
        try:
            embedder.cleanup()
        except Exception as e:
            logger.warning(f"Cleanup warning for {model_key}: {e}")

    _embedders.clear()

    # Force GPU cache clear
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return results


def run_all_tests(project_path: str) -> Dict:
    """Run all test phases.

    Args:
        project_path: Path to indexed project

    Returns:
        Dictionary with all test results
    """
    all_results = {
        "phase1_tests": [],
        "phase2_test": None,
        "summary": {}
    }

    # Phase 1: Two-model combinations
    logger.info("\n" + "="*80)
    logger.info("PHASE 1: TWO-MODEL COMBINATIONS")
    logger.info("="*80)

    phase1_combinations = [
        ["qwen3", "bge_m3"],
        ["qwen3", "coderankembed"],
        ["bge_m3", "coderankembed"]
    ]

    for models in phase1_combinations:
        # Filter queries relevant to these models
        relevant_queries = [q for q in TEST_QUERIES if q["expected_route"] in models]

        result = test_model_combination(models, relevant_queries, project_path)
        all_results["phase1_tests"].append(result)

        # Brief pause between tests
        time.sleep(2)

    # Phase 2: All three models
    logger.info("\n" + "="*80)
    logger.info("PHASE 2: ALL THREE MODELS")
    logger.info("="*80)

    result = test_model_combination(
        ["qwen3", "bge_m3", "coderankembed"],
        TEST_QUERIES,
        project_path
    )
    all_results["phase2_test"] = result

    # Generate summary
    logger.info("\n" + "="*80)
    logger.info("OVERALL SUMMARY")
    logger.info("="*80)

    # Phase 1 summary
    phase1_accuracies = [r["routing_accuracy"] for r in all_results["phase1_tests"]]
    phase1_avg_accuracy = sum(phase1_accuracies) / len(phase1_accuracies) if phase1_accuracies else 0
    phase1_max_vram = max([r["vram_peak"] for r in all_results["phase1_tests"]])

    logger.info(f"\nPhase 1 (Two-model combinations):")
    logger.info(f"  Average Routing Accuracy: {phase1_avg_accuracy:.1f}%")
    logger.info(f"  Peak VRAM Usage: {phase1_max_vram:.1f} GB")

    # Phase 2 summary
    phase2 = all_results["phase2_test"]
    logger.info(f"\nPhase 2 (All three models):")
    logger.info(f"  Routing Accuracy: {phase2['routing_accuracy']:.1f}% ({phase2['routing_correct']}/{phase2['queries_tested']})")
    logger.info(f"  VRAM Usage: {phase2['vram_after_load']:.1f} GB loaded, {phase2['vram_peak']:.1f} GB peak")
    logger.info(f"  VRAM Headroom on RTX 4090: {24 - phase2['vram_peak']:.1f} GB")

    # Overall verdict
    logger.info(f"\nOVERALL VERDICT:")

    success_criteria = {
        "Phase 2 VRAM < 20 GB": phase2['vram_peak'] < 20,
        "Phase 2 Accuracy ≥ 75%": phase2['routing_accuracy'] >= 75,
        "No critical errors": len(phase2['errors']) == 0,
        "All 8 queries tested": phase2['queries_tested'] == 8
    }

    all_passed = all(success_criteria.values())

    for criterion, passed in success_criteria.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {status}: {criterion}")

    if all_passed:
        logger.info(f"\n🎉 ALL TESTS PASSED! Multi-model system is production-ready.")
    else:
        logger.info(f"\n⚠️  Some tests failed. Review results above.")

    all_results["summary"] = {
        "phase1_avg_accuracy": phase1_avg_accuracy,
        "phase1_max_vram": phase1_max_vram,
        "phase2_accuracy": phase2['routing_accuracy'],
        "phase2_vram_peak": phase2['vram_peak'],
        "phase2_headroom": 24 - phase2['vram_peak'],
        "success_criteria": success_criteria,
        "all_passed": all_passed
    }

    return all_results


def main():
    """Main test entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test multi-model routing system")
    parser.add_argument(
        "--project",
        type=str,
        default=".",
        help="Path to indexed project (default: current directory)"
    )
    parser.add_argument(
        "--phase",
        type=str,
        choices=["1", "2", "all"],
        default="all",
        help="Test phase to run (default: all)"
    )
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        choices=["qwen3", "bge_m3", "coderankembed"],
        help="Specific models to test (overrides phase)"
    )

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("MULTI-MODEL ROUTING VALIDATION TEST SUITE")
    logger.info("="*80)
    logger.info(f"Project: {args.project}")

    # Check CUDA availability
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")
        else:
            logger.warning("⚠️  CUDA not available - VRAM monitoring disabled")
    except ImportError:
        logger.warning("⚠️  PyTorch not found - VRAM monitoring disabled")

    # Run tests
    if args.models:
        # Custom model combination
        logger.info(f"Testing custom combination: {args.models}\n")
        result = test_model_combination(args.models, TEST_QUERIES, args.project)
    elif args.phase == "all":
        # Full test suite
        results = run_all_tests(args.project)
    else:
        logger.error(f"Phase {args.phase} not yet implemented for standalone execution")
        return 1

    logger.info(f"\n{'='*80}")
    logger.info("TEST SUITE COMPLETE")
    logger.info("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
