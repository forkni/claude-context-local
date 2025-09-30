#!/usr/bin/env python3
"""Main evaluation runner for the Claude Context MCP system."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from evaluation.semantic_evaluator import BM25OnlyEvaluator, SemanticSearchEvaluator
from evaluation.swe_bench_evaluator import (
    SWEBenchDatasetLoader,
    SWEBenchEvaluationRunner,
)
from evaluation.token_efficiency_evaluator import TokenEfficiencyEvaluator


def detect_gpu_availability() -> bool:
    """
    Detect if GPU acceleration is available.

    Returns:
        bool: True if CUDA GPU is available, False otherwise
    """
    try:
        import torch

        available = torch.cuda.is_available()
        if available:
            device_count = torch.cuda.device_count()
            device_name = (
                torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
            )
            logging.getLogger().info(f"GPU detected: {device_name} (CUDA available)")
        else:
            logging.getLogger().info("No GPU detected, using CPU")
        return available
    except ImportError:
        logging.getLogger().warning("PyTorch not available, using CPU")
        return False
    except Exception as e:
        logging.getLogger().warning(f"Error detecting GPU: {e}, using CPU")
        return False


def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration with timestamped log file."""
    from datetime import datetime

    # Create logs directory if it doesn't exist
    log_dir = Path("benchmark_results/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamped log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"evaluation_{timestamp}.log"

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
    )


def run_swe_bench_evaluation(
    dataset_path: Optional[str],
    output_dir: str,
    max_instances: Optional[int],
    k: int,
    methods: List[str],
) -> None:
    """
    Run SWE-bench evaluation.

    Args:
        dataset_path: Path to dataset file
        output_dir: Output directory for results
        max_instances: Maximum instances to evaluate
        k: Number of top results to consider
        methods: List of methods to evaluate
    """
    logger = logging.getLogger("SWEBenchEvaluation")
    logger.info("Starting SWE-bench evaluation")

    # Load dataset
    dataset_loader = SWEBenchDatasetLoader()

    if dataset_path and Path(dataset_path).exists():
        logger.info(f"Loading dataset from {dataset_path}")
        instances = dataset_loader.load_dataset_file(dataset_path, max_instances)
    else:
        logger.info("Loading SWE-bench Lite dataset")
        instances = dataset_loader.load_swe_bench_lite(max_instances=max_instances)

    if not instances:
        logger.error("No evaluation instances loaded")
        return

    logger.info(f"Loaded {len(instances)} instances for evaluation")

    # Create evaluation runner
    runner = SWEBenchEvaluationRunner(output_dir)

    try:
        # Run comparison evaluation
        results = runner.run_comparison_evaluation(
            instances=instances, k=k, max_instances=max_instances
        )

        logger.info("SWE-bench evaluation completed successfully")
        print(f"\n{'=' * 60}")
        print("EVALUATION COMPLETED SUCCESSFULLY")
        print(f"{'=' * 60}")
        print(f"Results saved to: {output_dir}")
        print(f"Total instances evaluated: {results['metadata']['total_instances']}")
        print(f"Methods compared: {', '.join(results['metadata']['evaluators'])}")

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise
    finally:
        runner.cleanup()


def run_custom_evaluation(
    dataset_path: str,
    project_path: str,
    output_dir: str,
    method: str,
    max_instances: Optional[int],
    k: int,
) -> None:
    """
    Run custom evaluation on a specific project.

    Args:
        dataset_path: Path to custom evaluation dataset
        project_path: Path to project to evaluate on
        output_dir: Output directory for results
        method: Evaluation method to use
        max_instances: Maximum instances to evaluate
        k: Number of top results to consider
    """
    logger = logging.getLogger("CustomEvaluation")
    logger.info(f"Starting custom evaluation on {project_path}")

    # Create evaluator based on method
    if method == "hybrid":
        evaluator = SemanticSearchEvaluator(
            output_dir=output_dir, max_instances=max_instances, k=k
        )
    elif method == "bm25":
        evaluator = BM25OnlyEvaluator(
            output_dir=output_dir, max_instances=max_instances, k=k
        )
    elif method == "dense":
        evaluator = SemanticSearchEvaluator(
            output_dir=output_dir,
            max_instances=max_instances,
            k=k,
            bm25_weight=0.0,
            dense_weight=1.0,
        )
    else:
        raise ValueError(f"Unknown method: {method}")

    try:
        # Load custom dataset
        instances = evaluator.load_dataset(dataset_path)
        logger.info(f"Loaded {len(instances)} instances")

        # Run evaluation
        results = evaluator.run_evaluation(instances, project_path)

        # Generate report
        report = evaluator.create_benchmark_report(results)
        print(f"\n{report}")

        logger.info("Custom evaluation completed successfully")

    except Exception as e:
        logger.error(f"Custom evaluation failed: {e}")
        raise
    finally:
        evaluator.cleanup()


