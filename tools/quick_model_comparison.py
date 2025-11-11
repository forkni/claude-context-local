"""Quick comparison of CodeRankEmbed vs BGE-M3 in semantic-only mode.

This script tests if CodeRankEmbed provides different results than BGE-M3
by comparing them on 10 sample queries using pure semantic search (no BM25).

Goal: Determine if CodeRankEmbed suffers from the same "hybrid search masking"
issue that made Qodo-1.5B identical to BGE-M3.
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from search.config import SearchConfigManager, get_search_config
from search.hybrid_searcher import HybridSearcher
from embeddings.embedder import CodeEmbedder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test queries - designed to test semantic understanding
TEST_QUERIES = [
    "error handling patterns",
    "state management logic",
    "validation and authentication",
    "configuration loading system",
    "file system operations",
    "data transformation pipeline",
    "graph traversal algorithms",
    "embedding generation workflow",
    "test fixtures and mocking",
    "incremental indexing strategy",
]


def calculate_jaccard_similarity(set_a: set, set_b: set) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def run_search_test(
    model_name: str,
    project_path: str,
    queries: List[str],
    k: int = 5
) -> Dict[str, List[Dict]]:
    """Run search test for a single model."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing model: {model_name}")
    logger.info(f"{'='*80}")

    # Configure for semantic-only search
    config_mgr = SearchConfigManager()
    config = config_mgr.load_config()

    # Save original settings
    original_model = config.embedding_model_name
    original_mode = config.default_search_mode
    original_bm25_weight = config.bm25_weight
    original_dense_weight = config.dense_weight
    original_multi_hop = config.enable_multi_hop

    # Set semantic-only mode with multi-hop disabled for fair comparison
    config.embedding_model_name = model_name
    config.default_search_mode = "semantic"
    config.bm25_weight = 0.0  # Pure semantic, no BM25
    config.dense_weight = 1.0
    config.enable_multi_hop = False  # Disable multi-hop for direct embedding comparison
    config_mgr.save_config(config)

    logger.info(f"Configuration:")
    logger.info(f"  - Model: {model_name}")
    logger.info(f"  - Search mode: semantic (BM25=0.0, Dense=1.0)")
    logger.info(f"  - Multi-hop: disabled (single-hop for fair comparison)")
    logger.info(f"  - Results per query: {k}")

    try:
        # Get project storage directory
        import hashlib
        project_id = hashlib.md5(project_path.encode()).hexdigest()[:8]

        # Get model dimension
        from search.config import get_model_config
        model_config = get_model_config(model_name)
        dimension = model_config['dimension']

        # Build storage path
        storage_dir = Path.home() / ".claude_code_search" / "projects" / f"claude-context-local_{project_id}_{dimension}d" / "index"

        if not storage_dir.exists():
            logger.error(f"Storage directory not found: {storage_dir}")
            logger.error(f"Please index the project with {model_name} first")
            return {}

        logger.info(f"Loading index from: {storage_dir}")

        # Initialize embedder
        embedder = CodeEmbedder(model_name=model_name)

        # Initialize searcher with semantic-only weights
        searcher = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=embedder,
            bm25_weight=0.0,  # Pure semantic
            dense_weight=1.0,
            rrf_k=100,
            max_workers=2
        )

        # Check if index is ready
        stats = searcher.get_stats()
        if not stats.get('is_ready', False):
            logger.error(f"Index not ready: {stats}")
            return {}

        logger.info(f"Index loaded: {stats.get('dense_vectors', 0)} vectors")

        # Run queries
        results = {}
        total_time = 0.0

        for i, query in enumerate(queries, 1):
            logger.info(f"\n[{i}/{len(queries)}] Query: '{query}'")

            start_time = time.time()
            search_results = searcher.search(
                query=query,
                k=k,
                search_mode="semantic"
            )
            query_time = time.time() - start_time
            total_time += query_time

            results[query] = search_results

            logger.info(f"  - Found {len(search_results)} results in {query_time*1000:.1f}ms")
            for j, result in enumerate(search_results[:3], 1):
                # HybridSearcher returns reranker.SearchResult with metadata dict
                name = result.metadata.get('name', 'unknown') if hasattr(result, 'metadata') else 'unknown'
                score = result.score if hasattr(result, 'score') else 0.0
                logger.info(f"    {j}. {name} (score: {score:.4f})")

        avg_time = total_time / len(queries)
        logger.info(f"\n  Average query time: {avg_time*1000:.1f}ms")

        # Cleanup
        embedder.cleanup()

        return results

    finally:
        # Restore original configuration
        config.embedding_model_name = original_model
        config.default_search_mode = original_mode
        config.bm25_weight = original_bm25_weight
        config.dense_weight = original_dense_weight
        config.enable_multi_hop = original_multi_hop
        config_mgr.save_config(config)


