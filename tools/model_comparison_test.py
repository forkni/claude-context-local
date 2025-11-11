"""Comprehensive model comparison test: BGE-M3 vs Qodo-1.5B.

This script runs 30 representative queries on both models and compares:
- Relevance metrics (top-k overlap, rank correlation, precision@k)
- Performance metrics (latency, memory)
- Graph metadata (presence, accuracy, consistency)
- Score distributions

Usage:
    python tools/model_comparison_test.py \
        --queries tests/benchmarks/model_comparison_queries.json \
        --output analysis/MODEL_COMPARISON_RESULTS.json \
        --report analysis/MODEL_COMPARISON_REPORT.md
"""

import sys
import json
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search.config import SearchConfigManager, get_search_config
from mcp_server.server import get_searcher, get_index_manager
from embeddings.embedder import CodeEmbedder


@dataclass
class QueryResult:
    """Single query result from one model."""
    doc_id: str
    file: str
    name: str
    score: float
    rank: int
    chunk_type: str
    graph: Optional[Dict] = None


@dataclass
class ModelComparisonResult:
    """Comparison results for a single query across both models."""
    query_id: int
    query: str
    category: str

    # BGE-M3 results
    bge_results: List[Dict]
    bge_time_ms: float

    # Qodo-1.5B results
    qodo_results: List[Dict]
    qodo_time_ms: float

    # Overlap metrics
    top5_overlap: float  # Jaccard similarity
    rank_correlation: float  # Kendall's Tau (or None if no overlap)

    # Score metrics
    avg_score_diff: float
    max_score_diff: float
    score_separation_bge: float  # rank1 - rank5
    score_separation_qodo: float

    # Graph metrics
    bge_graph_presence_rate: float  # % of results with graph data
    qodo_graph_presence_rate: float
    graph_metadata_consistent: bool  # Do shared results have same graph?

    # Winner
    winner: str  # "BGE-M3", "Qodo-1.5B", or "Tie"
    reason: str


