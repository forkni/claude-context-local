"""MCP search_code() integration test with multi-model routing.

Tests that MCP server search functionality works correctly with:
- Multi-model routing
- Manual model selection
- CodeRankEmbed cache fix
- Routing metadata
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Test queries from verification results
TEST_QUERIES = [
    {"query": "Merkle tree change detection", "expected_route": "coderankembed"},
    {"query": "error handling patterns", "expected_route": "qwen3"},
    {"query": "configuration loading system", "expected_route": "bge_m3"},
]


def test_basic_search_with_routing():
    """Test 1: Basic search with routing enabled (default behavior)."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Basic search with routing enabled")
    logger.info("="*80)

    from mcp_server.server import search_code

    query = "Merkle tree change detection"
    logger.info(f"Query: '{query}'")

    try:
        result = search_code(query, k=3)

        # Verify routing metadata exists
        routing = result.get('routing')
        if routing:
            logger.info(f"✓ Routing metadata present:")
            logger.info(f"  - Model selected: {routing['model_selected']}")
            logger.info(f"  - Confidence: {routing['confidence']:.2f}")
            logger.info(f"  - Reason: {routing['reason']}")
        else:
            logger.error("✗ No routing metadata in results")
            return False

        # Verify results exist
        if result.get('results'):
            logger.info(f"✓ Found {len(result['results'])} results")
        else:
            logger.error("✗ No search results returned")
            return False

        return True

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_manual_model_override():
    """Test 2: Search with manual model_key override."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Manual model selection override")
    logger.info("="*80)

    from mcp_server.server import search_code

    query = "error handling patterns"
    model_key = "qwen3"
    logger.info(f"Query: '{query}'")
    logger.info(f"Forcing model: {model_key}")

    try:
        result = search_code(query, k=3, model_key=model_key)

        # Verify routing shows manual selection
        routing = result.get('routing')
        if routing:
            if routing['model_selected'] == model_key:
                logger.info(f"✓ Model override successful: {routing['model_selected']}")
            else:
                logger.error(f"✗ Expected {model_key}, got {routing['model_selected']}")
                return False
        else:
            logger.error("✗ No routing metadata")
            return False

        # Verify results exist
        if result.get('results'):
            logger.info(f"✓ Found {len(result['results'])} results")
        else:
            logger.error("✗ No search results")
            return False

        return True

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routing_disabled():
    """Test 3: Search with routing disabled (use default model)."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Search with routing disabled")
    logger.info("="*80)

    from mcp_server.server import search_code

    query = "configuration loading system"
    logger.info(f"Query: '{query}'")
    logger.info(f"Routing disabled (use_routing=False)")

    try:
        result = search_code(query, k=3, use_routing=False)

        # Verify routing metadata reflects disabled state
        routing = result.get('routing')
        if routing:
            logger.info(f"✓ Routing metadata present (disabled mode):")
            logger.info(f"  - Model selected: {routing['model_selected']}")
            logger.info(f"  - Expected: bge_m3 (default)")

            if routing['model_selected'] == 'bge_m3':
                logger.info(f"✓ Correctly using default model")
            else:
                logger.warning(f"⚠ Using {routing['model_selected']} instead of default")
        else:
            logger.error("✗ No routing metadata")
            return False

        # Verify results exist
        if result.get('results'):
            logger.info(f"✓ Found {len(result['results'])} results")
        else:
            logger.error("✗ No search results")
            return False

        return True

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_coderankembed_cache():
    """Test 4: Verify CodeRankEmbed loads without auto-recovery."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: CodeRankEmbed cache behavior")
    logger.info("="*80)

    from mcp_server.server import search_code

    # Query that routes to CodeRankEmbed
    query = "hybrid search RRF reranking"
    logger.info(f"Query: '{query}' (should route to CodeRankEmbed)")

    try:
        start_time = time.time()
        result = search_code(query, k=3)
        load_time = time.time() - start_time

        routing = result.get('routing')
        if routing and routing['model_selected'] == 'coderankembed':
            logger.info(f"✓ Routed to CodeRankEmbed as expected")
            logger.info(f"✓ Load time: {load_time:.1f}s")

            # Check load time (should be ~1s from cache, not 2s+ with auto-recovery)
            if load_time < 1.5:
                logger.info(f"✓ Fast load indicates no auto-recovery (cache working)")
            else:
                logger.warning(f"⚠ Slow load ({load_time:.1f}s) - may indicate cache issue")
        else:
            logger.error(f"✗ Did not route to CodeRankEmbed")
            return False

        # Verify results
        if result.get('results'):
            logger.info(f"✓ Found {len(result['results'])} results")
        else:
            logger.error("✗ No results")
            return False

        return True

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_verification_queries():
    """Test 5: Run all 8 verification queries through MCP search."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: All verification queries")
    logger.info("="*80)

    from mcp_server.server import search_code

    full_queries = [
        {"query": "error handling patterns", "expected": "qwen3"},
        {"query": "configuration loading system", "expected": "bge_m3"},
        {"query": "BM25 index implementation", "expected": "qwen3"},
        {"query": "incremental indexing logic", "expected": "bge_m3"},
        {"query": "embedding generation workflow", "expected": "bge_m3"},
        {"query": "multi-hop search algorithm", "expected": "qwen3"},
        {"query": "Merkle tree change detection", "expected": "coderankembed"},
        {"query": "hybrid search RRF reranking", "expected": "coderankembed"},
    ]

    correct = 0
    total = len(full_queries)

    for query_data in full_queries:
        query = query_data["query"]
        expected = query_data["expected"]

        try:
            result = search_code(query, k=3)
            routing = result.get('routing', {})
            actual = routing.get('model_selected', 'unknown')

            if actual == expected:
                logger.info(f"✓ '{query}' → {actual}")
                correct += 1
            else:
                logger.error(f"✗ '{query}' → {actual} (expected {expected})")

        except Exception as e:
            logger.error(f"✗ '{query}' failed: {e}")

    accuracy = (correct / total * 100) if total > 0 else 0
    logger.info(f"\nRouting Accuracy: {correct}/{total} ({accuracy:.1f}%)")

    return correct == total


