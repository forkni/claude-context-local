"""SWE-bench evaluation dataset integration and runner."""

import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_evaluator import EvaluationInstance
from .semantic_evaluator import BM25OnlyEvaluator, SemanticSearchEvaluator


class SWEBenchDatasetLoader:
    """Loader for SWE-bench evaluation datasets."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def load_swe_bench_lite(
        self, dataset_path: Optional[str] = None, max_instances: Optional[int] = None
    ) -> List[EvaluationInstance]:
        """
        Load SWE-bench Lite dataset.

        Args:
            dataset_path: Path to dataset file (downloads if None)
            max_instances: Maximum number of instances to load

        Returns:
            List of evaluation instances
        """
        if dataset_path is None:
            dataset_path = self._download_swe_bench_lite()

        return self._load_dataset_file(dataset_path, max_instances)

    def create_custom_subset(
        self,
        instances: List[Dict[str, Any]],
        output_path: str,
        criteria: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a custom subset of SWE-bench instances.

        Args:
            instances: List of SWE-bench instances
            output_path: Path to save subset
            criteria: Filtering criteria

        Returns:
            Path to created subset file
        """
        if criteria is None:
            criteria = {
                "max_files_modified": 3,
                "min_difficulty": "easy",
                "max_difficulty": "medium",
            }

        filtered_instances = []
        for instance in instances:
            if self._matches_criteria(instance, criteria):
                filtered_instances.append(instance)

        # Create dataset structure
        dataset = {
            "metadata": {
                "created_from": "SWE-bench",
                "criteria": criteria,
                "total_instances": len(filtered_instances),
                "statistics": self._calculate_stats(filtered_instances),
            },
            "instances": filtered_instances,
        }

        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)

        self.logger.info(
            f"Created subset with {len(filtered_instances)} instances at {output_path}"
        )
        return str(output_file)

    def _download_swe_bench_lite(self) -> str:
        """Download SWE-bench Lite dataset."""
        try:
            # Try to use datasets library if available
            from datasets import load_dataset

            dataset = load_dataset("princeton-nlp/SWE-bench_Lite")

            # Save to local file for consistency
            temp_dir = tempfile.mkdtemp()
            dataset_path = os.path.join(temp_dir, "swe_bench_lite.json")

            # Convert to our format
            instances = []
            for item in dataset["test"]:
                instances.append(dict(item))

            with open(dataset_path, "w", encoding="utf-8") as f:
                json.dump(instances, f, indent=2)

            self.logger.info(f"Downloaded SWE-bench Lite to {dataset_path}")
            return dataset_path

        except ImportError:
            self.logger.warning(
                "datasets library not available. Using local sample dataset."
            )
            # Use local sample dataset as fallback
            sample_path = Path(__file__).parent / "datasets" / "swe_bench_sample.json"
            if sample_path.exists():
                self.logger.info(f"Using fallback dataset: {sample_path}")
                return str(sample_path)
            else:
                self.logger.error("No fallback dataset available.")
                raise ImportError(
                    "Install 'datasets' library for full SWE-bench support: pip install datasets"
                )

    def _load_dataset_file(
        self, dataset_path: str, max_instances: Optional[int]
    ) -> List[EvaluationInstance]:
        """Load dataset from file and convert to evaluation instances."""
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle different formats
        if isinstance(data, dict) and "instances" in data:
            raw_instances = data["instances"]
        elif isinstance(data, list):
            raw_instances = data
        else:
            raw_instances = [data]

        # Limit if requested
        if max_instances and len(raw_instances) > max_instances:
            raw_instances = raw_instances[:max_instances]

        # Convert to evaluation instances
        instances = []
        for item in raw_instances:
            instance = self._convert_to_evaluation_instance(item)
            if instance:
                instances.append(instance)

        self.logger.info(f"Loaded {len(instances)} evaluation instances")
        return instances

    def _convert_to_evaluation_instance(
        self, swe_item: Dict[str, Any]
    ) -> Optional[EvaluationInstance]:
        """Convert SWE-bench item to evaluation instance."""
        try:
            # Extract query from problem statement
            problem_statement = swe_item.get("problem_statement", "")
            if not problem_statement:
                return None

            # Extract modified files as ground truth
            patch = swe_item.get("patch", "")
            ground_truth_files = self._extract_modified_files_from_patch(patch)

            # Create evaluation instance
            instance = EvaluationInstance(
                instance_id=swe_item.get("instance_id", ""),
                query=problem_statement,
                ground_truth_files=ground_truth_files,
                ground_truth_content=patch,
                metadata={
                    "repo": swe_item.get("repo", ""),
                    "base_commit": swe_item.get("base_commit", ""),
                    "created_at": swe_item.get("created_at", ""),
                    "difficulty": swe_item.get("difficulty", "unknown"),
                },
            )

            return instance

        except Exception as e:
            self.logger.warning(f"Failed to convert instance: {e}")
            return None

    def _extract_modified_files_from_patch(self, patch: str) -> List[str]:
        """Extract modified file paths from git patch."""
        files = []
        if not patch:
            return files

        # Regular expression to match file paths in git diff format
        file_pattern = re.compile(r"^(?:\+\+\+|---) [ab]/(.+)$", re.MULTILINE)
        matches = file_pattern.findall(patch)

        # Remove duplicates and filter out /dev/null
        seen = set()
        for match in matches:
            if match != "/dev/null" and match not in seen:
                files.append(match)
                seen.add(match)

        return files

    def _matches_criteria(
        self, instance: Dict[str, Any], criteria: Dict[str, Any]
    ) -> bool:
        """Check if instance matches filtering criteria."""
        # Check number of modified files
        patch = instance.get("patch", "")
        modified_files = self._extract_modified_files_from_patch(patch)
        max_files = criteria.get("max_files_modified", float("inf"))

        if len(modified_files) > max_files:
            return False

        # Add more criteria as needed
        return True

    def _calculate_stats(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for the dataset."""
        if not instances:
            return {}

        repos = [inst.get("repo", "") for inst in instances]
        repo_counts = {}
        for repo in repos:
            repo_counts[repo] = repo_counts.get(repo, 0) + 1

        return {
            "total_instances": len(instances),
            "unique_repos": len(set(repos)),
            "top_repos": sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)[
                :5
            ],
        }


class SWEBenchEvaluationRunner:
    """Runner for SWE-bench evaluations."""

    def __init__(self, output_dir: str, temp_dir: Optional[str] = None):
        """
        Initialize evaluation runner.

        Args:
            output_dir: Output directory for results
            temp_dir: Temporary directory for repositories
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = temp_dir or str(self.output_dir / "temp_repos")
        self.logger = logging.getLogger(self.__class__.__name__)

    def run_comparison_evaluation(
        self,
        instances: List[EvaluationInstance],
        k: int = 10,
        max_instances: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run comparison evaluation between different search methods.

        Args:
            instances: List of evaluation instances
            k: Number of top results to consider
            max_instances: Maximum instances to evaluate

        Returns:
            Comparison results
        """
        self.logger.info("Starting SWE-bench comparison evaluation")

        if max_instances and len(instances) > max_instances:
            instances = instances[:max_instances]

        # Define evaluators to compare
        evaluators = {
            "hybrid_search": SemanticSearchEvaluator(
                output_dir=str(self.output_dir / "hybrid"),
                k=k,
                bm25_weight=0.4,
                dense_weight=0.6,
            ),
            "bm25_only": BM25OnlyEvaluator(
                output_dir=str(self.output_dir / "bm25_only"), k=k
            ),
            "dense_only": SemanticSearchEvaluator(
                output_dir=str(self.output_dir / "dense_only"),
                k=k,
                bm25_weight=0.0,
                dense_weight=1.0,
            ),
        }

        comparison_results = {
            "metadata": {
                "total_instances": len(instances),
                "k": k,
                "evaluators": list(evaluators.keys()),
            },
            "results_by_method": {},
        }

        # Run evaluation for each method
        for method_name, evaluator in evaluators.items():
            self.logger.info(f"Running evaluation with {method_name}")

            try:
                # For SWE-bench, we need to evaluate on a per-repository basis
                method_results = self._run_method_evaluation(
                    evaluator, instances, method_name
                )
                comparison_results["results_by_method"][method_name] = method_results

            except Exception as e:
                self.logger.error(f"Error running {method_name} evaluation: {e}")
                comparison_results["results_by_method"][method_name] = {
                    "error": str(e),
                    "aggregate_metrics": {},
                }
            finally:
                # Cleanup
                evaluator.cleanup()

        # Calculate comparative metrics
        comparison_results["comparison"] = self._calculate_comparison_metrics(
            comparison_results["results_by_method"]
        )

        # Save comparison results
        self._save_comparison_results(comparison_results)

        self.logger.info("SWE-bench comparison evaluation completed")
        return comparison_results

    def _run_method_evaluation(
        self,
        evaluator: SemanticSearchEvaluator,
        instances: List[EvaluationInstance],
        method_name: str,
    ) -> Dict[str, Any]:
        """Run evaluation for a specific method."""
        # Group instances by repository
        repo_instances = {}
        for instance in instances:
            repo = instance.metadata.get("repo", "unknown")
            if repo not in repo_instances:
                repo_instances[repo] = []
            repo_instances[repo].append(instance)

        all_results = []

        # Evaluate each repository
        for repo, repo_instances_list in repo_instances.items():
            self.logger.info(f"Evaluating {method_name} on repository: {repo}")

            try:
                # Clone or create mock repository
                repo_path = self._prepare_repository(repo, repo_instances_list[0])

                if repo_path:
                    # Run evaluation on this repository
                    repo_results = evaluator.run_evaluation(
                        repo_instances_list, repo_path
                    )
                    all_results.append(repo_results)

            except Exception as e:
                self.logger.warning(f"Failed to evaluate repository {repo}: {e}")

        # Aggregate results across repositories
        if all_results:
            return self._aggregate_repository_results(all_results)
        else:
            return {"aggregate_metrics": {}, "results_by_instance": {}}

    def _prepare_repository(
        self, repo: str, sample_instance: EvaluationInstance
    ) -> Optional[str]:
        """Prepare repository for evaluation (mock or clone)."""
        # For this example, we'll create a simple mock repository
        # In a full implementation, you would clone the actual repository

        repo_dir = Path(self.temp_dir) / repo.replace("/", "_")
        repo_dir.mkdir(parents=True, exist_ok=True)

        # Create some sample Python files to demonstrate the evaluation
        sample_files = {
            "main.py": '''
def main():
    """Main entry point for the application."""
    print("Hello, World!")
    return 0

if __name__ == "__main__":
    main()
''',
            "utils.py": '''
def helper_function(x, y):
    """A helper function that adds two numbers."""
    return x + y

def process_data(data):
    """Process data and return results."""
    return [item * 2 for item in data]
''',
            "models.py": '''
class User:
    """User model class."""
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def get_display_name(self):
        return f"{self.name} <{self.email}>"
''',
        }

        # Write sample files
        for filename, content in sample_files.items():
            file_path = repo_dir / filename
            file_path.write_text(content, encoding="utf-8")

        self.logger.debug(f"Prepared mock repository at {repo_dir}")
        return str(repo_dir)

    def _aggregate_repository_results(
        self, repo_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate results across multiple repositories."""
        if not repo_results:
            return {"aggregate_metrics": {}, "results_by_instance": {}}

        # Combine all instance results
        combined_results = {}
        all_instances = []

        for repo_result in repo_results:
            # Combine instance results
            repo_instances = repo_result.get("results_by_instance", {})
            combined_results.update(repo_instances)

            # Collect metrics from all instances for aggregation
            for instance_data in repo_instances.values():
                all_instances.append(instance_data.get("metrics", {}))

        # Calculate aggregate metrics across all repositories
        aggregate_metrics = self._calculate_cross_repo_metrics(all_instances)

        return {
            "aggregate_metrics": aggregate_metrics,
            "results_by_instance": combined_results,
            "repository_count": len(repo_results),
        }

    def _calculate_cross_repo_metrics(
        self, instance_metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate metrics aggregated across repositories."""
        if not instance_metrics:
            return {}

        # Extract metric values
        precisions = [m.get("precision", 0.0) for m in instance_metrics]
        recalls = [m.get("recall", 0.0) for m in instance_metrics]
        f1_scores = [m.get("f1_score", 0.0) for m in instance_metrics]
        query_times = [m.get("query_time", 0.0) for m in instance_metrics]

        return {
            "precision_mean": sum(precisions) / len(precisions) if precisions else 0.0,
            "recall_mean": sum(recalls) / len(recalls) if recalls else 0.0,
            "f1_score_mean": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0,
            "query_time_mean": sum(query_times) / len(query_times)
            if query_times
            else 0.0,
            "total_instances": len(instance_metrics),
        }

    def _calculate_comparison_metrics(
        self, results_by_method: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate comparative metrics between methods."""
        comparison = {}

        # Extract aggregate metrics for each method
        method_metrics = {}
        for method, results in results_by_method.items():
            agg_metrics = results.get("aggregate_metrics", {})
            method_metrics[method] = agg_metrics

        # Compare methods
        if "hybrid_search" in method_metrics and "bm25_only" in method_metrics:
            hybrid = method_metrics["hybrid_search"]
            bm25 = method_metrics["bm25_only"]

            comparison["hybrid_vs_bm25"] = {
                "f1_improvement": self._safe_divide(
                    hybrid.get("f1_score_mean", 0) - bm25.get("f1_score_mean", 0),
                    bm25.get("f1_score_mean", 1),
                ),
                "precision_improvement": self._safe_divide(
                    hybrid.get("precision_mean", 0) - bm25.get("precision_mean", 0),
                    bm25.get("precision_mean", 1),
                ),
                "recall_improvement": self._safe_divide(
                    hybrid.get("recall_mean", 0) - bm25.get("recall_mean", 0),
                    bm25.get("recall_mean", 1),
                ),
            }

        return comparison

    def _safe_divide(self, numerator: float, denominator: float) -> float:
        """Safe division that handles zero denominators."""
        if denominator == 0:
            return 0.0
        return numerator / denominator

    def _save_comparison_results(self, results: Dict[str, Any]) -> None:
        """Save comparison results to disk."""
        # Save detailed results
        results_file = self.output_dir / "swe_bench_comparison.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        # Save summary report
        self._generate_comparison_report(results)

        self.logger.info(f"Comparison results saved to {results_file}")

    def _generate_comparison_report(self, results: Dict[str, Any]) -> None:
        """Generate human-readable comparison report."""
        report_lines = [
            "=" * 80,
            "SWE-BENCH EVALUATION COMPARISON REPORT",
            "=" * 80,
            "",
            f"Total Instances: {results['metadata']['total_instances']}",
            f"Top-K Results: {results['metadata']['k']}",
            f"Methods Compared: {', '.join(results['metadata']['evaluators'])}",
            "",
            "PERFORMANCE BY METHOD",
            "-" * 40,
        ]

        # Add method results
        for method, method_results in results["results_by_method"].items():
            agg_metrics = method_results.get("aggregate_metrics", {})

            report_lines.extend(
                [
                    "",
                    f"{method.upper().replace('_', ' ')}:",
                    f"  Precision: {agg_metrics.get('precision_mean', 0.0):.3f}",
                    f"  Recall: {agg_metrics.get('recall_mean', 0.0):.3f}",
                    f"  F1-Score: {agg_metrics.get('f1_score_mean', 0.0):.3f}",
                    f"  Query Time: {agg_metrics.get('query_time_mean', 0.0):.3f}s",
                ]
            )

        # Add comparison insights
        comparison = results.get("comparison", {})
        if comparison:
            report_lines.extend(
                [
                    "",
                    "COMPARATIVE ANALYSIS",
                    "-" * 40,
                ]
            )

            hybrid_vs_bm25 = comparison.get("hybrid_vs_bm25", {})
            if hybrid_vs_bm25:
                report_lines.extend(
                    [
                        "Hybrid vs BM25-Only:",
                        f"  F1 Improvement: {hybrid_vs_bm25.get('f1_improvement', 0.0):.1%}",
                        f"  Precision Improvement: {hybrid_vs_bm25.get('precision_improvement', 0.0):.1%}",
                        f"  Recall Improvement: {hybrid_vs_bm25.get('recall_improvement', 0.0):.1%}",
                    ]
                )

        report_lines.extend(["", "=" * 80])

        # Save report
        report_file = self.output_dir / "swe_bench_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        self.logger.info(f"Comparison report saved to {report_file}")

    def cleanup(self) -> None:
        """Clean up temporary files."""
        try:
            temp_path = Path(self.temp_dir)
            if temp_path.exists():
                shutil.rmtree(temp_path)
                self.logger.info("Cleaned up temporary repositories")
        except Exception as e:
            self.logger.warning(f"Failed to clean up temporary files: {e}")
