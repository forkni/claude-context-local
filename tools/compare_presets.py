"""Compare multi-hop presets (fast, balanced, thorough) on current codebase."""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search.config import SearchConfig, SearchConfigManager, MULTI_HOP_PRESETS
from search.hybrid_searcher import HybridSearcher
from embeddings.embedder import CodeEmbedder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# Test queries representing diverse real-world use cases
TEST_QUERIES = [
    # Conceptual/Algorithm queries
    "search algorithm implementation",
    "hybrid search combining BM25 and semantic",
    "configuration management system",
    "embedding model loading and initialization",

    # Code structure queries
    "chunking code into semantic units",
    "AST parsing for multiple languages",
    "FAISS vector index management",

    # Relationship/Integration queries
    "indexing and storage workflow",
    "search result reranking methods",
    "GPU memory optimization techniques",

    # Specific functionality queries
    "multi-language file support",
    "incremental indexing with Merkle trees",
    "BM25 sparse search implementation",
    "model dimension detection and validation",
    "multi-hop semantic search",  # Self-referential test
]


class PresetComparator:
    """Compare different multi-hop presets."""

    def __init__(self, project_path: str, storage_dir: str):
        """Initialize comparator.

        Args:
            project_path: Path to project being analyzed
            storage_dir: Path to search index storage (project directory, not index subdirectory)
        """
        self.project_path = Path(project_path)
        self.storage_dir = Path(storage_dir)

        # Initialize embedder
        logger.info("Initializing embedder...")
        cache_dir = self.storage_dir.parent.parent / "models"
        cache_dir.mkdir(exist_ok=True, parents=True)

        # Load existing config to get the model
        config_manager = SearchConfigManager()
        config = config_manager.load_config()
        logger.info(f"Using model from config: {config.embedding_model_name}")

        self.embedder = CodeEmbedder(
            model_name=config.embedding_model_name,
            cache_dir=str(cache_dir)
        )

        # Initialize hybrid searcher
        logger.info("Initializing hybrid searcher...")
        index_dir = self.storage_dir / "index"
        self.searcher = HybridSearcher(
            storage_dir=str(index_dir),
            embedder=self.embedder,
            bm25_weight=0.4,
            dense_weight=0.6
        )

        # Get index stats
        stats = self.searcher.get_stats()
        logger.info(f"Index loaded: {stats['total_chunks']} chunks")

        # Save original config to restore later
        self.config_manager = config_manager
        self.original_config = config

    def run_with_preset(
        self,
        preset_name: str,
        query: str,
        k: int = 10
    ) -> Tuple[List, float]:
        """Run search with a specific preset.

        Args:
            preset_name: Name of preset to use
            query: Search query
            k: Number of results

        Returns:
            Tuple of (results list, execution time in ms)
        """
        # Load preset configuration
        preset = MULTI_HOP_PRESETS[preset_name]

        start_time = time.time()
        results = self.searcher._multi_hop_search_internal(
            query=query,
            k=k,
            search_mode="hybrid",
            hops=preset["hops"],
            expansion_factor=preset["expansion"],
            use_parallel=True,
            min_bm25_score=0.1
        )
        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        return results, execution_time

    def analyze_preset_results(
        self,
        query: str,
        fast_results: List,
        deep_results: List,
        fast_time: float,
        deep_time: float
    ) -> Dict[str, Any]:
        """Analyze differences across presets with position-based analysis.

        Args:
            query: Original search query
            fast_results: Fast preset results (k=30)
            deep_results: Deep preset results (k=30)
            fast_time: Fast preset execution time (ms)
            deep_time: Deep preset execution time (ms)

        Returns:
            Analysis dictionary with position-based segments
        """
        # Extract doc IDs for full results and position segments
        fast_ids_all = {r.doc_id for r in fast_results}
        deep_ids_all = {r.doc_id for r in deep_results}

        # Segment by position
        fast_top10 = {r.doc_id for r in fast_results[:10]}
        fast_11_20 = {r.doc_id for r in fast_results[10:20]}
        fast_21_30 = {r.doc_id for r in fast_results[20:30]}

        deep_top10 = {r.doc_id for r in deep_results[:10]}
        deep_11_20 = {r.doc_id for r in deep_results[10:20]}
        deep_21_30 = {r.doc_id for r in deep_results[20:30]}

        # Find unique discoveries by Deep in each segment
        deep_unique_top10 = deep_top10 - fast_top10
        deep_unique_11_20 = deep_11_20 - fast_ids_all  # Not in ANY of Fast's results
        deep_unique_21_30 = deep_21_30 - fast_ids_all  # Not in ANY of Fast's results

        # Total unique discoveries
        deep_unique_total = deep_ids_all - fast_ids_all

        # Overlap metrics
        top10_overlap = len(fast_top10 & deep_top10)

        return {
            "query": query,
            "fast": {
                "time_ms": round(fast_time, 2),
                "result_count": len(fast_results),
                "top_10": [r.doc_id for r in fast_results[:10]],
                "positions_11_20": [r.doc_id for r in fast_results[10:20]],
                "positions_21_30": [r.doc_id for r in fast_results[20:30]],
                "all_doc_ids": list(fast_ids_all)
            },
            "deep": {
                "time_ms": round(deep_time, 2),
                "result_count": len(deep_results),
                "top_10": [r.doc_id for r in deep_results[:10]],
                "positions_11_20": [r.doc_id for r in deep_results[10:20]],
                "positions_21_30": [r.doc_id for r in deep_results[20:30]],
                "all_doc_ids": list(deep_ids_all),
                "unique_discoveries": {
                    "total": list(deep_unique_total),
                    "in_top10": list(deep_unique_top10),
                    "in_11_20": list(deep_unique_11_20),
                    "in_21_30": list(deep_unique_21_30),
                    "total_count": len(deep_unique_total),
                    "top10_count": len(deep_unique_top10),
                    "11_20_count": len(deep_unique_11_20),
                    "21_30_count": len(deep_unique_21_30)
                }
            },
            "comparison": {
                "top10_overlap": top10_overlap,
                "top10_overlap_pct": round((top10_overlap / 10) * 100, 1),
                "time_overhead_ms": round(deep_time - fast_time, 2),
                "time_overhead_pct": round(((deep_time - fast_time) / fast_time) * 100, 1) if fast_time > 0 else 0.0,
            }
        }

    def run_comparison(self, k: int = 30) -> Dict[str, Any]:
        """Run full comparison across all test queries with broader context.

        Args:
            k: Number of results per query (default 30 for broader context analysis)

        Returns:
            Complete comparison results with position-based analysis
        """
        logger.info(f"Starting preset comparison with {len(TEST_QUERIES)} queries...")
        logger.info(f"Testing broader context: k={k} (analyzing positions 1-10, 11-20, 21-30)")
        logger.info("Presets to test: fast, deep")

        results = {
            "metadata": {
                "date": datetime.now().isoformat(),
                "project": str(self.project_path),
                "index_size": self.searcher.get_stats()["total_chunks"],
                "model": self.embedder.model_name,
                "k": k,
                "analysis_type": "position_based",
                "segments": ["1-10 (top results)", "11-20 (secondary context)", "21-30 (extended context)"],
                "presets_tested": {
                    "fast": MULTI_HOP_PRESETS["fast"],
                    "deep": MULTI_HOP_PRESETS["deep"]
                }
            },
            "queries": []
        }

        for i, query in enumerate(TEST_QUERIES, 1):
            logger.info(f"Query {i}/{len(TEST_QUERIES)}: '{query}'")

            # Run with each preset
            logger.info("  Running with fast preset...")
            fast_results, fast_time = self.run_with_preset("fast", query, k=k)

            logger.info("  Running with deep preset...")
            deep_results, deep_time = self.run_with_preset("deep", query, k=k)

            # Analyze results
            analysis = self.analyze_preset_results(
                query, fast_results, deep_results,
                fast_time, deep_time
            )
            results["queries"].append(analysis)

            deep_disc = analysis['deep']['unique_discoveries']
            logger.info(
                f"  Fast: {fast_time:.1f}ms, Deep: {deep_time:.1f}ms (+{deep_time-fast_time:.1f}ms), "
                f"Deep unique: {deep_disc['total_count']} total "
                f"(top10: {deep_disc['top10_count']}, 11-20: {deep_disc['11_20_count']}, 21-30: {deep_disc['21_30_count']})"
            )

        # Calculate aggregate statistics
        results["aggregate"] = self._calculate_aggregates(results["queries"])

        return results

    def _calculate_aggregates(self, query_results: List[Dict]) -> Dict[str, Any]:
        """Calculate aggregate statistics across all queries.

        Args:
            query_results: List of query analysis results

        Returns:
            Aggregate statistics
        """
        total_queries = len(query_results)

        # Time statistics
        avg_fast = sum(q["fast"]["time_ms"] for q in query_results) / total_queries
        avg_deep = sum(q["deep"]["time_ms"] for q in query_results) / total_queries

        # Discovery statistics by position
        avg_deep_total = sum(q["deep"]["unique_discoveries"]["total_count"] for q in query_results) / total_queries
        avg_deep_top10 = sum(q["deep"]["unique_discoveries"]["top10_count"] for q in query_results) / total_queries
        avg_deep_11_20 = sum(q["deep"]["unique_discoveries"]["11_20_count"] for q in query_results) / total_queries
        avg_deep_21_30 = sum(q["deep"]["unique_discoveries"]["21_30_count"] for q in query_results) / total_queries

        # Count queries where Deep added value (by position)
        queries_with_total_discoveries = sum(1 for q in query_results if q["deep"]["unique_discoveries"]["total_count"] > 0)
        queries_with_top10_discoveries = sum(1 for q in query_results if q["deep"]["unique_discoveries"]["top10_count"] > 0)
        queries_with_11_20_discoveries = sum(1 for q in query_results if q["deep"]["unique_discoveries"]["11_20_count"] > 0)
        queries_with_21_30_discoveries = sum(1 for q in query_results if q["deep"]["unique_discoveries"]["21_30_count"] > 0)

        # Overlap statistics
        avg_top10_overlap = sum(q["comparison"]["top10_overlap"] for q in query_results) / total_queries

        return {
            "total_queries": total_queries,
            "avg_times_ms": {
                "fast": round(avg_fast, 2),
                "deep": round(avg_deep, 2)
            },
            "avg_overhead_ms": round(avg_deep - avg_fast, 2),
            "avg_overhead_pct": round(((avg_deep - avg_fast) / avg_fast) * 100, 1) if avg_fast > 0 else 0.0,
            "avg_unique_discoveries": {
                "total": round(avg_deep_total, 2),
                "in_top10": round(avg_deep_top10, 2),
                "in_11_20": round(avg_deep_11_20, 2),
                "in_21_30": round(avg_deep_21_30, 2)
            },
            "queries_with_discoveries": {
                "any_position": queries_with_total_discoveries,
                "any_position_pct": round((queries_with_total_discoveries / total_queries) * 100, 1),
                "in_top10": queries_with_top10_discoveries,
                "in_top10_pct": round((queries_with_top10_discoveries / total_queries) * 100, 1),
                "in_11_20": queries_with_11_20_discoveries,
                "in_11_20_pct": round((queries_with_11_20_discoveries / total_queries) * 100, 1),
                "in_21_30": queries_with_21_30_discoveries,
                "in_21_30_pct": round((queries_with_21_30_discoveries / total_queries) * 100, 1)
            },
            "avg_top10_overlap": round(avg_top10_overlap, 2),
            "avg_top10_overlap_pct": round((avg_top10_overlap / 10) * 100, 1)
        }


