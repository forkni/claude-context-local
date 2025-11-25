#!/usr/bin/env python3
"""
MCP Server Functionality Test
Tests basic MCP server import and functionality without full workflow.
"""
# ruff: noqa: I001

import asyncio
import sys
from pathlib import Path


def _mcp_imports_check():
    """Check that all MCP server modules can be imported."""
    print("Testing MCP server imports...")

    try:
        from mcp_server.tool_handlers import handle_find_similar_code  # noqa: F401
        from mcp_server.tool_handlers import handle_get_index_status  # noqa: F401
        from mcp_server.tool_handlers import handle_index_directory  # noqa: F401
        from mcp_server.tool_handlers import handle_list_projects  # noqa: F401
        from mcp_server.tool_handlers import handle_search_code  # noqa: F401
        from mcp_server.tool_handlers import handle_switch_project  # noqa: F401

        print("[OK] MCP server functions imported successfully")
        return True
    except ImportError as e:
        print(f"[ERROR] Failed to import MCP server: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error during import: {e}")
        return False


def test_mcp_imports():
    """Test that all MCP server modules can be imported."""
    assert _mcp_imports_check(), "MCP import check failed"


def _index_status_check():
    """Check get_index_status function."""
    print("\nTesting index status...")

    try:
        from mcp_server.tool_handlers import handle_get_index_status

        result = asyncio.run(handle_get_index_status({}))

        # result is already a dict, no parsing needed
        print(f"[OK] Index status retrieved: {len(result)} keys")

        if "index_statistics" in result:
            stats = result["index_statistics"]
            print(f"     Total chunks: {stats.get('total_chunks', 0)}")
            print(f"     Total files: {stats.get('total_files', 0)}")

        return True
    except Exception as e:
        print(f"[ERROR] Index status test failed: {e}")
        return False


def test_index_status():
    """Test get_index_status function."""
    assert _index_status_check(), "Index status check failed"


def _chunking_core_check():
    """Check core chunking functionality."""
    print("\nTesting chunking functionality...")

    try:
        # Create a simple test
        from tempfile import TemporaryDirectory

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

        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text(test_code)

            chunker = MultiLanguageChunker(Path(tmpdir))
            chunks = chunker.chunk_file(str(test_file))

            print(f"[OK] Chunking test completed: {len(chunks)} chunks generated")
            # Auto cleanup when context exits

        return True
    except Exception as e:
        print(f"[ERROR] Chunking test failed: {e}")
        return False


def test_chunking_core():
    """Test core chunking functionality."""
    assert _chunking_core_check(), "Chunking core check failed"


def main():
    """Run all functionality tests."""
    print("=" * 60)
    print("MCP SERVER FUNCTIONALITY TEST")
    print("=" * 60)

    tests = [
        ("Import Test", _mcp_imports_check),
        ("Index Status Test", _index_status_check),
        ("Chunking Test", _chunking_core_check),
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