def compare_results(
    results_a: Dict[str, List],  # List[SearchResult]
    results_b: Dict[str, List],  # List[SearchResult]
    model_a_name: str,
    model_b_name: str,
    k: int = 5
) -> Dict:
    """Compare results from two models."""
    logger.info(f"\n{'='*80}")
    logger.info(f"COMPARISON: {model_a_name} vs {model_b_name}")
    logger.info(f"{'='*80}")

    comparison = {
        "model_a": model_a_name,
        "model_b": model_b_name,
        "k": k,
        "queries": {},
        "summary": {},
    }

    jaccard_scores = []
    rank_differences = []

    for query in results_a.keys():
        # Extract doc IDs from results (HybridSearcher uses reranker.SearchResult with doc_id)
        chunks_a = {r.doc_id for r in results_a[query][:k]}
        chunks_b = {r.doc_id for r in results_b[query][:k]}

        # Calculate Jaccard similarity
        jaccard = calculate_jaccard_similarity(chunks_a, chunks_b)
        jaccard_scores.append(jaccard)

        # Calculate rank difference for common results
        common_chunks = chunks_a & chunks_b
        rank_diff = 0
        if common_chunks:
            for doc_id in common_chunks:
                try:
                    rank_a = next(i for i, r in enumerate(results_a[query]) if r.doc_id == doc_id)
                    rank_b = next(i for i, r in enumerate(results_b[query]) if r.doc_id == doc_id)
                    rank_diff += abs(rank_a - rank_b)
                except StopIteration:
                    pass
            rank_diff /= len(common_chunks)
        rank_differences.append(rank_diff)

        # Store per-query comparison
        comparison["queries"][query] = {
            "jaccard": jaccard,
            "rank_difference": rank_diff,
            "overlap": len(common_chunks),
            "unique_to_a": len(chunks_a - chunks_b),
            "unique_to_b": len(chunks_b - chunks_a),
        }

        logger.info(f"\nQuery: '{query}'")
        logger.info(f"  - Jaccard similarity: {jaccard:.4f}")
        logger.info(f"  - Common results: {len(common_chunks)}/{k}")
        logger.info(f"  - Unique to {model_a_name}: {len(chunks_a - chunks_b)}")
        logger.info(f"  - Unique to {model_b_name}: {len(chunks_b - chunks_a)}")
        logger.info(f"  - Avg rank difference: {rank_diff:.2f}")

    # Calculate summary statistics
    avg_jaccard = sum(jaccard_scores) / len(jaccard_scores)
    min_jaccard = min(jaccard_scores)
    max_jaccard = max(jaccard_scores)
    avg_rank_diff = sum(rank_differences) / len(rank_differences)

    comparison["summary"] = {
        "avg_jaccard": avg_jaccard,
        "min_jaccard": min_jaccard,
        "max_jaccard": max_jaccard,
        "avg_rank_difference": avg_rank_diff,
        "queries_with_differences": sum(1 for j in jaccard_scores if j < 1.0),
        "total_queries": len(jaccard_scores),
    }

    logger.info(f"\n{'='*80}")
    logger.info(f"SUMMARY STATISTICS")
    logger.info(f"{'='*80}")
    logger.info(f"Average Jaccard similarity: {avg_jaccard:.4f}")
    logger.info(f"Jaccard range: [{min_jaccard:.4f}, {max_jaccard:.4f}]")
    logger.info(f"Average rank difference: {avg_rank_diff:.2f}")
    logger.info(f"Queries with differences: {comparison['summary']['queries_with_differences']}/{len(jaccard_scores)}")

    # Interpretation
    logger.info(f"\n{'='*80}")
    logger.info(f"INTERPRETATION")
    logger.info(f"{'='*80}")

    if avg_jaccard >= 0.95:
        logger.warning(f"⚠️  MODELS ARE NEARLY IDENTICAL (avg Jaccard {avg_jaccard:.4f})")
        logger.warning(f"    Similar to Qodo-1.5B situation - no practical difference")
        logger.warning(f"    Recommendation: Focus on CodeRankLLM re-ranker for differentiation")
    elif avg_jaccard >= 0.80:
        logger.info(f"⚠️  MODELS ARE SIMILAR (avg Jaccard {avg_jaccard:.4f})")
        logger.info(f"    Some differences, but may not be significant")
        logger.info(f"    Recommendation: Test re-ranker to see if it provides value")
    elif avg_jaccard >= 0.60:
        logger.info(f"✓ MODELS SHOW MODERATE DIFFERENCES (avg Jaccard {avg_jaccard:.4f})")
        logger.info(f"    CodeRankEmbed provides different rankings")
        logger.info(f"    Recommendation: Proceed with comprehensive testing")
    else:
        logger.info(f"✓ MODELS ARE SIGNIFICANTLY DIFFERENT (avg Jaccard {avg_jaccard:.4f})")
        logger.info(f"    CodeRankEmbed provides substantially different results")
        logger.info(f"    Recommendation: Full evaluation to determine which is better")

    return comparison


