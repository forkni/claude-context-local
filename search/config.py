"""Configuration system for search modes and hybrid search features."""

import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

# Model registry with specifications
# Multi-model pool configuration for query routing
# Maps model keys to full model names in MODEL_REGISTRY
MODEL_POOL_CONFIG = {
    "qwen3": "Qwen/Qwen3-Embedding-0.6B",
    "bge_m3": "BAAI/bge-m3",
    "coderankembed": "nomic-ai/CodeRankEmbed",
}

MODEL_REGISTRY = {
    "google/embeddinggemma-300m": {
        "dimension": 768,
        "max_context": 2048,
        "passage_prefix": "Retrieval-document: ",
        "description": "Default model, fast and efficient",
        "vram_gb": "4-8GB",
        "fallback_batch_size": 128,  # Used when dynamic sizing disabled
    },
    "BAAI/bge-m3": {
        "dimension": 1024,
        "max_context": 8192,
        "description": "Recommended upgrade, hybrid search support",
        "vram_gb": "3-4GB",
        "fallback_batch_size": 256,  # Used when dynamic sizing disabled
    },
    "Qwen/Qwen3-Embedding-0.6B": {
        "dimension": 1024,
        "max_context": 32768,
        "description": "High-efficiency model with excellent performance-to-size ratio",
        "vram_gb": "2.3GB",
        "fallback_batch_size": 256,
    },
    # Code-specific models (optimized for Python, C++, and programming languages)
    "nomic-ai/CodeRankEmbed": {
        "dimension": 768,
        "max_context": 8192,
        "description": "Code-specific embedding model (CSN: 77.9 MRR, CoIR: 60.1 NDCG@10)",
        "vram_gb": "2GB",
        "fallback_batch_size": 128,
        "model_type": "code-specific",
        "task_instruction": "Represent this query for searching relevant code",  # Required query prefix
        "trust_remote_code": True,
    },
}

# Multi-hop search configuration
# Based on empirical testing: 2 hops with 0.3 expansion provides optimal balance
# of discovery quality and performance (+25-35ms overhead, 93%+ queries benefit)


@dataclass
class SearchConfig:
    """Configuration for search behavior."""

    # Embedding Model Configuration
    embedding_model_name: str = "google/embeddinggemma-300m"
    model_dimension: int = 768
    embedding_batch_size: int = 128  # Dynamic based on model, see MODEL_REGISTRY
    query_cache_size: int = 128  # LRU cache size for query embeddings

    # Search Mode Configuration
    default_search_mode: str = "hybrid"  # hybrid, semantic, bm25, auto
    enable_hybrid_search: bool = True

    # Hybrid Search Weights
    bm25_weight: float = 0.4
    dense_weight: float = 0.6

    # Performance Settings
    use_parallel_search: bool = True
    max_parallel_workers: int = 2

    # Multi-Model Routing Configuration
    multi_model_enabled: bool = True  # Enable intelligent query routing across models
    routing_default_model: str = "bge_m3"  # Default model key for routing (most balanced)

    # Parallel Chunking Configuration
    enable_parallel_chunking: bool = True  # Enable parallel file chunking
    max_chunking_workers: int = 4  # ThreadPoolExecutor workers for chunking

    # BM25 Configuration
    bm25_k_parameter: int = 100
    bm25_use_stopwords: bool = True
    bm25_use_stemming: bool = (
        True  # Snowball stemmer for word normalization (indexing→index)
    )
    min_bm25_score: float = 0.1

    # Reranking Configuration
    rrf_k_parameter: int = 100
    enable_result_reranking: bool = True

    # GPU Configuration
    prefer_gpu: bool = True
    gpu_memory_threshold: float = 0.8

    # Precision Configuration (fp16/bf16 for faster inference)
    enable_fp16: bool = True  # Enable fp16 for GPU (30-50% faster inference)
    prefer_bf16: bool = True  # Prefer bf16 on Ampere+ GPUs (better accuracy than fp16)

    # Dynamic Batch Sizing (GPU-based optimization)
    enable_dynamic_batch_size: bool = True  # Enable GPU-based auto-sizing
    dynamic_batch_min: int = 32  # Minimum batch size for safety
    dynamic_batch_max: int = 384  # Maximum batch size (safer for 8-16GB GPUs)

    # Auto-reindexing
    enable_auto_reindex: bool = True
    max_index_age_minutes: float = 5.0

    # Multi-hop Search Configuration
    # Optimal settings validated through empirical testing (93%+ queries benefit)
    enable_multi_hop: bool = True
    multi_hop_count: int = 2  # Number of expansion hops
    multi_hop_expansion: float = 0.3  # Expansion factor per hop
    multi_hop_initial_k_multiplier: float = (
        2.0  # Multiplier for initial results (k * multiplier)
    )

    # Search Result Limits
    default_k: int = 5
    max_k: int = 50

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchConfig":
        """Create from dictionary."""
        # Auto-update dimension and batch size if model is in registry
        if "embedding_model_name" in data:
            model_config = get_model_config(data["embedding_model_name"])
            if model_config:
                data["model_dimension"] = model_config["dimension"]
                # Only auto-set batch size if not explicitly provided
                if "embedding_batch_size" not in data:
                    data["embedding_batch_size"] = model_config.get(
                        "fallback_batch_size", 128
                    )

        # Filter only known fields to avoid TypeError
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


