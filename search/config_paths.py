"""Shared config path resolution — stdlib only, no heavy project imports."""

from __future__ import annotations

import os
from pathlib import Path


_DEFAULT_STORAGE_DIR: Path = Path.home() / ".claude_code_search"

# Repo root (this module lives at <repo-root>/search/config_paths.py), used to anchor
# the primary candidates below so config resolution doesn't depend on process cwd
# (e.g. MCP server launched from a different working directory, or scripts invoked
# from outside the repo). See project_search_config_guard memory note for the
# incident this fixes.
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent

# Ordered list of candidate paths tried when no explicit config file is given.
# First existing candidate wins; if none exist the first candidate is the default
# (also the write target for save_config()).
CONFIG_PATH_CANDIDATES: list[str] = [
    str(_REPO_ROOT / "search_config.json"),
    str(_REPO_ROOT / ".search_config.json"),
    str(_DEFAULT_STORAGE_DIR / "search_config.json"),
]


def resolve_config_path() -> str:
    """Return the first existing candidate path, or the first candidate as default."""
    for candidate in CONFIG_PATH_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return CONFIG_PATH_CANDIDATES[0]
