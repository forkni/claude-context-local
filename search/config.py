"""Configuration system for search modes and hybrid search features."""

import dataclasses
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Import DEFAULT_EDGE_WEIGHTS for ego-graph weighted BFS
from graph.graph_storage import DEFAULT_EDGE_WEIGHTS
from search.config_paths import resolve_config_path


# Model registry with specifications
# Multi-model pool configuration for query routing
# Maps model keys to full model names in MODEL_REGISTRY
# Note: Using 0.6B variant for systems with limited VRAM (<18GB)
MODEL_POOL_CONFIG = {
    "qwen3_0.6b": "Qwen/Qwen3-Embedding-0.6B",  # 1024d, ~1.1GB VRAM, MRR 0.94 on SSCG benchmark
    "coderankembed": "nomic-ai/CodeRankEmbed",  # Code localization, function-level search (CoRNStack/ICLR 2025)
}

# Lightweight pool configuration for 8GB VRAM GPUs
# Speed-focused with proven performance (1.65GB total VRAM)
MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED = {
    "gte_modernbert": "Alibaba-NLP/gte-modernbert-base",
    "bge_m3": "BAAI/bge-m3",
}

# Union of all known pool configs — used for cross-pool reverse lookups so that
# an index built with one pool's model can still be identified when the active
# pool changes.  Update this whenever a new pool dict is added.
ALL_POOL_MODELS: dict[str, str] = {
    **MODEL_POOL_CONFIG,
    **MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED,
}

# MODEL_REGISTRY convention for ONNX support:
# - "onnx_supported": False  -> ONNX path is skipped in _should_use_onnx().
#   Use this when the upstream pooling mode is not handled by
#   embeddings/onnx_wrapper.py (which supports only "cls" and "mean").
# - Key absent (or True)     -> ONNX path allowed, subject to other gates
#   (trust_remote_code, performance.use_onnx, etc.).
# New models with non-cls/mean pooling (lasttoken, weightedmean, etc.) MUST
# set onnx_supported: False explicitly until onnx_wrapper.py gains support.
MODEL_REGISTRY = {
    "google/embeddinggemma-300m": {
        "dimension": 768,
        "max_context": 2048,
        "passage_prefix": "Retrieval-document: ",
        "description": "Default model, fast and efficient",
        "vram_gb": "~1.2GB",  # 300M params @FP16 ≈0.6GB weights + buffers; original "4-8GB" was stale estimate
        "fallback_batch_size": 128,  # Used when dynamic sizing disabled
        "onnx_pooling": "mean",  # Gemma uses mean pooling
    },
    "BAAI/bge-m3": {
        "dimension": 1024,
        "max_context": 8192,
        "description": "Recommended upgrade, hybrid search support",
        "vram_gb": "1-1.5GB",  # Updated from "3-4GB" (actual measured: 1.07GB)
        "fallback_batch_size": 256,  # Used when dynamic sizing disabled
        "onnx_pooling": "cls",  # BGE uses CLS pooling (confirmed by Optimum notebook)
    },
    "BAAI/bge-code-v1": {
        "dimension": 1536,
        "max_context": 4096,  # 4k context
        "description": "SOTA Code Retrieval (CoIR 81.77), 2B params, Qwen2-based",
        "vram_gb": "4GB",  # ~4GB in FP16
        "fallback_batch_size": 32,  # Conservative batch size for 2B model
        "trust_remote_code": False,
        # Upstream uses lasttoken pooling, which the ONNX wrapper does not yet support.
        # Gate ONNX off for this model until lasttoken support lands in onnx_wrapper.py.
        "onnx_supported": False,
    },
    "Qwen/Qwen3-Embedding-0.6B": {
        "dimension": 1024,
        "max_context": 32768,
        "description": "High-efficiency model with excellent performance-to-size ratio",
        "vram_gb": "2.3GB",
        "fallback_batch_size": 256,
        "vram_tier": "minimal",  # Usable on all GPUs
        "onnx_pooling": "mean",  # Qwen3-Embedding uses mean pooling
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
        "description": "High-performance general model, MTEB code retrieval rank #3 (80.07)",
        "vram_gb": "~10GB",
        "fallback_batch_size": 16,
        "vram_tier": "high",  # Requires 12GB+ GPU
        "onnx_pooling": "mean",
        "mrl_dimensions": [2560, 1024, 512, 256, 128, 64, 32],
        "truncate_dim": None,
        "instruction_mode": "custom",
        "query_instruction": "Instruct: Retrieve source code implementations matching the query\nQuery: ",
        "prompt_name": "query",
    },
    # Code-specific models (optimized for Python, C++, and programming languages)
    "nomic-ai/CodeRankEmbed": {
        "dimension": 768,
        "max_context": 8192,
        "description": "Code-specific embedding model (CSN: 77.9 MRR, CoIR: 60.1 NDCG@10)",
        "vram_gb": "0.5-0.6GB",  # Updated from "2GB" (actual measured: 0.52GB)
        "fallback_batch_size": 128,
        "model_type": "code-specific",
        "task_instruction": "Represent this query for searching relevant code",  # Required query prefix
        "trust_remote_code": True,
        # Upstream pooling is CLS; `.get("onnx_pooling", "cls")` in model_loader
        # defaults correctly. ONNX is blocked anyway via trust_remote_code=True.
    },
    "Alibaba-NLP/gte-modernbert-base": {
        "dimension": 768,
        "max_context": 8192,
        "description": "Lightweight code-optimized model (CoIR: 79.31 NDCG@10, 144 docs/s throughput)",
        "vram_gb": "0.28GB",
        "fallback_batch_size": 256,
        "model_type": "code-optimized",
        "onnx_pooling": "cls",  # GTE-ModernBERT uses CLS pooling
    },
    "jinaai/jina-embeddings-v5-text-small-retrieval": {
        "dimension": 1024,
        "max_context": 32768,
        "description": "0.6B distilled from Qwen3-Embedding-4B; near-4B quality at 0.6B size (1.2-1.5GB VRAM)",
        "vram_gb": "1.2-1.5GB",
        "fallback_batch_size": 256,
        "trust_remote_code": True,
        # Last-token pooling: ONNX wrapper supports only cls/mean — gate ONNX off.
        "onnx_supported": False,
        "instruction_mode": "prompt_name",  # passes prompt_name="query" to encode for queries
        "prompt_name": "query",
        "passage_prefix": "",  # -retrieval task adapter merged in; no explicit doc prefix needed
    },
}