class SearchConfigManager:
    """Manages search configuration from environment variables and config files."""

    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file or self._get_default_config_path()
        self._config = None

    def _get_default_config_path(self) -> str:
        """Get default config file path."""
        # Try common locations
        candidates = [
            "search_config.json",
            ".search_config.json",
            os.path.expanduser("~/.claude_code_search/search_config.json"),
        ]

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        # Return first candidate as default
        return candidates[0]

    def load_config(self) -> SearchConfig:
        """Load configuration from file and environment variables."""
        if self._config is not None:
            return self._config

        # Start with defaults
        config_dict = {}

        # Load from file if exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config_dict = json.load(f)
                self.logger.info(f"Loaded search config from {self.config_file}")
            except Exception as e:
                self.logger.warning(
                    f"Failed to load config file {self.config_file}: {e}"
                )

        # Override with environment variables
        env_overrides = self._load_from_environment()
        config_dict.update(env_overrides)

        # Create config object
        self._config = SearchConfig.from_dict(config_dict)

        self.logger.info(
            f"Search mode: {self._config.default_search_mode}, "
            f"hybrid enabled: {self._config.enable_hybrid_search}"
        )

        return self._config

    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_mapping = {
            "CLAUDE_EMBEDDING_MODEL": ("embedding_model_name", str),
            "CLAUDE_EMBEDDING_BATCH_SIZE": ("embedding_batch_size", int),
            "CLAUDE_QUERY_CACHE_SIZE": ("query_cache_size", int),
            "CLAUDE_SEARCH_MODE": ("default_search_mode", str),
            "CLAUDE_ENABLE_HYBRID": ("enable_hybrid_search", self._bool_from_env),
            "CLAUDE_BM25_WEIGHT": ("bm25_weight", float),
            "CLAUDE_DENSE_WEIGHT": ("dense_weight", float),
            "CLAUDE_BM25_USE_STEMMING": ("bm25_use_stemming", self._bool_from_env),
            "CLAUDE_USE_PARALLEL": ("use_parallel_search", self._bool_from_env),
            "CLAUDE_ENABLE_PARALLEL_CHUNKING": (
                "enable_parallel_chunking",
                self._bool_from_env,
            ),
            "CLAUDE_MAX_CHUNKING_WORKERS": ("max_chunking_workers", int),
            "CLAUDE_PREFER_GPU": ("prefer_gpu", self._bool_from_env),
            "CLAUDE_GPU_THRESHOLD": ("gpu_memory_threshold", float),
            "CLAUDE_DYNAMIC_BATCH_ENABLED": (
                "enable_dynamic_batch_size",
                self._bool_from_env,
            ),
            "CLAUDE_DYNAMIC_BATCH_MIN": ("dynamic_batch_min", int),
            "CLAUDE_DYNAMIC_BATCH_MAX": ("dynamic_batch_max", int),
            "CLAUDE_AUTO_REINDEX": ("enable_auto_reindex", self._bool_from_env),
            "CLAUDE_MAX_INDEX_AGE": ("max_index_age_minutes", float),
            "CLAUDE_ENABLE_MULTI_HOP": ("enable_multi_hop", self._bool_from_env),
            "CLAUDE_MULTI_HOP_COUNT": ("multi_hop_count", int),
            "CLAUDE_MULTI_HOP_EXPANSION": ("multi_hop_expansion", float),
            "CLAUDE_MULTI_HOP_INITIAL_K_MULTIPLIER": (
                "multi_hop_initial_k_multiplier",
                float,
            ),
            "CLAUDE_DEFAULT_K": ("default_k", int),
            "CLAUDE_MAX_K": ("max_k", int),
            "CLAUDE_MULTI_MODEL_ENABLED": (
                "multi_model_enabled",
                self._bool_from_env,
            ),
            "CLAUDE_ROUTING_DEFAULT_MODEL": ("routing_default_model", str),
        }

        config_dict = {}
        for env_var, (config_key, converter) in env_mapping.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    config_dict[config_key] = converter(env_value)
                    self.logger.debug(
                        f"Set {config_key} = {config_dict[config_key]} from {env_var}"
                    )
                except ValueError as e:
                    self.logger.warning(
                        f"Invalid value for {env_var}: {env_value} ({e})"
                    )

        return config_dict

    def _bool_from_env(self, value: str) -> bool:
        """Convert environment variable string to boolean."""
        return value.lower() in ("true", "1", "yes", "on", "enabled")

    def save_config(self, config: SearchConfig) -> None:
        """Save configuration to file."""
        try:
            # Auto-sync dimension from model registry before saving
            model_config = get_model_config(config.embedding_model_name)
            if model_config:
                config.model_dimension = model_config["dimension"]

            # Create directory if needed (only if not current directory)
            config_dir = os.path.dirname(self.config_file)
            if config_dir:  # Only create if not empty (not current directory)
                os.makedirs(config_dir, exist_ok=True)

            # Save to file
            with open(self.config_file, "w") as f:
                json.dump(config.to_dict(), f, indent=2)

            self.logger.info(f"Saved search config to {self.config_file}")
            self._config = config  # Update cached config

        except Exception as e:
            self.logger.error(f"Failed to save config to {self.config_file}: {e}")

    def get_search_mode_for_query(
        self, query: str, explicit_mode: Optional[str] = None
    ) -> str:
        """Determine best search mode for a query."""
        config = self.load_config()

        # Use explicit mode if provided
        if explicit_mode and explicit_mode != "auto":
            return explicit_mode

        # Use default mode if not auto
        if config.default_search_mode != "auto":
            return config.default_search_mode

        # Auto-detect based on query characteristics
        query_lower = query.lower()

        # Text-heavy queries -> BM25
        if any(
            keyword in query_lower
            for keyword in ["text", "string", "message", "error", "log"]
        ):
            return "bm25"

        # Code structure queries -> semantic
        if any(
            keyword in query_lower
            for keyword in ["class", "function", "method", "interface"]
        ):
            return "semantic"

        # Default to hybrid for balanced approach
        return "hybrid"


