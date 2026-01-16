"""
Unit tests for CodeGraphStorage.get_neighbors() with expanded relationship type support.

Tests verify that get_neighbors() supports all 21 relationship types beyond the
original "calls"/"called_by" limitation.
"""

import tempfile

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