# Multi-hop search configuration
# Based on empirical testing: 2 hops with 0.3 expansion provides optimal balance
# of discovery quality and performance (+25-35ms overhead, 93%+ queries benefit)


@dataclass
class EmbeddingConfig:
    """Embedding model configuration (9 fields)."""

    model_name: str = "google/embeddinggemma-300m"
    dimension: int = 768
    batch_size: int = 128  # Dynamic based on model, see MODEL_REGISTRY
    query_cache_size: int = 128  # LRU cache size for query embeddings

    # Context Enhancement Features (v0.8.0+)
    enable_import_context: bool = True  # Include import statements in embeddings
    enable_class_context: bool = True  # Include parent class signature for methods
    max_import_lines: int = 10  # Maximum import lines to extract
    max_class_signature_lines: int = 5  # Maximum lines for class signature
    enable_structural_header: bool = (
        True  # Prepend file path + chunk type + qualified name
    )


@dataclass
class SearchModeConfig:
    """Search mode and BM25 settings (12 fields)."""

    default_mode: str = "hybrid"  # hybrid, semantic, bm25, auto
    enable_hybrid: bool = True

    # Hybrid Search Weights
    bm25_weight: float = 0.35
    dense_weight: float = 0.65

    # BM25 Configuration
    bm25_k_parameter: int = 100
    bm25_use_stopwords: bool = True
    bm25_use_stemming: bool = True  # Snowball stemmer for word normalization
    min_bm25_score: float = 0.1

    # Reranking Configuration
    rrf_k_parameter: int = 100
    enable_result_reranking: bool = True

    # Search Result Limits
    default_k: int = (
        4  # Reduced from 5: 0% result loss post-ego-fix + 20% token savings
    )
    max_k: int = 50

    # Context budget (0 = unlimited)
    default_max_context_tokens: int = 0


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
    vram_limit_fraction: float = 0.80  # Hard VRAM ceiling (80% of dedicated)
    allow_ram_fallback: bool = (
        False  # Allow spillover to system RAM (slower but reliable)
    )

    # Precision Configuration (fp16/bf16 for faster inference)
    enable_fp16: bool = True  # Enable fp16 for GPU (30-50% faster inference)
    prefer_bf16: bool = True  # Prefer bf16 on Ampere+ GPUs (better accuracy than fp16)

    # Dynamic Batch Sizing (GPU-based optimization)
    enable_dynamic_batch_size: bool = True  # Enable GPU-based auto-sizing
    dynamic_batch_min: int = (
        16  # Minimum batch size (lowered for fragmentation headroom)
    )
    dynamic_batch_max: int = 384  # Maximum batch size (safer for 8-16GB GPUs)

    # ONNX Runtime inference (optional — requires uv pip install -e .[onnx])
    use_onnx: bool = (
        False  # When True, loads eligible models via ORTModelForFeatureExtraction
    )
    # Constrain ORT CUDAExecutionProvider arena (same formula as set_vram_limit()).
    # Disable only for debugging — prevents WDDM spillover for ONNX sessions.
    onnx_gpu_mem_limit: bool = True

    # Auto-reindexing
    enable_auto_reindex: bool = True
    max_index_age_minutes: float = 5.0


