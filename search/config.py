"""Configuration system for search modes and hybrid search features."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

# Model registry with specifications
# Multi-model pool configuration for query routing
# Maps model keys to full model names in MODEL_REGISTRY
# Note: "qwen3" uses adaptive selection (4B max on all tiers, 0.6B fallback on minimal/laptop <10GB)
MODEL_POOL_CONFIG = {
    "qwen3": "Qwen/Qwen3-Embedding-4B",  # Adaptive: 0.6B (minimal/laptop) or 4B (desktop/workstation)
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
        "vram_tier": "minimal",  # Usable on all GPUs
        # Matryoshka Representation Learning (MRL) support
        "mrl_dimensions": [1024, 512, 256, 128, 64, 32],  # Supported MRL dimensions
        "truncate_dim": None,  # Optional: Set to reduce output dimension (e.g., 512)
        # Instruction tuning for code retrieval
        "instruction_mode": "custom",  # "custom" or "prompt_name"
        "query_instruction": "Instruct: Retrieve source code implementations matching the query\nQuery: ",
        "prompt_name": "query",  # Alternative: use model's built-in prompt (generic)
    },
    "Qwen/Qwen3-Embedding-4B": {
        "dimension": 2560,
        "max_context": 32768,
        "description": "Best value upgrade - 87.93% CodeSearchNet, +6% vs 0.6B (MTEB-Code 80.06)",
        "vram_gb": "8-10GB",
        "fallback_batch_size": 128,
        "vram_tier": "desktop",  # 12GB+ recommended
        # Matryoshka Representation Learning (MRL) support
        "mrl_dimensions": [
            2560,
            1024,
            512,
            256,
            128,
            64,
            32,
        ],  # Supported MRL dimensions
        "truncate_dim": 1024,  # ENABLED BY DEFAULT: Match 0.6B storage with 4B quality (36 layers)
        # Instruction tuning for code retrieval
        "instruction_mode": "custom",  # "custom" or "prompt_name"
        "query_instruction": "Instruct: Retrieve source code implementations matching the query\nQuery: ",
        "prompt_name": "query",  # Alternative: use model's built-in prompt (generic)
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


def resolve_qwen3_variant_for_lookup(project_hash: str, project_name: str) -> str:
    """Resolve actual Qwen3 variant indexed for a project.

    Qwen3 uses adaptive selection (0.6B vs 4B) based on VRAM, so the actual
    indexed variant may differ from MODEL_POOL_CONFIG["qwen3"].

    This function checks which Qwen3 variant is actually indexed for the given
    project and returns the correct full model name for directory lookup.

    Args:
        project_hash: Project hash for directory matching
        project_name: Project name for directory matching

    Returns:
        Full model name of indexed Qwen3 variant ("Qwen/Qwen3-Embedding-0.6B" or
        "Qwen/Qwen3-Embedding-4B"), or MODEL_POOL_CONFIG["qwen3"] if neither found.

    Example:
        >>> resolve_qwen3_variant_for_lookup("abc123", "my-project")
        "Qwen/Qwen3-Embedding-0.6B"  # If 0.6B variant is indexed
    """
    from pathlib import Path

    storage_dir = Path.home() / ".claude_code_search" / "projects"

    # Check for existing Qwen3 index (either 0.6B or 4B)
    # Try 0.6B first (more common on typical systems)
    qwen_variants = [
        ("Qwen/Qwen3-Embedding-0.6B", "qwen3-0.6b", 1024),
        ("Qwen/Qwen3-Embedding-4B", "qwen3-4b", 2560),
    ]

    for model_name, slug, dim in qwen_variants:
        # Check for both hash variants (drive-agnostic and legacy)
        pattern = f"{project_name}_{project_hash}_{slug}_{dim}d"
        index_path = storage_dir / pattern / "index" / "stats.json"
        if index_path.exists():
            logging.getLogger(__name__).debug(
                f"[QWEN3_RESOLUTION] Found {model_name} index at {pattern}"
            )
            return model_name

    # No index found → use VRAM-based selection for creation context
    # (During search lookups, this will find existing index above)
    # (During index creation, this selects correct variant for hardware)
    from search.vram_manager import VRAMTierManager

    tier = VRAMTierManager().detect_tier()
    logging.getLogger(__name__).debug(
        f"[QWEN3_RESOLUTION] No Qwen3 index found, using VRAM tier '{tier.name}': {tier.recommended_model}"
    )
    return tier.recommended_model  # e.g., "Qwen/Qwen3-Embedding-0.6B" for 8GB VRAM


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
    """GPU, parallelism, caching settings (14 fields)."""

    use_parallel_search: bool = True
    max_parallel_workers: int = 2

    # Parallel Chunking Configuration
    enable_parallel_chunking: bool = True  # Enable parallel file chunking
    max_chunking_workers: int = 4  # ThreadPoolExecutor workers for chunking
    enable_entity_tracking: bool = (
        False  # Enable P4-5 entity extractors (enums, defaults, context managers)
    )

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

    # Memory-mapped vector storage (Phase 3)
    mmap_storage_enabled: bool = True  # Enabled by default for <1μs vector access


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


@dataclass
class RerankerConfig:
    """Neural reranker settings (5 fields)."""

    enabled: bool = True  # Enabled by default (Quality First)
    model_name: str = "BAAI/bge-reranker-v2-m3"  # Cross-encoder reranker model
    top_k_candidates: int = 50  # Rerank top 50 from RRF
    min_vram_gb: float = 2.0  # Auto-disable below this threshold (reranker uses ~1.5GB)
    batch_size: int = 16  # Reranker inference batch size


@dataclass
class OutputConfig:
    """MCP output formatting settings (1 field)."""

    format: str = (
        "compact"  # json, compact, toon (default: compact for 30-40% token reduction)
    )


class SearchConfig:
    """Root configuration with nested sub-configs.

    Configuration organization:
    - Split into 6 focused sub-configs for better organization
    - embedding, search_mode, performance, multi_hop, routing, reranker, output

    Initialization style (nested configs only):
        config = SearchConfig(embedding=EmbeddingConfig(model_name="..."))
    """

    def __init__(
        self,
        embedding: Optional[EmbeddingConfig] = None,
        search_mode: Optional[SearchModeConfig] = None,
        performance: Optional[PerformanceConfig] = None,
        multi_hop: Optional[MultiHopConfig] = None,
        routing: Optional[RoutingConfig] = None,
        reranker: Optional[RerankerConfig] = None,
        output: Optional[OutputConfig] = None,
    ):
        """Initialize SearchConfig with nested sub-configs.

        Args:
            embedding: EmbeddingConfig instance (optional, defaults to EmbeddingConfig())
            search_mode: SearchModeConfig instance (optional, defaults to SearchModeConfig())
            performance: PerformanceConfig instance (optional, defaults to PerformanceConfig())
            multi_hop: MultiHopConfig instance (optional, defaults to MultiHopConfig())
            routing: RoutingConfig instance (optional, defaults to RoutingConfig())
            reranker: RerankerConfig instance (optional, defaults to RerankerConfig())
            output: OutputConfig instance (optional, defaults to OutputConfig())
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
        self.reranker = reranker if reranker is not None else RerankerConfig()
        self.output = output if output is not None else OutputConfig()

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
            "enable_entity_tracking": self.performance.enable_entity_tracking,
            "prefer_gpu": self.performance.prefer_gpu,
            "gpu_memory_threshold": self.performance.gpu_memory_threshold,
            "enable_fp16": self.performance.enable_fp16,
            "prefer_bf16": self.performance.prefer_bf16,
            "enable_dynamic_batch_size": self.performance.enable_dynamic_batch_size,
            "dynamic_batch_min": self.performance.dynamic_batch_min,
            "dynamic_batch_max": self.performance.dynamic_batch_max,
            "enable_auto_reindex": self.performance.enable_auto_reindex,
            "max_index_age_minutes": self.performance.max_index_age_minutes,
            "mmap_storage_enabled": self.performance.mmap_storage_enabled,
            # MultiHopConfig fields
            "enable_multi_hop": self.multi_hop.enabled,
            "multi_hop_count": self.multi_hop.hop_count,
            "multi_hop_expansion": self.multi_hop.expansion,
            "multi_hop_initial_k_multiplier": self.multi_hop.initial_k_multiplier,
            # RoutingConfig fields
            "multi_model_enabled": self.routing.multi_model_enabled,
            "routing_default_model": self.routing.default_model,
            # RerankerConfig fields
            "reranker_enabled": self.reranker.enabled,
            "reranker_model_name": self.reranker.model_name,
            "reranker_top_k_candidates": self.reranker.top_k_candidates,
            "reranker_min_vram_gb": self.reranker.min_vram_gb,
            "reranker_batch_size": self.reranker.batch_size,
            # OutputConfig fields
            "output_format": self.output.format,
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
                # Use truncate_dim if MRL is enabled, otherwise use native dimension
                data["model_dimension"] = (
                    model_config.get("truncate_dim") or model_config["dimension"]
                )
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
            enable_entity_tracking=data.get("enable_entity_tracking", False),
            prefer_gpu=data.get("prefer_gpu", True),
            gpu_memory_threshold=data.get("gpu_memory_threshold", 0.8),
            enable_fp16=data.get("enable_fp16", True),
            prefer_bf16=data.get("prefer_bf16", True),
            enable_dynamic_batch_size=data.get("enable_dynamic_batch_size", True),
            dynamic_batch_min=data.get("dynamic_batch_min", 32),
            dynamic_batch_max=data.get("dynamic_batch_max", 384),
            enable_auto_reindex=data.get("enable_auto_reindex", True),
            max_index_age_minutes=data.get("max_index_age_minutes", 5.0),
            mmap_storage_enabled=data.get("mmap_storage_enabled", False),
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

        reranker = RerankerConfig(
            enabled=data.get("reranker_enabled", True),
            model_name=data.get("reranker_model_name", "BAAI/bge-reranker-v2-m3"),
            top_k_candidates=data.get("reranker_top_k_candidates", 50),
            min_vram_gb=data.get("reranker_min_vram_gb", 6.0),
            batch_size=data.get("reranker_batch_size", 16),
        )

        output = OutputConfig(
            format=data.get("output_format", "compact"),
        )

        return cls(
            embedding=embedding,
            search_mode=search_mode,
            performance=performance,
            multi_hop=multi_hop,
            routing=routing,
            reranker=reranker,
            output=output,
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
            f"Search mode: {self._config.search_mode.default_mode}, "
            f"hybrid enabled: {self._config.search_mode.enable_hybrid}"
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
            "CLAUDE_ENABLE_ENTITY_TRACKING": (
                "enable_entity_tracking",
                self._bool_from_env,
            ),
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
            "CLAUDE_MMAP_STORAGE_ENABLED": (
                "mmap_storage_enabled",
                self._bool_from_env,
            ),
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
            "CLAUDE_RERANKER_ENABLED": ("reranker_enabled", self._bool_from_env),
            "CLAUDE_RERANKER_MODEL": ("reranker_model_name", str),
            "CLAUDE_RERANKER_TOP_K": ("reranker_top_k_candidates", int),
            "CLAUDE_RERANKER_MIN_VRAM_GB": ("reranker_min_vram_gb", float),
            "CLAUDE_RERANKER_BATCH_SIZE": ("reranker_batch_size", int),
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
            model_config = get_model_config(config.embedding.model_name)
            if model_config:
                # Use truncate_dim if MRL is enabled, otherwise use native dimension
                config.embedding.dimension = (
                    model_config.get("truncate_dim") or model_config["dimension"]
                )

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
        if config.search_mode.default_mode != "auto":
            return config.search_mode.default_mode

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
    return config.search_mode.enable_hybrid


def get_default_search_mode() -> str:
    """Get default search mode."""
    config = get_search_config()
    return config.search_mode.default_mode


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


# Register SearchConfigManager with ServiceLocator for dependency injection
# This allows flexible dependency resolution
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
