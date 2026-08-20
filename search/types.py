"""Shared domain types for the search pipeline.

Placing ImpactReport here (rather than in search.relationship_analyzer) lets callers
import it without pulling in the full analyzer or its graph dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from chunking.relationships.relationship_types import get_relationship_field_mapping


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


class ResultSource(StrEnum):
    """The retrieval-funnel provenance tags stamped on SearchResult.source.

    A real str subclass -- every ``== "hybrid"`` comparison, set/dict
    lookup, and JSON round-trip (dataclasses.asdict + json.dump) keeps
    working unchanged, including against plain strings replayed from
    captured benchmark JSON (see scripts/benchmark/probe_rerank_window.py's
    _SimResult shim). Centralizes the provenance vocabulary so a typo can't
    silently create a 14th, unrecognized channel.

    DENSE and SEMANTIC name the same dense-retrieval channel under two
    different labels -- a pre-existing inconsistency between RRFReranker/
    SearchExecutor (which stamp "dense") and ResultFactory.from_dense_results
    (which stamps "semantic"). Nothing consumes either value today, so
    unifying them is a behaviour-visible wire change deferred to its own
    round -- both members are kept here verbatim.
    """

    # Legs (hop-1 single-channel results)
    BM25 = "bm25"
    DENSE = "dense"
    SEMANTIC = "semantic"

    # Fusion
    HYBRID = "hybrid"

    # Expansion (multi-hop, graph, ego, parent, query-variant legs)
    MULTI_HOP = "multi_hop"
    GRAPH_HOP = "graph_hop"
    BM25_VARIANT = "bm25_variant"
    DENSE_VARIANT = "dense_variant"
    EGO_GRAPH = "ego_graph"
    PARENT_EXPANSION = "parent_expansion"

    # Lookup / similarity
    DIRECT_LOOKUP = "direct_lookup"
    SIMILARITY = "similarity"

    # Default
    UNKNOWN = "unknown"


# Source tags whose SearchResult.score is a fabricated placeholder, not a
# ranking signal -- SearchResult.is_unscored (search/reranker.py) reads this
# set directly. Only sources whose 0.0 is *unconditional* belong here.
#
# parent_expansion is unconditional: HybridSearcher._apply_parent_expansion
# always calls ResultFactory.from_expansion(parent_id, 0.0, ...) (D9) -- there
# is no config path that ever gives a parent chunk a real score.
#
# graph_hop is deliberately excluded even though it also stamps 0.0 on some
# candidates (MultiHopSearcher._score_graph_hop_candidates): whether a given
# graph_hop result is scored is conditional per query on
# SearchConfig.graph_enhanced.graph_hop_call_evidence_enabled (ADR-0039), not
# a static property of the source tag. That per-call distinction is carried
# by RerankWindowPolicy.graph_hop_unscored, a caller-declared flag -- adding
# "graph_hop" here unconditionally would mislabel every scored graph_hop
# result as unscored whenever call-evidence scoring is on.
UNSCORED_SOURCES: frozenset[str] = frozenset({ResultSource.PARENT_EXPANSION})


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
# their original order. Kept fixed (not derived) so any consumer relying on
# today's key order for these specific 23 names sees no change — the
# consolidation onto ImpactReport.relationships stays additive, not a
# reshuffle. See get_relationship_field_mapping() in
# chunking/relationships/relationship_types.py for the full vocabulary this
# is a subset of.
_LEGACY_RELATIONSHIP_FIELDS: tuple[str, ...] = (
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


def _compute_emitted_relationship_fields() -> tuple[str, ...]:
    """All relationship field names to_dict() emits, in stable order.

    Derived from get_relationship_field_mapping() — the single source of
    truth for the relationship vocabulary — rather than hand-maintained a
    second time. _LEGACY_RELATIONSHIP_FIELDS keeps its historical relative
    order first; every other field the mapping defines is appended, sorted
    for determinism, so adding a relationship type never reorders an
    existing one. "calls" is excluded: to_dict() already emits its forward
    field (direct_callers) as its own top-level key, separately from this
    loop.
    """
    all_fields: set[str] = set()
    for fwd, rev in get_relationship_field_mapping().values():
        if fwd:
            all_fields.add(fwd)
        if rev:
            all_fields.add(rev)
    all_fields.discard("direct_callers")

    remainder = sorted(all_fields - set(_LEGACY_RELATIONSHIP_FIELDS))
    return (*_LEGACY_RELATIONSHIP_FIELDS, *remainder)


_EMITTED_RELATIONSHIP_FIELDS: tuple[str, ...] = _compute_emitted_relationship_fields()


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

        # Unconditional (D13): unlike the other relationship buckets below, which
        # are ordinary absence-of-data, direct_callers/direct_callees are two of
        # NEVER_DROP_EMPTY_KEYS' four allowlisted keys (output_formatter.py) --
        # the formatter's post-pass can only re-add a key that was present here
        # to begin with, so gating this emission on truthiness silently defeated
        # the allowlist for every symbol with no callers.
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

        # Outbound callees (bidirectional). Unconditional for the same reason as
        # direct_callers above (D13).
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
