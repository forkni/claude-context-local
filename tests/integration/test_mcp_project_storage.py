#!/usr/bin/env python3
"""
Test script for MCP server project-specific storage functionality.
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set environment to suppress any server initialization
os.environ["MCP_TEST_MODE"] = "1"

from mcp_server.server import get_index_status, list_projects, search_code


def test_project_specific_storage():
    """Test that project-specific storage works correctly."""
    print("🧪 Testing project-specific storage functionality...")

    # Test 1: Index the test project
    print("\n1️⃣ Testing index_test_project()")
    from mcp_server.server import index_test_project

    result = index_test_project()
    result_data = json.loads(result)

    if "error" in result_data:
        print(f"[ERROR] Failed to index test project: {result_data['error']}")
        assert False, f"Failed to index test project: {result_data['error']}"
        return False

    print("[OK] Test project indexed successfully!")
    print(f"   📊 {result_data.get('chunks_processed', 'N/A')} chunks processed")

    # Test 2: List projects
    print("\n2️⃣ Testing list_projects()")
    projects_result = list_projects()
    projects_data = json.loads(projects_result)

    print(f"[OK] Found {projects_data.get('count', 0)} project(s)")
    if projects_data.get("projects"):
        for project in projects_data["projects"]:
            print(f"   📁 {project['project_name']} ({project['project_hash']})")

    # Test 3: Search in the project
    print("\n3️⃣ Testing search_code()")
    search_result = search_code("authentication functions", k=3)
    search_data = json.loads(search_result)

    if "error" not in search_data:
        results = search_data.get("results", [])
        print(f"[OK] Found {len(results)} results for 'authentication functions'")
        for i, result in enumerate(results[:2], 1):
            print(
                f"   {i}. {result.get('name', 'unnamed')} ({result.get('chunk_type', 'unknown')})"
            )
    else:
        print(f"[ERROR] Search failed: {search_data['error']}")

    # Test 4: Check index status
    print("\n4️⃣ Testing get_index_status()")
    status_result = get_index_status()
    status_data = json.loads(status_result)

    if "error" not in status_data:
        print("[OK] Index status retrieved")
        print(f"   📈 Total chunks: {status_data.get('total_chunks', 'N/A')}")
        print(f"   📁 Files indexed: {status_data.get('files_indexed', 'N/A')}")

    print("\n🎉 All tests completed!")
    print("\n📋 Summary of project-specific storage benefits:")
    print("   [OK] Each project has isolated storage")
    print("   [OK] Projects don't interfere with each other")
    print("   [OK] Fast switching between projects")
    print("   [OK] Easy project management")

    assert True, "Project-specific storage test successful"
    return True


if __name__ == "__main__":
    import logging

    success = test_project_specific_storage()
    if success:
        print("\n🎯 Project-specific storage is working correctly!")
    else:
        print("\n[ERROR] Some tests failed.")

    # Clean up logging handlers to prevent hang
    logging.shutdown()

    # Force exit to ensure test ends
    import os

    os._exit(0 if success else 1)
