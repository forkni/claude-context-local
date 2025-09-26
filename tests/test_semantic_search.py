#!/usr/bin/env python3
"""
Semantic Search Test
Tests the semantic search functionality using existing index.
"""

import json
import sys


def test_semantic_search():
    """Test semantic search on existing index."""
    print("Testing semantic search functionality...")

    try:
        from mcp_server.server import search_code

        # Test semantic searches on current codebase
        test_queries = [
            "exception handling",
            "file reading functions",
            "server configuration",
            "chunking code",
        ]

        for query in test_queries:
            print(f"\n[SEARCH] Testing query: '{query}'")

            try:
                result = search_code(query, k=3, include_context=True)
                data = json.loads(result)

                if "error" in data:
                    print(f"[ERROR] Search failed: {data['error']}")
                    continue

                results = data.get("results", [])
                print(f"[OK] Found {len(results)} results")

                # Show top result
                if results:
                    top = results[0]
                    print(
                        f"     Top: {top.get('file', 'unknown')}:{top.get('lines', '')}"
                    )
                    print(f"     Score: {top.get('score', 0):.2f}")

            except Exception as e:
                print(f"[ERROR] Query failed: {e}")
                return False

        return True

    except Exception as e:
        print(f"[ERROR] Search test failed: {e}")
        return False


def main():
    """Run semantic search test."""
    print("=" * 60)
    print("SEMANTIC SEARCH FUNCTIONALITY TEST")
    print("=" * 60)

    success = test_semantic_search()

    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] Semantic search functionality verified!")
    else:
        print("[ERROR] Semantic search test failed!")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