@dataclass
class MultiHopConfig:
    """Multi-hop search settings (6 fields)."""

    enabled: bool = True
    hop_count: int = 2  # Number of expansion hops
    expansion: float = 0.3  # Expansion factor per hop
    initial_k_multiplier: float = 2.0  # Multiplier for initial results (k * multiplier)
    multi_hop_mode: str = "hybrid"  # "semantic" | "graph" | "hybrid"
    edge_weights: dict[str, float] | None = (
        None  # Intent-specific weights (None = DEFAULT_EDGE_WEIGHTS)
    )


@dataclass
class RoutingConfig:
    """Multi-model routing settings (3 fields)."""

    multi_model_enabled: bool = True  # Enable intelligent query routing across models
    default_model: str = "qwen3_0.6b"  # Default model key for routing (best quality)
    multi_model_pool: str | None = (
        None  # Pool type: "full", "lightweight-speed", or "lightweight-accuracy"
    )


@dataclass
class IntentConfig:
    """Intent classification settings (6 fields)."""

    enabled: bool = True  # Enable intent classification for query routing
    confidence_threshold: float = 0.35  # Minimum confidence for intent-specific routing
    default_intent: str = "HYBRID"  # Default intent when confidence is low
    log_classifications: bool = True  # Log intent classification decisions
    semantic_enabled: bool = False  # Enable semantic anchor-embedding scoring (opt-in)
    semantic_weight: float = 0.3  # Semantic score weight in ensemble (0.0-1.0)


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
    """MCP output formatting settings (2 fields)."""

    format: str = (
        "ultra"  # verbose, compact, ultra (default: ultra for 45-55% token reduction)
    )
    source_order_output: bool = True  # Reorder results by file position (DOS RAG)


@dataclass
class ChunkingConfig:
    """Chunking algorithm settings (12 fields)."""

    # Token size constraints for chunks
    min_chunk_tokens: int = 50  # Minimum tokens before considering merge
    max_merged_tokens: int = (
        400  # Maximum tokens for merged chunk (research: 200-400 optimal)
    )

    # Community Detection settings (independent control restored)
    enable_community_detection: bool = (
        True  # Enable community detection via Louvain algorithm
    )
    enable_community_merge: bool = (
        True  # Enable community-based remerge (full index only)
    )
    community_resolution: float = (
        1.0  # Resolution parameter (higher = more/smaller communities)
    )
    max_phantom_degree: int = (
        20  # Skip phantom nodes with >N callers during community detection
    )

    # Large function splitting (cAST paper: AST-aware splitting improves Recall@5 +66%)
    enable_large_node_splitting: bool = True  # Split functions > max_chunk_lines
    max_chunk_lines: int = 100  # Maximum lines before AST block splitting

    # Token estimation method
    token_estimation: str = "whitespace"  # "whitespace" (fast) or "tiktoken" (accurate)

    # Size method for chunking (Option A: character-based vs Option B: token-based)
    size_method: str = "tokens"  # "tokens" (default) or "characters" (cAST paper)

    # Splitting-specific configs (separate from merging)
    split_size_method: str = "characters"  # "lines" or "characters"
    max_split_chars: int = (
        1600  # Character-based splitting (~400 tokens, optimal for retrieval)
    )

    # File-level module summaries (A2: improve GLOBAL query recall)
    enable_file_summaries: bool = True  # Generate module-summary chunks per file

    # Community-level summaries (B1: thematic grouping via Louvain communities)
    enable_community_summaries: bool = True  # Generate community-summary chunks

    # Incremental community-summary refresh (subordinate to enable_community_summaries)
    enable_incremental_community_summaries: bool = (
        True  # Refresh stale community summaries on incremental index
    )
    incremental_community_redetect_threshold: float = (
        0.3  # Cumulative changed-file fraction that triggers full redetect
    )

    # Adaptive chunk sizing (research: P75 baseline + complexity modulation)
    sizing_mode: str = "fixed"  # "fixed" (static) or "adaptive" (repo-profiled)
    adaptive_multiplier_max: float = 1.3  # T_max = P75_baseline × this (low-complexity)
    adaptive_multiplier_min: float = (
        0.5  # T_min = P75_baseline × this (high-complexity)
    )
    max_complexity_cap: int = 30  # Cv normalization ceiling (CC >= cap → Cv = 1.0)


@dataclass
class EgoGraphConfig:
    """Ego-graph retrieval settings (RepoGraph ICLR 2025)."""

    enabled: bool = False  # Enable ego-graph expansion
    k_hops: int = 1  # Number of hops (1=direct neighbors, reduces noise vs 2-hop)
    max_neighbors_per_hop: int = (
        5  # Max neighbors per hop (reduced from 10 to limit noise)
    )
    relation_types: list | None = None  # Filter to specific relations (None = all)
    include_anchor: bool = True  # Include original anchor nodes in results
    deduplicate: bool = True  # Remove duplicate chunk_ids
    # RepoGraph relation filtering (Feature #5)
    exclude_stdlib_imports: bool = True  # Filter stdlib from graph traversal
    exclude_third_party_imports: bool = True  # Filter third-party from traversal
    # Weighted graph traversal
    edge_weights: dict[str, float] | None = field(
        default_factory=lambda: DEFAULT_EDGE_WEIGHTS.copy()
    )  # Use weighted BFS by default (calls > imports priority)
    # QW2: community-bounded expansion — prefer intra-community neighbors
    community_bounded: bool = True  # Apply cross-community penalty when ranking
    cross_community_penalty: float = (
        0.6  # Score multiplier for cross-community neighbors
    )
    # QW3: expansion mode — "bfs" (default) or "ppr" (Personalized PageRank)
    expansion_mode: str = "bfs"  # "bfs" = k-hop BFS, "ppr" = Personalized PageRank
    ppr_alpha: float = 0.85  # PPR damping factor (standard default)
    # QW5: minimum cosine similarity threshold for ego-graph neighbor filtering
    min_similarity_threshold: float = 0.15  # Neighbors below this are filtered out


