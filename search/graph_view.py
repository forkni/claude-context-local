"""Read adapter that owns all NetworkX access for the search/ subsystem.

`search/` modules MUST NOT touch `graph_storage.graph` or call any `nx.*`
functions directly.  Route everything through this adapter instead so that:
  - The node/edge attribute schema ("name", "type", "file", "line") is
    defined in exactly one place.
  - NetworkX API details are hidden behind typed records.
  - Tests can supply a small hand-built fake instead of a full CodeGraphStorage.

Two callers exist today:
  - search/subgraph_extractor.py  (node lookup, edge traversal, SCC topology)
  - search/ego_graph_retriever.py (_expand_via_ppr — Personalized PageRank)

See ADR-0001/0005/0006 for constraints on the graph/ ↔ search/ layering.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import networkx as nx
from networkx.exception import PowerIterationFailedConvergence as PPRConvergenceError

from graph.schema import (
    EDGE_ATTR_LINE,
    EDGE_ATTR_TYPE,
    NODE_ATTR_FILE,
    NODE_ATTR_NAME,
    NODE_ATTR_TYPE,
)
from search.chunk_id import extract_name as _extract_name


if TYPE_CHECKING:
    from graph.graph_storage import CodeGraphStorage

# Re-export so callers never need to import networkx directly
__all__ = [
    "EdgeRecord",
    "GraphView",
    "NodeRecord",
    "PPRConvergenceError",
]


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typed records — the *access* layer (distinct from SubgraphNode/SubgraphEdge
# which are the *serialisation* layer for MCP consumers)
# ---------------------------------------------------------------------------

# Constants imported from graph.schema — re-declared here for local reference
# and backward compatibility (external code that imported them from graph_view).
# NODE_ATTR_NAME, NODE_ATTR_TYPE, NODE_ATTR_FILE, EDGE_ATTR_TYPE, EDGE_ATTR_LINE


@dataclass(frozen=True, slots=True)
class NodeRecord:
    """Decoded node attributes from the code graph."""

    chunk_id: str
    name: str  # symbol name (e.g. "CodeEmbedder", "IntelligentSearcher.__init__")
    kind: str  # chunk kind (function, class, method, split_block, …)
    file: str  # relative forward-slash file path


@dataclass(frozen=True, slots=True)
class EdgeRecord:
    """Decoded edge attributes from the code graph."""

    source: str  # source chunk_id
    target: str  # target chunk_id (or bare symbol name for unresolved calls)
    rel_type: str  # relationship kind (calls, imports, inherits, …)
    line: int  # call-site line number (0 if unknown)


# ---------------------------------------------------------------------------
# GraphView adapter
# ---------------------------------------------------------------------------


class GraphView:
    """Read-only adapter over CodeGraphStorage's NetworkX MultiDiGraph.

    Owns the attribute-name schema and all direct NX calls so no `search/`
    module needs to import networkx or access `graph_storage.graph` directly.

    Thread-safety: GraphView is stateless (all methods read from the shared
    NX graph).  It obeys the same coarse-lock contract as CodeGraphStorage
    (ADR-0006): callers are responsible for acquiring state._lock before
    passing a storage instance that may be torn down concurrently.
    """

    def __init__(self, storage: "CodeGraphStorage") -> None:
        """Wrap a CodeGraphStorage instance.

        Args:
            storage: The live CodeGraphStorage; its .graph attribute is
                accessed on every call so the view always reflects the
                current graph snapshot.
        """
        self._storage = storage

    # ------------------------------------------------------------------
    # Internal: raw graph access (all NX access goes through here)
    # ------------------------------------------------------------------

    @property
    def _graph(self) -> nx.MultiDiGraph:
        """Return the underlying NetworkX graph."""
        return self._storage.graph  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def contains(self, chunk_id: str) -> bool:
        """Return True if *chunk_id* is a node in the graph."""
        return chunk_id in self._graph

    def is_empty(self) -> bool:
        """Return True if the graph has no nodes."""
        return len(self._graph) == 0

    def has_edge(self, source: str, target: str) -> bool:
        """Return True if any edge exists from *source* to *target*."""
        return self._graph.has_edge(source, target)

    def node(self, chunk_id: str) -> NodeRecord | None:
        """Return decoded node attributes, or None if the node is absent.

        The *file* field is derived from the chunk_id itself (which encodes
        the relative path) rather than the stored ``file`` attribute, which
        may be an absolute path.
        """
        node_data = self._graph.nodes.get(chunk_id)
        if not node_data:
            return None
        # chunk_id encodes the relative path; prefer it over stored attribute
        file_path = (
            chunk_id.split(":")[0]
            if ":" in chunk_id
            else node_data.get(NODE_ATTR_FILE, "")
        )
        return NodeRecord(
            chunk_id=chunk_id,
            name=node_data.get(NODE_ATTR_NAME, _extract_name(chunk_id) or chunk_id),
            kind=node_data.get(NODE_ATTR_TYPE, "unknown"),
            file=file_path,
        )

    def out_edges(self, chunk_id: str) -> list[EdgeRecord]:
        """Return outgoing edges from *chunk_id* as typed records.

        Handles MultiDiGraph parallel edges: each parallel edge becomes a
        separate EdgeRecord.

        Args:
            chunk_id: Source node.

        Returns:
            List of EdgeRecord (empty if node absent or has no out-edges).
        """
        if chunk_id not in self._graph:
            return []
        return [
            EdgeRecord(
                source=chunk_id,
                target=target,
                rel_type=edge_data.get(EDGE_ATTR_TYPE, "calls"),
                line=edge_data.get(EDGE_ATTR_LINE, 0),
            )
            for _, target, edge_data in self._graph.out_edges(chunk_id, data=True)
        ]

    def in_edges(self, chunk_id: str) -> list[EdgeRecord]:
        """Return incoming edges to *chunk_id* as typed records.

        Args:
            chunk_id: Target node.

        Returns:
            List of EdgeRecord (empty if node absent or has no in-edges).
        """
        if chunk_id not in self._graph:
            return []
        return [
            EdgeRecord(
                source=source,
                target=chunk_id,
                rel_type=edge_data.get(EDGE_ATTR_TYPE, "calls"),
                line=edge_data.get(EDGE_ATTR_LINE, 0),
            )
            for source, _, edge_data in self._graph.in_edges(chunk_id, data=True)
        ]

    def induced_topology(self, chunk_ids: list[str]) -> list[str]:
        """Return a topological ordering over an induced subgraph.

        Uses SCC condensation when the induced subgraph has cycles (mutually
        recursive code).  Within an SCC the order is arbitrary (all members
        are mutually dependent).

        Args:
            chunk_ids: Nodes to include in the induced subgraph.

        Returns:
            Topologically sorted list (dependencies before their users).
        """
        induced = self._graph.subgraph(chunk_ids)
        try:
            return list(nx.topological_sort(induced))
        except nx.NetworkXUnfeasible:
            # Cycles detected — use SCC condensation
            logger.debug(
                "[GRAPH_VIEW] Cycles in induced subgraph; using SCC condensation"
            )
            scc_graph = nx.condensation(induced)
            scc_order = list(nx.topological_sort(scc_graph))
            result = []
            for scc_id in scc_order:
                scc_members = scc_graph.nodes[scc_id].get("members", [])
                result.extend(scc_members)
            return result

    def personalized_pagerank(
        self,
        personalization: dict[str, float],
        alpha: float,
        *,
        max_iter: int = 100,
        tol: float = 1e-6,
    ) -> dict[str, float]:
        """Run Personalized PageRank over the full graph.

        Raises:
            nx.PowerIterationFailedConvergence: if PPR does not converge;
                caller should fall back to BFS (as _expand_via_ppr does).

        Args:
            personalization: Seed distribution — maps anchor node_ids to
                initial probability mass.
            alpha: Damping factor (fraction of probability mass kept at each
                step; 1 - alpha teleports back to seed).
            max_iter: Maximum iterations.
            tol: Convergence tolerance.

        Returns:
            Dict mapping node_id -> PPR score.
        """
        return nx.pagerank(
            self._graph,
            alpha=alpha,
            personalization=personalization,
            max_iter=max_iter,
            tol=tol,
        )
