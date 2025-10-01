#!/usr/bin/env python3
"""
Test script to verify all critical dependencies are installed correctly.
Part of TouchDesigner MCP Integration testing process.
"""

import importlib
import sys


def test_imports():
    """Test importing all critical modules."""
    modules_to_test = [
        "chunking.multi_language_chunker",
        "embeddings.embedder",
        "search.indexer",
        "search.searcher",
        "sentence_transformers",
        "faiss",
        "tree_sitter",
        "sqlitedict",
        "mcp",
        "fastmcp",
        "rich",
        "click",
    ]

    results = []
    success_count = 0

    print(f"Testing Python {sys.version}")
    print("=" * 50)

    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            results.append(f"OK {module_name}")
            success_count += 1
        except Exception as e:
            results.append(f"FAIL {module_name}: {e}")

    print("\n".join(results))
    print("=" * 50)
    print(
        f"Success: {success_count}/{len(modules_to_test)} modules imported successfully"
    )

    if success_count == len(modules_to_test):
        print("All dependencies installed correctly!")
        assert True
    else:
        print("Some dependencies failed to import")
        assert False, (
            f"Only {success_count}/{len(modules_to_test)} modules imported successfully"
        )


if __name__ == "__main__":
    test_imports()
