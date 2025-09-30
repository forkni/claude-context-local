#!/usr/bin/env python3
"""Auto-tune hybrid search parameters for your codebase."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from evaluation.parameter_optimizer import ParameterOptimizer


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create logs directory if it doesn't exist
    log_dir = Path("benchmark_results/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"auto_tune_{timestamp}.log"

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    logging.getLogger().info(f"Log file: {log_file}")


def apply_parameters(bm25_weight: float, dense_weight: float, rrf_k: int) -> bool:
    """
    Apply optimized parameters to hybrid_searcher.py.

    Args:
        bm25_weight: Optimal BM25 weight
        dense_weight: Optimal dense weight
        rrf_k: Optimal RRF k value

    Returns:
        True if successfully applied, False otherwise
    """
    import re

    searcher_file = Path("search/hybrid_searcher.py")
    if not searcher_file.exists():
        print(f"[ERROR] Could not find {searcher_file}")
        return False

    try:
        # Read file
        content = searcher_file.read_text(encoding="utf-8")

        # Match the __init__ default parameters
        pattern = r"(bm25_weight: float = )[\d.]+,\s*(dense_weight: float = )[\d.]+,\s*(rrf_k: int = )\d+"
        replacement = f"\\g<1>{bm25_weight},\n        \\g<2>{dense_weight},\n        \\g<3>{rrf_k}"

        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            print("[WARN] Parameters unchanged (already optimal or pattern not found)")
            return False

        # Write back
        searcher_file.write_text(new_content, encoding="utf-8")
        print(f"[OK] Applied to {searcher_file}:")
        print(
            f"     bm25_weight={bm25_weight}, dense_weight={dense_weight}, rrf_k={rrf_k}"
        )
        return True

    except Exception as e:
        print(f"[ERROR] Failed to apply: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Auto-tune hybrid search parameters for your codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick optimization on current project with debug scenarios
  python tools/auto_tune_search.py --project . --dataset evaluation/datasets/debug_scenarios.json

  # Optimize with custom dataset
  python tools/auto_tune_search.py --project /path/to/project --dataset my_queries.json

  # Keep old results for comparison
  python tools/auto_tune_search.py --project . --keep-results

  # Verbose output for debugging
  python tools/auto_tune_search.py --project . --verbose
        """,
    )

    parser.add_argument(
        "--project",
        type=str,
        default=".",
        help="Path to project to optimize for (default: current directory)",
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default="evaluation/datasets/debug_scenarios.json",
        help="Path to evaluation dataset (default: debug_scenarios.json)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results/tuning",
        help="Output directory for results (default: benchmark_results/tuning)",
    )

    parser.add_argument(
        "--max-instances",
        type=int,
        help="Maximum evaluation instances to test (default: all)",
    )

    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of top results to consider (default: 5)",
    )

    parser.add_argument(
        "--keep-results",
        action="store_true",
        help="Keep old tuning results instead of cleaning (default: clean)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--current-f1",
        type=float,
        help="Current F1-score for comparison (optional)",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Automatically apply optimal parameters to hybrid_searcher.py",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Validate inputs
    project_path = Path(args.project)
    if not project_path.exists():
        print(f"ERROR: Project path does not exist: {args.project}")
        sys.exit(1)

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"ERROR: Dataset path does not exist: {args.dataset}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("HYBRID SEARCH AUTO-TUNING")
    print("=" * 80)
    print(f"Project: {args.project}")
    print(f"Dataset: {args.dataset}")
    print(f"Output: {args.output_dir}")
    print("=" * 80)

    try:
        # Create optimizer
        optimizer = ParameterOptimizer(
            project_path=str(project_path),
            dataset_path=str(dataset_path),
            output_dir=args.output_dir,
            k=args.k,
            max_instances=args.max_instances,
        )

        # Cleanup old results (unless --keep-results)
        if not args.keep_results:
            optimizer.cleanup_old_results()
        else:
            print("[INFO] Keeping old results (--keep-results flag)")

        # Build index once
        optimizer.build_index_once()

        # Run optimization with 3 strategic configurations
        weight_pairs = [
            (0.3, 0.7),  # Heavy semantic
            (0.4, 0.6),  # Current default
            (0.6, 0.4),  # Keyword-focused
        ]

        optimization_results = optimizer.optimize(weight_pairs=weight_pairs)

        # Generate report
        report = optimizer.generate_report(
            optimization_results, current_f1=args.current_f1
        )
        print(report)

        # Save results
        optimizer.save_results(optimization_results, report)

        print("\n[OK] Auto-tuning completed successfully!")

        # Get best configuration
        best_config = optimization_results["best_config"]["config"]
        logger.info(
            f"Best configuration: BM25={best_config['bm25_weight']}, "
            f"Dense={best_config['dense_weight']}, "
            f"RRF_k={best_config['rrf_k']}"
        )

        # Apply parameters if requested
        if args.apply:
            print("\n" + "=" * 80)
            print("APPLYING OPTIMIZED PARAMETERS")
            print("=" * 80)
            success = apply_parameters(
                best_config["bm25_weight"],
                best_config["dense_weight"],
                best_config["rrf_k"],
            )
            if success:
                print(
                    "[OK] Parameters applied! Changes will take effect on next index build."
                )
            else:
                print(
                    "[WARN] Parameters not applied. Manually update search/hybrid_searcher.py"
                )
        else:
            print(
                "\nTo apply parameters: python tools/auto_tune_search.py --project . --apply"
            )

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Auto-tuning interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Auto-tuning failed: {e}", exc_info=True)
        print(f"\n[ERROR] Auto-tuning failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
