"""Storage path and project directory management.

Extracted from server.py as part of Phase 2 refactoring.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp_server.services import get_state
from search.config import (
    MODEL_POOL_CONFIG,
    MODEL_REGISTRY,
    get_model_slug,
    get_search_config,
)

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages storage paths and project directories."""

    def __init__(self):
        """Initialize StorageManager."""
        pass

    def get_storage_dir(self) -> Path:
        """Get or create base storage directory.

        Returns:
            Path to the base storage directory
        """
        state = get_state()

        if state.storage_dir is None:
            storage_path = os.getenv(
                "CODE_SEARCH_STORAGE", str(Path.home() / ".claude_code_search")
            )
            state.storage_dir = Path(storage_path)
            state.storage_dir.mkdir(parents=True, exist_ok=True)
        return state.storage_dir

    def set_current_project(self, project_path: str) -> None:
        """Set the current project path in global state.

        Args:
            project_path: Path to the project
        """
        get_state().current_project = project_path
        logger.info(
            f"Current project set to: {Path(project_path).name if project_path else None}"
        )

    def get_project_storage_dir(
        self,
        project_path: str,
        model_key: Optional[str] = None,
        include_dirs: Optional[list] = None,
        exclude_dirs: Optional[list] = None,
    ) -> Path:
        """Get or create project-specific storage directory with per-model dimension suffix.

        Args:
            project_path: Path to the project
            model_key: Model key for routing (None = use config default)
            include_dirs: Optional list of directories to include during indexing
            exclude_dirs: Optional list of directories to exclude during indexing

        Returns:
            Path to the project-specific storage directory

        Raises:
            ValueError: If model_name is not in MODEL_REGISTRY
        """
        base_dir = self.get_storage_dir()

        project_path = Path(project_path).resolve()
        project_name = project_path.name
        project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:8]

        # Determine which model to use
        if model_key:
            # Use routing-selected model (map model_key to model_name via MODEL_POOL_CONFIG)
            if model_key not in MODEL_POOL_CONFIG:
                logger.error(
                    f"Invalid model_key: {model_key}, falling back to config default"
                )
                config = get_search_config()
                model_name = config.embedding.model_name
            else:
                model_name = MODEL_POOL_CONFIG[model_key]
                logger.info(
                    f"[ROUTING] Using routed model: {model_name} (key: {model_key})"
                )
        else:
            # Use config default
            config = get_search_config()
            model_name = config.embedding.model_name
            logger.info(f"[CONFIG] Using config default model: {model_name}")

        # Validate model exists in registry (prevent silent 768d fallback)
        model_config = MODEL_REGISTRY.get(model_name)
        if model_config is None:
            available_models = ", ".join(sorted(MODEL_REGISTRY.keys()))
            raise ValueError(
                f"Unknown embedding model: '{model_name}'\n"
                f"This model is not registered in MODEL_REGISTRY.\n"
                f"Available models:\n  {available_models}\n"
                f"To add this model, update search/config.py:MODEL_REGISTRY"
            )
        dimension = model_config["dimension"]
        model_slug = get_model_slug(model_name)
        project_dir = (
            base_dir
            / "projects"
            / f"{project_name}_{project_hash}_{model_slug}_{dimension}d"
        )
        project_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"[PER_MODEL_INDICES] Using storage: {project_dir.name} (model: {model_name}, dimension: {dimension}d)"
        )
        project_info_file = project_dir / "project_info.json"
        if not project_info_file.exists():
            # Import default excluded dirs for transparency
            from chunking.multi_language_chunker import MultiLanguageChunker

            project_info = {
                "project_name": project_name,
                "project_path": str(project_path),
                "project_hash": project_hash,
                "embedding_model": model_name,
                "model_dimension": dimension,
                "created_at": datetime.now().isoformat(),
                "default_excluded_dirs": sorted(
                    MultiLanguageChunker.DEFAULT_IGNORED_DIRS
                ),
                "user_excluded_dirs": exclude_dirs,
                "default_included_dirs": None,
                "user_included_dirs": include_dirs,
            }
            with open(project_info_file, "w") as f:
                json.dump(project_info, f, indent=2)
        return project_dir

    def update_project_filters(
        self,
        project_path: str,
        include_dirs: Optional[list] = None,
        exclude_dirs: Optional[list] = None,
        model_key: Optional[str] = None,
    ) -> None:
        """Update filters in project_info.json after filter change with full reindex.

        Args:
            project_path: Path to the project
            include_dirs: New include_dirs filter
            exclude_dirs: New exclude_dirs filter
            model_key: Optional model key to update specific model's project_info
        """
        project_storage = self.get_project_storage_dir(
            project_path, model_key=model_key
        )
        project_info_file = project_storage / "project_info.json"

        if not project_info_file.exists():
            logger.warning(
                "[PROJECT_INFO] Cannot update filters - project_info.json not found"
            )
            return

        try:
            with open(project_info_file) as f:
                project_info = json.load(f)

            # Update default excluded dirs snapshot for transparency
            from chunking.multi_language_chunker import MultiLanguageChunker

            project_info["default_excluded_dirs"] = sorted(
                MultiLanguageChunker.DEFAULT_IGNORED_DIRS
            )

            # Update user-defined filter fields
            project_info["user_included_dirs"] = include_dirs
            project_info["user_excluded_dirs"] = exclude_dirs

            # Clean up old field names (migration)
            project_info.pop("include_dirs", None)
            project_info.pop("exclude_dirs", None)

            # Write back updated info
            with open(project_info_file, "w") as f:
                json.dump(project_info, f, indent=2)

            logger.info(
                f"[PROJECT_INFO] Updated filters: user_include={include_dirs}, user_exclude={exclude_dirs}"
            )
        except Exception as e:
            logger.warning(f"[PROJECT_INFO] Failed to update filters: {e}")


# Module-level singleton for backward compatibility
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get or create singleton StorageManager instance.

    Returns:
        Singleton StorageManager instance
    """
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager


# Backward-compatible module-level functions
def get_storage_dir() -> Path:
    """Get or create base storage directory.

    Backward-compatible wrapper for StorageManager.get_storage_dir().
    """
    return get_storage_manager().get_storage_dir()


def set_current_project(project_path: str) -> None:
    """Set the current project path.

    Backward-compatible wrapper for StorageManager.set_current_project().
    """
    return get_storage_manager().set_current_project(project_path)


def get_project_storage_dir(
    project_path: str,
    model_key: Optional[str] = None,
    include_dirs: Optional[list] = None,
    exclude_dirs: Optional[list] = None,
) -> Path:
    """Get or create project-specific storage directory.

    Backward-compatible wrapper for StorageManager.get_project_storage_dir().
    """
    return get_storage_manager().get_project_storage_dir(
        project_path, model_key, include_dirs, exclude_dirs
    )


def update_project_filters(
    project_path: str,
    include_dirs: Optional[list] = None,
    exclude_dirs: Optional[list] = None,
    model_key: Optional[str] = None,
) -> None:
    """Update filters in project_info.json.

    Backward-compatible wrapper for StorageManager.update_project_filters().
    """
    return get_storage_manager().update_project_filters(
        project_path, include_dirs, exclude_dirs, model_key
    )
