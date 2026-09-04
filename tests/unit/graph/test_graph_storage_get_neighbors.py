"""
Unit tests for CodeGraphStorage.get_neighbors() with expanded relationship type support.

Tests verify that get_neighbors() supports all 29 relationship types beyond the
original "calls"/"called_by" limitation.
"""

import heapq
import tempfile
from unittest.mock import patch

import pytest

from graph.graph_storage import (
    CodeGraphStorage,
    edge_confidence,
    is_ambiguous_call_edge,
)
from graph.traversal_policy import TraversalPolicy


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def graph_storage(temp_storage):
    """Create a CodeGraphStorage instance."""
    storage = CodeGraphStorage(project_id="test_project", storage_dir=temp_storage)
    yield storage
    # CodeGraphStorage doesn't have a close() method


@pytest.fixture
def multi_relationship_graph(graph_storage):
    """
    Create a graph with multiple relationship types for testing.

    Graph structure:
        A --calls--> B --inherits--> C --imports--> D
        E --decorates--> A
        F --uses_type--> C
    """
    # Add nodes
    nodes = [
        ("test.py:1-10:function:A", "A", "function"),
        ("test.py:20-30:class:B", "B", "class"),
        ("test.py:40-50:class:C", "C", "class"),
        ("test.py:60-70:module:D", "D", "module"),
        ("test.py:80-90:function:E", "E", "function"),
        ("test.py:100-110:function:F", "F", "function"),
    ]
    for chunk_id, name, chunk_type in nodes:
        graph_storage.add_node(
            chunk_id=chunk_id,
            name=name,
            chunk_type=chunk_type,
            file_path="test.py",
            language="python",
        )

    # Add edges with different relationship types using direct graph access
    graph_storage.graph.add_edge(
        "test.py:1-10:function:A", "test.py:20-30:class:B", relationship_type="calls"
    )
    graph_storage.graph.add_edge(
        "test.py:20-30:class:B", "test.py:40-50:class:C", relationship_type="inherits"
    )
    graph_storage.graph.add_edge(
        "test.py:40-50:class:C", "test.py:60-70:module:D", relationship_type="imports"
    )
    graph_storage.graph.add_edge(
        "test.py:80-90:function:E",
        "test.py:1-10:function:A",
        relationship_type="decorates",
    )
    graph_storage.graph.add_edge(
        "test.py:100-110:function:F",
        "test.py:40-50:class:C",
        relationship_type="uses_type",
    )

    return graph_storage


def test_get_neighbors_default_backward_compatibility(multi_relationship_graph):
    """Test that default behavior (no relation_types) still works for calls/called_by."""
    # Default should return call relationships only
    neighbors = multi_relationship_graph.get_neighbors("test.py:1-10:function:A")

    # A calls B, and E "calls" (decorates) A
    # Default should only traverse "calls" and "called_by"
    # A --calls--> B, so B should be included
    assert "test.py:20-30:class:B" in neighbors


def test_get_neighbors_single_type_forward(multi_relationship_graph):
    """Test filtering by a single forward relationship type."""
    # Get only inheritance relationships from B
    neighbors = multi_relationship_graph.get_neighbors(
        "test.py:20-30:class:B", relation_types=["inherits"]
    )

    # B --inherits--> C
    assert neighbors == {"test.py:40-50:class:C"}


def test_get_neighbors_single_type_reverse(multi_relationship_graph):
    """Test filtering by a single reverse relationship type."""
    # Get only "inherited_by" relationships from C
    neighbors = multi_relationship_graph.get_neighbors(
        "test.py:40-50:class:C", relation_types=["inherited_by"]
    )

    # B --inherits--> C, so B inherits from C
    assert neighbors == {"test.py:20-30:class:B"}


def test_get_neighbors_import_relationships(multi_relationship_graph):
    """Test import relationship traversal."""
    # Forward: C imports D
    neighbors_forward = multi_relationship_graph.get_neighbors(
        "test.py:40-50:class:C", relation_types=["imports"]
    )
    assert neighbors_forward == {"test.py:60-70:module:D"}

    # Reverse: D is imported by C
    neighbors_reverse = multi_relationship_graph.get_neighbors(
        "test.py:60-70:module:D", relation_types=["imported_by"]
    )
    assert neighbors_reverse == {"test.py:40-50:class:C"}


def test_get_neighbors_decorator_relationships(multi_relationship_graph):
    """Test decorator relationship traversal."""
    # Forward: E decorates A
    neighbors_forward = multi_relationship_graph.get_neighbors(
        "test.py:80-90:function:E", relation_types=["decorates"]
    )
    assert neighbors_forward == {"test.py:1-10:function:A"}

    # Reverse: A is decorated by E
    neighbors_reverse = multi_relationship_graph.get_neighbors(
        "test.py:1-10:function:A", relation_types=["decorated_by"]
    )
    assert neighbors_reverse == {"test.py:80-90:function:E"}


