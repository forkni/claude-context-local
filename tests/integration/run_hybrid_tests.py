#!/usr/bin/env python3
"""
Test runner for hybrid search integration tests.

This script runs the integration tests and captures the results,
specifically designed to demonstrate the current hybrid search issues.
"""

import sys
import pytest
import traceback
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def run_integration_tests():
    """Run hybrid search integration tests."""
    print("=" * 80)
    print("HYBRID SEARCH INTEGRATION TESTS")
    print("=" * 80)
    print(f"Running at: {datetime.now()}")
    print(f"Project root: {project_root}")
    print()

    # Test file path
    test_file = Path(__file__).parent / "test_hybrid_search_integration.py"

    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return False

    print(f"Running tests from: {test_file}")
    print()

    # Run pytest with verbose output
    args = [
        str(test_file),
        "-v",                    # Verbose output
        "-s",                    # Don't capture stdout/stderr
        "--tb=short",            # Short traceback format
        "--color=yes",           # Colored output
        "--durations=10"         # Show slowest 10 tests
    ]

    try:
        result = pytest.main(args)
        return result == 0
    except Exception as e:
        print(f"ERROR running tests: {e}")
        traceback.print_exc()
        return False

def run_specific_test(test_name: str):
    """Run a specific test method."""
    test_file = Path(__file__).parent / "test_hybrid_search_integration.py"

    print(f"Running specific test: {test_name}")
    print("-" * 60)

    args = [
        f"{test_file}::{test_name}",
        "-v",
        "-s",
        "--tb=long"
    ]

    try:
        result = pytest.main(args)
        return result == 0
    except Exception as e:
        print(f"ERROR running test {test_name}: {e}")
        traceback.print_exc()
        return False

def demonstrate_current_issues():
    """Run tests that will demonstrate the current hybrid search issues."""
    print("DEMONSTRATING CURRENT HYBRID SEARCH ISSUES")
    print("=" * 60)
    print()

    # These tests are expected to fail and will show the issues
    critical_tests = [
        "TestHybridSearchIntegration::test_hybrid_searcher_has_add_embeddings_method",
        "TestHybridSearchIntegration::test_incremental_indexing_with_hybrid_search",
        "TestHybridSearchIntegration::test_hybrid_indices_are_populated",
    ]

    results = {}

    for test in critical_tests:
        print(f"Running: {test}")
        print("-" * 40)
        success = run_specific_test(test)
        results[test] = success
        print()
        print("=" * 60)
        print()

    # Summary
    print("RESULTS SUMMARY:")
    print("-" * 30)
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        test_short = test.split("::")[-1]
        print(f"{status:4} | {test_short}")

    print()
    total_tests = len(results)
    passed_tests = sum(results.values())
    failed_tests = total_tests - passed_tests

    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")

    if failed_tests > 0:
        print()
        print("EXPECTED FAILURES:")
        print("- test_hybrid_searcher_has_add_embeddings_method: HybridSearcher missing add_embeddings method")
        print("- test_incremental_indexing_with_hybrid_search: Incremental indexer can't use HybridSearcher")
        print("- test_hybrid_indices_are_populated: BM25 index never gets populated")
        print()
        print("These failures confirm the issues identified in the analysis:")
        print("1. HybridSearcher lacks add_embeddings() method")
        print("2. Integration between incremental indexer and hybrid searcher is broken")
        print("3. BM25 index is not populated during indexing process")

    return failed_tests == 0

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run hybrid search integration tests")
    parser.add_argument("--test", help="Run specific test method")
    parser.add_argument("--demo", action="store_true", help="Demonstrate current issues")
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    if args.demo:
        success = demonstrate_current_issues()
    elif args.test:
        success = run_specific_test(args.test)
    elif args.all:
        success = run_integration_tests()
    else:
        # Default: demonstrate issues
        success = demonstrate_current_issues()

    sys.exit(0 if success else 1)