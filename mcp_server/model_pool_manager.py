"""Embedding model pool management and lazy loading.

Manages embedding model lifecycle, lazy loading, and memory optimization.
"""

import logging
import os

from embeddings.embedder import CodeEmbedder
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import get_storage_dir
from search.config import MODEL_POOL_CONFIG, MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED


logger = logging.getLogger(__name__)


class ModelPoolManager:
    """Manages embedding model pool and lazy loading."""

    def __init__(self):
        """Initialize ModelPoolManager."""
        self._cached_pool_config: dict[str, str] | None = None

    def get_pool_config(self) -> dict[str, str]:
        """Get appropriate model pool configuration based on VRAM tier or environment.

        Result is cached for the server lifecycle. Call reset_pool_manager() to clear.

        Returns:
            Dict mapping model keys to model names (defensive copy, safe to modify)
        """
        # Return cached result if available (reduces log spam)
        if self._cached_pool_config is not None:
            return dict(self._cached_pool_config)

        # 1. Check config file setting FIRST (user's explicit choice via menu)
        try:
            from search.config import get_search_config

            config = get_search_config()
            pool_type = config.routing.multi_model_pool

            if pool_type == "lightweight-speed":
                logger.info(
                    "Using lightweight-speed model pool from config (1.65GB total)"
                )
                self._cached_pool_config = MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED
                return dict(self._cached_pool_config)
            elif pool_type == "full":
                logger.info("Using full model pool from config (6.8GB total)")
                self._cached_pool_config = MODEL_POOL_CONFIG
                return dict(self._cached_pool_config)
            # If None or unrecognized, fall through to env var / VRAM detection
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not read pool config from file: {e}")

        # 2. Check environment variable override
        pool_type = os.getenv("CLAUDE_MULTI_MODEL_POOL", "").lower()

        if pool_type in ["lightweight-speed", "lightweight_speed"]:
            logger.info("Using lightweight-speed model pool (1.65GB total)")
            self._cached_pool_config = MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED
            return dict(self._cached_pool_config)
        elif pool_type == "full":
            logger.info("Using full model pool (6.8GB total)")
            self._cached_pool_config = MODEL_POOL_CONFIG
            return dict(self._cached_pool_config)

        # Auto-detect based on VRAM tier
        try:
            from search.vram_manager import VRAMTierManager

            tier_manager = VRAMTierManager()
            tier = tier_manager.detect_tier()

            if tier.multi_model_pool == "lightweight-speed":
                logger.info(
                    f"VRAM tier '{tier.name}' → lightweight-speed pool (1.65GB total)"
                )
                self._cached_pool_config = MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED
                return dict(self._cached_pool_config)
            elif tier.multi_model_pool == "full":
                logger.info(f"VRAM tier '{tier.name}' → full model pool (6.8GB total)")
                self._cached_pool_config = MODEL_POOL_CONFIG
                return dict(self._cached_pool_config)
            else:
                # Tier doesn't specify pool type (minimal tier, single-model)
                logger.info("Using full model pool (default)")
                self._cached_pool_config = MODEL_POOL_CONFIG
                return dict(self._cached_pool_config)

        except Exception as e:
            logger.warning(f"Failed to detect VRAM tier, using full model pool: {e}")
            self._cached_pool_config = MODEL_POOL_CONFIG
            return dict(self._cached_pool_config)

    def initialize_pool(self, lazy_load: bool = True) -> None:
        """Initialize multi-model pool with appropriate models (2 or 3 models).

        Args:
            lazy_load: If True, models are loaded on first access.
                      If False, all models loaded immediately.
        """
        state = get_state()

        if not state.multi_model_enabled:
            logger.info("Multi-model routing disabled - using single model mode")
            return

        cache_dir = get_storage_dir() / "models"
        cache_dir.mkdir(exist_ok=True)

        # Get pool configuration (full or lightweight-speed)
        pool_config = self.get_pool_config()

        if lazy_load:
            # Initialize empty slots - models will load on first get_embedder() call
            for model_key in pool_config:
                if model_key not in state.embedders:
                    state.embedders[model_key] = None
            logger.info(
                f"Model pool initialized in lazy mode: {list(pool_config.keys())}"
            )
        else:
            # Eagerly load all models
            logger.info("Loading all models eagerly (this may take 30-60 seconds)...")
            for model_key, model_name in pool_config.items():
                try:
                    logger.info(f"Loading {model_key} ({model_name})...")
                    embedder = CodeEmbedder(
                        model_name=model_name, cache_dir=str(cache_dir)
                    )
                    state.set_embedder(model_key, embedder)
                    logger.info(f"✓ {model_key} loaded successfully")
                except Exception as e:
                    logger.error(f"✗ Failed to load {model_key}: {e}")
                    state.embedders[model_key] = None

            loaded_count = sum(1 for e in state.embedders.values() if e is not None)
            logger.info(
                f"Model pool loaded: {loaded_count}/{len(pool_config)} models ready"
            )

    def get_embedder(self, model_key: str | None = None) -> CodeEmbedder:
        """Get embedder from multi-model pool or single-model fallback.

        Args:
            model_key: Model key from pool config ("qwen3", "bge_m3", "coderankembed",
                      "gte_modernbert", "c2llm", or "code_model" for lightweight pools).
                      If None, uses config default or falls back to BGE-M3.

        Returns:
            CodeEmbedder instance for the specified model.

        Raises:
            Exception: If model loading fails and no fallback is available.
        """
        state = get_state()

        cache_dir = get_storage_dir() / "models"
        cache_dir.mkdir(exist_ok=True)

        # Get pool configuration (full or lightweight-speed)
        pool_config = self.get_pool_config()

        # PRIORITY: Explicit model_key override takes precedence over multi_model_enabled setting
        # This ensures model_key parameter works even when multi-model mode is disabled
        if model_key is not None and model_key in pool_config:
            logger.info(f"[OVERRIDE] Explicit model_key requested: {model_key}")

            # Lazy load model if not already loaded
            if model_key not in state.embedders or state.embedders[model_key] is None:
                model_name = pool_config[model_key]

                logger.info(
                    f"[OVERRIDE] Loading {model_key} ({model_name}) - explicit request"
                )
                try:
                    embedder = CodeEmbedder(
                        model_name=model_name, cache_dir=str(cache_dir)
                    )
                    state.set_embedder(model_key, embedder)
                    logger.info(
                        f"✓ {model_key} loaded successfully (explicit override)"
                    )
                except Exception as e:
                    logger.error(f"✗ Failed to load {model_key}: {e}")
                    # Fallback to first available model in pool
                    pool_config = self.get_pool_config()
                    fallback_key = next(iter(pool_config.keys()))
                    if (
                        model_key != fallback_key
                        and fallback_key in state.embedders
                        and state.embedders[fallback_key] is not None
                    ):
                        logger.warning(f"Falling back to {fallback_key}")
                        return state.embedders[fallback_key]
                    raise

            return state.embedders[model_key]

        # Multi-model mode
        if state.multi_model_enabled:
            # Determine which model to use
            if model_key is None:
                # Try to get from config, fallback to bge_m3
                try:
                    config = get_config()
                    config_model_name = config.embedding.model_name

                    # Map config model name to model_key
                    pool_config = self.get_pool_config()
                    model_key = None
                    for key, name in pool_config.items():
                        if name == config_model_name:
                            model_key = key
                            break

                    if model_key is None:
                        pool_config = self.get_pool_config()
                        fallback_key = next(iter(pool_config.keys()))
                        logger.warning(
                            f"Config model '{config_model_name}' not in pool, using {fallback_key}"
                        )
                        model_key = fallback_key
                except (RuntimeError, AttributeError) as e:
                    pool_config = self.get_pool_config()
                    fallback_key = next(iter(pool_config.keys()))
                    logger.warning(
                        f"Failed to load model from config: {e}, using {fallback_key}"
                    )
                    model_key = fallback_key

            # Validate model_key against current pool config
            pool_config = self.get_pool_config()
            if model_key not in pool_config:
                logger.error(
                    f"Invalid model_key '{model_key}', available: {list(pool_config.keys())}"
                )
                model_key = next(
                    iter(pool_config.keys())
                )  # Fallback to first available model

            # Lazy load model if not already loaded
            if model_key not in state.embedders or state.embedders[model_key] is None:
                model_name = pool_config[model_key]

                # Check if this is the first model being loaded (cold start)
                is_first_load = not any(state.embedders.values())
                if is_first_load:
                    logger.info(
                        f"[FIRST USE] Loading embedding model {model_key} ({model_name})... "
                        f"This is a one-time initialization (~5-10s). Subsequent searches will be fast."
                    )
                else:
                    logger.info(f"Lazy loading {model_key} ({model_name})...")
                try:
                    embedder = CodeEmbedder(
                        model_name=model_name, cache_dir=str(cache_dir)
                    )
                    state.set_embedder(model_key, embedder)
                    if is_first_load:
                        logger.info(
                            f"✓ {model_key} loaded successfully. Ready for fast searches!"
                        )
                    else:
                        logger.info(f"✓ {model_key} loaded successfully")
                except Exception as e:
                    logger.error(f"✗ Failed to load {model_key}: {e}")
                    # Fallback to first available model in pool
                    pool_config = self.get_pool_config()
                    fallback_key = next(iter(pool_config.keys()))
                    if (
                        model_key != fallback_key
                        and fallback_key in state.embedders
                        and state.embedders[fallback_key] is not None
                    ):
                        logger.warning(f"Falling back to {fallback_key}")
                        return state.embedders[fallback_key]
                    raise

            return state.embedders[model_key]

        # Single-model mode (legacy fallback)
        else:
            # Use old singleton pattern with "default" key
            if "default" not in state.embedders or state.embedders["default"] is None:
                try:
                    config = get_config()
                    model_name = config.embedding.model_name
                    logger.info(f"Using single embedding model: {model_name}")
                except (RuntimeError, AttributeError) as e:
                    logger.warning(f"Failed to load model from config: {e}")
                    model_name = "google/embeddinggemma-300m"
                    logger.info(f"Falling back to default model: {model_name}")

                embedder = CodeEmbedder(model_name=model_name, cache_dir=str(cache_dir))
                state.set_embedder("default", embedder)
                logger.info("Embedder initialized successfully")

            return state.embedders["default"]


