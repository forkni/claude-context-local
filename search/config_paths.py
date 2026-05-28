"""Shared config path resolution — stdlib only, no heavy project imports."""

from __future__ import annotations

import os
from pathlib import Path


_DEFAULT_STORAGE_DIR: Path = Path.home() / ".claude_code_search"

# Ordered list of candidate paths tried when no explicit config file is given.
# First existing candidate wins; if none exist the first candidate is the default.
CONFIG_PATH_CANDIDATES: list[str] = [
    "search_config.json",
    ".search_config.json",
    str(_DEFAULT_STORAGE_DIR / "search_config.json"),
]


def resolve_config_path() -> str:
    """Return the first existing candidate path, or the first candidate as default."""
    for candidate in CONFIG_PATH_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return CONFIG_PATH_CANDIDATES[0]
