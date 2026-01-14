"""Application state management for MCP server.

Centralizes all global state into a single ApplicationState class for:
- Better testability (easy to reset state between tests)
- Clearer dependencies (state is explicit, not implicit globals)
- Improved maintainability (all state in one place)

Usage:
    from mcp_server.state import get_state, reset_state

    # Access state
    state = get_state()
    state.current_project = "/path/to/project"

    # Reset for testing
    reset_state()
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from search.config import SearchConfig


@dataclass
class ApplicationState:
    """Centralized application state container.

    Replaces the following global variables from server.py:
    - _embedders: Dict of model_key -> CodeEmbedder instances
    - _index_manager: CodeIndexManager instance
    - _searcher: HybridSearcher instance
    - _current_model_key: Currently active embedding model
    - _storage_dir: Base storage directory path
    - _current_project: Currently active project path
    - _model_preload_task_started: Whether preload has started
    - _multi_model_enabled: Whether multi-model mode is active
    """

    # Model management
    embedders: dict[str, Any] = field(default_factory=dict)
    current_model_key: Optional[str] = None
    current_index_model_key: Optional[str] = None  # Track index manager's model
    model_preload_task_started: bool = False

    # Search components (lazy-initialized)
    index_manager: Optional[Any] = None  # CodeIndexManager
    searcher: Optional[Any] = None  # HybridSearcher

    # Storage and project
    storage_dir: Optional[Path] = None
    current_project: Optional[str] = None

    # Configuration
    multi_model_enabled: bool = field(
        default_factory=lambda: os.getenv("CLAUDE_MULTI_MODEL_ENABLED", "true").lower()
        in ("true", "1", "yes")
    )

    def reset(self) -> None:
        """Reset all state to initial values.

        Useful for testing to ensure clean state between tests.
        """
        self.embedders = {}
        self.current_model_key = None
        self.current_index_model_key = None
        self.model_preload_task_started = False
        self.index_manager = None
        self.searcher = None
        self.storage_dir = None
        self.current_project = None
        # Re-read from config with env override
        self._reset_multi_model_from_config()

    def _reset_multi_model_from_config(self) -> None:
        """Reset multi_model_enabled from config file with env override."""
        try:
            from search.config import get_search_config

            config = get_search_config()
            self.sync_from_config(config)
        except (AttributeError, KeyError, RuntimeError):
            # Fallback to env var if config unavailable
            self.multi_model_enabled = os.getenv(
                "CLAUDE_MULTI_MODEL_ENABLED", "true"
            ).lower() in ("true", "1", "yes")

    def sync_from_config(self, config: "SearchConfig") -> None:
        """Sync multi_model_enabled from config file.

        Environment variable CLAUDE_MULTI_MODEL_ENABLED overrides config file.
        Called during server startup in app_lifespan().

        Args:
            config: SearchConfig instance to sync from
        """
        # Environment variable takes precedence over config file
        env_value = os.getenv("CLAUDE_MULTI_MODEL_ENABLED")
        if env_value is not None:
            self.multi_model_enabled = env_value.lower() in ("true", "1", "yes")
        else:
            self.multi_model_enabled = config.routing.multi_model_enabled

    def switch_project(self, path: str) -> None:
        """Switch to a different project.

        Resets project-specific state (index_manager, searcher) but
        preserves model state (embedders, current_model_key).

        Args:
            path: Absolute path to the project directory
        """
        self.current_project = path
        # Reset project-specific components
        self.index_manager = None
        self.searcher = None

    def switch_model(self, model_key: str) -> None:
        """Switch to a different embedding model.

        Searcher needs to be recreated with new model, but index_manager
        may remain if it supports the new model's dimension.

        Args:
            model_key: Model key (e.g., 'qwen3', 'bge_m3')
        """
        self.current_model_key = model_key
        self.current_index_model_key = None  # Force index reload on model switch
        # Searcher needs to be recreated with new model
        self.searcher = None

    def get_embedder(self, model_key: Optional[str] = None) -> Optional[Any]:
        """Get embedder for a specific model key.

        Args:
            model_key: Model key, or None to use current_model_key

        Returns:
            CodeEmbedder instance or None if not loaded
        """
        key = model_key or self.current_model_key
        if key:
            return self.embedders.get(key)
        return None

    def set_embedder(self, model_key: str, embedder: Any) -> None:
        """Store an embedder instance.

        Args:
            model_key: Model key to associate with embedder
            embedder: CodeEmbedder instance
        """
        self.embedders[model_key] = embedder

    def clear_embedders(self) -> None:
        """Clear all cached embedder instances and release GPU memory."""
        import logging

        logger = logging.getLogger(__name__)

        # Call cleanup on each embedder to release GPU memory
        for model_key, embedder in self.embedders.items():
            if hasattr(embedder, "cleanup"):
                try:
                    logger.info(f"[CLEANUP] Releasing embedder: {model_key}")
                    embedder.cleanup()
                except Exception as e:
                    logger.warning(f"[CLEANUP] Failed to cleanup {model_key}: {e}")

        self.embedders = {}

    def reset_search_components(self) -> None:
        """Reset index_manager and searcher to force re-initialization.

        Use this when:
        - Clearing index files
        - After multi-model batch indexing
        - When search components need to be recreated
        """
        self.index_manager = None
        self.searcher = None

    def reset_searcher(self) -> None:
        """Reset only the searcher (preserves index_manager).

        Use this when:
        - Search configuration changes (hybrid settings, weights, etc.)
        - Searcher needs refresh but index is still valid
        """
        self.searcher = None

    def reset_for_model_switch(self) -> None:
        """Full reset including embedders for model switch.

        Use this when:
        - Switching embedding models
        - Need to reload all model-dependent components
        """
        self.clear_embedders()
        self.index_manager = None
        self.searcher = None

    def __repr__(self) -> str:
        return (
            f"ApplicationState("
            f"project={self.current_project!r}, "
            f"model={self.current_model_key!r}, "
            f"embedders={list(self.embedders.keys())}, "
            f"multi_model={self.multi_model_enabled})"
        )


# Singleton instance
_app_state = ApplicationState()


def get_state() -> ApplicationState:
    """Get the application state singleton.

    Returns:
        The global ApplicationState instance
    """
    return _app_state


# Register ApplicationState with ServiceLocator for dependency injection
def _register_with_service_locator():
    """Register ApplicationState with ServiceLocator on module import."""
    try:
        from mcp_server.services import ServiceLocator

        locator = ServiceLocator.instance()
        locator.register("state", _app_state)
    except ImportError:
        # ServiceLocator not yet available (during early initialization)
        pass


# Auto-register on module import
_register_with_service_locator()


def reset_state() -> None:
    """Reset application state to initial values.

    Call this in test fixtures to ensure clean state between tests.
    Replaces the manual reset_global_state fixture in conftest.py.
    """
    _app_state.reset()


# Convenience functions for accessing ApplicationState
def get_current_project() -> Optional[str]:
    """Get current project path (backward compatibility)."""
    return _app_state.current_project


def set_current_project_compat(path: str) -> None:
    """Set current project path (backward compatibility)."""
    _app_state.switch_project(path)


def is_multi_model_enabled() -> bool:
    """Check if multi-model mode is enabled (backward compatibility)."""
    return _app_state.multi_model_enabled