def run_token_efficiency_evaluation(
    dataset_path: str,
    project_path: str,
    output_dir: str,
    max_instances: Optional[int],
    k: int,
    use_gpu: Optional[bool] = None,
) -> None:
    """
    Run token efficiency evaluation comparing MCP semantic search vs vanilla file reading.

    Args:
        dataset_path: Path to token efficiency evaluation dataset
        project_path: Path to project to evaluate on
        output_dir: Output directory for results
        max_instances: Maximum instances to evaluate
        k: Number of top results to consider
        use_gpu: Whether to use GPU (None for auto-detection)
    """
    logger = logging.getLogger("TokenEfficiencyEvaluation")
    logger.info(f"Starting token efficiency evaluation on {project_path}")

    # Auto-detect GPU if not specified
    if use_gpu is None:
        use_gpu = detect_gpu_availability()
        logger.info(f"Auto-detected GPU usage: {use_gpu}")
    else:
        logger.info(f"GPU usage manually set to: {use_gpu}")

    # Create evaluator with automatic GPU detection
    evaluator = TokenEfficiencyEvaluator(
        output_dir=output_dir, max_instances=max_instances, k=k, use_gpu=use_gpu
    )

    try:
        # Load dataset
        instances = evaluator.load_dataset(dataset_path)
        logger.info(f"Loaded {len(instances)} token efficiency test scenarios")

        # Run evaluation
        results = evaluator.run_token_efficiency_evaluation(instances, project_path)

        # Generate report
        report = evaluator.create_efficiency_report(results)
        print(f"\n{report}")

        logger.info("Token efficiency evaluation completed successfully")
        print(f"\n{'=' * 60}")
        print("TOKEN EFFICIENCY EVALUATION COMPLETED")
        print(f"{'=' * 60}")
        print(f"Results saved to: {output_dir}")
        print(f"GPU acceleration: {'Enabled' if use_gpu else 'Disabled (CPU only)'}")

    except Exception as e:
        logger.error(f"Token efficiency evaluation failed: {e}")
        raise
    finally:
        evaluator.cleanup()


