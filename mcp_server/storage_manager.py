"""Storage path and project directory management.

Manages project storage directories, metadata persistence, and path resolution.
"""

import contextlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import cast

from mcp_server.services import get_state
from search.config import (
    MODEL_REGISTRY,
    get_model_slug,
    get_search_config,
)
from search.filters import (
    compute_drive_agnostic_hash,
    compute_legacy_hash,
    extract_drive_agnostic_path,
)


logger = logging.getLogger(__name__)

# Filename written into every legitimate storage root on first init.
# Downstream guards use its presence to verify a directory is a real
# storage root before performing destructive operations.
STORAGE_SENTINEL = ".claude_code_search_storage"

# Project-root markers — if any ancestor of the candidate path contains
# one of these (excluding the home dir itself), the path is inside a
# source tree and must be refused as storage location.
_PROJECT_MARKERS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
)


def validate_storage_path(path: Path) -> tuple[bool, str]:
    """Check that *path* is a safe location for an index storage root.

    Refuses:
    - The user's home directory itself or a filesystem root
    - Any path whose directory tree (up to home) contains a project-root marker

    Returns ``(True, "ok")`` when safe, ``(False, reason)`` when refused.
    """
    p = path.resolve()
    home = Path.home()

    if p == home or p == Path(p.anchor):
        return False, f"refusing home dir or filesystem root: {p}"

    for ancestor in (p, *p.parents):
        if ancestor == home or ancestor == ancestor.parent:
            break
        for marker in _PROJECT_MARKERS:
            if (ancestor / marker).exists():
                return (
                    False,
                    f"path is inside a project tree ({marker} found at {ancestor})",
                )

    return True, "ok"


