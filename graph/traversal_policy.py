"""Traversal policy: the shape of one graph-neighbour walk.

See CONTEXT.md's "Traversal policy" glossary entry. The seven fields here are
everything ``CodeGraphStorage.get_neighbors_ranked`` needs to know to walk
from an anchor: which relations to follow, how deep, which import categories
to skip, the edge-type weights (``None`` = unweighted BFS), and the three
edge gates (confidence floor, confidence-scaled priority, ``tag:ambiguous``
drop). Callers build one policy and pass it whole instead of threading seven
loose parameters through every layer between them and the traversal.

The two named constructors mirror the two production callers:

- :meth:`TraversalPolicy.ego` -- ``EgoGraphRetriever`` (k-hop ego graph,
  relation filter and import exclusions from ``EgoGraphConfig``).
- :meth:`TraversalPolicy.graph_hop` -- ``MultiHopSearcher._graph_expand``
  (depth-1 weighted hop over ``DEFAULT_EDGE_WEIGHTS``).

Both read the three gates off ``GraphEnhancedConfig``
(``min_traversal_confidence``, ``traversal_confidence_weighting_enabled``,
``drop_ambiguous_traversal_edges``) and tolerate ``None`` for it: the
no-config path stays byte-identical to the all-defaults policy.

This module has no runtime dependency on ``graph.graph_storage`` (which
imports it), so :meth:`admits` takes the edge's already-resolved ambiguity
flag and confidence rather than the raw edge dict.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:  # pragma: no mutate
    from search.config import EgoGraphConfig, GraphEnhancedConfig


DEFAULT_RELATION_TYPES: tuple[str, ...] = ("calls", "called_by")


@dataclass(frozen=True)
class TraversalPolicy:
    """How ``get_neighbors_ranked`` walks the graph from an anchor.

    Attributes:
        relation_types: Relation names to follow (``"_by"`` suffix for the
            reverse direction). ``None`` means :data:`DEFAULT_RELATION_TYPES`;
            see :attr:`effective_relation_types`.
        max_depth: Maximum hop count from the anchor.
        exclude_import_categories: Import categories to skip on ``imports``
            edges (e.g. ``["stdlib", "builtin", "third_party"]``); ``None``
            skips nothing.
        edge_weights: Edge-type weights for priority-queue traversal.
            ``None`` selects plain level-order BFS.
        min_confidence: Drop edges whose resolved confidence is below this
            floor. ``0.0`` is a true no-op.
        confidence_weighting: Weighted mode only. Scale each edge's
            type-weight by its resolved confidence.
        drop_ambiguous: Skip ``tag:ambiguous`` call edges
            (``graph.graph_storage.is_ambiguous_call_edge``) regardless of
            ``min_confidence``.
    """

    relation_types: list[str] | None = None
    max_depth: int = 1
    exclude_import_categories: list[str] | None = None
    edge_weights: dict[str, float] | None = None
    min_confidence: float = 0.0
    confidence_weighting: bool = False
    drop_ambiguous: bool = False

    @property
    def effective_relation_types(self) -> list[str]:
        """``relation_types`` with ``None`` resolved to the call-both-ways
        default. An explicit empty list stays empty (follows nothing)."""
        if self.relation_types is None:
            return list(DEFAULT_RELATION_TYPES)
        return self.relation_types

    def admits(self, *, ambiguous: bool, confidence: float) -> bool:
        """The one edge filter both traversal modes apply.

        ``ambiguous`` is ``is_ambiguous_call_edge(edge_data)`` and
        ``confidence`` is ``CodeGraphStorage._edge_confidence(...)`` for the
        edge under consideration. Both are resolved by the caller, so the
        permissive unknown-confidence default (ADR-0050) stays in
        ``CodeGraphStorage``. Drops edges, not nodes: a neighbour reachable
        through a surviving edge is still admitted.
        """
        if self.drop_ambiguous and ambiguous:
            return False
        return not (self.min_confidence > 0.0 and confidence < self.min_confidence)

    @classmethod
    def graph_hop(
        cls,
        graph_enhanced: "GraphEnhancedConfig | None" = None,
        edge_weights: dict[str, float] | None = None,
    ) -> "TraversalPolicy":
        """``MultiHopSearcher._graph_expand``'s walk: one weighted hop.

        ``edge_weights`` falls back to ``DEFAULT_EDGE_WEIGHTS``. This walk
        is always weighted (calls 1.0 > imports 0.3), never level-order BFS.
        """
        if edge_weights is None:
            # Local import: graph_storage imports this module at load time.
            from graph.graph_storage import DEFAULT_EDGE_WEIGHTS

            edge_weights = DEFAULT_EDGE_WEIGHTS
        min_confidence, confidence_weighting, drop_ambiguous = cls._gates(
            graph_enhanced
        )
        return cls(
            max_depth=1,
            edge_weights=edge_weights,
            min_confidence=min_confidence,
            confidence_weighting=confidence_weighting,
            drop_ambiguous=drop_ambiguous,
        )

    @classmethod
    def ego(
        cls,
        ego_graph: "EgoGraphConfig",
        graph_enhanced: "GraphEnhancedConfig | None" = None,
    ) -> "TraversalPolicy":
        """``EgoGraphRetriever``'s walk: ``k_hops`` deep over the configured
        relation filter, with stdlib/builtin and third-party ``imports``
        edges excluded per ``EgoGraphConfig``."""
        exclude_categories: list[str] = []
        if ego_graph.exclude_stdlib_imports:
            exclude_categories.extend(["stdlib", "builtin"])
        if ego_graph.exclude_third_party_imports:
            exclude_categories.append("third_party")
        min_confidence, confidence_weighting, drop_ambiguous = cls._gates(
            graph_enhanced
        )
        return cls(
            relation_types=ego_graph.relation_types,
            max_depth=ego_graph.k_hops,
            exclude_import_categories=exclude_categories or None,
            edge_weights=ego_graph.edge_weights,
            min_confidence=min_confidence,
            confidence_weighting=confidence_weighting,
            drop_ambiguous=drop_ambiguous,
        )

    @staticmethod
    def _gates(
        graph_enhanced: "GraphEnhancedConfig | None",
    ) -> tuple[float, bool, bool]:
        """``(min_confidence, confidence_weighting, drop_ambiguous)`` read off
        ``GraphEnhancedConfig``, or the no-op defaults when no config is
        supplied."""
        if graph_enhanced is None:
            return 0.0, False, False
        return (
            graph_enhanced.min_traversal_confidence,
            graph_enhanced.traversal_confidence_weighting_enabled,
            graph_enhanced.drop_ambiguous_traversal_edges,
        )
