"""List indexed projects grouped by path with model details.

STANDALONE VERSION - No ML imports to avoid PyTorch crash.
Uses only Python stdlib.
"""

import json
import os
import sys
from pathlib import Path


def get_storage_dir():
    """Get storage directory without importing from mcp_server.

    Replicates logic from mcp_server.server.get_storage_dir().
    """
    storage_path = os.getenv(
        "CODE_SEARCH_STORAGE", str(Path.home() / ".claude_code_search")
    )
    return Path(storage_path)


def main():
    try:
        storage = get_storage_dir()
    except (AttributeError, KeyError, RuntimeError):
        # Storage dir doesn't exist - no projects
        print("No indexed projects found.\n")
        return

    projects_dir = storage / "projects"

    if not projects_dir.exists():
        print("No indexed projects found.\n")
        return

    projects_by_path = {}

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        info_file = project_dir / "project_info.json"
        if not info_file.exists():
            continue

        try:
            with open(info_file, encoding="utf-8") as f:
                info = json.load(f)
        except (json.JSONDecodeError, KeyError):
            # Skip malformed project_info.json
            continue

        path = info.get("project_path")
        if not path:
            continue

        if path not in projects_by_path:
            projects_by_path[path] = {
                "name": info.get("project_name", "Unknown"),
                "path": path,
                "models": [],
            }

        # Get model short name and dimension
        model_full = info.get("embedding_model", "unknown")
        model_short = model_full.split("/")[-1]
        dimension = info.get("model_dimension", 0)

        projects_by_path[path]["models"].append(f"{model_short} ({dimension}d)")

    if not projects_by_path:
        print("No indexed projects found.\n")
        return

    total_indices = sum(len(p["models"]) for p in projects_by_path.values())
    print(
        f"Found {len(projects_by_path)} projects with {total_indices} model indices:\n"
    )

    for i, (_path, info) in enumerate(projects_by_path.items(), 1):
        print(f"  {i}. {info['name']}")
        print(f"     Path: {info['path']}")
        print(f"     Models: {', '.join(info['models'])}")
        print()


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError):
        # Silent exit for batch script - no projects if error
        print("No indexed projects found.\n")
        sys.exit(0)
