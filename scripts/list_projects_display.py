"""List indexed projects grouped by path with model details.

STANDALONE VERSION - No ML imports to avoid PyTorch crash.
Uses only Python stdlib (``--freshness`` is the exception: it loads the
server's index check, see ``project_status.index_statuses``).

``--scip`` adds a ``SCIP:`` line (Rust SCIP table state) and ``--freshness``
an ``Index:`` line per model (search index current or stale).
"""

import argparse
import sys

import project_status
from list_projects_parseable import collect_projects, get_storage_dir


def main(argv: list[str] | None = None) -> None:
    """Print each indexed project with its models (and SCIP/index lines on request)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scip", action="store_true", help="show the SCIP status")
    parser.add_argument(
        "--freshness", action="store_true", help="show the search-index status"
    )
    args = parser.parse_args(argv)

    try:
        storage = get_storage_dir()
    except (AttributeError, KeyError, RuntimeError):
        # Storage dir doesn't exist - no projects
        print("No indexed projects found.\n")
        return

    projects = list(collect_projects(storage).values())
    if not projects:
        print("No indexed projects found.\n")
        return

    index_lines: list[list[tuple[str, str]]] = [[] for _ in projects]
    if args.freshness:
        print("[INFO] Checking index freshness...\n", flush=True)
        index_lines = project_status.index_statuses(
            [(p["path"], p["model_dims"]) for p in projects]
        )

    paint = project_status.colourize if project_status.enable_ansi() else str
    total_indices = sum(len(p["models"]) for p in projects)
    print(f"Found {len(projects)} projects with {total_indices} model indices:\n")

    for i, (info, statuses) in enumerate(zip(projects, index_lines, strict=True), 1):
        print(f"  {i}. {info['name']}")
        print(f"     Path: {info['path']}")
        print(f"     Models: {', '.join(info['models'])}")
        if args.scip:
            scip = project_status.scip_text(storage, info["path"], info["dirs"])
            if scip is not None:
                print(f"     SCIP: {paint(scip)}")
        for name, text in statuses:
            label = "Index" if len(statuses) == 1 else f"Index ({name})"
            print(f"     {label}: {paint(text)}")
        print()


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError):
        # Silent exit for batch script - no projects if error
        print("No indexed projects found.\n")
        sys.exit(0)
