"""Intent classification system for search query routing.

Classifies queries by intent (LOCAL, GLOBAL, NAVIGATIONAL, HYBRID) to optimize
retrieval strategy and enable intelligent tool routing.

Intent taxonomy:
- LOCAL: Symbol/entity lookup queries ("where is X defined", CamelCase symbols)
- GLOBAL: Architectural/conceptual queries ("how does X work", "system overview")
- NAVIGATIONAL: Relationship queries ("what calls X", "dependencies of Y")
- HYBRID: Ambiguous queries that don't match specific patterns
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Query intent types for retrieval strategy selection."""

    LOCAL = "local"  # Symbol lookup: "where is QueryRouter defined"
    GLOBAL = "global"  # Architectural: "how does search pipeline work"
    NAVIGATIONAL = "navigational"  # Relationships: "what calls handle_search_code"
    HYBRID = "hybrid"  # Ambiguous/uncertain queries


@dataclass
class IntentDecision:
    """Result of intent classification decision."""

    intent: QueryIntent
    confidence: float
    reason: str
    scores: dict[str, float]
    suggested_params: dict[str, Any] = field(default_factory=dict)


class IntentClassifier:
    """Classifies search queries by intent for optimal handling.

    Routing strategy based on intent:
    - LOCAL: Direct dense search with k=5 (symbol definitions)
    - GLOBAL: Multi-hop search with k=10+ (architectural understanding)
    - NAVIGATIONAL: Redirect to find_connections (dependency analysis)
    - HYBRID: Default hybrid search (uncertain intent)

    Pattern: Follows QueryRouter structure for consistency.
    """

    # Intent classification rules (keyword + pattern matching)
    INTENT_RULES: dict[str, dict[str, Any]] = {
        "local": {
            "keywords": [
                # Definition/implementation queries
                "where is",
                "find the implementation",
                "find the definition",
                "definition of",
                "implementation of",
                "locate",
                "show me",
                # Symbol-specific
                "class",
                "function",
                "method",
                "variable",
                "constant",
                "module",
                "file",
            ],
            "patterns": [
                (r"\b[A-Z][a-z]+([A-Z][a-z]+)+\b", 0.5),  # CamelCase
                (r"\bwhere\s+is\b", 1.5),
                (r"\bfind\s+(the\s+)?(implementation|definition)\b", 1.5),
                (r"\bshow\s+me\s+(the\s+)?", 1.2),
            ],
            "max_tokens": 6,  # Short, focused queries
            "weight": 1.0,
            "description": "Symbol/entity lookup queries",
        },
        "global": {
            "keywords": [
                # Architectural/conceptual queries
                "how does",
                "how do",
                "explain",
                "overview",
                "architecture",
                "design",
                "structure",
                "system",
                "pipeline",
                "workflow",
                "flow",
                "process",
                "mechanism",
                "strategy",
                # Understanding queries
                "understand",
                "learn about",
                "describe",
                "summary",
                "high-level",
            ],
            "patterns": [
                (r"\bhow\s+does\s+.+\s+work\b", 1.8),
                (r"\bhow\s+do\s+.+\s+work\b", 1.8),
                (r"\b(architecture|pipeline|flow|overview)\b", 1.2),
                (r"\bexplain\s+(the\s+)?", 1.3),
            ],
            "weight": 1.0,
            "description": "Architectural/conceptual queries",
        },
        "navigational": {
            "keywords": [
                # Caller/dependency queries
                "what calls",
                "what uses",
                "what depends",
                "who calls",
                "who uses",
                "callers",
                "called by",
                "used by",
                "depends on",
                "dependencies",
                "dependents",
                # Relationship queries
                "imports",
                "imported by",
                "inherits",
                "inherited by",
                "extends",
                "extended by",
                "implements",
                "implemented by",
                # Flow tracing
                "trace",
                "flow from",
                "flow to",
                "call chain",
                "call graph",
                "call stack",
            ],
            "patterns": [
                (r"\b(callers?|called\s+by)\b", 2.0),
                (r"\bwhat\s+(calls|uses|depends)\b", 1.8),
                (r"\b(who\s+)?(calls|uses)\b", 1.5),
                (r"\b(imports?|inherits?|extends?|implements?)\b", 1.5),
                (r"\btrace\s+", 1.3),
                (r"\bdependenc(y|ies)\b", 1.2),
            ],
            "weight": 1.2,  # Higher weight for strong signal
            "description": "Relationship/dependency queries",
        },
    }

    # Precedence order for tie-breaking (highest priority first)
    PRECEDENCE = ["navigational", "local", "global"]

    # Default intent when no patterns match
    DEFAULT_INTENT = QueryIntent.HYBRID

    # Minimum confidence threshold for classification
    CONFIDENCE_THRESHOLD = 0.3

    def __init__(
        self, confidence_threshold: Optional[float] = None, enable_logging: bool = True
    ) -> None:
        """Initialize intent classifier.

        Args:
            confidence_threshold: Minimum confidence for intent-specific routing.
                If None, uses CONFIDENCE_THRESHOLD (0.3).
            enable_logging: Enable detailed classification logging.
        """
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else self.CONFIDENCE_THRESHOLD
        )
        self.enable_logging = enable_logging

    def classify(
        self, query: str, confidence_threshold: Optional[float] = None
    ) -> IntentDecision:
        """Classify query intent for retrieval strategy selection.

        Args:
            query: Natural language search query.
            confidence_threshold: Minimum confidence for intent classification.
                If None, uses instance threshold.

        Returns:
            IntentDecision with intent type, confidence, reason, and suggested params.

        Examples:
            >>> classifier = IntentClassifier()
            >>> decision = classifier.classify("where is QueryRouter defined")
            >>> decision.intent
            QueryIntent.LOCAL

            >>> decision = classifier.classify("how does search pipeline work")
            >>> decision.intent
            QueryIntent.GLOBAL

            >>> decision = classifier.classify("what calls handle_search_code")
            >>> decision.intent
            QueryIntent.NAVIGATIONAL
        """
        if confidence_threshold is None:
            confidence_threshold = self.confidence_threshold

        # Calculate scores for each intent
        scores = self._calculate_scores(query)

        # Check for token count constraint (LOCAL intent)
        query_tokens = query.lower().split()
        is_short_query = len(query_tokens) <= self.INTENT_RULES["local"]["max_tokens"]

        # Find best intent and confidence
        if not scores or max(scores.values()) == 0:
            # No patterns matched - use default
            decision = IntentDecision(
                intent=self.DEFAULT_INTENT,
                confidence=0.0,
                reason=f"No specific patterns matched - using default ({self.DEFAULT_INTENT.value})",
                scores=scores,
            )
        else:
            # Use explicit tie-breaking logic
            best_intent_key = self._resolve_tie(scores)
            confidence = scores[best_intent_key]

            # Apply token count constraint for LOCAL
            if best_intent_key == "local" and not is_short_query:
                confidence *= 0.7  # Reduce confidence for long queries

            if confidence < confidence_threshold:
                # Low confidence - use default (hybrid search)
                decision = IntentDecision(
                    intent=self.DEFAULT_INTENT,
                    confidence=confidence,
                    reason=f"Low confidence ({confidence:.2f} < {confidence_threshold}) - using default ({self.DEFAULT_INTENT.value})",
                    scores=scores,
                )
            else:
                # High confidence - use classified intent
                intent = QueryIntent(best_intent_key)
                rule = self.INTENT_RULES[best_intent_key]
                decision = IntentDecision(
                    intent=intent,
                    confidence=confidence,
                    reason=f"Matched {rule['description']} with confidence {confidence:.2f}",
                    scores=scores,
                )

                # Extract suggested parameters based on intent
                decision.suggested_params = self._extract_suggested_params(
                    query, intent
                )

        if self.enable_logging:
            logger.info(
                f"[INTENT] Query: '{query[:50]}...' → {decision.intent.value} "
                f"(confidence: {decision.confidence:.2f}, reason: {decision.reason})"
            )
            if scores:
                logger.debug(f"[INTENT] Scores: {scores}")

        return decision

    def _calculate_scores(self, query: str) -> dict[str, float]:
        """Calculate intent scores based on keyword and pattern matching.

        Args:
            query: Search query string.

        Returns:
            Dictionary mapping intent key to normalized score (0.0-1.0).
        """
        query_lower = query.lower()
        scores = {}

        for intent_key, rule in self.INTENT_RULES.items():
            total_score = 0.0

            # Keyword matching
            keywords = rule["keywords"]
            keyword_matches = sum(1 for kw in keywords if kw in query_lower)
            total_score += keyword_matches * 0.10

            # Pattern matching
            patterns = rule.get("patterns", [])
            for pattern, pattern_weight in patterns:
                if re.search(pattern, query_lower):
                    total_score += pattern_weight

            # Apply rule weight
            weight = rule.get("weight", 1.0)
            normalized_score = min(total_score * weight, 1.0)
            scores[intent_key] = normalized_score

        # Ensure scores don't exceed 1.0
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 1.0:
            scores = {k: v / max_score for k, v in scores.items()}

        return scores

    def _resolve_tie(self, scores: dict[str, float]) -> str:
        """Resolve ties using explicit precedence order.

        When multiple intents have scores within 0.05 margin, select based on
        PRECEDENCE order: navigational > local > global.

        Args:
            scores: Dictionary mapping intent key to score.

        Returns:
            Intent key with highest precedence among tied intents.
        """
        if not scores:
            return self.DEFAULT_INTENT.value

        max_score = max(scores.values())
        # Consider scores within 0.05 as tied (wider margin than QueryRouter)
        tied_intents = [k for k, v in scores.items() if abs(v - max_score) < 0.05]

        # Return first intent in precedence order that's in the tie
        for intent_key in self.PRECEDENCE:
            if intent_key in tied_intents:
                return intent_key

        # Fallback (should not reach here)
        return self.DEFAULT_INTENT.value

    def _extract_suggested_params(
        self, query: str, intent: QueryIntent
    ) -> dict[str, Any]:
        """Extract suggested parameters based on classified intent.

        Args:
            query: Original search query.
            intent: Classified intent type.

        Returns:
            Dictionary with suggested parameters for downstream tools.
        """
        params: dict[str, Any] = {}

        if intent == QueryIntent.GLOBAL:
            # Suggest larger k for architectural queries
            params["k"] = 10
            params["search_mode"] = "hybrid"

        elif intent == QueryIntent.LOCAL:
            # Suggest smaller k for symbol lookups
            params["k"] = 5
            params["search_mode"] = "semantic"

        elif intent == QueryIntent.NAVIGATIONAL:
            # Extract symbol name for find_connections redirect
            symbol_name = self._extract_symbol_from_query(query)
            if symbol_name:
                params["symbol_name"] = symbol_name
                params["tool"] = "find_connections"

        return params

    def _extract_symbol_from_query(self, query: str) -> Optional[str]:
        """Extract symbol name from navigational queries.

        Examples:
            "what calls handle_search_code" → "handle_search_code"
            "who uses QueryRouter" → "QueryRouter"
            "dependencies of CodeIndexManager" → "CodeIndexManager"

        Args:
            query: Navigational query string.

        Returns:
            Extracted symbol name or None if not found.
        """
        query = query.strip()

        # Pattern 1: "what calls/uses X"
        match = re.search(r"what\s+(calls|uses|depends\s+on)\s+(\w+)", query, re.I)
        if match:
            return match.group(2)

        # Pattern 2: "who calls/uses X"
        match = re.search(r"who\s+(calls|uses)\s+(\w+)", query, re.I)
        if match:
            return match.group(2)

        # Pattern 3: "callers of X" / "dependencies of X"
        match = re.search(r"(callers?|dependencies)\s+of\s+(\w+)", query, re.I)
        if match:
            return match.group(2)

        # Pattern 4: "X callers" / "X dependencies"
        match = re.search(r"(\w+)\s+(callers?|dependencies)", query, re.I)
        if match:
            return match.group(1)

        # Pattern 5: Last CamelCase or snake_case word
        words = query.split()
        for word in reversed(words):
            # Remove trailing punctuation
            word = word.rstrip(".,!?;:")
            # Check if it looks like a symbol (CamelCase or snake_case)
            if re.match(r"^[A-Z][a-zA-Z0-9]+$", word) or re.match(
                r"^[a-z][a-z0-9_]+$", word
            ):
                return word

        return None

    def get_intent_patterns(self, intent: QueryIntent) -> Optional[dict]:
        """Get pattern details for a specific intent type.

        Args:
            intent: Query intent type.

        Returns:
            Dictionary with keywords, patterns, and description, or None if not found.
        """
        intent_key = intent.value
        return self.INTENT_RULES.get(intent_key)
