"""
Subgraph extraction for SSCG (Structural-Semantic Code Graph) integration.

Extracts induced subgraphs over search result chunk_ids from the code graph,
preserving typed edges, topological ordering, and community context.

Based on research:
- RepoGraph (ICLR 2025): Ego-graph retrieval with topological ordering
- LogicLens (arXiv 2601.10773): Entity nodes as functional bridges
- JSON Graph Format: Lightweight interchange for agent consumption
"""

import logging
from collections import Counter
from dataclasses import dataclass

import networkx as nx


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SubgraphNode:
    """A node in the extracted subgraph."""

    chunk_id: str
    name: str
    kind: str  # function, class, method, module...
    file: str
    community_id: int | None = None
    centrality: float | None = None
    is_search_result: bool = True  # False for ego-graph neighbors


@dataclass(slots=True)
class SubgraphEdge:
    """A typed edge in the extracted subgraph."""

    source: str  # chunk_id or symbol name
    target: str  # chunk_id or symbol name
    rel_type: str  # One of 21 RelationshipType values
    line: int = 0
    is_boundary: bool = False  # Edge pointing outside the result set


@dataclass
class SubgraphResult:
    """Complete subgraph extraction result with serialization."""

    nodes: list[SubgraphNode]
    edges: list[SubgraphEdge]
    topology_order: list[str]
    communities: dict[int, dict] | None = None

    def to_dict(self) -> dict:
        """Compact JSON serialization (JSON Graph Format inspired).

        Returns:
            dict with nodes, edges, topology_order, optional communities
        """
        result = {
            "nodes": [self._node_dict(n) for n in self.nodes],
            "edges": [self._edge_dict(e) for e in self.edges],
            "topology_order": self.topology_order,
        }
        if self.communities:
            result["communities"] = self.communities
        return result

    def _node_dict(self, n: SubgraphNode) -> dict:
        """Serialize a node, omitting optional empty fields."""
        d = {"id": n.chunk_id, "name": n.name, "kind": n.kind, "file": n.file}
        if n.community_id is not None:
            d["community"] = n.community_id
        if n.centrality is not None:
            d["centrality"] = round(n.centrality, 4)
        if not n.is_search_result:
            d["source"] = "ego_graph"
        return d

    def _edge_dict(self, e: SubgraphEdge) -> dict:
        """Serialize an edge, omitting optional empty fields."""
        d = {"src": e.source, "tgt": e.target, "rel": e.rel_type}
        if e.line:
            d["line"] = e.line
        if e.is_boundary:
            d["boundary"] = True
        return d