def test_get_neighbors_uses_type_relationships(multi_relationship_graph):
    """Test uses_type relationship traversal."""
    # Forward: F uses_type C
    neighbors_forward = multi_relationship_graph.get_neighbors(
        "test.py:100-110:function:F", relation_types=["uses_type"]
    )
    assert neighbors_forward == {"test.py:40-50:class:C"}

    # Reverse: C is used as type by F
    neighbors_reverse = multi_relationship_graph.get_neighbors(
        "test.py:40-50:class:C", relation_types=["used_as_type_by"]
    )
    assert neighbors_reverse == {"test.py:100-110:function:F"}


def test_get_neighbors_multiple_types(multi_relationship_graph):
    """Test filtering by multiple relationship types."""
    # Get both calls and decorated_by from A
    neighbors = multi_relationship_graph.get_neighbors(
        "test.py:1-10:function:A", relation_types=["calls", "decorated_by"]
    )

    # A --calls--> B and E --decorates--> A
    assert neighbors == {"test.py:20-30:class:B", "test.py:80-90:function:E"}


def test_get_neighbors_max_depth_multi_hop(multi_relationship_graph):
    """Test multi-hop traversal with max_depth."""
    # Traverse inheritance chain with depth 2
    neighbors = multi_relationship_graph.get_neighbors(
        "test.py:20-30:class:B", relation_types=["inherits"], max_depth=2
    )

    # B --inherits--> C --imports--> D (but imports not in filter)
    # So only C should be included at depth 1
    assert neighbors == {"test.py:40-50:class:C"}

    # Now include both inherits and imports
    neighbors = multi_relationship_graph.get_neighbors(
        "test.py:20-30:class:B", relation_types=["inherits", "imports"], max_depth=2
    )

    # B --inherits--> C --imports--> D
    assert neighbors == {"test.py:40-50:class:C", "test.py:60-70:module:D"}


def test_get_neighbors_no_matching_edges(multi_relationship_graph):
    """Test that non-existent relationship types return empty set."""
    # A doesn't have any "overrides" relationships
    neighbors = multi_relationship_graph.get_neighbors(
        "test.py:1-10:function:A", relation_types=["overrides"]
    )

    assert neighbors == set()


def test_get_neighbors_nonexistent_node(multi_relationship_graph):
    """Test that nonexistent nodes return empty set."""
    neighbors = multi_relationship_graph.get_neighbors(
        "test.py:999-999:function:NONEXISTENT"
    )

    assert neighbors == set()


def test_get_neighbors_all_types_none_filter(multi_relationship_graph):
    """Test that None filter uses default behavior (calls/called_by)."""
    # None should default to ["calls", "called_by"]
    neighbors = multi_relationship_graph.get_neighbors(
        "test.py:1-10:function:A", relation_types=None
    )

    # Should only get call relationships by default
    assert "test.py:20-30:class:B" in neighbors


def test_reverse_relation_type_mapping(graph_storage):
    """Test the _get_reverse_relation_type helper method."""
    # Standard pattern: append "_by"
    assert graph_storage._get_reverse_relation_type("calls") == "called_by"
    assert graph_storage._get_reverse_relation_type("imports") == "imported_by"
    assert graph_storage._get_reverse_relation_type("inherits") == "inherited_by"
    assert graph_storage._get_reverse_relation_type("decorates") == "decorated_by"
    assert graph_storage._get_reverse_relation_type("instantiates") == "instantiated_by"

    # Special cases
    assert graph_storage._get_reverse_relation_type("overrides") == "overridden_by"
    assert graph_storage._get_reverse_relation_type("catches") == "caught_by"


