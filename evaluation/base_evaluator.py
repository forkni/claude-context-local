"""Base evaluation framework for semantic search systems."""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics


@dataclass
class RetrievalResult:
    """Single retrieval result."""
    file_path: str
    chunk_id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    line_start: int = 0
    line_end: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class SearchMetrics:
    """Search performance metrics."""
    query_time: float
    total_results: int
    precision: float
    recall: float
    f1_score: float
    mrr: float  # Mean Reciprocal Rank
    ndcg: float  # Normalized Discounted Cumulative Gain
    token_usage: int = 0
    tool_calls: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class EvaluationInstance:
    """Single evaluation instance."""
    instance_id: str
    query: str
    ground_truth_files: List[str]
    ground_truth_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class BaseEvaluator(ABC):
    """Base class for search evaluation systems."""

    def __init__(
        self,
        output_dir: str,
        max_instances: Optional[int] = None,
        k: int = 10
    ):
        """
        Initialize evaluator.

        Args:
            output_dir: Output directory for results
            max_instances: Maximum number of instances to evaluate
            k: Number of top results to consider
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_instances = max_instances
        self.k = k
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def build_index(self, project_path: str) -> None:
        """Build search index for the given project."""
        pass

    @abstractmethod
    def search(self, query: str, k: int) -> List[RetrievalResult]:
        """Execute semantic search and return results."""
        pass

    def calculate_precision_recall(
        self,
        retrieved_files: List[str],
        ground_truth_files: List[str]
    ) -> Tuple[float, float]:
        """
        Calculate precision and recall.

        Args:
            retrieved_files: List of retrieved file paths
            ground_truth_files: List of ground truth file paths

        Returns:
            Tuple of (precision, recall)
        """
        if not retrieved_files:
            return 0.0, 0.0

        retrieved_set = set(retrieved_files)
        ground_truth_set = set(ground_truth_files)

        true_positives = len(retrieved_set & ground_truth_set)
        precision = true_positives / len(retrieved_set) if retrieved_files else 0.0
        recall = true_positives / len(ground_truth_set) if ground_truth_files else 0.0

        return precision, recall

    def calculate_f1_score(self, precision: float, recall: float) -> float:
        """Calculate F1 score from precision and recall."""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def calculate_mrr(
        self,
        retrieved_files: List[str],
        ground_truth_files: List[str]
    ) -> float:
        """
        Calculate Mean Reciprocal Rank.

        Args:
            retrieved_files: List of retrieved file paths (ranked)
            ground_truth_files: List of ground truth file paths

        Returns:
            MRR score
        """
        ground_truth_set = set(ground_truth_files)

        for i, file_path in enumerate(retrieved_files):
            if file_path in ground_truth_set:
                return 1.0 / (i + 1)

        return 0.0

    def calculate_ndcg(
        self,
        retrieved_files: List[str],
        ground_truth_files: List[str],
        scores: List[float]
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain.

        Args:
            retrieved_files: List of retrieved file paths (ranked)
            ground_truth_files: List of ground truth file paths
            scores: List of relevance scores

        Returns:
            NDCG score
        """
        def dcg_at_k(relevances: List[float], k: int) -> float:
            """Calculate DCG at k."""
            dcg = 0.0
            for i in range(min(len(relevances), k)):
                dcg += relevances[i] / (1 + i)  # Using simplified DCG formula
            return dcg

        # Create relevance scores (1 for relevant, 0 for not relevant)
        relevances = []
        ground_truth_set = set(ground_truth_files)

        for file_path in retrieved_files[:self.k]:
            relevances.append(1.0 if file_path in ground_truth_set else 0.0)

        if not any(relevances):
            return 0.0

        # Calculate DCG
        dcg = dcg_at_k(relevances, self.k)

        # Calculate IDCG (ideal DCG)
        ideal_relevances = [1.0] * min(len(ground_truth_files), self.k)
        ideal_relevances.extend([0.0] * max(0, self.k - len(ground_truth_files)))
        idcg = dcg_at_k(ideal_relevances, self.k)

        return dcg / idcg if idcg > 0 else 0.0

    def evaluate_single_query(
        self,
        instance: EvaluationInstance,
        project_path: str
    ) -> SearchMetrics:
        """
        Evaluate a single query.

        Args:
            instance: Evaluation instance
            project_path: Path to the project being searched

        Returns:
            Search metrics for the query
        """
        self.logger.info(f"Evaluating query: {instance.instance_id}")

        start_time = time.time()

        try:
            # Execute search
            results = self.search(instance.query, self.k)
            query_time = time.time() - start_time

            # Extract file paths and scores
            retrieved_files = [r.file_path for r in results]
            scores = [r.score for r in results]

            # Calculate metrics
            precision, recall = self.calculate_precision_recall(
                retrieved_files, instance.ground_truth_files
            )
            f1_score = self.calculate_f1_score(precision, recall)
            mrr = self.calculate_mrr(retrieved_files, instance.ground_truth_files)
            ndcg = self.calculate_ndcg(
                retrieved_files, instance.ground_truth_files, scores
            )

            metrics = SearchMetrics(
                query_time=query_time,
                total_results=len(results),
                precision=precision,
                recall=recall,
                f1_score=f1_score,
                mrr=mrr,
                ndcg=ndcg
            )

            self.logger.debug(
                f"Query {instance.instance_id}: "
                f"P={precision:.3f}, R={recall:.3f}, F1={f1_score:.3f}"
            )

            return metrics

        except Exception as e:
            self.logger.error(f"Error evaluating query {instance.instance_id}: {e}")
            return SearchMetrics(
                query_time=time.time() - start_time,
                total_results=0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                mrr=0.0,
                ndcg=0.0
            )

    def run_evaluation(
        self,
        instances: List[EvaluationInstance],
        project_path: str
    ) -> Dict[str, Any]:
        """
        Run full evaluation on a list of instances.

        Args:
            instances: List of evaluation instances
            project_path: Path to the project being searched

        Returns:
            Comprehensive evaluation results
        """
        self.logger.info(f"Starting evaluation with {len(instances)} instances")

        # Limit instances if specified
        if self.max_instances and len(instances) > self.max_instances:
            instances = instances[:self.max_instances]
            self.logger.info(f"Limited to {len(instances)} instances")

        # Build index once
        self.logger.info("Building search index...")
        build_start = time.time()
        self.build_index(project_path)
        build_time = time.time() - build_start
        self.logger.info(f"Index built in {build_time:.2f}s")

        # Evaluate each instance
        all_metrics = []
        results_by_instance = {}

        for i, instance in enumerate(instances):
            self.logger.info(f"Processing instance {i+1}/{len(instances)}")

            metrics = self.evaluate_single_query(instance, project_path)
            all_metrics.append(metrics)

            # Store detailed results
            results_by_instance[instance.instance_id] = {
                'instance': instance.to_dict(),
                'metrics': metrics.to_dict(),
                'timestamp': time.time()
            }

        # Calculate aggregate statistics
        if all_metrics:
            aggregate_results = self._calculate_aggregate_metrics(all_metrics)
        else:
            aggregate_results = {}

        # Compile final results
        evaluation_results = {
            'metadata': {
                'total_instances': len(instances),
                'project_path': str(project_path),
                'k': self.k,
                'build_time': build_time,
                'evaluation_timestamp': time.time()
            },
            'aggregate_metrics': aggregate_results,
            'results_by_instance': results_by_instance
        }

        # Save results
        self._save_results(evaluation_results)

        self.logger.info("Evaluation completed successfully")
        return evaluation_results

    def _calculate_aggregate_metrics(self, all_metrics: List[SearchMetrics]) -> Dict[str, Any]:
        """Calculate aggregate metrics across all queries."""
        if not all_metrics:
            return {}

        # Extract values
        query_times = [m.query_time for m in all_metrics]
        precisions = [m.precision for m in all_metrics]
        recalls = [m.recall for m in all_metrics]
        f1_scores = [m.f1_score for m in all_metrics]
        mrr_scores = [m.mrr for m in all_metrics]
        ndcg_scores = [m.ndcg for m in all_metrics]
        total_results = [m.total_results for m in all_metrics]

        return {
            'count': len(all_metrics),
            'query_time': {
                'mean': statistics.mean(query_times),
                'median': statistics.median(query_times),
                'stdev': statistics.stdev(query_times) if len(query_times) > 1 else 0.0,
                'min': min(query_times),
                'max': max(query_times)
            },
            'precision': {
                'mean': statistics.mean(precisions),
                'median': statistics.median(precisions),
                'stdev': statistics.stdev(precisions) if len(precisions) > 1 else 0.0
            },
            'recall': {
                'mean': statistics.mean(recalls),
                'median': statistics.median(recalls),
                'stdev': statistics.stdev(recalls) if len(recalls) > 1 else 0.0
            },
            'f1_score': {
                'mean': statistics.mean(f1_scores),
                'median': statistics.median(f1_scores),
                'stdev': statistics.stdev(f1_scores) if len(f1_scores) > 1 else 0.0
            },
            'mrr': {
                'mean': statistics.mean(mrr_scores),
                'median': statistics.median(mrr_scores),
                'stdev': statistics.stdev(mrr_scores) if len(mrr_scores) > 1 else 0.0
            },
            'ndcg': {
                'mean': statistics.mean(ndcg_scores),
                'median': statistics.median(ndcg_scores),
                'stdev': statistics.stdev(ndcg_scores) if len(ndcg_scores) > 1 else 0.0
            },
            'total_results': {
                'mean': statistics.mean(total_results),
                'median': statistics.median(total_results),
                'stdev': statistics.stdev(total_results) if len(total_results) > 1 else 0.0
            }
        }

    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save evaluation results to disk."""
        # Save main results file
        results_file = self.output_dir / "evaluation_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        self.logger.info(f"Results saved to {results_file}")

        # Save summary file
        summary_file = self.output_dir / "evaluation_summary.json"
        summary = {
            'metadata': results['metadata'],
            'aggregate_metrics': results['aggregate_metrics']
        }
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)

        self.logger.info(f"Summary saved to {summary_file}")

    def load_dataset(self, dataset_path: str) -> List[EvaluationInstance]:
        """
        Load evaluation dataset.

        Args:
            dataset_path: Path to dataset file

        Returns:
            List of evaluation instances
        """
        dataset_file = Path(dataset_path)
        if not dataset_file.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

        self.logger.info(f"Loading dataset from {dataset_path}")

        if dataset_file.suffix == '.json':
            with open(dataset_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            instances = []
            # Handle different JSON formats
            if isinstance(data, list):
                raw_instances = data
            elif isinstance(data, dict):
                if 'instances' in data:
                    raw_instances = data['instances']
                else:
                    raw_instances = [data]
            else:
                raise ValueError(f"Unsupported dataset format in {dataset_path}")

            for item in raw_instances:
                instance = EvaluationInstance(
                    instance_id=item.get('instance_id', str(len(instances))),
                    query=item['query'],
                    ground_truth_files=item['ground_truth_files'],
                    ground_truth_content=item.get('ground_truth_content'),
                    metadata=item.get('metadata', {})
                )
                instances.append(instance)

            self.logger.info(f"Loaded {len(instances)} instances")
            return instances

        else:
            raise ValueError(f"Unsupported dataset format: {dataset_file.suffix}")

    def create_benchmark_report(self, results: Dict[str, Any]) -> str:
        """
        Create a human-readable benchmark report.

        Args:
            results: Evaluation results

        Returns:
            Formatted report string
        """
        metadata = results['metadata']
        agg_metrics = results['aggregate_metrics']

        report_lines = [
            "=" * 80,
            "SEMANTIC SEARCH EVALUATION REPORT",
            "=" * 80,
            "",
            f"Project: {metadata['project_path']}",
            f"Total Instances: {metadata['total_instances']}",
            f"Top-K Results: {metadata['k']}",
            f"Index Build Time: {metadata['build_time']:.2f}s",
            "",
            "AGGREGATE PERFORMANCE METRICS",
            "-" * 40,
        ]

        if agg_metrics:
            report_lines.extend([
                f"Query Time (avg): {agg_metrics['query_time']['mean']:.3f}s ± {agg_metrics['query_time']['stdev']:.3f}s",
                f"Precision (avg): {agg_metrics['precision']['mean']:.3f} ± {agg_metrics['precision']['stdev']:.3f}",
                f"Recall (avg): {agg_metrics['recall']['mean']:.3f} ± {agg_metrics['recall']['stdev']:.3f}",
                f"F1-Score (avg): {agg_metrics['f1_score']['mean']:.3f} ± {agg_metrics['f1_score']['stdev']:.3f}",
                f"MRR (avg): {agg_metrics['mrr']['mean']:.3f} ± {agg_metrics['mrr']['stdev']:.3f}",
                f"NDCG (avg): {agg_metrics['ndcg']['mean']:.3f} ± {agg_metrics['ndcg']['stdev']:.3f}",
                f"Results per Query (avg): {agg_metrics['total_results']['mean']:.1f}",
            ])
        else:
            report_lines.append("No metrics available.")

        report_lines.extend([
            "",
            "=" * 80
        ])

        report = "\n".join(report_lines)

        # Save report to file
        report_file = self.output_dir / "evaluation_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        self.logger.info(f"Benchmark report saved to {report_file}")
        return report