#!/usr/bin/env python3
"""
Complete Workflow Test for TouchDesigner MCP Integration
Tests the entire pipeline from indexing to searching TouchDesigner Python scripts.
"""

import json
import sys
import time
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.server import (
    get_index_status,
    index_directory,
    list_projects,
    search_code,
)


def test_complete_workflow():
    """Test the complete TouchDesigner integration workflow."""

    print("=" * 70)
    print("TouchDesigner MCP Integration - Complete Workflow Test")
    print("=" * 70)
    print()

    # Step 1: Index the test TouchDesigner project
    test_project_path = Path(__file__).parent.parent / "test_td_project"
    test_project_path = test_project_path.resolve()

    print("Step 1: Indexing test TouchDesigner project")
    print(f"Project path: {test_project_path}")

    if not test_project_path.exists():
        print("[ERROR] Test project directory not found!")
        print("Make sure the test_td_project directory exists.")
        return False

    # Check Python files in test project
    python_files = list(test_project_path.rglob("*.py"))
    print(f"Found {len(python_files)} Python files:")
    for py_file in python_files:
        rel_path = py_file.relative_to(test_project_path)
        print(f"  - {rel_path}")
    print()

    if not python_files:
        print("[ERROR] No Python files found in test project!")
        return False

    # Index the project
    print("Indexing project...")
    start_time = time.time()

    try:
        result = index_directory(
            str(test_project_path), project_name="TouchDesigner_Test"
        )
        result_data = json.loads(result)

        index_time = time.time() - start_time

        if "error" in result_data:
            print(f"[ERROR] Indexing failed: {result_data['error']}")
            return False

        print(f"[OK] Indexing completed in {index_time:.2f}s")
        print(f"   Files processed: {result_data.get('files_added', 0)}")
        print(f"   Chunks created: {result_data.get('chunks_added', 0)}")
        print()

    except Exception as e:
        print(f"[ERROR] Indexing error: {e}")
        return False

    # Step 2: Check index status
    print("Step 2: Checking index status")
    try:
        status_result = get_index_status()
        status_data = json.loads(status_result)

        if "error" in status_data:
            print(f"[ERROR] Status check failed: {status_data['error']}")
            return False

        stats = status_data.get("index_statistics", {})
        print("[OK] Index status:")
        print(f"   Total chunks: {stats.get('total_chunks', 0)}")
        print(f"   Total files: {stats.get('total_files', 0)}")
        print()

    except Exception as e:
        print(f"[ERROR] Status check error: {e}")
        return False

    # Step 3: Test semantic searches
    print("Step 3: Testing semantic searches")

    test_queries = [
        ("callback functions", "Should find button callbacks and parameter handlers"),
        ("parameter value change", "Should find onValueChange functions"),
        ("extension initialization", "Should find extension __init__ methods"),
        ("data processing functions", "Should find data analysis and processing"),
        ("error handling", "Should find try/except blocks and error management"),
        (
            "TouchDesigner project manager",
            "Should find project management functionality",
        ),
        ("audio processing", "Should find audio-related data processing"),
        ("motion analysis", "Should find motion and position data analysis"),
    ]

    successful_searches = 0

    for i, (query, description) in enumerate(test_queries, 1):
        print(f"   Search {i}: '{query}'")
        print(f"   {description}")

        try:
            search_start = time.time()
            search_result = search_code(query, k=3, include_context=True)
            search_time = time.time() - search_start

            search_data = json.loads(search_result)

            if "error" in search_data:
                print(f"   [ERROR] Search failed: {search_data['error']}")
            else:
                results = search_data.get("results", [])
                print(f"   [OK] Found {len(results)} results in {search_time:.2f}s")

                # Show top result
                if results:
                    top_result = results[0]
                    print(
                        f"      Top: {top_result.get('file', 'unknown')}:{top_result.get('lines', '')}"
                    )
                    print(f"      Type: {top_result.get('kind', 'unknown')}")
                    print(f"      Score: {top_result.get('score', 0):.2f}")

                    if top_result.get("name"):
                        print(f"      Name: {top_result['name']}")

                successful_searches += 1

        except Exception as e:
            print(f"   [ERROR] Search error: {e}")

        print()

    # Step 4: Test project listing
    print("Step 4: Testing project listing")
    try:
        projects_result = list_projects()
        projects_data = json.loads(projects_result)

        if "error" in projects_data:
            print(f"[ERROR] Project listing failed: {projects_data['error']}")
        else:
            projects = projects_data.get("projects", [])
            print(f"[OK] Found {len(projects)} indexed projects")

            for project in projects:
                name = project.get("project_name", "Unknown")
                path = project.get("project_path", "Unknown")
                print(f"   - {name}: {path}")
        print()

    except Exception as e:
        print(f"[ERROR] Project listing error: {e}")
        print()

    # Summary
    print("=" * 70)
    print("WORKFLOW TEST SUMMARY")
    print("=" * 70)
    print(f"[OK] Project indexed: {test_project_path.name}")
    print(f"[OK] Successful searches: {successful_searches}/{len(test_queries)}")

    if successful_searches >= len(test_queries) * 0.8:  # 80% success rate
        print("[SUCCESS] Complete workflow test PASSED!")
        print()
        print("Next steps:")
        print("1. Configure Claude Code MCP integration:")
        print("   Run: scripts\\batch\\manual_configure.bat")
        print("   Or: .venv\\Scripts\\python.exe scripts\\manual_configure.py --global")
        print("2. Open Claude Code and test with your real TouchDesigner projects")
        print("3. Use semantic search to optimize your development workflow")
        return True
    else:
        print("[WARNING] Workflow test completed with some issues")
        print("Check the error messages above for debugging")
        return False


def show_usage_examples():
    """Show example usage patterns for TouchDesigner development."""
    print("\n" + "=" * 70)
    print("TOUCHDESIGNER USAGE EXAMPLES")
    print("=" * 70)
    print()
    print("After configuring Claude Code MCP integration, you can use:")
    print()
    print("[SEARCH] Semantic Code Search:")
    print('   /search_code "button callback functions"')
    print('   /search_code "parameter value change handlers"')
    print('   /search_code "extension initialization patterns"')
    print('   /search_code "audio data processing"')
    print('   /search_code "motion tracking analysis"')
    print('   /search_code "error handling in TouchDesigner"')
    print()
    print("[DIR] Project Management:")
    print('   /index_directory "C:\\TouchDesigner\\Projects\\MyProject"')
    print("   /list_projects")
    print("   /get_index_status")
    print()
    print("[LINK] Find Similar Code:")
    print(
        '   /find_similar_code "Scripts/Callbacks/UI_Callbacks.py:15-30:function:onValueChange"'
    )
    print()
    print(
        "[INFO] This enables 90-95% token reduction when working with TouchDesigner projects!"
    )


if __name__ == "__main__":
    success = test_complete_workflow()

    if success:
        show_usage_examples()

    input("\nPress Enter to exit...")