def test_get_neighbors_complex_graph_structure(graph_storage):
    """
    Test with a more complex graph structure.

    Graph:
        BaseClass <--inherits-- ChildA --calls--> method1
        BaseClass <--inherits-- ChildB --calls--> method2
        ChildA --imports--> module1
        ChildB --imports--> module2
    """
    # Add nodes
    nodes = [
        ("test.py:1-10:class:BaseClass", "BaseClass", "class"),
        ("test.py:20-30:class:ChildA", "ChildA", "class"),
        ("test.py:40-50:class:ChildB", "ChildB", "class"),
        ("test.py:60-70:function:method1", "method1", "function"),
        ("test.py:80-90:function:method2", "method2", "function"),
        ("test.py:100-110:module:module1", "module1", "module"),
        ("test.py:120-130:module:module2", "module2", "module"),
    ]
    for chunk_id, name, chunk_type in nodes:
        graph_storage.add_node(
            chunk_id=chunk_id, name=name, chunk_type=chunk_type, file_path="test.py"
        )

    # Add relationships
    graph_storage.graph.add_edge(
        "test.py:20-30:class:ChildA",
        "test.py:1-10:class:BaseClass",
        relationship_type="inherits",
    )
    graph_storage.graph.add_edge(
        "test.py:40-50:class:ChildB",
        "test.py:1-10:class:BaseClass",
        relationship_type="inherits",
    )
    graph_storage.graph.add_edge(
        "test.py:20-30:class:ChildA",
        "test.py:60-70:function:method1",
        relationship_type="calls",
    )
    graph_storage.graph.add_edge(
        "test.py:40-50:class:ChildB",
        "test.py:80-90:function:method2",
        relationship_type="calls",
    )
    graph_storage.graph.add_edge(
        "test.py:20-30:class:ChildA",
        "test.py:100-110:module:module1",
        relationship_type="imports",
    )
    graph_storage.graph.add_edge(
        "test.py:40-50:class:ChildB",
        "test.py:120-130:module:module2",
        relationship_type="imports",
    )

    # Test: Get all children of BaseClass
    children = graph_storage.get_neighbors(
        "test.py:1-10:class:BaseClass", relation_types=["inherited_by"]
    )
    assert children == {"test.py:20-30:class:ChildA", "test.py:40-50:class:ChildB"}

    # Test: Get all methods called by ChildA
    methods = graph_storage.get_neighbors(
        "test.py:20-30:class:ChildA", relation_types=["calls"]
    )
    assert methods == {"test.py:60-70:function:method1"}

    # Test: Multi-hop from BaseClass to methods (depth 2)
    neighbors_depth2 = graph_storage.get_neighbors(
        "test.py:1-10:class:BaseClass",
        relation_types=["inherited_by", "calls"],
        max_depth=2,
    )
    assert neighbors_depth2 == {
        "test.py:20-30:class:ChildA",
        "test.py:40-50:class:ChildB",
        "test.py:60-70:function:method1",
        "test.py:80-90:function:method2",
    }

    # Test: Multi-type query from ChildA
    neighbors_multi = graph_storage.get_neighbors(
        "test.py:20-30:class:ChildA", relation_types=["calls", "imports", "inherits"]
    )
    assert neighbors_multi == {
        "test.py:60-70:function:method1",
        "test.py:100-110:module:module1",
        "test.py:1-10:class:BaseClass",
    }


def test_get_neighbors_bidirectional_traversal(graph_storage):
    """Test that we can traverse both directions simultaneously."""
    # Create a simple chain: A --calls--> B --calls--> C
    nodes = [
        ("test.py:1-10:function:A", "A", "function"),
        ("test.py:20-30:function:B", "B", "function"),
        ("test.py:40-50:function:C", "C", "function"),
    ]
    for chunk_id, name, chunk_type in nodes:
        graph_storage.add_node(
            chunk_id=chunk_id, name=name, chunk_type=chunk_type, file_path="test.py"
        )

    graph_storage.graph.add_edge(
        "test.py:1-10:function:A", "test.py:20-30:function:B", relationship_type="calls"
    )
    graph_storage.graph.add_edge(
        "test.py:20-30:function:B",
        "test.py:40-50:function:C",
        relationship_type="calls",
    )

    # From B, get both callers and callees
    neighbors = graph_storage.get_neighbors(
        "test.py:20-30:function:B", relation_types=["calls", "called_by"]
    )

    # B calls C, and is called by A
    assert neighbors == {"test.py:1-10:function:A", "test.py:40-50:function:C"}


def test_get_neighbors_exclude_import_categories(graph_storage):
    """Test that exclude_import_categories still works with new implementation."""
    # Add nodes
    nodes = [
        ("test.py:1-10:module:module_a", "module_a", "module"),
        ("stdlib.py:1-10:module:stdlib_module", "stdlib_module", "module"),
        ("local.py:1-10:module:local_module", "local_module", "module"),
    ]
    for chunk_id, name, chunk_type in nodes:
        graph_storage.add_node(
            chunk_id=chunk_id, name=name, chunk_type=chunk_type, file_path="test.py"
        )

    # Add import edges with categories
    graph_storage.graph.add_edge(
        "test.py:1-10:module:module_a",
        "stdlib.py:1-10:module:stdlib_module",
        relationship_type="imports",
        import_category="stdlib",
    )
    graph_storage.graph.add_edge(
        "test.py:1-10:module:module_a",
        "local.py:1-10:module:local_module",
        relationship_type="imports",
        import_category="local",
    )

    # Get all imports
    all_imports = graph_storage.get_neighbors(
        "test.py:1-10:module:module_a", relation_types=["imports"]
    )
    assert all_imports == {
        "stdlib.py:1-10:module:stdlib_module",
        "local.py:1-10:module:local_module",
    }

    # Exclude stdlib imports
    filtered_imports = graph_storage.get_neighbors(
        "test.py:1-10:module:module_a",
        relation_types=["imports"],
        exclude_import_categories=["stdlib"],
    )
    assert filtered_imports == {"local.py:1-10:module:local_module"}


