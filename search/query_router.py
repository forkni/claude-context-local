"""Query routing system for multi-model semantic search.

Routes queries to the optimal embedding model based on query characteristics.
Based on empirical verification results comparing Qwen3, BGE-M3, and CodeRankEmbed.

Note: Qwen3 adaptively selects Qwen3-4B (12GB+ GPUs) or Qwen3-0.6B (8GB GPUs).
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


logger = logging.getLogger(__name__)


def _load_routing_config() -> dict | None:
    """Load routing configuration from YAML with fallback to None.

    Returns:
        Loaded config dict if successful, None to trigger hardcoded fallback
    """
    config_path = Path(__file__).parent.parent / "config" / "routing_keywords.yaml"
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded routing config from {config_path}")
                return config
    except Exception as e:
        logger.warning(
            f"Failed to load routing config from {config_path}: {e}. Using hardcoded defaults."
        )
    return None


# Cache loaded config at module level (loaded once on import)
_ROUTING_CONFIG = _load_routing_config()


@dataclass
class RoutingDecision:
    """Result of query routing decision."""

    model_key: str
    confidence: float
    reason: str
    scores: dict[str, float]


class QueryRouter:
    """Routes queries to optimal embedding model based on query characteristics.

    Routing strategy based on verification results:
    - Qwen3 (3/8 wins): Implementation-heavy queries, algorithms, complete systems
      (Adaptive: Qwen3-4B on 12GB+ GPUs, Qwen3-0.6B on 8GB GPUs)
    - BGE-M3 (3/8 wins): Workflow queries, configuration, system plumbing (most consistent)
    - CodeRankEmbed (2/8 wins): Specialized algorithms (Merkle, RRF, etc.)
    """

    # Routing rules based on verification results (analysis/model_relevance_verification_results.md)
    # Enhanced with single-word variants for natural query support (2025-11-15)
    ROUTING_RULES = {
        "coderankembed": {
            "keywords": [
                # Specialized algorithms (2/8 wins, but high precision)
                "merkle",
                "merkle tree",
                "merkle dag",
                "tree",
                "change detection",
                "rrf",
                "reranking",
                "reciprocal rank",
                "rank fusion",
                "rerank",
                "tree structure",
                "directed acyclic",
                "dag",
                # Data structures
                "binary tree",
                "graph structure",
                "binary",
                "graph",
                # Hybrid search components
                "hybrid",
                "fusion",
                "fuse",
                "combine",
                # NEW - Compound data structure phrases (SAFE)
                "data structure",
                "data structures",
                "data model",
                "data modeling",
                "dataclass",
                "dataclasses",
                "pydantic",
                # NEW - Type system compounds (SAFE)
                "type definition",
                "type definitions",
                "type schema",
                "schema definition",
                "schema definitions",
                "type system",
                "type annotation",
                "type annotations",
                # NEW - Specific OOP compounds (SAFE)
                "class definition",
                "class schema",
                "class hierarchy",
                "interface definition",
                "protocol definition",
                "enum definition",
                "struct definition",
                # NEW - Safe single words (unambiguous)
                "schema",
                "struct",
                "enum",
                "interface",
                "protocol",
                "inheritance",
                "polymorphism",
                "generic",
                "template",
                # NEW - Call graph and dependency analysis (2025-12-15, moved from bge_m3)
                "call graph",
                "callgraph",
                "caller",
                "callers",
                "callee",
                "callees",
                "dependency",
                "dependencies",
                "dependency graph",
            ],
            "weight": 1.5,  # Higher weight for specialized matches
            "description": "Specialized algorithms (Merkle trees, RRF reranking, data structures)",
        },
        "qwen3": {
            "keywords": [
                # Implementation-heavy queries (3/8 wins)
                "implementation",
                "implement",
                "implementing",
                "implements",
                "how to implement",
                "algorithm",
                "algorithmic",
                "algorithms",
                "pattern",
                "patterns",
                "design pattern",
                "how does",
                "how do",
                "how is",
                "how to",
                "how can",
                "class structure",
                "method flow",
                "function flow",
                "function",
                "method",
                "class",
                "complete system",
                "full implementation",
                # Error handling (verified win) - expanded
                "error",
                "error handling",
                "exception",
                "try except",
                "error pattern",
                "exception handling",
                "catch",
                "raise",
                "throw",
                # BM25 implementation (verified win) - expanded
                "bm25",
                "sparse index",
                "keyword search",
                "index implementation",
                "search implementation",
                "search",
                "searching",
                "query",
                # Multi-hop search (verified win) - expanded
                "multi-hop",
                "multi hop",
                "iterative search",
                "search algorithm",
                "hop",
                "iterative",
                "recursive",
                # Common programming terms
                "code",
                "coding",
                "write",
                "create",
                "build",
                # Async programming
                "async",
                "await",
                "coroutine",
                "asyncio",
                "async def",
                "concurrent",
                "concurrency",
                # NEW - Validation and code logic (2025-12-15)
                "validate",
                "validation",
                "validator",
                "validators",
                "handler",
                "handlers",
                "registry",
                "registries",
                "extract",
                "extraction",
                "extractor",
                "parser",
                "parsing",
                "parse",
            ],
            "weight": 1.0,
            "description": "Implementation queries and algorithms",
        },
        "bge_m3": {
            "keywords": [
                # Workflow & configuration (3/8 wins, most consistent)
                "workflow",
                "process",
                "pipeline",
                "flow",
                "loading",
                "initialization",
                "init",
                "setup",
                "initialize",
                "configuration",
                "config",
                "settings",
                "manager",
                "configure",
                # Configuration loading (verified win) - expanded
                "load config",
                "config file",
                "environment variable",
                "loading system",
                "load",
                # Incremental indexing (verified win) - expanded
                "incremental",
                "indexing logic",
                "reindex",
                "indexing",
                "logic",
                "index",
                # Embedding workflow (verified win) - expanded
                "embedding",
                "embed",
                "generation",
                "batch",
                "generation workflow",
                "generate",
                # Vector search components
                "faiss",
                "vector",
                "vectors",
                "similarity",
                "dense",
                "nearest neighbor",
                "knn",
                "ann",
                # General system queries
                "system",
                "integration",
                "connection",
                "connect",
                "integrate",
                # Relationship queries (graph/dependency moved to coderankembed)
                "relationship",
                "relationships",
                "impact",
                "inheritance",
                "inherits",
                "extends",
                "uses",
                "type usage",
                "imports",
                # NEW - Project and workflow terms (2025-12-15)
                "switch",
                "switching",
                "verify",
                "verification",
                "project",
                "projects",
            ],
            "weight": 1.0,
            "description": "Workflow and configuration queries",
        },
    }

    # Explicit precedence for tie-breaking (2025-12-15)
    # When scores are within 0.01 margin, use this order:
    # 1. CodeRankEmbed (specialized algorithms)
    # 2. Qwen3 (implementation logic)
    # 3. BGE-M3 (workflow/config)
    PRECEDENCE = ["coderankembed", "qwen3", "bge_m3"]

    # Default fallback model (most balanced)
    DEFAULT_MODEL = "bge_m3"

    # Confidence threshold for routing (below this, use default)
    # Lowered from 0.3 → 0.15 → 0.10 → 0.05 based on empirical testing
    # Enhanced routing with single-word keywords enables lower threshold
    # Natural queries now trigger routing with 2-3 keyword matches
    CONFIDENCE_THRESHOLD = 0.05

    # Lightweight routing rules for 2-model pools (8GB VRAM GPUs)
    # Used when multi_model_pool="lightweight-speed"
    # Uses BGE-M3 + GTE-ModernBERT (proven combination)
    ROUTING_RULES_LIGHTWEIGHT = {
        "code_model": {  # Maps to gte_modernbert
            "keywords": [
                # Code implementation and algorithms (VALIDATED: 5/11 wins)
                "implementation",
                "implement",
                "implementing",
                "algorithm",
                "algorithmic",
                # Parsing and chunking (VALIDATED: parse/chunk queries won)
                "parse",
                "parsing",
                "parser",
                "chunk",
                "chunking",
                # Data structures and types (VALIDATED: found dataclass in results)
                "data structure",
                "dataclass",
                "dataclasses",
                "type definition",
                "type schema",
                "merkle",
                "binary",
                "dag",
                # OOP concepts (VALIDATED: base class queries won)
                "base class",
                "inheritance",
                "extends",
                "inherits",
                # Search-specific algorithms
                "bm25",
                "multi-hop",
                "recursive",
                "iterative",
                # Async programming
                "async",
                "await",
                "coroutine",
                "concurrent",
                # Code analysis and extraction (VALIDATED: extraction queries won)
                "extract",
                "extraction",
                "extractor",
                # Call graph (VALIDATED: call graph extraction won)
                "call graph",
                "caller",
                "callers",
                "callee",
                "callees",
                "dependency",
                "dependencies",
                "relationship",
                "relationships",
            ],
            "weight": 1.2,  # Reduced from 1.5 to prevent thin-evidence routing
            "description": "Code-specific queries (routes to gte-modernbert)",
        },
        "bge_m3": {
            "keywords": [
                # Workflow and configuration (VALIDATED: BGE strength)
                "workflow",
                "process",
                "pipeline",
                "flow",
                "loading",
                "initialization",
                "init",
                "setup",
                "initialize",
                "configuration",
                "config",
                "configure",
                "settings",
                "manager",
                # Config serialization (VALIDATED: BGE won serialize/deserialize)
                "serialize",
                "serialization",
                "deserialize",
                "to_dict",
                "from_dict",
                "json",
                # Embedding and indexing
                "embedding",
                "embed",
                "indexing",
                "index",
                "incremental",
                "reindex",
                # Vector search
                "faiss",
                "vector",
                "vectors",
                "similarity",
                "dense",
                # System integration
                "system",
                "integration",
                "connection",
                "connect",
                "project",
                "projects",
                "verification",
                "verify",
            ],
            "weight": 1.0,  # Default fallback
            "description": "Workflow, configuration, and system queries",
        },
    }

    # Lightweight precedence (2-model tier breaking)
    PRECEDENCE_LIGHTWEIGHT = ["code_model", "bge_m3"]

    # Default for lightweight pools
    DEFAULT_MODEL_LIGHTWEIGHT = "bge_m3"

    def __init__(self, enable_logging: bool = True) -> None:
        """Initialize query router.

        Args:
            enable_logging: Enable detailed routing decision logging
        """
        self.enable_logging = enable_logging

    def _get_active_pool_type(self) -> str:
        """Get the configured multi-model pool type.

        Returns:
            Pool type: "full" or "lightweight-speed"
        """
        try:
            from search.config import get_search_config

            config = get_search_config()
            return config.routing.multi_model_pool or "full"
        except Exception as e:
            logger.debug(f"Config unavailable, using full pool: {e}")
            return "full"

    def _get_routing_rules(self) -> tuple[dict, list, str]:
        """Get appropriate routing rules based on configured pool.

        Loads from YAML config if available, falls back to hardcoded defaults.

        Returns:
            Tuple of (rules_dict, precedence_list, default_model)
        """
        pool_type = self._get_active_pool_type()

        # Try YAML config first
        if _ROUTING_CONFIG is not None:
            pool_key = (
                "lightweight_pool" if pool_type == "lightweight-speed" else "full_pool"
            )
            try:
                pool_config = _ROUTING_CONFIG[pool_key]
                return (
                    pool_config["models"],
                    pool_config["precedence"],
                    pool_config["default_model"],
                )
            except (KeyError, TypeError) as e:
                logger.warning(
                    f"Invalid YAML config structure: {e}. Using hardcoded defaults."
                )

        # Fallback to hardcoded constants
        if pool_type == "lightweight-speed":
            return (
                self.ROUTING_RULES_LIGHTWEIGHT,
                self.PRECEDENCE_LIGHTWEIGHT,
                self.DEFAULT_MODEL_LIGHTWEIGHT,
            )
        else:
            return (
                self.ROUTING_RULES,
                self.PRECEDENCE,
                self.DEFAULT_MODEL,
            )

    def _map_model_key(self, model_key: str) -> str:
        """Map abstract model key to actual model key.

        For lightweight pools, maps 'code_model' to actual model:
        - 'gte_modernbert' for lightweight-speed

        Args:
            model_key: Model key from routing decision

        Returns:
            Actual model key to use for embedding
        """
        if model_key != "code_model":
            return model_key

        pool_type = self._get_active_pool_type()
        if pool_type == "lightweight-speed":
            return "gte_modernbert"
        return model_key  # Fallback (shouldn't happen)

    def route(
        self, query: str, confidence_threshold: Optional[float] = None
    ) -> RoutingDecision:
        """Route query to optimal model based on characteristics.

        Args:
            query: Natural language search query
            confidence_threshold: Minimum confidence to use non-default model.
                                  If None, uses value from YAML config or CONFIDENCE_THRESHOLD (0.05).

        Returns:
            RoutingDecision with model_key, confidence, and reasoning
        """
        if confidence_threshold is None:
            # Try YAML config first (only full_pool has explicit threshold)
            if _ROUTING_CONFIG is not None:
                pool_type = self._get_active_pool_type()
                pool_key = (
                    "lightweight_pool"
                    if pool_type == "lightweight-speed"
                    else "full_pool"
                )
                try:
                    confidence_threshold = _ROUTING_CONFIG[pool_key].get(
                        "confidence_threshold"
                    )
                except (KeyError, TypeError, AttributeError):
                    pass
            # Fallback to hardcoded constant
            if confidence_threshold is None:
                confidence_threshold = self.CONFIDENCE_THRESHOLD

        # Get pool-specific routing rules
        routing_rules, precedence, default_model = self._get_routing_rules()

        # Calculate scores using pool-aware rules
        scores = self._calculate_scores(query)

        # Find best model and confidence
        if not scores or max(scores.values()) == 0:
            # No keywords matched - use default
            decision = RoutingDecision(
                model_key=default_model,
                confidence=0.0,
                reason=f"No specific keywords matched - using default ({default_model})",
                scores=scores,
            )
        else:
            # Use explicit tie-breaking logic with pool-aware precedence
            best_model = self._resolve_tie(scores, precedence)
            confidence = scores[best_model]

            if confidence < confidence_threshold:
                # Low confidence - use default (most reliable)
                decision = RoutingDecision(
                    model_key=default_model,
                    confidence=confidence,
                    reason=f"Low confidence ({confidence:.2f} < {confidence_threshold}) - using default ({default_model})",
                    scores=scores,
                )
            else:
                # High confidence - use matched model
                rule = routing_rules[best_model]
                decision = RoutingDecision(
                    model_key=best_model,
                    confidence=confidence,
                    reason=f"Matched {rule['description']} with confidence {confidence:.2f}",
                    scores=scores,
                )

        # Map abstract model key to actual model (for lightweight pools)
        decision.model_key = self._map_model_key(decision.model_key)

        if self.enable_logging:
            logger.info(
                f"[ROUTING] Query: '{query[:50]}...' → {decision.model_key} "
                f"(confidence: {decision.confidence:.2f}, reason: {decision.reason})"
            )
            if scores:
                logger.debug(f"[ROUTING] Scores: {scores}")

        return decision

    def _calculate_scores(self, query: str) -> dict[str, float]:
        """Calculate routing scores for each model based on keyword matching.

        Args:
            query: Search query string

        Returns:
            Dictionary mapping model_key to normalized score (0.0-1.0)
        """
        query_lower = query.lower()
        scores = {}

        # Get appropriate rules for configured pool
        routing_rules, _, _ = self._get_routing_rules()

        for model_key, rule in routing_rules.items():
            keywords = rule["keywords"]
            weight = rule.get("weight", 1.0)

            # Count matching keywords
            matches = sum(1 for keyword in keywords if keyword in query_lower)

            # Score based on match count: each match adds 0.10, apply weight, cap at 1.0
            # This gives more predictable scores based on actual matches instead of
            # penalizing categories with many keywords (old: matches/len(keywords))
            # Increased from 0.05 to 0.10 for better confidence scores:
            # - 2 matches = 0.20 confidence
            # - 3 matches = 0.30 confidence
            # - 5 matches = 0.50 confidence
            normalized_score = min(matches * 0.10 * weight, 1.0)
            scores[model_key] = normalized_score

        # Ensure scores don't exceed 1.0 after weighting
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 1.0:
            scores = {k: v / max_score for k, v in scores.items()}

        return scores

    def _resolve_tie(self, scores: dict[str, float], precedence: list = None) -> str:
        """Resolve ties using explicit precedence order.

        When multiple models have scores within 0.01 margin, select based on
        precedence order (pool-aware).

        Args:
            scores: Dictionary mapping model_key to score
            precedence: List of model keys in precedence order (from _get_routing_rules)
                        If None, gets from current pool config

        Returns:
            Model key with highest precedence among tied models
        """
        # Get pool-aware defaults if precedence not provided
        if precedence is None:
            _, precedence, default_model = self._get_routing_rules()
        else:
            _, _, default_model = self._get_routing_rules()

        if not scores:
            return default_model

        max_score = max(scores.values())
        # Consider scores within 0.01 as tied
        tied_models = [k for k, v in scores.items() if abs(v - max_score) < 0.01]

        # Return first model in precedence order that's in the tie
        for model in precedence:
            if model in tied_models:
                return model

        # Fallback (should not reach here)
        return default_model

    def get_model_strengths(self, model_key: str) -> Optional[dict]:
        """Get routing rule details for a specific model.

        Args:
            model_key: Model identifier ("qwen3", "bge_m3", "coderankembed")

        Returns:
            Dictionary with keywords, weight, and description, or None if invalid
        """
        return self.ROUTING_RULES.get(model_key)

    def get_available_models(self) -> list[str]:
        """Get list of all models supported by router.

        Returns:
            List of model keys
        """
        return list(self.ROUTING_RULES.keys())


# Convenience function for quick routing
def route_query(query: str, confidence_threshold: float = 0.3) -> str:
    """Quick routing function that returns just the model_key.

    Args:
        query: Search query string
        confidence_threshold: Minimum confidence for non-default model

    Returns:
        Model key string ("qwen3", "bge_m3", or "coderankembed")
    """
    router = QueryRouter(enable_logging=False)
    decision = router.route(query, confidence_threshold)
    return decision.model_key
