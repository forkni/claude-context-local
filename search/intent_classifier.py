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
from typing import Any


logger = logging.getLogger(__name__)


# Blocklist of common programming terms that shouldn't be matched as symbols
_CODE_TERM_BLOCKLIST = {
    "method",
    "function",
    "class",
    "module",
    "variable",
    "constant",
    "attribute",
    "property",
    "field",
    "parameter",
    "argument",
    "type",
    "interface",
    "enum",
    "struct",
    "trait",
    "protocol",
    "caller",
    "callers",
    "callee",
    "callees",
    "implementation",
    "definition",
    "declaration",
    "reference",
    "import",
    "imports",
    "export",
    "exports",
    "handler",
    "helper",
    "utility",
    "wrapper",
    "factory",
    "object",
    "instance",
    "value",
    "result",
    "error",
    "exception",
}


class QueryIntent(Enum):
    """Query intent types for retrieval strategy selection."""

    LOCAL = "local"  # Symbol lookup: "where is QueryRouter defined"
    GLOBAL = "global"  # Architectural: "how does search pipeline work"
    NAVIGATIONAL = "navigational"  # Relationships: "what calls handle_search_code"
    PATH_TRACING = "path_tracing"  # Path finding: "trace path from X to Y"
    SIMILARITY = "similarity"  # Code similarity: "find code similar to X"
    CONTEXTUAL = "contextual"  # Context exploration: "explore context around X"
    HYBRID = "hybrid"  # Ambiguous/uncertain queries


