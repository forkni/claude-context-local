#!/usr/bin/env python3
"""Wrapper script to run benchmarks with BGE-M3 model.

This script sets the CLAUDE_EMBEDDING_MODEL environment variable to BGE-M3
and runs comprehensive benchmarks to compare performance against Gemma baseline.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set BGE-M3 as the embedding model BEFORE any imports
os.environ['CLAUDE_EMBEDDING_MODEL'] = 'BAAI/bge-m3'

# Verify the environment variable is set
print(f"Environment variable set: CLAUDE_EMBEDDING_MODEL={os.getenv('CLAUDE_EMBEDDING_MODEL')}")

# Import and verify configuration
from search.config import get_search_config

config = get_search_config()
print(f"[OK] Current model: {config.embedding_model_name}")
print(f"[OK] Dimensions: {config.model_dimension}")

if config.embedding_model_name != 'BAAI/bge-m3':
    print("ERROR: Model configuration did not update correctly!")
    sys.exit(1)

print("\n" + "=" * 80)
print("BGE-M3 BENCHMARK SUITE")
print("=" * 80)
print(f"Model: {config.embedding_model_name}")
print(f"Dimensions: {config.model_dimension}")
print("=" * 80)

# Get script directory
script_dir = Path(__file__).parent
eval_script = script_dir / "run_evaluation.py"

print("\n[1/2] Running token efficiency benchmark with BGE-M3...")
print("-" * 80)

# Run token efficiency benchmark
result = subprocess.run([
    sys.executable,
    str(eval_script),
    "token-efficiency",
    "--max-instances", "5",
    "--k", "5",
    "--output-dir", "benchmark_results/token_efficiency_bge"
], env=os.environ.copy())

if result.returncode != 0:
    print("\nERROR: Token efficiency benchmark failed!")
    sys.exit(1)

print("\n[2/2] Running method comparison benchmark with BGE-M3...")
print("-" * 80)

# Run method comparison benchmark
result = subprocess.run([
    sys.executable,
    str(eval_script),
    "method-comparison",
    "--max-instances", "5",
    "--k", "5",
    "--output-dir", "benchmark_results/method_comparison_bge"
], env=os.environ.copy())

if result.returncode != 0:
    print("\nERROR: Method comparison benchmark failed!")
    sys.exit(1)

print("\n" + "=" * 80)
print("[SUCCESS] All BGE-M3 benchmarks completed successfully!")
print("=" * 80)
print("\nResults saved to:")
print("  - benchmark_results/token_efficiency_bge/")
print("  - benchmark_results/method_comparison_bge/")
print("\nNext step: Run compare_model_benchmarks.py to generate comparison report")
print("=" * 80)
