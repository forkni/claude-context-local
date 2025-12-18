"""Embedding model pool management and lazy loading.

Manages embedding model lifecycle, lazy loading, and memory optimization.
"""

import logging
from typing import Optional

from embeddings.embedder import CodeEmbedder
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import get_storage_dir
from search.config import MODEL_POOL_CONFIG

logger = logging.getLogger(__name__)


class ModelPoolManager:
    """Manages embedding model pool and lazy loading."""

    def __init__(self):
        """Initialize ModelPoolManager."""
        pass

    def initialize_pool(self, lazy_load: bool = True) -> None:
        """Initialize multi-model pool with all 3 models.

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

        if lazy_load:
            # Initialize empty slots - models will load on first get_embedder() call
            for model_key in MODEL_POOL_CONFIG.keys():
                if model_key not in state.embedders:
                    state.embedders[model_key] = None
            logger.info(
                f"Model pool initialized in lazy mode: {list(MODEL_POOL_CONFIG.keys())}"
            )
        else:
            # Eagerly load all models (WARNING: ~18-20 GB VRAM)
            logger.info("Loading all models eagerly (this may take 30-60 seconds)...")
            for model_key, model_name in MODEL_POOL_CONFIG.items():
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
                f"Model pool loaded: {loaded_count}/{len(MODEL_POOL_CONFIG)} models ready"
            )

    def get_embedder(self, model_key: Optional[str] = None) -> CodeEmbedder:
        """Get embedder from multi-model pool or single-model fallback.

        Args:
            model_key: Model key from MODEL_POOL_CONFIG ("qwen3", "bge_m3", "coderankembed").
                      If None, uses config default or falls back to BGE-M3.

        Returns:
            CodeEmbedder instance for the specified model.

        Raises:
            Exception: If model loading fails and no fallback is available.
        """
        state = get_state()

        cache_dir = get_storage_dir() / "models"
        cache_dir.mkdir(exist_ok=True)

        # PRIORITY: Explicit model_key override takes precedence over multi_model_enabled setting
        # This ensures model_key parameter works even when multi-model mode is disabled
        if model_key is not None and model_key in MODEL_POOL_CONFIG:
            logger.info(f"[OVERRIDE] Explicit model_key requested: {model_key}")

            # Lazy load model if not already loaded
            if model_key not in state.embedders or state.embedders[model_key] is None:
                model_name = MODEL_POOL_CONFIG[model_key]

                # VRAM tier adaptive selection: Upgrade/downgrade based on available VRAM
                if model_key == "qwen3" and model_name == "Qwen/Qwen3-Embedding-4B":
                    try:
                        from search.vram_manager import VRAMTierManager

                        tier_manager = VRAMTierManager()
                        tier = tier_manager.detect_tier()

                        # Fallback to 0.6B on laptop/minimal tiers (VRAM < 10GB)
                        # Max model is 4B (8B removed for safety and compatibility)
                        if tier.name in ["minimal", "laptop"]:
                            original_model = model_name
                            model_name = "Qwen/Qwen3-Embedding-0.6B"
                            logger.info(
                                f"VRAM tier '{tier.name}' detected: "
                                f"Using {model_name} instead of {original_model}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to detect VRAM tier, using configured model: {e}"
                        )

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
                    # Fallback to bge_m3 if available
                    if (
                        model_key != "bge_m3"
                        and "bge_m3" in state.embedders
                        and state.embedders["bge_m3"] is not None
                    ):
                        logger.warning("Falling back to bge_m3")
                        return state.embedders["bge_m3"]
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
                    model_key = None
                    for key, name in MODEL_POOL_CONFIG.items():
                        if name == config_model_name:
                            model_key = key
                            break

                    if model_key is None:
                        logger.warning(
                            f"Config model '{config_model_name}' not in pool, using bge_m3"
                        )
                        model_key = "bge_m3"
                except Exception as e:
                    logger.warning(
                        f"Failed to load model from config: {e}, using bge_m3"
                    )
                    model_key = "bge_m3"

            # Validate model_key
            if model_key not in MODEL_POOL_CONFIG:
                logger.error(
                    f"Invalid model_key '{model_key}', available: {list(MODEL_POOL_CONFIG.keys())}"
                )
                model_key = "bge_m3"  # Fallback to most reliable model

            # Lazy load model if not already loaded
            if model_key not in state.embedders or state.embedders[model_key] is None:
                model_name = MODEL_POOL_CONFIG[model_key]

                # VRAM tier adaptive selection: Upgrade/downgrade based on available VRAM
                if model_key == "qwen3" and model_name == "Qwen/Qwen3-Embedding-4B":
                    try:
                        from search.vram_manager import VRAMTierManager

                        tier_manager = VRAMTierManager()
                        tier = tier_manager.detect_tier()

                        # Fallback to 0.6B on laptop/minimal tiers (VRAM < 10GB)
                        # Max model is 4B (8B removed for safety and compatibility)
                        if tier.name in ["minimal", "laptop"]:
                            original_model = model_name
                            model_name = "Qwen/Qwen3-Embedding-0.6B"
                            logger.info(
                                f"VRAM tier '{tier.name}' detected: "
                                f"Using {model_name} instead of {original_model}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to detect VRAM tier, using configured model: {e}"
                        )

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
                    # Fallback to bge_m3 if available
                    if (
                        model_key != "bge_m3"
                        and "bge_m3" in state.embedders
                        and state.embedders["bge_m3"] is not None
                    ):
                        logger.warning("Falling back to bge_m3")
                        return state.embedders["bge_m3"]
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
                except Exception as e:
                    logger.warning(f"Failed to load model from config: {e}")
                    model_name = "google/embeddinggemma-300m"
                    logger.info(f"Falling back to default model: {model_name}")

                embedder = CodeEmbedder(model_name=model_name, cache_dir=str(cache_dir))
                state.set_embedder("default", embedder)
                logger.info("Embedder initialized successfully")

            return state.embedders["default"]


# Module-level singleton for backward compatibility
_model_pool_manager: Optional[ModelPoolManager] = None


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
    """Initialize multi-model pool with all 3 models.

    Backward-compatible wrapper for ModelPoolManager.initialize_pool().
    """
    return get_model_pool_manager().initialize_pool(lazy_load)


def get_embedder(model_key: Optional[str] = None) -> CodeEmbedder:
    """Get embedder from multi-model pool or single-model fallback.

    Backward-compatible wrapper for ModelPoolManager.get_embedder().
    """
    return get_model_pool_manager().get_embedder(model_key)