# Module-level singleton for backward compatibility
_model_pool_manager: ModelPoolManager | None = None


def get_model_pool_manager() -> ModelPoolManager:
    """Get or create singleton ModelPoolManager instance.

    Returns:
        Singleton ModelPoolManager instance
    """
    global _model_pool_manager
    if _model_pool_manager is None:
        _model_pool_manager = ModelPoolManager()
    return _model_pool_manager


# Backward-compatible module-level functions
def initialize_model_pool(lazy_load: bool = True) -> None:
    """Initialize multi-model pool with all models in the pool.

    Backward-compatible wrapper for ModelPoolManager.initialize_pool().
    """
    return get_model_pool_manager().initialize_pool(lazy_load)


def get_embedder(model_key: str | None = None) -> CodeEmbedder:
    """Get embedder from multi-model pool or single-model fallback.

    Backward-compatible wrapper for ModelPoolManager.get_embedder().
    """
    return get_model_pool_manager().get_embedder(model_key)


def get_model_key_from_name(model_name: str) -> str | None:
    """Get model_key from model name by reverse lookup in pool config.

    This is used to ensure incremental indexing uses the same model that
    was used to create the index (read from project_info.json).

    Args:
        model_name: Full model name (e.g., "Alibaba-NLP/gte-modernbert-base")

    Returns:
        Model key (e.g., "gte_modernbert") or None if not found
    """
    pool_config = get_model_pool_manager().get_pool_config()

    # Reverse lookup: model_name -> model_key
    for key, name in pool_config.items():
        if name == model_name:
            return key

    # Special case: Qwen3 variants
    if "qwen3" in model_name.lower() or "qwen-3" in model_name.lower():
        return "qwen3"

    return None


def reset_pool_manager() -> None:
    """Reset the module-level ModelPoolManager singleton.

    Call this during cleanup to ensure all model references are released.
    This forces a fresh ModelPoolManager instance to be created on next access.
    """
    global _model_pool_manager
    _model_pool_manager = None
