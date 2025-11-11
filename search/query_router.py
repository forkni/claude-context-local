"""Query routing system for multi-model semantic search.

Routes queries to the optimal embedding model based on query characteristics.
Based on empirical verification results comparing Qwen3-0.6B, BGE-M3, and CodeRankEmbed.
"""

import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Result of query routing decision."""
    model_key: str
    confidence: float
    reason: str
    scores: Dict[str, float]


class QueryRouter:
    """Routes queries to optimal embedding model based on query characteristics.

    Routing strategy based on verification results:
    - Qwen3 (3/8 wins): Implementation-heavy queries, algorithms, complete systems
    - BGE-M3 (3/8 wins): Workflow queries, configuration, system plumbing (most consistent)
    - CodeRankEmbed (2/8 wins): Specialized algorithms (Merkle, RRF, etc.)
    """

    # Routing rules based on verification results (analysis/model_relevance_verification_results.md)
    ROUTING_RULES = {
        "coderankembed": {
            "keywords": [
                # Specialized algorithms (2/8 wins, but high precision)
                "merkle", "merkle tree", "merkle dag", "tree", "change detection",
                "rrf", "reranking", "reciprocal rank", "rank fusion", "rerank",
                "tree structure", "directed acyclic", "dag",
                # Data structures
                "binary tree", "graph structure",
                # Hybrid search components
                "hybrid", "fusion"
            ],
            "weight": 1.5,  # Higher weight for specialized matches
            "description": "Specialized algorithms (Merkle trees, RRF reranking)"
        },
        "qwen3": {
            "keywords": [
                # Implementation-heavy queries (3/8 wins)
                "implementation", "implement", "how to implement",
                "algorithm", "algorithmic",
                "pattern", "patterns", "design pattern",
                "how does", "how do", "how is",
                "class structure", "method flow", "function flow",
                "complete system", "full implementation",
                # Error handling (verified win) - expanded
                "error", "error handling", "exception", "try except", "error pattern",
                "exception handling", "catch", "raise",
                # BM25 implementation (verified win) - expanded
                "bm25", "sparse index", "keyword search", "index implementation",
                "search implementation",
                # Multi-hop search (verified win) - expanded
                "multi-hop", "multi hop", "iterative search", "search algorithm",
                "hop"
            ],
            "weight": 1.0,
            "description": "Implementation queries and algorithms"
        },
        "bge_m3": {
            "keywords": [
                # Workflow & configuration (3/8 wins, most consistent)
                "workflow", "process", "pipeline",
                "loading", "initialization", "init", "setup",
                "configuration", "config", "settings", "manager",
                # Configuration loading (verified win) - expanded
                "load config", "config file", "environment variable", "loading system",
                # Incremental indexing (verified win) - expanded
                "incremental", "indexing logic", "reindex", "indexing", "logic",
                # Embedding workflow (verified win) - expanded
                "embedding", "embed", "generation", "batch", "generation workflow",
                # General system queries
                "system", "integration", "connection"
            ],
            "weight": 1.0,
            "description": "Workflow and configuration queries"
        }
    }

    # Default fallback model (most balanced)
    DEFAULT_MODEL = "bge_m3"

    # Confidence threshold for routing (below this, use default)
    # Lowered from 0.3 → 0.15 → 0.10 based on empirical testing
    # Keyword-based matching requires aggressive threshold for good routing
    CONFIDENCE_THRESHOLD = 0.10

    def __init__(self, enable_logging: bool = True):
        """Initialize query router.

        Args:
            enable_logging: Enable detailed routing decision logging
        """
        self.enable_logging = enable_logging

    def route(self, query: str, confidence_threshold: Optional[float] = None) -> RoutingDecision:
        """Route query to optimal model based on characteristics.

        Args:
            query: Natural language search query
            confidence_threshold: Minimum confidence to use non-default model.
                                  If None, uses CONFIDENCE_THRESHOLD (0.3).

        Returns:
            RoutingDecision with model_key, confidence, and reasoning
        """
        if confidence_threshold is None:
            confidence_threshold = self.CONFIDENCE_THRESHOLD

        # Calculate scores for each model
        scores = self._calculate_scores(query)

        # Find best model and confidence
        if not scores or max(scores.values()) == 0:
            # No keywords matched - use default
            decision = RoutingDecision(
                model_key=self.DEFAULT_MODEL,
                confidence=0.0,
                reason=f"No specific keywords matched - using default ({self.DEFAULT_MODEL})",
                scores=scores
            )
        else:
            best_model = max(scores, key=scores.get)
            confidence = scores[best_model]

            if confidence < confidence_threshold:
                # Low confidence - use default (most reliable)
                decision = RoutingDecision(
                    model_key=self.DEFAULT_MODEL,
                    confidence=confidence,
                    reason=f"Low confidence ({confidence:.2f} < {confidence_threshold}) - using default ({self.DEFAULT_MODEL})",
                    scores=scores
                )
            else:
                # High confidence - use matched model
                rule = self.ROUTING_RULES[best_model]
                decision = RoutingDecision(
                    model_key=best_model,
                    confidence=confidence,
                    reason=f"Matched {rule['description']} with confidence {confidence:.2f}",
                    scores=scores
                )

        if self.enable_logging:
            logger.info(
                f"[ROUTING] Query: '{query[:50]}...' → {decision.model_key} "
                f"(confidence: {decision.confidence:.2f}, reason: {decision.reason})"
            )
            if scores:
                logger.debug(f"[ROUTING] Scores: {scores}")

        return decision

    def _calculate_scores(self, query: str) -> Dict[str, float]:
        """Calculate routing scores for each model based on keyword matching.

        Args:
            query: Search query string

        Returns:
            Dictionary mapping model_key to normalized score (0.0-1.0)
        """
        query_lower = query.lower()
        scores = {}

        for model_key, rule in self.ROUTING_RULES.items():
            keywords = rule["keywords"]
            weight = rule.get("weight", 1.0)

            # Count matching keywords
            matches = sum(1 for keyword in keywords if keyword in query_lower)

            # Normalize by keyword count and apply weight
            if len(keywords) > 0:
                normalized_score = (matches / len(keywords)) * weight
                scores[model_key] = normalized_score
            else:
                scores[model_key] = 0.0

        # Ensure scores don't exceed 1.0 after weighting
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 1.0:
            scores = {k: v / max_score for k, v in scores.items()}

        return scores

    def get_model_strengths(self, model_key: str) -> Optional[Dict]:
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