def test_exclude_import_categories_with_weighted_bfs(graph_storage):
    """Import-category exclusion is applied by _iter_matching_neighbors for both BFS modes.

    The weighted path previously had its own copy of the exclusion logic. This test
    guards that _iter_matching_neighbors correctly filters categories when used by the
    weighted BFS — i.e., the exclusion didn't get dropped during extraction.
    """
    nodes = [
        ("test.py:1-10:module:module_a", "module_a", "module"),
        ("stdlib.py:1-10:module:stdlib_module", "stdlib_module", "module"),
        ("local.py:1-10:module:local_module", "local_module", "module"),
    ]
    for chunk_id, name, chunk_type in nodes:
        graph_storage.add_node(
            chunk_id=chunk_id, name=name, chunk_type=chunk_type, file_path="test.py"
        )

    graph_storage.graph.add_edge(
        "test.py:1-10:module:module_a",
        "stdlib.py:1-10:module:stdlib_module",
        relationship_type="imports",
        import_category="stdlib",
    )
    graph_storage.graph.add_edge(
        "test.py:1-10:module:module_a",
        "local.py:1-10:module:local_module",
        relationship_type="imports",
        import_category="local",
    )

    edge_weights = {"imports": 1.0}

    # Weighted BFS without exclusion: both neighbors returned
    all_imports = graph_storage.get_neighbors(
        "test.py:1-10:module:module_a",
        relation_types=["imports"],
        edge_weights=edge_weights,
    )
    assert all_imports == {
        "stdlib.py:1-10:module:stdlib_module",
        "local.py:1-10:module:local_module",
    }

    # Weighted BFS with stdlib excluded: only local returned
    filtered_imports = graph_storage.get_neighbors(
        "test.py:1-10:module:module_a",
        relation_types=["imports"],
        exclude_import_categories=["stdlib"],
        edge_weights=edge_weights,
    )
    assert filtered_imports == {"local.py:1-10:module:local_module"}


