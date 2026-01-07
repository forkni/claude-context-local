#!/usr/bin/env python3
"""
Project Indexer
Indexes Python scripts in a project for semantic search.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict

# Add project root directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.server import index_directory


def find_projects(search_path: str = "C:\\Projects") -> list:
    """
    Find projects by looking for common project files (.toe, .py, .js, .ts, etc.).

    Args:
        search_path: Root path to search for projects

    Returns:
        List of project directories
    """
    projects = []
    search_path = Path(search_path)

    if not search_path.exists():
        print(f"Search path does not exist: {search_path}")
        return projects

    print(f"Searching for projects in: {search_path}")

    # Look for project files (TouchDesigner .toe, Python, JS, TS, etc.)
    project_extensions = [
        "*.toe",
        "*.py",
        "*.js",
        "*.ts",
        "*.tsx",
        "*.jsx",
        "*.go",
        "*.rs",
        "*.java",
        "*.c",
        "*.cpp",
        "*.cs",
    ]

    found_dirs = set()

    for ext in project_extensions:
        for project_file in search_path.rglob(ext):
            project_dir = project_file.parent

            if project_dir in found_dirs:
                continue

            found_dirs.add(project_dir)

            # Count code files
            code_files = []
            for code_ext in project_extensions:
                code_files.extend(list(project_dir.rglob(code_ext)))

            if code_files:
                projects.append(
                    {
                        "project_dir": str(project_dir),
                        "main_file": str(project_file),
                        "code_files": len(code_files),
                        "name": project_dir.name,
                    }
                )

    return projects


def index_project(
    project_path: str, include_subfolders: bool = True, force_full: bool = False
) -> Dict:
    """
    Index a project focusing on code files.

    Args:
        project_path: Path to project directory
        include_subfolders: Whether to include code files in subfolders
        force_full: Force full reindex, bypassing Merkle snapshot change detection

    Returns:
        Dictionary with indexing results
    """
    project_path = Path(project_path).resolve()

    if not project_path.exists():
        return {"error": f"Project path does not exist: {project_path}"}

    # Look for common project indicators
    project_indicators = (
        list(project_path.glob("*.toe"))
        + list(project_path.glob("package.json"))
        + list(project_path.glob("pyproject.toml"))
        + list(project_path.glob("Cargo.toml"))
    )

    if project_indicators:
        print(f"Found project indicator: {project_indicators[0].name}")
    else:
        print(f"No specific project file found in {project_path}")
        print("Indexing as a general code directory.")

    # Count code files (excluding common build/dependency directories)
    code_extensions = [
        "*.py",
        "*.js",
        "*.ts",
        "*.tsx",
        "*.jsx",
        "*.go",
        "*.rs",
        "*.java",
        "*.c",
        "*.cpp",
        "*.cs",
    ]

    # Import ignored directories from chunker
    from chunking.multi_language_chunker import MultiLanguageChunker

    ignored_dirs = MultiLanguageChunker.DEFAULT_IGNORED_DIRS

    code_files = []

    for ext in code_extensions:
        if include_subfolders:
            all_files = list(project_path.rglob(ext))
            # Filter out files in ignored directories (.venv, node_modules, etc.)
            code_files.extend(
                [
                    f
                    for f in all_files
                    if not any(part in ignored_dirs for part in f.parts)
                ]
            )
        else:
            code_files.extend(list(project_path.glob(ext)))

    print(f"Found {len(code_files)} code files to index")

    if not code_files:
        return {
            "error": "No code files found in project directory",
            "suggestion": "Make sure the directory contains code files (Python, JavaScript, TypeScript, etc.)",
        }

    # Show file breakdown
    for code_file in code_files[:10]:  # Show first 10 files
        rel_path = code_file.relative_to(project_path)
        print(f"  - {rel_path}")

    if len(code_files) > 10:
        print(f"  ... and {len(code_files) - 10} more files")

    print(f"\nIndexing project: {project_path.name}")
    if force_full:
        print("[INFO] Forcing full reindex (bypassing Merkle snapshot)")

    # Use the MCP server's index_directory function
    result_data = index_directory(
        str(project_path),
        project_name=f"Proj_{project_path.name}",
        incremental=not force_full,
    )

    try:
        if "error" not in result_data:
            print("[OK] Indexing completed successfully!")
            print(f"   Files processed: {result_data.get('files_added', 0)}")
            print(f"   Chunks created: {result_data.get('chunks_added', 0)}")
            print(f"   Time taken: {result_data.get('time_taken', 0):.2f}s")
        else:
            print(f"[ERROR] Indexing failed: {result_data['error']}")

        return result_data

    except json.JSONDecodeError:
        return {"error": "Failed to parse indexing results"}


def main():
    """Entry point for project indexer CLI."""
    parser = argparse.ArgumentParser(description="Index project for semantic search")
    parser.add_argument("project_path", nargs="?", help="Path to project directory")
    parser.add_argument(
        "--find",
        "-f",
        metavar="SEARCH_PATH",
        help="Find projects in the specified directory",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List all found projects",
    )
    parser.add_argument(
        "--no-subfolders",
        action="store_true",
        help="Don't include code files in subfolders",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full reindex, bypassing Merkle snapshot change detection (use if 'No changes detected' occurs)",
    )

    args = parser.parse_args()

    if args.find or args.list:
        # Find projects
        search_path = args.find or "C:\\Projects"
        projects = find_projects(search_path)

        if not projects:
            print("No projects found.")
            return

        print(f"\nFound {len(projects)} projects:")
        for i, project in enumerate(projects, 1):
            print(f"{i:2d}. {project['name']}")
            print(f"     Path: {project['project_dir']}")
            print(f"     Code files: {project['code_files']}")
            print()

        if not args.list:
            try:
                choice = input(
                    "Enter project number to index (or press Enter to exit): "
                ).strip()
                if choice:
                    idx = int(choice) - 1
                    if 0 <= idx < len(projects):
                        project = projects[idx]
                        print(f"\nIndexing project: {project['name']}")
                        index_project(
                            project["project_dir"], not args.no_subfolders, args.force
                        )
                    else:
                        print("Invalid project number.")
            except (ValueError, KeyboardInterrupt):
                print("Exiting...")

        return

    if not args.project_path:
        # Default to current directory
        args.project_path = os.getcwd()
        print(
            f"No project path specified, using current directory: {args.project_path}"
        )

    # Index the specified project
    index_project(args.project_path, not args.no_subfolders, args.force)


if __name__ == "__main__":
    main()