# Intent-driven BM25/Dense weight profiles
INTENT_WEIGHT_PROFILES: dict[QueryIntent, tuple[float, float]] = {
    QueryIntent.LOCAL: (
        0.35,
        0.65,
    ),  # (bm25, dense) - Semantic-dominant for symbol discovery (optimal via Step 1A/1B testing)
    QueryIntent.GLOBAL: (0.3, 0.7),  # semantic understanding matters
    QueryIntent.CONTEXTUAL: (0.3, 0.7),  # similar to GLOBAL
    QueryIntent.NAVIGATIONAL: (0.5, 0.5),  # balanced for relationship tracing
    QueryIntent.PATH_TRACING: (0.4, 0.6),
    QueryIntent.SIMILARITY: (0.4, 0.6),
    QueryIntent.HYBRID: (0.4, 0.6),  # default balanced
}


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
    - LOCAL: Direct dense search with k=4 (symbol definitions)
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
                # Retrieval verbs
                "lookup",
                "retrieve",
                "get the",
                "obtain",
                "fetch",
                # Discovery terms
                "discover",
                "identify",
                # Existence-checking query patterns
                "check if",
                "does",
                "is there",
                "exists",
                # Symbol-specific
                "class",
                "function",
                "method",
                "variable",
                "constant",
                "module",
                "file",
                "interface",
                "type",
                "enum",
                "struct",
                # Implementation-focused verbs (added to fix Q19 intent classification failure)
                # These verbs indicate concrete code implementation queries, not architectural queries
                "encode",
                "decode",
                "parse",
                "serialize",
                "deserialize",
                "convert",
                "transform",
                "validate",
                "normalize",
                "extract",
                "process",
                "handle",
                "compute",
                "calculate",
                "render",
                "format",
                "generate",
                "build",
            ],
            "patterns": [
                # REMOVED: Dead CamelCase pattern (ran against lowered query, never matched)
                # Functionality moved to _detect_code_symbols() fallback
                (r"\bwhere\s+is\b", 1.5),
                (r"\bfind\s+(the\s+)?(implementation|definition)\b", 1.5),
                (r"\bshow\s+me\s+(the\s+)?", 1.2),
                (r"\b(lookup|retrieve|fetch)\s+(\w+)\b", 1.3),  # "lookup QueryRouter"
                (
                    r"\bget\s+(the\s+)?(\w+)\s+(class|function|definition)\b",
                    1.5,
                ),  # "get the QueryRouter class"
                (
                    r"\bget\s+\w+(\s+\w+)*\s+from\b",
                    1.3,
                ),  # "get node text from tree sitter"
                (
                    r"\b(enum|interface|struct|type)\s+\w+\b",
                    1.2,
                ),  # "interface SearchResult"
                (r"\bcheck\s+if\s+\w+\s+exists?\b", 1.4),
                (r"\bdoes\s+\w+\s+exist\b", 1.4),
                (r"\bis\s+there\s+(a\s+)?\w+\b", 1.3),
            ],
            "max_tokens": 8,  # Short, focused queries (raised for natural language function lookups)
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
                # Software patterns
                "pattern",
                "approach",
                "paradigm",
                "model",
                "framework",
                # Conceptual understanding
                "concept",
                "rationale",
                "purpose",
                "reasoning",
                "logic behind",
                # System terms
                "component",
                "module interaction",
                "integration",
                "data flow",
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
                (r"\bwhy\s+(does|is)\b", 1.3),  # "why does search use embeddings"
                (
                    r"\bwhat\s+is\s+the\s+(purpose|rationale|logic)\b",
                    1.4,
                ),  # "what is the purpose of..."
                (
                    r"\b(component|layer)s?\s+(interact|work)\b",
                    1.2,
                ),  # "how components interact"
                (
                    r"\b(arrangement|organization|scheme)\s+of\b",
                    1.2,
                ),  # e.g., "organization of search system"
                (
                    r"\b(procedure|technique|methodology)\s+(for|of)\b",
                    1.3,
                ),  # e.g., "methodology for indexing"
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
                # Synonym coverage for dependency terminology
                "relations",
                "reliance",
                "correlations",
                # Caller/Callee terminology
                "callee",
                "callees",
                "invokes",
                "invoked by",
                "triggers",
                "triggered by",
                # Upstream/Downstream
                "upstream",
                "downstream",
                "upstream of",
                "downstream of",
                # Consumer/Provider
                "consumer",
                "consumers",
                "provider",
                "providers",
                "client",
                "clients",
                "supplier",
                "suppliers",
                # Relationship queries
                "imports",
                "imported by",
                "inherits",
                "inherited by",
                "extends",
                "extended by",
                "implements",
                "implemented by",
                "decorates",
                "decorated by",
                # Exception handling
                "raises",
                "throws",
                "exception",
                "exceptions",
                # Instantiation
                "creates",
                "instantiates",
                "instances",
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
                (r"\b(decorates?|decorated\s+by)\b", 1.5),
                (r"\b(raises?|throws?|exceptions?)\b", 1.5),
                (r"\b(creates?|instantiates?|instances?)\b", 1.5),
                (r"\b(callee|callees)\s+(of|for)\b", 1.8),  # "callees of process_query"
                (
                    r"\b(upstream|downstream)\s+(of|from|to)\b",
                    1.5,
                ),  # "upstream of QueryRouter"
                (
                    r"\b(consumer|provider|client|supplier)s?\s+(of|for)\b",
                    1.5,
                ),  # "consumers of API"
                (r"\b(invokes?|triggers?)\s+\w+\b", 1.3),  # "invokes handle_search"
                (r"\btrace\s+", 1.3),
                (r"\bdependenc(y|ies)\b", 1.2),
                (
                    r"\b(relations|reliance|correlations)\s+(of|between)\b",
                    1.3,
                ),  # e.g., "relations of IntentClassifier"
            ],
            "weight": 1.2,  # Higher weight for strong signal
            "description": "Relationship/dependency queries",
        },
        "path_tracing": {
            "keywords": [
                "trace",
                "follow",
                "path from",
                "path to",
                "path between",
                "connect",
                "connection between",
                "how does X connect",
                "flow from",
                "flow to",
                "reaches",
                "leads to",
                # Synonym coverage for path-tracing terminology
                "trail",
                "pursue",
                # Journey metaphors
                "route",
                "route from",
                "route to",
                "journey",
                # Linking terms
                "link",
                "link between",
                "bridge",
                "bridge to",
                # Sequence terms
                "traversal",
            ],
            "patterns": [
                (r"\btrace\s+(path\s+)?(from|to)\b", 2.0),
                (
                    r"\bfollow\s+(the\s+)?(path|call|execution|flow)\b",
                    1.8,
                ),  # "follow the path", "follow call"
                (r"\bpath\s+(from|to|between)\b", 2.0),
                (r"\bhow\s+does\s+\w+\s+connect\s+to\b", 1.8),
                (r"\bconnection\s+between\b", 1.5),
                (r"\b(from|to)\s+\w+\s+(to|from)\s+\w+\b", 1.3),
                (
                    r"\b(trail|pursue)\s+(the\s+)?(path|call|flow)\b",
                    1.5,
                ),  # e.g., "trail the path"
                (
                    r"\b(route|journey)\s+(from|to|between)\b",
                    1.8,
                ),  # "route from login to logout"
                (r"\blink\s+(between|from|to)\b", 1.5),  # "link between modules"
            ],
            "weight": 1.3,
            "description": "Path tracing queries between code entities",
        },
        "similarity": {
            "keywords": [
                "similar to",
                "similar code",
                "like this",
                "patterns like",
                "code like",
                "implementations like",
                "similar implementations",
                "same pattern",
                "resembles",
                "looks like",
                # Synonym coverage for similarity terminology
                "replicate",
                "mimic",
                "emulate",
                "replica",
                "mirror",
                "counterpart",
                "look-alike",
                "parallel",
                "twin",
                # Clone detection terminology
                "clone",
                "clones",
                "clone of",
                "duplicate",
                "duplicates",
                "duplicate of",
                "copy",
                "copies",
                "copy of",
                # Comparative terms
                "equivalent",
                "analogous",
                "comparable",
                "matching",
                "matches",
            ],
            "patterns": [
                (r"\bsimilar\s+(to|code|implementations?)\b", 2.0),
                (r"\b(code|patterns?|implementations?)\s+like\b", 1.8),
                (r"\bfind\s+(code\s+)?similar\b", 1.8),
                (r"\b(resembles?|looks?\s+like)\b", 1.3),
                (
                    r"\b(clone|duplicate|copy)\s+(of|code)\b",
                    2.0,
                ),  # "clone of QueryRouter"
                (r"\bfind\s+(clones?|duplicates?|copies)\b", 1.8),  # "find clones"
                (
                    r"\b(equivalent|analogous|comparable)\s+to\b",
                    1.5,
                ),  # "equivalent to X"
                (r"\b(matches|matching)\s+\w+\b", 1.3),  # "matches QueryRouter pattern"
                (
                    r"\b(replicate|mimic|emulate)s?\s+\w+\b",
                    1.5,
                ),  # e.g., "replicate QueryRouter"
                (
                    r"\b(replica|counterpart|twin)\s+(of|for)\b",
                    1.8,
                ),  # e.g., "replica of QueryRouter"
                (
                    r"\b(mirror|parallel)\s+(of|to)\b",
                    1.5,
                ),  # e.g., "mirror of IntentClassifier"
                (
                    r"\blook-alike\s+(of|for|to)\b",
                    1.5,
                ),  # e.g., "look-alike of QueryRouter"
            ],
            "weight": 1.2,
            "description": "Code similarity queries",
        },
        "contextual": {
            "keywords": [
                "context",
                "around",
                "related to",
                "connected to",
                "neighbors",
                "surrounding",
                "nearby code",
                "explore",
                "overview of",
                "understand",
                # Synonym coverage for contextual exploration terminology
                "investigate",
                "examine",
                "probe",
                "inspect",
                "survey",
                "look into",
                "delve into",
                "delve",
                "scout",
                "scour",
                # Spatial metaphors
                "vicinity",
                "vicinity of",
                "proximity",
                "proximity to",
                "neighborhood",
                "periphery",
                # Scope terms
                "scope",
                "scope of",
                "environment",
                "ecosystem",
                # Discovery
                "discover related",
                "what touches",
            ],
            "patterns": [
                (r"\b(context|surrounding)\b.*\b(of|around|for)\b", 1.8),
                (r"\brelated\s+(to|code)\b", 1.5),
                (r"\bexplore\s+\w+\b", 1.3),
                (r"\bunderstand\s+(how|the)\b", 1.2),
                (
                    r"\b(investigate|examine|inspect)\s+\w+\b",
                    1.3,
                ),  # e.g., "investigate handle_search_code"
                (
                    r"\b(delve|probe)\s+(into\s+)?\w+\b",
                    1.5,
                ),  # e.g., "delve into QueryRouter"
                (
                    r"\b(survey|scout)\s+(the\s+)?\w+\b",
                    1.2,
                ),  # e.g., "survey the codebase"
                (
                    r"\b(vicinity|proximity|neighborhood)\s+(of|around)\b",
                    1.8,
                ),  # "vicinity of QueryRouter"
                (
                    r"\bwhat\s+(touches|interacts\s+with)\b",
                    1.5,
                ),  # "what touches this module"
                (
                    r"\b(ecosystem|environment)\s+(of|around)\b",
                    1.3,
                ),  # "ecosystem of search"
            ],
            "weight": 1.0,
            "description": "Contextual exploration queries (ego-graph beneficial)",
        },
    }

    # Precedence order for tie-breaking (highest priority first)
    PRECEDENCE = [
        "path_tracing",
        "similarity",
        "navigational",
        "contextual",
        "local",
        "global",
    ]

    # Default intent when no patterns match
    DEFAULT_INTENT = QueryIntent.HYBRID

    # Minimum confidence threshold for classification
    CONFIDENCE_THRESHOLD = 0.3

    def __init__(
        self, confidence_threshold: float | None = None, enable_logging: bool = True
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
        self, query: str, confidence_threshold: float | None = None
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
            # Log weight overrides for debugging Q12
            if "bm25_weight" in decision.suggested_params:
                bm25_w = decision.suggested_params["bm25_weight"]
                dense_w = decision.suggested_params["dense_weight"]
                profile_w = INTENT_WEIGHT_PROFILES.get(decision.intent, (None, None))
                if (bm25_w, dense_w) != profile_w:
                    logger.info(
                        f"[INTENT] Weight override active: BM25={bm25_w}, Dense={dense_w} "
                        f"(profile default would be {profile_w})"
                    )

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

        # Fallback: Symbol detection when main classification produces no signal.
        # Only activates when NO intent scored above 0.15, preventing symbol names
        # from overwhelming verb signals in mixed queries ("how does HybridSearcher work").
        # Research: Prevents regression on verb-signaled queries (Q31 GLOBAL=0.20,
        # Q19 LOCAL=0.20) while fixing all-zero queries (FAISS query max=0.0).
        if scores and max(scores.values()) < 0.15:
            symbol_boost = self._detect_code_symbols(query)
            if symbol_boost > 0:
                scores["local"] = min(scores.get("local", 0.0) + symbol_boost, 1.0)
                logger.debug(
                    f"[INTENT] Symbol fallback: detected code symbols, "
                    f"LOCAL boosted by {symbol_boost:.2f} → {scores['local']:.2f}"
                )

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

    def _detect_code_symbols(self, query: str) -> float:
        """Detect code symbols using Python naming conventions (case-sensitive).

        Runs against ORIGINAL query (not lowercased) to detect:
        - CamelCase/PascalCase: HybridSearcher, IndexFlatIP, HTMLParser
        - UPPER_CASE constants: FAISS, BM25, API, MAX_RETRIES
        - snake_case identifiers: embed_chunks, search_code
        - Dunder methods: __init__, __enter__, __repr__
        - dot.notation: module.Class, self.method

        Per Python style guide (PYTHON_STYLE_GUIDE_QUICK.md lines 46-52):
        CamelCase=classes, snake_case=functions, UPPER_CASE=constants,
        dunder=special methods.

        Returns:
            LOCAL score boost (0.0-0.5), capped to prevent overwhelming
            verb signals in mixed queries.

        Examples:
            >>> classifier = IntentClassifier()
            >>> classifier._detect_code_symbols("HybridSearcher BM25")
            0.40  # CamelCase +0.25, UPPER_CASE +0.15
            >>> classifier._detect_code_symbols("how does X work")
            0.0   # No symbols detected
        """
        boost = 0.0
        tokens = re.findall(r"[\w.]+", query)  # Split preserving dots and underscores

        for token in tokens:
            # Skip common programming terms (not actual symbol names)
            if token in _CODE_TERM_BLOCKLIST:
                continue

            # CamelCase/PascalCase: HybridSearcher, IndexFlatIP, HTMLParser
            # Detect transition from lowercase to uppercase within token
            if re.search(r"[a-z][A-Z]", token) or re.search(r"[A-Z][a-z]+[A-Z]", token):
                boost += 0.25
            # UPPER_CASE with 2+ alpha chars: FAISS, BM25, MAX_RETRIES
            # Requires at least one alphabetic char after first to avoid single letters
            elif re.match(r"^[A-Z][A-Z0-9_]{1,}$", token) and any(
                c.isalpha() for c in token[1:]
            ):
                boost += 0.15
            # Dunder methods: __init__, __enter__, __repr__
            elif (
                re.match(r"^__[a-z]\w+__$", token)
                or "_" in token
                and re.match(r"^_?[a-z][a-z0-9_]+$", token)
            ):
                boost += 0.20
            # dot.notation with mixed case: module.Class, self.method
            elif "." in token and re.search(r"[A-Z]", token):
                boost += 0.25

        return min(boost, 0.5)

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
            # Suggest k=5 for symbol lookups (reverted from k=4 in commit 1802322)
            # Wider pool helps graph-isolated symbols that can't benefit from multi-hop
            params["k"] = 5
            params["search_mode"] = "hybrid"

            # Existence-checking queries benefit from semantic-heavy weights.
            # BM25 over-matches "index" and "exists" on internal implementation code,
            # while semantic search better understands user intent for discovery queries.
            query_lower = query.lower()
            if any(
                p in query_lower for p in ("check if", "is there", "exists for")
            ) or re.search(r"^does\b.+\b(exist|have|support|contain)\b", query_lower):
                params["bm25_weight"] = 0.35
                params["dense_weight"] = 0.65

        elif intent == QueryIntent.NAVIGATIONAL:
            # Extract symbol name for find_connections redirect
            symbol_name = self._extract_symbol_from_query(query)
            if symbol_name:
                params["symbol_name"] = symbol_name
                params["tool"] = "find_connections"
            # Suggest relationship_types filter for specific relationship queries
            rel_types = self._detect_relationship_types(query)
            if rel_types:
                params["relationship_types"] = rel_types

        elif intent == QueryIntent.PATH_TRACING:
            # Extract source and target for find_path
            source, target = self._extract_path_endpoints(query)
            if source and target:
                params["source"] = source
                params["target"] = target
                params["tool"] = "find_path"

        elif intent == QueryIntent.SIMILARITY:
            # Extract reference symbol for find_similar_code
            reference = self._extract_symbol_from_query(query)
            if reference:
                params["symbol_name"] = reference
                params["tool"] = "find_similar_code"

        elif intent == QueryIntent.CONTEXTUAL:
            # Suggest ego_graph for broader context
            params["ego_graph_enabled"] = True
            params["ego_graph_k_hops"] = 2
            symbol_name = self._extract_symbol_from_query(query)
            if symbol_name:
                params["symbol_name"] = symbol_name

        # Add weight suggestions from profile (don't overwrite intent-specific)
        if intent in INTENT_WEIGHT_PROFILES and "bm25_weight" not in params:
            bm25_w, dense_w = INTENT_WEIGHT_PROFILES[intent]
            params["bm25_weight"] = bm25_w
            params["dense_weight"] = dense_w

        return params

    def _extract_symbol_from_query(self, query: str) -> str | None:
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

        # Pattern 5: Last CamelCase or snake_case word (3-pass with blocklist)
        words = query.split()

        # First pass: prefer words with underscores (strong symbol signal)
        for word in reversed(words):
            word = word.rstrip(".,!?;:")
            if "_" in word and re.match(r"^[a-z][a-z0-9_]+$", word):
                return word

        # Second pass: CamelCase (always a symbol)
        for word in reversed(words):
            word = word.rstrip(".,!?;:")
            if re.match(r"^[A-Z][a-zA-Z0-9]+$", word):
                return word

        # Third pass: plain lowercase (but not blocklisted)
        for word in reversed(words):
            word = word.rstrip(".,!?;:")
            if word.lower() not in _CODE_TERM_BLOCKLIST and re.match(
                r"^[a-z][a-z0-9_]+$", word
            ):
                return word

        return None

    def _detect_relationship_types(self, query: str) -> list[str]:
        """Detect which relationship_types filter to suggest based on query.

        Args:
            query: Search query string.

        Returns:
            List of relationship types to filter by, or empty for all.

        Examples:
            >>> classifier = IntentClassifier()
            >>> classifier._detect_relationship_types("what inherits from BaseChunker")
            ['inherits']
            >>> classifier._detect_relationship_types("what imports QueryRouter")
            ['imports']
            >>> classifier._detect_relationship_types("callee of process_query")
            ['calls']
        """
        query_lower = query.lower()
        types = []

        # Caller/Callee detection (for calls relationship)
        if any(
            kw in query_lower
            for kw in ["caller", "callee", "calls", "invokes", "triggers"]
        ):
            types.append("calls")

        # Consumer/Provider detection (maps to calls/uses)
        if any(
            kw in query_lower for kw in ["consumer", "provider", "client", "supplier"]
        ):
            types.append("calls")

        # Inheritance patterns
        if any(
            kw in query_lower
            for kw in ["inherit", "parent", "child", "extends", "subclass"]
        ):
            types.append("inherits")

        # Import patterns
        if any(
            kw in query_lower for kw in ["import", "imported by", "module dependencies"]
        ):
            types.append("imports")

        # Decorator patterns
        if any(kw in query_lower for kw in ["decorate", "decorated", "@"]):
            types.append("decorates")

        # Type usage patterns
        if any(
            kw in query_lower for kw in ["type annotation", "typed as", "uses type"]
        ):
            types.append("uses_type")

        # Exception patterns
        if any(kw in query_lower for kw in ["raises", "throws", "exception"]):
            types.extend(["raises", "catches"])

        # Instantiation patterns
        if any(kw in query_lower for kw in ["creates", "instantiate", "new instance"]):
            types.append("instantiates")

        return types

    def _extract_path_endpoints(self, query: str) -> tuple[str | None, str | None]:
        """Extract source and target symbols from path-tracing queries.

        Args:
            query: Path tracing query string.

        Returns:
            Tuple of (source, target) or (None, None) if not found.

        Examples:
            >>> classifier = IntentClassifier()
            >>> classifier._extract_path_endpoints("trace path from login to database")
            ('login', 'database')
            >>> classifier._extract_path_endpoints("how does UserModel connect to API")
            ('UserModel', 'API')
        """
        query = query.strip()

        # Pattern 1: "from X to Y"
        match = re.search(r"from\s+(\w+)\s+to\s+(\w+)", query, re.I)
        if match:
            return match.group(1), match.group(2)

        # Pattern 2: "between X and Y"
        match = re.search(r"between\s+(\w+)\s+and\s+(\w+)", query, re.I)
        if match:
            return match.group(1), match.group(2)

        # Pattern 3: "how does X connect to Y"
        match = re.search(r"how\s+does\s+(\w+)\s+connect\s+to\s+(\w+)", query, re.I)
        if match:
            return match.group(1), match.group(2)

        # Pattern 4: "X to Y path/connection"
        match = re.search(r"(\w+)\s+to\s+(\w+)\s+(path|connection)", query, re.I)
        if match:
            return match.group(1), match.group(2)

        return None, None

    def get_intent_patterns(self, intent: QueryIntent) -> dict | None:
        """Get pattern details for a specific intent type.

        Args:
            intent: Query intent type.

        Returns:
            Dictionary with keywords, patterns, and description, or None if not found.
        """
        intent_key = intent.value
        return self.INTENT_RULES.get(intent_key)