def main():
    """Main comparison runner."""
    project_path = str(project_root)
    k = 5  # Top-k results to compare

    logger.info("="*80)
    logger.info("QUICK MODEL COMPARISON: CodeRankEmbed vs BGE-M3")
    logger.info("="*80)
    logger.info(f"Project: {project_path}")
    logger.info(f"Queries: {len(TEST_QUERIES)}")
    logger.info(f"Search mode: SEMANTIC ONLY (BM25=0.0, Dense=1.0)")
    logger.info(f"Top-k: {k}")

    # Test CodeRankEmbed
    logger.info("\n" + "="*80)
    logger.info("PHASE 1: Testing CodeRankEmbed")
    logger.info("="*80)
    results_coderankembed = run_search_test(
        model_name="nomic-ai/CodeRankEmbed",
        project_path=project_path,
        queries=TEST_QUERIES,
        k=k
    )

    # Test BGE-M3
    logger.info("\n" + "="*80)
    logger.info("PHASE 2: Testing BGE-M3")
    logger.info("="*80)
    results_bge_m3 = run_search_test(
        model_name="BAAI/bge-m3",
        project_path=project_path,
        queries=TEST_QUERIES,
        k=k
    )

    # Compare results
    comparison = compare_results(
        results_a=results_coderankembed,
        results_b=results_bge_m3,
        model_a_name="CodeRankEmbed",
        model_b_name="BGE-M3",
        k=k
    )

    # Save results
    output_file = project_root / "analysis" / "quick_model_comparison.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(comparison, f, indent=2)

    logger.info(f"\n{'='*80}")
    logger.info(f"Results saved to: {output_file}")
    logger.info(f"{'='*80}")

    # Return exit code based on similarity
    avg_jaccard = comparison["summary"]["avg_jaccard"]
    if avg_jaccard >= 0.95:
        logger.warning("\n⚠️  Models are nearly identical - proceed to re-ranker implementation")
        sys.exit(1)  # Exit code 1 = identical models
    else:
        logger.info(f"\n✓ Models show differences (Jaccard {avg_jaccard:.4f}) - proceed with full evaluation")
        sys.exit(0)  # Exit code 0 = models differ


if __name__ == "__main__":
    main()
