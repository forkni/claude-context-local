"""
Graph storage and persistence using NetworkX.

Provides NetworkX-based storage for code call graphs with JSON persistence.
"""

import contextlib
import heapq
import itertools
import json
import logging
from collections import deque
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from graph.schema import (
    EDGE_ATTR_CONFIDENCE,
    EDGE_ATTR_IS_METHOD,
    EDGE_ATTR_IS_RESOLVED,
    EDGE_ATTR_LINE,
    EDGE_ATTR_TYPE,
    NODE_ATTR_FILE,
    NODE_ATTR_IS_CALL_TARGET,
    NODE_ATTR_IS_TARGET_NAME,
    NODE_ATTR_LANGUAGE,
    NODE_ATTR_NAME,
    NODE_ATTR_TYPE,
    NODE_TYPE_SYMBOL_NAME,
    edge_relation_type,
    get_reverse_relation,
)
from utils.atomic_io import write_json_atomic
from utils.path_utils import normalize_path


if TYPE_CHECKING:
    from chunking.relationships.relationship_types import RelationshipEdge

import networkx as nx


# Legacy string confidence tags written by the in-house call extractor
# (add_relationship_edge writes confidence=edge.confidence which is "exact" / "ambiguous").
# These must be passed through unchanged by get_edge_data — do NOT coerce to float.
# Downstream enrichers (_enrich_callers/_enrich_callees) read them as string tokens.
_LEGACY_CONFIDENCE_TAGS: frozenset[str] = frozenset({"exact", "ambiguous", "recovered"})

# Numeric proxy for the legacy string confidence tags, used only by
# `edge_confidence()` below when no float `resolver_confidence` is present.
# Values are below every real resolver score (pyan 0.75 / libcst 0.90 / lsp 0.98)
# so a tagged-but-unresolved edge never outranks a resolver-verified one.
AST_CONFIDENCE_BY_TAG: dict[str, float] = {
    "ambiguous": 0.5,
    "recovered": 0.5,
    "exact": 0.7,
}


def edge_confidence(edge_data: dict, edge_type: "str | None" = None) -> "float | None":
    """Resolve an edge's confidence to a float, or ``None`` when truly unknown.

    Canonical confidence-resolution algorithm, used directly by
    :meth:`CodeGraphStorage.get_neighbors` (traversal), which maps ``None`` to
    ``1.0`` (permissive — never silently prune). Two other layers apply this
    same "unknown" policy but do not call this function directly, because
    they read from already-decayed display dicts rather than raw
    ``edge_data``, and doing so would additionally pull in the string-tag
    mapping below and change their existing ordering (out of scope for a
    no-op fix — see ``search/relationship_analyzer.py:220,226,483,574``,
    which defaults bare ``resolver_confidence`` to ``0.5`` and intentionally
    ignores the ``confidence`` string tag for sort/dedup purposes, and
    ``mcp_server/tools/result_view.py:275``, which defaults to ``0.0`` so
    unranked callers always sort last). Returning ``None`` for "unknown"
    here — rather than baking in one of those three defaults — is what lets
    each layer keep its own documented policy instead of silently agreeing on
    one magic constant.

    Resolution order:
      1. Float ``resolver_confidence`` (written by the resolver pipeline:
         pyan 0.75 / libcst 0.90 / lsp 0.98) — the ground truth when present.
      2. Legacy string ``confidence`` tag ("exact"/"ambiguous"/"recovered"),
         mapped via :data:`AST_CONFIDENCE_BY_TAG`.
      3. ``0.5`` when ``edge_type == "calls"`` and neither of the above is
         present — the common case for untagged base-AST call edges when the
         ``[callgraph]`` extras are not installed (~80% of `calls` edges on a
         typical index carry no confidence signal at all).
      4. ``None`` otherwise — non-call relationship edges with no tag/float.

    Args:
        edge_data: Edge attribute dict from the NetworkX graph.
        edge_type: The edge's forward relationship type (e.g. from
            :func:`graph.schema.edge_relation_type`), or ``None`` if unknown
            to the caller.

    Returns:
        A confidence float, or ``None`` when no signal is available.
    """
    confidence = edge_data.get("resolver_confidence")
    if isinstance(confidence, (int, float)):
        return float(confidence)
    tag = edge_data.get("confidence")
    if isinstance(tag, str) and tag in AST_CONFIDENCE_BY_TAG:
        return AST_CONFIDENCE_BY_TAG[tag]
    if edge_type == "calls":
        return 0.5
    return None


# Edge-type weights for weighted BFS (SOG paper: data flow > control flow > effect flow)
# Higher weight = higher priority in graph traversal
DEFAULT_EDGE_WEIGHTS: dict[str, float] = {
    "calls": 1.0,  # Most important for code understanding
    "inherits": 0.9,  # Critical for class hierarchies
    "implements": 0.9,  # Critical for interface patterns
    "overrides": 0.85,  # Important for polymorphism
    "uses_type": 0.7,  # Type usage
    "instantiates": 0.7,  # Object creation
    "decorates": 0.5,  # Moderate signal
    "raises": 0.4,  # Exception patterns
    "catches": 0.4,  # Exception patterns
    "imports": 0.3,  # Low signal - most code imports many things
    "assigns_to": 0.5,  # Assignment tracking
    "reads_from": 0.5,  # Read tracking
    "defines_constant": 0.4,  # Constant definitions
    "defines_enum_member": 0.4,  # Enum members
    "defines_class_attr": 0.5,  # Class attributes
    "defines_field": 0.5,  # Dataclass fields
    "uses_constant": 0.4,  # Constant usage
    "uses_default": 0.3,  # Default parameter values
    "uses_global": 0.3,  # Global references
    "asserts_type": 0.4,  # Type assertions
    "uses_context_manager": 0.4,  # Context manager usage
}