class StorageManager:
    """Manages storage paths and project directories."""

    def __init__(self) -> None:
        """Initialize StorageManager.

        The manager operates on global state via ServiceLocator pattern,
        providing centralized storage path management for project directories.
        """
        pass

    def get_storage_dir(self) -> Path:
        """Get or create base storage directory.

        Reads CODE_SEARCH_STORAGE env var if set; falls back to
        ``~/.claude_code_search``.  Refuses paths that sit inside a project
        source tree (have a .git / pyproject.toml ancestor) and falls back to
        the default rather than using the unsafe path.

        Returns:
            Path to the base storage directory
        """
        state = get_state()

        if state.storage_dir is None:
            env_val = os.getenv("CODE_SEARCH_STORAGE")
            if env_val:
                candidate = Path(env_val).expanduser()
                ok, reason = validate_storage_path(candidate)
                if not ok:
                    logger.error(
                        "CODE_SEARCH_STORAGE=%r is unsafe (%s); "
                        "falling back to ~/.claude_code_search",
                        env_val,
                        reason,
                    )
                    candidate = Path.home() / ".claude_code_search"
            else:
                candidate = Path.home() / ".claude_code_search"

            candidate.mkdir(parents=True, exist_ok=True)

            sentinel = candidate / STORAGE_SENTINEL
            if not sentinel.exists():
                with contextlib.suppress(OSError):
                    sentinel.write_text(
                        "claude-context-local storage root\n", encoding="utf-8"
                    )

            state.storage_dir = candidate

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

    def _find_existing_project_dir(
        self,
        projects_dir: Path,
        project_name: str,
        new_hash: str,
        legacy_hash: str,
        model_slug: str,
        dimension: int,
    ) -> Path | None:
        """Find existing project directory by hash (new or legacy).

        Args:
            projects_dir: Base projects directory
            project_name: Project directory name
            new_hash: Drive-agnostic hash
            legacy_hash: Full-path hash (backward compatibility)
            model_slug: Model identifier slug
            dimension: Model dimension

        Returns:
            Path to existing directory or None if not found
        """
        # Try drive-agnostic hash first
        new_dir = projects_dir / f"{project_name}_{new_hash}_{model_slug}_{dimension}d"
        if new_dir.exists():
            return new_dir

        # Try legacy hash (backward compatibility)
        legacy_dir = (
            projects_dir / f"{project_name}_{legacy_hash}_{model_slug}_{dimension}d"
        )
        if legacy_dir.exists():
            logger.info(f"Found project with legacy hash: {legacy_dir.name}")
            return legacy_dir

        return None

    def _update_stored_path_if_changed(
        self, project_dir: Path, current_path: str
    ) -> None:
        """Update stored path if drive letter changed.

        Args:
            project_dir: Project storage directory
            current_path: Current project path
        """
        info_file = project_dir / "project_info.json"
        if not info_file.exists():
            return

        try:
            with open(info_file) as f:
                info = json.load(f)

            stored = info.get("project_path", "")
            if stored != current_path:
                logger.info(f"Updating project path: {stored} -> {current_path}")
                info["project_path"] = current_path
                info["previous_paths"] = info.get("previous_paths", [])
                if stored and stored not in info["previous_paths"]:
                    info["previous_paths"].append(stored)

                with open(info_file, "w") as f:
                    json.dump(info, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update stored path: {e}")

    def get_project_storage_dir(
        self,
        project_path: str,
        model_key: str | None = None,
        include_dirs: list | None = None,
        exclude_dirs: list | None = None,
    ) -> Path:
        """Get or create project-specific storage directory with per-model dimension suffix.

        Args:
            project_path: Path to the project
            model_key: Unused (kept for call-site compatibility). Model is always
                       read from config.embedding.model_name.
            include_dirs: Optional list of directories to include during indexing
            exclude_dirs: Optional list of directories to exclude during indexing

        Returns:
            Path to the project-specific storage directory

        Raises:
            ValueError: If model_name is not in MODEL_REGISTRY
        """
        base_dir = self.get_storage_dir()

        # pyrefly: ignore [bad-assignment]
        project_path = Path(project_path).resolve()
        # pyrefly: ignore [missing-attribute]
        project_name = project_path.name

        # Compute both hashes for backward compatibility
        new_hash = compute_drive_agnostic_hash(str(project_path))
        legacy_hash = compute_legacy_hash(str(project_path))

        # Always use the configured model (single-model mode)
        config = get_search_config()
        model_name = config.embedding.model_name
        logger.info(f"[CONFIG] Using model: {model_name}")

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
        # Use effective dimension (truncate_dim for MRL, else native dimension)
        dimension = cast(
            int, model_config.get("truncate_dim") or model_config["dimension"]
        )
        model_slug = get_model_slug(model_name)

        # Check for existing project directory (handles drive letter changes)
        projects_dir = base_dir / "projects"
        existing_dir = self._find_existing_project_dir(
            projects_dir,
            project_name,
            new_hash,
            legacy_hash,
            model_slug,
            dimension,
        )

        if existing_dir:
            # Update stored path if drive letter changed
            self._update_stored_path_if_changed(existing_dir, str(project_path))
            logger.info(
                f"[PER_MODEL_INDICES] Using existing storage: {existing_dir.name} (model: {model_name}, dimension: {dimension}d)"
            )
            return existing_dir

        # Create new directory with drive-agnostic hash
        project_hash = new_hash
        project_dir = (
            base_dir
            / "projects"
            / f"{project_name}_{project_hash}_{model_slug}_{dimension}d"
        )
        project_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"[PER_MODEL_INDICES] Creating new storage: {project_dir.name} (model: {model_name}, dimension: {dimension}d)"
        )
        project_info_file = project_dir / "project_info.json"
        if not project_info_file.exists():
            # Import default excluded dirs for transparency
            from chunking.multi_language_chunker import MultiLanguageChunker

            project_info = {
                "project_name": project_name,
                "project_path": str(project_path),
                "project_path_agnostic": extract_drive_agnostic_path(str(project_path)),
                "project_hash": project_hash,
                "hash_version": 2,  # Version 2 = drive-agnostic hash
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

    def get_canonical_project_info(self, project_path: str) -> Path | None:
        """Find the first existing project_info.json across all model dirs for this project.

        Searches all model-specific storage dirs for this project hash and returns the
        first project_info.json found. Use this instead of get_project_storage_dir() when
        reading stored filters, so the result is independent of the current config model.

        Args:
            project_path: Path to the project

        Returns:
            Path to an existing project_info.json, or None if no model dir has one yet.
        """
        base_dir = self.get_storage_dir()
        projects_dir = base_dir / "projects"
        resolved = Path(project_path).resolve()
        project_name = resolved.name
        new_hash = compute_drive_agnostic_hash(str(resolved))
        legacy_hash = compute_legacy_hash(str(resolved))

        for hash_val in (new_hash, legacy_hash):
            for model_dir in sorted(projects_dir.glob(f"{project_name}_{hash_val}_*")):
                info = model_dir / "project_info.json"
                if info.exists():
                    return info
        return None

    def update_project_filters(
        self,
        project_path: str,
        include_dirs: list | None = None,
        exclude_dirs: list | None = None,
        model_key: str | None = None,
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

            # Guard against silently clearing user-defined filters.
            # None means "caller didn't specify", not "user wants to clear".
            # Pass [] to explicitly clear a filter.
            stored_include = project_info.get("user_included_dirs")
            stored_exclude = project_info.get("user_excluded_dirs")

            if include_dirs is None and stored_include is not None:
                logger.warning(
                    "[PROJECT_INFO] refusing to clear user_included_dirs %r with None; "
                    "pass [] to clear explicitly",
                    stored_include,
                )
                include_dirs = stored_include
            project_info["user_included_dirs"] = include_dirs

            if exclude_dirs is None and stored_exclude is not None:
                logger.warning(
                    "[PROJECT_INFO] refusing to clear user_excluded_dirs %r with None; "
                    "pass [] to clear explicitly",
                    stored_exclude,
                )
                exclude_dirs = stored_exclude
            project_info["user_excluded_dirs"] = exclude_dirs

            # Clean up obsolete field names
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
_storage_manager: StorageManager | None = None


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
    model_key: str | None = None,
    include_dirs: list | None = None,
    exclude_dirs: list | None = None,
) -> Path:
    """Get or create project-specific storage directory.

    Backward-compatible wrapper for StorageManager.get_project_storage_dir().
    """
    return get_storage_manager().get_project_storage_dir(
        project_path, model_key, include_dirs, exclude_dirs
    )


def get_canonical_project_info(project_path: str) -> Path | None:
    """Find the first existing project_info.json across all model dirs.

    Backward-compatible wrapper for StorageManager.get_canonical_project_info().
    """
    return get_storage_manager().get_canonical_project_info(project_path)


def update_project_filters(
    project_path: str,
    include_dirs: list | None = None,
    exclude_dirs: list | None = None,
    model_key: str | None = None,
) -> None:
    """Update filters in project_info.json.

    Backward-compatible wrapper for StorageManager.update_project_filters().
    """
    return get_storage_manager().update_project_filters(
        project_path, include_dirs, exclude_dirs, model_key
    )