@dataclass
class ParentRetrievalConfig:
    """Parent chunk retrieval settings for Match Small, Retrieve Big."""

    enabled: bool = False  # Disabled — parents get score=0, no ranking value
    include_parent_content: bool = True  # Include parent's full content
    max_parents_per_result: int = 1  # Usually 1 (direct parent only)


@dataclass
class GraphEnhancedConfig:
    """Graph-enhanced search settings."""

    centrality_method: str = "pagerank"  # Centrality algorithm
    centrality_alpha: float = 0.3  # Blending weight (0=semantic, 1=centrality)
    centrality_annotation: bool = True  # Always annotate centrality when graph exists
    centrality_reranking: bool = True  # Always rerank by blended score
    # Chunk-size normalization (penalize oversized chunks)
    enable_size_normalization: bool = True  # Enable logarithmic size penalty
    size_norm_target_lines: int = 200  # Target chunk size (no penalty below this)
    size_norm_alpha: float = 0.1  # Penalty strength (higher = stronger penalty)
    # Centrality-adaptive BM25 boost (LIMIT paper insight)
    # High-centrality chunks (utility functions, base classes) are exactly where
    # single-vector embeddings fail. Extra boost compensates for this limitation.
    centrality_bm25_boost: bool = (
        True  # Enable adaptive boost for high-centrality results
    )
    centrality_boost_threshold: float = (
        0.02  # Centrality score threshold to trigger boost
    )
    centrality_boost_factor: float = 5.0  # Multiplier: boost = centrality * factor
    centrality_boost_cap: float = 0.15  # Maximum boost added to blended_score


@dataclass
class ObservabilityConfig:
    """OTel tracing configuration (traces-only v1; metrics deferred to v2)."""

    enabled: bool = False
    service_name: str = "claude-context-local"
    exporter: str = "otlp"  # otlp | console(->stderr) | none
    otlp_endpoint: str = "http://localhost:4318"
    sample_ratio: float = 1.0
    capture_query_text: bool = False  # off by default (query text can be sensitive)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Merge *override* into *base* in-place.

    One level of nesting is sufficient for SearchConfig (sub-config dicts are flat).
    Sub-config dicts are merged field-by-field so an override touching only a subset
    of fields does not wipe out the rest.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key].update(value)
        else:
            base[key] = value


