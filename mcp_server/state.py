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

import asyncio
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ApplicationState:
    """Centralized application state container.

    Replaces the following global variables from server.py:
    - _embedders: Dict of CodeEmbedder instances (keyed by "default")
    - _index_manager: CodeIndexManager instance
    - _searcher: HybridSearcher instance
    - _storage_dir: Base storage directory path
    - _current_project: Currently active project path
    - _model_preload_task_started: Whether preload has started

    """

    # Model management
    embedders: dict[str, Any] = field(default_factory=dict)
    model_preload_task_started: bool = False

    # Search components (lazy-initialized)
    index_manager: Any | None = None  # CodeIndexManager
    searcher: Any | None = None  # HybridSearcher

    # Storage and project
    storage_dir: Path | None = None
    current_project: str | None = None

    # Concurrency guards — intentionally NOT reset by reset() so that in-flight
    # threads always share the same stable lock instance across state resets.
    _lock: threading.RLock = field(default_factory=threading.RLock)
    # Per-project asyncio reindex locks.  Only touched on the event loop; no
    # extra threading lock needed.  reset() replaces this with a fresh dict.
    _reindex_locks: dict[str, asyncio.Lock] = field(default_factory=dict)
    # Global asyncio lock serializing state-mutating tool calls (switch_project,
    # configure_*, clear_index, delete_project) so a mutation from one HTTP
    # client cannot interleave with another client's in-flight search reading
    # the same global state.  Only touched on the event loop; lazily created
    # (see get_mutation_lock()) for the same reason _reindex_locks is lazy.
    _mutation_lock: asyncio.Lock | None = None

    def reset(self) -> None:
        """Reset all state to initial values.

        Useful for testing to ensure clean state between tests.
        Note: _lock is deliberately NOT reset — it must survive resets so that
        any in-flight threads keep a stable lock reference.
        """
        self.embedders = {}
        self.model_preload_task_started = False
        self.index_manager = None
        self.searcher = None
        self.storage_dir = None
        self.current_project = None
        # Per-project reindex locks are project-scoped; reset with fresh dict.
        self._reindex_locks = {}
        # Recreated lazily on next get_mutation_lock() call.
        self._mutation_lock = None

    def get_reindex_lock(self, project_path: str) -> asyncio.Lock:
        """Return the per-project asyncio.Lock for reindex serialization.

        Creates a new Lock on first access for a given project path.
        Safe to call from any coroutine; must NOT be called from a thread
        (asyncio.Lock is event-loop-bound and only touched on the loop).
        """
        if project_path not in self._reindex_locks:
            self._reindex_locks[project_path] = asyncio.Lock()
        return self._reindex_locks[project_path]

    def get_mutation_lock(self) -> asyncio.Lock:
        """Return the process-wide asyncio.Lock guarding state-mutating tools.

        Used to single-flight `switch_project`, `configure_*`,
        `switch_embedding_model`, `clear_index`, and `delete_project` so
        concurrent HTTP clients can't interleave a mutation with another
        client's in-flight search over the same global state. Created on
        first access for the same reason `get_reindex_lock` is lazy.
        """
        if self._mutation_lock is None:
            self._mutation_lock = asyncio.Lock()
        return self._mutation_lock

    def switch_project(self, path: str) -> None:
        """Switch to a different project.

        Resets project-specific state (index_manager, searcher) but
        preserves model state (embedders).

        Args:
            path: Absolute path to the project directory
        """
        with self._lock:
            self.current_project = path
            # Reset project-specific components
            self.index_manager = None
            self.searcher = None

    def get_embedder(self) -> Any | None:
        """Get the active embedder.

        Returns:
            CodeEmbedder instance or None if not loaded
        """
        return self.embedders.get("default")

    def set_embedder(self, key: str, embedder: Any) -> None:
        """Store an embedder instance.

        Args:
            key: Key to associate with embedder (always "default")
            embedder: CodeEmbedder instance
        """
        self.embedders[key] = embedder

    def clear_embedders(self) -> None:
        """Clear all cached embedder instances and release GPU memory."""
        import logging

        logger = logging.getLogger(__name__)

        # Atomically swap out the embedder dict and null the searcher under the
        # lock so construction paths see a consistent state.  Cleanup (which can
        # be slow — VRAM release) is performed outside the lock.
        with self._lock:
            old_embedders = self.embedders
            self.embedders = {}
            # Every searcher component stashes embedder refs that are now dead.
            # Force rebuild on next search request.
            self.searcher = None

        # Call cleanup on each embedder to release GPU memory (outside lock)
        for key, embedder in old_embedders.items():
            if hasattr(embedder, "cleanup"):
                try:
                    logger.info(f"[CLEANUP] Releasing embedder: {key}")
                    embedder.cleanup()
                except Exception as e:  # noqa: BLE001 - cleanup: per-embedder release, must not block remaining embedders
                    logger.warning(f"[CLEANUP] Failed to cleanup {key}: {e}")

    def reset_search_components(self) -> None:
        """Reset index_manager and searcher to force re-initialization.

        Use this when:
        - Clearing index files
        - After multi-model batch indexing
        - When search components need to be recreated
        """
        with self._lock:
            self.index_manager = None
            self.searcher = None

    def reset_searcher(self) -> None:
        """Reset only the searcher (preserves index_manager).

        Use this when:
        - Search configuration changes (hybrid settings, weights, etc.)
        - Searcher needs refresh but index is still valid
        """
        with self._lock:
            self.searcher = None

    def reset_for_model_switch(self) -> None:
        """Full reset including embedders for model switch.

        Use this when:
        - Switching embedding models
        - Need to reload all model-dependent components
        """
        # clear_embedders() acquires _lock internally to snapshot+null embedders.
        self.clear_embedders()
        # Null index_manager under lock as a separate step (searcher already
        # nulled by clear_embedders).
        with self._lock:
            self.index_manager = None

    def __repr__(self) -> str:
        return (
            f"ApplicationState("
            f"project={self.current_project!r}, "
            f"embedders={list(self.embedders.keys())})"
        )


# Singleton instance
_app_state = ApplicationState()


def get_state() -> ApplicationState:
    """Get the application state singleton.

    Returns:
        The global ApplicationState instance
    """
    return _app_state


def reset_state() -> None:
    """Reset application state to initial values.

    Call this in test fixtures to ensure clean state between tests.
    Replaces the manual reset_global_state fixture in conftest.py.
    """
    _app_state.reset()


# Convenience functions for accessing ApplicationState
def get_current_project() -> str | None:
    """Get current project path (backward compatibility)."""
    return _app_state.current_project


def set_current_project_compat(path: str) -> None:
    """Set current project path (backward compatibility)."""
    _app_state.switch_project(path)