class CodeGraphStorage:
    """
    NetworkX-based graph storage with persistence.

    Stores call graph relationships and provides efficient graph operations.

    Storage Format:
        - Nodes: Chunk IDs with metadata (name, type, file, language)
        - Edges: Call relationships with metadata (line_number, is_method_call)
        - Persistence: JSON via nx.node_link_data/graph
    """

    def __init__(self, project_id: str, storage_dir: Path | None = None) -> None:
        """
        Initialize graph storage.

        Args:
            project_id: Unique identifier for the project
            storage_dir: Directory for graph storage (default: ~/.claude_code_search/graphs)
        """
        self.logger = logging.getLogger(__name__)
        self.project_id = project_id

        # Setup storage directory
        if storage_dir is None:
            home = Path.home()
            storage_dir = home / ".claude_code_search" / "graphs"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Graph file path
        self.graph_path = self.storage_dir / f"{project_id}_call_graph.json"

        # Initialize multi-directed graph: allows parallel edges per (u,v) pair keyed
        # by relationship type, so a node pair can carry both "calls" and "imports"
        # without data loss.  Old DiGraph JSON is coerced on load (see load()).
        self.graph = nx.MultiDiGraph()

        # Secondary index: name -> list[chunk_id] for O(1) find_path lookups.
        # Populated by add_node() and rebuilt by load() after graph restore.
        self._name_index: dict[str, list[str]] = {}

        # Monotonic version counter + centrality memo (P3-3, search-latency plan).
        # `_bump_version()` is called by every method that mutates `self.graph`
        # (construction, add_node, add_call_edge, upgrade_call_edge,
        # add_relationship_edge, load, clear, remove_file_nodes) — see
        # `_bump_version` docstring for why `itertools.count()` rather than a
        # plain counter. `_centrality_cache` maps method name -> (version at
        # computation time, scores); see get_cached_centrality/set_cached_centrality.
        self._version_seq = itertools.count()
        self._version: int = -1
        self._centrality_cache: dict[str, tuple[int, dict[str, float]]] = {}
        self._bump_version()

        # Load existing graph if available
        if self.graph_path.exists():
            self.load()

    def _bump_version(self) -> None:
        """Advance the graph version counter, invalidating the centrality memo.

        Must be called by every method that mutates ``self.graph`` — including
        replacing it wholesale (``load``, ``clear``) or updating an edge's
        attributes in place (``upgrade_call_edge``). Completeness is enforced by
        an AST test (``tests/unit/graph/test_graph_storage_version.py``) that
        scans this class for methods touching ``self.graph`` and asserts each
        one also calls this method.

        Uses ``itertools.count()`` rather than a plain ``+= 1``: ``next()`` on an
        ``itertools.count()`` is atomic in CPython (single bytecode-level
        operation), so two concurrent bumps cannot race and collide on the same
        value. A plain increment could lose an update under concurrent callers,
        letting two *distinct* graph states share a version number — the one way
        this cache could serve stale centrality scores.
        """
        self._version = next(self._version_seq)

    @property
    def version(self) -> int:
        """Monotonic counter bumped by :meth:`_bump_version` on every mutation.

        Consumed by :class:`search.centrality_ranker.CentralityRanker` to key its
        memoized centrality scores (see :meth:`get_cached_centrality`).
        """
        return self._version

    def get_cached_centrality(self, method: str) -> dict[str, float] | None:
        """Return a fresh copy of memoized centrality scores for *method*.

        Returns ``None`` if there is no entry, or if the graph has mutated since
        the entry was computed (version mismatch) — in which case the caller
        should recompute and store the new result via
        :meth:`set_cached_centrality`.

        Always returns a shallow copy, never the cached dict itself: the caller
        (``CentralityRanker.get_centrality_scores``) hands this dict onward to
        shared, long-lived state (``ego_graph_retriever.set_centrality_scores``),
        so every call must return a distinct object — required for the
        per-query isolation the search-latency plan's byte-identical
        equivalence tests depend on.
        """
        entry = self._centrality_cache.get(method)
        if entry is None:
            return None
        cached_version, scores = entry
        if cached_version != self._version:
            return None
        return dict(scores)

    def set_cached_centrality(
        self, method: str, version: int, scores: dict[str, float]
    ) -> None:
        """Store *scores* for *method*, tagged with the graph *version*.

        *version* must be captured by the caller BEFORE computing *scores* (not
        after) — see ``CentralityRanker.get_centrality_scores``. If a mutation
        lands on the graph mid-computation, ``self._version`` will have already
        advanced past the captured value by the time this is called, so the
        entry is stored under a version that can never be the *current* one
        again — the next read misses and recomputes. Worst case is one
        duplicated computation; never a stale read.
        """
        self._centrality_cache[method] = (version, dict(scores))

    def add_node(
        self,
        chunk_id: str,
        name: str,
        chunk_type: str,
        file_path: str,
        language: str = "python",
        **kwargs,
    ) -> None:
        """
        Add a node to the graph.

        Args:
            chunk_id: Unique chunk identifier
            name: Function/class/method name
            chunk_type: Type of chunk (function, method, class, etc.)
            file_path: Source file path
            language: Programming language
            **kwargs: Additional node attributes
        """
        # If node already exists under a different name, remove the stale mapping.
        if chunk_id in self.graph:
            old_name = self.graph.nodes[chunk_id].get("name")
            if old_name and old_name != name and old_name in self._name_index:
                with contextlib.suppress(ValueError):
                    self._name_index[old_name].remove(chunk_id)
                if not self._name_index[old_name]:
                    del self._name_index[old_name]

        self.graph.add_node(
            chunk_id,
            name=name,
            type=chunk_type,
            file=file_path,
            language=language,
            **kwargs,
        )
        if name not in self._name_index:
            self._name_index[name] = []
        if chunk_id not in self._name_index[name]:
            self._name_index[name].append(chunk_id)
        self._bump_version()

    def add_call_edge(
        self,
        caller_id: str,
        callee_name: str,
        line_number: int = 0,
        is_method_call: bool = False,
        is_resolved: bool = False,
        **kwargs,
    ) -> None:
        """
        Add a call relationship edge.

        Args:
            caller_id: Chunk ID of the caller
            callee_name: Name of the called function. Can be:
                - Qualified name (ClassName.method) for self/super calls
                - Bare name (method) for unresolved calls
                - Full chunk_id (future: for fully resolved calls)
            line_number: Line number of the call
            is_method_call: Whether this is a method call
            is_resolved: Whether callee_name is fully resolved to a chunk_id
                (vs qualified name or bare name)
            **kwargs: Additional edge attributes.  **⚠ Never pass ``source``
                or ``target`` as a key** — NetworkX node-link format reserves
                those names for edge endpoints and silently drops them on
                save/load.  Use ``resolver_source`` instead.
        """
        # Create lightweight target_name node if it doesn't exist
        # This enables get_callers(callee_name) queries to work
        # (matching add_relationship_edge() behavior at lines 167-175)
        if callee_name not in self.graph:
            self.graph.add_node(
                callee_name,
                **{
                    NODE_ATTR_NAME: callee_name,
                    NODE_ATTR_TYPE: NODE_TYPE_SYMBOL_NAME,  # Distinguish from full chunk nodes
                    NODE_ATTR_IS_TARGET_NAME: True,  # Flag for query filtering
                    NODE_ATTR_IS_CALL_TARGET: True,  # New flag: distinguishes from relationship targets
                    NODE_ATTR_FILE: "",  # Unknown file (will be resolved if chunk exists)
                    NODE_ATTR_LANGUAGE: "",  # Unknown language
                },
            )

        self.graph.add_edge(
            caller_id,
            callee_name,
            key="calls",  # MultiDiGraph: dedups within-type; different types are parallel edges
            **{
                EDGE_ATTR_TYPE: "calls",
                EDGE_ATTR_LINE: line_number,
                EDGE_ATTR_IS_METHOD: is_method_call,
                EDGE_ATTR_IS_RESOLVED: is_resolved,
            },
            **kwargs,
        )
        self._bump_version()

    def upgrade_call_edge(
        self, caller_id: str, callee_id: str, **attrs: object
    ) -> None:
        """Update attributes on an existing ``calls`` edge in-place.

        Called by the resolver injection seam when a higher-confidence resolver
        produces an edge that was already added by a lower-confidence resolver.
        Only updates the keys supplied in *attrs*; all other edge attributes are
        preserved.

        Args:
            caller_id: Source node (caller chunk_id).
            callee_id: Target node (callee chunk_id or symbol name).
            **attrs: Edge attribute key-value pairs to overwrite.  Typical keys:
                ``resolver_source``, ``resolver_confidence``, ``is_resolved``, ``line``.

                **⚠ Never use ``source`` or ``target`` as attr keys** — the
                NetworkX node-link serialization format (`nx.node_link_data`)
                reserves those names for edge endpoints; any edge attribute
                named ``source`` or ``target`` is silently destroyed on
                save/load round-trip.

        Raises:
            KeyError: If the edge ``(caller_id, callee_id)`` does not exist in
                the graph.  Callers should check ``graph.has_edge`` first.
        """
        # Normalize so Windows backslash ids don't cause KeyError when the
        # graph was written with forward-slash ids (or vice-versa) (#47).
        self.graph.edges[
            normalize_path(caller_id), normalize_path(callee_id), "calls"
        ].update(attrs)
        self._bump_version()

    def add_relationship_edge(self, edge: "RelationshipEdge") -> None:
        """
        Add a relationship edge to the graph.

        This is the new unified method for adding any type of relationship edge.
        It replaces add_call_edge().

        Args:
            edge: RelationshipEdge object with all relationship data

        Example:
            >>> from chunking.relationships.relationship_types import RelationshipEdge, RelationshipType
            >>> edge = RelationshipEdge(
            ...     source_id="child.py:1-10:class:Child",
            ...     target_name="Parent",
            ...     relationship_type=RelationshipType.INHERITS,
            ...     line_number=1
            ... )
            >>> graph_storage.add_relationship_edge(edge)
        """
        # Normalize source_id path separators to forward slashes (cross-platform)
        normalized_source = normalize_path(edge.source_id)

        # Create lightweight node for target_name if it doesn't exist
        # This enables queries like get_callers("BaseRelationshipExtractor") to work
        #
        # Background: Edges use symbol names as targets (e.g., "BaseRelationshipExtractor")
        # but only full chunk_ids exist as nodes initially. Without target name nodes,
        # queries fail silently because NetworkX checks "if node in graph" before traversing.
        #
        # Solution: Create lightweight "symbol_name" nodes that serve as query endpoints.
        # These nodes have minimal metadata and are flagged with is_target_name=True.
        if edge.target_name not in self.graph:
            self.graph.add_node(
                edge.target_name,
                **{
                    NODE_ATTR_NAME: edge.target_name,
                    NODE_ATTR_TYPE: NODE_TYPE_SYMBOL_NAME,  # Distinguish from full chunk nodes
                    NODE_ATTR_IS_TARGET_NAME: True,  # Flag for query filtering if needed
                    NODE_ATTR_FILE: "",  # Unknown file (symbol might be external or not yet indexed)
                    NODE_ATTR_LANGUAGE: "",  # Unknown language
                },
            )

        # Add edge to graph with all attributes.
        # key=relationship_type: dedups within-type, preserves parallel edges across types.
        self.graph.add_edge(
            normalized_source,
            edge.target_name,
            key=edge.relationship_type.value,
            **{
                EDGE_ATTR_TYPE: edge.relationship_type.value,
                EDGE_ATTR_LINE: edge.line_number,
                EDGE_ATTR_CONFIDENCE: edge.confidence,
            },
            **edge.metadata,  # Include all additional metadata
        )
        self._bump_version()

    def get_callers(self, chunk_id: str) -> list[str]:
        """
        Get all functions that call this function.

        Args:
            chunk_id: Chunk ID to find callers for

        Returns:
            List of caller chunk IDs
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Query path normalization mismatch
        normalized_chunk_id = normalize_path(chunk_id)

        # Debug logging for relationship queries
        self.logger.debug(
            f"[GET_CALLERS] {chunk_id} → normalized: {normalized_chunk_id}"
        )
        self.logger.debug(
            f"  [GET_CALLERS] Node exists: {normalized_chunk_id in self.graph}, Total nodes: {self.graph.number_of_nodes()}"
        )

        if normalized_chunk_id not in self.graph:
            self.logger.debug("  [GET_CALLERS] → Node not found, returning []")
            return []

        # In a directed graph, predecessors are callers
        predecessors = list(self.graph.predecessors(normalized_chunk_id))
        self.logger.debug(
            f"  [GET_CALLERS] → Found {len(predecessors)} predecessors: {predecessors[:3] if predecessors else '[]'}..."
        )
        return predecessors

    def get_callees(self, chunk_id: str) -> list[str]:
        """
        Get all functions called by this function.

        Args:
            chunk_id: Chunk ID to find callees for

        Returns:
            List of callee chunk IDs or names
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Query path normalization mismatch
        normalized_chunk_id = normalize_path(chunk_id)

        if normalized_chunk_id not in self.graph:
            return []

        # In a directed graph, successors are callees
        return list(self.graph.successors(normalized_chunk_id))

    def _traverse_neighbors(
        self,
        normalized_chunk_id: str,
        relation_types: list[str],
        max_depth: int,
        exclude_import_categories: list[str] | None,
        edge_weights: dict[str, float] | None,
        min_confidence: float,
        confidence_weighting: bool,
    ) -> Iterator[str]:
        """Shared BFS/priority traversal, yielding each neighbor exactly once
        at first discovery.

        This is the single generator behind both ``get_neighbors`` (collects
        the yielded IDs into a ``set``) and ``get_neighbors_ranked`` (keeps
        them as an ordered ``list``) — the two callers can never drift apart
        on *which* nodes are reachable because they share this one walk.

        Unweighted mode (``edge_weights is None``) yields in BFS level order
        (queue pop order). Weighted mode yields in priority-queue pop order
        (higher edge-type weight, optionally scaled by ``confidence_weighting``,
        expands first). Both orders are deterministic given a fixed graph and
        fixed edge-iteration order (see ``_iter_matching_neighbors``) — no
        ``set`` iteration is involved in either path.
        """
        if edge_weights is None:
            # Unweighted BFS (original behavior, backward compatible)
            queue = deque([(normalized_chunk_id, 0)])
            visited = {normalized_chunk_id}

            while queue:
                current_id, depth = queue.popleft()
                if depth >= max_depth:
                    continue
                for neighbor, edge_type, edge_data in self._iter_matching_neighbors(
                    current_id, relation_types, exclude_import_categories
                ):
                    if (
                        min_confidence > 0.0
                        and self._edge_confidence(edge_data, edge_type) < min_confidence
                    ):
                        continue  # Drop this edge; neighbor may arrive via another
                    if neighbor not in visited:
                        visited.add(neighbor)
                        yield neighbor
                        queue.append((neighbor, depth + 1))

        else:
            # Weighted BFS using priority queue (higher weight = higher priority)
            # Priority queue format: (-weight, counter, chunk_id, depth)
            # Use negative weight so heapq min-heap becomes max-heap for weights
            counter = 0  # Tie-breaker for equal weights
            pq = [(0.0, counter, normalized_chunk_id, 0)]  # Start node has priority 0
            visited = {normalized_chunk_id}

            while pq:
                _neg_weight, _, current_id, depth = heapq.heappop(pq)
                if depth >= max_depth:
                    continue
                for neighbor, edge_type, edge_data in self._iter_matching_neighbors(
                    current_id, relation_types, exclude_import_categories
                ):
                    confidence = self._edge_confidence(edge_data, edge_type)
                    if min_confidence > 0.0 and confidence < min_confidence:
                        continue  # Drop this edge; neighbor may arrive via another
                    if neighbor not in visited:
                        visited.add(neighbor)
                        yield neighbor
                        # Get weight for the forward edge type (not reverse)
                        weight = edge_weights.get(edge_type, 0.5)
                        if confidence_weighting:
                            weight *= confidence
                        counter += 1
                        heapq.heappush(pq, (-weight, counter, neighbor, depth + 1))

    def get_neighbors(
        self,
        chunk_id: str,
        relation_types: list[str] | None = None,
        max_depth: int = 1,
        exclude_import_categories: list[str] | None = None,
        edge_weights: dict[str, float] | None = None,
        min_confidence: float = 0.0,
        confidence_weighting: bool = False,
    ) -> set[str]:
        """
        Get all related chunks within max_depth hops.

        Args:
            chunk_id: Starting chunk ID
            relation_types: Types of relations to follow (e.g., ["calls", "called_by", "inherits", "imports"])
                Supports all 21 relationship types. Use "_by" suffix for reverse direction
                (e.g., "called_by", "imported_by", "inherited_by")
            max_depth: Maximum graph traversal depth
            exclude_import_categories: Categories to exclude for "imports" edges
                (e.g., ["stdlib", "third_party"] to filter out noise)
            edge_weights: Optional edge-type weights for weighted BFS (higher weight = higher priority).
                When None, uses unweighted BFS (default behavior). When provided, uses priority queue
                to expand higher-weight edges first.
            min_confidence: Drop edges whose confidence (see
                :func:`edge_confidence`) falls below this floor (both BFS
                modes). Resolver-verified edges use their float
                ``resolver_confidence``; legacy-tagged ``calls`` edges
                ("exact"/"ambiguous"/"recovered") and untagged ``calls`` edges
                resolve to 0.7/0.5 via :data:`AST_CONFIDENCE_BY_TAG`; edges
                with no confidence signal at all (non-call relationship
                types) default to 1.0 and always survive. Default 0.0 = no-op
                (confidence is never read, so this is a true no-op regardless
                of edge_confidence's mapping). Drops edges, not nodes — a
                neighbor also reachable through a surviving edge is still
                returned.
            confidence_weighting: Weighted BFS only — multiply each edge's
                type-weight by its resolved confidence (see
                :func:`edge_confidence`) so unvalidated (ambiguous-AST) edges
                stop competing equally with resolver-validated ones for
                expansion priority. Default False = no-op.

        Returns:
            Set of related chunk IDs. Order is not preserved — callers that
            truncate the result (e.g. ``list(neighbors)[:n]``) get Python's
            set-iteration order, which is stable within one process but not
            guaranteed across processes/graph states. Use
            :meth:`get_neighbors_ranked` when truncation needs to be
            deterministic and priority-ordered instead.
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Query path normalization mismatch
        normalized_chunk_id = normalize_path(chunk_id)

        if normalized_chunk_id not in self.graph:
            return set()

        # Default to both directions of call relationships for backward compatibility
        if relation_types is None:
            relation_types = ["calls", "called_by"]

        return set(
            self._traverse_neighbors(
                normalized_chunk_id,
                relation_types,
                max_depth,
                exclude_import_categories,
                edge_weights,
                min_confidence,
                confidence_weighting,
            )
        )

    def get_neighbors_ranked(
        self,
        chunk_id: str,
        relation_types: list[str] | None = None,
        max_depth: int = 1,
        exclude_import_categories: list[str] | None = None,
        edge_weights: dict[str, float] | None = None,
        min_confidence: float = 0.0,
        confidence_weighting: bool = False,
    ) -> list[str]:
        """Like :meth:`get_neighbors`, but returns neighbors in discovery/
        priority order instead of an unordered ``set``.

        Shares the exact same traversal (:meth:`_traverse_neighbors`) as
        ``get_neighbors``, so ``set(get_neighbors_ranked(...)) ==
        get_neighbors(...)`` always holds for identical arguments — only the
        return type differs. Use this when a caller truncates the result
        (``result[:n]``): unweighted BFS order is level order (closer nodes
        first); weighted order is edge-type-weight priority (optionally
        scaled by ``confidence_weighting``). Both are deterministic given a
        fixed graph, unlike truncating ``list(get_neighbors(...))[:n]``,
        which depends on Python's set-iteration order.

        Args: see :meth:`get_neighbors`.

        Returns:
            List of related chunk IDs in traversal order, each appearing once.
        """
        # Normalize path separators to forward slashes for consistent lookup
        normalized_chunk_id = normalize_path(chunk_id)

        if normalized_chunk_id not in self.graph:
            return []

        # Default to both directions of call relationships for backward compatibility
        if relation_types is None:
            relation_types = ["calls", "called_by"]

        return list(
            self._traverse_neighbors(
                normalized_chunk_id,
                relation_types,
                max_depth,
                exclude_import_categories,
                edge_weights,
                min_confidence,
                confidence_weighting,
            )
        )

    @staticmethod
    def _edge_confidence(edge_data: dict, edge_type: "str | None" = None) -> float:
        """Resolver confidence of an edge for traversal decisions.

        Thin delegate to the module-level :func:`edge_confidence`, applying
        this layer's own policy for the "unknown" case: **permissive** —
        default to 1.0 so an edge with no confidence signal is never silently
        pruned by ``min_confidence`` and traverses exactly as before this
        helper existed. This is deliberately different from the 0.5 default
        used by ``relationship_analyzer`` (display ordering) and the 0.0
        default used by ``result_view`` (caller-hint ranking) — each layer's
        risk from misjudging an unknown edge is different, so each keeps its
        own default rather than sharing one magic constant.
        """
        confidence = edge_confidence(edge_data, edge_type)
        return confidence if confidence is not None else 1.0

    def _iter_matching_neighbors(
        self,
        current_id: str,
        relation_types: list[str],
        exclude_import_categories: list[str] | None,
    ) -> Iterator[tuple[str, str, dict]]:
        """Yield ``(neighbor_id, edge_type, edge_data)`` for each matching edge of ``current_id``.

        Forward (outgoing) edges are yielded first, then reverse (incoming) edges — the
        same order the BFS bodies in :meth:`get_neighbors` relied on.  ``edge_type`` is
        always the *forward* (stored) relationship type, so callers can compute edge
        weights from it (preserving the "weight for the forward edge type, not reverse"
        invariant used by the weighted BFS).  ``edge_data`` is the edge's attribute
        dict, so callers can additionally read per-edge attributes such as
        ``resolver_confidence`` (confidence-weighted traversal) without re-querying.

        This is the single source of truth for edge-type resolution, requested-type
        matching, and the ``imports`` exclusion filter that was previously duplicated
        across four blocks in :meth:`get_neighbors`.

        Args:
            current_id: The node whose edges are iterated.
            relation_types: Accepted forward and reverse relation type names.
            exclude_import_categories: If set, ``imports`` edges whose import category
                is in this list are skipped (same semantics as :meth:`_should_exclude_edge`).
        """
        # Forward (outgoing) relationships — forward edge_type matched directly
        for _, target, edge_data in self.graph.out_edges(current_id, data=True):
            edge_type = edge_relation_type(edge_data)
            if edge_type and edge_type in relation_types:
                if (
                    edge_type == "imports"
                    and exclude_import_categories
                    and self._should_exclude_edge(
                        current_id,
                        target,
                        exclude_import_categories,
                        edge_data=edge_data,
                    )
                ):
                    continue
                yield target, edge_type, edge_data
        # Reverse (incoming) relationships — reverse type matched, forward type yielded
        for source, _, edge_data in self.graph.in_edges(current_id, data=True):
            edge_type = edge_relation_type(edge_data)
            reverse_type = (
                self._get_reverse_relation_type(edge_type) if edge_type else None
            )
            if edge_type and reverse_type and reverse_type in relation_types:
                if (
                    edge_type == "imports"
                    and exclude_import_categories
                    and self._should_exclude_edge(
                        source,
                        current_id,
                        exclude_import_categories,
                        edge_data=edge_data,
                    )
                ):
                    continue
                yield source, edge_type, edge_data

    def _get_reverse_relation_type(self, relation_type: str) -> str:
        """
        Get the reverse name for a relationship type.

        Args:
            relation_type: Forward relationship type (e.g., "calls", "imports", "inherits")

        Returns:
            Reverse relationship type (e.g., "called_by", "imported_by", "inherited_by")

        Note:
            Most verb-based types need past participle form + "_by".
            Special irregular forms are handled explicitly.
        """
        # Delegate to the single owner of the reverse-relation mapping.
        return get_reverse_relation(relation_type)

    def _should_exclude_edge(
        self,
        source_id: str,
        target_id: str,
        exclude_categories: list[str],
        edge_data: "dict[str, Any] | None" = None,
    ) -> bool:
        """
        Check if edge should be excluded based on import category.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            exclude_categories: Categories to exclude (e.g., ["stdlib", "third_party"])
            edge_data: Pre-fetched edge attrs dict for the specific traversed edge.
                When provided (the normal path from ``_iter_matching_neighbors``) this
                data is used directly, avoiding a second graph lookup and ensuring the
                correct parallel edge is checked regardless of the edge's dict key.
                When omitted, falls back to a keyed lookup on the "imports" edge.

        Returns:
            True if edge should be excluded, False otherwise
        """
        if edge_data is None:
            # Fallback: keyed lookup — only used by callers that don't have edge_data.
            edge_data = self.get_edge_data(
                source_id, target_id, relationship_type="imports"
            )
        if not edge_data:
            return False

        # Type guard — the caller may pass any edge; only imports edges carry categories.
        edge_type = edge_relation_type(edge_data)
        if edge_type != "imports":
            return False

        # Check import category
        import_category = edge_data.get("metadata", {}).get("import_category")
        if not import_category:
            # Fallback: check if import_category is a direct edge attribute
            import_category = edge_data.get("import_category")

        if import_category in exclude_categories:
            self.logger.debug(
                f"Excluding {edge_type} edge {source_id} -> {target_id} "
                f"(category: {import_category})"
            )
            return True

        return False

    def get_node_data(self, chunk_id: str) -> dict[str, Any] | None:
        """
        Get node metadata.

        Args:
            chunk_id: Chunk ID

        Returns:
            Node data dictionary or None if not found
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Query path normalization mismatch
        normalized_chunk_id = normalize_path(chunk_id)

        if normalized_chunk_id not in self.graph:
            return None

        return dict(self.graph.nodes[normalized_chunk_id])

    def get_nodes_by_name(self, name: str) -> list[str]:
        """Get chunk_ids whose ``name`` attribute equals *name* (O(1) lookup).

        Uses the secondary ``_name_index`` maintained by :meth:`add_node`.

        Args:
            name: Symbol name to look up (e.g. ``"my_function"``).

        Returns:
            List of matching chunk_ids (empty list if none found).
        """
        return list(self._name_index.get(name, []))

    def get_edge_data(
        self,
        caller_id: str,
        callee_id: str,
        relationship_type: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get edge metadata with validation and normalization.

        On a MultiDiGraph a (u,v) pair may carry multiple parallel edges, one per
        relationship type.  When *relationship_type* is given, returns data for that
        specific edge (or None if it does not exist).  When omitted, returns the
        **primary** edge — the one with the highest resolver_confidence; "calls" is
        preferred on ties — preserving the single-dict contract for existing callers.

        Non-"calls" relationship edges all default resolver_confidence to 0.0, so ties
        between them fall back to insertion order — whichever extractor ran first in
        chunking/relationships/relationship_extractors/registry.py's priority list wins.
        This primary-edge selection is a deliberate, single-dict-returning contract for
        callers that want one representative edge (e.g. path display in
        ``_build_path_result``). Callers that need every relationship a pair carries —
        notably ``GraphQueryEngine._traverse_outbound``/``_traverse_inbound``, which
        used to silently drop non-primary types before applying a ``relation_types``
        filter — use :meth:`get_all_edge_data` instead and fan out over its result.

        Args:
            caller_id: Caller chunk ID (source node)
            callee_id: Callee chunk ID (target node)
            relationship_type: If provided, look up this specific edge key (e.g.
                "calls", "imports").  If None, return the primary (highest-confidence)
                edge.

        Returns:
            Edge data dictionary with normalized keys, or None if edge not found.
            Guaranteed to have 'relationship_type' and 'line_number' fields (with defaults).
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Query path normalization mismatch
        normalized_caller = normalize_path(caller_id)
        normalized_callee = normalize_path(callee_id)

        if not self.graph.has_edge(normalized_caller, normalized_callee):
            return None

        if relationship_type is not None:
            # Keyed lookup — native get_edge_data returns the flat attrs dict for this key
            raw = self.graph.get_edge_data(
                normalized_caller, normalized_callee, key=relationship_type
            )
            if raw is None:
                return None
            edge_data = dict(raw)
        else:
            # No key: pick the primary edge — highest resolver_confidence, prefer "calls"
            all_edges = self.graph.get_edge_data(normalized_caller, normalized_callee)
            if not all_edges:
                return None

            def _primary_key(item: tuple) -> tuple:
                k, attrs = item
                return (attrs.get("resolver_confidence", 0.0), k == "calls")

            edge_data = dict(max(all_edges.items(), key=_primary_key)[1])

        # Validate and normalize required fields
        # Support both old ('type', 'line') and new ('relationship_type', 'line_number') keys

        # 1. Normalize relationship_type
        if "relationship_type" not in edge_data:
            if "type" in edge_data:
                edge_data["relationship_type"] = edge_data["type"]
            else:
                self.logger.warning(
                    f"Edge {caller_id} → {callee_id} missing relationship type, defaulting to 'calls'"
                )
                edge_data["relationship_type"] = "calls"

        # 2. Normalize line_number
        if "line_number" not in edge_data:
            edge_data["line_number"] = edge_data.get("line", 0)

        # 3. Ensure confidence exists (optional but useful)
        if "confidence" not in edge_data:
            edge_data["confidence"] = 1.0  # Default to full confidence

        # 4. Validate data types
        try:
            # Ensure line_number is int
            edge_data["line_number"] = int(edge_data["line_number"])
        except (ValueError, TypeError):
            self.logger.warning(
                f"Edge {caller_id} → {callee_id} has invalid line_number, defaulting to 0"
            )
            edge_data["line_number"] = 0

        conf = edge_data["confidence"]
        if isinstance(conf, str) and conf in _LEGACY_CONFIDENCE_TAGS:
            # Known legacy string tag written by the in-house call extractor.
            # Downstream enrichers (_enrich_callers/_enrich_callees) consume this
            # as a string — do not coerce to float.
            pass
        else:
            try:
                # Ensure numeric confidence edges carry a float (e.g. resolver_confidence
                # paths that also mirror to "confidence" in the future).
                edge_data["confidence"] = float(conf)
            except (ValueError, TypeError):
                self.logger.warning(
                    f"Edge {caller_id} → {callee_id} has invalid confidence, defaulting to 1.0"
                )
                edge_data["confidence"] = 1.0

        return edge_data

    def get_all_edge_data(self, caller_id: str, callee_id: str) -> list[dict[str, Any]]:
        """Return normalized edge data for every parallel edge between caller and callee.

        On a MultiDiGraph there may be more than one edge per (u,v) pair — one per
        relationship type (e.g., "calls" *and* "imports" on the same node pair).
        Returns an empty list when no edge exists.

        Used by ``GraphQueryEngine._traverse_outbound``/``_traverse_inbound`` to
        populate ``RelationshipEntry.parallel_edges`` so every relationship type
        between a pair is visible downstream instead of only the primary one
        :meth:`get_edge_data` would return.

        Args:
            caller_id: Caller chunk ID (source node).
            callee_id: Callee chunk ID (target node).

        Returns:
            List of normalized edge-data dicts, one per parallel edge.  May be empty.
        """
        normalized_caller = normalize_path(caller_id)
        normalized_callee = normalize_path(callee_id)

        all_edges = self.graph.get_edge_data(normalized_caller, normalized_callee)
        if not all_edges:
            return []

        results = []
        for key in all_edges:
            edge = self.get_edge_data(caller_id, callee_id, relationship_type=key)
            if edge is not None:
                results.append(edge)
        return results

    def save(self) -> None:
        """
        Save graph to JSON file.

        Uses NetworkX's node_link_data format for efficient serialization.
        """
        try:
            # Stamp schema version so load() can detect and coerce old DiGraph JSON.
            self.graph.graph["schema_version"] = 2

            # Convert graph to JSON-serializable format
            # Using edges="edges" for NetworkX 3.6+ forward compatibility
            # pyrefly: ignore [missing-attribute]
            data = nx.node_link_data(self.graph, edges="edges")

            # Save to file (atomic write: tmp → os.replace)
            write_json_atomic(self.graph_path, data)

            self.logger.info(
                f"Saved call graph: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges → {self.graph_path}"
            )

        except Exception as e:
            self.logger.error(f"Failed to save graph: {e}")
            raise

    def load(self) -> bool:
        """
        Load graph from JSON file.

        Returns:
            True if graph was loaded, False if file doesn't exist
        """
        if not self.graph_path.exists():
            self.logger.info(f"No existing graph found at {self.graph_path}")
            return False

        try:
            with open(self.graph_path) as f:
                data = json.load(f)

            # Reconstruct graph from JSON
            # Using edges="edges" for NetworkX 3.6+ forward compatibility
            self.graph = nx.node_link_graph(data, directed=True, edges="edges")

            # Coerce pre-multigraph JSON (schema_version absent / < 2) written by
            # an older DiGraph-based release.  Each old single edge becomes key=0;
            # new parallel edges accumulate normally on the next reindex.
            if not self.graph.is_multigraph():
                self.graph = nx.MultiDiGraph(self.graph)

            # Rebuild name index from loaded graph so get_nodes_by_name() works.
            # Node IDs are unique, so no duplicate check needed.
            self._name_index = {}
            for node_id, attrs in self.graph.nodes(data=True):
                node_name = attrs.get("name")
                if node_name:
                    if node_name not in self._name_index:
                        self._name_index[node_name] = []
                    self._name_index[node_name].append(node_id)

            self.logger.info(
                f"Loaded call graph: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges ← {self.graph_path}"
            )

            self._bump_version()
            return True

        except (OSError, ValueError, KeyError, TypeError, nx.NetworkXError) as e:
            self.logger.error(f"Failed to load graph: {e}", exc_info=True)
            # Initialize empty graph on error
            # pyrefly: ignore [missing-attribute]
            self.graph = nx.MultiDiGraph()
            self._bump_version()
            return False

    def clear(self) -> None:
        """Clear all nodes and edges from the graph and remove the backing JSON file.

        Deletes the on-disk call_graph.json so that subsequent CodeGraphStorage
        re-initialization does not reload stale phantom nodes from a previous index.
        """
        self.graph.clear()
        self._name_index.clear()
        self._bump_version()
        if self.graph_path.exists():
            self.graph_path.unlink()
            self.logger.info("Cleared call graph (on-disk file deleted)")
        else:
            self.logger.info("Cleared call graph")

    def remove_file_nodes(self, file_path: str) -> int:
        """Remove all graph nodes (and their incident edges) belonging to a file.

        Intended for incremental reindex: prunes stale nodes when a file's chunks
        are deleted from the metadata store so the call graph and the metadata
        store stay in sync.  Without this, old node IDs (which embed line ranges)
        survive incremental reindex and cause ``Chunk not found`` errors in
        ``find_connections``.

        Args:
            file_path: Source file path — may use any path separator; normalized
                internally to forward slashes to match the chunk_id format used by
                the chunker (``path:start-end:type:name``).

        Returns:
            Number of nodes removed.
        """
        # Normalize to forward slashes, matching chunk_id construction in chunker
        normalized = normalize_path(file_path).rstrip("/")
        prefix = normalized + ":"

        # Collect IDs first to avoid mutating the graph during iteration
        to_remove = [n for n in self.graph.nodes() if n.startswith(prefix)]

        for node_id in to_remove:
            # Clean _name_index before removing the node
            node_name = self.graph.nodes[node_id].get("name")
            if node_name and node_name in self._name_index:
                with contextlib.suppress(ValueError):
                    self._name_index[node_name].remove(node_id)
                if not self._name_index[node_name]:
                    del self._name_index[node_name]
            # networkx automatically removes all incident edges when a node is removed
            self.graph.remove_node(node_id)

        if to_remove:
            self._bump_version()
            self.logger.debug(
                f"[GRAPH_PRUNE] Removed {len(to_remove)} nodes for '{normalized}'"
            )
        return len(to_remove)

    def get_stats(self) -> dict[str, Any]:
        """
        Get graph statistics.

        Returns:
            Dictionary with graph statistics
        """
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "is_directed": self.graph.is_directed(),
            "is_multigraph": self.graph.is_multigraph(),
            "schema_version": self.graph.graph.get("schema_version", 1),
            "storage_path": str(self.graph_path),
            "exists_on_disk": self.graph_path.exists(),
        }

    def __len__(self) -> int:
        """Return number of nodes in graph.

        WARNING: this class defines __len__ but not __bool__, so Python falls
        back to `len(obj) != 0` for `bool(obj)`. A valid instance with an empty
        (or just-cleared) graph is therefore falsy. Callers checking for
        *existence* must use `is not None`, not truthiness — see the
        clear_index() re-sync bug this caused in hybrid_searcher.py.
        """
        return self.graph.number_of_nodes()

    def __contains__(self, chunk_id: str) -> bool:
        """Check if chunk_id is in graph."""
        # Normalize for cross-platform path consistency (#47).
        return normalize_path(chunk_id) in self.graph

    # pyrefly: ignore [missing-attribute]
    def get_graph(self) -> "nx.MultiDiGraph":
        """Expose raw NetworkX MultiDiGraph for external algorithms (e.g., PPR).

        Returns:
            The underlying NetworkX multi-directed graph.
        """
        return self.graph
