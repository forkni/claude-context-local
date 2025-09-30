"""Parameter optimizer for hybrid search - codebase-specific tuning."""

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from evaluation.base_evaluator import EvaluationInstance
from evaluation.semantic_evaluator import SemanticSearchEvaluator


class ParameterOptimizer:
    """Optimize hybrid search parameters for a specific codebase."""

    def __init__(
        self,
        project_path: str,
        dataset_path: str,
        output_dir: str = "benchmark_results/tuning",
        k: int = 5,
        max_instances: Optional[int] = None,
    ):
        """
        Initialize parameter optimizer.

        Args:
            project_path: Path to project to optimize for
            dataset_path: Path to evaluation dataset
            output_dir: Directory for tuning results
            k: Number of top results to consider
            max_instances: Maximum evaluation instances
        """
        self.project_path = project_path
        self.dataset_path = dataset_path
        self.output_dir = Path(output_dir)
        self.k = k
        self.max_instances = max_instances

        self.logger = logging.getLogger(__name__)
        self.evaluator: Optional[SemanticSearchEvaluator] = None
        self.instances: List[Dict] = []

    def cleanup_old_results(self) -> None:
        """Remove old tuning results to start fresh."""
        if self.output_dir.exists():
            self.logger.info(f"Cleaning up old tuning results: {self.output_dir}")
            shutil.rmtree(self.output_dir)
            print("[CLEANUP] Removed old tuning results")
        else:
            print("[CLEANUP] No old results to clean")

    def build_index_once(
        self, bm25_weight: float = 0.4, dense_weight: float = 0.6, rrf_k: int = 60
    ) -> None:
        """
        Build search index once for reuse across parameter tests.

        Args:
            bm25_weight: Initial BM25 weight
            dense_weight: Initial dense weight
            rrf_k: Initial RRF k parameter
        """
        self.logger.info(f"Building index for project: {self.project_path}")
        print("\n[BUILD] Indexing project (one-time, ~90-100s)...")

        # Create evaluator with initial parameters
        eval_output_dir = self.output_dir / "shared_index"
        eval_output_dir.mkdir(parents=True, exist_ok=True)

        self.evaluator = SemanticSearchEvaluator(
            output_dir=str(eval_output_dir),
            k=self.k,
            bm25_weight=bm25_weight,
            dense_weight=dense_weight,
            rrf_k=rrf_k,
        )

        # Build index
        start_time = time.time()
        self.evaluator.build_index(self.project_path)
        build_time = time.time() - start_time

        print(f"[BUILD] Index built in {build_time:.1f}s")
        self.logger.info(f"Index built in {build_time:.2f}s")

        # Load evaluation dataset
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        self.instances = dataset.get("instances", [])
        if self.max_instances:
            self.instances = self.instances[: self.max_instances]

        print(f"[BUILD] Loaded {len(self.instances)} evaluation queries\n")

    def test_configuration(
        self, bm25_weight: float, dense_weight: float, rrf_k: int = 60
    ) -> Dict:
        """
        Test a specific parameter configuration.

        Args:
            bm25_weight: BM25 weight to test
            dense_weight: Dense weight to test
            rrf_k: RRF k parameter

        Returns:
            Dict with configuration and performance metrics
        """
        if not self.evaluator or not self.evaluator.hybrid_searcher:
            raise RuntimeError("Index not built. Call build_index_once() first.")

        # Update parameters without rebuilding index
        self.evaluator.bm25_weight = bm25_weight
        self.evaluator.dense_weight = dense_weight
        self.evaluator.rrf_k = rrf_k

        # Update hybrid searcher parameters
        searcher = self.evaluator.hybrid_searcher
        searcher.bm25_weight = bm25_weight
        searcher.dense_weight = dense_weight
        searcher.reranker.k = rrf_k

        self.logger.info(
            f"Testing config: BM25={bm25_weight}, Dense={dense_weight}, RRF_k={rrf_k}"
        )

        # Verify weights are actually set
        self.logger.debug(
            f"[VERIFY] Searcher weights after update: BM25={searcher.bm25_weight}, "
            f"Dense={searcher.dense_weight}, RRF_k={searcher.reranker.k}"
        )

        # Convert dict instances to EvaluationInstance objects
        eval_instances = []
        for inst in self.instances:
            if isinstance(inst, dict):
                eval_instances.append(
                    EvaluationInstance(
                        instance_id=inst["instance_id"],
                        query=inst["query"],
                        ground_truth_files=inst["ground_truth_files"],
                        ground_truth_content=inst.get("ground_truth_content", ""),
                        metadata=inst.get("metadata", {}),
                    )
                )
            else:
                eval_instances.append(inst)

        # Evaluate queries directly without rebuilding index
        start_time = time.time()

        all_metrics = []
        for idx, instance in enumerate(eval_instances):
            metrics = self.evaluator.evaluate_single_query(instance, self.project_path)
            all_metrics.append(metrics)

            # Log first query results to verify weights affect output
            if idx == 0:
                self.logger.debug(
                    f"[FIRST_QUERY] Instance: {instance.instance_id}, "
                    f"Precision: {metrics.precision:.3f}, Recall: {metrics.recall:.3f}"
                )

        eval_time = time.time() - start_time

        # Calculate aggregate metrics
        if all_metrics:
            precision_vals = [m.precision for m in all_metrics]
            recall_vals = [m.recall for m in all_metrics]
            f1_vals = [m.f1_score for m in all_metrics]
            time_vals = [m.query_time for m in all_metrics]

            mean_precision = sum(precision_vals) / len(precision_vals)
            mean_recall = sum(recall_vals) / len(recall_vals)
            mean_f1 = sum(f1_vals) / len(f1_vals)
            mean_time = sum(time_vals) / len(time_vals)
        else:
            mean_precision = mean_recall = mean_f1 = mean_time = 0.0

        return {
            "config": {
                "bm25_weight": bm25_weight,
                "dense_weight": dense_weight,
                "rrf_k": rrf_k,
            },
            "metrics": {
                "precision": mean_precision,
                "recall": mean_recall,
                "f1_score": mean_f1,
                "query_time": mean_time,
            },
            "eval_time": eval_time,
        }

    def optimize(
        self,
        weight_pairs: Optional[List[Tuple[float, float]]] = None,
        rrf_k: int = 60,
    ) -> Dict:
        """
        Run optimization across parameter configurations.

        Args:
            weight_pairs: List of (bm25_weight, dense_weight) tuples to test
            rrf_k: RRF k parameter (fixed for now)

        Returns:
            Dict with all results and best configuration
        """
        # Default to 3 strategic configurations
        if weight_pairs is None:
            weight_pairs = [
                (0.3, 0.7),  # Heavy semantic
                (0.4, 0.6),  # Current default
                (0.6, 0.4),  # Keyword-focused
            ]

        results = []
        total_configs = len(weight_pairs)

        print(f"{'=' * 80}")
        print("HYBRID SEARCH PARAMETER OPTIMIZATION")
        print(f"{'=' * 80}")
        print(f"Project: {self.project_path}")
        print(f"Testing {total_configs} configurations\n")

        for i, (bm25_w, dense_w) in enumerate(weight_pairs, 1):
            print(
                f"[{i}/{total_configs}] Testing BM25={bm25_w}, Dense={dense_w}...",
                end=" ",
            )

            try:
                result = self.test_configuration(bm25_w, dense_w, rrf_k)
                result["status"] = "ok"  # Mark as successful
                results.append(result)

                metrics = result["metrics"]
                f1 = metrics["f1_score"]
                print(f"F1={f1:.3f}")
                self.logger.info(
                    f"Config {i}: F1={f1:.3f}, P={metrics['precision']:.3f}, R={metrics['recall']:.3f}"
                )

            except Exception as e:
                self.logger.error(f"Failed to test config {i}: {e}")
                print(f"FAILED: {e}")
                # Add failed result with status
                results.append(
                    {
                        "config": {
                            "bm25_weight": bm25_w,
                            "dense_weight": dense_w,
                            "rrf_k": rrf_k,
                        },
                        "metrics": {
                            "f1_score": 0.0,
                            "precision": 0.0,
                            "recall": 0.0,
                            "query_time": 0.0,
                        },
                        "status": "failed",
                        "error": str(e),
                    }
                )

        # Find best configuration (F1 primary, query_time tie-breaker)
        # Only consider successful results
        successful_results = [r for r in results if r.get("status") != "failed"]
        if not successful_results:
            raise RuntimeError("All configurations failed testing")

        best_result = max(
            successful_results,
            key=lambda x: (x["metrics"]["f1_score"], -x["metrics"]["query_time"]),
        )

        return {
            "all_results": results,
            "best_config": best_result,
            "total_tested": len(results),
        }

    def generate_report(
        self, optimization_results: Dict, current_f1: Optional[float] = None
    ) -> str:
        """
        Generate human-readable optimization report.

        Args:
            optimization_results: Results from optimize()
            current_f1: Current F1-score for comparison (optional)

        Returns:
            Formatted report string
        """
        results = optimization_results["all_results"]
        best = optimization_results["best_config"]
        best_config = best["config"]
        best_metrics = best["metrics"]

        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("OPTIMIZATION RESULTS")
        lines.append("=" * 80)
        lines.append("")

        # Comparison table
        lines.append("Configuration Comparison:")
        lines.append("-" * 80)
        lines.append(
            f"{'BM25/Dense':<15} {'F1-Score':<12} {'Precision':<12} {'Recall':<12} {'Query(s)':<10} {'Status'}"
        )
        lines.append("-" * 80)

        best_f1 = best_metrics["f1_score"]
        best_weights = (
            f"{best_config['bm25_weight']:.1f}/{best_config['dense_weight']:.1f}"
        )

        # Check if there are tied F1 scores
        tied_configs = [
            r for r in results if abs(r["metrics"]["f1_score"] - best_f1) < 0.001
        ]
        has_tie = len(tied_configs) > 1

        for result in sorted(
            results, key=lambda x: x["metrics"]["f1_score"], reverse=True
        ):
            cfg = result["config"]
            met = result["metrics"]
            weights = f"{cfg['bm25_weight']:.1f}/{cfg['dense_weight']:.1f}"
            f1 = met["f1_score"]
            query_time = met["query_time"]

            # Determine status based on test result
            if result.get("status") == "failed":
                status = "[FAILED]"
            elif weights == best_weights:
                status = "[BEST]"
            else:
                status = "[OK]"

            lines.append(
                f"{weights:<15} {f1:<12.3f} {met['precision']:<12.3f} {met['recall']:<12.3f} {query_time:<10.3f} {status}"
            )

        lines.append("")

        # Explain tie-breaking if applicable
        if has_tie:
            lines.append(f"NOTE: Multiple configurations achieved F1={best_f1:.3f}")
            lines.append("      Tie broken by query time (faster is better)")
            lines.append("")

        # Best configuration
        lines.append("RECOMMENDED CONFIGURATION:")
        lines.append("-" * 80)
        lines.append(f"  bm25_weight: {best_config['bm25_weight']}")
        lines.append(f"  dense_weight: {best_config['dense_weight']}")
        lines.append(f"  rrf_k: {best_config['rrf_k']}")
        lines.append("")
        lines.append(f"  Expected F1-Score: {best_metrics['f1_score']:.3f}")
        lines.append(f"  Expected Precision: {best_metrics['precision']:.3f}")
        lines.append(f"  Expected Recall: {best_metrics['recall']:.3f}")
        lines.append(f"  Avg Query Time: {best_metrics['query_time']:.3f}s")

        # Comparison with current
        if current_f1 is not None:
            lines.append("")
            if best_metrics["f1_score"] > current_f1:
                improvement = (
                    (best_metrics["f1_score"] - current_f1) / current_f1
                ) * 100
                lines.append(
                    f"[OK] IMPROVEMENT: +{improvement:.1f}% over current settings"
                )
                lines.append("")
                lines.append(
                    "ACTION: Update hybrid_searcher.py with recommended values"
                )
            elif abs(best_metrics["f1_score"] - current_f1) < 0.001:
                lines.append("[OK] Current settings are already optimal!")
            else:
                lines.append("[INFO] Current settings perform similarly")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def save_results(self, optimization_results: Dict, report: str) -> None:
        """Save optimization results and report to files."""
        output_file = self.output_dir / "optimization_results.json"
        report_file = self.output_dir / "optimization_report.txt"

        # Save JSON results
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(optimization_results, f, indent=2)

        # Save text report
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n[SAVED] Results: {output_file}")
        print(f"[SAVED] Report: {report_file}")
