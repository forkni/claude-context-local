"""Shared domain types for the search pipeline.

Placing ImpactReport here (rather than in search.relationship_analyzer) lets callers
import it without pulling in the full analyzer or its graph dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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

    parent_classes: list[dict[str, Any]] = field(default_factory=list)
    child_classes: list[dict[str, Any]] = field(default_factory=list)
    uses_types: list[dict[str, Any]] = field(default_factory=list)
    used_as_type_in: list[dict[str, Any]] = field(default_factory=list)
    imports: list[dict[str, Any]] = field(default_factory=list)
    imported_by: list[dict[str, Any]] = field(default_factory=list)

    decorates: list[dict[str, Any]] = field(default_factory=list)
    decorated_by: list[dict[str, Any]] = field(default_factory=list)
    exceptions_raised: list[dict[str, Any]] = field(default_factory=list)
    exception_handlers: list[dict[str, Any]] = field(default_factory=list)
    exceptions_caught: list[dict[str, Any]] = field(default_factory=list)
    instantiates: list[dict[str, Any]] = field(default_factory=list)
    instantiated_by: list[dict[str, Any]] = field(default_factory=list)

    defines_constants: list[dict[str, Any]] = field(default_factory=list)
    uses_constants: list[dict[str, Any]] = field(default_factory=list)
    defines_enum_members: list[dict[str, Any]] = field(default_factory=list)
    uses_defaults: list[dict[str, Any]] = field(default_factory=list)
    defines_class_attrs: list[dict[str, Any]] = field(default_factory=list)
    class_attr_definitions: list[dict[str, Any]] = field(default_factory=list)
    defines_fields: list[dict[str, Any]] = field(default_factory=list)
    field_definitions: list[dict[str, Any]] = field(default_factory=list)
    uses_context_managers: list[dict[str, Any]] = field(default_factory=list)
    context_manager_usages: list[dict[str, Any]] = field(default_factory=list)

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

        for name, value in [
            ("parent_classes", self.parent_classes),
            ("child_classes", self.child_classes),
            ("uses_types", self.uses_types),
            ("used_as_type_in", self.used_as_type_in),
            ("imports", self.imports),
            ("imported_by", self.imported_by),
            ("decorates", self.decorates),
            ("decorated_by", self.decorated_by),
            ("exceptions_raised", self.exceptions_raised),
            ("exception_handlers", self.exception_handlers),
            ("exceptions_caught", self.exceptions_caught),
            ("instantiates", self.instantiates),
            ("instantiated_by", self.instantiated_by),
            ("defines_constants", self.defines_constants),
            ("uses_constants", self.uses_constants),
            ("defines_enum_members", self.defines_enum_members),
            ("uses_defaults", self.uses_defaults),
            ("defines_class_attrs", self.defines_class_attrs),
            ("class_attr_definitions", self.class_attr_definitions),
            ("defines_fields", self.defines_fields),
            ("field_definitions", self.field_definitions),
            ("uses_context_managers", self.uses_context_managers),
            ("context_manager_usages", self.context_manager_usages),
        ]:
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
