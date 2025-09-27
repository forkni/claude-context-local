"""Token efficiency evaluation for MCP semantic search vs vanilla file reading."""

import json
import logging
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tiktoken

from .base_evaluator import (
    BaseEvaluator,
    EvaluationInstance,
    RetrievalResult,
    SearchMetrics,
)


@dataclass
class TokenEfficiencyMetrics:
    """Token efficiency comparison metrics."""

    search_tokens: int
    vanilla_read_tokens: int
    token_savings: int
    efficiency_ratio: float  # search_tokens / vanilla_read_tokens
    percentage_savings: float  # (vanilla - search) / vanilla * 100
    search_time: float
    read_time: float
    time_savings: float
    files_avoided: int  # Number of files that didn't need to be read


@dataclass
class TokenEfficiencyResult:
    """Complete token efficiency evaluation result."""

    scenario_id: str
    query: str
    search_metrics: SearchMetrics
    efficiency_metrics: TokenEfficiencyMetrics
    search_results: List[RetrievalResult]
    simulated_files: List[str]  # Files that would be read in vanilla approach
    metadata: Dict[str, Any]


class TokenCounter:
    """Utility class for counting tokens using tiktoken."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        """Initialize token counter.

        Args:
            encoding_name: tiktoken encoding to use (cl100k_base for GPT-4/Claude)
        """
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.logger = logging.getLogger(__name__)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            self.logger.warning(f"Error counting tokens: {e}")
            # Fallback to rough estimation
            return len(text.split()) * 1.3  # Rough token estimation

    def count_tokens_batch(self, texts: List[str]) -> List[int]:
        """Count tokens for multiple texts.

        Args:
            texts: List of texts to count tokens for

        Returns:
            List of token counts
        """
        return [self.count_tokens(text) for text in texts]


class VanillaReadSimulator:
    """Simulates vanilla file reading approach for comparison."""

    def __init__(self, project_path: str):
        """Initialize simulator.

        Args:
            project_path: Path to the project being evaluated
        """
        self.project_path = Path(project_path)
        self.token_counter = TokenCounter()
        self.logger = logging.getLogger(__name__)

    def simulate_find_files(
        self, query: str, ground_truth_files: List[str]
    ) -> List[str]:
        """Simulate finding relevant files without semantic search.

        This simulates how a developer would find files manually:
        1. Based on file names and directory structure
        2. Potentially reading multiple files to find relevant code
        3. Following imports and dependencies

        Args:
            query: The search query
            ground_truth_files: Known relevant files for this query

        Returns:
            List of file paths that would likely be read
        """
        # For now, simulate reading related files based on patterns
        # In reality, this would involve more complex logic

        files_to_read = set(ground_truth_files)

        # Add related files that might be read during exploration
        for gt_file in ground_truth_files:
            gt_path = Path(gt_file)

            # Add files in same directory
            if self.project_path.exists():
                same_dir = self.project_path / gt_path.parent
                if same_dir.exists():
                    for file in same_dir.glob("*.py"):
                        if len(files_to_read) < 10:  # Limit simulation
                            files_to_read.add(str(file.relative_to(self.project_path)))

        return list(files_to_read)

    def simulate_read_files(self, file_paths: List[str]) -> Tuple[str, int, float]:
        """Simulate reading files and count total tokens.

        Args:
            file_paths: List of file paths to read

        Returns:
            Tuple of (combined_content, total_tokens, read_time)
        """
        start_time = time.time()
        all_content = []
        total_tokens = 0

        for file_path in file_paths:
            full_path = self.project_path / file_path

            if full_path.exists() and full_path.is_file():
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        all_content.append(f"# File: {file_path}\n{content}")
                        total_tokens += self.token_counter.count_tokens(content)
                except Exception as e:
                    self.logger.warning(f"Error reading {file_path}: {e}")
                    # Add placeholder content
                    placeholder = f"# Error reading {file_path}: {e}"
                    all_content.append(placeholder)
                    total_tokens += self.token_counter.count_tokens(placeholder)
            else:
                # Add placeholder for missing files
                placeholder = f"# File not found: {file_path}"
                all_content.append(placeholder)
                total_tokens += self.token_counter.count_tokens(placeholder)

        read_time = time.time() - start_time
        combined_content = "\n\n".join(all_content)

        return combined_content, total_tokens, read_time


class TokenEfficiencyEvaluator(BaseEvaluator):
    """Evaluator for comparing token efficiency of MCP search vs vanilla reading."""

    def __init__(
        self,
        output_dir: str,
        max_instances: Optional[int] = None,
        k: int = 5,
        use_gpu: bool = True,
        encoding_name: str = "cl100k_base",
    ):
        """Initialize token efficiency evaluator.

        Args:
            output_dir: Directory for output files
            max_instances: Maximum number of instances to evaluate
            k: Number of search results to return
            use_gpu: Whether to use GPU for search
            encoding_name: tiktoken encoding name
        """
        super().__init__(output_dir, max_instances, k)
        self.use_gpu = use_gpu
        self.token_counter = TokenCounter(encoding_name)
        self.searcher = None
        self.current_project_path = None
        self.semantic_evaluator = None

    def build_index(self, project_path: str) -> None:
        """Build search index for the project.

        Args:
            project_path: Path to the project
        """
        from evaluation.semantic_evaluator import SemanticSearchEvaluator

        # Use the existing semantic evaluator for indexing
        self.semantic_evaluator = SemanticSearchEvaluator(
            output_dir=str(self.output_dir / "semantic_temp"),
            k=self.k,
            use_gpu=self.use_gpu,
        )

        self.semantic_evaluator.build_index(project_path)
        self.current_project_path = project_path

        self.logger.info(f"Index built for token efficiency evaluation: {project_path}")

    def search(self, query: str, k: int) -> List[RetrievalResult]:
        """Execute search and return results.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of retrieval results
        """
        if not self.semantic_evaluator:
            raise ValueError("Index not built. Call build_index() first.")

        return self.semantic_evaluator.search(query, k)

    def evaluate_token_efficiency(
        self, instance: EvaluationInstance, project_path: str
    ) -> TokenEfficiencyResult:
        """Evaluate token efficiency for a single query.

        Args:
            instance: Evaluation instance
            project_path: Project path

        Returns:
            Token efficiency result
        """
        self.logger.info(f"Evaluating token efficiency: {instance.instance_id}")

        # 1. Execute semantic search and measure tokens
        search_start = time.time()
        search_results = self.search(instance.query, self.k)
        search_time = time.time() - search_start

        # Count tokens in search query and results
        query_tokens = self.token_counter.count_tokens(instance.query)
        result_tokens = sum(
            self.token_counter.count_tokens(r.content) for r in search_results
        )
        search_total_tokens = query_tokens + result_tokens

        # 2. Simulate vanilla file reading approach
        simulator = VanillaReadSimulator(project_path)
        simulated_files = simulator.simulate_find_files(
            instance.query, instance.ground_truth_files
        )

        vanilla_content, vanilla_tokens, read_time = simulator.simulate_read_files(
            simulated_files
        )

        # 3. Calculate efficiency metrics
        token_savings = vanilla_tokens - search_total_tokens
        efficiency_ratio = (
            search_total_tokens / vanilla_tokens if vanilla_tokens > 0 else 0.0
        )
        percentage_savings = (
            (token_savings / vanilla_tokens * 100) if vanilla_tokens > 0 else 0.0
        )
        time_savings = read_time - search_time
        files_avoided = len(simulated_files) - len(search_results)

        efficiency_metrics = TokenEfficiencyMetrics(
            search_tokens=search_total_tokens,
            vanilla_read_tokens=vanilla_tokens,
            token_savings=token_savings,
            efficiency_ratio=efficiency_ratio,
            percentage_savings=percentage_savings,
            search_time=search_time,
            read_time=read_time,
            time_savings=time_savings,
            files_avoided=files_avoided,
        )

        # 4. Calculate standard search metrics
        retrieved_files = [r.file_path for r in search_results]
        scores = [r.score for r in search_results]

        precision, recall = self.calculate_precision_recall(
            retrieved_files, instance.ground_truth_files
        )
        f1_score = self.calculate_f1_score(precision, recall)
        mrr = self.calculate_mrr(retrieved_files, instance.ground_truth_files)
        ndcg = self.calculate_ndcg(retrieved_files, instance.ground_truth_files, scores)

        search_metrics = SearchMetrics(
            query_time=search_time,
            total_results=len(search_results),
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            mrr=mrr,
            ndcg=ndcg,
            token_usage=search_total_tokens,
            tool_calls=1,  # One search call
        )

        # 5. Create comprehensive result
        result = TokenEfficiencyResult(
            scenario_id=instance.instance_id,
            query=instance.query,
            search_metrics=search_metrics,
            efficiency_metrics=efficiency_metrics,
            search_results=search_results,
            simulated_files=simulated_files,
            metadata={
                "ground_truth_files": instance.ground_truth_files,
                "project_path": project_path,
                "k": self.k,
                **(instance.metadata or {}),
            },
        )

        self.logger.info(
            f"Token efficiency - Query: {instance.instance_id}, "
            f"Savings: {percentage_savings:.1f}% ({token_savings} tokens), "
            f"Time: {time_savings:.2f}s faster"
        )

        return result

    def run_token_efficiency_evaluation(
        self, instances: List[EvaluationInstance], project_path: str
    ) -> Dict[str, Any]:
        """Run complete token efficiency evaluation.

        Args:
            instances: List of evaluation instances
            project_path: Project path

        Returns:
            Comprehensive evaluation results
        """
        self.logger.info(
            f"Starting token efficiency evaluation with {len(instances)} instances"
        )

        # Limit instances if specified
        if self.max_instances and len(instances) > self.max_instances:
            instances = instances[: self.max_instances]
            self.logger.info(f"Limited to {len(instances)} instances")

        # Build index once
        self.logger.info("Building search index...")
        build_start = time.time()
        self.build_index(project_path)
        build_time = time.time() - build_start
        self.logger.info(f"Index built in {build_time:.2f}s")

        # Evaluate each instance
        all_results = []

        for i, instance in enumerate(instances):
            self.logger.info(f"Processing instance {i + 1}/{len(instances)}")

            try:
                result = self.evaluate_token_efficiency(instance, project_path)
                all_results.append(result)
            except Exception as e:
                self.logger.error(f"Error evaluating {instance.instance_id}: {e}")
                continue

        # Calculate aggregate statistics
        if all_results:
            aggregate_results = self._calculate_token_efficiency_aggregates(all_results)
        else:
            aggregate_results = {}

        # Compile final results
        evaluation_results = {
            "metadata": {
                "total_instances": len(instances),
                "successful_evaluations": len(all_results),
                "project_path": str(project_path),
                "k": self.k,
                "build_time": build_time,
                "evaluation_timestamp": time.time(),
                "encoding_name": self.token_counter.encoding.name,
            },
            "aggregate_metrics": aggregate_results,
            "results_by_instance": {
                result.scenario_id: {
                    "scenario_id": result.scenario_id,
                    "query": result.query,
                    "search_metrics": result.search_metrics.to_dict(),
                    "efficiency_metrics": asdict(result.efficiency_metrics),
                    "metadata": result.metadata,
                    "timestamp": time.time(),
                }
                for result in all_results
            },
        }

        # Save results
        self._save_token_efficiency_results(evaluation_results)

        self.logger.info("Token efficiency evaluation completed successfully")
        return evaluation_results

    def _calculate_token_efficiency_aggregates(
        self, results: List[TokenEfficiencyResult]
    ) -> Dict[str, Any]:
        """Calculate aggregate token efficiency metrics.

        Args:
            results: List of token efficiency results

        Returns:
            Aggregate metrics
        """
        if not results:
            return {}

        # Extract efficiency metrics
        token_savings = [r.efficiency_metrics.token_savings for r in results]
        percentage_savings = [r.efficiency_metrics.percentage_savings for r in results]
        efficiency_ratios = [r.efficiency_metrics.efficiency_ratio for r in results]
        time_savings = [r.efficiency_metrics.time_savings for r in results]
        files_avoided = [r.efficiency_metrics.files_avoided for r in results]

        # Extract search metrics
        precisions = [r.search_metrics.precision for r in results]
        recalls = [r.search_metrics.recall for r in results]
        f1_scores = [r.search_metrics.f1_score for r in results]

        return {
            "count": len(results),
            "token_efficiency": {
                "mean_token_savings": statistics.mean(token_savings),
                "median_token_savings": statistics.median(token_savings),
                "total_token_savings": sum(token_savings),
                "mean_percentage_savings": statistics.mean(percentage_savings),
                "median_percentage_savings": statistics.median(percentage_savings),
                "min_percentage_savings": min(percentage_savings),
                "max_percentage_savings": max(percentage_savings),
                "mean_efficiency_ratio": statistics.mean(efficiency_ratios),
                "median_efficiency_ratio": statistics.median(efficiency_ratios),
            },
            "time_efficiency": {
                "mean_time_savings": statistics.mean(time_savings),
                "median_time_savings": statistics.median(time_savings),
                "total_time_savings": sum(time_savings),
            },
            "file_efficiency": {
                "mean_files_avoided": statistics.mean(files_avoided),
                "total_files_avoided": sum(files_avoided),
            },
            "search_quality": {
                "mean_precision": statistics.mean(precisions),
                "mean_recall": statistics.mean(recalls),
                "mean_f1_score": statistics.mean(f1_scores),
            },
        }

    def _save_token_efficiency_results(self, results: Dict[str, Any]) -> None:
        """Save token efficiency evaluation results.

        Args:
            results: Evaluation results to save
        """
        # Save main results file
        results_file = self.output_dir / "token_efficiency_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        self.logger.info(f"Token efficiency results saved to {results_file}")

        # Save summary file
        summary_file = self.output_dir / "token_efficiency_summary.json"
        summary = {
            "metadata": results["metadata"],
            "aggregate_metrics": results["aggregate_metrics"],
        }
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)

        self.logger.info(f"Token efficiency summary saved to {summary_file}")

    def create_efficiency_report(self, results: Dict[str, Any]) -> str:
        """Create human-readable token efficiency report.

        Args:
            results: Evaluation results

        Returns:
            Formatted report string
        """
        metadata = results["metadata"]
        agg_metrics = results["aggregate_metrics"]

        report_lines = [
            "=" * 80,
            "TOKEN EFFICIENCY EVALUATION REPORT",
            "=" * 80,
            "",
            f"Project: {metadata['project_path']}",
            f"Total Instances: {metadata['total_instances']}",
            f"Successful Evaluations: {metadata['successful_evaluations']}",
            f"Top-K Results: {metadata['k']}",
            f"Index Build Time: {metadata['build_time']:.2f}s",
            f"Token Encoding: {metadata['encoding_name']}",
            "",
            "TOKEN EFFICIENCY RESULTS",
            "-" * 40,
        ]

        if agg_metrics and "token_efficiency" in agg_metrics:
            token_eff = agg_metrics["token_efficiency"]
            time_eff = agg_metrics["time_efficiency"]
            file_eff = agg_metrics["file_efficiency"]
            search_qual = agg_metrics["search_quality"]

            report_lines.extend(
                [
                    f"Mean Token Savings: {token_eff['mean_percentage_savings']:.1f}%",
                    f"Median Token Savings: {token_eff['median_percentage_savings']:.1f}%",
                    f"Total Tokens Saved: {token_eff['total_token_savings']:,}",
                    f"Efficiency Ratio (search/vanilla): {token_eff['mean_efficiency_ratio']:.3f}",
                    "",
                    "TIME EFFICIENCY",
                    "-" * 20,
                    f"Mean Time Savings: {time_eff['mean_time_savings']:.2f}s",
                    f"Total Time Saved: {time_eff['total_time_savings']:.2f}s",
                    "",
                    "FILE EFFICIENCY",
                    "-" * 20,
                    f"Mean Files Avoided: {file_eff['mean_files_avoided']:.1f}",
                    f"Total Files Avoided: {file_eff['total_files_avoided']}",
                    "",
                    "SEARCH QUALITY",
                    "-" * 20,
                    f"Mean Precision: {search_qual['mean_precision']:.3f}",
                    f"Mean Recall: {search_qual['mean_recall']:.3f}",
                    f"Mean F1-Score: {search_qual['mean_f1_score']:.3f}",
                ]
            )
        else:
            report_lines.append("No efficiency metrics available.")

        report_lines.extend(["", "=" * 80])

        report = "\n".join(report_lines)

        # Save report to file
        report_file = self.output_dir / "token_efficiency_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        self.logger.info(f"Token efficiency report saved to {report_file}")
        return report

    def cleanup(self) -> None:
        """Clean up resources used by the token efficiency evaluator."""
        if hasattr(self, "semantic_evaluator") and self.semantic_evaluator is not None:
            try:
                self.semantic_evaluator.cleanup()
            except Exception as e:
                self.logger.warning(f"Error during semantic evaluator cleanup: {e}")

        self.logger.info("Token efficiency evaluator cleanup completed")
