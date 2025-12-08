"""Configuration system for search modes and hybrid search features."""

import json
import logging
import os
from dataclasses import dataclass
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
class EmbeddingConfig:
    """Embedding model configuration (4 fields)."""

    model_name: str = "google/embeddinggemma-300m"
    dimension: int = 768
    batch_size: int = 128  # Dynamic based on model, see MODEL_REGISTRY
    query_cache_size: int = 128  # LRU cache size for query embeddings


@dataclass
class SearchModeConfig:
    """Search mode and BM25 settings (12 fields)."""

    default_mode: str = "hybrid"  # hybrid, semantic, bm25, auto
    enable_hybrid: bool = True

    # Hybrid Search Weights
    bm25_weight: float = 0.4
    dense_weight: float = 0.6

    # BM25 Configuration
    bm25_k_parameter: int = 100
    bm25_use_stopwords: bool = True
    bm25_use_stemming: bool = True  # Snowball stemmer for word normalization
    min_bm25_score: float = 0.1

    # Reranking Configuration
    rrf_k_parameter: int = 100
    enable_result_reranking: bool = True

    # Search Result Limits
    default_k: int = 5
    max_k: int = 50


@dataclass
class PerformanceConfig:
    """GPU, parallelism, caching settings (13 fields)."""

    use_parallel_search: bool = True
    max_parallel_workers: int = 2

    # Parallel Chunking Configuration
    enable_parallel_chunking: bool = True  # Enable parallel file chunking
    max_chunking_workers: int = 4  # ThreadPoolExecutor workers for chunking

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


@dataclass
class MultiHopConfig:
    """Multi-hop search settings (4 fields)."""

    enabled: bool = True
    hop_count: int = 2  # Number of expansion hops
    expansion: float = 0.3  # Expansion factor per hop
    initial_k_multiplier: float = 2.0  # Multiplier for initial results (k * multiplier)


@dataclass
class RoutingConfig:
    """Multi-model routing settings (2 fields)."""

    multi_model_enabled: bool = True  # Enable intelligent query routing across models
    default_model: str = "bge_m3"  # Default model key for routing (most balanced)


