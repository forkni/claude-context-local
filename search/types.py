"""Shared domain types for the search pipeline.

Placing ImpactReport here (rather than in search.relationship_analyzer) lets callers
import it without pulling in the full analyzer or its graph dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from search.config import SearchConfig, SearchMode


# Python primitives, stdlib types, and typing module types that will never be
# found in the project index — skip searcher.search() for these.
BUILTIN_TYPES: frozenset[str] = frozenset(
    {
        "str",
        "int",
        "bool",
        "float",
        "bytes",
        "complex",
        "list",
        "dict",
        "tuple",
        "set",
        "frozenset",
        "None",
        "type",
        "object",
        "slice",
        "range",
        "Any",
        "Union",
        "Optional",
        "List",
        "Dict",
        "Tuple",
        "Set",
        "FrozenSet",
        "Type",
        "Callable",
        "Iterator",
        "Iterable",
        "Generator",
        "Sequence",
        "Mapping",
        "MutableMapping",
        "MutableSequence",
        "MutableSet",
        "Awaitable",
        "Coroutine",
        "AsyncIterator",
        "AsyncIterable",
        "AsyncGenerator",
        "T",
        "K",
        "V",
        "KT",
        "VT",
    }
)


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Everything one retrieval executes against.

    Constructed once by HybridSearcher.search and threaded unchanged through
    MultiHopSearcher, the single-hop callback, and SearchExecutor.execute_single_hop.
    Hop-1 widening derives a copy with a different k via dataclasses.replace —
    there is no with_k() helper; one call site doesn't earn one.

    NB: shallow freeze — `config` is a mutable SearchConfig reachable through
    this object. Nothing may mutate it mid-request; the orchestrator's only
    config mutation happens before construction (search_orchestrator.py:498-501,
    before the search call at :511).
    """

    query: str
    k: int
    search_mode: SearchMode
    bm25_weight: float
    dense_weight: float
    min_bm25_score: float
    use_parallel: bool
    filters: dict[str, Any] | None
    config: SearchConfig


# The 23 relationship buckets ImpactReport.to_dict() has always emitted, in
# their original order. See get_relationship_field_mapping() in
# chunking/relationships/relationship_types.py for the full vocabulary this
# is a subset of.
_EMITTED_RELATIONSHIP_FIELDS: tuple[str, ...] = (
    "parent_classes",
    "child_classes",
    "uses_types",
    "used_as_type_in",
    "imports",
    "imported_by",
    "decorates",
    "decorated_by",
    "exceptions_raised",
    "exception_handlers",
    "exceptions_caught",
    "instantiates",
    "instantiated_by",
    "defines_constants",
    "uses_constants",
    "defines_enum_members",
    "uses_defaults",
    "defines_class_attrs",
    "class_attr_definitions",
    "defines_fields",
    "field_definitions",
    "uses_context_managers",
    "context_manager_usages",
)


@dataclass
class ImpactReport:
    """Structured impact analysis report."""

    symbol: dict[str, Any]
    chunk_id: str
    direct_callers: list[dict[str, Any]]
    indirect_callers: list[dict[str, Any]]
    similar_code: list[dict[str, Any]]
    total_impacted: int
    unique_files: set[str]
    dependency_graph: dict[str, list[str]]

    # All non-caller relationship buckets (inheritance, type usage, imports,
    # decorators, exceptions, instantiation, constants, class attrs, fields,
    # context managers, …), keyed by the field names in
    # get_relationship_field_mapping() (chunking/relationships/relationship_types.py).
    # Populated wholesale by RelationshipAnalyzer._build_graph_relationships,
    # which already iterates that same mapping — this dict is its shape
    # verbatim, not a second declaration of the vocabulary.
    relationships: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    stale_chunk_count: int = 0

    # Phase 4 observability: per-confidence counts for direct callers.
    # Populated by RelationshipAnalyzer._enrich_callers.
    # - exact: caller_id was resolved directly by get_by_chunk_id
    # - recovered: stale/drifted ID re-resolved by _resolve_by_symbol
    # - ambiguous: graph edge tagged confidence="ambiguous" (multiple candidates)
    direct_callers_exact: int = 0
    direct_callers_recovered: int = 0
    direct_callers_ambiguous: int = 0

    # Outbound call resolution: what the target calls.
    # Populated by RelationshipAnalyzer._enrich_callees (bidirectional Stage).
    direct_callees: list[dict[str, Any]] = field(default_factory=list)
    direct_callees_exact: int = 0
    direct_callees_recovered: int = 0
    direct_callees_ambiguous: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict, omitting empty fields."""
        result: dict[str, Any] = {
            "symbol": self.symbol,
            "chunk_id": self.chunk_id,
        }

        if self.direct_callers:
            result["direct_callers"] = self.direct_callers
        if self.indirect_callers:
            result["indirect_callers"] = self.indirect_callers
        if self.similar_code:
            result["similar_code"] = self.similar_code

        result["total_impacted"] = self.total_impacted
        result["file_count"] = len(self.unique_files)

        if self.unique_files:
            result["affected_files"] = sorted(self.unique_files)
        if self.dependency_graph:
            result["dependency_graph"] = self.dependency_graph

        for name in _EMITTED_RELATIONSHIP_FIELDS:
            value = self.relationships.get(name)
            if value:
                result[name] = value

        if self.stale_chunk_count > 0:
            result["stale_chunk_count"] = self.stale_chunk_count

        # Emit caller-confidence breakdown whenever any non-zero counter is present
        if (
            self.direct_callers_exact
            or self.direct_callers_recovered
            or self.direct_callers_ambiguous
        ):
            result["caller_confidence"] = {
                "exact": self.direct_callers_exact,
                "recovered": self.direct_callers_recovered,
                "ambiguous": self.direct_callers_ambiguous,
            }

        # Outbound callees (bidirectional)
        if self.direct_callees:
            result["direct_callees"] = self.direct_callees
        if (
            self.direct_callees_exact
            or self.direct_callees_recovered
            or self.direct_callees_ambiguous
        ):
            result["callee_confidence"] = {
                "exact": self.direct_callees_exact,
                "recovered": self.direct_callees_recovered,
                "ambiguous": self.direct_callees_ambiguous,
            }

        return result
