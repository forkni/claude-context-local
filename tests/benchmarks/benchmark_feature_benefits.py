"""
Unified Benchmark: Codanna Feature Benefits Assessment

Runs all three feature benchmarks and generates comprehensive report:
1. Query Intent Detection Quality (MRR, P@5)
2. Symbol Hash Cache Efficiency (hit rate, latency)
3. Mmap Vector Storage Performance (access time, speedup)

Usage:
    python tests/benchmarks/benchmark_feature_benefits.py

Outputs:
    - Console report with pass/fail for each feature
    - JSON report at: tests/benchmarks/results/feature_benefits_report.json
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.benchmarks.benchmark_intent_quality import IntentQualityBenchmark

from tests.benchmarks.benchmark_cache_efficiency import CacheEfficiencyBenchmark
from tests.benchmarks.benchmark_mmap_realistic import MmapRealisticBenchmark


class FeatureBenefitsAssessment:
    """Unified assessment of all three Codanna features."""

    def __init__(self):
        self.storage_dir = Path("C:/Users/Inter/.claude_code_search")
        self.labeled_queries_path = (
            Path(__file__).parent.parent / "fixtures" / "labeled_queries.json"
        )
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)

    def run_all_benchmarks(self) -> Dict:
        """Run all benchmarks and collect results."""
        print("=" * 80)
        print(" CODANNA FEATURE BENEFITS ASSESSMENT")
        print("=" * 80)
        print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Storage:   {self.storage_dir}")

        overall_start = time.time()

        all_results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "storage_dir": str(self.storage_dir),
                "labeled_queries": str(self.labeled_queries_path),
            },
            "features": {},
        }

        # 1. Query Intent Detection
        print("\n\n")
        print("=" * 80)
        print(" FEATURE 1: QUERY INTENT DETECTION ".center(80))
        print("=" * 80)

        try:
            benchmark1 = IntentQualityBenchmark(
                self.storage_dir, self.labeled_queries_path
            )
            results1 = benchmark1.run_full_benchmark()
            all_results["features"]["intent_detection"] = {
                "status": "completed",
                "results": results1,
            }
        except Exception as e:
            print(f"\n[X] FAILED: {e}")
            import traceback

            traceback.print_exc()
            all_results["features"]["intent_detection"] = {
                "status": "error",
                "error": str(e),
            }

        # 2. Symbol Hash Cache
        print("\n\n")
        print("=" * 80)
        print(" FEATURE 2: SYMBOL HASH CACHE ".center(80))
        print("=" * 80)

        try:
            benchmark2 = CacheEfficiencyBenchmark(
                self.storage_dir, self.labeled_queries_path
            )
            results2 = benchmark2.run_full_benchmark()
            all_results["features"]["symbol_cache"] = {
                "status": "completed",
                "results": results2,
            }
        except Exception as e:
            print(f"\n[X] FAILED: {e}")
            import traceback

            traceback.print_exc()
            all_results["features"]["symbol_cache"] = {
                "status": "error",
                "error": str(e),
            }

        # 3. Mmap Vector Storage
        print("\n\n")
        print("=" * 80)
        print(" FEATURE 3: MMAP VECTOR STORAGE ".center(80))
        print("=" * 80)

        try:
            benchmark3 = MmapRealisticBenchmark(self.storage_dir)
            results3 = benchmark3.run_full_benchmark()
            all_results["features"]["mmap_storage"] = {
                "status": "completed",
                "results": results3,
            }
        except Exception as e:
            print(f"\n[X] FAILED: {e}")
            import traceback

            traceback.print_exc()
            all_results["features"]["mmap_storage"] = {
                "status": "error",
                "error": str(e),
            }

        overall_time = time.time() - overall_start
        all_results["metadata"]["total_time_seconds"] = overall_time

        return all_results

    def generate_decision_matrix(self, results: Dict) -> Dict:
        """Generate decision matrix based on benchmark results.

        Returns:
            Dict with recommendations for each feature
        """
        decisions = {}

        # Feature 1: Intent Detection
        if results["features"]["intent_detection"]["status"] == "completed":
            intent_results = results["features"]["intent_detection"]["results"]
            mrr_improvement = intent_results.get("mrr_improvement_pct", 0)

            if mrr_improvement >= 5.0:
                decision = "KEEP - Proven quality improvement"
            elif mrr_improvement >= 2.0:
                decision = "SIMPLIFY - Modest benefit, reduce complexity"
            else:
                decision = "REMOVE - No meaningful benefit"

            decisions["intent_detection"] = {
                "decision": decision,
                "metric": f"MRR improvement: {mrr_improvement:+.2f}%",
                "threshold": "≥5%",
                "passed": mrr_improvement >= 5.0,
            }
        else:
            decisions["intent_detection"] = {
                "decision": "ERROR - Could not assess",
                "metric": "N/A",
                "threshold": "≥5%",
                "passed": False,
            }

        # Feature 2: Symbol Cache
        if results["features"]["symbol_cache"]["status"] == "completed":
            cache_results = results["features"]["symbol_cache"]["results"]
            hit_rate = cache_results["hit_rate"].get("hit_rate_pct", 0)

            if hit_rate >= 70.0:
                decision = "KEEP - High hit rate justifies overhead"
            elif hit_rate >= 50.0:
                decision = "MONITOR - Moderate benefit, needs investigation"
            else:
                decision = "REMOVE - Low hit rate, not worth complexity"

            decisions["symbol_cache"] = {
                "decision": decision,
                "metric": f"Hit rate: {hit_rate:.1f}%",
                "threshold": "≥70%",
                "passed": hit_rate >= 70.0,
            }
        else:
            decisions["symbol_cache"] = {
                "decision": "ERROR - Could not assess",
                "metric": "N/A",
                "threshold": "≥70%",
                "passed": False,
            }

        # Feature 3: Mmap Storage
        if results["features"]["mmap_storage"]["status"] == "completed":
            mmap_results = results["features"]["mmap_storage"]["results"]
            speedup = (
                mmap_results["mmap_vs_faiss"].get("speedup")
                if "mmap_vs_faiss" in mmap_results
                else None
            )

            if speedup and speedup >= 2.0:
                decision = "KEEP - Significant speedup at current scale"
            elif speedup and speedup >= 1.5:
                decision = "CONDITIONAL - Enable only for large indices (>10K vectors)"
            else:
                decision = "DISABLE BY DEFAULT - Not justified at 964 vectors"

            decisions["mmap_storage"] = {
                "decision": decision,
                "metric": f"Speedup: {speedup:.2f}x" if speedup else "N/A",
                "threshold": "≥2x",
                "passed": speedup >= 2.0 if speedup else False,
            }
        else:
            decisions["mmap_storage"] = {
                "decision": "ERROR - Could not assess",
                "metric": "N/A",
                "threshold": "≥2x",
                "passed": False,
            }

        return decisions

    def print_final_report(self, results: Dict, decisions: Dict):
        """Print comprehensive final report."""
        print("\n\n")
        print("=" * 80)
        print(" FINAL ASSESSMENT & RECOMMENDATIONS ".center(80))
        print("=" * 80)

        print("\n" + "-" * 80)
        print("DECISION MATRIX")
        print("-" * 80)

        for feature_name, decision_info in decisions.items():
            feature_label = feature_name.replace("_", " ").upper()
            print(f"\n{feature_label}:")
            print(f"  Metric:     {decision_info['metric']}")
            print(f"  Threshold:  {decision_info['threshold']}")
            print(
                f"  Status:     {'[OK] PASSED' if decision_info['passed'] else '[X] FAILED'}"
            )
            print(f"  Decision:   {decision_info['decision']}")

        # Overall recommendation
        print("\n" + "-" * 80)
        print("OVERALL RECOMMENDATION")
        print("-" * 80)

        passed_count = sum(1 for d in decisions.values() if d["passed"])
        total_count = len(decisions)

        print(f"\nFeatures meeting thresholds: {passed_count}/{total_count}")

        if passed_count == 3:
            print("\n[OK] ALL FEATURES JUSTIFIED - Codanna adoption successful")
        elif passed_count == 2:
            print("\n[!] PARTIAL SUCCESS - Review failing feature")
        elif passed_count == 1:
            print("\n[X] LIMITED BENEFIT - Consider reverting underperforming features")
        else:
            print(
                "\n[X] NO FEATURES JUSTIFIED - Recommend reverting all Codanna features"
            )

        # Execution time
        total_time = results["metadata"]["total_time_seconds"]
        print(f"\nTotal benchmark time: {total_time:.1f}s")

    def save_results(self, results: Dict, decisions: Dict):
        """Save results to JSON file."""
        report_path = (
            self.results_dir
            / f"feature_benefits_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        report = {
            "benchmark_results": results,
            "decisions": decisions,
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n\nReport saved to: {report_path}")

    def run(self) -> bool:
        """Run full assessment.

        Returns:
            True if all features pass, False otherwise
        """
        # Run benchmarks
        results = self.run_all_benchmarks()

        # Generate decisions
        decisions = self.generate_decision_matrix(results)

        # Print report
        self.print_final_report(results, decisions)

        # Save results
        self.save_results(results, decisions)

        # Return overall pass/fail
        return all(d["passed"] for d in decisions.values())


def main():
    """Run unified assessment."""
    assessment = FeatureBenefitsAssessment()

    try:
        all_passed = assessment.run()
        sys.exit(0 if all_passed else 1)
    except Exception as e:
        print(f"\n\n[X] ASSESSMENT FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