# Global configuration manager instance
_config_manager: Optional[SearchConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> SearchConfigManager:
    """Get or create global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = SearchConfigManager(config_file)
    return _config_manager


def get_search_config() -> SearchConfig:
    """Get current search configuration."""
    return get_config_manager().load_config()


def is_hybrid_search_enabled() -> bool:
    """Check if hybrid search is enabled."""
    config = get_search_config()
    return config.enable_hybrid_search


def get_default_search_mode() -> str:
    """Get default search mode."""
    config = get_search_config()
    return config.default_search_mode


def get_model_registry() -> Dict[str, Dict[str, Any]]:
    """Get the model registry with all supported models."""
    return MODEL_REGISTRY


def get_model_config(model_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific model."""
    return MODEL_REGISTRY.get(model_name)


def get_model_slug(model_name: str) -> str:
    """Convert model name to filesystem-safe slug for storage paths.

    Generates unique, readable slugs for model storage directories and snapshots.
    Prevents collisions between models with same dimension (e.g., BGE-M3 and Qwen3-0.6B).

    Args:
        model_name: Full model name (e.g., "BAAI/bge-m3", "Qwen/Qwen3-Embedding-0.6B")

    Returns:
        Lowercase slug suitable for filesystem paths

    Examples:
        >>> get_model_slug("BAAI/bge-m3")
        'bge-m3'
        >>> get_model_slug("Qwen/Qwen3-Embedding-0.6B")
        'qwen3-0.6b'
        >>> get_model_slug("nomic-ai/CodeRankEmbed")
        'coderankembed'
        >>> get_model_slug("google/embeddinggemma-300m")
        'gemma-300m'
    """
    # Remove organization prefix (everything before /)
    if "/" in model_name:
        model_name = model_name.split("/")[-1]

    # Convert to lowercase
    slug = model_name.lower()

    # Remove common model prefixes/suffixes for brevity
    slug = slug.replace("embedding", "").replace("embed", "")
    slug = slug.replace("-base", "").replace("-code", "")

    # Clean up consecutive hyphens and leading/trailing hyphens
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")

    return slug
