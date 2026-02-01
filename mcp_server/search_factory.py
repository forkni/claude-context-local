"""Search component factory functions for MCP server.

Provides factory functions for creating index managers and searchers
with proper lifecycle management and caching.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from search.base_searcher import BaseSearcher
    from search.indexer import CodeIndexManager

logger = logging.getLogger(__name__)


class SearchFactory:
    """Factory for creating and caching search components.

    This class encapsulates the creation logic for index managers and searchers
    that was previously in server.py, providing better separation of concerns
    and easier testing.
    """

    def __init__(self):
        """Initialize SearchFactory.

        The factory operates on global state via ServiceLocator pattern.
        """
        pass

    def get_index_manager(
        self, project_path: str = None, model_key: str = None
    ) -> "CodeIndexManager":
        """Get index manager for specific project or current project.

        Args:
            project_path: Path to the project (None = use current project)
            model_key: Model key for routing (None = use config default)

        Returns:
            CodeIndexManager instance for the project

        Raises:
            ValueError: If no project is set and no path provided
        """
        from mcp_server.resource_manager import _cleanup_previous_resources
        from mcp_server.services import get_state
        from mcp_server.storage_manager import get_project_storage_dir
        from search.indexer import CodeIndexManager

        state = get_state()

        if project_path is None:
            if state.current_project is None:
                raise ValueError(
                    "No indexed project found. Please run index_directory first."
                )
            else:
                project_path = state.current_project

        # Invalidate cache if project or model changed
        if (
            state.current_project != project_path
            or state.current_index_model_key != model_key
        ):
            if state.current_project != project_path:
                logger.info(
                    f"Switching project from '{state.current_project}' to '{Path(project_path).name}'"
                )
            if state.current_index_model_key != model_key:
                logger.info(
                    f"Switching index model from '{state.current_index_model_key}' to '{model_key}'"
                )
            _cleanup_previous_resources()

            state.current_project = project_path
            state.current_index_model_key = model_key
            state.index_manager = None

        if state.index_manager is None:
            project_dir = get_project_storage_dir(project_path, model_key=model_key)
            index_dir = project_dir / "index"
            index_dir.mkdir(exist_ok=True)

            # Extract project_id from storage directory name
            # Format: projectname_hash_modelslug_dimension (e.g., claude-context-local_caf2e75a_qwen3_1024d)
            project_id = project_dir.name.rsplit("_", 1)[0]  # Remove dimension suffix

            # Get config for performance settings (including mmap)
            from search.config import get_config_manager

            config = get_config_manager().load_config()

            state.index_manager = CodeIndexManager(
                str(index_dir), project_id=project_id, config=config
            )
            logger.info(
                f"Index manager initialized for project: {Path(project_path).name} (ID: {project_id}, model_key: {model_key})"
            )

        return state.index_manager

    def get_searcher(
        self, project_path: str = None, model_key: str = None
    ) -> "BaseSearcher":
        """Get searcher for specific project or current project.

        Args:
            project_path: Path to project (None = use current project)
            model_key: Model key for routing (None = preserve current model,
                       or use config default if no current model)

        Returns:
            HybridSearcher or IntelligentSearcher instance depending on config
        """
        from mcp_server.model_pool_manager import get_embedder

        # Import PROJECT_ROOT only when needed
        from mcp_server.server import PROJECT_ROOT
        from mcp_server.services import get_config, get_state
        from mcp_server.storage_manager import get_project_storage_dir
        from search.dimension_validator import validate_embedder_index_compatibility
        from search.exceptions import DimensionMismatchError
        from search.hybrid_searcher import HybridSearcher
        from search.searcher import IntelligentSearcher

        state = get_state()

        if project_path is None and state.current_project is None:
            project_path = str(PROJECT_ROOT)
            logger.info(
                f"No active project found. Using server directory: {project_path}"
            )

        # Use effective model key: passed value OR current value (preserve routing)
        effective_model_key = (
            model_key if model_key is not None else state.current_model_key
        )

        # Invalidate cache if project or model changed
        if (
            state.current_project != project_path
            or state.current_model_key != effective_model_key
            or state.searcher is None
        ):
            state.current_project = project_path or state.current_project
            state.current_model_key = effective_model_key
            config = get_config()
            logger.info(
                f"[GET_SEARCHER] Initializing searcher for project: {state.current_project}"
            )
            if config.search_mode.enable_hybrid:
                project_storage = get_project_storage_dir(
                    state.current_project, model_key=effective_model_key
                )
                storage_dir = project_storage / "index"
                logger.info(f"[GET_SEARCHER] Using storage directory: {storage_dir}")

                # Pre-validate dimension compatibility
                embedder = get_embedder(effective_model_key)

                try:
                    validate_embedder_index_compatibility(
                        embedder, project_storage, raise_on_mismatch=True
                    )
                except DimensionMismatchError as e:
                    logger.error(f"Cannot create searcher: {e}")
                    raise  # Let caller handle recovery

                # Extract project_id from storage directory name
                # Format: projectname_hash_dimension (e.g., claude-context-local_caf2e75a_1024d)
                project_id = project_storage.name.rsplit("_", 1)[
                    0
                ]  # Remove dimension suffix

                state.searcher = HybridSearcher(
                    storage_dir=str(storage_dir),
                    embedder=embedder,
                    bm25_weight=config.search_mode.bm25_weight,
                    dense_weight=config.search_mode.dense_weight,
                    rrf_k=config.search_mode.rrf_k_parameter,
                    max_workers=2,
                    project_id=project_id,
                    config=config,
                )
                # REMOVED: get_index_manager() call that was causing state corruption
                # The HybridSearcher already loads existing indices during initialization
                logger.info(
                    f"HybridSearcher initialized (BM25: {config.search_mode.bm25_weight}, Dense: {config.search_mode.dense_weight})"
                )
            else:
                state.searcher = IntelligentSearcher(
                    self.get_index_manager(project_path, model_key=effective_model_key),
                    get_embedder(effective_model_key),
                    config=config,
                )
                logger.info("IntelligentSearcher initialized (semantic-only mode)")

            logger.info(
                f"Searcher initialized for project: {Path(state.current_project).name if state.current_project else 'unknown'}"
            )

        return state.searcher


# ============================================================================
# Module-level singleton and backward-compatible wrappers
# ============================================================================

_search_factory = None


def get_search_factory() -> SearchFactory:
    """Get or create singleton SearchFactory instance.

    Returns:
        Singleton SearchFactory instance
    """
    global _search_factory
    if _search_factory is None:
        _search_factory = SearchFactory()
    return _search_factory


def get_index_manager(project_path: Optional[str] = None, model_key: Optional[str] = None) -> "CodeIndexManager":
    """Get index manager for specific project or current project.

    Args:
        project_path: Path to the project (None = use current project)
        model_key: Model key for routing (None = use config default)

    Returns:
        CodeIndexManager instance

    .. note::
        This is a backward-compatible wrapper around SearchFactory.
        For new code, consider using SearchFactory directly.
    """
    return get_search_factory().get_index_manager(project_path, model_key)


def get_searcher(project_path: str = None, model_key: str = None) -> "BaseSearcher":
    """Get searcher for specific project or current project.

    Args:
        project_path: Path to project (None = use current project)
        model_key: Model key for routing (None = preserve current)

    Returns:
        BaseSearcher instance (either HybridSearcher or IntelligentSearcher)

    .. note::
        This is a backward-compatible wrapper around SearchFactory.
        For new code, consider using SearchFactory directly.
    """
    return get_search_factory().get_searcher(project_path, model_key)
