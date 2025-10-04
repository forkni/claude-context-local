#!/usr/bin/env python3
"""
MCP Server Functionality Test
Tests basic MCP server import and functionality without full workflow.
"""

import json
import sys
from pathlib import Path


def test_mcp_imports():
    """Test that all MCP server modules can be imported."""
    print("Testing MCP server imports...")

    try:
        from mcp_server.server import (find_similar_code, get_index_status,  # noqa: F401
                                       index_directory, list_projects,  # noqa: F401
                                       search_code, switch_project)  # noqa: F401

        print("[OK] MCP server functions imported successfully")
        return True
    except ImportError as e:
        print(f"[ERROR] Failed to import MCP server: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error during import: {e}")
        return False


def test_index_status():
    """Test get_index_status function."""
    print("\nTesting index status...")

    try:
        from mcp_server.server import get_index_status

        result = get_index_status()

        # Parse result
        data = json.loads(result)
        print(f"[OK] Index status retrieved: {len(data)} keys")

        if "index_statistics" in data:
            stats = data["index_statistics"]
            print(f"     Total chunks: {stats.get('total_chunks', 0)}")
            print(f"     Total files: {stats.get('total_files', 0)}")

        return True
    except Exception as e:
        print(f"[ERROR] Index status test failed: {e}")
        return False


def test_chunking_core():
    """Test core chunking functionality."""
    print("\nTesting chunking functionality...")

    try:
        # Create a simple test
        import tempfile

        from chunking.multi_language_chunker import MultiLanguageChunker

        test_code = '''
def hello_world():
    """Simple test function."""
    return "Hello, World!"

class TestClass:
    """Simple test class."""
    def __init__(self):
        self.value = 42
'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_code)
            f.flush()

            chunker = MultiLanguageChunker(Path(f.name).parent)
            chunks = chunker.chunk_file(f.name)

            print(f"[OK] Chunking test completed: {len(chunks)} chunks generated")

            # Clean up
            Path(f.name).unlink()

        return True
    except Exception as e:
        print(f"[ERROR] Chunking test failed: {e}")
        return False


def main():
    """Run all functionality tests."""
    print("=" * 60)
    print("MCP SERVER FUNCTIONALITY TEST")
    print("=" * 60)

    tests = [
        ("Import Test", test_mcp_imports),
        ("Index Status Test", test_index_status),
        ("Chunking Test", test_chunking_core),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"[FAIL] {test_name}")
        except Exception as e:
            print(f"[FAIL] {test_name}: {e}")

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("[SUCCESS] All MCP functionality tests passed!")
        return True
    else:
        print(f"[WARNING] {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
