"""
Unit tests for CodeGraphStorage.get_neighbors() with expanded relationship type support.

Tests verify that get_neighbors() supports all 21 relationship types beyond the
original "calls"/"called_by" limitation.
"""

import heapq
import tempfile
from unittest.mock import patch

import pytest

from graph.graph_storage import CodeGraphStorage


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


class TestConfidenceTraversal:
    """Tests for A2: confidence-weighted traversal in get_neighbors.

    ``min_confidence`` drops edges whose float ``resolver_confidence`` falls
    below the floor (both BFS modes); edges without the float (non-call,
    legacy, unresolved) count as 1.0 and always survive. The legacy string
    ``confidence`` tags are never parsed. ``confidence_weighting`` multiplies
    the weighted-BFS type-weight by the edge's confidence.
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
        """Unweighted BFS: the 0.5 ambiguous edge is dropped at floor 0.6;
        the LSP edge and the confidence-free edge (counts as 1.0) survive."""
        neighbors = confidence_graph.get_neighbors(
            self.A, relation_types=["calls"], min_confidence=0.6
        )
        assert neighbors == {self.C, self.D}

    def test_floor_drops_low_confidence_weighted(self, confidence_graph):
        """Weighted BFS applies the same floor."""
        neighbors = confidence_graph.get_neighbors(
            self.A,
            relation_types=["calls"],
            min_confidence=0.6,
            edge_weights={"calls": 1.0},
        )
        assert neighbors == {self.C, self.D}

    def test_legacy_string_tag_never_parsed(self, confidence_graph):
        """An edge carrying only the string tag ("ambiguous") counts as 1.0 —
        it survives a floor that drops even the 0.98 LSP edge."""
        neighbors = confidence_graph.get_neighbors(
            self.A, relation_types=["calls"], min_confidence=0.99
        )
        assert neighbors == {self.D}

    def test_floor_drops_edges_not_nodes(self, confidence_graph):
        """A neighbor whose low-confidence edge is dropped is still returned
        when another surviving edge reaches it."""
        # Forward edge A->B (0.5) is floored out on its own...
        assert self.B not in confidence_graph.get_neighbors(
            self.A, relation_types=["calls", "called_by"], min_confidence=0.6
        )
        # ...but a reverse call edge B->A (no float attr -> 1.0) revives B.
        confidence_graph.graph.add_edge(self.B, self.A, relationship_type="calls")
        neighbors = confidence_graph.get_neighbors(
            self.A, relation_types=["calls", "called_by"], min_confidence=0.6
        )
        assert self.B in neighbors

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
        """Enabled: expansion priority = type-weight * resolver_confidence;
        edges without the float keep the bare type-weight."""
        weights = self._captured_push_weights(
            confidence_graph, confidence_weighting=True
        )
        assert weights[self.B] == pytest.approx(0.5)  # 1.0 * 0.5 ambiguous
        assert weights[self.C] == pytest.approx(0.98)  # 1.0 * 0.98 LSP
        assert weights[self.D] == pytest.approx(1.0)  # no float attr

    def test_confidence_weighting_disabled_keeps_type_weight(self, confidence_graph):
        """Disabled (default): every calls edge pushes at the bare type-weight."""
        weights = self._captured_push_weights(
            confidence_graph, confidence_weighting=False
        )
        assert weights == {self.B: 1.0, self.C: 1.0, self.D: 1.0}

    def test_edge_confidence_reads_only_float(self, graph_storage):
        """_edge_confidence: floats/ints pass through, everything else -> 1.0."""
        assert graph_storage._edge_confidence({"resolver_confidence": 0.75}) == 0.75
        assert graph_storage._edge_confidence({"resolver_confidence": 1}) == 1.0
        assert graph_storage._edge_confidence({}) == 1.0
        assert graph_storage._edge_confidence({"confidence": "ambiguous"}) == 1.0
        assert graph_storage._edge_confidence({"resolver_confidence": "0.5"}) == 1.0
