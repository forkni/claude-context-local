#!/usr/bin/env python3
"""
Project Switcher Helper
CLI wrapper for batch files to switch between indexed projects.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tool_handlers import handle_switch_project


def main():
    parser = argparse.ArgumentParser(
        description="Switch to a different indexed project for semantic code search"
    )
    parser.add_argument(
        "--path", required=True, help="Path to project directory to switch to"
    )

    args = parser.parse_args()

    # Validate path
    project_path = Path(args.path)
    if not project_path.exists():
        print(f"[ERROR] Path does not exist: {project_path}")
        return 1

    if not project_path.is_dir():
        print(f"[ERROR] Path is not a directory: {project_path}")
        return 1

    # Display configuration
    print("=" * 70)
    print("PROJECT SWITCHER")
    print("=" * 70)
    print(f"Switching to: {project_path}")
    print("=" * 70)
    print()

    try:
        print("[INFO] Switching project...")
        print()

        result = asyncio.run(handle_switch_project({"project_path": str(project_path)}))

        # Display results
        print()
        print("=" * 70)
        print("SWITCH RESULTS")
        print("=" * 70)

        if result.get("success"):
            print("[OK] Project switched successfully")
            print("[OK] Selection saved (will persist across restarts)")
            print()
            print(f"Message: {result.get('message', 'Unknown')}")

            # Show project info if available
            project_info = result.get("project_info", {})
            if project_info:
                print()
                print("Project Information:")
                print(f"  Name: {project_info.get('project_name', 'Unknown')}")
                print(f"  Directory: {project_info.get('directory', 'Unknown')}")

                # Show index statistics if available
                index_stats = project_info.get("index_stats", {})
                if index_stats:
                    print()
                    print("Index Statistics:")
                    print(f"  Total files: {index_stats.get('total_files', 0)}")
                    print(f"  Supported files: {index_stats.get('supported_files', 0)}")
                    print(f"  Total chunks: {index_stats.get('chunks_indexed', 0)}")

            print("=" * 70)
            return 0

        else:
            print("[ERROR] Project switch failed")
            error = result.get("error", "Unknown error")
            print(f"Error: {error}")

            # Show suggestion if available
            suggestion = result.get("suggestion", "")
            if suggestion:
                print()
                print(f"Suggestion: {suggestion}")

            print("=" * 70)
            return 1

    except Exception as e:
        print()
        print("=" * 70)
        print("[ERROR] Project switch failed with exception")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print("=" * 70)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
