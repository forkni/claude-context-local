"""
Baseline Metrics Capture Script

Captures current v0.5.2 performance metrics for comparison with enhanced versions.

Usage:
    python tests/benchmarks/capture_baseline.py --project-path <path> --output baseline_metrics.json

Metrics Captured:
    - Search quality: Success@5, Success@10, MRR
    - Performance: Average query times by mode
    - Multi-hop: Success rate, avg discoveries
    - Index stats: Chunk count, file count, index size
"""

import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any
from statistics import mean, median, stdev

# Add parent directories to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from search.hybrid_searcher import HybridSearcher
from search.indexer import CodeIndexManager
from search.incremental_indexer import IncrementalIndexer


class BaselineMetricsCapture:
    """Capture baseline performance metrics"""

    def __init__(self, project_path: str, storage_dir: str = None):
        self.project_path = Path(project_path)
        self.storage_dir = storage_dir or str(Path.home() / ".claude_code_search")
        self.searcher = None
        self.indexer = None

    def load_test_queries(self, queries_path: str = None) -> Dict[str, List[str]]:
        """Load test queries from JSON file"""
        if queries_path is None:
            queries_path = Path(__file__).parent / "test_queries.json"

        with open(queries_path, 'r') as f:
            data = json.load(f)

        # Flatten query categories
        all_queries = []
        for category, category_data in data['query_categories'].items():
            all_queries.extend(category_data['queries'])

        return {
            'all_queries': all_queries,
            'by_category': {
                cat: cat_data['queries']
                for cat, cat_data in data['query_categories'].items()
            }
        }

    def initialize_searcher(self):
        """Initialize searcher with current project"""
        print(f"Initializing searcher for project: {self.project_path}")
        print(f"Using storage directory: {self.storage_dir}")

        # Initialize HybridSearcher with storage directory
        # Note: Assumes project is already indexed
        self.searcher = HybridSearcher(
            storage_dir=self.storage_dir,
            embedder=None  # Will auto-load if available
        )

    def measure_search_performance(
        self,
        queries: List[str],
        search_mode: str,
        k: int = 5
    ) -> Dict[str, Any]:
        """Measure search performance for a set of queries"""
        print(f"  Measuring {search_mode} search performance...")

        times = []
        results_counts = []

        for query in queries:
            start_time = time.time()

            try:
                results = self.searcher.search(
                    query=query,
                    k=k,
                    search_mode=search_mode
                )
                elapsed_ms = (time.time() - start_time) * 1000
                times.append(elapsed_ms)
                results_counts.append(len(results))

            except Exception as e:
                print(f"    Error on query '{query}': {e}")
                continue

        if not times:
            return {"error": "No successful queries"}

        return {
            'avg_time_ms': mean(times),
            'median_time_ms': median(times),
            'min_time_ms': min(times),
            'max_time_ms': max(times),
            'stddev_time_ms': stdev(times) if len(times) > 1 else 0,
            'p95_time_ms': sorted(times)[int(len(times) * 0.95)] if len(times) > 10 else max(times),
            'avg_results_returned': mean(results_counts),
            'total_queries': len(queries),
            'successful_queries': len(times)
        }

    def measure_multi_hop_performance(
        self,
        queries: List[str],
        k: int = 5
    ) -> Dict[str, Any]:
        """Measure multi-hop search performance"""
        print("  Measuring multi-hop search performance...")

        discoveries = []
        success_count = 0

        for query in queries:
            try:
                # Run search with multi-hop enabled (if configured)
                results = self.searcher.search(
                    query=query,
                    k=k,
                    search_mode='hybrid'
                )

                # Count unique discoveries (in production, would compare to baseline without multi-hop)
                # Results are SearchResult objects, access via attributes
                unique_chunks = len(set([r.chunk_id if hasattr(r, 'chunk_id') else r['chunk_id'] for r in results]))
                discoveries.append(unique_chunks)

                if len(results) > 0:
                    success_count += 1

            except Exception as e:
                print(f"    Error on query '{query}': {e}")
                continue

        if not discoveries:
            return {"error": "No successful queries"}

        return {
            'success_rate': success_count / len(queries),
            'avg_unique_discoveries': mean(discoveries),
            'median_unique_discoveries': median(discoveries),
            'min_discoveries': min(discoveries),
            'max_discoveries': max(discoveries),
            'total_queries': len(queries)
        }

    def get_index_statistics(self) -> Dict[str, Any]:
        """Get current index statistics"""
        print("  Collecting index statistics...")

        try:
            # Get index stats from dense index
            dense_index = self.searcher.dense_index
            bm25_index = self.searcher.bm25_index

            # Get embedding dimension
            embedding_dim = 0
            if dense_index.index is not None:
                embedding_dim = dense_index.index.d

            return {
                'total_chunks': dense_index.index.ntotal if dense_index.index else 0,
                'bm25_documents': bm25_index.size if bm25_index else 0,
                'embedding_dimension': embedding_dim,
                'index_type': 'FAISS IndexFlatIP + BM25',
                'bm25_stemming': self.searcher.bm25_use_stemming,
                'bm25_stopwords': self.searcher.bm25_use_stopwords
            }

        except Exception as e:
            print(f"    Error getting index stats: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def capture_all_metrics(self, output_path: str = None):
        """Capture all baseline metrics"""
        print("\n=== Capturing Baseline Metrics (v0.5.2) ===\n")

        # Load test queries
        print("Loading test queries...")
        queries_data = self.load_test_queries()
        all_queries = queries_data['all_queries']

        # Initialize searcher
        self.initialize_searcher()

        # Capture metrics
        metrics = {
            'version': 'v0.5.2',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'project_path': str(self.project_path),
            'index_statistics': {},
            'performance': {},
            'multi_hop': {},
            'queries_used': {
                'total': len(all_queries),
                'by_category': {
                    cat: len(queries)
                    for cat, queries in queries_data['by_category'].items()
                }
            }
        }

        # Index statistics
        print("\n1. Index Statistics")
        metrics['index_statistics'] = self.get_index_statistics()
        print(f"   Total chunks: {metrics['index_statistics'].get('total_chunks', 'N/A')}")
        print(f"   Files indexed: {metrics['index_statistics'].get('files_indexed', 'N/A')}")

        # Performance metrics for each search mode
        print("\n2. Performance Metrics")
        search_modes = ['hybrid', 'semantic', 'bm25']

        for mode in search_modes:
            print(f"\n   Testing {mode} mode:")
            metrics['performance'][mode] = self.measure_search_performance(
                queries=all_queries[:20],  # Use subset for speed
                search_mode=mode,
                k=5
            )
            avg_time = metrics['performance'][mode].get('avg_time_ms', 'N/A')
            if isinstance(avg_time, (int, float)):
                print(f"   Avg time: {avg_time:.2f}ms")
            else:
                print(f"   Avg time: {avg_time}")

        # Multi-hop performance
        print("\n3. Multi-Hop Performance")
        metrics['multi_hop'] = self.measure_multi_hop_performance(
            queries=all_queries[:20],
            k=5
        )
        print(f"   Success rate: {metrics['multi_hop'].get('success_rate', 'N/A'):.2%}")
        print(f"   Avg discoveries: {metrics['multi_hop'].get('avg_unique_discoveries', 'N/A'):.2f}")

        # Note about search quality metrics
        metrics['search_quality'] = {
            'note': 'Success@k and MRR require ground truth labels. ' +
                    'These metrics should be computed manually or with labeled dataset.',
            'success_at_5': None,
            'success_at_10': None,
            'mrr': None
        }

        # Save metrics
        if output_path is None:
            output_path = Path(__file__).parent / 'baseline_metrics.json'

        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)

        print(f"\n=== Baseline Metrics Saved to: {output_path} ===\n")

        # Print summary
        self.print_summary(metrics)

        return metrics

    def print_summary(self, metrics: Dict[str, Any]):
        """Print metrics summary"""
        print("\n=== BASELINE METRICS SUMMARY ===\n")

        print("Index Statistics:")
        idx_stats = metrics.get('index_statistics', {})
        print(f"  Total Chunks: {idx_stats.get('total_chunks', 'N/A')}")
        print(f"  Files Indexed: {idx_stats.get('files_indexed', 'N/A')}")
        print(f"  Model: {idx_stats.get('model_name', 'N/A')}")
        print(f"  Embedding Dimension: {idx_stats.get('embedding_dimension', 'N/A')}")

        print("\nPerformance (Average Query Time):")
        perf = metrics.get('performance', {})
        for mode, mode_metrics in perf.items():
            avg_time = mode_metrics.get('avg_time_ms', 'N/A')
            print(f"  {mode.capitalize()}: {avg_time:.2f}ms" if isinstance(avg_time, (int, float)) else f"  {mode.capitalize()}: {avg_time}")

        print("\nMulti-Hop Performance:")
        mh = metrics.get('multi_hop', {})
        print(f"  Success Rate: {mh.get('success_rate', 'N/A'):.2%}" if isinstance(mh.get('success_rate'), (int, float)) else f"  Success Rate: {mh.get('success_rate', 'N/A')}")
        print(f"  Avg Unique Discoveries: {mh.get('avg_unique_discoveries', 'N/A'):.2f}" if isinstance(mh.get('avg_unique_discoveries'), (int, float)) else f"  Avg Unique Discoveries: {mh.get('avg_unique_discoveries', 'N/A')}")

        print("\nSearch Quality:")
        print("  Note: Requires ground truth labels for Success@k and MRR")
        print("  These should be computed separately with labeled data")

        print("\n" + "="*40 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Capture baseline metrics for code search')
    parser.add_argument(
        '--project-path',
        type=str,
        default='.',
        help='Path to project to benchmark (default: current directory)'
    )
    parser.add_argument(
        '--storage-dir',
        type=str,
        default=None,
        help='Storage directory for indices (default: ~/.claude_code_search)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output path for metrics JSON (default: tests/benchmarks/baseline_metrics.json)'
    )
    parser.add_argument(
        '--queries',
        type=str,
        default=None,
        help='Path to test queries JSON (default: tests/benchmarks/test_queries.json)'
    )

    args = parser.parse_args()

    # Capture baseline
    capture = BaselineMetricsCapture(
        project_path=args.project_path,
        storage_dir=args.storage_dir
    )

    try:
        metrics = capture.capture_all_metrics(output_path=args.output)
        print("[SUCCESS] Baseline metrics captured successfully!")
        return 0

    except Exception as e:
        print(f"\n[ERROR] Error capturing baseline metrics: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