def main():
    """Main entry point."""
    # Get project path
    project_path = Path(__file__).parent.parent

    # Get storage directory from config
    base_storage_dir = Path.home() / ".claude_code_search" / "projects"

    # Get project-specific storage
    import hashlib
    project_hash = hashlib.md5(str(project_path.resolve()).encode()).hexdigest()[:8]

    # Find existing index directory
    storage_dir = None
    for dimension in [1024, 768]:  # Try BGE-M3 first, then Gemma
        candidate = base_storage_dir / f"{project_path.name}_{project_hash}_{dimension}d"
        if candidate.exists() and (candidate / "index" / "code.index").exists():
            storage_dir = candidate
            logger.info(f"Found existing index at: {storage_dir}")
            break

    if not storage_dir:
        logger.error(f"Project not indexed. Please index first: {project_path}")
        logger.error(f"Tried: {base_storage_dir / f'{project_path.name}_{project_hash}_*d'}")
        sys.exit(1)

    # Run comparison
    comparator = PresetComparator(str(project_path), str(storage_dir))
    results = comparator.run_comparison(k=10)

    # Save results as JSON
    output_dir = project_path / "analysis"
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / "preset_comparison_results.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nResults saved to: {json_path}")

    # Print summary
    agg = results["aggregate"]
    print("\n" + "="*80)
    print("PRESET COMPARISON SUMMARY (BROADER CONTEXT ANALYSIS)")
    print("="*80)
    print(f"Total queries: {agg['total_queries']}")
    print(f"Results analyzed: k=30 (positions 1-10, 11-20, 21-30)")
    print()
    print("Performance:")
    print(f"  Fast: {agg['avg_times_ms']['fast']:.1f}ms")
    print(f"  Deep: {agg['avg_times_ms']['deep']:.1f}ms (+{agg['avg_overhead_ms']:.1f}ms, {agg['avg_overhead_pct']:+.1f}%)")
    print()
    print("Top-10 Overlap:")
    print(f"  {agg['avg_top10_overlap']:.1f}/10 results ({agg['avg_top10_overlap_pct']:.1f}%) - Fast and Deep agree on top results")
    print()
    print("Deep's Unique Discoveries (avg per query):")
    print(f"  Total unique:        {agg['avg_unique_discoveries']['total']:.2f} chunks")
    print(f"  In top-10:           {agg['avg_unique_discoveries']['in_top10']:.2f} chunks")
    print(f"  In positions 11-20:  {agg['avg_unique_discoveries']['in_11_20']:.2f} chunks")
    print(f"  In positions 21-30:  {agg['avg_unique_discoveries']['in_21_30']:.2f} chunks")
    print()
    print("Queries with Discoveries:")
    print(f"  Any position:  {agg['queries_with_discoveries']['any_position']}/{agg['total_queries']} ({agg['queries_with_discoveries']['any_position_pct']:.1f}%)")
    print(f"  In top-10:     {agg['queries_with_discoveries']['in_top10']}/{agg['total_queries']} ({agg['queries_with_discoveries']['in_top10_pct']:.1f}%)")
    print(f"  In 11-20:      {agg['queries_with_discoveries']['in_11_20']}/{agg['total_queries']} ({agg['queries_with_discoveries']['in_11_20_pct']:.1f}%)")
    print(f"  In 21-30:      {agg['queries_with_discoveries']['in_21_30']}/{agg['total_queries']} ({agg['queries_with_discoveries']['in_21_30_pct']:.1f}%)")
    print("="*80)


if __name__ == "__main__":
    main()
