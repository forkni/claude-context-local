"""Compare single-hop vs multi-hop search methods on current codebase.

This script runs comprehensive tests comparing standard (single-hop) search
with multi-hop semantic search, documenting performance and quality differences.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search.config import SearchConfig, SearchConfigManager
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


class SearchMethodComparator:
    """Compare single-hop and multi-hop search methods."""

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

        # Load existing config to get the model that was used for indexing
        config_manager = SearchConfigManager()
        config = config_manager.load_config()
        logger.info(f"Using model from config: {config.embedding_model_name}")

        self.embedder = CodeEmbedder(
            model_name=config.embedding_model_name,
            cache_dir=str(cache_dir)
        )

        # Initialize hybrid searcher
        logger.info("Initializing hybrid searcher...")
        # HybridSearcher needs the index subdirectory
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

    def run_single_hop_search(self, query: str, k: int = 10) -> Tuple[List, float]:
        """Run standard single-hop search.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            Tuple of (results list, execution time in ms)
        """
        start_time = time.time()
        results = self.searcher.search(
            query=query,
            k=k,
            search_mode="hybrid",
            use_parallel=True,
            min_bm25_score=0.1
        )
        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        return results, execution_time

    def run_multi_hop_search(
        self,
        query: str,
        k: int = 10,
        hops: int = 2,
        expansion: float = 0.3
    ) -> Tuple[List, float]:
        """Run multi-hop search.

        Args:
            query: Search query
            k: Number of results to return
            hops: Number of search hops
            expansion: Expansion factor per hop

        Returns:
            Tuple of (results list, execution time in ms)
        """
        start_time = time.time()
        results = self.searcher._multi_hop_search_internal(
            query=query,
            k=k,
            search_mode="hybrid",
            hops=hops,
            expansion_factor=expansion,
            use_parallel=True,
            min_bm25_score=0.1
        )
        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        return results, execution_time

    def analyze_results(
        self,
        query: str,
        single_results: List,
        multi_results: List,
        single_time: float,
        multi_time: float
    ) -> Dict[str, Any]:
        """Analyze differences between single-hop and multi-hop results.

        Args:
            query: Original search query
            single_results: Single-hop search results
            multi_results: Multi-hop search results
            single_time: Single-hop execution time (ms)
            multi_time: Multi-hop execution time (ms)

        Returns:
            Analysis dictionary
        """
        # Extract doc IDs
        single_doc_ids = {r.doc_id for r in single_results}
        multi_doc_ids = {r.doc_id for r in multi_results}

        # Find unique discoveries in multi-hop
        unique_discoveries = multi_doc_ids - single_doc_ids

        # Find overlap (top 5)
        single_top5_ids = {r.doc_id for r in single_results[:5]}
        multi_top5_ids = {r.doc_id for r in multi_results[:5]}
        top5_overlap = len(single_top5_ids & multi_top5_ids)

        # Determine value rating
        unique_count = len(unique_discoveries)
        if unique_count >= 4:
            value_rating = "HIGH"
        elif unique_count >= 2:
            value_rating = "MEDIUM"
        elif unique_count >= 1:
            value_rating = "LOW"
        else:
            value_rating = "NONE"

        return {
            "query": query,
            "single_hop": {
                "time_ms": round(single_time, 2),
                "result_count": len(single_results),
                "top_5": [
                    {
                        "doc_id": r.doc_id,
                        "score": round(r.score, 3),
                        "metadata": r.metadata
                    }
                    for r in single_results[:5]
                ],
                "all_doc_ids": list(single_doc_ids)
            },
            "multi_hop": {
                "time_ms": round(multi_time, 2),
                "result_count": len(multi_results),
                "top_5": [
                    {
                        "doc_id": r.doc_id,
                        "score": round(r.score, 3),
                        "metadata": r.metadata
                    }
                    for r in multi_results[:5]
                ],
                "all_doc_ids": list(multi_doc_ids),
                "unique_discoveries": list(unique_discoveries)
            },
            "comparison": {
                "time_overhead_ms": round(multi_time - single_time, 2),
                "time_overhead_pct": round(((multi_time - single_time) / single_time) * 100, 1) if single_time > 0 else 0.0,
                "top5_overlap_count": top5_overlap,
                "top5_overlap_pct": round((top5_overlap / 5) * 100, 1),
                "unique_discovery_count": unique_count,
                "value_rating": value_rating
            }
        }

    def run_comparison(self, k: int = 10) -> Dict[str, Any]:
        """Run full comparison across all test queries.

        Args:
            k: Number of results per query

        Returns:
            Complete comparison results
        """
        logger.info(f"Starting comparison with {len(TEST_QUERIES)} queries...")

        results = {
            "metadata": {
                "date": datetime.now().isoformat(),
                "project": str(self.project_path),
                "index_size": self.searcher.get_stats()["total_chunks"],
                "model": self.embedder.model_name,
                "k": k,
                "multi_hop_config": {
                    "hops": 2,
                    "expansion": 0.3
                }
            },
            "queries": []
        }

        for i, query in enumerate(TEST_QUERIES, 1):
            logger.info(f"Query {i}/{len(TEST_QUERIES)}: '{query}'")

            # Run single-hop search
            logger.info("  Running single-hop search...")
            single_results, single_time = self.run_single_hop_search(query, k=k)

            # Run multi-hop search
            logger.info("  Running multi-hop search...")
            multi_results, multi_time = self.run_multi_hop_search(query, k=k)

            # Analyze results
            analysis = self.analyze_results(
                query, single_results, multi_results,
                single_time, multi_time
            )
            results["queries"].append(analysis)

            logger.info(
                f"  Single: {single_time:.1f}ms, Multi: {multi_time:.1f}ms "
                f"({analysis['comparison']['time_overhead_pct']}% overhead), "
                f"Unique: {analysis['comparison']['unique_discovery_count']} chunks, "
                f"Value: {analysis['comparison']['value_rating']}"
            )

        # Calculate aggregate statistics
        results["aggregate"] = self._calculate_aggregates(results["queries"])

        return results

    def _calculate_aggregates(self, query_results: List[Dict]) -> Dict[str, Any]:
        """Calculate aggregate statistics.

        Args:
            query_results: List of query analysis results

        Returns:
            Aggregate statistics
        """
        total_queries = len(query_results)

        # Time statistics
        avg_single_time = sum(q["single_hop"]["time_ms"] for q in query_results) / total_queries
        avg_multi_time = sum(q["multi_hop"]["time_ms"] for q in query_results) / total_queries
        avg_overhead = sum(q["comparison"]["time_overhead_ms"] for q in query_results) / total_queries
        avg_overhead_pct = sum(q["comparison"]["time_overhead_pct"] for q in query_results) / total_queries

        # Discovery statistics
        avg_unique_discoveries = sum(
            q["comparison"]["unique_discovery_count"] for q in query_results
        ) / total_queries
        avg_top5_overlap = sum(
            q["comparison"]["top5_overlap_count"] for q in query_results
        ) / total_queries

        # Value distribution
        value_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
        for q in query_results:
            value_counts[q["comparison"]["value_rating"]] += 1

        queries_with_benefits = total_queries - value_counts["NONE"]
        benefit_pct = (queries_with_benefits / total_queries) * 100

        return {
            "total_queries": total_queries,
            "avg_single_time_ms": round(avg_single_time, 2),
            "avg_multi_time_ms": round(avg_multi_time, 2),
            "avg_overhead_ms": round(avg_overhead, 2),
            "avg_overhead_pct": round(avg_overhead_pct, 1),
            "avg_unique_discoveries": round(avg_unique_discoveries, 2),
            "avg_top5_overlap": round(avg_top5_overlap, 2),
            "queries_with_benefits": queries_with_benefits,
            "queries_with_benefits_pct": round(benefit_pct, 1),
            "value_distribution": value_counts
        }


def main():
    """Main entry point."""
    # Get project path
    project_path = Path(__file__).parent.parent

    # Get storage directory from config
    base_storage_dir = Path.home() / ".claude_code_search"  / "projects"

    # Get project-specific storage
    import hashlib
    project_hash = hashlib.md5(str(project_path.resolve()).encode()).hexdigest()[:8]

    # Find existing index directory (try both 768d and 1024d)
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
    comparator = SearchMethodComparator(str(project_path), str(storage_dir))
    results = comparator.run_comparison(k=10)

    # Save results as JSON
    output_dir = project_path / "analysis"
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / "comparison_results.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nResults saved to: {json_path}")

    # Print summary
    agg = results["aggregate"]
    print("\n" + "="*70)
    print("COMPARISON SUMMARY")
    print("="*70)
    print(f"Total queries: {agg['total_queries']}")
    print(f"Queries with benefits: {agg['queries_with_benefits']} ({agg['queries_with_benefits_pct']}%)")
    print(f"\nPerformance:")
    print(f"  Single-hop avg: {agg['avg_single_time_ms']:.1f}ms")
    print(f"  Multi-hop avg: {agg['avg_multi_time_ms']:.1f}ms")
    print(f"  Overhead: +{agg['avg_overhead_ms']:.1f}ms (+{agg['avg_overhead_pct']:.1f}%)")
    print(f"\nDiscoveries:")
    print(f"  Avg unique discoveries: {agg['avg_unique_discoveries']:.2f} chunks/query")
    overlap_pct = (agg['avg_top5_overlap'] / 5) * 100
    print(f"  Avg top-5 overlap: {agg['avg_top5_overlap']:.1f}/5 ({overlap_pct:.1f}%)")
    print(f"\nValue distribution:")
    for value, count in agg['value_distribution'].items():
        pct = (count / agg['total_queries']) * 100
        print(f"  {value}: {count} queries ({pct:.1f}%)")
    print("="*70)


if __name__ == "__main__":
    main()
