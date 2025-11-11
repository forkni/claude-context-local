"""Compare BM25 search with and without Snowball stemming.

This script runs comprehensive tests comparing BM25 search performance
with stemming enabled vs disabled, documenting recall improvements and
performance impact.

Usage:
    python tools/compare_stemming_impact.py

Output:
    - analysis/stemming_comparison_results.json: Raw comparison data
    - Console: Summary of findings
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

from search.bm25_index import BM25Index
from chunking.multi_language_chunker import MultiLanguageChunker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# Test queries with emphasis on verb form variations
# These queries are specifically designed to benefit from stemming
TEST_QUERIES = [
    # PRIMARY BENEFIT: Verb form variations
    "indexing and storage workflow",
    "searching for user records",
    "managing configuration settings",
    "processing data in chunks",
    "connecting to database",
    "embedding model loading",

    # SECONDARY BENEFIT: Noun/verb mismatches
    "authentication manager implementation",
    "optimization techniques for memory",
    "validation of user input",
    "chunking code into semantic units",

    # CONTROL: Should work similarly regardless of stemming
    "class UserManager",
    "def search_code",
    "FAISS vector index",
    "import torch",
    "BM25 sparse search",
]


class StemmingComparator:
    """Compare BM25 search with and without stemming."""

    def __init__(self, project_path: str):
        """Initialize comparator.

        Args:
            project_path: Path to project to analyze
        """
        self.project_path = Path(project_path)
        self.analysis_dir = self.project_path / "analysis"
        self.analysis_dir.mkdir(exist_ok=True)

        # Create temporary storage directories
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp())
        self.storage_baseline = self.temp_dir / "baseline"
        self.storage_stemmed = self.temp_dir / "stemmed"

        logger.info(f"Project path: {self.project_path}")
        logger.info(f"Temporary storage: {self.temp_dir}")

    def index_codebase(self, storage_dir: Path, use_stemming: bool) -> Tuple[BM25Index, List[Dict]]:
        """Index the codebase with specified stemming configuration.

        Args:
            storage_dir: Directory to store index
            use_stemming: Whether to enable stemming

        Returns:
            Tuple of (BM25Index, list of chunk metadata)
        """
        logger.info(f"Indexing codebase (stemming={use_stemming})...")
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Create BM25 index
        bm25_index = BM25Index(str(storage_dir), use_stemming=use_stemming)

        # Chunk the codebase
        chunker = MultiLanguageChunker(str(self.project_path))
        all_chunks = []

        # Find all supported files
        for ext in chunker.SUPPORTED_EXTENSIONS:
            for file_path in self.project_path.rglob(f"*{ext}"):
                # Skip ignored directories
                if any(part in chunker.DEFAULT_IGNORED_DIRS for part in file_path.parts):
                    continue

                try:
                    chunks = chunker.chunk_file(str(file_path))
                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.warning(f"Failed to chunk {file_path}: {e}")

        logger.info(f"Found {len(all_chunks)} chunks")

        # Prepare documents for BM25
        documents = []
        doc_ids = []
        metadata = {}

        for i, chunk in enumerate(all_chunks):
            doc_id = f"{chunk.relative_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}:{chunk.name}"
            documents.append(chunk.content)
            doc_ids.append(doc_id)
            metadata[doc_id] = {
                "file": chunk.relative_path,
                "lines": f"{chunk.start_line}-{chunk.end_line}",
                "type": chunk.chunk_type,
                "name": chunk.name,
                "content": chunk.content[:200]  # First 200 chars
            }

        # Index documents
        bm25_index.index_documents(documents, doc_ids, metadata)
        bm25_index.save()

        logger.info(f"Indexed {bm25_index.size} documents (stemming={use_stemming})")

        return bm25_index, all_chunks

    def compare_queries(
        self,
        baseline_index: BM25Index,
        stemmed_index: BM25Index,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """Compare search results for all test queries.

        Args:
            baseline_index: BM25 index without stemming
            stemmed_index: BM25 index with stemming
            k: Number of results to retrieve

        Returns:
            List of comparison results for each query
        """
        logger.info(f"Running {len(TEST_QUERIES)} test queries...")

        results = []

        for query_idx, query in enumerate(TEST_QUERIES, 1):
            logger.info(f"[{query_idx}/{len(TEST_QUERIES)}] Query: '{query}'")

            # Search baseline (no stemming)
            start_time = time.time()
            baseline_results = baseline_index.search(query, k=k, min_score=0.0)
            baseline_time = time.time() - start_time

            # Search with stemming
            start_time = time.time()
            stemmed_results = stemmed_index.search(query, k=k, min_score=0.0)
            stemmed_time = time.time() - start_time

            # Extract doc IDs
            baseline_ids = set(doc_id for doc_id, _, _ in baseline_results)
            stemmed_ids = set(doc_id for doc_id, _, _ in stemmed_results)

            # Calculate overlap and unique discoveries
            overlap = baseline_ids & stemmed_ids
            unique_to_stemmed = stemmed_ids - baseline_ids
            unique_to_baseline = baseline_ids - stemmed_ids

            # Analyze top result changes
            baseline_top = baseline_results[0][0] if baseline_results else None
            stemmed_top = stemmed_results[0][0] if stemmed_results else None
            top_result_changed = baseline_top != stemmed_top

            # Collect result details
            comparison = {
                "query": query,
                "baseline": {
                    "count": len(baseline_results),
                    "time_ms": baseline_time * 1000,
                    "results": [
                        {
                            "doc_id": doc_id,
                            "score": float(score),
                            "snippet": meta.get("content", "")[:150]
                        }
                        for doc_id, score, meta in baseline_results
                    ]
                },
                "stemmed": {
                    "count": len(stemmed_results),
                    "time_ms": stemmed_time * 1000,
                    "results": [
                        {
                            "doc_id": doc_id,
                            "score": float(score),
                            "snippet": meta.get("content", "")[:150]
                        }
                        for doc_id, score, meta in stemmed_results
                    ]
                },
                "comparison": {
                    "overlap_count": len(overlap),
                    "overlap_percentage": (len(overlap) / k * 100) if k > 0 else 0,
                    "unique_to_stemmed": len(unique_to_stemmed),
                    "unique_to_baseline": len(unique_to_baseline),
                    "top_result_changed": top_result_changed,
                    "time_difference_ms": (stemmed_time - baseline_time) * 1000
                },
                "unique_stemmed_discoveries": [
                    {
                        "doc_id": doc_id,
                        "score": next((float(s) for d, s, _ in stemmed_results if d == doc_id), 0.0)
                    }
                    for doc_id in list(unique_to_stemmed)[:5]  # Top 5 unique
                ]
            }

            results.append(comparison)

            # Log summary
            logger.info(f"  Baseline: {len(baseline_results)} results in {baseline_time*1000:.1f}ms")
            logger.info(f"  Stemmed:  {len(stemmed_results)} results in {stemmed_time*1000:.1f}ms")
            logger.info(f"  Overlap: {len(overlap)}/{k} ({len(overlap)/k*100:.1f}%)")
            logger.info(f"  Unique to stemmed: {len(unique_to_stemmed)}")

        return results

    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze comparison results and generate summary statistics.

        Args:
            results: List of query comparison results

        Returns:
            Summary analysis
        """
        logger.info("Analyzing results...")

        total_queries = len(results)
        queries_with_benefit = 0
        queries_with_top_change = 0
        total_unique_discoveries = 0
        total_time_overhead = 0

        benefit_distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}

        for result in results:
            comp = result["comparison"]
            unique_count = comp["unique_to_stemmed"]

            # Count queries that benefited
            if unique_count > 0:
                queries_with_benefit += 1

            # Classify benefit level
            if unique_count >= 5:
                benefit_distribution["HIGH"] += 1
            elif unique_count >= 2:
                benefit_distribution["MEDIUM"] += 1
            elif unique_count >= 1:
                benefit_distribution["LOW"] += 1
            else:
                benefit_distribution["NONE"] += 1

            # Count top result changes
            if comp["top_result_changed"]:
                queries_with_top_change += 1

            total_unique_discoveries += unique_count
            total_time_overhead += comp["time_difference_ms"]

        # Calculate statistics
        avg_unique_discoveries = total_unique_discoveries / total_queries
        avg_time_overhead = total_time_overhead / total_queries
        success_rate = (queries_with_benefit / total_queries) * 100

        summary = {
            "test_date": datetime.now().isoformat(),
            "total_queries": total_queries,
            "queries_with_benefit": queries_with_benefit,
            "success_rate_percentage": success_rate,
            "avg_unique_discoveries": avg_unique_discoveries,
            "total_unique_discoveries": total_unique_discoveries,
            "queries_with_top_result_change": queries_with_top_change,
            "avg_time_overhead_ms": avg_time_overhead,
            "benefit_distribution": benefit_distribution,
            "recommendation": self._generate_recommendation(success_rate, avg_unique_discoveries, avg_time_overhead)
        }

        return summary

    def _generate_recommendation(
        self,
        success_rate: float,
        avg_discoveries: float,
        avg_overhead: float
    ) -> str:
        """Generate recommendation based on analysis.

        Args:
            success_rate: Percentage of queries that benefited
            avg_discoveries: Average unique discoveries per query
            avg_overhead: Average time overhead in ms

        Returns:
            Recommendation string
        """
        if success_rate >= 70 and avg_discoveries >= 2.0 and avg_overhead < 5:
            return "STRONGLY RECOMMEND: Enable stemming by default"
        elif success_rate >= 50 and avg_discoveries >= 1.0 and avg_overhead < 10:
            return "RECOMMEND: Enable stemming by default"
        elif success_rate >= 30 and avg_overhead < 10:
            return "CONDITIONAL: Enable with config option, not default"
        else:
            return "NOT RECOMMENDED: Disable by default, make opt-in"

    def save_results(self, results: List[Dict[str, Any]], summary: Dict[str, Any]):
        """Save comparison results to JSON file.

        Args:
            results: Query comparison results
            summary: Summary analysis
        """
        output_file = self.analysis_dir / "stemming_comparison_results.json"

        output_data = {
            "metadata": {
                "test_date": summary["test_date"],
                "project_path": str(self.project_path),
                "total_queries": len(results)
            },
            "summary": summary,
            "query_results": results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {output_file}")

        # Also print summary to console
        self.print_summary(summary)

    def print_summary(self, summary: Dict[str, Any]):
        """Print summary to console.

        Args:
            summary: Summary analysis
        """
        print("\n" + "="*70)
        print("STEMMING IMPACT ANALYSIS - SUMMARY")
        print("="*70)
        print(f"\nTotal Queries Tested: {summary['total_queries']}")
        print(f"Queries Benefiting from Stemming: {summary['queries_with_benefit']} ({summary['success_rate_percentage']:.1f}%)")
        print(f"Average Unique Discoveries: {summary['avg_unique_discoveries']:.2f} per query")
        print(f"Total Unique Discoveries: {summary['total_unique_discoveries']}")
        print(f"Queries with Top Result Change: {summary['queries_with_top_result_change']}")
        print(f"Average Time Overhead: {summary['avg_time_overhead_ms']:.2f}ms")

        print(f"\nBenefit Distribution:")
        dist = summary['benefit_distribution']
        print(f"  HIGH (5+ discoveries):   {dist['HIGH']}/{summary['total_queries']} ({dist['HIGH']/summary['total_queries']*100:.1f}%)")
        print(f"  MEDIUM (2-4 discoveries): {dist['MEDIUM']}/{summary['total_queries']} ({dist['MEDIUM']/summary['total_queries']*100:.1f}%)")
        print(f"  LOW (1 discovery):        {dist['LOW']}/{summary['total_queries']} ({dist['LOW']/summary['total_queries']*100:.1f}%)")
        print(f"  NONE (no benefit):        {dist['NONE']}/{summary['total_queries']} ({dist['NONE']/summary['total_queries']*100:.1f}%)")

        print(f"\n{'='*70}")
        print(f"RECOMMENDATION: {summary['recommendation']}")
        print("="*70 + "\n")

    def cleanup(self):
        """Clean up temporary directories."""
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary files: {e}")

    def run(self):
        """Run the complete comparison analysis."""
        try:
            logger.info("Starting stemming impact comparison...")

            # Index codebase with baseline (no stemming)
            baseline_index, _ = self.index_codebase(self.storage_baseline, use_stemming=False)

            # Index codebase with stemming
            stemmed_index, _ = self.index_codebase(self.storage_stemmed, use_stemming=True)

            # Run comparison
            results = self.compare_queries(baseline_index, stemmed_index, k=10)

            # Analyze results
            summary = self.analyze_results(results)

            # Save results
            self.save_results(results, summary)

            logger.info("Comparison complete!")

            return summary

        finally:
            self.cleanup()


def main():
    """Main entry point."""
    # Use current project directory
    project_path = Path(__file__).parent.parent

    comparator = StemmingComparator(str(project_path))
    comparator.run()


if __name__ == "__main__":
    main()
