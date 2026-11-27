"""List indexed projects in selection format for batch scripts.

STANDALONE VERSION - No ML imports to avoid PyTorch crash.
Uses only Python stdlib (``--freshness`` is the exception: it loads the
server's index check, see ``project_status.index_statuses``).

Output format: index|project_name|project_path|models_list|scip|index_status
Example: 1|myproject|F:/Projects/MyProject|bge-m3 (1024d)|up to date (made ...)|-

``scip`` needs ``--scip`` and ``index_status`` needs ``--freshness``. A field
with no text is ``-``, never empty: ``for /f`` in the launcher merges empty
fields and would shift the next one into its place.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import project_status


EMPTY = "-"


def get_storage_dir():
    """Get storage directory without importing from mcp_server.

    Replicates logic from mcp_server.server.get_storage_dir().
    """
    storage_path = os.getenv(
        "CODE_SEARCH_STORAGE", str(Path.home() / ".claude_code_search")
    )
    return Path(storage_path)


def collect_projects(storage: Path) -> dict[str, dict]:
    """Indexed projects by path: name, model labels, (model, dim) pairs, storage folders."""
    projects_dir = storage / "projects"
    if not projects_dir.exists():
        return {}

    projects_by_path: dict[str, dict] = {}
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
                "hash": info.get("project_hash", ""),
                "models": [],
                "model_dims": [],
                "dirs": [],
            }

        # Get model short name and dimension
        model_full = info.get("embedding_model", "unknown")
        model_short = model_full.split("/")[-1]
        dimension = info.get("model_dimension", 0)

        entry = projects_by_path[path]
        entry["models"].append(f"{model_short} ({dimension}d)")
        entry["model_dims"].append((model_full, dimension))
        entry["dirs"].append(project_dir)
    return projects_by_path


def main(argv: list[str] | None = None) -> None:
    """Print one ``|``-separated picker line per indexed project (format above)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scip", action="store_true", help="add the SCIP status")
    parser.add_argument(
        "--freshness", action="store_true", help="add the search-index status"
    )
    args = parser.parse_args(argv)

    try:
        storage = get_storage_dir()
    except (AttributeError, KeyError, RuntimeError):
        # Storage dir doesn't exist - silent exit
        return

    projects = list(collect_projects(storage).values())
    index_fields = [EMPTY] * len(projects)
    if args.freshness and projects:
        statuses = project_status.index_statuses(
            [(p["path"], p["model_dims"]) for p in projects]
        )
        index_fields = [project_status.index_field(s) or EMPTY for s in statuses]

    # Output format: index|name|path|models|scip|index_status
    for i, (info, index_text) in enumerate(zip(projects, index_fields, strict=True), 1):
        models_str = ", ".join(info["models"])
        scip = EMPTY
        if args.scip:
            scip = (
                project_status.scip_text(storage, info["path"], info["dirs"]) or EMPTY
            )
        print(f"{i}|{info['name']}|{info['path']}|{models_str}|{scip}|{index_text}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError):
        # Silent exit for batch script error handling
        sys.exit(0)
