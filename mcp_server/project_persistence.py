"""Persistent project selection for MCP server.

Saves and restores the last-used project between server restarts.
Storage: ~/.claude_code_search/project_selection.json
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from search.filters import find_project_at_different_drive


logger = logging.getLogger(__name__)

# Default storage location (same as main storage)
_STORAGE_DIR = Path.home() / ".claude_code_search"
_SELECTION_FILE = "project_selection.json"


def get_selection_file_path() -> Path:
    """Get the path to the project selection file."""
    import os

    storage_path = os.getenv("CODE_SEARCH_STORAGE", str(_STORAGE_DIR))
    return Path(storage_path) / _SELECTION_FILE


def save_project_selection(project_path: str, model_key: str | None = None) -> bool:
    """Save the current project selection for persistence.

    Args:
        project_path: Absolute path to the project directory
        model_key: Optional model key (e.g., 'bge_m3', 'qwen3')

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        selection_file = get_selection_file_path()
        selection_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "last_project_path": str(Path(project_path).resolve()),
            "last_model_key": model_key,
            "updated_at": datetime.now().isoformat(),
        }

        with open(selection_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Project selection saved: {Path(project_path).name}")
        return True

    except Exception as e:
        logger.warning(f"Failed to save project selection: {e}")
        return False


def load_project_selection() -> dict | None:
    """Load the last project selection from disk.

    Returns:
        Dict with 'last_project_path', 'last_model_key', 'updated_at'
        or None if no selection exists or file is invalid
    """
    try:
        selection_file = get_selection_file_path()

        if not selection_file.exists():
            logger.debug("No project selection file found")
            return None

        with open(selection_file, encoding="utf-8") as f:
            data = json.load(f)

        # Validate required fields
        if "last_project_path" not in data:
            logger.warning("Invalid project selection file: missing last_project_path")
            return None

        # Verify project path still exists
        project_path = Path(data["last_project_path"])
        if not project_path.exists():
            # Try to find at different drive letter
            alt_path = find_project_at_different_drive(data["last_project_path"])
            if alt_path:
                logger.info(f"Found project at new location: {alt_path}")
                data["last_project_path"] = alt_path
                # Update selection file with new path
                save_project_selection(alt_path, data.get("last_model_key"))
                return data

            logger.warning(f"Saved project no longer exists: {project_path}")
            return None

        logger.debug(f"Loaded project selection: {project_path.name}")
        return data

    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in project selection file: {e}")
        return None
    except Exception as e:
        logger.warning(f"Failed to load project selection: {e}")
        return None


def get_project_display_name(project_path: str) -> str:
    """Extract a display-friendly project name from path.

    Args:
        project_path: Full path to project

    Returns:
        Project directory name (e.g., 'claude-context-local')
    """
    if project_path is None:
        return "None"
    return Path(project_path).name


def clear_project_selection() -> bool:
    """Clear the saved project selection.

    Returns:
        True if cleared successfully, False otherwise
    """
    try:
        selection_file = get_selection_file_path()
        if selection_file.exists():
            selection_file.unlink()
            logger.info("Project selection cleared")
        return True
    except Exception as e:
        logger.warning(f"Failed to clear project selection: {e}")
        return False


def get_selection_for_display() -> dict:
    """Get project selection info formatted for display.

    Returns:
        Dict with 'name', 'path', 'model_key', 'updated_at' (all strings)
        Safe for display even if no selection exists
    """
    selection = load_project_selection()

    if selection is None:
        return {
            "name": "None",
            "path": "",
            "model_key": "",
            "updated_at": "",
            "exists": False,
        }

    return {
        "name": get_project_display_name(selection.get("last_project_path", "")),
        "path": selection.get("last_project_path", ""),
        "model_key": selection.get("last_model_key", ""),
        "updated_at": selection.get("updated_at", ""),
        "exists": True,
    }