class SearchConfig:
    """Root configuration with nested sub-configs.

    Phase 4 Item 13: Config Splitting
    - Split 35 monolithic fields into 5 sub-configs for better organization
    - Backward-compatible property aliases during migration (Phase 13-B)

    Supports both initialization styles:
        # New style (nested configs)
        config = SearchConfig(embedding=EmbeddingConfig(model_name="..."))

        # Old style (flat field names) - backward compatible
        config = SearchConfig(embedding_model_name="...", model_dimension=768)
    """

    def __init__(
        self,
        embedding: Optional[EmbeddingConfig] = None,
        search_mode: Optional[SearchModeConfig] = None,
        performance: Optional[PerformanceConfig] = None,
        multi_hop: Optional[MultiHopConfig] = None,
        routing: Optional[RoutingConfig] = None,
        **kwargs,
    ):
        """Initialize SearchConfig with nested or flat field names.

        Args:
            embedding: EmbeddingConfig instance (optional)
            search_mode: SearchModeConfig instance (optional)
            performance: PerformanceConfig instance (optional)
            multi_hop: MultiHopConfig instance (optional)
            routing: RoutingConfig instance (optional)
            **kwargs: Flat field names for backward compatibility
        """
        # Initialize nested configs with defaults
        self.embedding = embedding if embedding is not None else EmbeddingConfig()
        self.search_mode = (
            search_mode if search_mode is not None else SearchModeConfig()
        )
        self.performance = (
            performance if performance is not None else PerformanceConfig()
        )
        self.multi_hop = multi_hop if multi_hop is not None else MultiHopConfig()
        self.routing = routing if routing is not None else RoutingConfig()

        # Handle flat field names via property setters (backward compatibility)
        if kwargs:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    raise TypeError(
                        f"SearchConfig.__init__() got an unexpected keyword argument '{key}'"
                    )

    # ==================== BACKWARD COMPATIBILITY ALIASES ====================
    # Phase 13-B: Temporary aliases for gradual migration
    # These will be removed in Phase 13-C after all consumers are updated
    # ========================================================================

    # EmbeddingConfig aliases (4 fields)
    @property
    def embedding_model_name(self) -> str:
        return self.embedding.model_name

    @embedding_model_name.setter
    def embedding_model_name(self, value: str):
        self.embedding.model_name = value

    @property
    def model_dimension(self) -> int:
        return self.embedding.dimension

    @model_dimension.setter
    def model_dimension(self, value: int):
        self.embedding.dimension = value

    @property
    def embedding_batch_size(self) -> int:
        return self.embedding.batch_size

    @embedding_batch_size.setter
    def embedding_batch_size(self, value: int):
        self.embedding.batch_size = value

    @property
    def query_cache_size(self) -> int:
        return self.embedding.query_cache_size

    @query_cache_size.setter
    def query_cache_size(self, value: int):
        self.embedding.query_cache_size = value

    # SearchModeConfig aliases (12 fields)
    @property
    def default_search_mode(self) -> str:
        return self.search_mode.default_mode

    @default_search_mode.setter
    def default_search_mode(self, value: str):
        self.search_mode.default_mode = value

    @property
    def enable_hybrid_search(self) -> bool:
        return self.search_mode.enable_hybrid

    @enable_hybrid_search.setter
    def enable_hybrid_search(self, value: bool):
        self.search_mode.enable_hybrid = value

    @property
    def bm25_weight(self) -> float:
        return self.search_mode.bm25_weight

    @bm25_weight.setter
    def bm25_weight(self, value: float):
        self.search_mode.bm25_weight = value

    @property
    def dense_weight(self) -> float:
        return self.search_mode.dense_weight

    @dense_weight.setter
    def dense_weight(self, value: float):
        self.search_mode.dense_weight = value

    @property
    def bm25_k_parameter(self) -> int:
        return self.search_mode.bm25_k_parameter

    @bm25_k_parameter.setter
    def bm25_k_parameter(self, value: int):
        self.search_mode.bm25_k_parameter = value

    @property
    def bm25_use_stopwords(self) -> bool:
        return self.search_mode.bm25_use_stopwords

    @bm25_use_stopwords.setter
    def bm25_use_stopwords(self, value: bool):
        self.search_mode.bm25_use_stopwords = value

    @property
    def bm25_use_stemming(self) -> bool:
        return self.search_mode.bm25_use_stemming

    @bm25_use_stemming.setter
    def bm25_use_stemming(self, value: bool):
        self.search_mode.bm25_use_stemming = value

    @property
    def min_bm25_score(self) -> float:
        return self.search_mode.min_bm25_score

    @min_bm25_score.setter
    def min_bm25_score(self, value: float):
        self.search_mode.min_bm25_score = value

    @property
    def rrf_k_parameter(self) -> int:
        return self.search_mode.rrf_k_parameter

    @rrf_k_parameter.setter
    def rrf_k_parameter(self, value: int):
        self.search_mode.rrf_k_parameter = value

    @property
    def enable_result_reranking(self) -> bool:
        return self.search_mode.enable_result_reranking

    @enable_result_reranking.setter
    def enable_result_reranking(self, value: bool):
        self.search_mode.enable_result_reranking = value

    @property
    def default_k(self) -> int:
        return self.search_mode.default_k

    @default_k.setter
    def default_k(self, value: int):
        self.search_mode.default_k = value

    @property
    def max_k(self) -> int:
        return self.search_mode.max_k

    @max_k.setter
    def max_k(self, value: int):
        self.search_mode.max_k = value

    # PerformanceConfig aliases (13 fields)
    @property
    def use_parallel_search(self) -> bool:
        return self.performance.use_parallel_search

    @use_parallel_search.setter
    def use_parallel_search(self, value: bool):
        self.performance.use_parallel_search = value

    @property
    def max_parallel_workers(self) -> int:
        return self.performance.max_parallel_workers

    @max_parallel_workers.setter
    def max_parallel_workers(self, value: int):
        self.performance.max_parallel_workers = value

    @property
    def enable_parallel_chunking(self) -> bool:
        return self.performance.enable_parallel_chunking

    @enable_parallel_chunking.setter
    def enable_parallel_chunking(self, value: bool):
        self.performance.enable_parallel_chunking = value

    @property
    def max_chunking_workers(self) -> int:
        return self.performance.max_chunking_workers

    @max_chunking_workers.setter
    def max_chunking_workers(self, value: int):
        self.performance.max_chunking_workers = value

    @property
    def prefer_gpu(self) -> bool:
        return self.performance.prefer_gpu

    @prefer_gpu.setter
    def prefer_gpu(self, value: bool):
        self.performance.prefer_gpu = value

    @property
    def gpu_memory_threshold(self) -> float:
        return self.performance.gpu_memory_threshold

    @gpu_memory_threshold.setter
    def gpu_memory_threshold(self, value: float):
        self.performance.gpu_memory_threshold = value

    @property
    def enable_fp16(self) -> bool:
        return self.performance.enable_fp16

    @enable_fp16.setter
    def enable_fp16(self, value: bool):
        self.performance.enable_fp16 = value

    @property
    def prefer_bf16(self) -> bool:
        return self.performance.prefer_bf16

    @prefer_bf16.setter
    def prefer_bf16(self, value: bool):
        self.performance.prefer_bf16 = value

    @property
    def enable_dynamic_batch_size(self) -> bool:
        return self.performance.enable_dynamic_batch_size

    @enable_dynamic_batch_size.setter
    def enable_dynamic_batch_size(self, value: bool):
        self.performance.enable_dynamic_batch_size = value

    @property
    def dynamic_batch_min(self) -> int:
        return self.performance.dynamic_batch_min

    @dynamic_batch_min.setter
    def dynamic_batch_min(self, value: int):
        self.performance.dynamic_batch_min = value

    @property
    def dynamic_batch_max(self) -> int:
        return self.performance.dynamic_batch_max

    @dynamic_batch_max.setter
    def dynamic_batch_max(self, value: int):
        self.performance.dynamic_batch_max = value

    @property
    def enable_auto_reindex(self) -> bool:
        return self.performance.enable_auto_reindex

    @enable_auto_reindex.setter
    def enable_auto_reindex(self, value: bool):
        self.performance.enable_auto_reindex = value

    @property
    def max_index_age_minutes(self) -> float:
        return self.performance.max_index_age_minutes

    @max_index_age_minutes.setter
    def max_index_age_minutes(self, value: float):
        self.performance.max_index_age_minutes = value

    # MultiHopConfig aliases (4 fields)
    @property
    def enable_multi_hop(self) -> bool:
        return self.multi_hop.enabled

    @enable_multi_hop.setter
    def enable_multi_hop(self, value: bool):
        self.multi_hop.enabled = value

    @property
    def multi_hop_count(self) -> int:
        return self.multi_hop.hop_count

    @multi_hop_count.setter
    def multi_hop_count(self, value: int):
        self.multi_hop.hop_count = value

    @property
    def multi_hop_expansion(self) -> float:
        return self.multi_hop.expansion

    @multi_hop_expansion.setter
    def multi_hop_expansion(self, value: float):
        self.multi_hop.expansion = value

    @property
    def multi_hop_initial_k_multiplier(self) -> float:
        return self.multi_hop.initial_k_multiplier

    @multi_hop_initial_k_multiplier.setter
    def multi_hop_initial_k_multiplier(self, value: float):
        self.multi_hop.initial_k_multiplier = value

    # RoutingConfig aliases (2 fields)
    @property
    def multi_model_enabled(self) -> bool:
        return self.routing.multi_model_enabled

    @multi_model_enabled.setter
    def multi_model_enabled(self, value: bool):
        self.routing.multi_model_enabled = value

    @property
    def routing_default_model(self) -> str:
        return self.routing.default_model

    @routing_default_model.setter
    def routing_default_model(self, value: str):
        self.routing.default_model = value

    # ==================== END ALIASES ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for JSON serialization.

        This maintains backward compatibility with search_config.json format.
        The nested structure is flattened for persistence.
        """
        return {
            # EmbeddingConfig fields
            "embedding_model_name": self.embedding.model_name,
            "model_dimension": self.embedding.dimension,
            "embedding_batch_size": self.embedding.batch_size,
            "query_cache_size": self.embedding.query_cache_size,
            # SearchModeConfig fields
            "default_search_mode": self.search_mode.default_mode,
            "enable_hybrid_search": self.search_mode.enable_hybrid,
            "bm25_weight": self.search_mode.bm25_weight,
            "dense_weight": self.search_mode.dense_weight,
            "bm25_k_parameter": self.search_mode.bm25_k_parameter,
            "bm25_use_stopwords": self.search_mode.bm25_use_stopwords,
            "bm25_use_stemming": self.search_mode.bm25_use_stemming,
            "min_bm25_score": self.search_mode.min_bm25_score,
            "rrf_k_parameter": self.search_mode.rrf_k_parameter,
            "enable_result_reranking": self.search_mode.enable_result_reranking,
            "default_k": self.search_mode.default_k,
            "max_k": self.search_mode.max_k,
            # PerformanceConfig fields
            "use_parallel_search": self.performance.use_parallel_search,
            "max_parallel_workers": self.performance.max_parallel_workers,
            "enable_parallel_chunking": self.performance.enable_parallel_chunking,
            "max_chunking_workers": self.performance.max_chunking_workers,
            "prefer_gpu": self.performance.prefer_gpu,
            "gpu_memory_threshold": self.performance.gpu_memory_threshold,
            "enable_fp16": self.performance.enable_fp16,
            "prefer_bf16": self.performance.prefer_bf16,
            "enable_dynamic_batch_size": self.performance.enable_dynamic_batch_size,
            "dynamic_batch_min": self.performance.dynamic_batch_min,
            "dynamic_batch_max": self.performance.dynamic_batch_max,
            "enable_auto_reindex": self.performance.enable_auto_reindex,
            "max_index_age_minutes": self.performance.max_index_age_minutes,
            # MultiHopConfig fields
            "enable_multi_hop": self.multi_hop.enabled,
            "multi_hop_count": self.multi_hop.hop_count,
            "multi_hop_expansion": self.multi_hop.expansion,
            "multi_hop_initial_k_multiplier": self.multi_hop.initial_k_multiplier,
            # RoutingConfig fields
            "multi_model_enabled": self.routing.multi_model_enabled,
            "routing_default_model": self.routing.default_model,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchConfig":
        """Create from flat dictionary (backward compatible with JSON format).

        Args:
            data: Flat dictionary with old field names

        Returns:
            SearchConfig with populated nested sub-configs
        """
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

        # Create sub-configs from flat data
        embedding = EmbeddingConfig(
            model_name=data.get("embedding_model_name", "google/embeddinggemma-300m"),
            dimension=data.get("model_dimension", 768),
            batch_size=data.get("embedding_batch_size", 128),
            query_cache_size=data.get("query_cache_size", 128),
        )

        search_mode = SearchModeConfig(
            default_mode=data.get("default_search_mode", "hybrid"),
            enable_hybrid=data.get("enable_hybrid_search", True),
            bm25_weight=data.get("bm25_weight", 0.4),
            dense_weight=data.get("dense_weight", 0.6),
            bm25_k_parameter=data.get("bm25_k_parameter", 100),
            bm25_use_stopwords=data.get("bm25_use_stopwords", True),
            bm25_use_stemming=data.get("bm25_use_stemming", True),
            min_bm25_score=data.get("min_bm25_score", 0.1),
            rrf_k_parameter=data.get("rrf_k_parameter", 100),
            enable_result_reranking=data.get("enable_result_reranking", True),
            default_k=data.get("default_k", 5),
            max_k=data.get("max_k", 50),
        )

        performance = PerformanceConfig(
            use_parallel_search=data.get("use_parallel_search", True),
            max_parallel_workers=data.get("max_parallel_workers", 2),
            enable_parallel_chunking=data.get("enable_parallel_chunking", True),
            max_chunking_workers=data.get("max_chunking_workers", 4),
            prefer_gpu=data.get("prefer_gpu", True),
            gpu_memory_threshold=data.get("gpu_memory_threshold", 0.8),
            enable_fp16=data.get("enable_fp16", True),
            prefer_bf16=data.get("prefer_bf16", True),
            enable_dynamic_batch_size=data.get("enable_dynamic_batch_size", True),
            dynamic_batch_min=data.get("dynamic_batch_min", 32),
            dynamic_batch_max=data.get("dynamic_batch_max", 384),
            enable_auto_reindex=data.get("enable_auto_reindex", True),
            max_index_age_minutes=data.get("max_index_age_minutes", 5.0),
        )

        multi_hop = MultiHopConfig(
            enabled=data.get("enable_multi_hop", True),
            hop_count=data.get("multi_hop_count", 2),
            expansion=data.get("multi_hop_expansion", 0.3),
            initial_k_multiplier=data.get("multi_hop_initial_k_multiplier", 2.0),
        )

        routing = RoutingConfig(
            multi_model_enabled=data.get("multi_model_enabled", True),
            default_model=data.get("routing_default_model", "bge_m3"),
        )

        return cls(
            embedding=embedding,
            search_mode=search_mode,
            performance=performance,
            multi_hop=multi_hop,
            routing=routing,
        )


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
            "CLAUDE_ENABLE_FP16": ("enable_fp16", self._bool_from_env),
            "CLAUDE_PREFER_BF16": ("prefer_bf16", self._bool_from_env),
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


# Register SearchConfigManager with ServiceLocator for Phase 4 DI
# This allows gradual migration while maintaining backward compatibility
def _register_with_service_locator():
    """Register SearchConfig with ServiceLocator on module import."""
    try:
        from mcp_server.services import ServiceLocator

        locator = ServiceLocator.instance()
        # Register factory for lazy loading
        locator.register_factory("config", get_search_config)
    except ImportError:
        # ServiceLocator not yet available (during early initialization)
        pass


# Auto-register on module import
_register_with_service_locator()
