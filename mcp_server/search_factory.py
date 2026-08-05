"""Search component factory functions for MCP server.

Provides factory functions for creating index managers and searchers
with proper lifecycle management and caching.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from search.base_searcher import BaseSearcher
    from search.hybrid_searcher import HybridSearcher
    from search.indexer import CodeIndexManager

logger = logging.getLogger(__name__)


def get_index_manager(
    project_path: str | None = None,
) -> "CodeIndexManager":
    """Get index manager for specific project or current project.

    Args:
        project_path: Path to the project (None = use current project)

    Returns:
        CodeIndexManager instance for the project

    Raises:
        ValueError: If no project is set and no path provided
    """
    from mcp_server.resource_manager import _cleanup_previous_resources
    from mcp_server.state import get_state
    from mcp_server.storage_manager import get_project_storage_dir
    from search.indexer import CodeIndexManager
    from search.storage_layout import project_id_from_model_dir_name

    state = get_state()

    if project_path is None:
        if state.current_project is None:
            raise ValueError(
                "No indexed project found. Please run index_directory first."
            )
        else:
            project_path = state.current_project

    # Double-checked locking: cheap outer test avoids the lock on the hot path.
    if state.current_project != project_path or state.index_manager is None:
        with state._lock:
            # Re-check inside lock — another thread may have constructed by now.
            if state.current_project != project_path:
                logger.info(
                    f"Switching project from '{state.current_project}' to '{Path(project_path).name}'"
                )
                _cleanup_previous_resources()
                state.current_project = project_path
                state.index_manager = None

            if state.index_manager is None:
                project_dir = get_project_storage_dir(project_path)
                index_dir = project_dir / "index"
                index_dir.mkdir(exist_ok=True)

                project_id = project_id_from_model_dir_name(project_dir.name)

                state.index_manager = CodeIndexManager(
                    str(index_dir), project_id=project_id
                )
                logger.info(
                    f"Index manager initialized for project: {Path(project_path).name} (ID: {project_id})"
                )

    return state.index_manager


def build_hybrid_searcher(
    config,
    project_storage: Path,
    embedder,
    *,
    load_existing: bool = True,
) -> "HybridSearcher":
    """Construct a HybridSearcher from live config for a project's storage dir.

    Shared by ``get_searcher`` (the cached-lookup path) and
    ``search_handlers._check_auto_reindex`` (the auto-reindex path) — both
    built the identical 12-kwarg construction inline before this extraction
    (C3 of the ADR-0018 follow-on). Callers retain their own locking, caching,
    and error-handling around this call; only the construction itself is
    shared.

    Args:
        config: Effective SearchConfig (already resolved by the caller).
        project_storage: Project's storage root (parent of ``index/``).
        embedder: Embedder instance to wire into the searcher.
        load_existing: Forwarded to HybridSearcher(...) — set False when the
            caller is about to discard whatever is on disk (force-full
            reindex), so the stale index isn't loaded only to be thrown away.

    Returns:
        A newly constructed HybridSearcher.
    """
    from search.hybrid_searcher import HybridSearcher
    from search.storage_layout import project_id_from_model_dir_name

    storage_dir = project_storage / "index"
    project_id = project_id_from_model_dir_name(project_storage.name)

    return HybridSearcher(
        storage_dir=str(storage_dir),
        embedder=embedder,
        project_id=project_id,
        config=config,
        load_existing=load_existing,
    )


def get_searcher(
    project_path: str | None = None,
    load_existing: bool = True,
) -> "BaseSearcher":
    """Get searcher for specific project or current project.

    Args:
        project_path: Path to project (None = use current project)
        load_existing: Forwarded to HybridSearcher(...) — set False when the
            caller is about to discard whatever is on disk (force-full
            reindex), so the stale index isn't loaded only to be thrown away.
            Ignored when a cached searcher for this project is already live.

    Returns:
        HybridSearcher or IntelligentSearcher instance depending on config
    """
    from mcp_server.model_pool_manager import get_embedder

    # Import PROJECT_ROOT only when needed
    from mcp_server.server import PROJECT_ROOT
    from mcp_server.state import get_state
    from mcp_server.storage_manager import get_project_storage_dir
    from search.config import get_search_config
    from search.dimension_validator import validate_embedder_index_compatibility
    from search.exceptions import DimensionMismatchError
    from search.searcher import IntelligentSearcher

    state = get_state()

    if project_path is None:
        if state.current_project is None:
            project_path = str(PROJECT_ROOT)
            logger.info(
                f"No active project found. Using server directory: {project_path}"
            )
        else:
            project_path = state.current_project

    # Double-checked locking: cheap outer test avoids the lock on the hot path.
    if state.current_project != project_path or state.searcher is None:
        with state._lock:
            # Re-check inside lock — another thread may have constructed by now.
            if state.current_project != project_path or state.searcher is None:
                # Capture project before construction.
                # Do NOT mutate state.current_project yet —
                # if construction raises (e.g. DimensionMismatchError) the old searcher
                # stays valid under the old key, preventing a stale-searcher mismatch.
                new_project = project_path or state.current_project
                config = get_search_config()
                logger.info(
                    f"[GET_SEARCHER] Initializing searcher for project: {new_project}"
                )
                if config.search_mode.enable_hybrid:
                    project_storage = get_project_storage_dir(
                        # pyrefly: ignore [bad-argument-type]
                        new_project,
                    )
                    logger.info(
                        f"[GET_SEARCHER] Using storage directory: {project_storage / 'index'}"
                    )

                    # Pre-validate dimension compatibility
                    embedder = get_embedder()

                    try:
                        validate_embedder_index_compatibility(
                            embedder, project_storage, raise_on_mismatch=True
                        )
                    except DimensionMismatchError as e:
                        logger.error(f"Cannot create searcher: {e}")
                        state.searcher = None  # force re-init on next call
                        raise  # Let caller handle recovery

                    new_searcher = build_hybrid_searcher(
                        config, project_storage, embedder, load_existing=load_existing
                    )
                    # The HybridSearcher already loads existing indices during initialization
                    logger.info(
                        f"HybridSearcher initialized (BM25: {config.search_mode.bm25_weight}, Dense: {config.search_mode.dense_weight})"
                    )
                else:
                    new_searcher = IntelligentSearcher(
                        get_index_manager(project_path),
                        get_embedder(),
                        config=config,
                    )
                    logger.info("IntelligentSearcher initialized (semantic-only mode)")

                # Commit both together only on success — no partial state visible (#2).
                state.current_project = new_project
                state.searcher = new_searcher
                logger.info(
                    f"Searcher initialized for project: {Path(state.current_project).name if state.current_project else 'unknown'}"
                )

    return state.searcher