def run_method_comparison(
    dataset_path: str,
    project_path: str,
    output_dir: str,
    max_instances: Optional[int],
    k: int,
) -> None:
    """
    Run comparison of all search methods (hybrid, BM25, semantic) on a project.

    Args:
        dataset_path: Path to evaluation dataset
        project_path: Path to project to evaluate on
        output_dir: Output directory for results
        max_instances: Maximum instances to evaluate
        k: Number of top results to consider
    """
    logger = logging.getLogger("MethodComparison")
    logger.info(f"Starting method comparison evaluation on {project_path}")

    methods = ["hybrid", "bm25", "dense"]
    results = {}

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for method in methods:
        logger.info(f"Running evaluation with {method} method...")
        print(f"\n{'=' * 60}")
        print(f"EVALUATING: {method.upper()} METHOD")
        print(f"{'=' * 60}")

        # Create evaluator based on method
        if method == "hybrid":
            evaluator = SemanticSearchEvaluator(
                output_dir=f"{output_dir}/{method}", max_instances=max_instances, k=k
            )
        elif method == "bm25":
            evaluator = BM25OnlyEvaluator(
                output_dir=f"{output_dir}/{method}", max_instances=max_instances, k=k
            )
        elif method == "dense":
            evaluator = SemanticSearchEvaluator(
                output_dir=f"{output_dir}/{method}",
                max_instances=max_instances,
                k=k,
                bm25_weight=0.0,
                dense_weight=1.0,
            )

        try:
            # Load dataset for this method
            instances = evaluator.load_dataset(dataset_path)
            logger.info(f"Loaded {len(instances)} instances for {method} method")

            # Run evaluation (build_index is called internally by run_evaluation)
            logger.info(f"Running evaluation for {method} method...")
            method_results = evaluator.run_evaluation(instances, project_path)

            # Validate results have meaningful metrics
            if method_results and "metrics" in method_results:
                metrics = method_results["metrics"]
                logger.info(
                    f"{method} results: P={metrics.get('precision', 0):.3f}, R={metrics.get('recall', 0):.3f}, F1={metrics.get('f1_score', 0):.3f}"
                )
            else:
                logger.warning(f"{method} method returned no valid metrics")

            results[method] = method_results

            # Print individual method results
            report = evaluator.create_benchmark_report(method_results)
            print(f"\n{report}")

        except Exception as e:
            logger.error(f"Error running {method} evaluation: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            results[method] = {"error": str(e)}
        finally:
            evaluator.cleanup()

    # Create comparison report
    comparison_report = create_method_comparison_report(
        results, project_path, dataset_path
    )
    print(f"\n{comparison_report}")

    # Save comparison report
    comparison_file = Path(output_dir) / "method_comparison_report.txt"
    with open(comparison_file, "w", encoding="utf-8") as f:
        f.write(comparison_report)

    logger.info("Method comparison evaluation completed successfully")
    print(f"\n{'=' * 60}")
    print("METHOD COMPARISON COMPLETED")
    print(f"{'=' * 60}")
    print(f"Results saved to: {output_dir}")
    print(f"Comparison report: {comparison_file}")


def create_method_comparison_report(
    results: dict, project_path: str, dataset_path: str
) -> str:
    """Create a comprehensive comparison report of all search methods."""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("SEARCH METHOD COMPARISON REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Project: {project_path}")
    report_lines.append(f"Dataset: {dataset_path}")
    report_lines.append(f"Methods Evaluated: {', '.join(results.keys())}")
    report_lines.append("")

    # Extract metrics for comparison table
    metrics_table = []
    headers = ["Method", "Precision", "Recall", "F1-Score", "Avg Query Time", "Status"]

    for method, result in results.items():
        if "error" in result:
            row = [method.upper(), "ERROR", "ERROR", "ERROR", "ERROR", result["error"]]
        else:
            aggregate = result.get("aggregate_metrics", {})
            precision = f"{aggregate.get('precision', {}).get('mean', 0):.3f}"
            recall = f"{aggregate.get('recall', {}).get('mean', 0):.3f}"
            f1 = f"{aggregate.get('f1_score', {}).get('mean', 0):.3f}"
            avg_time = f"{aggregate.get('query_time', {}).get('mean', 0):.3f}s"
            row = [method.upper(), precision, recall, f1, avg_time, "SUCCESS"]
        metrics_table.append(row)

    # Create formatted table
    report_lines.append("PERFORMANCE COMPARISON")
    report_lines.append("-" * 80)

    # Calculate column widths
    col_widths = [
        max(len(str(row[i])) for row in [headers] + metrics_table) + 2
        for i in range(len(headers))
    ]

    # Header row
    header_row = (
        "| "
        + " | ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers)))
        + " |"
    )
    report_lines.append(header_row)
    report_lines.append(
        "|" + "|".join("-" * (col_widths[i] + 2) for i in range(len(headers))) + "|"
    )

    # Data rows
    for row in metrics_table:
        data_row = (
            "| "
            + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
            + " |"
        )
        report_lines.append(data_row)

    report_lines.append("")

    # Determine winner and provide recommendations
    successful_results = {k: v for k, v in results.items() if "error" not in v}
    if successful_results:
        # Find best performing method by F1 score
        best_method = None
        best_f1 = -1

        for method, result in successful_results.items():
            f1 = result.get("aggregate_metrics", {}).get("f1_score", {}).get("mean", 0)
            if f1 > best_f1:
                best_f1 = f1
                best_method = method

        report_lines.append("WINNER & RECOMMENDATIONS")
        report_lines.append("-" * 80)

        if best_method and best_f1 > 0:
            report_lines.append(
                f"[WINNER] BEST PERFORMING METHOD: {best_method.upper()}"
            )
            report_lines.append(f"   F1-Score: {best_f1:.3f}")
            report_lines.append("")

            # Method-specific recommendations
            if best_method == "hybrid":
                report_lines.append("[RECOMMENDED] Use HYBRID search for best results")
                report_lines.append(
                    "   - Combines semantic understanding with keyword matching"
                )
                report_lines.append("   - Best balance of precision and recall")
                report_lines.append("   - Optimal for most search scenarios")
            elif best_method == "bm25":
                report_lines.append(
                    "[RECOMMENDED] Use BM25 for keyword-focused searches"
                )
                report_lines.append("   - Excellent for exact term matching")
                report_lines.append("   - Fast and resource-efficient")
                report_lines.append("   - Best when you know specific keywords")
            elif best_method == "dense":
                report_lines.append(
                    "[RECOMMENDED] Use SEMANTIC search for conceptual queries"
                )
                report_lines.append("   - Best for understanding meaning and context")
                report_lines.append("   - Finds semantically related code")
                report_lines.append("   - Ideal for exploratory searches")
        else:
            report_lines.append(
                "[NOTE] NO CLEAR WINNER: All methods performed similarly"
            )
            report_lines.append(
                "   Consider using HYBRID as the default balanced approach"
            )

        report_lines.append("")

        # Performance insights
        report_lines.append("PERFORMANCE INSIGHTS")
        report_lines.append("-" * 80)

        # Compare query times
        times = []
        for method, result in successful_results.items():
            if "error" not in result:
                avg_time = (
                    result.get("aggregate_metrics", {})
                    .get("query_time", {})
                    .get("mean", 0)
                )
                times.append((method, avg_time))

        if times:
            times.sort(key=lambda x: x[1])
            fastest = times[0]
            slowest = times[-1]

            report_lines.append(f"[FASTEST] {fastest[0].upper()} ({fastest[1]:.3f}s)")
            if len(times) > 1:
                report_lines.append(
                    f"[SLOWEST] {slowest[0].upper()} ({slowest[1]:.3f}s)"
                )
                speed_diff = slowest[1] / fastest[1] if fastest[1] > 0 else 1
                report_lines.append(f"   Speed difference: {speed_diff:.1f}x")
    else:
        report_lines.append("[ERROR] NO SUCCESSFUL EVALUATIONS")
        report_lines.append("   All methods encountered errors during evaluation")

    report_lines.append("")
    report_lines.append("=" * 80)

    return "\n".join(report_lines)


def create_sample_dataset(output_path: str) -> None:
    """Create a sample evaluation dataset for testing."""
    logger = logging.getLogger("SampleDataset")
    logger.info(f"Creating sample dataset at {output_path}")

    # Sample evaluation instances
    sample_instances = [
        {
            "instance_id": "test_001",
            "query": "function to calculate sum of two numbers",
            "ground_truth_files": ["utils.py", "math_utils.py"],
            "ground_truth_content": "def add(a, b): return a + b",
            "metadata": {"difficulty": "easy", "language": "python"},
        },
        {
            "instance_id": "test_002",
            "query": "class for user management and authentication",
            "ground_truth_files": ["models.py", "auth.py"],
            "ground_truth_content": "class User: pass",
            "metadata": {"difficulty": "medium", "language": "python"},
        },
        {
            "instance_id": "test_003",
            "query": "error handling and exception management",
            "ground_truth_files": ["exceptions.py", "error_handler.py"],
            "ground_truth_content": "try: pass except Exception: pass",
            "metadata": {"difficulty": "medium", "language": "python"},
        },
    ]

    # Create dataset structure
    dataset = {
        "metadata": {
            "name": "sample_evaluation_dataset",
            "description": "Sample dataset for testing evaluation framework",
            "total_instances": len(sample_instances),
            "created_by": "evaluation_runner",
        },
        "instances": sample_instances,
    }

    # Save dataset
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    logger.info(f"Sample dataset created with {len(sample_instances)} instances")
    print(f"Sample dataset created at: {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluation runner for Claude Context MCP system"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Evaluation commands")

    # SWE-bench evaluation
    swe_parser = subparsers.add_parser("swe-bench", help="Run SWE-bench evaluation")
    swe_parser.add_argument(
        "--dataset",
        type=str,
        help="Path to SWE-bench dataset file (downloads if not provided)",
    )
    swe_parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation_results",
        help="Output directory for results",
    )
    swe_parser.add_argument(
        "--max-instances", type=int, help="Maximum number of instances to evaluate"
    )
    swe_parser.add_argument(
        "--k", type=int, default=10, help="Number of top results to consider"
    )
    swe_parser.add_argument(
        "--methods",
        nargs="+",
        default=["hybrid", "bm25", "dense"],
        choices=["hybrid", "bm25", "dense"],
        help="Evaluation methods to compare",
    )

    # Custom evaluation
    custom_parser = subparsers.add_parser("custom", help="Run custom evaluation")
    custom_parser.add_argument(
        "--dataset", type=str, required=True, help="Path to custom evaluation dataset"
    )
    custom_parser.add_argument(
        "--project", type=str, required=True, help="Path to project to evaluate on"
    )
    custom_parser.add_argument(
        "--output-dir",
        type=str,
        default="custom_evaluation_results",
        help="Output directory for results",
    )
    custom_parser.add_argument(
        "--method",
        type=str,
        default="hybrid",
        choices=["hybrid", "bm25", "dense"],
        help="Evaluation method to use",
    )
    custom_parser.add_argument(
        "--max-instances", type=int, help="Maximum number of instances to evaluate"
    )
    custom_parser.add_argument(
        "--k", type=int, default=10, help="Number of top results to consider"
    )

    # Token efficiency evaluation
    token_parser = subparsers.add_parser(
        "token-efficiency", help="Run token efficiency evaluation"
    )
    token_parser.add_argument(
        "--dataset",
        type=str,
        default="evaluation/datasets/token_efficiency_scenarios.json",
        help="Path to token efficiency evaluation dataset",
    )
    token_parser.add_argument(
        "--project",
        type=str,
        default=".",
        help="Path to project to evaluate on",
    )
    token_parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results/token_efficiency",
        help="Output directory for results",
    )
    token_parser.add_argument(
        "--max-instances",
        type=int,
        default=3,
        help="Maximum number of instances to evaluate",
    )
    token_parser.add_argument(
        "--k", type=int, default=3, help="Number of top results to consider"
    )
    token_parser.add_argument(
        "--gpu", action="store_true", help="Force GPU usage (auto-detected by default)"
    )
    token_parser.add_argument(
        "--cpu", action="store_true", help="Force CPU usage (auto-detected by default)"
    )

    # Method comparison evaluation
    comparison_parser = subparsers.add_parser(
        "method-comparison", help="Compare all search methods (hybrid, BM25, semantic)"
    )
    comparison_parser.add_argument(
        "--dataset",
        type=str,
        default="evaluation/datasets/token_efficiency_scenarios.json",
        help="Path to evaluation dataset",
    )
    comparison_parser.add_argument(
        "--project",
        type=str,
        default=".",
        help="Path to project to evaluate on (default: current directory)",
    )
    comparison_parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results/method_comparison",
        help="Output directory for results",
    )
    comparison_parser.add_argument(
        "--max-instances",
        type=int,
        default=5,
        help="Maximum number of instances to evaluate",
    )
    comparison_parser.add_argument(
        "--k", type=int, default=5, help="Number of top results to consider"
    )

    # Create sample dataset
    sample_parser = subparsers.add_parser(
        "create-sample", help="Create sample evaluation dataset"
    )
    sample_parser.add_argument(
        "--output",
        type=str,
        default="sample_evaluation_dataset.json",
        help="Output path for sample dataset",
    )

    # Global arguments
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level)

    try:
        if args.command == "swe-bench":
            run_swe_bench_evaluation(
                dataset_path=args.dataset,
                output_dir=args.output_dir,
                max_instances=args.max_instances,
                k=args.k,
                methods=args.methods,
            )
        elif args.command == "custom":
            run_custom_evaluation(
                dataset_path=args.dataset,
                project_path=args.project,
                output_dir=args.output_dir,
                method=args.method,
                max_instances=args.max_instances,
                k=args.k,
            )
        elif args.command == "token-efficiency":
            # Handle GPU/CPU flags
            use_gpu = None
            if args.gpu and args.cpu:
                logging.getLogger().error("Cannot specify both --gpu and --cpu flags")
                sys.exit(1)
            elif args.gpu:
                use_gpu = True
            elif args.cpu:
                use_gpu = False
            # If neither flag is specified, use_gpu remains None for auto-detection

            run_token_efficiency_evaluation(
                dataset_path=args.dataset,
                project_path=args.project,
                output_dir=args.output_dir,
                max_instances=args.max_instances,
                k=args.k,
                use_gpu=use_gpu,
            )
        elif args.command == "method-comparison":
            run_method_comparison(
                dataset_path=args.dataset,
                project_path=args.project,
                output_dir=args.output_dir,
                max_instances=args.max_instances,
                k=args.k,
            )
        elif args.command == "create-sample":
            create_sample_dataset(args.output)
        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.getLogger().error(f"Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
