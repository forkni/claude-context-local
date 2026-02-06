"""Tests for SSCG Phase 5: Ego-graph structure preservation in subgraphs.

This module tests that ego-graph neighbors are properly integrated into the
subgraph output with typed edges preserved, instead of being flattened.
"""

import unittest
from unittest.mock import Mock

import networkx as nx

from search.subgraph_extractor import SubgraphExtractor


class TestEgoGraphStructured(unittest.TestCase):
    """Test ego-graph structure preservation in SubgraphExtractor."""

    def setUp(self):
        """Create mock graph storage with search results + ego-graph neighbors."""
        self.mock_storage = Mock()

        # Create NetworkX DiGraph with 5 nodes:
        # - 2 search results: auth.py:login, auth.py:AuthService
        # - 2 ego-graph neighbors: db.py:query, session.py:create_session
        # - 1 boundary node: models.py:User
        self.graph = nx.DiGraph()

        # Add nodes with metadata
        nodes = {
            "auth.py:10-50:function:login": {
                "name": "login",
                "type": "function",
                "file": "auth.py",
            },
            "auth.py:55-80:class:AuthService": {
                "name": "AuthService",
                "type": "class",
                "file": "auth.py",
            },
            "db.py:5-20:function:query": {
                "name": "query",
                "type": "function",
                "file": "db.py",
            },
            "session.py:10-30:function:create_session": {
                "name": "create_session",
                "type": "function",
                "file": "session.py",
            },
            "models.py:40-60:class:User": {
                "name": "User",
                "type": "class",
                "file": "models.py",
            },
        }

        for chunk_id, attrs in nodes.items():
            self.graph.add_node(chunk_id, **attrs)

        # Add typed edges
        # Search result -> ego-graph neighbor (calls)
        self.graph.add_edge(
            "auth.py:10-50:function:login",
            "db.py:5-20:function:query",
            type="calls",
            line=25,
        )
        # Search result -> ego-graph neighbor (calls)
        self.graph.add_edge(
            "auth.py:10-50:function:login",
            "session.py:10-30:function:create_session",
            type="calls",
            line=30,
        )
        # Search result -> search result (calls)
        self.graph.add_edge(
            "auth.py:55-80:class:AuthService",
            "auth.py:10-50:function:login",
            type="calls",
            line=70,
        )
        # Search result -> boundary node (uses_type)
        self.graph.add_edge(
            "auth.py:10-50:function:login",
            "models.py:40-60:class:User",
            type="uses_type",
            line=15,
        )
        # Ego-graph neighbor -> ego-graph neighbor (calls)
        self.graph.add_edge(
            "db.py:5-20:function:query",
            "session.py:10-30:function:create_session",
            type="calls",
            line=12,
        )

        self.mock_storage.graph = self.graph
        self.mock_storage.project_root = None

        self.extractor = SubgraphExtractor(self.mock_storage)

    def test_ego_neighbors_in_subgraph(self):
        """Test that ego-graph neighbors are added to subgraph with is_search_result=False."""
        search_result_ids = [
            "auth.py:10-50:function:login",
            "auth.py:55-80:class:AuthService",
        ]
        ego_neighbor_ids = [
            "db.py:5-20:function:query",
            "session.py:10-30:function:create_session",
        ]

        result = self.extractor.extract_subgraph(
            chunk_ids=search_result_ids,
            ego_neighbor_ids=ego_neighbor_ids,
        )

        # Verify 4 nodes total (2 search results + 2 ego neighbors)
        self.assertEqual(len(result.nodes), 4)

        # Check search result nodes
        search_nodes = [n for n in result.nodes if n.is_search_result]
        self.assertEqual(len(search_nodes), 2)
        search_ids = {n.chunk_id for n in search_nodes}
        self.assertEqual(search_ids, set(search_result_ids))

        # Check ego-graph neighbor nodes
        ego_nodes = [n for n in result.nodes if not n.is_search_result]
        self.assertEqual(len(ego_nodes), 2)
        ego_ids = {n.chunk_id for n in ego_nodes}
        self.assertEqual(ego_ids, set(ego_neighbor_ids))

    def test_edges_between_results_and_neighbors(self):
        """Test that edges between search results and ego neighbors are inter-edges (not boundary)."""
        search_result_ids = ["auth.py:10-50:function:login"]
        ego_neighbor_ids = [
            "db.py:5-20:function:query",
            "session.py:10-30:function:create_session",
        ]

        result = self.extractor.extract_subgraph(
            chunk_ids=search_result_ids,
            ego_neighbor_ids=ego_neighbor_ids,
        )

        # Find edges from login to query and create_session
        login_to_query = [
            e
            for e in result.edges
            if e.source == "auth.py:10-50:function:login"
            and e.target == "db.py:5-20:function:query"
        ]
        login_to_session = [
            e
            for e in result.edges
            if e.source == "auth.py:10-50:function:login"
            and e.target == "session.py:10-30:function:create_session"
        ]

        # Verify both edges exist
        self.assertEqual(len(login_to_query), 1)
        self.assertEqual(len(login_to_session), 1)

        # Verify they are NOT boundary edges (both endpoints in subgraph)
        self.assertFalse(login_to_query[0].is_boundary)
        self.assertFalse(login_to_session[0].is_boundary)

        # Verify edge types preserved
        self.assertEqual(login_to_query[0].rel_type, "calls")
        self.assertEqual(login_to_session[0].rel_type, "calls")

    def test_ego_neighbors_in_topology_order(self):
        """Test that ego-graph neighbors appear in topological ordering."""
        search_result_ids = [
            "auth.py:10-50:function:login",
            "auth.py:55-80:class:AuthService",
        ]
        ego_neighbor_ids = [
            "db.py:5-20:function:query",
            "session.py:10-30:function:create_session",
        ]

        result = self.extractor.extract_subgraph(
            chunk_ids=search_result_ids,
            ego_neighbor_ids=ego_neighbor_ids,
        )

        # Verify all 4 chunk_ids in topology order
        self.assertEqual(len(result.topology_order), 4)
        topology_set = set(result.topology_order)
        expected_set = set(search_result_ids + ego_neighbor_ids)
        self.assertEqual(topology_set, expected_set)

        # Note: In a call graph, edges point FROM caller TO callee
        # Topological sort ensures dependencies (callees) appear before callers
        # Since there are multiple valid topological orderings, we just verify all 4 nodes are present
        self.assertIn("auth.py:10-50:function:login", result.topology_order)
        self.assertIn("db.py:5-20:function:query", result.topology_order)
        self.assertIn("session.py:10-30:function:create_session", result.topology_order)
        self.assertIn("auth.py:55-80:class:AuthService", result.topology_order)

    def test_backward_compat_no_ego_ids(self):
        """Test that ego_neighbor_ids=None produces identical behavior to Phase 1."""
        search_result_ids = [
            "auth.py:10-50:function:login",
            "auth.py:55-80:class:AuthService",
        ]

        result_with_none = self.extractor.extract_subgraph(
            chunk_ids=search_result_ids,
            ego_neighbor_ids=None,
        )

        result_without_param = self.extractor.extract_subgraph(
            chunk_ids=search_result_ids,
        )

        # Verify identical outputs
        self.assertEqual(len(result_with_none.nodes), len(result_without_param.nodes))
        self.assertEqual(len(result_with_none.edges), len(result_without_param.edges))
        self.assertEqual(
            result_with_none.topology_order, result_without_param.topology_order
        )

        # Verify only search results (no ego neighbors)
        self.assertEqual(len(result_with_none.nodes), 2)
        self.assertTrue(all(n.is_search_result for n in result_with_none.nodes))

    def test_source_field_propagation(self):
        """Test that ego-graph nodes serialize with 'source': 'ego_graph' marker."""
        search_result_ids = ["auth.py:10-50:function:login"]
        ego_neighbor_ids = ["db.py:5-20:function:query"]

        result = self.extractor.extract_subgraph(
            chunk_ids=search_result_ids,
            ego_neighbor_ids=ego_neighbor_ids,
        )

        serialized = result.to_dict()

        # Find the query node in serialized output
        query_node = [
            n for n in serialized["nodes"] if n["id"] == "db.py:5-20:function:query"
        ]
        self.assertEqual(len(query_node), 1)

        # Verify it has source: ego_graph marker
        self.assertEqual(query_node[0].get("source"), "ego_graph")

        # Find the login node (search result)
        login_node = [
            n for n in serialized["nodes"] if n["id"] == "auth.py:10-50:function:login"
        ]
        self.assertEqual(len(login_node), 1)

        # Verify search result does NOT have source marker
        self.assertNotIn("source", login_node[0])

    def test_ego_neighbor_dedup(self):
        """Test that ego neighbor already in search results is NOT duplicated."""
        search_result_ids = [
            "auth.py:10-50:function:login",
            "db.py:5-20:function:query",
        ]
        # db.py:query is both a search result AND an ego neighbor
        ego_neighbor_ids = [
            "db.py:5-20:function:query",
            "session.py:10-30:function:create_session",
        ]

        result = self.extractor.extract_subgraph(
            chunk_ids=search_result_ids,
            ego_neighbor_ids=ego_neighbor_ids,
        )

        # Verify 3 nodes total (2 search results + 1 unique ego neighbor)
        self.assertEqual(len(result.nodes), 3)

        # Verify db.py:query appears exactly once
        query_nodes = [
            n for n in result.nodes if n.chunk_id == "db.py:5-20:function:query"
        ]
        self.assertEqual(len(query_nodes), 1)

        # Verify it remains a search result (not overwritten by ego neighbor)
        self.assertTrue(query_nodes[0].is_search_result)

    def test_edges_between_ego_neighbors(self):
        """Test that edges between two ego-graph neighbors are also discovered."""
        search_result_ids = ["auth.py:10-50:function:login"]
        ego_neighbor_ids = [
            "db.py:5-20:function:query",
            "session.py:10-30:function:create_session",
        ]

        result = self.extractor.extract_subgraph(
            chunk_ids=search_result_ids,
            ego_neighbor_ids=ego_neighbor_ids,
        )

        # Find edge from query to create_session (both are ego neighbors)
        query_to_session = [
            e
            for e in result.edges
            if e.source == "db.py:5-20:function:query"
            and e.target == "session.py:10-30:function:create_session"
        ]

        # Verify edge exists and is NOT a boundary edge
        self.assertEqual(len(query_to_session), 1)
        self.assertFalse(query_to_session[0].is_boundary)
        self.assertEqual(query_to_session[0].rel_type, "calls")


if __name__ == "__main__":
    unittest.main()
