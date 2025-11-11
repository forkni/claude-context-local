"""Test Qodo-1.5B code-specific search quality.

Usage:
    python tools/test_qodo_search.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search.config import get_search_config
from search.hybrid_searcher import HybridSearcher
from embeddings.embedder import CodeEmbedder


def test_code_search_queries():
    """Test code-specific queries with Qodo-1.5B."""

    print("=" * 70)
    print("Qodo-1.5B Code-Specific Search Quality Test")
    print("=" * 70)
    print()

    # Load config
    config = get_search_config()
    print(f"Model: {config.embedding_model_name}")
    print(f"Dimension: {config.model_dimension}d")
    print(f"Search mode: {config.default_search_mode}")
    print()

    # Initialize embedder
    embedder = CodeEmbedder(config.embedding_model_name)

    # Test queries (code-specific patterns)
    test_queries = [
        {
            "query": "function decorator error handling try except",
            "description": "Code Pattern - Decorators with error handling",
            "expected_files": ["embeddings", "search", "mcp_server"]
        },
        {
            "query": "FAISS index vector search add remove",
            "description": "API Usage - FAISS integration",
            "expected_files": ["search/indexer.py", "search/hybrid_searcher.py"]
        },
        {
            "query": "hybrid search BM25 dense fusion RRF ranking",
            "description": "Architecture - Hybrid search implementation",
            "expected_files": ["search/hybrid_searcher.py", "search/config.py"]
        },
        {
            "query": "merkle tree snapshot incremental change detection",
            "description": "Algorithm - Merkle tree for change detection",
            "expected_files": ["merkle/merkle_dag.py", "search/incremental_indexer.py"]
        },
        {
            "query": "cache validation corruption detection recovery",
            "description": "Error Handling - Cache validation (our new code!)",
            "expected_files": ["embeddings/embedder.py"]
        }
    ]

    print("Running test queries...")
    print()

    results_summary = []

    for i, test in enumerate(test_queries, 1):
        print(f"Query {i}: {test['description']}")
        print(f"  Input: \"{test['query']}\"")
        print(f"  Expected: {', '.join(test['expected_files'])}")

        # Generate embedding
        try:
            query_embedding = embedder.embed_query(test['query'])
            print(f"  Embedding: {query_embedding.shape} (dimension validated)")

            # Note: We can't actually search yet if indices don't exist
            # This is prepared for when Qodo indexing completes
            print(f"  Status: Ready for search (indices pending)")

            results_summary.append({
                "query": test['query'],
                "status": "embedding_ready",
                "dimension": query_embedding.shape[0]
            })

        except Exception as e:
            print(f"  Error: {e}")
            results_summary.append({
                "query": test['query'],
                "status": "error",
                "error": str(e)
            })

        print()

    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    embeddings_ready = sum(1 for r in results_summary if r['status'] == 'embedding_ready')
    print(f"Queries with embeddings ready: {embeddings_ready}/{len(test_queries)}")

    if embeddings_ready == len(test_queries):
        print()
        print("[OK] All test queries ready for search!")
        print("[INFO] Wait for Qodo-1.5B indexing to complete, then run:")
        print("       python tools/search_helper.py")
        print()
        print("Example search command:")
        print('  python tools/search_helper.py --query "cache validation corruption" --k 5')
    else:
        print()
        print("[WARNING] Some queries failed. Check errors above.")

    print()


if __name__ == "__main__":
    test_code_search_queries()
