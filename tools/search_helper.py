#!/usr/bin/env python3
"""
Code Search Helper
Interactive tool for searching code using semantic search.
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.server import (
    find_similar_code,
    get_index_status,
    list_projects,
    search_code,
)


class CodeSearchHelper:
    """Interactive search helper for code projects."""

    def __init__(self):
        self.current_project = None

    def show_welcome(self):
        """Show welcome message and help."""
        print("=" * 60)
        print("Semantic Code Search Helper")
        print("=" * 60)
        print("This tool helps you search code using AI.")
        print("You can ask questions in natural language to find relevant code.")
        print()
        print("Examples of searches:")
        print("  - 'callback functions for buttons'")
        print("  - 'parameter change handlers'")
        print("  - 'class initialization'")
        print("  - 'data input output processing'")
        print("  - 'error handling in scripts'")
        print()

    def show_status(self):
        """Show current index status."""
        try:
            status_result = get_index_status()
            status_data = json.loads(status_result)

            if "error" in status_data:
                print(f"[ERROR] Status check failed: {status_data['error']}")
                return

            stats = status_data.get("index_statistics", {})
            model_info = status_data.get("model_information", {})

            print("[INFO] Current Index Status:")
            print(f"   Total chunks: {stats.get('total_chunks', 0)}")
            print(f"   Total files: {stats.get('total_files', 0)}")
            print(f"   Model status: {model_info.get('status', 'unknown')}")

            if model_info.get("status") == "loaded":
                print(f"   Model: {model_info.get('model_name', 'unknown')}")

        except Exception as e:
            print(f"[ERROR] Failed to get status: {e}")

    def show_projects(self):
        """Show available indexed projects."""
        try:
            projects_result = list_projects()
            projects_data = json.loads(projects_result)

            if "error" in projects_data:
                print(f"[ERROR] Failed to list projects: {projects_data['error']}")
                return

            projects = projects_data.get("projects", [])
            if not projects:
                print("[DIR] No indexed projects found.")
                print("   Use index_project.py to index a project first.")
                return

            print("[DIR] Available Indexed Projects:")
            for i, project in enumerate(projects, 1):
                name = project.get("project_name", "Unknown")
                path = project.get("project_path", "Unknown")
                stats = project.get("index_stats", {})
                chunks = stats.get("total_chunks", 0)

                print(f"   {i}. {name}")
                print(f"      Path: {path}")
                print(f"      Chunks: {chunks}")
                print()

        except Exception as e:
            print(f"[ERROR] Failed to list projects: {e}")

    def search_interactive(self):
        """Run interactive search session."""
        self.show_welcome()
        self.show_status()
        print()
        self.show_projects()
        print()

        print("[INFO] Tips:")
        print("   - Type 'help' for search examples")
        print("   - Type 'status' to check index status")
        print("   - Type 'projects' to list indexed projects")
        print("   - Type 'quit' or 'exit' to quit")
        print("   - Press Ctrl+C to quit anytime")
        print()

        try:
            while True:
                query = input("[SEARCH] Search query (or command): ").strip()

                if not query:
                    continue

                if query.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break

                if query.lower() == "help":
                    self.show_help()
                    continue

                if query.lower() == "status":
                    self.show_status()
                    continue

                if query.lower() == "projects":
                    self.show_projects()
                    continue

                if query.lower().startswith("similar "):
                    chunk_id = query[8:].strip()
                    if chunk_id:
                        self.find_similar(chunk_id)
                    else:
                        print("Usage: similar <chunk_id>")
                    continue

                # Perform search
                self.search(query)
                print()

        except KeyboardInterrupt:
            print("\nGoodbye!")

    def show_help(self):
        """Show search help and examples."""
        print()
        print("[SEARCH] Code Search Examples:")
        print()
        print("General Patterns:")
        print("  - 'callback functions'")
        print("  - 'parameter handling'")
        print("  - 'class initialization'")
        print("  - 'data processing'")
        print()
        print("Specific Programming Tasks:")
        print("  - 'button callback onclick'")
        print("  - 'parameter value change handler'")
        print("  - 'async function with error handling'")
        print("  - 'class constructor initialization'")
        print("  - 'input output processing'")
        print("  - 'custom function creation'")
        print("  - 'timer callback handling'")
        print("  - 'event listener setup'")
        print("  - 'error debugging patterns'")
        print()
        print("Commands:")
        print("  - help - Show this help")
        print("  - status - Check index status")
        print("  - projects - List indexed projects")
        print("  - similar <chunk_id> - Find similar code")
        print("  - quit/exit - Exit the program")
        print()

    def search(self, query: str, k: int = 5):
        """Perform search and display results."""
        try:
            print(f"Searching for: '{query}'...")

            result = search_code(
                query=query, k=k, include_context=True, auto_reindex=True
            )

            result_data = json.loads(result)

            if "error" in result_data:
                print(f"[ERROR] Search failed: {result_data['error']}")
                return

            results = result_data.get("results", [])

            if not results:
                print("[INFO] No results found.")
                print("[INFO] Try:")
                print(
                    "   - More general terms (e.g., 'callback' instead of 'onValueChange')"
                )
                print(
                    "   - Different phrasing (e.g., 'button handling' instead of 'button press')"
                )
                print("   - Check if the project is indexed with index_project.py")
                return

            print(f"[OK] Found {len(results)} results:")
            print()

            for i, result in enumerate(results, 1):
                file_path = result.get("file", "")
                lines = result.get("lines", "")
                chunk_type = result.get("kind", "")
                score = result.get("score", 0)
                name = result.get("name", "")
                chunk_id = result.get("chunk_id", "")
                snippet = result.get("snippet", "")

                print(f"{i:2d}. [FILE] {file_path}:{lines}")
                print(f"    Type: {chunk_type}")
                if name:
                    print(f"    Name: {name}")
                print(f"    Score: {score:.2f}")
                if snippet:
                    print(f"    Code: {snippet}")
                print(f"    ID: {chunk_id}")
                print()

        except Exception as e:
            print(f"[ERROR] Search error: {e}")

    def find_similar(self, chunk_id: str):
        """Find code similar to a specific chunk."""
        try:
            print(f"Finding code similar to: {chunk_id}")

            result = find_similar_code(chunk_id, k=5)
            result_data = json.loads(result)

            if "error" in result_data:
                print(f"[ERROR] Similar search failed: {result_data['error']}")
                return

            similar_chunks = result_data.get("similar_chunks", [])

            if not similar_chunks:
                print("[INFO] No similar code found.")
                return

            print(f"[OK] Found {len(similar_chunks)} similar chunks:")
            print()

            for i, chunk in enumerate(similar_chunks, 1):
                file_path = chunk.get("file_path", "")
                lines = chunk.get("lines", "")
                chunk_type = chunk.get("chunk_type", "")
                name = chunk.get("name", "")
                score = chunk.get("similarity_score", 0)
                preview = chunk.get("content_preview", "")

                print(f"{i:2d}. [FILE] {file_path}:{lines}")
                print(f"    Type: {chunk_type}")
                if name:
                    print(f"    Name: {name}")
                print(f"    Similarity: {score:.3f}")
                if preview:
                    # Show first line of preview
                    first_line = preview.split("\n")[0].strip()
                    if first_line:
                        print(f"    Code: {first_line}")
                print()

        except Exception as e:
            print(f"[ERROR] Similar search error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Semantic Code Search Helper")
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query (if not provided, starts interactive mode)",
    )
    parser.add_argument(
        "-k",
        "--results",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    parser.add_argument(
        "--similar",
        metavar="CHUNK_ID",
        help="Find code similar to the specified chunk ID",
    )

    args = parser.parse_args()

    helper = CodeSearchHelper()

    if args.similar:
        helper.find_similar(args.similar)
    elif args.query:
        helper.search(args.query, args.results)
    else:
        helper.search_interactive()


if __name__ == "__main__":
    main()
