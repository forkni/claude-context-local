"""Compare Qwen3-0.6B vs BGE-M3 vs CodeRankEmbed result relevance side-by-side.

This tool runs identical queries on all three models and displays results for manual
inspection to determine which model returns most RELEVANT results.

The goal: Compare general-purpose (Qwen3, BGE-M3) vs code-specific (CodeRankEmbed)
models to determine optimal model selection strategy.
"""

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from embeddings.embedder import CodeEmbedder
from search.config import get_model_slug
from search.hybrid_searcher import HybridSearcher

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Test queries covering actual use cases in this codebase
TEST_QUERIES = [
    "error handling patterns",
    "configuration loading system",
    "BM25 index implementation",
    "incremental indexing logic",
    "embedding generation workflow",
    "multi-hop search algorithm",
    "Merkle tree change detection",
    "hybrid search RRF reranking",
]


def get_storage_dir(project_path: str, model_name: str, dimension: int) -> Path:
    """Get storage directory for model using model slug."""
    project_id = hashlib.md5(project_path.encode()).hexdigest()[:8]
    model_slug = get_model_slug(model_name)
    return (
        Path.home()
        / ".claude_code_search"
        / "projects"
        / f"claude-context-local_{project_id}_{model_slug}_{dimension}d"
        / "index"
    )


