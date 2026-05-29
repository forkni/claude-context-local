"""Embedding model pool management and lazy loading.

Manages embedding model lifecycle, lazy loading, and memory optimization.
"""

import logging
import os
from pathlib import Path

from embeddings.embedder import CodeEmbedder
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import get_storage_dir
from search.config import (
    ALL_POOL_MODELS,
    MODEL_POOL_CONFIG,
    MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED,
)


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
                    logger.error(f"✗ Failed to load {model_key}: {e}", exc_info=True)
                    state.embedders[model_key] = None

            loaded_count = sum(1 for e in state.embedders.values() if e is not None)
            logger.info(
                f"Model pool loaded: {loaded_count}/{len(pool_config)} models ready"
            )

    def _load_pool_embedder(
        self,
        state,
        model_key: str,
        model_name: str,
        cache_dir: Path,
        *,
        allow_fallback: bool,
        exc_info: bool,
        loading_log: str | None = None,
        success_log: str | None = None,
        error_label: str = "",
    ) -> CodeEmbedder:
        """Lazy-load ``model_key`` into ``state.embedders``; return the cached embedder.

        Idempotent: if the embedder is already loaded, returns it without constructing
        a new one.

        On ``CodeEmbedder`` construction failure: when ``allow_fallback=True`` and a
        *different* pool model is already loaded, silently return that fallback and log a
        warning; otherwise re-raise the exception.  The ``allow_fallback`` and ``exc_info``
        flags are the single source of truth for the load-failure policy across all three
        lazy-load call sites in :meth:`get_embedder`.

        Args:
            state: Live ``ApplicationState`` instance (from :func:`get_state`).
            model_key: Pool key to load (e.g. ``"bge_m3"``).
            model_name: Full HuggingFace model identifier passed to :class:`CodeEmbedder`.
            cache_dir: Directory where model weights are cached on disk.
            allow_fallback: When ``True``, a load failure returns the first already-loaded
                pool model instead of raising.  Cross-pool loads set this to ``False``.
            exc_info: When ``True``, attaches the exception traceback to the error log
                entry (passed through to :func:`logger.error`).
            loading_log: Optional ``logger.info`` message emitted before construction.
                Pass ``None`` to suppress (cross-pool path uses a prior ``logger.warning``
                instead).
            success_log: Optional success message.  Defaults to
                ``"✓ {model_key} loaded successfully"``.
            error_label: Text inserted between ``"✗ Failed to load "`` and
                ``model_key`` in the error message.  Use ``"cross-pool model "`` for
                Block A, empty string (default) for Blocks B and C.
        """
        if model_key in state.embedders and state.embedders[model_key] is not None:
            return state.embedders[model_key]
        if loading_log:
            logger.info(loading_log)
        try:
            embedder = CodeEmbedder(model_name=model_name, cache_dir=str(cache_dir))
            state.set_embedder(model_key, embedder)
            logger.info(success_log or f"✓ {model_key} loaded successfully")
            return state.embedders[model_key]
        except Exception as e:
            logger.error(
                f"✗ Failed to load {error_label}{model_key}: {e}", exc_info=exc_info
            )
            if allow_fallback:
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

    def get_embedder(
        self, model_key: str | None = None, allow_cross_pool: bool = False
    ) -> CodeEmbedder:
        """Get embedder from multi-model pool or single-model fallback.

        Args:
            model_key: Model key from pool config ("qwen3_0.6b", "bge_m3", "coderankembed",
                      "gte_modernbert", "c2llm", or "code_model" for lightweight pools).
                      If None, uses config default or falls back to BGE-M3.
            allow_cross_pool: When True and model_key belongs to a pool other than the
                      active one, load it anyway to preserve an existing index. The
                      caller is responsible for understanding the VRAM implications.
                      Defaults to False so routing-selected loads stay pool-disciplined.

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

        # Cross-pool path: model_key known globally but not in the active pool.
        # Only attempted when the caller explicitly opts in (index-preservation path).
        if (
            allow_cross_pool
            and model_key is not None
            and model_key not in pool_config
            and model_key in ALL_POOL_MODELS
        ):
            model_name = ALL_POOL_MODELS[model_key]
            active_keys = list(pool_config.keys())
            logger.warning(
                f"[CROSS_POOL] Loading '{model_key}' ({model_name}) outside active pool "
                f"{active_keys} to preserve existing index (may exceed pool VRAM budget)"
            )
            return self._load_pool_embedder(
                state,
                model_key,
                model_name,
                cache_dir,
                allow_fallback=False,
                exc_info=False,
                success_log=f"✓ {model_key} loaded successfully (cross-pool)",
                error_label="cross-pool model ",
            )

        # PRIORITY: Explicit model_key override takes precedence over multi_model_enabled setting
        # This ensures model_key parameter works even when multi-model mode is disabled
        if model_key is not None and model_key in pool_config:
            logger.info(f"[OVERRIDE] Explicit model_key requested: {model_key}")

            model_name = pool_config[model_key]
            return self._load_pool_embedder(
                state,
                model_key,
                model_name,
                cache_dir,
                allow_fallback=True,
                exc_info=True,
                loading_log=(
                    f"[OVERRIDE] Loading {model_key} ({model_name}) - explicit request"
                ),
                success_log=f"✓ {model_key} loaded successfully (explicit override)",
            )

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
                        from search.config import MODEL_REGISTRY

                        if config_model_name in MODEL_REGISTRY:
                            logger.warning(
                                f"Config model '{config_model_name}' not in active pool "
                                f"{list(pool_config.keys())}; loading it directly as "
                                f"single-model (multi-model default-load bypassed)."
                            )
                            if (
                                "default" not in state.embedders
                                or state.embedders["default"] is None
                            ):
                                embedder = CodeEmbedder(
                                    model_name=config_model_name,
                                    cache_dir=str(cache_dir),
                                )
                                state.set_embedder("default", embedder)
                            return state.embedders["default"]
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

            model_name = pool_config[model_key]
            # Cold-start detection for first-use messaging (computed here; used in logs)
            is_first_load = not any(state.embedders.values())
            loading_log = (
                f"[FIRST USE] Loading embedding model {model_key} ({model_name})... "
                f"This is a one-time initialization (~5-10s). Subsequent searches will be fast."
                if is_first_load
                else f"Lazy loading {model_key} ({model_name})..."
            )
            success_log = (
                f"✓ {model_key} loaded successfully. Ready for fast searches!"
                if is_first_load
                else f"✓ {model_key} loaded successfully"
            )
            return self._load_pool_embedder(
                state,
                model_key,
                model_name,
                cache_dir,
                allow_fallback=True,
                exc_info=True,
                loading_log=loading_log,
                success_log=success_log,
            )

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


def get_embedder(
    model_key: str | None = None, allow_cross_pool: bool = False
) -> CodeEmbedder:
    """Get embedder from multi-model pool or single-model fallback.

    Backward-compatible wrapper for ModelPoolManager.get_embedder().
    """
    return get_model_pool_manager().get_embedder(
        model_key, allow_cross_pool=allow_cross_pool
    )


def get_model_key_from_name(model_name: str) -> str | None:
    """Get model_key from model name by reverse lookup in pool config.

    This is used to ensure incremental indexing uses the same model that
    was used to create the index (read from project_info.json).

    Performs a two-tier lookup: active pool first (fast path), then all
    known pool dicts (ALL_POOL_MODELS) so that an index built with a model
    from a different pool can still be identified after the active pool changes.

    Args:
        model_name: Full model name (e.g., "Alibaba-NLP/gte-modernbert-base")

    Returns:
        Model key (e.g., "gte_modernbert") or None if not found in any pool
    """
    pool_config = get_model_pool_manager().get_pool_config()

    # Tier 1: active pool — fast path, no extra log noise
    for key, name in pool_config.items():
        if name == model_name:
            return key

    # Tier 2: any other known pool — index-preservation path
    for key, name in ALL_POOL_MODELS.items():
        if name == model_name:
            active_pool_name = next(iter(pool_config.keys()), "unknown")
            logger.info(
                f"[CROSS_POOL] Stored model '{model_name}' resolved to key '{key}' "
                f"(outside active pool containing '{active_pool_name}')"
            )
            return key

    return None


def get_model_name_from_key(model_key: str) -> str | None:
    """Get full model name from model key — symmetric counterpart to get_model_key_from_name.

    Performs a two-tier lookup: active pool first (fast path), then ALL_POOL_MODELS
    so that a key produced by get_model_key_from_name can always be resolved back
    to a model name even when the active pool has changed.

    Args:
        model_key: Pool key (e.g., "qwen3_0.6b", "coderankembed")

    Returns:
        Full model name (e.g., "Qwen/Qwen3-Embedding-0.6B") or None if unknown
    """
    pool_config = get_model_pool_manager().get_pool_config()

    # Tier 1: active pool — fast path, no extra log noise
    if model_key in pool_config:
        return pool_config[model_key]

    # Tier 2: any other known pool — index-preservation path (storage resolution only)
    if model_key in ALL_POOL_MODELS:
        model_name = ALL_POOL_MODELS[model_key]
        active_pool_name = next(iter(pool_config.keys()), "unknown")
        logger.info(
            f"[CROSS_POOL] Key '{model_key}' resolved to model '{model_name}' "
            f"(outside active pool containing '{active_pool_name}')"
        )
        return model_name

    return None


def reset_pool_manager() -> None:
    """Reset the module-level ModelPoolManager singleton.

    Call this during cleanup to ensure all model references are released.
    This forces a fresh ModelPoolManager instance to be created on next access.
    """
    global _model_pool_manager
    _model_pool_manager = None