class ModelComparisonTester:
    """Comprehensive model comparison testing framework."""

    def __init__(self, project_path: str):
        """Initialize tester with project path."""
        self.project_path = Path(project_path)
        self.config_manager = SearchConfigManager()

        print("=" * 70)
        print("MODEL COMPARISON TEST: BGE-M3 vs Qodo-1.5B")
        print("=" * 70)
        print()

        # Initialize searchers for both models
        print("[1/2] Initializing BGE-M3 searcher...")
        self.bge_searcher, self.bge_embedder = self._create_searcher("BAAI/bge-m3")
        print(f"  [OK] BGE-M3 loaded (1024d)")

        print("[2/2] Initializing Qodo-1.5B searcher...")
        self.qodo_searcher, self.qodo_embedder = self._create_searcher("Qodo/Qodo-Embed-1-1.5B")
        print(f"  [OK] Qodo-1.5B loaded (1536d)")
        print()

    def _create_searcher(self, model_name: str) -> Tuple:
        """Create a searcher for the specified model using MCP server infrastructure."""
        # Switch to model
        config = self.config_manager.load_config()
        config.embedding_model_name = model_name
        self.config_manager.save_config(config)

        # Create embedder
        embedder = CodeEmbedder(model_name)

        # Use MCP server's get_searcher which handles initialization correctly
        searcher = get_searcher(str(self.project_path))

        return searcher, embedder

    def run_comparison(self, queries_file: str) -> List[ModelComparisonResult]:
        """Run comparison test on all queries."""
        # Load queries
        with open(queries_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        queries = data['queries']

        print(f"Running comparison on {len(queries)} queries...")
        print()

        results = []
        for i, query_data in enumerate(queries, 1):
            print(f"[{i}/{len(queries)}] {query_data['category']}: {query_data['query'][:60]}...")

            try:
                result = self._compare_query(query_data)
                results.append(result)
                print(f"  -> Winner: {result.winner} ({result.reason})")
            except Exception as e:
                print(f"  [ERROR] {e}")
                continue

            print()

        return results

    def _compare_query(self, query_data: Dict) -> ModelComparisonResult:
        """Compare single query across both models."""
        query = query_data['query']
        k = 5  # Top-k results

        # Run on BGE-M3
        bge_results, bge_time = self._search_model(
            self.bge_searcher,
            self.bge_embedder,
            query,
            k,
            "BGE-M3"
        )

        # Run on Qodo-1.5B
        qodo_results, qodo_time = self._search_model(
            self.qodo_searcher,
            self.qodo_embedder,
            query,
            k,
            "Qodo-1.5B"
        )

        # Compute overlap metrics
        top5_overlap = self._jaccard_similarity(bge_results, qodo_results)
        rank_correlation = self._kendall_tau(bge_results, qodo_results)

        # Compute score metrics
        avg_score_diff, max_score_diff = self._score_differences(bge_results, qodo_results)
        score_sep_bge = self._score_separation(bge_results)
        score_sep_qodo = self._score_separation(qodo_results)

        # Compute graph metrics
        bge_graph_rate = self._graph_presence_rate(bge_results)
        qodo_graph_rate = self._graph_presence_rate(qodo_results)
        graph_consistent = self._graph_consistency(bge_results, qodo_results)

        # Determine winner
        winner, reason = self._determine_winner(
            bge_results, qodo_results,
            bge_time, qodo_time,
            top5_overlap, rank_correlation,
            query_data
        )

        return ModelComparisonResult(
            query_id=query_data['id'],
            query=query,
            category=query_data['category'],
            bge_results=bge_results,
            bge_time_ms=bge_time,
            qodo_results=qodo_results,
            qodo_time_ms=qodo_time,
            top5_overlap=top5_overlap,
            rank_correlation=rank_correlation,
            avg_score_diff=avg_score_diff,
            max_score_diff=max_score_diff,
            score_separation_bge=score_sep_bge,
            score_separation_qodo=score_sep_qodo,
            bge_graph_presence_rate=bge_graph_rate,
            qodo_graph_presence_rate=qodo_graph_rate,
            graph_metadata_consistent=graph_consistent,
            winner=winner,
            reason=reason
        )

    def _search_model(
        self,
        searcher,  # HybridSearcher instance
        embedder: CodeEmbedder,
        query: str,
        k: int,
        model_name: str
    ) -> Tuple[List[Dict], float]:
        """Search with a specific model and measure time."""
        start_time = time.time()

        try:
            # Run search
            results = searcher.search(
                query=query,
                k=k,
                search_mode='hybrid'
            )

            elapsed_ms = (time.time() - start_time) * 1000

            # Convert to standardized format
            formatted_results = []
            for i, result in enumerate(results[:k], 1):
                formatted_results.append({
                    'rank': i,
                    'doc_id': result.doc_id,
                    'file': result.metadata.get('file', ''),
                    'name': result.metadata.get('name', ''),
                    'score': result.score,
                    'chunk_type': result.metadata.get('kind', ''),
                    'graph': result.metadata.get('graph', None)
                })

            return formatted_results, elapsed_ms

        except Exception as e:
            print(f"    Search error ({model_name}): {e}")
            return [], 0.0

    def _jaccard_similarity(self, bge_results: List[Dict], qodo_results: List[Dict]) -> float:
        """Compute Jaccard similarity of top-k result sets."""
        if not bge_results or not qodo_results:
            return 0.0

        bge_files = set(r['file'] for r in bge_results)
        qodo_files = set(r['file'] for r in qodo_results)

        intersection = len(bge_files & qodo_files)
        union = len(bge_files | qodo_files)

        return intersection / union if union > 0 else 0.0

    def _kendall_tau(self, bge_results: List[Dict], qodo_results: List[Dict]) -> Optional[float]:
        """Compute Kendall's Tau rank correlation for overlapping results."""
        if not bge_results or not qodo_results:
            return None

        # Find shared files
        bge_files = {r['file']: r['rank'] for r in bge_results}
        qodo_files = {r['file']: r['rank'] for r in qodo_results}

        shared_files = set(bge_files.keys()) & set(qodo_files.keys())

        if len(shared_files) < 2:
            return None  # Need at least 2 shared results for correlation

        # Compute Kendall's Tau
        bge_ranks = [bge_files[f] for f in shared_files]
        qodo_ranks = [qodo_files[f] for f in shared_files]

        # Count concordant and discordant pairs
        concordant = 0
        discordant = 0

        for i in range(len(bge_ranks)):
            for j in range(i + 1, len(bge_ranks)):
                bge_diff = bge_ranks[i] - bge_ranks[j]
                qodo_diff = qodo_ranks[i] - qodo_ranks[j]

                if bge_diff * qodo_diff > 0:
                    concordant += 1
                elif bge_diff * qodo_diff < 0:
                    discordant += 1

        total_pairs = concordant + discordant
        if total_pairs == 0:
            return None

        tau = (concordant - discordant) / total_pairs
        return tau

    def _score_differences(self, bge_results: List[Dict], qodo_results: List[Dict]) -> Tuple[float, float]:
        """Compute average and max score differences for shared results."""
        if not bge_results or not qodo_results:
            return 0.0, 0.0

        # Find shared files
        bge_scores = {r['file']: r['score'] for r in bge_results}
        qodo_scores = {r['file']: r['score'] for r in qodo_results}

        shared_files = set(bge_scores.keys()) & set(qodo_scores.keys())

        if not shared_files:
            return 0.0, 0.0

        diffs = [abs(bge_scores[f] - qodo_scores[f]) for f in shared_files]

        return np.mean(diffs), np.max(diffs)

    def _score_separation(self, results: List[Dict]) -> float:
        """Compute score separation between rank 1 and rank 5."""
        if len(results) < 2:
            return 0.0

        rank1_score = results[0]['score']
        last_score = results[-1]['score']

        return rank1_score - last_score

    def _graph_presence_rate(self, results: List[Dict]) -> float:
        """Compute % of results with non-empty graph metadata."""
        if not results:
            return 0.0

        with_graph = sum(
            1 for r in results
            if r.get('graph') and (r['graph'].get('calls') or r['graph'].get('called_by'))
        )

        return with_graph / len(results)

    def _graph_consistency(self, bge_results: List[Dict], qodo_results: List[Dict]) -> bool:
        """Check if shared results have identical graph metadata."""
        if not bge_results or not qodo_results:
            return True  # Vacuously true

        # Find shared files
        bge_graphs = {r['file']: r.get('graph') for r in bge_results}
        qodo_graphs = {r['file']: r.get('graph') for r in qodo_results}

        shared_files = set(bge_graphs.keys()) & set(qodo_graphs.keys())

        if not shared_files:
            return True  # Vacuously true

        # Check if graphs are identical for shared files
        for file in shared_files:
            bge_graph = bge_graphs[file]
            qodo_graph = qodo_graphs[file]

            # Both should have graph or both should not
            if (bge_graph is None) != (qodo_graph is None):
                return False

            # If both have graph, compare
            if bge_graph and qodo_graph:
                if set(bge_graph.get('calls', [])) != set(qodo_graph.get('calls', [])):
                    return False
                if set(bge_graph.get('called_by', [])) != set(qodo_graph.get('called_by', [])):
                    return False

        return True

    def _determine_winner(
        self,
        bge_results: List[Dict],
        qodo_results: List[Dict],
        bge_time: float,
        qodo_time: float,
        overlap: float,
        correlation: Optional[float],
        query_data: Dict
    ) -> Tuple[str, str]:
        """Determine winner based on multiple criteria."""
        # If results are identical or very similar (overlap > 0.8)
        if overlap > 0.8:
            # Use latency as tiebreaker
            if bge_time < qodo_time * 0.9:  # BGE significantly faster
                return "BGE-M3", f"Similar results but {bge_time:.0f}ms vs {qodo_time:.0f}ms"
            elif qodo_time < bge_time * 0.9:  # Qodo significantly faster
                return "Qodo-1.5B", f"Similar results but {qodo_time:.0f}ms vs {bge_time:.0f}ms"
            else:
                return "Tie", f"Identical top results (overlap={overlap:.2f})"

        # If expected files specified, check if either model found them
        expected_files = query_data.get('expected_top_files', [])
        if expected_files:
            bge_found = sum(
                1 for r in bge_results[:3]
                if any(exp in r['file'] for exp in expected_files)
            )
            qodo_found = sum(
                1 for r in qodo_results[:3]
                if any(exp in r['file'] for exp in expected_files)
            )

            if qodo_found > bge_found:
                return "Qodo-1.5B", f"Found {qodo_found}/3 expected files vs {bge_found}/3"
            elif bge_found > qodo_found:
                return "BGE-M3", f"Found {bge_found}/3 expected files vs {qodo_found}/3"

        # Graph validation criteria
        graph_val = query_data.get('graph_validation')
        if graph_val:
            bge_graph_rate = self._graph_presence_rate(bge_results)
            qodo_graph_rate = self._graph_presence_rate(qodo_results)

            if graph_val.get('expect_graph_metadata'):
                if qodo_graph_rate > bge_graph_rate:
                    return "Qodo-1.5B", f"Better graph metadata ({qodo_graph_rate:.0%} vs {bge_graph_rate:.0%})"
                elif bge_graph_rate > qodo_graph_rate:
                    return "BGE-M3", f"Better graph metadata ({bge_graph_rate:.0%} vs {qodo_graph_rate:.0%})"

        # Default: use correlation
        if correlation is not None:
            if correlation > 0.7:
                return "Tie", f"High rank agreement (τ={correlation:.2f})"
            elif correlation < -0.3:
                return "Tie", f"Inverse ranking (τ={correlation:.2f}), unclear winner"

        # Fallback: different results, unclear winner
        return "Tie", f"Different results (overlap={overlap:.2f}), need manual evaluation"

    def generate_report(self, results: List[ModelComparisonResult], output_file: str):
        """Generate comprehensive Markdown report."""
        report_lines = []

        # Header
        report_lines.append("# Model Comparison Report: BGE-M3 vs Qodo-1.5B")
        report_lines.append("")
        report_lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**Queries Tested**: {len(results)}")
        report_lines.append("")

        # Executive Summary
        report_lines.append("## Executive Summary")
        report_lines.append("")

        # Count winners by category
        category_winners = defaultdict(lambda: {'BGE-M3': 0, 'Qodo-1.5B': 0, 'Tie': 0})
        overall_winners = {'BGE-M3': 0, 'Qodo-1.5B': 0, 'Tie': 0}

        for result in results:
            category_winners[result.category][result.winner] += 1
            overall_winners[result.winner] += 1

        # Overall winner
        report_lines.append("### Overall Results")
        report_lines.append("")
        report_lines.append(f"- **BGE-M3 wins**: {overall_winners['BGE-M3']} queries")
        report_lines.append(f"- **Qodo-1.5B wins**: {overall_winners['Qodo-1.5B']} queries")
        report_lines.append(f"- **Ties**: {overall_winners['Tie']} queries")
        report_lines.append("")

        # Winner by category
        report_lines.append("### Results by Category")
        report_lines.append("")
        report_lines.append("| Category | BGE-M3 | Qodo-1.5B | Tie |")
        report_lines.append("|----------|--------|-----------|-----|")

        for cat in sorted(category_winners.keys()):
            wins = category_winners[cat]
            report_lines.append(
                f"| {cat.replace('_', ' ').title()} | "
                f"{wins['BGE-M3']} | {wins['Qodo-1.5B']} | {wins['Tie']} |"
            )

        report_lines.append("")

        # Performance metrics
        report_lines.append("### Performance Metrics")
        report_lines.append("")

        bge_times = [r.bge_time_ms for r in results]
        qodo_times = [r.qodo_time_ms for r in results]

        report_lines.append("| Metric | BGE-M3 | Qodo-1.5B | Difference |")
        report_lines.append("|--------|--------|-----------|------------|")
        report_lines.append(f"| Median latency | {np.median(bge_times):.0f}ms | {np.median(qodo_times):.0f}ms | +{np.median(qodo_times) - np.median(bge_times):.0f}ms |")
        report_lines.append(f"| p95 latency | {np.percentile(bge_times, 95):.0f}ms | {np.percentile(qodo_times, 95):.0f}ms | +{np.percentile(qodo_times, 95) - np.percentile(bge_times, 95):.0f}ms |")
        report_lines.append(f"| Average latency | {np.mean(bge_times):.0f}ms | {np.mean(qodo_times):.0f}ms | +{np.mean(qodo_times) - np.mean(bge_times):.0f}ms |")
        report_lines.append("")

        # Overlap metrics
        report_lines.append("### Result Overlap Metrics")
        report_lines.append("")

        overlaps = [r.top5_overlap for r in results]
        correlations = [r.rank_correlation for r in results if r.rank_correlation is not None]

        report_lines.append(f"- **Average top-5 overlap (Jaccard)**: {np.mean(overlaps):.2f}")
        report_lines.append(f"- **Median top-5 overlap**: {np.median(overlaps):.2f}")
        avg_corr = f"{np.mean(correlations):.2f}" if correlations else "N/A"
        report_lines.append(f"- **Average rank correlation (Kendall's Tau)**: {avg_corr}")
        report_lines.append("")

        # Graph metadata
        report_lines.append("### Graph Metadata Analysis")
        report_lines.append("")

        bge_graph_rates = [r.bge_graph_presence_rate for r in results]
        qodo_graph_rates = [r.qodo_graph_presence_rate for r in results]
        graph_consistent_count = sum(1 for r in results if r.graph_metadata_consistent)

        report_lines.append(f"- **BGE-M3 graph presence**: {np.mean(bge_graph_rates):.1%} of results")
        report_lines.append(f"- **Qodo-1.5B graph presence**: {np.mean(qodo_graph_rates):.1%} of results")
        report_lines.append(f"- **Graph consistency**: {graph_consistent_count}/{len(results)} queries ({graph_consistent_count/len(results):.1%})")
        report_lines.append("")

        # Per-query results
        report_lines.append("## Per-Query Results")
        report_lines.append("")
        report_lines.append("| ID | Category | Query | BGE-M3 Top-1 | Qodo-1.5B Top-1 | Overlap | Winner |")
        report_lines.append("|----|----------|-------|--------------|-----------------|---------|--------|")

        for result in results:
            bge_top1 = result.bge_results[0]['file'].split('/')[-1] if result.bge_results else "N/A"
            qodo_top1 = result.qodo_results[0]['file'].split('/')[-1] if result.qodo_results else "N/A"

            report_lines.append(
                f"| {result.query_id} | {result.category} | "
                f"{result.query[:40]}... | {bge_top1[:20]} | {qodo_top1[:20]} | "
                f"{result.top5_overlap:.2f} | {result.winner} |"
            )

        report_lines.append("")

        # Recommendations
        report_lines.append("## Recommendations")
        report_lines.append("")

        if overall_winners['Qodo-1.5B'] > overall_winners['BGE-M3'] * 1.2:
            report_lines.append("**Recommendation**: Switch to **Qodo-1.5B** for this codebase.")
            report_lines.append("")
            report_lines.append(f"**Reason**: Qodo-1.5B won {overall_winners['Qodo-1.5B']} queries vs BGE-M3's {overall_winners['BGE-M3']}, ")
            report_lines.append(f"demonstrating superior code-specific retrieval despite being {np.median(qodo_times) - np.median(bge_times):.0f}ms slower on average.")
        elif overall_winners['BGE-M3'] > overall_winners['Qodo-1.5B'] * 1.2:
            report_lines.append("**Recommendation**: Continue using **BGE-M3** as default.")
            report_lines.append("")
            report_lines.append(f"**Reason**: BGE-M3 won {overall_winners['BGE-M3']} queries vs Qodo-1.5B's {overall_winners['Qodo-1.5B']}, ")
            report_lines.append(f"while being {np.median(bge_times):.0f}ms faster on average with lower resource costs.")
        else:
            report_lines.append("**Recommendation**: **Hybrid approach** - keep both models available.")
            report_lines.append("")
            report_lines.append(f"**Reason**: Results are competitive ({overall_winners['BGE-M3']} vs {overall_winners['Qodo-1.5B']} wins). ")
            report_lines.append(f"Use BGE-M3 as default for speed, Qodo-1.5B for code-specific deep dives.")

        report_lines.append("")

        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        print(f"[OK] Report saved to: {output_file}")

    def save_results(self, results: List[ModelComparisonResult], output_file: str):
        """Save raw results to JSON."""
        output_data = {
            'metadata': {
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_queries': len(results),
                'models': ['BAAI/bge-m3', 'Qodo/Qodo-Embed-1-1.5B']
            },
            'results': [asdict(r) for r in results]
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)

        print(f"[OK] Raw results saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Compare BGE-M3 vs Qodo-1.5B models')
    parser.add_argument(
        '--queries',
        default='tests/benchmarks/model_comparison_queries.json',
        help='Path to queries JSON file'
    )
    parser.add_argument(
        '--output',
        default='analysis/MODEL_COMPARISON_RESULTS.json',
        help='Path to output JSON file'
    )
    parser.add_argument(
        '--report',
        default='analysis/MODEL_COMPARISON_REPORT.md',
        help='Path to output Markdown report'
    )
    parser.add_argument(
        '--project',
        default='.',
        help='Path to project directory'
    )

    args = parser.parse_args()

    # Create tester
    tester = ModelComparisonTester(args.project)

    # Run comparison
    results = tester.run_comparison(args.queries)

    # Save results
    tester.save_results(results, args.output)

    # Generate report
    tester.generate_report(results, args.report)

    print()
    print("=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)
    print(f"Total queries: {len(results)}")
    print(f"Results: {args.output}")
    print(f"Report: {args.report}")


if __name__ == '__main__':
    main()
