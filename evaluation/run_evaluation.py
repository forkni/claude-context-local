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
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("evaluation.log")],
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
        default="test_evaluation",
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