class SubgraphExtractor:
    """Extract induced subgraphs over search result chunk_ids.

    This is the core SSCG serialization layer that transforms the NetworkX
    DiGraph stored in CodeGraphStorage into a compact, agent-consumable format.
    """

    def __init__(self, graph_storage):
        """Initialize with a CodeGraphStorage instance.

        Args:
            graph_storage: CodeGraphStorage with the full code graph
        """
        self.graph_storage = graph_storage
        self.graph = graph_storage.graph
        self.project_root = getattr(graph_storage, "project_root", None)

    def extract_subgraph(
        self,
        chunk_ids: list[str],
        include_boundary_edges: bool = False,
        max_boundary_depth: int = 1,
        centrality_scores: dict[str, float] | None = None,
        ego_neighbor_ids: list[str] | None = None,
    ) -> SubgraphResult:
        """Extract the induced subgraph over the given chunk_ids.

        Algorithm:
        1. Collect result chunk_ids as node set
        2. For each node, iterate out_edges and in_edges
        3. If both endpoints are in node set → inter-edge (always included)
        4. If one endpoint is outside → boundary edge (optional)
        5. Build topological ordering (SCC condensation for cycles)
        6. Return SubgraphResult

        Args:
            chunk_ids: List of chunk_ids from search results
            include_boundary_edges: Include edges to nodes outside result set
            max_boundary_depth: Ignored for now (future: multi-hop boundary)
            centrality_scores: Optional dict mapping chunk_id -> centrality score
            ego_neighbor_ids: Optional list of ego-graph neighbor chunk_ids (marked with is_search_result=False)

        Returns:
            SubgraphResult with nodes, edges, topology_order
        """
        if not chunk_ids:
            return SubgraphResult(nodes=[], edges=[], topology_order=[])

        chunk_id_set = set(chunk_ids)
        nodes: list[SubgraphNode] = []
        edges: list[SubgraphEdge] = []

        # Build node list with metadata from graph
        for chunk_id in chunk_ids:
            node_data = self.graph.nodes.get(chunk_id, {})
            if not node_data:
                # Try to find the node (path normalization issues)
                logger.debug(f"[SUBGRAPH] Node {chunk_id} not found in graph")
                continue

            # Extract relative file path from chunk_id (format: "relative/path/file.py:lines:type:name")
            # chunk_id already uses relative forward-slash paths, so we can extract the file path directly
            file_path = (
                chunk_id.split(":")[0] if ":" in chunk_id else node_data.get("file", "")
            )

            # Create node with optional centrality score
            node = SubgraphNode(
                chunk_id=chunk_id,
                name=node_data.get(
                    "name", chunk_id.split(":")[-1] if ":" in chunk_id else chunk_id
                ),
                kind=node_data.get("type", "unknown"),
                file=file_path,
                is_search_result=True,
            )

            # Populate centrality if scores provided
            if centrality_scores:
                node.centrality = centrality_scores.get(chunk_id)

            nodes.append(node)

        # Add ego-graph neighbor nodes (is_search_result=False)
        if ego_neighbor_ids:
            for neighbor_id in ego_neighbor_ids:
                if neighbor_id in chunk_id_set:
                    continue  # Already a search result node, skip duplication

                node_data = self.graph.nodes.get(neighbor_id, {})
                if not node_data:
                    logger.debug(
                        f"[SUBGRAPH] Ego-graph neighbor {neighbor_id} not found in graph"
                    )
                    continue

                # Extract relative file path from chunk_id (same pattern as search result nodes)
                file_path = (
                    neighbor_id.split(":")[0]
                    if ":" in neighbor_id
                    else node_data.get("file", "")
                )

                # Create ego-graph neighbor node
                node = SubgraphNode(
                    chunk_id=neighbor_id,
                    name=node_data.get(
                        "name",
                        neighbor_id.split(":")[-1]
                        if ":" in neighbor_id
                        else neighbor_id,
                    ),
                    kind=node_data.get("type", "unknown"),
                    file=file_path,
                    is_search_result=False,  # KEY: marks as ego-graph neighbor
                )

                # Populate centrality if scores provided
                if centrality_scores:
                    node.centrality = centrality_scores.get(neighbor_id)

                nodes.append(node)

            # Expand chunk_id_set to include ego neighbors for edge discovery
            chunk_id_set.update(ego_neighbor_ids)

        # Extract edges between all nodes (search results + ego neighbors)
        # Cap boundary edges to avoid token explosion (max 3 per source node)
        MAX_BOUNDARY_PER_NODE = 3
        boundary_counts: dict[str, int] = {}

        # Convert ego_neighbor_ids to set for fast lookup
        ego_neighbor_id_set = set(ego_neighbor_ids) if ego_neighbor_ids else set()

        for chunk_id in chunk_id_set:
            if chunk_id not in self.graph:
                continue

            # Outgoing edges
            for _, target, edge_data in self.graph.out_edges(chunk_id, data=True):
                rel_type = edge_data.get("type", "calls")
                line = edge_data.get("line", 0)
                is_boundary = target not in chunk_id_set

                # Skip boundary edges from ego-graph neighbors (2+ hops from query = noise)
                if is_boundary and chunk_id in ego_neighbor_id_set:
                    continue

                # Cap boundary edges per source node
                if is_boundary:
                    boundary_counts[chunk_id] = boundary_counts.get(chunk_id, 0) + 1
                    if boundary_counts[chunk_id] > MAX_BOUNDARY_PER_NODE:
                        continue

                if not is_boundary or include_boundary_edges:
                    edges.append(
                        SubgraphEdge(
                            source=chunk_id,
                            target=target,
                            rel_type=rel_type,
                            line=line,
                            is_boundary=is_boundary,
                        )
                    )

            # Incoming edges (to avoid duplicates, only add if source is NOT in chunk_id_set)
            for source, _, edge_data in self.graph.in_edges(chunk_id, data=True):
                if source in chunk_id_set:
                    # Already captured in outgoing edges above
                    continue

                if include_boundary_edges:
                    rel_type = edge_data.get("type", "calls")
                    line = edge_data.get("line", 0)
                    edges.append(
                        SubgraphEdge(
                            source=source,
                            target=chunk_id,
                            rel_type=rel_type,
                            line=line,
                            is_boundary=True,
                        )
                    )

        # Build topological ordering (includes both search results and ego neighbors)
        all_ids = list(
            chunk_id_set
        )  # includes search results + ego neighbors if present
        topology_order = self._build_topology_order(all_ids)

        # Annotate nodes with community IDs and generate labels
        communities = self._annotate_communities(nodes)

        return SubgraphResult(
            nodes=nodes,
            edges=edges,
            topology_order=topology_order,
            communities=communities if communities else None,
        )

    def _build_topology_order(self, chunk_ids: list[str]) -> list[str]:
        """Build topological ordering of chunk_ids.

        Uses SCC condensation for cycles. Dependencies appear before their users.

        Args:
            chunk_ids: Chunk IDs to order

        Returns:
            Topologically sorted list of chunk_ids
        """
        # Extract induced subgraph
        induced = self.graph.subgraph(chunk_ids)

        try:
            # Try direct topological sort (works if DAG)
            return list(nx.topological_sort(induced))
        except nx.NetworkXUnfeasible:
            # Graph has cycles, use SCC condensation
            logger.debug("[SUBGRAPH] Cycles detected, using SCC condensation")

            # Create SCC-based DAG
            scc_graph = nx.condensation(induced)

            # Topological sort the condensation
            scc_order = list(nx.topological_sort(scc_graph))

            # Expand SCCs back to individual nodes
            # SCCs are stored in 'members' attribute of condensation nodes
            result = []
            for scc_id in scc_order:
                scc_members = scc_graph.nodes[scc_id].get("members", [])
                # Within an SCC, order doesn't matter (they're mutually recursive)
                result.extend(scc_members)

            return result

    def _annotate_communities(self, nodes: list[SubgraphNode]) -> dict[int, dict]:
        """Load community map and annotate nodes with community IDs.

        Args:
            nodes: List of SubgraphNode to annotate

        Returns:
            dict mapping community_id -> {label, count}
        """
        community_map = self.graph_storage.load_community_map()
        if not community_map:
            return {}

        communities: dict[int, list[str]] = {}
        for node in nodes:
            cid = community_map.get(node.chunk_id)
            if cid is not None:
                node.community_id = cid
                communities.setdefault(cid, []).append(node.chunk_id)

        # Generate heuristic labels from most common directory per community
        labels = self._generate_community_labels(communities)

        return {
            cid: {"label": labels.get(cid, f"cluster_{cid}"), "count": len(members)}
            for cid, members in communities.items()
        }

    def _generate_community_labels(
        self, communities: dict[int, list[str]]
    ) -> dict[int, str]:
        """Generate heuristic community labels from most common directory prefix.

        Args:
            communities: dict mapping community_id -> list of chunk_ids

        Returns:
            dict mapping community_id -> label string
        """
        labels = {}
        for cid, chunk_ids in communities.items():
            dirs = []
            for chunk_id in chunk_ids:
                # Extract file path from chunk_id (format: "file.py:lines:type:name")
                parts = chunk_id.replace("\\", "/").split(":")
                if parts:
                    file_path = parts[0]
                    path_parts = file_path.split("/")
                    # Use parent directory as label component
                    if len(path_parts) > 1:
                        dirs.append(path_parts[-2])
                    elif path_parts:
                        dirs.append(path_parts[0])

            if dirs:
                # Most common directory becomes the label
                most_common = Counter(dirs).most_common(1)
                if most_common:
                    labels[cid] = most_common[0][0]

        return labels
