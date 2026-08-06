"""Configuration system for search modes and hybrid search features."""

import dataclasses
import json
import logging
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

# Import DEFAULT_EDGE_WEIGHTS for ego-graph weighted BFS
from graph.graph_storage import DEFAULT_EDGE_WEIGHTS
from search.config_paths import resolve_config_path
from utils.atomic_io import write_json_atomic


MODEL_REGISTRY = {
    "google/embeddinggemma-300m": {
        "dimension": 768,
        "max_context": 2048,
        "passage_prefix": "Retrieval-document: ",
        "description": "Default model, fast and efficient",
        "vram_gb": "~1.2GB",  # 300M params @FP16 ≈0.6GB weights + buffers; original "4-8GB" was stale estimate
        "fallback_batch_size": 128,  # Used when dynamic sizing disabled
    },
    "BAAI/bge-m3": {
        "dimension": 1024,
        "max_context": 8192,
        "description": "Recommended upgrade, hybrid search support",
        "vram_gb": "1-1.5GB",  # Updated from "3-4GB" (actual measured: 1.07GB)
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
    "codefuse-ai/F2LLM-v2-0.6B": {
        "dimension": 1024,
        "max_context": 40960,
        "description": "Qwen3-0.6B-based embedding (MTEB avg 66.47 vs Qwen3-0.6B 64.02)",
        "vram_gb": "2.2GB",
        "fallback_batch_size": 256,
        "vram_tier": "minimal",  # Usable on all GPUs
        # Instruction tuning for code retrieval (same "Instruct: ...\nQuery: "
        # template family as Qwen3-Embedding; documents are embedded raw)
        "instruction_mode": "custom",  # "custom" or "prompt_name"
        "query_instruction": "Instruct: Retrieve source code implementations matching the query\nQuery: ",
        "prompt_name": "query",  # Alternative: model's built-in generic passage prompt
    },
}


# Multi-hop search configuration
# Based on empirical testing: 2 hops with 0.3 expansion provides optimal balance
# of discovery quality and performance (+25-35ms overhead, 93%+ queries benefit)


def spec(
    *,
    range: tuple[float, float] | None = None,
    choices: tuple[str, ...] | None = None,
    flat_alias: str | None = None,
    env: str | None = None,
    mcp: str | None = None,
    reader: str | None = None,
    schema_only: bool = False,
    construction_baked: bool = False,
) -> dict[str, Any]:
    """Build a ``field(metadata=...)`` dict for one config field — the single
    declaration site for its validation rule, legacy/env alias, MCP exposure,
    and liveness anchor (see ADR-0022).

    Every key is explicit and defaults to absent/``None`` — nothing here is
    inferred from the field's name, so a field with no alias or no env var
    stays that way rather than acquiring one by convention.  ``reader`` names
    the production file whose behavior the field actually controls (checked
    by ``test_config_field_liveness.py``); ``schema_only=True`` is the escape
    hatch for a field that has no single behavioral reader. ``construction_baked``
    marks a field that is read once into a collaborator at construction time
    (e.g. a cached ``HybridSearcher``/reranker instance) rather than live per
    call — mutating it on the config singleton is a no-op until that
    collaborator is rebuilt (see ``evaluation/arm_overrides.py``'s
    ``requires_rebuild`` and Part 2 / C1 of the ADR-0018 follow-on plan).
    """
    meta: dict[str, Any] = {}
    if range is not None:
        meta["range"] = range
    if choices is not None:
        meta["choices"] = choices
    if flat_alias is not None:
        meta["flat_alias"] = flat_alias
    if env is not None:
        meta["env"] = env
    if mcp is not None:
        meta["mcp"] = mcp
    if reader is not None:
        meta["reader"] = reader
    if schema_only:
        meta["schema_only"] = True
    if construction_baked:
        meta["construction_baked"] = True
    return meta


@dataclass
class EmbeddingConfig:
    """Embedding model configuration (11 fields)."""

    model_name: str = field(
        default="BAAI/bge-m3",
        metadata=spec(
            flat_alias="embedding_model_name",
            env="CLAUDE_EMBEDDING_MODEL",
            reader="embeddings/model_loader.py",
        ),
    )
    dimension: int = field(
        default=1024,  # Derived, not configured: overwritten from
        # MODEL_REGISTRY[model_name] on every from_dict() and save_config() call
        # (_apply_model_registry_dimension). Editing this value in the JSON file
        # has no effect.
        metadata=spec(flat_alias="model_dimension", reader="embeddings/embedder.py"),
    )
    batch_size: int = field(
        default=64,  # Dynamic based on model, see MODEL_REGISTRY. Used only
        # when performance.enable_dynamic_batch_size is False or no CUDA GPU
        # is available — otherwise calculate_optimal_batch_size() overrides it.
        metadata=spec(
            flat_alias="embedding_batch_size",
            env="CLAUDE_EMBEDDING_BATCH_SIZE",
            reader="embeddings/embedder.py",
        ),
    )
    query_cache_size: int = field(
        default=128,  # LRU cache size for query embeddings
        metadata=spec(
            flat_alias="query_cache_size",
            env="CLAUDE_QUERY_CACHE_SIZE",
            reader="embeddings/embedder.py",
        ),
    )

    # Context Enhancement Features (v0.8.0+)
    enable_import_context: bool = field(
        default=True,  # Include import statements in embeddings
        metadata=spec(
            flat_alias="enable_import_context", reader="embeddings/embedder.py"
        ),
    )
    enable_class_context: bool = field(
        default=True,  # Include parent class signature for methods
        metadata=spec(
            flat_alias="enable_class_context", reader="embeddings/embedder.py"
        ),
    )
    max_import_lines: int = field(
        default=25,  # Maximum import lines to extract
        metadata=spec(flat_alias="max_import_lines", reader="embeddings/embedder.py"),
    )
    max_class_signature_lines: int = field(
        default=20,  # Maximum lines for class signature
        metadata=spec(
            flat_alias="max_class_signature_lines", reader="embeddings/embedder.py"
        ),
    )
    enable_structural_header: bool = field(
        default=True,  # Prepend file path + chunk type + qualified name
        metadata=spec(
            flat_alias="enable_structural_header", reader="embeddings/embedder.py"
        ),
    )

    # Persistent content-hash embedding cache (Round 3)
    enable_chunk_cache: bool = field(
        default=True,  # Skip GPU re-embedding for unchanged chunks
        metadata=spec(reader="embeddings/chunk_cache.py"),
    )
    chunk_cache_max_entries: int = field(
        default=0,  # 0 = auto (max(2 * live_keys, 2_000), 32MB clamp)
        metadata=spec(reader="embeddings/chunk_cache.py"),
    )


class SearchMode(StrEnum):
    """The four search-mode values accepted by SearchModeConfig.default_mode.

    A real str subclass — every ``== "hybrid"`` comparison, dict-key lookup,
    and JSON round-trip (dataclasses.asdict + json.dump) keeps working
    unchanged. Centralizes the mode literals so a typo can't silently fall
    through search dispatch logic to the wrong branch.
    """

    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    BM25 = "bm25"
    AUTO = "auto"


@dataclass
class SearchModeConfig:
    """Search mode and BM25 settings."""

    # Typed as ``str`` (not SearchMode) so values loaded from JSON — which are
    # always plain str — remain valid without extra coercion; SearchMode.HYBRID
    # is itself a valid str default since StrEnum subclasses str.
    default_mode: str = field(
        default=SearchMode.HYBRID,
        metadata=spec(
            choices=tuple(m.value for m in SearchMode),
            flat_alias="default_search_mode",
            env="CLAUDE_SEARCH_MODE",
            reader="mcp_server/server.py",
        ),
    )  # hybrid, semantic, bm25, auto
    enable_hybrid: bool = field(
        default=True,
        metadata=spec(
            flat_alias="enable_hybrid_search",
            env="CLAUDE_ENABLE_HYBRID",
            reader="mcp_server/search_factory.py",
        ),
    )

    # Hybrid Search Weights
    #
    # NOT construction_baked: HybridSearcher.__init__ takes no weight
    # parameters. Both fields are read live from effective_config on every
    # search() call (hybrid_searcher.py:731-739), so mutating them on the
    # live config takes effect on the next call — no searcher rebuild needed.
    bm25_weight: float = field(
        default=0.35,
        metadata=spec(
            range=(0.0, 1.0),
            flat_alias="bm25_weight",
            env="CLAUDE_BM25_WEIGHT",
            mcp="search_mode",
            reader="search/hybrid_searcher.py",
        ),
    )
    dense_weight: float = field(
        default=0.65,
        metadata=spec(
            range=(0.0, 1.0),
            flat_alias="dense_weight",
            env="CLAUDE_DENSE_WEIGHT",
            mcp="search_mode",
            reader="search/hybrid_searcher.py",
        ),
    )

    # BM25 Configuration
    # Okapi BM25 scoring parameters (rank_bm25 defaults). k1 controls term-
    # frequency saturation; b controls document-length normalization. No
    # re-index needed — bm25_index.py re-applies configured k1/b against the
    # saved corpus stats on load. But they are read once at HybridSearcher
    # construction (BM25Index build/load/rebuild), not at query time: mutating
    # a live SearchConfig singleton is inert until the index reloads or the
    # searcher is rebuilt (construction_baked=True below drives
    # arm_overrides.requires_rebuild() accordingly). Both are also in
    # index_probe.py's FORBIDDEN_AUTO_TUNE_KEYS — fusion sweep saturated, do
    # not re-sweep; that frozenset governs whether the ADR-0014 auto-tuning
    # probe may write a key, a different question from whether a benchmark
    # arm must rebuild the cached searcher. (Replaces the dead
    # ``bm25_k_parameter`` field, which was never read by any scoring path.)
    bm25_k1: float = field(
        default=1.5,
        metadata=spec(
            flat_alias="bm25_k1",
            reader="search/hybrid_searcher.py",
            construction_baked=True,
        ),
    )
    bm25_b: float = field(
        default=0.75,
        metadata=spec(
            flat_alias="bm25_b",
            reader="search/hybrid_searcher.py",
            construction_baked=True,
        ),
    )
    # Also in FORBIDDEN_AUTO_TUNE_KEYS (A/B 2026-08-01: removing regresses
    # recall@5/MRR) — read once at construction, same rebuild caveat as k1/b.
    bm25_use_stopwords: bool = field(
        default=True,
        metadata=spec(
            flat_alias="bm25_use_stopwords",
            reader="search/hybrid_searcher.py",
            construction_baked=True,
        ),
    )
    # Not in FORBIDDEN_AUTO_TUNE_KEYS — covered by neither guardrail today.
    # Read once at construction like the other four BM25 tuning knobs.
    bm25_use_stemming: bool = field(
        default=True,  # Snowball stemmer for word normalization
        metadata=spec(
            flat_alias="bm25_use_stemming",
            env="CLAUDE_BM25_USE_STEMMING",
            reader="search/hybrid_searcher.py",
            construction_baked=True,
        ),
    )
    # Tokenizer variant (arXiv 2605.18561): "legacy" = destructive camel/snake
    # split + stemming; "whole" = identifiers kept intact, no stemming;
    # "additive" = whole identifiers + camel/snake sub-tokens. Changing this
    # requires a re-index (index/query tokenization must match) — also read
    # once at construction (construction_baked=True) and in
    # FORBIDDEN_AUTO_TUNE_KEYS (INDEX_VERSION 4, identifier-preserving
    # "whole" tokenizer).
    # Default "whole": +0.05/+0.07 Recall@5, +0.09/+0.10 MRR vs legacy on the
    # 96q/63q golden sets (BM25-standalone, bm25_tokenizer_ab.py 2026-07-26).
    bm25_tokenizer: str = field(
        default="whole",
        metadata=spec(
            choices=("legacy", "whole", "additive"),
            flat_alias="bm25_tokenizer",
            reader="search/hybrid_searcher.py",
            construction_baked=True,
        ),
    )
    # Reserved fused-pool slots for BM25-unique candidates. Under weighted RRF
    # (bm25 0.35 / dense 0.65, rrf_k 100) the best BM25-unique candidate scores
    # below the worst dense candidate, so the fused pool is 100% dense-sourced
    # (see evaluation/POOL_MISS_DIAGNOSIS.md). N > 0 fills the last N pool
    # slots with the top BM25-only candidates so the neural reranker can judge
    # them. 0 = disabled (today's behavior).
    bm25_reserved_slots: int = field(
        default=0,
        metadata=spec(
            flat_alias="bm25_reserved_slots", reader="search/search_executor.py"
        ),
    )
    min_bm25_score: float = field(
        default=0.1,
        metadata=spec(flat_alias="min_bm25_score", reader="search/search_executor.py"),
    )

    # Reranking Configuration
    rrf_k_parameter: int = field(
        default=100,
        metadata=spec(
            flat_alias="rrf_k_parameter",
            reader="search/hybrid_searcher.py",
            construction_baked=True,
        ),
    )

    # Search Result Limits
    default_k: int = field(
        default=7,
        metadata=spec(
            range=(1, 50),
            flat_alias="default_k",
            env="CLAUDE_DEFAULT_K",
            reader="mcp_server/tools/search_handlers.py",
        ),
    )  # SSCG MRR +0.093, R@7 +0.122 vs 4 (commit 447dc9a); aligned with
    # find_similar_code's default (commit 730f67c)
    max_k: int = field(
        default=50,
        metadata=spec(
            flat_alias="max_k",
            env="CLAUDE_MAX_K",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )

    # Context budget (0 = unlimited)
    default_max_context_tokens: int = field(
        default=0,
        metadata=spec(reader="mcp_server/tools/search_orchestrator.py"),
    )


@dataclass
class PerformanceConfig:
    """GPU, parallelism, caching settings (16 fields)."""

    use_parallel_search: bool = field(
        default=True,
        metadata=spec(
            flat_alias="use_parallel_search",
            env="CLAUDE_USE_PARALLEL",
            mcp="performance_search",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )
    # Read once at HybridSearcher construction (ThreadPoolExecutor max_workers);
    # not in index_probe.py's FORBIDDEN_AUTO_TUNE_KEYS — covered by neither
    # guardrail today, same gap as bm25_use_stemming above.
    max_parallel_workers: int = field(
        default=2,
        metadata=spec(
            flat_alias="max_parallel_workers",
            reader="search/hybrid_searcher.py",
            construction_baked=True,
        ),
    )

    # Parallel Chunking Configuration
    enable_parallel_chunking: bool = field(
        default=True,  # Enable parallel file chunking
        metadata=spec(
            flat_alias="enable_parallel_chunking",
            env="CLAUDE_ENABLE_PARALLEL_CHUNKING",
            reader="search/incremental_indexer.py",
        ),
    )
    max_chunking_workers: int = field(
        default=8,  # ThreadPoolExecutor workers for chunking
        metadata=spec(
            flat_alias="max_chunking_workers",
            env="CLAUDE_MAX_CHUNKING_WORKERS",
            reader="search/incremental_indexer.py",
        ),
    )
    enable_entity_tracking: bool = field(
        default=True,  # Enable P4-5 entity extractors (enums, defaults, context managers)
        metadata=spec(
            flat_alias="enable_entity_tracking",
            env="CLAUDE_ENABLE_ENTITY_TRACKING",
            reader="chunking/multi_language_chunker.py",
        ),
    )

    # GPU Configuration
    # Gates dynamic embedding-batch-size calculation only (embed_chunks());
    # does NOT select the compute device. CUDA is used whenever available
    # regardless of this flag — disabling it falls back to the fixed
    # embedding.batch_size, not to CPU.
    prefer_gpu: bool = field(
        default=True,
        metadata=spec(
            flat_alias="prefer_gpu",
            env="CLAUDE_PREFER_GPU",
            reader="embeddings/embedder.py",
        ),
    )
    vram_limit_fraction: float = field(
        default=0.80,  # Hard VRAM ceiling (80% of dedicated)
        metadata=spec(reader="embeddings/embedder.py"),
    )
    allow_ram_fallback: bool = field(
        default=True,  # Allow spillover to system RAM (slower but reliable); indexing
        # overrides this locally via temporary_ram_fallback_off()
        metadata=spec(
            flat_alias="allow_shared_memory", reader="embeddings/embedder.py"
        ),
    )

    # Precision Configuration (fp16/bf16 for faster inference)
    enable_fp16: bool = field(
        default=True,  # Enable fp16 for GPU (30-50% faster inference)
        metadata=spec(
            flat_alias="enable_fp16",
            env="CLAUDE_ENABLE_FP16",
            reader="embeddings/model_loader.py",
        ),
    )
    prefer_bf16: bool = field(
        default=True,  # Prefer bf16 on Ampere+ GPUs (better accuracy than fp16)
        metadata=spec(
            flat_alias="prefer_bf16",
            env="CLAUDE_PREFER_BF16",
            reader="embeddings/model_loader.py",
        ),
    )

    # Dynamic Batch Sizing (GPU-based optimization)
    enable_dynamic_batch_size: bool = field(
        default=True,  # Enable GPU-based auto-sizing
        metadata=spec(
            flat_alias="enable_dynamic_batch_size",
            env="CLAUDE_DYNAMIC_BATCH_ENABLED",
            reader="embeddings/embedder.py",
        ),
    )
    dynamic_batch_min: int = field(
        default=16,  # Minimum batch size (lowered for fragmentation headroom)
        metadata=spec(
            flat_alias="dynamic_batch_min",
            env="CLAUDE_DYNAMIC_BATCH_MIN",
            reader="embeddings/embedder.py",
        ),
    )
    dynamic_batch_max: int = field(
        default=64,  # Maximum batch size (safer for 8-16GB GPUs)
        metadata=spec(
            flat_alias="dynamic_batch_max",
            env="CLAUDE_DYNAMIC_BATCH_MAX",
            reader="embeddings/embedder.py",
        ),
    )

    # Auto-reindexing
    enable_auto_reindex: bool = field(
        default=True,
        metadata=spec(
            flat_alias="enable_auto_reindex",
            env="CLAUDE_AUTO_REINDEX",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )
    max_index_age_minutes: float = field(
        default=30.0,
        metadata=spec(
            flat_alias="max_index_age_minutes",
            env="CLAUDE_MAX_INDEX_AGE",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )

    # Per-project overrides layer (ADR-0014). Read from the GLOBAL config layer
    # only (an overrides file cannot re-enable itself). Env escape hatch:
    # CLAUDE_DISABLE_PROJECT_OVERRIDES.
    enable_project_overrides: bool = field(
        default=True,
        metadata=spec(reader="search/index_probe.py"),
    )


@dataclass
class MultiHopConfig:
    """Multi-hop search settings (6 fields)."""

    enabled: bool = field(
        default=True,
        metadata=spec(
            flat_alias="enable_multi_hop",
            env="CLAUDE_ENABLE_MULTI_HOP",
            reader="search/hybrid_searcher.py",
        ),
    )
    hop_count: int = field(
        default=2,
        metadata=spec(
            range=(1, 3),
            flat_alias="multi_hop_count",
            env="CLAUDE_MULTI_HOP_COUNT",
            reader="search/hybrid_searcher.py",
        ),
    )  # Number of expansion hops
    expansion: float = field(
        default=0.5,  # Expansion factor per hop (0.25 arm rejected 2026-08-02:
        # replicated recall losses H034/H067; 0.5 stays)
        metadata=spec(
            flat_alias="multi_hop_expansion",
            env="CLAUDE_MULTI_HOP_EXPANSION",
            reader="search/hybrid_searcher.py",
        ),
    )
    initial_k_multiplier: float = field(
        default=2.0,  # Multiplier for initial results (k * multiplier)
        metadata=spec(
            flat_alias="multi_hop_initial_k_multiplier",
            env="CLAUDE_MULTI_HOP_INITIAL_K_MULTIPLIER",
            reader="search/multi_hop_searcher.py",
        ),
    )
    multi_hop_mode: str = field(
        default="hybrid",  # "semantic" | "graph" | "hybrid"
        metadata=spec(
            flat_alias="multi_hop_mode", reader="search/multi_hop_searcher.py"
        ),
    )
    edge_weights: dict[str, float] | None = field(
        default=None,  # None = DEFAULT_EDGE_WEIGHTS
        metadata=spec(reader="search/hybrid_searcher.py"),
    )


@dataclass
class IntentConfig:
    """Intent classification settings (6 fields)."""

    enabled: bool = field(
        # Default on: ADR-0028 took this off pending a repair of the SIMILARITY-intent symbol
        # extractor (_extract_symbol_from_query), which was misfiring on trailing prose words
        # instead of the query's actual anchor symbol. ADR-0029 repaired the extractor and
        # re-gated it: on the same substrate, the find_similar redirect now beats the normal
        # ranked path on MRR for the 9 similarity queries without falling below the find_similar
        # ceiling on recall@20, on both the 63q and 133q golden datasets. See ADR-0029.
        default=True,  # Enable intent classification for query routing
        metadata=spec(
            flat_alias="intent_enabled",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )
    confidence_threshold: float = field(
        default=0.4,  # Minimum confidence for intent-specific routing
        metadata=spec(
            flat_alias="intent_confidence_threshold",
            reader="search/intent_classifier.py",
        ),
    )
    default_intent: str = field(
        default="HYBRID",  # Default intent when confidence is low
        metadata=spec(
            flat_alias="intent_default_intent", reader="search/intent_classifier.py"
        ),
    )
    log_classifications: bool = field(
        default=True,  # Log intent classification decisions
        metadata=spec(
            flat_alias="intent_log_classifications",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )
    semantic_enabled: bool = field(
        default=True,  # Enable semantic anchor-embedding scoring
        metadata=spec(
            flat_alias="intent_semantic_enabled",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )
    semantic_weight: float = field(
        default=0.3,  # Semantic score weight in ensemble (0.0-1.0)
        metadata=spec(
            flat_alias="intent_semantic_weight",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )


@dataclass
class RerankerConfig:
    """Neural reranker settings (12 fields)."""

    enabled: bool = field(
        default=True,  # Enabled by default (Quality First)
        metadata=spec(
            flat_alias="reranker_enabled",
            env="CLAUDE_RERANKER_ENABLED",
            mcp="reranker",
            reader="search/reranking_engine.py",
        ),
    )
    model_name: str = field(
        default="Alibaba-NLP/gte-reranker-modernbert-base",  # Cross-encoder reranker model
        metadata=spec(
            flat_alias="reranker_model_name",
            env="CLAUDE_RERANKER_MODEL",
            mcp="reranker",
            reader="search/reranking_engine.py",
        ),
    )
    top_k_candidates: int = field(
        default=30,  # Rerank top 30 from RRF (Q2 sweep 2026-07-26:
        # 30 vs 50 quality-neutral within ±0.025 on both golden sets, -32% latency;
        # listwise reranking saturates ≈30 candidates)
        metadata=spec(
            range=(5, 100),
            flat_alias="reranker_top_k_candidates",
            env="CLAUDE_RERANKER_TOP_K",
            mcp="reranker",
            reader="search/reranking_engine.py",
        ),
    )
    min_vram_gb: float = field(
        default=2.0,  # Auto-disable below this threshold (reranker uses ~1.5GB).
        # Bypassed entirely when performance.allow_ram_fallback=True — that
        # check short-circuits first in should_enable_neural_reranking().
        metadata=spec(
            flat_alias="reranker_min_vram_gb",
            env="CLAUDE_RERANKER_MIN_VRAM_GB",
            mcp="reranker_echo",
            reader="search/reranking_engine.py",
        ),
    )
    batch_size: int = field(
        default=16,  # NeuralReranker/GenerativeReranker inference batch size.
        # Ignored by JinaRerankerV3 (the deployed default), which batches
        # internally and never reads this field.
        metadata=spec(
            flat_alias="reranker_batch_size",
            env="CLAUDE_RERANKER_BATCH_SIZE",
            mcp="reranker_echo",
            reader="search/reranking_engine.py",
            construction_baked=True,
        ),
    )
    dedupe_split_blocks: bool = field(
        default=True,  # Collapse split_block fragments to one result before final truncation
        metadata=spec(
            flat_alias="reranker_dedupe_split_blocks",
            env="CLAUDE_RERANKER_DEDUPE_SPLIT_BLOCKS",
            reader="search/reranking_engine.py",
        ),
    )
    single_pass: bool = field(
        default=False,  # Q3: skip hop-1 and multi-hop-merge neural rerank
        # passes; run ONE listwise pass over the final merged pool (hop-1 + multi-hop
        # + ego expansion) at the tail of HybridSearcher.search(). Trade-off: multi-hop
        # expansion seeds degrade from neural-reranked to RRF-fusion order.
        metadata=spec(
            flat_alias="reranker_single_pass",
            env="CLAUDE_RERANKER_SINGLE_PASS",
            reader="search/search_executor.py",
        ),
    )
    instruction: str = field(
        default="",  # GenerativeReranker only. Empty means "use the
        # model's built-in code-retrieval default" (see GenerativeReranker docstring).
        metadata=spec(
            flat_alias="reranker_instruction",
            env="CLAUDE_RERANKER_INSTRUCTION",
            reader="search/reranking_engine.py",
            construction_baked=True,
        ),
    )
    doc_max_chars: int = field(
        default=4000,  # GenerativeReranker only (pointwise — cost scales
        # with batch_size, so it can afford a larger per-document budget).
        metadata=spec(
            flat_alias="reranker_doc_max_chars",
            env="CLAUDE_RERANKER_DOC_MAX_CHARS",
            reader="search/reranking_engine.py",
            construction_baked=True,
        ),
    )
    listwise_doc_max_chars: int = field(
        default=1000,  # JinaRerankerV3 only (listwise — ALL
        # candidates share one context window, so cost is O(n^2) in the packed
        # sequence length via attention activation memory — not context-window
        # occupancy). A 4-run SSCG sweep at 4000 measured peak_vram_reserved_gb
        # 27.66 on a 24GB card (WDDM shared-memory spill, no OOM raised — see
        # allow_ram_fallback), 42-45/96 queries stalling past 8s (max 354.9s),
        # and every quality metric flat-to-negative within the +/-0.02 MRR noise
        # floor vs this default. See docs/adr/0011-listwise-reranker-doc-cap.md.
        metadata=spec(
            flat_alias="reranker_listwise_doc_max_chars",
            env="CLAUDE_RERANKER_LISTWISE_DOC_MAX_CHARS",
            reader="search/reranking_engine.py",
            construction_baked=True,
        ),
    )
    listwise_dtype: str = field(
        default="auto",
        metadata=spec(
            choices=("auto", "fp32", "bf16", "fp16"),
            flat_alias="reranker_listwise_dtype",
            env="CLAUDE_RERANKER_LISTWISE_DTYPE",
            reader="search/reranking_engine.py",
            construction_baked=True,
        ),
    )  # JinaRerankerV3 only. Weight dtype for the
    # listwise reranker: "auto" (checkpoint default — bf16), "fp32", "bf16",
    # or "fp16". bf16 listwise scoring is run-to-run non-deterministic at
    # ranking boundaries (4-5 golden queries flip between identical SSCG
    # runs); "fp32" trades ~2x reranker VRAM (~2.4 GB for the 0.6B model)
    # for reproducible scores. Construction-baked like listwise_doc_max_chars:
    # _ensure_reranker() rebuilds only on model_name change, so a dtype-only
    # config change needs a searcher reset to take effect (the SSCG
    # benchmark's --reranker-dtype handles this via
    # _maybe_reset_for_construction_overrides).
    hop1_reserved_slots: int = field(
        default=6,  # Reserve up to N hop-1-ranked candidates into
        # the multi-hop rerank window (rerank_by_query) when hop-2 expansion pushes
        # them out via score-scale incomparability at the top_k_candidates cut
        # (hop-1 jina scores vs. raw cosine/0.0 expansion scores sorted together).
        # 6 chosen by A/B sweep (N=5,6,8,9,10 probed; N>=8 starts evicting other
        # golds' window slots as collateral damage; N=10 aggregate-regressed MRR
        # on the 96q set). N=6: MRR flat within +/-0.02 noise on 96q and 63q,
        # recall@20/recall@50/pool_hit_rate all positive on both, no latency cost.
        # 0 disables (byte-identical to pre-fix behaviour). See
        # docs/adr/0013-hop1-reserve-at-final-pool.md.
        metadata=spec(
            flat_alias="reranker_hop1_reserved_slots",
            env="CLAUDE_RERANKER_HOP1_RESERVED_SLOTS",
            reader="search/multi_hop_searcher.py",
        ),
    )


@dataclass
class OutputConfig:
    """MCP output formatting settings (4 fields)."""

    format: str = field(
        default="ultra",  # verbose, compact, ultra (default: ultra for 45-55% token reduction)
        metadata=spec(flat_alias="output_format", reader="mcp_server/server.py"),
    )
    source_order_output: bool = field(
        default=False,  # Emit results in relevance order (blended_score desc); set True to restore DOS-RAG file/line ordering
        metadata=spec(
            flat_alias="source_order_output",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )
    include_subgraph: bool = field(
        default=False,  # Serialize ego_graph subgraph_* blocks into the response
        metadata=spec(
            flat_alias="include_subgraph", reader="search/graph_scoring_stage.py"
        ),
    )
    include_result_graph: bool = field(
        default=False,  # Attach per-result `graph` dict to each result
        metadata=spec(
            flat_alias="include_result_graph",
            reader="mcp_server/tools/search_orchestrator.py",
        ),
    )


@dataclass
class ChunkingConfig:
    """Chunking algorithm settings (10 fields)."""

    # Large function splitting (cAST paper: AST-aware splitting improves Recall@5 +66%)
    enable_large_node_splitting: bool = field(
        default=True,  # Split functions > max_chunk_lines
        metadata=spec(
            flat_alias="enable_large_node_splitting",
            mcp="chunking",
            reader="chunking/languages/base.py",
        ),
    )
    max_chunk_lines: int = field(
        default=100,  # Maximum lines before AST block splitting
        metadata=spec(
            range=(10, 1000),
            flat_alias="max_chunk_lines",
            mcp="chunking",
            reader="chunking/languages/base.py",
        ),
    )

    # Splitting-specific configs (separate from merging)
    split_size_method: str = field(
        default="characters",
        metadata=spec(
            choices=("lines", "characters"),
            flat_alias="split_size_method",
            mcp="chunking",
            reader="chunking/languages/base.py",
        ),
    )  # "lines" or "characters"
    max_split_chars: int = field(
        default=3000,
        metadata=spec(
            range=(1000, 10000),
            flat_alias="max_split_chars",
            mcp="chunking",
            reader="chunking/languages/base.py",
        ),
    )  # Character-based splitting (~750 tokens, optimal for retrieval)

    # File-level module summaries (A2: improve GLOBAL query recall)
    enable_file_summaries: bool = field(
        default=True,  # Generate module-summary chunks per file
        metadata=spec(mcp="chunking", reader="search/incremental_indexer.py"),
    )

    # Adaptive chunk sizing (research: P75 baseline + complexity modulation)
    sizing_mode: str = field(
        default="adaptive",
        metadata=spec(
            choices=("fixed", "adaptive"),
            mcp="chunking",
            reader="chunking/languages/base.py",
        ),
    )  # "fixed" (static) or "adaptive" (repo-profiled)
    adaptive_multiplier_max: float = field(
        default=1.3,
        metadata=spec(
            range=(1.0, 2.0), mcp="chunking", reader="chunking/languages/base.py"
        ),
    )  # T_max = P75_baseline × this (low-complexity)
    adaptive_multiplier_min: float = field(
        default=0.5,
        metadata=spec(
            range=(0.1, 1.0), mcp="chunking", reader="chunking/languages/base.py"
        ),
    )  # T_min = P75_baseline × this (high-complexity)
    max_complexity_cap: int = field(
        default=30,
        metadata=spec(
            range=(5, 100), mcp="chunking", reader="chunking/languages/base.py"
        ),
    )  # Cv normalization ceiling (CC >= cap → Cv = 1.0)

    # GLSL call-graph extraction (Phase 2b): filter TouchDesigner's TD-prefixed
    # shader-include builtins (TDPanelSize, TDOutputSwizzle, ...) out of
    # metadata["calls"] alongside the always-on GLSL builtin/type-constructor
    # filter. Disable for non-TouchDesigner GLSL projects where a real
    # user-defined symbol might start with "TD".
    glsl_filter_td_prefix: bool = field(
        default=True,
        metadata=spec(mcp="chunking", reader="chunking/languages/glsl.py"),
    )


@dataclass
class EgoGraphConfig:
    """Ego-graph retrieval settings (RepoGraph ICLR 2025)."""

    enabled: bool = field(
        default=True,  # Enable ego-graph expansion
        metadata=spec(
            flat_alias="ego_graph_enabled", reader="search/hybrid_searcher.py"
        ),
    )
    k_hops: int = field(
        default=2,
        metadata=spec(
            range=(1, 3),
            flat_alias="ego_graph_k_hops",
            reader="search/ego_graph_retriever.py",
        ),
    )  # Number of hops (1=direct neighbors, 2=include second-degree)
    max_neighbors_per_hop: int = field(
        default=10,  # Max neighbors per hop
        metadata=spec(
            flat_alias="ego_graph_max_neighbors_per_hop",
            reader="search/ego_graph_retriever.py",
        ),
    )
    relation_types: list | None = field(
        default=None,  # Filter to specific relations (None = all)
        metadata=spec(
            flat_alias="ego_graph_relation_types",
            reader="search/ego_graph_retriever.py",
        ),
    )
    include_anchor: bool = field(
        default=True,  # Include original anchor nodes in results
        metadata=spec(
            flat_alias="ego_graph_include_anchor",
            reader="search/ego_graph_retriever.py",
        ),
    )
    deduplicate: bool = field(
        default=True,  # Remove duplicate chunk_ids
        metadata=spec(
            flat_alias="ego_graph_deduplicate", reader="search/ego_graph_retriever.py"
        ),
    )
    # RepoGraph relation filtering (Feature #5)
    exclude_stdlib_imports: bool = field(
        default=True,  # Filter stdlib from graph traversal
        metadata=spec(reader="search/ego_graph_retriever.py"),
    )
    exclude_third_party_imports: bool = field(
        default=True,  # Filter third-party from traversal
        metadata=spec(reader="search/ego_graph_retriever.py"),
    )
    # Weighted graph traversal
    edge_weights: dict[str, float] | None = field(
        default_factory=lambda: DEFAULT_EDGE_WEIGHTS.copy(),
        metadata=spec(reader="search/ego_graph_retriever.py"),
    )  # Use weighted BFS by default (calls > imports priority)
    # QW3: expansion mode — "bfs" (default) or "ppr" (Personalized PageRank)
    expansion_mode: str = field(
        default="bfs",
        metadata=spec(choices=("bfs", "ppr"), reader="search/ego_graph_retriever.py"),
    )  # "bfs" = k-hop BFS, "ppr" = Personalized PageRank
    ppr_alpha: float = field(
        default=0.85,  # PPR damping factor (standard default)
        metadata=spec(reader="search/ego_graph_retriever.py"),
    )
    # QW5: minimum cosine similarity threshold for ego-graph neighbor filtering
    min_similarity_threshold: float = field(
        default=0.15,  # Neighbors below this are filtered out
        metadata=spec(reader="search/ego_graph_retriever.py"),
    )


@dataclass
class ParentRetrievalConfig:
    """Parent chunk retrieval settings for Match Small, Retrieve Big."""

    enabled: bool = field(
        default=False,  # Disabled — parents get score=0, no ranking value
        metadata=spec(reader="search/hybrid_searcher.py"),
    )
    include_parent_content: bool = field(
        default=True,  # Include parent's full content
        metadata=spec(reader="search/hybrid_searcher.py"),
    )


@dataclass
class GraphEnhancedConfig:
    """Graph-enhanced search settings."""

    centrality_method: str = field(
        default="pagerank",  # Centrality algorithm
        metadata=spec(
            flat_alias="centrality_method", reader="search/graph_scoring_stage.py"
        ),
    )
    # Blending weight (0=semantic, 1=centrality). 0.0 per 2026-07-26 SSCG sweep:
    # recall falls monotonically with alpha on both golden sets (replicated
    # R@5 -0.027 at 0.2, -0.038 at 0.3 vs 0.0) with no MRR gain; the
    # query-aware boost suite in CentralityRanker.rerank() stays active.
    centrality_alpha: float = field(
        default=0.0,
        metadata=spec(
            flat_alias="centrality_alpha", reader="search/graph_scoring_stage.py"
        ),
    )
    centrality_annotation: bool = field(
        default=True,  # Always annotate centrality when graph exists
        metadata=spec(
            flat_alias="centrality_annotation", reader="search/graph_scoring_stage.py"
        ),
    )
    centrality_reranking: bool = field(
        default=True,  # Always rerank by blended score
        metadata=spec(
            flat_alias="centrality_reranking", reader="search/graph_scoring_stage.py"
        ),
    )
    # Chunk-size normalization (penalize oversized chunks)
    enable_size_normalization: bool = field(
        default=True,  # Enable logarithmic size penalty
        metadata=spec(
            flat_alias="enable_size_normalization", reader="search/centrality_ranker.py"
        ),
    )
    size_norm_target_lines: int = field(
        default=200,  # Target chunk size (no penalty below this)
        metadata=spec(
            flat_alias="size_norm_target_lines", reader="search/centrality_ranker.py"
        ),
    )
    size_norm_alpha: float = field(
        default=0.1,  # Penalty strength (higher = stronger penalty)
        metadata=spec(
            flat_alias="size_norm_alpha", reader="search/centrality_ranker.py"
        ),
    )
    # Centrality-adaptive BM25 boost (LIMIT paper insight)
    # High-centrality chunks (utility functions, base classes) are exactly where
    # single-vector embeddings fail. Extra boost compensates for this limitation.
    centrality_bm25_boost: bool = field(
        default=True,  # Enable adaptive boost for high-centrality results
        metadata=spec(
            flat_alias="centrality_bm25_boost", reader="search/centrality_ranker.py"
        ),
    )
    centrality_boost_threshold: float = field(
        default=0.02,  # Centrality score threshold to trigger boost
        metadata=spec(
            flat_alias="centrality_boost_threshold",
            reader="search/centrality_ranker.py",
        ),
    )
    centrality_boost_factor: float = field(
        default=5.0,  # Multiplier: boost = centrality * factor
        metadata=spec(
            flat_alias="centrality_boost_factor", reader="search/centrality_ranker.py"
        ),
    )
    centrality_boost_cap: float = field(
        default=0.15,  # Maximum boost added to blended_score
        metadata=spec(
            flat_alias="centrality_boost_cap", reader="search/centrality_ranker.py"
        ),
    )
    # Post-centrality result cap: total results kept = k * this multiplier
    # (k primary + (multiplier-1)*k graph/ego/parent context chunks)
    max_results_multiplier: int = field(
        default=8,
        metadata=spec(
            flat_alias="max_results_multiplier", reader="search/graph_scoring_stage.py"
        ),
    )


@dataclass
class ObservabilityConfig:
    """OTel tracing configuration (traces-only v1; metrics deferred to v2)."""

    enabled: bool = field(
        default=False,
        metadata=spec(
            flat_alias="otel_enabled",
            env="CLAUDE_OTEL_ENABLED",
            reader="utils/observability.py",
        ),
    )
    service_name: str = field(
        default="claude-context-local",
        metadata=spec(
            flat_alias="otel_service_name",
            reader="utils/observability.py",
        ),
    )
    exporter: str = field(
        default="otlp",
        metadata=spec(
            choices=("otlp", "console", "none"),
            flat_alias="otel_exporter",
            env="CLAUDE_OTEL_EXPORTER",
            reader="utils/observability.py",
        ),
    )  # otlp | console(->stderr) | none
    otlp_endpoint: str = field(
        default="http://localhost:4318",
        metadata=spec(
            flat_alias="otel_endpoint",
            env="CLAUDE_OTEL_ENDPOINT",
            reader="utils/observability.py",
        ),
    )
    sample_ratio: float = field(
        default=1.0,
        metadata=spec(
            flat_alias="otel_sample_ratio",
            env="CLAUDE_OTEL_SAMPLE",
            reader="utils/observability.py",
        ),
    )
    capture_query_text: bool = field(
        default=False,
        metadata=spec(
            flat_alias="otel_capture_query_text",
            env="CLAUDE_OTEL_CAPTURE_QUERY",
            reader="search/hybrid_searcher.py",
        ),
    )  # off by default (query text can be sensitive)


@dataclass
class QueryExpansionConfig:
    """Curated-vocabulary query expansion settings (6 fields).

    When enabled, queries whose lowercased text contains a concept trigger
    from ``config/query_expansion_variants.yaml`` gain extra discounted
    fusion legs built from that concept's code-domain terms (see
    ``search/query_expansion.py``). Bridges zero-identifier English
    paraphrases ("survive a restart") to the identifiers code actually
    uses ("save", "persist", "disk"). Unmatched or disabled queries take
    exactly the unexpanded two-leg fusion path.
    """

    enabled: bool = field(
        default=False,
        metadata=spec(
            flat_alias="query_expansion_enabled",
            reader="search/search_executor.py",
        ),
    )  # Opt-in pending A/B (flip on pass, BM25-only)
    variants_path: str = field(
        default="",  # Empty = package default config/query_expansion_variants.yaml
        metadata=spec(
            flat_alias="query_expansion_variants_path",
            reader="search/search_executor.py",
        ),
    )
    max_variants: int = field(
        default=2,
        metadata=spec(
            flat_alias="query_expansion_max_variants",
            reader="search/search_executor.py",
        ),
    )  # Max matched concepts per query (deterministic order)
    variant_weight_discount: float = field(
        default=0.5,
        metadata=spec(
            flat_alias="query_expansion_weight_discount",
            reader="search/search_executor.py",
        ),
    )  # Variant-leg weight = base leg weight * this
    apply_to_bm25: bool = field(
        default=True,
        metadata=spec(
            flat_alias="query_expansion_apply_to_bm25",
            reader="search/search_executor.py",
        ),
    )  # Add expanded-query BM25 leg(s)
    apply_to_dense: bool = field(
        default=False,
        metadata=spec(
            flat_alias="query_expansion_apply_to_dense",
            reader="search/search_executor.py",
        ),
    )  # Add expanded-query dense leg(s) — needs its own A/B


@dataclass
class CallGraphConfig:
    """Call-graph resolver pipeline settings (6 fields).

    Controls which static-analysis backends run at full-index time to inject
    cross-module ``calls`` edges into the code graph.

    ``resolvers`` below governs Stages 1-2 only. Names map to concrete classes
    in the ``chunking/relationships/`` package; only resolvers that are also
    *available* (i.e. their optional dependency is installed) are executed::

        "pyan"   → PyanResolver   (pyan3>=2.6.0, optional extra [callgraph])
        "libcst" → LibCSTResolver (libcst>=1.8.6, optional extra [callgraph])

    Stage 3 (LSP/basedpyright) is governed **solely** by ``lsp_enabled``
    below — it is not a ``resolvers`` entry, and ``resolvers: []`` does not
    disable it. Any name in ``resolvers`` other than ``"pyan"``/``"libcst"``
    is silently ignored (``search/call_edge_injection.py``).

    The ``"ast"`` entry is a documentation placeholder — in-house AST edges are
    produced during chunking and are already in the graph before the injection
    seam runs.
    """

    resolvers: list[str] | None = field(
        default=None,
        metadata=spec(reader="search/call_edge_injection.py"),
    )
    """Resolver names to attempt in the injection pipeline.

    Default: ``["pyan", "libcst"]`` (both in the ``[callgraph]`` extra).
    Set to ``["pyan"]`` to disable LibCST (Stage 2), ``[]`` to skip both.
    Does **not** affect the LSP resolver (Stage 3) — see ``lsp_enabled``.
    """

    lsp_enabled: bool = field(
        default=True,
        metadata=spec(reader="search/call_edge_injection.py"),
    )
    """Enable the basedpyright LSP resolver (Stage 3).

    Requested by default; no-ops unless the ``[lsp]`` extra is installed:
    ``pip install -e ".[lsp]"``. Adds basedpyright as the highest-accuracy
    resolver (confidence 0.98) but is the slowest and requires a
    full-type-check pass.
    """

    lsp_timeout_seconds: float = field(
        default=30.0,
        metadata=spec(reader="search/call_edge_injection.py"),
    )
    """Per-request timeout for LSP JSON-RPC calls (seconds).

    Increase for large codebases where basedpyright type-checking takes longer.
    """

    lsp_total_timeout_seconds: float = field(
        default=180.0,
        metadata=spec(reader="search/call_edge_injection.py"),
    )
    """Aggregate wall-clock budget for the *entire* LSP pass (seconds).

    Unlike ``lsp_timeout_seconds`` (per JSON-RPC request), this bounds the
    whole ``resolve()`` call across all files. If exceeded, the basedpyright
    subprocess is force-killed and edges collected so far are returned —
    partial LSP results are safe because LSP only *upgrades confidence* on
    edges the pyan/libcst resolvers already produced.
    """

    use_pyproject_toml: bool = field(
        default=False,
        metadata=spec(reader="search/call_edge_injection.py"),
    )
    """Derive LibCST FQNs from the nearest ``pyproject.toml`` package root.

    Enable for *src-layout* projects (``src/mypkg/mod.py``) where the project
    root is *not* the Python package root.  With the default ``False``, LibCST
    computes FQNs relative to the repo root (``src.mypkg.mod``), which will
    fail to match graph chunk IDs.  Setting this to ``True`` makes LibCST look
    for the nearest ``pyproject.toml`` and strips the ``src/`` prefix so FQNs
    resolve correctly (``mypkg.mod``).

    Has no effect when ``"libcst"`` is not in ``resolvers``.
    """

    min_confidence: float = field(
        default=0.65,
        metadata=spec(reader="search/call_edge_injection.py"),
    )
    """Minimum resolver confidence required to inject an edge (inclusive floor).

    Edges from ``run_resolvers()`` whose ``confidence`` is strictly below this
    threshold are discarded before injection.  The default ``0.65`` drops
    wildcard-fan-out pyan edges (0.6) while keeping whole-project pyan (0.75)
    and higher-confidence resolvers.

    Reference confidence tiers:
    - ``0.5`` / ``0.7`` — in-house AST (single-file, already in graph)
    - ``0.6``           — pyan expand_unknowns wildcard fan-out
    - ``0.75``          — pyan whole-project name resolution
    - ``0.90``          — LibCST FQN cross-module resolution
    - ``0.98``          — LSP / basedpyright type-level resolution

    Example: set ``0.75`` to drop wildcard-fan-out pyan edges; set ``0.90``
    to keep only LibCST and LSP edges.
    """

    def __post_init__(self) -> None:
        if self.resolvers is None:
            self.resolvers = ["pyan", "libcst"]


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


def _dotted_keys(nested: dict[str, Any], _prefix: str = "") -> list[str]:
    """Flatten a nested dict to sorted dotted leaf-key paths.

    ``{"performance": {"max_chunking_workers": 12}}`` →
    ``["performance.max_chunking_workers"]``.  Used for override provenance.
    """
    keys: list[str] = []
    for key, value in nested.items():
        path = f"{_prefix}{key}"
        if isinstance(value, dict) and value:
            keys.extend(_dotted_keys(value, f"{path}."))
        else:
            keys.append(path)
    return sorted(keys)


def validate_field_value(spec_cls: type, field_name: str, value: Any) -> str | None:
    """Return an error message if *value* violates *spec_cls*'s field metadata, else None.

    Reads ``{"range": (lo, hi)}`` (inclusive numeric bounds) or ``{"choices": (...)}``
    (allowed string values) from :func:`dataclasses.fields` metadata.  Fields with no
    matching metadata key are accepted unconditionally.

    *spec_cls* is the **real** dataclass type (e.g. ``ChunkingConfig``) — never pass
    ``type(mock_instance)`` or the function will not find the spec.
    """
    for f in dataclasses.fields(spec_cls):
        if f.name != field_name:
            continue
        spec = f.metadata
        if "range" in spec:
            lo, hi = spec["range"]
            if not (lo <= value <= hi):
                return f"Invalid {field_name}: {value}. Must be between {lo} and {hi}"
        if "choices" in spec and value not in spec["choices"]:
            return (
                f"Invalid {field_name}: {value}. Must be one of {list(spec['choices'])}"
            )
        return None  # found the field — spec passes (or no relevant key)
    return None  # unknown field — no spec to enforce


def _derive_flat_key_aliases(
    subconfig_types: dict[str, type],
) -> dict[str, tuple[str, str]]:
    """Derive the legacy-flat-key alias map from each field's ``spec(flat_alias=...)``.

    Single declaration site per ADR-0022: a field states its own alias (or
    leaves it unset), rather than restating that decision in a second
    hand-maintained table.
    """
    aliases: dict[str, tuple[str, str]] = {}
    for section_name, section_cls in subconfig_types.items():
        for f in dataclasses.fields(section_cls):
            alias = f.metadata.get("flat_alias")
            if alias is not None:
                aliases[alias] = (section_name, f.name)
    return aliases


def _derive_env_mapping(
    subconfig_types: dict[str, type],
    bool_converter: Callable[[str], bool],
) -> dict[str, tuple[str, Callable[[str], Any]]]:
    """Derive the ``CLAUDE_*`` env-var mapping from each field's ``spec(env=...)``.

    The converter is inferred from the field's declared type — ``bool`` uses
    the tolerant *bool_converter* (``bool("false")`` is truthy, so the raw
    type is never usable directly); ``str``/``int``/``float`` use the type
    itself. Every env-settable field is also flat-aliased (asserted by
    ``test_search_config.py``), so ``flat_alias`` doubles as the dict key the
    validation path looks up in ``_FLAT_KEY_ALIASES``. See ADR-0022.
    """
    type_converters: dict[type, Callable[[str], Any]] = {
        str: str,
        int: int,
        float: float,
        bool: bool_converter,
    }
    mapping: dict[str, tuple[str, Callable[[str], Any]]] = {}
    for section_cls in subconfig_types.values():
        for f in dataclasses.fields(section_cls):
            env_var = f.metadata.get("env")
            if env_var is None:
                continue
            mapping[env_var] = (
                f.metadata["flat_alias"],
                type_converters[cast(type, f.type)],
            )
    return mapping


def _derive_mcp_field_names(section_cls: type, *mcp_tags: str) -> tuple[str, ...]:
    """Field names (declaration order) whose ``spec(mcp=...)`` is one of *mcp_tags*.

    Derives the MCP config handlers' per-tool field maps (e.g. ``configure_chunking``'s
    settable fields, ``configure_reranker``'s settable + read-only echo fields) from the
    same spec table instead of a hand-maintained tuple. See ADR-0022.
    """
    return tuple(
        f.name
        for f in dataclasses.fields(section_cls)
        if f.metadata.get("mcp") in mcp_tags
    )


def _derive_construction_baked_fields(
    subconfig_types: dict[str, type],
) -> frozenset[tuple[str, str]]:
    """Derive the set of (section_name, field_name) pairs baked into a
    collaborator at construction time from each field's ``spec(construction_baked=True)``.

    Single declaration site per ADR-0022: a field states its own liveness
    (read fresh every call vs. baked into e.g. a cached ``HybridSearcher``/
    reranker at construction), rather than restating that domain knowledge in
    a hand-written six-argument None-check (the original
    ``_maybe_reset_for_construction_overrides`` in
    ``scripts/benchmark/run_sscg_benchmark.py``). Used by
    ``evaluation/arm_overrides.py``'s ``requires_rebuild`` to decide whether
    an A/B arm's override needs a fresh searcher instead of a live mutation.
    """
    baked: set[tuple[str, str]] = set()
    for section_name, section_cls in subconfig_types.items():
        for f in dataclasses.fields(section_cls):
            if f.metadata.get("construction_baked"):
                baked.add((section_name, f.name))
    return frozenset(baked)


class SearchConfig:
    """Root configuration with nested sub-configs.

    Split into focused sub-configs for organization; see ``_SUBCONFIG_FIELDS``
    below for the current, single-source-of-truth list of section names (this
    docstring used to hand-duplicate that list and had drifted to 8 of 14
    sections before being replaced by this pointer -- see ADR-0022).

    Initialization style (nested configs only):
        config = SearchConfig(embedding=EmbeddingConfig(model_name="..."))
    """

    def __init__(
        self,
        embedding: EmbeddingConfig | None = None,
        search_mode: SearchModeConfig | None = None,
        performance: PerformanceConfig | None = None,
        multi_hop: MultiHopConfig | None = None,
        intent: IntentConfig | None = None,
        reranker: RerankerConfig | None = None,
        output: OutputConfig | None = None,
        chunking: ChunkingConfig | None = None,
        ego_graph: EgoGraphConfig | None = None,
        parent_retrieval: ParentRetrievalConfig | None = None,
        graph_enhanced: GraphEnhancedConfig | None = None,
        observability: ObservabilityConfig | None = None,
        call_graph: CallGraphConfig | None = None,
        query_expansion: QueryExpansionConfig | None = None,
    ):
        """Initialize SearchConfig with nested sub-configs.

        Args:
            embedding: EmbeddingConfig instance (optional, defaults to EmbeddingConfig())
            search_mode: SearchModeConfig instance (optional, defaults to SearchModeConfig())
            performance: PerformanceConfig instance (optional, defaults to PerformanceConfig())
            multi_hop: MultiHopConfig instance (optional, defaults to MultiHopConfig())
            intent: IntentConfig instance (optional, defaults to IntentConfig())
            reranker: RerankerConfig instance (optional, defaults to RerankerConfig())
            output: OutputConfig instance (optional, defaults to OutputConfig())
            chunking: ChunkingConfig instance (optional, defaults to ChunkingConfig())
            ego_graph: EgoGraphConfig instance (optional, defaults to EgoGraphConfig())
            parent_retrieval: ParentRetrievalConfig instance (optional, defaults to ParentRetrievalConfig())
            graph_enhanced: GraphEnhancedConfig instance (optional, defaults to GraphEnhancedConfig())
            observability: ObservabilityConfig instance (optional, defaults to ObservabilityConfig())
            call_graph: CallGraphConfig instance (optional, defaults to CallGraphConfig())
            query_expansion: QueryExpansionConfig instance (optional, defaults to QueryExpansionConfig())
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
        self.call_graph = call_graph if call_graph is not None else CallGraphConfig()
        self.query_expansion = (
            query_expansion if query_expansion is not None else QueryExpansionConfig()
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
        "intent",
        "reranker",
        "output",
        "chunking",
        "ego_graph",
        "parent_retrieval",
        "graph_enhanced",
        "observability",
        "call_graph",
        "query_expansion",
    )

    # frozenset for O(1) membership tests in _flat_to_nested / is_nested checks
    _SUBCONFIG_NAMES: frozenset[str] = frozenset(_SUBCONFIG_FIELDS)

    _SUBCONFIG_TYPES: dict[str, type] = {
        "embedding": EmbeddingConfig,
        "search_mode": SearchModeConfig,
        "performance": PerformanceConfig,
        "multi_hop": MultiHopConfig,
        "intent": IntentConfig,
        "reranker": RerankerConfig,
        "output": OutputConfig,
        "chunking": ChunkingConfig,
        "ego_graph": EgoGraphConfig,
        "parent_retrieval": ParentRetrievalConfig,
        "graph_enhanced": GraphEnhancedConfig,
        "observability": ObservabilityConfig,
        "call_graph": CallGraphConfig,
        "query_expansion": QueryExpansionConfig,
    }

    # Maps legacy flat config keys (and env-var flat keys) to
    # (sub_config_name, field_name) in the nested schema.
    # Used by _flat_to_nested() and by SearchConfigManager.load_config()
    # to translate env overrides into the nested structure before merging.
    #
    # Derived from each field's spec(flat_alias=...) — see ADR-0022. The
    # backward-compat shim ("allow_shared_memory" -> performance.allow_ram_fallback)
    # is declared the same way, as PerformanceConfig.allow_ram_fallback's alias.
    _FLAT_KEY_ALIASES: dict[str, tuple[str, str]] = _derive_flat_key_aliases(
        _SUBCONFIG_TYPES
    )

    # (section_name, field_name) pairs baked into a collaborator (cached
    # HybridSearcher / reranker) at construction time rather than read live
    # per search call — mutating one on the config singleton is a no-op until
    # that collaborator is rebuilt. Derived from each field's
    # spec(construction_baked=True) — see ADR-0022 and
    # evaluation/arm_overrides.py's requires_rebuild().
    _CONSTRUCTION_BAKED_FIELDS: frozenset[tuple[str, str]] = (
        _derive_construction_baked_fields(_SUBCONFIG_TYPES)
    )

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
        # (path, mtime) of the applied per-project overrides file — part of the
        # hot-reload cache key so project switches and hand-edits invalidate.
        self._overrides_key: tuple[str, float] | None = None
        self._active_overrides_meta: dict[str, Any] | None = None
        # Guards the reload body in load_config() (#reindex-log-audit-2026-07-30):
        # a cache-key change (e.g. index_probe rewriting search_overrides.json)
        # can be observed by every ThreadPoolExecutor worker in the same instant,
        # and without a lock each one redundantly re-parses and re-merges the
        # config. RLock because get_active_overrides_meta() re-enters load_config().
        self._lock = threading.RLock()

    def _resolve_overrides_path(self) -> Path | None:
        """Path to the active project's search_overrides.json, or None.

        None when no active project storage dir is set, the file does not
        exist, or ``CLAUDE_DISABLE_PROJECT_OVERRIDES`` is truthy (escape hatch
        checked before anything else).
        """
        if self._bool_from_env(os.environ.get("CLAUDE_DISABLE_PROJECT_OVERRIDES", "")):
            return None
        storage_dir = get_active_project_storage_dir()
        if not storage_dir:
            return None
        path = Path(storage_dir) / PROJECT_OVERRIDES_FILENAME
        return path if path.exists() else None

    def get_active_overrides_meta(self) -> dict[str, Any] | None:
        """Provenance of the applied per-project overrides, or None if inactive.

        Keys: ``path``, ``probe_version``, ``generated_at``, ``keys`` (sorted
        dotted config keys).  Forces a (cached) load so the answer is current.
        """
        self.load_config()
        return self._active_overrides_meta

    def _get_default_config_path(self) -> str:
        """Get default config file path (delegates to shared config_paths module)."""
        return resolve_config_path()

    def load_config(self) -> SearchConfig:
        """Load configuration from file and environment variables."""
        # Check if file changed since last load.
        # stat() is called on every load_config() invocation to support hot-reload
        # without a file-watcher thread (#61). A single stat() is ~1 µs — cheaper than
        # any alternative that avoids it entirely — so this is intentional, not a
        # performance concern. The cache hit-path (mtime unchanged) returns immediately.
        current_mtime = None
        _config_path = Path(self.config_file)
        # search_config.json is a gitignored, machine-local file (see .gitignore /
        # search_config.json.example). When it hasn't been created yet, fall back to
        # the committed template so shared defaults still apply -- read-only: this
        # branch never affects save_config(), which always writes self.config_file.
        _read_path = _config_path
        if not _config_path.exists():
            _example_path = _config_path.with_name(_config_path.name + ".example")
            if _example_path.exists():
                _read_path = _example_path
        if _read_path.exists():
            current_mtime = _read_path.stat().st_mtime

        # Per-project overrides file (ADR-0014) participates in the cache key:
        # switching projects or hand-editing the file must trigger a reload.
        override_path = self._resolve_overrides_path()
        overrides_key: tuple[str, float] | None = None
        if override_path is not None:
            try:
                overrides_key = (str(override_path), override_path.stat().st_mtime)
            except OSError:
                override_path = None

        # Double-checked locking: cheap outer test avoids the lock on the hot
        # path (#reindex-log-audit-2026-07-30). Only a cache-key change (config
        # file edit, or index_probe rewriting search_overrides.json) reaches the
        # lock below — otherwise every ThreadPoolExecutor worker racing a cache
        # miss (e.g. ParallelChunker calling get_chunking_config() per file)
        # would redundantly re-parse and re-merge the config in lockstep.
        if (
            self._config is not None
            and current_mtime == self._config_mtime
            and overrides_key == self._overrides_key
        ):
            return self._config

        with self._lock:
            # Re-check inside the lock: another thread may have already
            # completed the reload while we were waiting to acquire it.
            if (
                self._config is not None
                and current_mtime == self._config_mtime
                and overrides_key == self._overrides_key
            ):
                return self._config

            # Start with defaults
            config_dict: dict[str, Any] = {}

            # Load from file if exists
            if _read_path.exists():
                try:
                    with open(_read_path) as f:
                        raw = json.load(f)
                    self.logger.info(f"Loaded search config from {_read_path}")
                    # Normalise to nested format so env overrides can be deep-merged
                    # without mixing flat and nested keys in a single dict.
                    file_is_nested = any(
                        isinstance(v, dict) and k in SearchConfig._SUBCONFIG_NAMES
                        for k, v in raw.items()
                    )
                    config_dict = (
                        raw if file_is_nested else SearchConfig._flat_to_nested(raw)
                    )
                except Exception as e:  # noqa: BLE001 - parse-recovery: malformed config file, fall back to defaults
                    self.logger.warning(f"Failed to load config file {_read_path}: {e}")

            # Per-project overrides (ADR-0014): deep-merged over the global file so
            # probe results apply only to the active project.  Env vars are merged
            # last (below) and therefore still win — the human-in-the-loop escape.
            # The enable flag is read from the GLOBAL layer only, so an overrides
            # file can never re-enable itself.
            self._active_overrides_meta = None
            if override_path is not None and config_dict.get("performance", {}).get(
                "enable_project_overrides", True
            ):
                try:
                    with open(override_path) as f:
                        raw_overrides = json.load(f)
                    overrides = raw_overrides.get("overrides") or {}
                    if not isinstance(overrides, dict):
                        raise TypeError("'overrides' must be a JSON object")
                    _deep_merge(config_dict, overrides)
                    self._active_overrides_meta = {
                        "path": str(override_path),
                        "probe_version": raw_overrides.get("probe_version"),
                        "generated_at": raw_overrides.get("generated_at"),
                        "keys": _dotted_keys(overrides),
                    }
                    self.logger.info(
                        f"Applied project overrides from {override_path}: "
                        f"{', '.join(self._active_overrides_meta['keys']) or '(none)'}"
                    )
                except Exception as e:  # noqa: BLE001 - parse-recovery: malformed overrides file, skip the layer
                    self.logger.warning(
                        f"Failed to load project overrides {override_path}: {e}"
                    )

            # Translate env-var flat keys to nested and deep-merge so they apply over
            # a nested config file (previously the update() call was a no-op for nested
            # files because the flat env keys were never read by the nested branch).
            env_overrides = self._load_from_environment()
            env_nested = SearchConfig._flat_to_nested(env_overrides)
            _deep_merge(config_dict, env_nested)

            # Create config object
            self._config = SearchConfig.from_dict(config_dict)

            # Store mtimes after loading
            self._config_mtime = current_mtime
            self._overrides_key = overrides_key

            self.logger.info(
                f"Search mode: {self._config.search_mode.default_mode}, "
                f"hybrid enabled: {self._config.search_mode.enable_hybrid}"
            )

            return self._config

    def _load_from_environment(self) -> dict[str, Any]:
        """Load configuration from environment variables."""
        # Derived from each field's spec(env=...) — see ADR-0022.
        env_mapping = _derive_env_mapping(
            SearchConfig._SUBCONFIG_TYPES, self._bool_from_env
        )

        config_dict: dict[str, Any] = {}
        for env_var, (config_key, converter) in env_mapping.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    converted = converter(env_value)
                except ValueError as e:
                    self.logger.warning(
                        f"Invalid value for {env_var}: {env_value} ({e})"
                    )
                    continue

                # Validate against the same field metadata the MCP config handlers
                # use (validate_field_value), so an env override can't smuggle in a
                # value the file-based path would never persist. Warn-and-skip,
                # matching the ValueError handling above.
                alias = SearchConfig._FLAT_KEY_ALIASES.get(config_key)
                if alias is not None:
                    section, field_name = alias
                    spec_cls = SearchConfig._SUBCONFIG_TYPES[section]
                    err = validate_field_value(spec_cls, field_name, converted)
                    if err:
                        self.logger.warning(f"Invalid value for {env_var}: {err}")
                        continue

                config_dict[config_key] = converted
                self.logger.debug(
                    f"Set {config_key} = {config_dict[config_key]} from {env_var}"
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

    def _read_global_config_dict(self) -> dict[str, Any]:
        """Read ``self.config_file`` as a nested dict, ignoring project overrides
        and env vars — i.e. exactly the "global layer" ``load_config`` starts from
        before ``_deep_merge``-ing the overrides file in. Returns ``{}`` if the
        file does not exist or fails to parse (same fallback ``load_config`` uses).
        """
        config_path = Path(self.config_file)
        if not config_path.exists():
            return {}
        try:
            with open(config_path) as f:
                raw = json.load(f)
        except Exception:  # noqa: BLE001 - parse-recovery, mirrors load_config
            return {}
        file_is_nested = any(
            isinstance(v, dict) and k in SearchConfig._SUBCONFIG_NAMES
            for k, v in raw.items()
        )
        return raw if file_is_nested else SearchConfig._flat_to_nested(raw)

    def _prune_active_overrides(self, config_dict: dict[str, Any]) -> None:
        """Strip the active project's overridden fields from *config_dict* in-place.

        ``load_config`` deep-merges the active project's ``search_overrides.json``
        (ADR-0014) into the returned config, so ``config`` — and therefore
        ``config_dict`` — can carry values that only apply to that project.
        Without this guard, every ``load_config()`` -> mutate -> ``save_config()``
        handler (e.g. ``handle_configure_search_mode``) would silently promote
        those project-scoped values into the global config file. Each overridden
        field is restored to whatever the global file currently has on disk for
        it, or omitted entirely if the global file never set it.
        """
        meta = self._active_overrides_meta
        if not meta:
            return
        global_dict = self._read_global_config_dict()
        for dotted in meta["keys"]:
            section, _, field = dotted.partition(".")
            if not field:
                continue  # defensive: SearchConfig overrides are always "section.field"
            global_section = global_dict.get(section)
            if isinstance(global_section, dict) and field in global_section:
                config_dict.setdefault(section, {})[field] = global_section[field]
            else:
                config_dict.get(section, {}).pop(field, None)

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

            config_dict = config.to_dict()  # Serialize BEFORE opening file
            self._prune_active_overrides(config_dict)
            write_json_atomic(self.config_file, config_dict)

            self.logger.info(f"Saved search config to {self.config_file}")
            self._config = config  # Update cached config
            # Sync mtime so the next load_config() short-circuits to the cache
            # instead of re-reading and re-parsing the file we just wrote.
            self._config_mtime = Path(self.config_file).stat().st_mtime

        except Exception as e:
            self.logger.error(f"Failed to save config to {self.config_file}: {e}")
            raise  # Re-raise so caller knows save failed

    def get_search_mode_for_query(
        self, query: str, explicit_mode: str | None = None
    ) -> str:
        """Determine best search mode for a query."""
        config = self.load_config()

        # Use explicit mode if provided
        if explicit_mode and explicit_mode != SearchMode.AUTO:
            return explicit_mode

        # Use default mode if not auto
        if config.search_mode.default_mode != SearchMode.AUTO:
            return config.search_mode.default_mode

        # Auto-detect based on query characteristics
        query_lower = query.lower()

        # Text-heavy queries -> BM25
        if any(
            keyword in query_lower for keyword in ["string", "message", "error", "log"]
        ):
            return SearchMode.BM25

        # Code structure queries -> semantic
        if any(
            keyword in query_lower
            for keyword in ["class", "function", "method", "interface"]
        ):
            return SearchMode.SEMANTIC

        # Default to hybrid for balanced approach
        return SearchMode.HYBRID


# Global configuration manager instance
_config_manager: SearchConfigManager | None = None

# Transient override set by temporary_ram_fallback_off() during indexing.
# Lives at module scope so it survives _config_manager = None (which clears
# the singleton but does NOT touch this binding) and is never serialised to
# disk, so it cannot trigger the Merkle reindex-loop that a disk write would.
_indexing_ram_fallback_override: bool | None = None


def set_indexing_ram_fallback_override(value: bool | None) -> None:
    """Set (or clear) the transient RAM-fallback override used during indexing.

    Call with ``False`` to suppress PyTorch VRAM spillover during indexing even
    when ``allow_ram_fallback=True`` in the persisted config.  Call with ``None``
    to restore normal config-driven behaviour.  This flag is module-level and
    survives ``_config_manager = None`` resets that happen on every model switch.
    """
    global _indexing_ram_fallback_override
    _indexing_ram_fallback_override = value


def get_indexing_ram_fallback_override() -> bool | None:
    """Return the current transient RAM-fallback override, or None if not set."""
    return _indexing_ram_fallback_override


# Per-project overrides layer (ADR-0014).
PROJECT_OVERRIDES_FILENAME = "search_overrides.json"

# Storage directory of the currently active project (set by the MCP server on
# switch_project / index_directory).  Module-level for the same
# survive-singleton-reset reason as _indexing_ram_fallback_override: it must
# outlive `_config_manager = None` resets on model switches.
_active_project_storage_dir: str | None = None


def set_active_project_storage_dir(path: str | Path | None) -> None:
    """Point the config layer at the active project's storage directory.

    Enables the per-project ``search_overrides.json`` merge in
    :meth:`SearchConfigManager.load_config`.  Pass ``None`` to detach (no
    project active).  The manager's hot-reload cache key includes the override
    file's path+mtime, so no explicit invalidation is required here — the next
    ``load_config()`` picks up the new project's overrides automatically.
    """
    global _active_project_storage_dir
    _active_project_storage_dir = str(path) if path else None


def get_active_project_storage_dir() -> str | None:
    """Return the active project's storage directory, or None if unset."""
    return _active_project_storage_dir


def get_config_manager(config_file: str | None = None) -> SearchConfigManager:
    """Get or create global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = SearchConfigManager(config_file)
    return _config_manager


def get_search_config() -> SearchConfig:
    """Get current search configuration."""
    return get_config_manager().load_config()


def get_chunking_config():
    """Get ChunkingConfig from the current search config, or None if unavailable.

    Safe to call from ``chunking/`` modules — uses a try/except guard so the
    chunker can still function when the search config is not yet initialised.
    """
    try:
        config = get_search_config()
        return config.chunking if config else None
    except AttributeError:
        return None


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