class SearchConfig:
    """Root configuration with nested sub-configs.

    Configuration organization:
    - Split into 8 focused sub-configs for better organization
    - embedding, search_mode, performance, multi_hop, routing, intent, reranker, output, chunking

    Initialization style (nested configs only):
        config = SearchConfig(embedding=EmbeddingConfig(model_name="..."))
    """

    def __init__(
        self,
        embedding: EmbeddingConfig | None = None,
        search_mode: SearchModeConfig | None = None,
        performance: PerformanceConfig | None = None,
        multi_hop: MultiHopConfig | None = None,
        routing: RoutingConfig | None = None,
        intent: IntentConfig | None = None,
        reranker: RerankerConfig | None = None,
        output: OutputConfig | None = None,
        chunking: ChunkingConfig | None = None,
        ego_graph: EgoGraphConfig | None = None,
        parent_retrieval: ParentRetrievalConfig | None = None,
        graph_enhanced: GraphEnhancedConfig | None = None,
        observability: ObservabilityConfig | None = None,
    ):
        """Initialize SearchConfig with nested sub-configs.

        Args:
            embedding: EmbeddingConfig instance (optional, defaults to EmbeddingConfig())
            search_mode: SearchModeConfig instance (optional, defaults to SearchModeConfig())
            performance: PerformanceConfig instance (optional, defaults to PerformanceConfig())
            multi_hop: MultiHopConfig instance (optional, defaults to MultiHopConfig())
            routing: RoutingConfig instance (optional, defaults to RoutingConfig())
            intent: IntentConfig instance (optional, defaults to IntentConfig())
            reranker: RerankerConfig instance (optional, defaults to RerankerConfig())
            output: OutputConfig instance (optional, defaults to OutputConfig())
            chunking: ChunkingConfig instance (optional, defaults to ChunkingConfig())
            ego_graph: EgoGraphConfig instance (optional, defaults to EgoGraphConfig())
            parent_retrieval: ParentRetrievalConfig instance (optional, defaults to ParentRetrievalConfig())
            graph_enhanced: GraphEnhancedConfig instance (optional, defaults to GraphEnhancedConfig())
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
        self.intent = intent if intent is not None else IntentConfig()
        self.reranker = reranker if reranker is not None else RerankerConfig()
        self.output = output if output is not None else OutputConfig()
        self.chunking = chunking if chunking is not None else ChunkingConfig()
        self.ego_graph = ego_graph if ego_graph is not None else EgoGraphConfig()
        self.parent_retrieval = (
            parent_retrieval
            if parent_retrieval is not None
            else ParentRetrievalConfig()
        )
        self.graph_enhanced = (
            graph_enhanced if graph_enhanced is not None else GraphEnhancedConfig()
        )
        self.observability = (
            observability if observability is not None else ObservabilityConfig()
        )

    # ------------------------------------------------------------------
    # Serialization schema — single source of truth
    # Adding a field to a sub-config dataclass is sufficient; no manual
    # update of to_dict / from_dict is required.
    # ------------------------------------------------------------------

    _SUBCONFIG_FIELDS: tuple[str, ...] = (
        "embedding",
        "search_mode",
        "performance",
        "multi_hop",
        "routing",
        "intent",
        "reranker",
        "output",
        "chunking",
        "ego_graph",
        "parent_retrieval",
        "graph_enhanced",
        "observability",
    )

    # frozenset for O(1) membership tests in _flat_to_nested / is_nested checks
    _SUBCONFIG_NAMES: frozenset[str] = frozenset(_SUBCONFIG_FIELDS)

    _SUBCONFIG_TYPES: dict[str, type] = {
        "embedding": EmbeddingConfig,
        "search_mode": SearchModeConfig,
        "performance": PerformanceConfig,
        "multi_hop": MultiHopConfig,
        "routing": RoutingConfig,
        "intent": IntentConfig,
        "reranker": RerankerConfig,
        "output": OutputConfig,
        "chunking": ChunkingConfig,
        "ego_graph": EgoGraphConfig,
        "parent_retrieval": ParentRetrievalConfig,
        "graph_enhanced": GraphEnhancedConfig,
        "observability": ObservabilityConfig,
    }

    # Maps legacy flat config keys (and env-var flat keys) to
    # (sub_config_name, field_name) in the nested schema.
    # Used by _flat_to_nested() and by SearchConfigManager.load_config()
    # to translate env overrides into the nested structure before merging.
    _FLAT_KEY_ALIASES: dict[str, tuple[str, str]] = {
        # EmbeddingConfig
        "embedding_model_name": ("embedding", "model_name"),
        "model_dimension": ("embedding", "dimension"),
        "embedding_batch_size": ("embedding", "batch_size"),
        "query_cache_size": ("embedding", "query_cache_size"),
        "enable_import_context": ("embedding", "enable_import_context"),
        "enable_class_context": ("embedding", "enable_class_context"),
        "max_import_lines": ("embedding", "max_import_lines"),
        "max_class_signature_lines": ("embedding", "max_class_signature_lines"),
        "enable_structural_header": ("embedding", "enable_structural_header"),
        # SearchModeConfig
        "default_search_mode": ("search_mode", "default_mode"),
        "enable_hybrid_search": ("search_mode", "enable_hybrid"),
        "bm25_weight": ("search_mode", "bm25_weight"),
        "dense_weight": ("search_mode", "dense_weight"),
        "bm25_k_parameter": ("search_mode", "bm25_k_parameter"),
        "bm25_use_stopwords": ("search_mode", "bm25_use_stopwords"),
        "bm25_use_stemming": ("search_mode", "bm25_use_stemming"),
        "min_bm25_score": ("search_mode", "min_bm25_score"),
        "rrf_k_parameter": ("search_mode", "rrf_k_parameter"),
        "enable_result_reranking": ("search_mode", "enable_result_reranking"),
        "default_k": ("search_mode", "default_k"),
        "max_k": ("search_mode", "max_k"),
        # PerformanceConfig
        "use_parallel_search": ("performance", "use_parallel_search"),
        "max_parallel_workers": ("performance", "max_parallel_workers"),
        "enable_parallel_chunking": ("performance", "enable_parallel_chunking"),
        "max_chunking_workers": ("performance", "max_chunking_workers"),
        "enable_entity_tracking": ("performance", "enable_entity_tracking"),
        "prefer_gpu": ("performance", "prefer_gpu"),
        "enable_fp16": ("performance", "enable_fp16"),
        "prefer_bf16": ("performance", "prefer_bf16"),
        "enable_dynamic_batch_size": ("performance", "enable_dynamic_batch_size"),
        "dynamic_batch_min": ("performance", "dynamic_batch_min"),
        "dynamic_batch_max": ("performance", "dynamic_batch_max"),
        "enable_auto_reindex": ("performance", "enable_auto_reindex"),
        "max_index_age_minutes": ("performance", "max_index_age_minutes"),
        "use_onnx": ("performance", "use_onnx"),
        "onnx_gpu_mem_limit": ("performance", "onnx_gpu_mem_limit"),
        "allow_shared_memory": ("performance", "allow_ram_fallback"),  # backward-compat
        # MultiHopConfig
        "enable_multi_hop": ("multi_hop", "enabled"),
        "multi_hop_count": ("multi_hop", "hop_count"),
        "multi_hop_expansion": ("multi_hop", "expansion"),
        "multi_hop_initial_k_multiplier": ("multi_hop", "initial_k_multiplier"),
        "multi_hop_mode": ("multi_hop", "multi_hop_mode"),
        # RoutingConfig
        "multi_model_enabled": ("routing", "multi_model_enabled"),
        "routing_default_model": ("routing", "default_model"),
        "routing_multi_model_pool": ("routing", "multi_model_pool"),
        # IntentConfig
        "intent_enabled": ("intent", "enabled"),
        "intent_confidence_threshold": ("intent", "confidence_threshold"),
        "intent_default_intent": ("intent", "default_intent"),
        "intent_log_classifications": ("intent", "log_classifications"),
        "intent_semantic_enabled": ("intent", "semantic_enabled"),
        "intent_semantic_weight": ("intent", "semantic_weight"),
        # RerankerConfig
        "reranker_enabled": ("reranker", "enabled"),
        "reranker_model_name": ("reranker", "model_name"),
        "reranker_top_k_candidates": ("reranker", "top_k_candidates"),
        "reranker_min_vram_gb": ("reranker", "min_vram_gb"),
        "reranker_batch_size": ("reranker", "batch_size"),
        # OutputConfig
        "output_format": ("output", "format"),
        "source_order_output": ("output", "source_order_output"),
        # ChunkingConfig (flat keys equal their field names for most)
        "min_chunk_tokens": ("chunking", "min_chunk_tokens"),
        "max_merged_tokens": ("chunking", "max_merged_tokens"),
        "enable_large_node_splitting": ("chunking", "enable_large_node_splitting"),
        "max_chunk_lines": ("chunking", "max_chunk_lines"),
        "token_estimation": ("chunking", "token_estimation"),
        "community_resolution": ("chunking", "community_resolution"),
        "size_method": ("chunking", "size_method"),
        "enable_community_detection": ("chunking", "enable_community_detection"),
        "enable_community_merge": ("chunking", "enable_community_merge"),
        "split_size_method": ("chunking", "split_size_method"),
        "max_split_chars": ("chunking", "max_split_chars"),
        "max_phantom_degree": ("chunking", "max_phantom_degree"),
        # EgoGraphConfig
        "ego_graph_enabled": ("ego_graph", "enabled"),
        "ego_graph_k_hops": ("ego_graph", "k_hops"),
        "ego_graph_max_neighbors_per_hop": ("ego_graph", "max_neighbors_per_hop"),
        "ego_graph_relation_types": ("ego_graph", "relation_types"),
        "ego_graph_include_anchor": ("ego_graph", "include_anchor"),
        "ego_graph_deduplicate": ("ego_graph", "deduplicate"),
        # GraphEnhancedConfig (flat keys equal their field names)
        "centrality_method": ("graph_enhanced", "centrality_method"),
        "centrality_alpha": ("graph_enhanced", "centrality_alpha"),
        "centrality_annotation": ("graph_enhanced", "centrality_annotation"),
        "centrality_reranking": ("graph_enhanced", "centrality_reranking"),
        "enable_size_normalization": ("graph_enhanced", "enable_size_normalization"),
        "size_norm_target_lines": ("graph_enhanced", "size_norm_target_lines"),
        "size_norm_alpha": ("graph_enhanced", "size_norm_alpha"),
        "centrality_bm25_boost": ("graph_enhanced", "centrality_bm25_boost"),
        "centrality_boost_threshold": ("graph_enhanced", "centrality_boost_threshold"),
        "centrality_boost_factor": ("graph_enhanced", "centrality_boost_factor"),
        "centrality_boost_cap": ("graph_enhanced", "centrality_boost_cap"),
        # ObservabilityConfig
        "otel_enabled": ("observability", "enabled"),
        "otel_service_name": ("observability", "service_name"),
        "otel_exporter": ("observability", "exporter"),
        "otel_endpoint": ("observability", "otlp_endpoint"),
        "otel_sample_ratio": ("observability", "sample_ratio"),
        "otel_capture_query_text": ("observability", "capture_query_text"),
    }

    def to_dict(self) -> dict[str, Any]:
        """Convert to nested dictionary for JSON serialization.

        Uses dataclasses.asdict so every sub-config field is included automatically.
        Adding a field to a sub-config dataclass requires no change here.
        """
        return {
            name: dataclasses.asdict(getattr(self, name))
            for name in self._SUBCONFIG_FIELDS
        }

    @staticmethod
    def _build_subconfig(cls_type: type, data: dict[str, Any]) -> Any:
        """Instantiate a sub-config dataclass from a dict, using dataclass defaults for
        any missing keys.  Unknown keys are silently dropped (forward-compatible).
        """
        valid = {f.name for f in dataclasses.fields(cls_type)}
        return cls_type(**{k: v for k, v in data.items() if k in valid})

    @classmethod
    def _flat_to_nested(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Translate a flat (legacy / env-var) key dict into the nested sub-config structure.

        Only keys present in _FLAT_KEY_ALIASES are translated; unknown keys are dropped.
        """
        nested: dict[str, dict[str, Any]] = {}
        for flat_key, value in data.items():
            if flat_key in cls._FLAT_KEY_ALIASES:
                sub_name, field_name = cls._FLAT_KEY_ALIASES[flat_key]
                nested.setdefault(sub_name, {})[field_name] = value
        return nested

    @staticmethod
    def _apply_model_registry_dimension(embedding_data: dict[str, Any]) -> None:
        """Sync dimension (and optionally batch_size) from MODEL_REGISTRY in-place.

        Extracted to avoid duplicating the auto-update logic across the two old
        from_dict branches.
        """
        model_name = embedding_data.get("model_name")
        if model_name:
            model_config = get_model_config(model_name)
            if model_config:
                embedding_data["dimension"] = (
                    model_config.get("truncate_dim") or model_config["dimension"]
                )
                if "batch_size" not in embedding_data:
                    embedding_data["batch_size"] = model_config.get(
                        "fallback_batch_size", 128
                    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchConfig":
        """Create from dictionary (supports both flat and nested formats).

        Detects format automatically:
        - Nested: {"embedding": {...}, "search_mode": {...}, ...}
        - Flat (legacy): {"embedding_model_name": "...", "default_search_mode": "...", ...}

        Dataclass defaults are the single source of truth for missing keys — no
        hard-coded fallback values in this method.  Adding a field to any sub-config
        dataclass is sufficient; this method does not need to be updated.

        Args:
            data: Dictionary in either format

        Returns:
            SearchConfig with populated nested sub-configs
        """
        # Detect nested format: any key that is a sub-config section name with a dict
        # value.  Checking all section names (not just "embedding") handles partial
        # nested dicts produced by env-only loads or single-section overrides.
        is_nested = any(
            isinstance(v, dict) and k in cls._SUBCONFIG_NAMES for k, v in data.items()
        )

        if is_nested:
            # Shallow-copy sub-dicts so we never mutate the caller's data
            nested: dict[str, Any] = {
                k: dict(v) if isinstance(v, dict) else v for k, v in data.items()
            }
            # Backward-compat: allow_shared_memory may appear inside the nested
            # performance dict (pre-v0.8.0 configs that were partially upgraded).
            perf = nested.get("performance")
            if (
                isinstance(perf, dict)
                and "allow_shared_memory" in perf
                and "allow_ram_fallback" not in perf
            ):
                perf["allow_ram_fallback"] = perf.pop("allow_shared_memory")
        else:
            # LEGACY: Flat format (pre-v0.8.0) — translate via alias map
            nested = cls._flat_to_nested(data)

        cls._apply_model_registry_dimension(nested.setdefault("embedding", {}))

        return cls(
            **{
                name: cls._build_subconfig(
                    cls._SUBCONFIG_TYPES[name], nested.get(name) or {}
                )
                for name in cls._SUBCONFIG_FIELDS
            }
        )


class SearchConfigManager:
    """Manages search configuration from environment variables and config files."""

    def __init__(self, config_file: str | None = None):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file or self._get_default_config_path()
        self._config = None
        self._config_mtime: float | None = None  # Track file modification time

    def _get_default_config_path(self) -> str:
        """Get default config file path (delegates to shared config_paths module)."""
        return resolve_config_path()

    def load_config(self) -> SearchConfig:
        """Load configuration from file and environment variables."""
        # Check if file changed since last load
        current_mtime = None
        _config_path = Path(self.config_file)
        if _config_path.exists():
            current_mtime = _config_path.stat().st_mtime

        # Return cache only if file hasn't changed
        if self._config is not None and current_mtime == self._config_mtime:
            return self._config

        # Start with defaults
        config_dict: dict[str, Any] = {}

        # Load from file if exists
        if _config_path.exists():
            try:
                with open(self.config_file) as f:
                    raw = json.load(f)
                self.logger.info(f"Loaded search config from {self.config_file}")
                # Normalise to nested format so env overrides can be deep-merged
                # without mixing flat and nested keys in a single dict.
                file_is_nested = any(
                    isinstance(v, dict) and k in SearchConfig._SUBCONFIG_NAMES
                    for k, v in raw.items()
                )
                config_dict = (
                    raw if file_is_nested else SearchConfig._flat_to_nested(raw)
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to load config file {self.config_file}: {e}"
                )

        # Translate env-var flat keys to nested and deep-merge so they apply over
        # a nested config file (previously the update() call was a no-op for nested
        # files because the flat env keys were never read by the nested branch).
        env_overrides = self._load_from_environment()
        env_nested = SearchConfig._flat_to_nested(env_overrides)
        _deep_merge(config_dict, env_nested)

        # Create config object
        self._config = SearchConfig.from_dict(config_dict)

        # Store mtime after loading
        self._config_mtime = current_mtime

        self.logger.info(
            f"Search mode: {self._config.search_mode.default_mode}, "
            f"hybrid enabled: {self._config.search_mode.enable_hybrid}"
        )

        return self._config

    def _load_from_environment(self) -> dict[str, Any]:
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
            "CLAUDE_RERANKER_ENABLED": ("reranker_enabled", self._bool_from_env),
            "CLAUDE_RERANKER_MODEL": ("reranker_model_name", str),
            "CLAUDE_RERANKER_TOP_K": ("reranker_top_k_candidates", int),
            "CLAUDE_RERANKER_MIN_VRAM_GB": ("reranker_min_vram_gb", float),
            "CLAUDE_RERANKER_BATCH_SIZE": ("reranker_batch_size", int),
            # Observability (OTel tracing) env vars
            "CLAUDE_OTEL_ENABLED": ("otel_enabled", self._bool_from_env),
            "CLAUDE_OTEL_EXPORTER": ("otel_exporter", str),
            "CLAUDE_OTEL_ENDPOINT": ("otel_endpoint", str),
            "CLAUDE_OTEL_SAMPLE": ("otel_sample_ratio", float),
            "CLAUDE_OTEL_CAPTURE_QUERY": (
                "otel_capture_query_text",
                self._bool_from_env,
            ),
        }

        config_dict = {}
        for env_var, (config_key, converter) in env_mapping.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    # pyrefly: ignore [unsupported-operation]
                    config_dict[config_key] = converter(env_value)
                    self.logger.debug(
                        f"Set {config_key} = {config_dict[config_key]} from {env_var}"
                    )
                except ValueError as e:
                    self.logger.warning(
                        f"Invalid value for {env_var}: {env_value} ({e})"
                    )

        # Auto-detect: if standard OTEL_* vars are present without CLAUDE_OTEL_ENABLED,
        # treat as opted-in with OTLP (network exporter — never touches stdio).
        if (
            "CLAUDE_OTEL_ENABLED" not in os.environ
            and "otel_enabled" not in config_dict
            and any(k.startswith("OTEL_") for k in os.environ)
        ):
            config_dict["otel_enabled"] = True
            if "otel_exporter" not in config_dict:
                config_dict["otel_exporter"] = "otlp"
            self.logger.info(
                "[OTEL] Auto-detected OTEL_* env vars — enabling OTLP tracing"
            )

        return config_dict

    def _bool_from_env(self, value: str) -> bool:
        """Convert environment variable string to boolean."""
        return value.lower() in ("true", "1", "yes", "on", "enabled")

    def save_config(self, config: SearchConfig) -> None:
        """Save configuration to file with atomic write protection."""
        try:
            # Auto-sync dimension from model registry before saving
            model_config = get_model_config(config.embedding.model_name)
            if model_config:
                # Use truncate_dim if MRL is enabled, otherwise use native dimension
                config.embedding.dimension = (
                    model_config.get("truncate_dim") or model_config["dimension"]
                )

            # Create directory if needed (pathlib handles the current-dir no-op case)
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)

            # ATOMIC WRITE: Write to temp file first, then rename
            # This prevents data loss if exception occurs during write
            temp_file = self.config_file + ".tmp"
            config_dict = config.to_dict()  # Serialize BEFORE opening file

            with open(temp_file, "w") as f:
                json.dump(config_dict, f, indent=2)

            # Validate temp file before replacing original
            with open(temp_file) as f:
                json.load(f)  # Verify valid JSON was written

            # Atomic rename (safe on same filesystem)
            os.replace(temp_file, self.config_file)

            self.logger.info(f"Saved search config to {self.config_file}")
            self._config = config  # Update cached config
            # Sync mtime so the next load_config() short-circuits to the cache
            # instead of re-reading and re-parsing the file we just wrote.
            self._config_mtime = Path(self.config_file).stat().st_mtime

        except Exception as e:
            self.logger.error(f"Failed to save config to {self.config_file}: {e}")
            # Clean up temp file if it exists
            temp_file = self.config_file + ".tmp"
            Path(temp_file).unlink(missing_ok=True)
            raise  # Re-raise so caller knows save failed

    def get_search_mode_for_query(
        self, query: str, explicit_mode: str | None = None
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
            keyword in query_lower for keyword in ["string", "message", "error", "log"]
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
_config_manager: SearchConfigManager | None = None


def get_config_manager(config_file: str | None = None) -> SearchConfigManager:
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


def get_model_registry() -> dict[str, dict[str, Any]]:
    """Get the model registry with all supported models."""
    return MODEL_REGISTRY


def get_model_config(model_name: str) -> dict[str, Any] | None:
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
