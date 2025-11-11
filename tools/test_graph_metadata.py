"""Test graph metadata in search results.

Usage:
    python tools/test_graph_metadata.py
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search.config import get_search_config, SearchConfigManager
from mcp_server.server import search_code


def test_graph_metadata():
    """Test graph metadata inclusion in search results."""

    print("=" * 70)
    print("Graph Metadata Test - Model Comparison")
    print("=" * 70)
    print()

    # Test queries that should have graph relationships
    test_queries = [
        {
            "query": "_validate_model_cache",
            "description": "Cache validation method (should have calls/called_by)"
        },
        {
            "query": "hybrid search BM25",
            "description": "Hybrid search method (should have calls)"
        }
    ]

    models = [
        ("Qodo/Qodo-Embed-1-1.5B", "1536d"),
        ("BAAI/bge-m3", "1024d")
    ]

    config_manager = SearchConfigManager()

    for model_name, dimension in models:
        print(f"\n{'=' * 70}")
        print(f"Testing Model: {model_name} ({dimension})")
        print(f"{'=' * 70}\n")

        # Switch model
        config = config_manager.load_config()
        config.embedding_model_name = model_name
        config_manager.save_config(config)
        print(f"Switched to {model_name}\n")

        for test in test_queries:
            print(f"Query: {test['description']}")
            print(f"  Input: \"{test['query']}\"")

            try:
                # Run search
                results = search_code(
                    query=test['query'],
                    k=3
                )

                print(f"  Found {len(results['results'])} results\n")

                # Check first result for graph metadata
                if results['results']:
                    first_result = results['results'][0]
                    print(f"  Top Result:")
                    print(f"    File: {first_result.get('file', 'N/A')}")
                    print(f"    Name: {first_result.get('name', 'N/A')}")
                    print(f"    Score: {first_result.get('score', 0.0):.2f}")

                    # Check graph metadata
                    if 'graph' in first_result:
                        graph = first_result['graph']
                        calls = graph.get('calls', [])
                        called_by = graph.get('called_by', [])
                        print(f"    Graph Metadata:")
                        print(f"      Calls: {len(calls)} functions")
                        if calls:
                            print(f"        {', '.join(calls[:3])}{'...' if len(calls) > 3 else ''}")
                        print(f"      Called By: {len(called_by)} callers")
                        if called_by:
                            print(f"        {', '.join(called_by[:3])}{'...' if len(called_by) > 3 else ''}")
                    else:
                        print(f"    Graph Metadata: NOT PRESENT")

            except Exception as e:
                print(f"  Error: {e}")

            print()

    print("=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    test_graph_metadata()