class TestGetNeighborsRanked:
    """Tests for fix #3: get_neighbors_ranked(...) -> list[str].

    Shares _traverse_neighbors with get_neighbors, so the two can never
    disagree on *which* nodes are reachable -- only get_neighbors_ranked
    additionally guarantees a deterministic *order*, which callers that
    truncate (e.g. multi_hop_searcher._graph_expand, ego_graph_retriever)
    need instead of Python's set-iteration order.
    """

    A = "test.py:1-10:function:A"
    B = "test.py:20-30:function:B"
    C = "test.py:40-50:function:C"
    D = "test.py:60-70:function:D"

    def test_ranked_matches_get_neighbors_as_set_unweighted(
        self, multi_relationship_graph
    ):
        """set(get_neighbors_ranked(...)) == get_neighbors(...) for identical
        args, unweighted BFS."""
        ranked = multi_relationship_graph.get_neighbors_ranked(
            "test.py:1-10:function:A",
            TraversalPolicy(relation_types=["calls", "decorated_by"], max_depth=2),
        )
        unranked = multi_relationship_graph.get_neighbors(
            "test.py:1-10:function:A",
            relation_types=["calls", "decorated_by"],
            max_depth=2,
        )
        assert set(ranked) == unranked
        assert len(ranked) == len(set(ranked))  # each neighbor appears once

    def test_ranked_matches_get_neighbors_as_set_weighted(
        self, multi_relationship_graph
    ):
        """Same equivalence holds for the weighted (priority-queue) path."""
        edge_weights = {"calls": 1.0, "inherits": 0.6, "imports": 0.3}
        ranked = multi_relationship_graph.get_neighbors_ranked(
            "test.py:1-10:function:A",
            TraversalPolicy(
                relation_types=["calls", "inherits", "imports"],
                max_depth=3,
                edge_weights=edge_weights,
            ),
        )
        unranked = multi_relationship_graph.get_neighbors(
            "test.py:1-10:function:A",
            relation_types=["calls", "inherits", "imports"],
            max_depth=3,
            edge_weights=edge_weights,
        )
        assert set(ranked) == unranked

    def test_ranked_unweighted_bfs_is_level_order(self, graph_storage):
        """Direct (depth-1) neighbors are yielded in edge-insertion order;
        depth-2 neighbors -- reached only after every depth-1 neighbor of the
        root has been discovered -- always come after them (level order)."""
        for chunk_id, name in [
            (self.A, "A"),
            (self.B, "B"),
            (self.C, "C"),
            (self.D, "D"),
        ]:
            graph_storage.add_node(
                chunk_id=chunk_id, name=name, chunk_type="function", file_path="test.py"
            )
        # A -> C, then A -> B (insertion order deliberately not sorted), B -> D.
        graph_storage.graph.add_edge(self.A, self.C, relationship_type="calls")
        graph_storage.graph.add_edge(self.A, self.B, relationship_type="calls")
        graph_storage.graph.add_edge(self.B, self.D, relationship_type="calls")

        ranked = graph_storage.get_neighbors_ranked(
            self.A, TraversalPolicy(relation_types=["calls"], max_depth=2)
        )

        assert ranked == [self.C, self.B, self.D]

    def test_ranked_weighted_priority_expands_higher_weight_child_first(
        self, graph_storage
    ):
        """Direct neighbors of the root are discovered together (edge-insertion
        order, independent of weight) but the *next* generation is reached in
        weight-priority order: the higher-weight child's own neighbor is
        yielded before the lower-weight child's, even though the lower-weight
        child was discovered (and would sort) first in insertion order."""
        for chunk_id, name in [
            (self.A, "A"),
            (self.B, "X"),
            (self.C, "Y"),
            ("test.py:60-70:function:Z", "Z"),
            ("test.py:80-90:function:W", "W"),
        ]:
            graph_storage.add_node(
                chunk_id=chunk_id, name=name, chunk_type="function", file_path="test.py"
            )
        z = "test.py:60-70:function:Z"
        w = "test.py:80-90:function:W"

        # X (via low-weight "imports") is inserted before Y (via high-weight
        # "calls") so a naive "insertion order all the way down" traversal
        # would put X's subtree first -- the weighted BFS must not do that.
        graph_storage.graph.add_edge(self.A, self.B, relationship_type="imports")
        graph_storage.graph.add_edge(self.A, self.C, relationship_type="calls")
        graph_storage.graph.add_edge(self.B, z, relationship_type="imports")
        graph_storage.graph.add_edge(self.C, w, relationship_type="calls")

        ranked = graph_storage.get_neighbors_ranked(
            self.A,
            TraversalPolicy(
                relation_types=["calls", "imports"],
                max_depth=2,
                edge_weights={"calls": 1.0, "imports": 0.3},
            ),
        )

        # Depth-1 neighbors keep edge-insertion order (X before Y) ...
        assert ranked[:2] == [self.B, self.C]
        # ... but Y's child (W, weight 1.0) is expanded before X's child
        # (Z, weight 0.3), so W precedes Z despite X being discovered first.
        assert ranked[2:] == [w, z]

    def test_ranked_deterministic_across_repeated_calls(self, multi_relationship_graph):
        """Two calls with identical arguments return the identical list --
        this is the property that regresses under truncation when a caller
        instead does list(get_neighbors(...))[:n]."""
        policy = TraversalPolicy(relation_types=["calls", "decorated_by"])
        first = multi_relationship_graph.get_neighbors_ranked(
            "test.py:1-10:function:A", policy
        )
        second = multi_relationship_graph.get_neighbors_ranked(
            "test.py:1-10:function:A", policy
        )
        assert first == second

    def test_ranked_respects_min_confidence_floor(self, graph_storage):
        """The floor is applied inside the shared generator, so
        get_neighbors_ranked drops exactly the same edges as get_neighbors."""
        for chunk_id, name in [(self.A, "A"), (self.B, "B"), (self.C, "C")]:
            graph_storage.add_node(
                chunk_id=chunk_id, name=name, chunk_type="function", file_path="test.py"
            )
        graph_storage.graph.add_edge(
            self.A, self.B, relationship_type="calls", resolver_confidence=0.5
        )
        graph_storage.graph.add_edge(
            self.A, self.C, relationship_type="calls", resolver_confidence=0.98
        )

        ranked = graph_storage.get_neighbors_ranked(
            self.A, TraversalPolicy(relation_types=["calls"], min_confidence=0.6)
        )

        assert ranked == [self.C]

    def test_ranked_nonexistent_node_returns_empty_list(self, graph_storage):
        """Mirrors get_neighbors' empty-set return for an unknown chunk_id."""
        assert graph_storage.get_neighbors_ranked("does.py:1-1:function:missing") == []


class TestEdgeConfidenceFunction:
    """Direct tests for the module-level ``edge_confidence()`` resolver
    (graph/graph_storage.py), independent of any layer's ``None`` policy.

    Resolution order: float ``resolver_confidence`` -> legacy string
    ``confidence`` tag -> 0.5 for an untagged ``calls`` edge -> ``None``.
    """

    def test_float_resolver_confidence_wins(self):
        """A resolver-written float always wins, even over a string tag."""
        assert edge_confidence({"resolver_confidence": 0.75}) == 0.75
        assert (
            edge_confidence({"resolver_confidence": 0.75, "confidence": "ambiguous"})
            == 0.75
        )

    def test_string_tag_mapped_when_no_float(self):
        """Legacy string tags map via AST_CONFIDENCE_BY_TAG."""
        assert edge_confidence({"confidence": "ambiguous"}) == 0.5
        assert edge_confidence({"confidence": "recovered"}) == 0.5
        assert edge_confidence({"confidence": "exact"}) == 0.7

    def test_untagged_calls_edge_defaults_to_half(self):
        """No float, no tag, but edge_type == 'calls' -> 0.5."""
        assert edge_confidence({}, edge_type="calls") == 0.5

    def test_non_call_untagged_edge_is_none(self):
        """No float, no tag, non-`calls` edge_type -> None (truly unknown;
        each calling layer decides its own default for this case)."""
        assert edge_confidence({}, edge_type="imports") is None
        assert edge_confidence({}) is None  # edge_type omitted

    def test_non_numeric_resolver_confidence_is_ignored(self):
        """A non-numeric resolver_confidence value (e.g. a stray string) is
        not coerced -- resolution falls through to the next tier."""
        assert edge_confidence({"resolver_confidence": "0.5"}, edge_type="calls") == 0.5
        assert edge_confidence({"resolver_confidence": "0.5"}) is None


