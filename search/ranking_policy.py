"""Ranking constants and pure factor functions shared across all rankers.

Single source of truth for the magic numbers and common factor logic that
appear in both ranking_heuristics and centrality_ranker.  Each ranker keeps
its own orchestration (mutation order, rounding, logging) and may extend the
shared dicts with ranker-specific entries.

MUST NOT import from other search/ modules to avoid circular imports.
"""

# ---------------------------------------------------------------------------
# Lifecycle method constants
# ---------------------------------------------------------------------------

LIFECYCLE_METHODS: frozenset[str] = frozenset(
    {
        "__init__",
        "__enter__",
        "__exit__",
        "__del__",
        "__repr__",
        "__str__",
    }
)
"""Dunder methods treated as boilerplate when the query has no lifecycle intent."""

LIFECYCLE_INTENT_WORDS: frozenset[str] = frozenset(
    {
        "init",
        "enter",
        "exit",
        "del",
        "repr",
        "lifecycle",
    }
)
"""Query words that signal explicit lifecycle intent, suppressing the ×0.85 demotion."""

# ---------------------------------------------------------------------------
# Entity-detection: action words used to distinguish entity vs prose queries
# ---------------------------------------------------------------------------

ACTION_WORDS: frozenset[str] = frozenset(
    {
        "find",
        "search",
        "get",
        "show",
        "list",
        "how",
        "what",
        "where",
        "when",
        "create",
        "build",
        "make",
        "handle",
        "process",
        "manage",
        "implement",
    }
)
"""Tokens that indicate a procedural query (find / search / get …), not an entity lookup."""

# ---------------------------------------------------------------------------
# Type boost dicts
#
# Each dict maps chunk kind → score multiplier.
# Callers may add ranker-specific entries (e.g. decorated_definition, split_block)
# via {**SHARED_DICT, "decorated_definition": 1.1} without touching shared values.
# ---------------------------------------------------------------------------

TYPE_BOOSTS_CLASS_KEYWORD: dict[str, float] = {
    "class": 1.4,
    "function": 1.2,
    "method": 1.2,
    "module": 0.82,
    "operator": 1.2,
    "td_class": 0.82,
}
"""Applied when the query explicitly contains the word 'class' (ranking_heuristics branch)."""

TYPE_BOOSTS_ENTITY: dict[str, float] = {
    "class": 1.35,
    "function": 1.15,
    "method": 1.15,
    "module": 0.85,
    "struct": 1.25,
    "operator": 1.15,
    "td_class": 0.85,
}
"""Applied when the query looks like an entity/type name (shared by both rankers)."""

TYPE_BOOSTS_CODE: dict[str, float] = {
    "function": 1.2,
    "method": 1.2,
    "class": 1.35,
    "module": 0.90,
    "operator": 1.2,
    "td_class": 0.9,
}
"""Default type multipliers for code/prose queries (shared by both rankers)."""

TD_CLASS_TAG = "td_class"
"""Tag the TD network chunker puts on its synthetic per-op-type ``class`` chunks."""

TD_NETWORK_SUFFIX = ".tdgraph.json"
"""Compound extension of TD network exports (mirrors chunking.language_registry;
duplicated here so ranking_policy stays a leaf module)."""


def effective_chunk_kind(chunk_type: str, tags, chunk_id: str = "") -> str:
    """Map a chunk's stored kind to the key used in the type-boost tables.

    The TD network chunker emits one ``class`` chunk per operator type
    (``class:glslTOP``) tagged ``td_class``.  It is a summary of the instances,
    not a definition, so it must not inherit the ×1.35 ``class`` boost tuned for
    Python classes; ADR-0062 D2 measured that boost putting the class chunk above
    its own instance on every type-descriptive query.  Everything else passes
    through unchanged.
    """
    if chunk_type != "class":
        return chunk_type
    if tags and TD_CLASS_TAG in tags:
        return "td_class"
    # The MCP result rows (result_view._format_search_results) carry no tags,
    # so at runtime the chunk id is the only signal: a class chunk whose file
    # part is a .tdgraph.json export can only come from the TD chunker.
    file_part = chunk_id.split(":", 1)[0] if chunk_id else ""
    if file_part.endswith(TD_NETWORK_SUFFIX):
        return "td_class"
    return chunk_type


# ---------------------------------------------------------------------------
# Name-overlap tiers
#
# (min_ratio, multiplier) pairs, highest threshold first.
# Both rankers use these same thresholds and multipliers, but differ in how
# they compute the overlap ratio:
#   ranking_heuristics: query-centric  (overlap / len(query_tokens))
#   centrality_ranker:  name-centric   (overlap / len(name_tokens))
# The tiers themselves are shared; the denominator choice stays in each ranker.
# ---------------------------------------------------------------------------

NAME_OVERLAP_TIERS: tuple[tuple[float, float], ...] = (
    (0.8, 1.3),
    (0.5, 1.2),
    (0.3, 1.1),
)
"""(min_ratio, multiplier) pairs for name-token overlap boosting.  Iterate from
highest threshold down and apply the first match."""

# ---------------------------------------------------------------------------
# Pure factor functions
# ---------------------------------------------------------------------------


def lifecycle_demotion(terminal_name: str, query_lower: str) -> float:
    """Return the lifecycle-method demotion factor.

    Args:
        terminal_name: The bare name to check — callers are responsible for
            stripping any class qualification before calling
            (e.g. "IntelligentSearcher.__init__" → "__init__").
        query_lower: The query string, already lowercased.

    Returns:
        0.85 when the name is a lifecycle method and the query has no explicit
        lifecycle intent; 1.0 otherwise (no-op multiplier).
    """
    if terminal_name in LIFECYCLE_METHODS and not any(
        w in query_lower for w in LIFECYCLE_INTENT_WORDS
    ):
        return 0.85
    return 1.0
