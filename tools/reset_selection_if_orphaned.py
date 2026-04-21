#!/usr/bin/env python3
"""Reset project_selection.json if the active selection's path has no remaining indices.

Reads CGW_PROJ_PATH from env (set by start_mcp_server.cmd before calling).
Silent on the happy path; prints one [INFO] line when a reset occurs.
Tracebacks propagate — any import error signals a real bug worth surfacing.
"""
import json
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.project_persistence import (
    clear_project_selection,
    load_project_selection,
)
from mcp_server.storage_manager import get_storage_dir


def main() -> int:
    proj_path = os.environ.get("CGW_PROJ_PATH")
    if not proj_path:
        return 0

    selection = load_project_selection()
    if not selection or selection.get("last_project_path") != proj_path:
        return 0

    projects_dir = get_storage_dir() / "projects"
    for info_file in projects_dir.glob("*/project_info.json"):
        try:
            with open(info_file, encoding="utf-8") as f:
                if json.load(f)["project_path"] == proj_path:
                    return 0
        except (OSError, json.JSONDecodeError, KeyError):
            continue

    clear_project_selection()
    print("[INFO] Current project reset to None (all indices cleared)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