def run_search(model_name: str, dimension: int, queries: List[str], k: int = 5) -> Dict:
    """Run queries on a specific model and return results.

    Args:
        model_name: Model identifier (e.g., "BAAI/bge-m3")
        dimension: Model dimension (768 or 1024)
        queries: List of queries to run
        k: Number of results per query

    Returns:
        Dict with results per query
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Running queries with: {model_name}")
    logger.info(f"{'='*80}")

    # Load embedder
    embedder = CodeEmbedder(model_name=model_name)

    # Get storage directory
    project_path = str(project_root)
    storage_dir = get_storage_dir(project_path, model_name, dimension)

    if not storage_dir.exists():
        logger.error(f"Index not found: {storage_dir}")
        logger.error(f"Please index project with {model_name} first")
        return {}

    # Create searcher (semantic only for direct comparison)
    searcher = HybridSearcher(
        storage_dir=str(storage_dir),
        embedder=embedder,
        bm25_weight=0.0,  # Semantic only
        dense_weight=1.0,
    )

    results_by_query = {}

    for i, query in enumerate(queries, 1):
        logger.info(f"  [{i}/{len(queries)}] {query}")

        search_results = searcher.search(query=query, k=k, search_mode="semantic")

        results_by_query[query] = [
            {
                "chunk_id": r.doc_id,
                "name": r.metadata.get("name", "unknown"),
                "file": r.metadata.get("file", "unknown"),
                "lines": r.metadata.get("lines", "unknown"),
                "kind": r.metadata.get("kind", "unknown"),
                "score": r.score,
                "content_preview": r.metadata.get("content", "")[:200],  # First 200 chars
            }
            for r in search_results
        ]

    # Cleanup
    embedder.cleanup()

    return results_by_query


def generate_comparison_report(
    qwen3_results: Dict,
    bge_m3_results: Dict,
    coderankembed_results: Dict,
    output_path: Path
):
    """Generate 3-way comparison report.

    Args:
        qwen3_results: Results from Qwen3-0.6B
        bge_m3_results: Results from BGE-M3
        coderankembed_results: Results from CodeRankEmbed
        output_path: Path to save markdown report
    """
    report = []

    # Header
    report.append("# Model Relevance Comparison: Qwen3-0.6B vs BGE-M3 vs CodeRankEmbed")
    report.append("")
    report.append("**Purpose**: Compare general-purpose (Qwen3, BGE-M3) vs code-specific (CodeRankEmbed) models")
    report.append("")
    report.append("**Models**:")
    report.append("- **Qwen3-0.6B** (1024d) - General-purpose, MTEB: 75.42 (+21.9% vs BGE-M3)")
    report.append("- **BGE-M3** (1024d) - General-purpose baseline, MTEB: 61.85")
    report.append("- **CodeRankEmbed** (768d) - Code-specific, CoIR: 60.1")
    report.append("")
    report.append("**Method**: Side-by-side comparison of top-5 results for 8 queries")
    report.append("")
    report.append("**Search mode**: Semantic only (no BM25, no multi-hop)")
    report.append("")
    report.append("---")
    report.append("")

    # Per-query comparison
    for query in qwen3_results.keys():
        report.append(f"## Query: \"{query}\"")
        report.append("")

        qwen3_top5 = qwen3_results[query]
        bge_m3_top5 = bge_m3_results[query]
        coderankembed_top5 = coderankembed_results[query]

        # Qwen3-0.6B results
        report.append("### Qwen3-0.6B Results")
        report.append("")
        for i, result in enumerate(qwen3_top5, 1):
            report.append(f"**#{i}** `{result['name']}` ({result['kind']})")
            report.append(f"- **File**: `{result['file']}:{result['lines']}`")
            report.append(f"- **Score**: {result['score']:.4f}")
            report.append(f"- **Preview**: `{result['content_preview']}...`")
            report.append("")

        # BGE-M3 results
        report.append("### BGE-M3 Results")
        report.append("")
        for i, result in enumerate(bge_m3_top5, 1):
            report.append(f"**#{i}** `{result['name']}` ({result['kind']})")
            report.append(f"- **File**: `{result['file']}:{result['lines']}`")
            report.append(f"- **Score**: {result['score']:.4f}")
            report.append(f"- **Preview**: `{result['content_preview']}...`")
            report.append("")

        # CodeRankEmbed results
        report.append("### CodeRankEmbed Results")
        report.append("")
        for i, result in enumerate(coderankembed_top5, 1):
            report.append(f"**#{i}** `{result['name']}` ({result['kind']})")
            report.append(f"- **File**: `{result['file']}:{result['lines']}`")
            report.append(f"- **Score**: {result['score']:.4f}")
            report.append(f"- **Preview**: `{result['content_preview']}...`")
            report.append("")

        # Overlap analysis
        qwen3_ids = {r['chunk_id'] for r in qwen3_top5}
        bge_m3_ids = {r['chunk_id'] for r in bge_m3_top5}
        coderankembed_ids = {r['chunk_id'] for r in coderankembed_top5}

        # All 3 models agree
        all_three = qwen3_ids & bge_m3_ids & coderankembed_ids

        # Two models agree
        qwen3_bge = (qwen3_ids & bge_m3_ids) - coderankembed_ids
        qwen3_coderank = (qwen3_ids & coderankembed_ids) - bge_m3_ids
        bge_coderank = (bge_m3_ids & coderankembed_ids) - qwen3_ids

        # Unique to each
        unique_qwen3 = qwen3_ids - bge_m3_ids - coderankembed_ids
        unique_bge = bge_m3_ids - qwen3_ids - coderankembed_ids
        unique_coderank = coderankembed_ids - qwen3_ids - bge_m3_ids

        report.append("### Overlap Analysis")
        report.append("")
        report.append(f"- **All 3 models agree**: {len(all_three)}/5")
        report.append(f"- **Qwen3 + BGE-M3 only**: {len(qwen3_bge)}/5")
        report.append(f"- **Qwen3 + CodeRankEmbed only**: {len(qwen3_coderank)}/5")
        report.append(f"- **BGE-M3 + CodeRankEmbed only**: {len(bge_coderank)}/5")
        report.append(f"- **Unique to Qwen3**: {len(unique_qwen3)}/5")
        report.append(f"- **Unique to BGE-M3**: {len(unique_bge)}/5")
        report.append(f"- **Unique to CodeRankEmbed**: {len(unique_coderank)}/5")
        report.append("")

        if unique_qwen3:
            report.append("**Qwen3 unique results:**")
            for chunk_id in unique_qwen3:
                result = next(r for r in qwen3_top5 if r['chunk_id'] == chunk_id)
                report.append(f"- `{result['name']}` in `{result['file']}`")
            report.append("")

        if unique_bge:
            report.append("**BGE-M3 unique results:**")
            for chunk_id in unique_bge:
                result = next(r for r in bge_m3_top5 if r['chunk_id'] == chunk_id)
                report.append(f"- `{result['name']}` in `{result['file']}`")
            report.append("")

        if unique_coderank:
            report.append("**CodeRankEmbed unique results:**")
            for chunk_id in unique_coderank:
                result = next(r for r in coderankembed_top5 if r['chunk_id'] == chunk_id)
                report.append(f"- `{result['name']}` in `{result['file']}`")
            report.append("")

        report.append("### Manual Assessment")
        report.append("")
        report.append("**Which model's results are most relevant to the query?**")
        report.append("")
        report.append("- [ ] Qwen3-0.6B clearly better")
        report.append("- [ ] BGE-M3 clearly better")
        report.append("- [ ] CodeRankEmbed clearly better")
        report.append("- [ ] Similar quality across all models")
        report.append("- [ ] Mixed (different models excel)")
        report.append("")
        report.append("**Notes**: [Add your observations here]")
        report.append("")
        report.append("---")
        report.append("")

    # Summary section
    report.append("## Summary")
    report.append("")
    report.append("### Overall Observations")
    report.append("")
    report.append("[Fill in after manual inspection]")
    report.append("")
    report.append("### Recommendation")
    report.append("")
    report.append("Based on relevance assessment:")
    report.append("")
    report.append("- [ ] **Use Qwen3-0.6B** - Clearly most relevant, justifies general-purpose model")
    report.append("- [ ] **Use BGE-M3** - Best balance of performance and relevance")
    report.append("- [ ] **Use CodeRankEmbed** - Code-specific model wins for code queries")
    report.append("- [ ] **Smart routing** - Different models excel at different query types")
    report.append("- [ ] **No clear winner** - Similar quality, use fastest/smallest model")
    report.append("")
    report.append("### Next Steps")
    report.append("")
    report.append("If smart routing recommended:")
    report.append("1. Categorize queries by type (technical/natural language)")
    report.append("2. Implement query classifier with keyword heuristics")
    report.append("3. Route to appropriate model automatically")
    report.append("")
    report.append("If single model recommended:")
    report.append("1. Switch to recommended model")
    report.append("2. Document decision rationale")
    report.append("3. Monitor real-world performance")
    report.append("")

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(report), encoding="utf-8")

    logger.info(f"\nComparison report saved to: {output_path}")


def main():
    """Run 3-way relevance comparison."""
    print("=" * 80)
    print("MODEL RELEVANCE COMPARISON: Qwen3-0.6B vs BGE-M3 vs CodeRankEmbed")
    print("=" * 80)
    print()
    print("This tool will:")
    print("1. Run 8 queries on all 3 models")
    print("2. Show top-5 results side-by-side")
    print("3. Generate a detailed comparison report")
    print()
    print("Goal: Compare general-purpose vs code-specific models")
    print("=" * 80)
    print()

    # Run queries on all 3 models
    print("Running queries on Qwen3-0.6B...")
    qwen3_results = run_search(
        model_name="Qwen/Qwen3-Embedding-0.6B",
        dimension=1024,
        queries=TEST_QUERIES,
        k=5
    )

    print("\nRunning queries on BGE-M3...")
    bge_m3_results = run_search(
        model_name="BAAI/bge-m3",
        dimension=1024,
        queries=TEST_QUERIES,
        k=5
    )

    print("\nRunning queries on CodeRankEmbed...")
    coderankembed_results = run_search(
        model_name="nomic-ai/CodeRankEmbed",
        dimension=768,
        queries=TEST_QUERIES,
        k=5
    )

    # Generate comparison report
    output_path = project_root / "analysis" / "model_relevance_comparison.md"
    print(f"\nGenerating 3-way comparison report...")
    generate_comparison_report(
        qwen3_results=qwen3_results,
        bge_m3_results=bge_m3_results,
        coderankembed_results=coderankembed_results,
        output_path=output_path
    )

    print("\n" + "=" * 80)
    print("COMPARISON COMPLETE")
    print("=" * 80)
    print(f"\nReport saved to: {output_path}")
    print()
    print("Next steps:")
    print("1. Open the report and review all 3 models' results")
    print("2. Check which model returns most relevant results per query")
    print("3. Fill in the manual assessment sections")
    print("4. Determine if smart routing or single model is optimal")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
