"""Embedding model management and lazy loading.

Manages a single active embedding model selected via config.embedding.model_name.
Use switch_embedding_model / list_embedding_models MCP tools to change the active model.
"""

import logging
import threading

from embeddings.embedder import CodeEmbedder
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import get_storage_dir


logger = logging.getLogger(__name__)

# Guards the _model_pool_manager module singleton and the per-embedder
# construct-if-absent path inside ModelPoolManager.get_embedder.
# Lock ordering: state._lock is always acquired BEFORE _pool_lock (get_searcher
# calls get_embedder).  Never acquire _pool_lock then state._lock.
_pool_lock = threading.Lock()


class ModelPoolManager:
    """Manages the active embedding model and lazy loading."""

    def __init__(self):
        """Initialize ModelPoolManager."""

    def get_embedder(self, model_key: str | None = None) -> CodeEmbedder:
        """Get embedder for the currently configured embedding model.

        Args:
            model_key: Unused (kept for call-site compatibility during migration).
                       The active model is always read from config.embedding.model_name.

        Returns:
            CodeEmbedder instance for the active model.

        Raises:
            Exception: If model loading fails.
        """
        state = get_state()

        cache_dir = get_storage_dir() / "models"
        cache_dir.mkdir(exist_ok=True)

        if state.embedders.get("default") is None:
            with _pool_lock:
                if state.embedders.get("default") is None:
                    try:
                        config = get_config()
                        model_name = config.embedding.model_name
                        logger.info(f"Using embedding model: {model_name}")
                    except (RuntimeError, AttributeError) as e:
                        logger.warning(f"Failed to load model from config: {e}")
                        model_name = "google/embeddinggemma-300m"
                        logger.info(f"Falling back to default model: {model_name}")

                    is_first_load = not any(state.embedders.values())
                    if is_first_load:
                        logger.info(
                            f"[FIRST USE] Loading embedding model {model_name}... "
                            f"This is a one-time initialization (~5-10s). "
                            f"Subsequent searches will be fast."
                        )
                    embedder = CodeEmbedder(
                        model_name=model_name, cache_dir=str(cache_dir)
                    )
                    state.set_embedder("default", embedder)
                    logger.info(
                        "✓ Embedder initialized successfully. Ready for fast searches!"
                        if is_first_load
                        else "✓ Embedder initialized successfully"
                    )

        default_embedder = state.embedders["default"]
        assert default_embedder is not None  # initialized above under lock
        return default_embedder


# Module-level singleton
_model_pool_manager: ModelPoolManager | None = None


def get_model_pool_manager() -> ModelPoolManager:
    """Get or create singleton ModelPoolManager instance."""
    global _model_pool_manager
    if _model_pool_manager is None:
        with _pool_lock:
            if _model_pool_manager is None:
                _model_pool_manager = ModelPoolManager()
    return _model_pool_manager


def get_embedder(model_key: str | None = None) -> CodeEmbedder:
    """Get embedder for the currently configured embedding model.

    Backward-compatible wrapper for ModelPoolManager.get_embedder().
    """
    return get_model_pool_manager().get_embedder(model_key)


def reset_pool_manager() -> None:
    """Reset the module-level ModelPoolManager singleton.

    Call this during cleanup to ensure all model references are released.
    """
    global _model_pool_manager
    with _pool_lock:
        _model_pool_manager = None