def check_vram_usage():
    """Check VRAM usage with all models loaded."""
    logger.info("\n" + "="*80)
    logger.info("VRAM USAGE CHECK")
    logger.info("="*80)

    try:
        import torch
        if not torch.cuda.is_available():
            logger.warning("⚠ CUDA not available - skipping VRAM check")
            return True

        total = torch.cuda.get_device_properties(0).total_memory / 1e9
        reserved = torch.cuda.memory_reserved(0) / 1e9

        logger.info(f"Total VRAM: {total:.1f} GB")
        logger.info(f"Reserved: {reserved:.1f} GB ({reserved/total*100:.1f}%)")

        if reserved < 20:
            logger.info(f"✓ VRAM usage under 20 GB threshold")
        else:
            logger.warning(f"⚠ High VRAM usage ({reserved:.1f} GB)")

        return True

    except Exception as e:
        logger.warning(f"⚠ Could not check VRAM: {e}")
        return True


def main():
    """Run all MCP integration tests."""
    logger.info("="*80)
    logger.info("MCP SEARCH_CODE() INTEGRATION TEST SUITE")
    logger.info("="*80)

    # Ensure project is indexed
    logger.info("\n[SETUP] Ensuring project is indexed...")
    try:
        from mcp_server.server import index_directory
        result = index_directory(str(Path.cwd()))
        if result.get('success') is True:
            logger.info(f"✓ Project indexed ({result.get('chunks_indexed', 0)} chunks)")
        else:
            logger.error(f"✗ Indexing failed: {result}")
            return 1
    except Exception as e:
        logger.error(f"✗ Setup failed: {e}")
        return 1

    # Run tests
    tests = [
        ("Basic search with routing", test_basic_search_with_routing),
        ("Manual model override", test_manual_model_override),
        ("Routing disabled", test_routing_disabled),
        ("CodeRankEmbed cache", test_coderankembed_cache),
        ("All verification queries", test_all_verification_queries),
    ]

    results = {}
    for i, (test_name, test_func) in enumerate(tests, 1):
        try:
            passed = test_func()
            results[test_name] = passed

            # Cleanup models between tests (except after last test)
            if i < len(tests):
                logger.info(f"\n[CLEANUP] Unloading models after test {i}...")
                try:
                    from mcp_server.server import _embedders, _cleanup_previous_resources
                    models_before = list(_embedders.keys())
                    _cleanup_previous_resources()
                    logger.info(f"✓ Cleaned up models: {models_before}")

                    # Force GPU cache clear
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                            logger.info("✓ Cleared GPU cache")
                    except ImportError:
                        pass
                except Exception as cleanup_error:
                    logger.warning(f"⚠ Cleanup warning: {cleanup_error}")

        except Exception as e:
            logger.error(f"✗ {test_name} crashed: {e}")
            results[test_name] = False

    # VRAM check
    check_vram_usage()

    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        logger.info("\n🎉 ALL MCP INTEGRATION TESTS PASSED!")
        return 0
    else:
        logger.info("\n⚠️  Some tests failed - review results above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