class TestIsAmbiguousCallEdge:
    """Direct tests for ``is_ambiguous_call_edge()``: only an AST ``calls``
    edge carrying the ``"ambiguous"`` string tag and no float
    ``resolver_confidence`` qualifies."""

    def test_tagged_ambiguous_call_edge(self):
        assert is_ambiguous_call_edge(
            {"relationship_type": "calls", "confidence": "ambiguous"}
        )

    def test_float_resolver_confidence_supersedes_tag(self):
        """A resolver that validated the edge wrote a float; the stale tag
        no longer counts, matching edge_confidence's precedence."""
        assert not is_ambiguous_call_edge(
            {
                "relationship_type": "calls",
                "confidence": "ambiguous",
                "resolver_confidence": 0.9,
            }
        )

    def test_exact_and_untagged_and_non_call_are_not_ambiguous(self):
        assert not is_ambiguous_call_edge(
            {"relationship_type": "calls", "confidence": "exact"}
        )
        assert not is_ambiguous_call_edge({"relationship_type": "calls"})
        assert not is_ambiguous_call_edge(
            {"relationship_type": "imports", "confidence": "ambiguous"}
        )


class TestConfidenceTraversal:
    """Tests for A2: confidence-weighted traversal in get_neighbors.

    ``min_confidence`` drops edges whose resolved confidence (see
    :func:`graph.graph_storage.edge_confidence`) falls below the floor (both
    BFS modes). Resolution order: float ``resolver_confidence`` first;
    otherwise a legacy ``confidence`` string tag ("exact"/"ambiguous"/
    "recovered") maps to 0.7/0.5/0.5; otherwise an untagged ``calls`` edge
    defaults to 0.5; only a non-call edge with neither a float nor a tag
    counts as 1.0 and always survives. ``confidence_weighting`` multiplies
    the weighted-BFS type-weight by the edge's resolved confidence.
    """

    A = "test.py:1-10:function:A"
    B = "test.py:20-30:function:B"
    C = "test.py:40-50:function:C"
    D = "test.py:60-70:function:D"

    @pytest.fixture
    def confidence_graph(self, graph_storage):
        """A calls B (ambiguous 0.5), C (LSP 0.98), D (legacy string tag only)."""
        for chunk_id, name in [
            (self.A, "A"),
            (self.B, "B"),
            (self.C, "C"),
            (self.D, "D"),
        ]:
            graph_storage.add_node(
                chunk_id=chunk_id,
                name=name,
                chunk_type="function",
                file_path="test.py",
            )
        graph_storage.graph.add_edge(
            self.A, self.B, relationship_type="calls", resolver_confidence=0.5
        )
        graph_storage.graph.add_edge(
            self.A, self.C, relationship_type="calls", resolver_confidence=0.98
        )
        graph_storage.graph.add_edge(
            self.A, self.D, relationship_type="calls", confidence="ambiguous"
        )
        return graph_storage

    def test_default_floor_is_byte_identical(self, confidence_graph):
        """min_confidence=0.0 (default) returns every edge, however low its
        resolver_confidence."""
        neighbors = confidence_graph.get_neighbors(self.A, relation_types=["calls"])
        assert neighbors == {self.B, self.C, self.D}

    def test_floor_drops_low_confidence_unweighted(self, confidence_graph):
        """Unweighted BFS: both the 0.5 float edge and the "ambiguous"-tagged
        edge (now also resolved to 0.5, not 1.0) are dropped at floor 0.6;
        only the 0.98 LSP edge survives."""
        neighbors = confidence_graph.get_neighbors(
            self.A, relation_types=["calls"], min_confidence=0.6
        )
        assert neighbors == {self.C}

    def test_floor_drops_low_confidence_weighted(self, confidence_graph):
        """Weighted BFS applies the same floor."""
        neighbors = confidence_graph.get_neighbors(
            self.A,
            relation_types=["calls"],
            min_confidence=0.6,
            edge_weights={"calls": 1.0},
        )
        assert neighbors == {self.C}

    def test_legacy_string_tag_now_parsed(self, confidence_graph):
        """An edge carrying only the "ambiguous" string tag resolves to
        exactly 0.5 (via AST_CONFIDENCE_BY_TAG) — it survives a floor of 0.5
        but is dropped the instant the floor exceeds it, same as a real 0.5
        float edge. This reverses the old "tags are never parsed" behavior."""
        assert self.D in confidence_graph.get_neighbors(
            self.A, relation_types=["calls"], min_confidence=0.5
        )
        assert self.D not in confidence_graph.get_neighbors(
            self.A, relation_types=["calls"], min_confidence=0.51
        )

    def test_floor_drops_edges_not_nodes(self, confidence_graph):
        """A neighbor whose low-confidence edge is dropped is still returned
        when another surviving edge reaches it."""
        # Forward edge A->B (0.5) is floored out on its own...
        assert self.B not in confidence_graph.get_neighbors(
            self.A, relation_types=["calls", "called_by"], min_confidence=0.6
        )
        # ...but a reverse call edge B->A with an explicit high-confidence
        # float (0.9) revives B. (An untagged reverse edge would no longer
        # demonstrate this: untagged `calls` edges now default to 0.5 too,
        # same as the forward edge, so the float is made explicit here to
        # keep the "edges not nodes" behavior decoupled from that default.)
        confidence_graph.graph.add_edge(
            self.B, self.A, relationship_type="calls", resolver_confidence=0.9
        )
        neighbors = confidence_graph.get_neighbors(
            self.A, relation_types=["calls", "called_by"], min_confidence=0.6
        )
        assert self.B in neighbors

    E = "test.py:80-90:function:E"
    F = "test.py:100-110:function:F"

    @pytest.fixture
    def ambiguous_graph(self, confidence_graph):
        """confidence_graph plus A->E (tag:exact) and A->F (untagged calls)."""
        for chunk_id, name in [(self.E, "E"), (self.F, "F")]:
            confidence_graph.add_node(
                chunk_id=chunk_id,
                name=name,
                chunk_type="function",
                file_path="test.py",
            )
        confidence_graph.graph.add_edge(
            self.A, self.E, relationship_type="calls", confidence="exact"
        )
        confidence_graph.graph.add_edge(self.A, self.F, relationship_type="calls")
        return confidence_graph

    def test_drop_ambiguous_default_off_is_byte_identical(self, ambiguous_graph):
        """drop_ambiguous defaults to False: every edge is returned."""
        neighbors = ambiguous_graph.get_neighbors(self.A, relation_types=["calls"])
        assert neighbors == {self.B, self.C, self.D, self.E, self.F}
        ranked = ambiguous_graph.get_neighbors_ranked(
            self.A, TraversalPolicy(relation_types=["calls"])
        )
        assert set(ranked) == neighbors

    def test_drop_ambiguous_drops_only_tagged_edge_unweighted(self, ambiguous_graph):
        """Only the ``confidence="ambiguous"`` edge (D) is dropped. The float
        0.5 edge (B), the tag:exact edge (E) and the untagged calls edge (F)
        all resolve to <= 0.7 too, but they are not ambiguous and survive —
        unlike a min_confidence floor of 0.6, which would also drop B and F.
        """
        neighbors = ambiguous_graph.get_neighbors(
            self.A, relation_types=["calls"], drop_ambiguous=True
        )
        assert neighbors == {self.B, self.C, self.E, self.F}
        floored = ambiguous_graph.get_neighbors(
            self.A, relation_types=["calls"], min_confidence=0.6
        )
        assert floored == {self.C, self.E}

    def test_drop_ambiguous_drops_only_tagged_edge_weighted(self, ambiguous_graph):
        """Weighted BFS applies the same predicate."""
        neighbors = ambiguous_graph.get_neighbors(
            self.A,
            relation_types=["calls"],
            edge_weights={"calls": 1.0},
            drop_ambiguous=True,
        )
        assert neighbors == {self.B, self.C, self.E, self.F}

    def test_drop_ambiguous_ranked_matches_unranked(self, ambiguous_graph):
        ranked = ambiguous_graph.get_neighbors_ranked(
            self.A, TraversalPolicy(relation_types=["calls"], drop_ambiguous=True)
        )
        assert set(ranked) == {self.B, self.C, self.E, self.F}
        assert self.D not in ranked

    def test_drop_ambiguous_float_supersedes_tag(self, ambiguous_graph):
        """An edge whose stale tag says "ambiguous" but which a later resolver
        validated with a float is kept."""
        ambiguous_graph.graph.remove_edge(self.A, self.D)
        ambiguous_graph.graph.add_edge(
            self.A,
            self.D,
            relationship_type="calls",
            confidence="ambiguous",
            resolver_confidence=0.9,
        )
        neighbors = ambiguous_graph.get_neighbors(
            self.A, relation_types=["calls"], drop_ambiguous=True
        )
        assert self.D in neighbors

    def test_drop_ambiguous_drops_edges_not_nodes(self, ambiguous_graph):
        """D is unreachable through its ambiguous edge but comes back once a
        surviving reverse call edge D->A exists."""
        assert self.D not in ambiguous_graph.get_neighbors(
            self.A, relation_types=["calls", "called_by"], drop_ambiguous=True
        )
        ambiguous_graph.graph.add_edge(
            self.D, self.A, relationship_type="calls", resolver_confidence=0.9
        )
        assert self.D in ambiguous_graph.get_neighbors(
            self.A, relation_types=["calls", "called_by"], drop_ambiguous=True
        )

    def test_drop_ambiguous_at_depth_two(self, ambiguous_graph):
        """The predicate applies on every hop: D's onward neighbor G is not
        reached through the dropped A->D edge."""
        g = "test.py:120-130:function:G"
        ambiguous_graph.add_node(
            chunk_id=g, name="G", chunk_type="function", file_path="test.py"
        )
        ambiguous_graph.graph.add_edge(
            self.D, g, relationship_type="calls", resolver_confidence=0.98
        )
        base = ambiguous_graph.get_neighbors(
            self.A, relation_types=["calls"], max_depth=2
        )
        assert g in base
        dropped = ambiguous_graph.get_neighbors(
            self.A, relation_types=["calls"], max_depth=2, drop_ambiguous=True
        )
        assert g not in dropped

    def _captured_push_weights(self, storage, confidence_weighting):
        """Run a weighted BFS and capture the priority-queue weight per neighbor."""
        pushes = []
        # Bind before patching: graph_storage shares this module object, so
        # calling heapq.heappush inside the spy would recurse into the patch.
        original_push = heapq.heappush

        def spy(pq, item):
            pushes.append(item)
            original_push(pq, item)

        with patch("graph.graph_storage.heapq.heappush", side_effect=spy):
            storage.get_neighbors(
                self.A,
                relation_types=["calls"],
                edge_weights={"calls": 1.0},
                confidence_weighting=confidence_weighting,
            )
        return {item[2]: -item[0] for item in pushes}

    def test_confidence_weighting_multiplies_push_weight(self, confidence_graph):
        """Enabled: expansion priority = type-weight * resolved confidence;
        the "ambiguous"-tagged edge (D) now resolves to 0.5 too, same as the
        explicit 0.5 float edge (B) — it no longer keeps the bare type-weight."""
        weights = self._captured_push_weights(
            confidence_graph, confidence_weighting=True
        )
        assert weights[self.B] == pytest.approx(0.5)  # 1.0 * 0.5 float
        assert weights[self.C] == pytest.approx(0.98)  # 1.0 * 0.98 LSP
        assert weights[self.D] == pytest.approx(0.5)  # 1.0 * 0.5 ambiguous tag

    def test_confidence_weighting_disabled_keeps_type_weight(self, confidence_graph):
        """Disabled (default): every calls edge pushes at the bare type-weight."""
        weights = self._captured_push_weights(
            confidence_graph, confidence_weighting=False
        )
        assert weights == {self.B: 1.0, self.C: 1.0, self.D: 1.0}

    def test_edge_confidence_reads_only_float(self, graph_storage):
        """_edge_confidence: floats/ints pass through as-is; a non-numeric
        resolver_confidence is ignored (falls through to the next tier)."""
        assert graph_storage._edge_confidence({"resolver_confidence": 0.75}) == 0.75
        assert graph_storage._edge_confidence({"resolver_confidence": 1}) == 1.0
        assert (
            graph_storage._edge_confidence({"resolver_confidence": "0.5"}) == 1.0
        )  # non-numeric string -> ignored -> no tag, no edge_type -> None -> 1.0

    def test_edge_confidence_legacy_tags_now_mapped(self, graph_storage):
        """A legacy string ``confidence`` tag with no float resolves via
        AST_CONFIDENCE_BY_TAG instead of the old blanket 1.0 default."""
        assert graph_storage._edge_confidence({"confidence": "ambiguous"}) == 0.5
        assert graph_storage._edge_confidence({"confidence": "recovered"}) == 0.5
        assert graph_storage._edge_confidence({"confidence": "exact"}) == 0.7

    def test_edge_confidence_untagged_calls_defaults_to_half(self, graph_storage):
        """An untagged, float-free edge on a `calls` edge_type defaults to
        0.5 (the common ~80% case: base-AST edges with no resolver signal)."""
        assert graph_storage._edge_confidence({}, edge_type="calls") == 0.5

    def test_edge_confidence_unknown_non_call_defaults_to_permissive(
        self, graph_storage
    ):
        """An edge with no float, no tag, and a non-`calls` (or unknown)
        edge_type has no confidence signal at all -> module-level
        edge_confidence() returns None -> the traversal layer's own
        permissive policy maps that to 1.0 (never silently pruned)."""
        assert graph_storage._edge_confidence({}) == 1.0
        assert graph_storage._edge_confidence({}, edge_type="imports") == 1.0
