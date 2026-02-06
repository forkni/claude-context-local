"""Unit tests for CodeRelationshipAnalyzer relationship extraction.

Tests the core relationship extraction logic including:
- Forward relationships (parent_classes, uses_types, imports)
- Reverse relationships (child_classes, used_as_type_in, imported_by)
- Edge case handling and graceful degradation
"""

from unittest.mock import Mock

import pytest

from mcp_server.tools.code_relationship_analyzer import CodeRelationshipAnalyzer


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_searcher():
    """Create a mock searcher with get_by_chunk_id method."""
    searcher = Mock()
    searcher.index_manager = Mock()
    return searcher


@pytest.fixture
def mock_graph():
    """Create a mock graph storage with relationship edges."""
    graph = Mock()
    return graph


@pytest.fixture
def impact_analyzer(mock_searcher, mock_graph):
    """Create an CodeRelationshipAnalyzer instance with mocked dependencies."""
    # Configure mock to explicitly NOT have dense_index attribute
    # This prevents symbol_cache auto-creation in CodeRelationshipAnalyzer.__init__
    del mock_searcher.dense_index
    del mock_searcher.symbol_cache
    analyzer = CodeRelationshipAnalyzer(searcher=mock_searcher)
    analyzer.graph = mock_graph
    return analyzer


# ============================================================================
# REVERSE RELATIONSHIP TESTS - child_classes
# ============================================================================


def test_reverse_inherits_found_by_symbol_name(
    impact_analyzer, mock_graph, mock_searcher
):
    """Test child_classes reverse relationship using symbol name lookup.

    Scenario:
        - Our chunk: models.py:10-30:class:Parent (defines Parent class)
        - Graph has edge: models.py:40-60:class:Child → "Parent" (name, not chunk_id)
        - Should find Child when looking up reverse relationships for Parent
    """
    # Setup: Our chunk is the Parent class
    parent_chunk_id = "models.py:10-30:class:Parent"
    child_chunk_id = "models.py:40-60:class:Child"

    # Graph has NO edges to full chunk_id (backward compat check returns empty)
    mock_graph.get_callees.return_value = []
    mock_graph.get_callers.side_effect = lambda target: {
        parent_chunk_id: [],  # No edges to full chunk_id
        "Parent": [child_chunk_id],  # Edge to symbol name
    }.get(target, [])

    # Edge data
    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (child_chunk_id, "Parent"): {
            "relationship_type": "inherits",
            "line_number": 40,
            "confidence": 1.0,
        }
    }.get((source, target))

    # Child chunk lookup
    mock_child = Mock()
    mock_child.chunk_id = child_chunk_id
    mock_child.metadata = {
        "file": "models.py",
        "start_line": 40,
        "end_line": 60,
        "chunk_type": "class",
    }
    mock_child.name = "Child"

    mock_searcher.get_by_chunk_id.side_effect = lambda cid: {
        child_chunk_id: mock_child
    }.get(cid)

    # Execute
    result = impact_analyzer._extract_relationships(parent_chunk_id)

    # Verify
    assert "child_classes" in result
    assert len(result["child_classes"]) == 1

    child_rel = result["child_classes"][0]
    assert child_rel["chunk_id"] == child_chunk_id
    assert child_rel["file"] == "models.py"
    assert child_rel["relationship_type"] == "inherits"
    assert child_rel["line"] == 40


def test_reverse_inherits_graceful_degradation(
    impact_analyzer, mock_graph, mock_searcher
):
    """Test graceful degradation when source chunk lookup fails.

    Scenario:
        - Graph has edge but source chunk not found in index
        - Should return partial info without crashing
    """
    parent_chunk_id = "models.py:10-30:class:Parent"
    child_chunk_id = "models.py:40-60:class:Child"

    mock_graph.get_callees.return_value = []
    mock_graph.get_callers.side_effect = lambda target: {
        "Parent": [child_chunk_id]
    }.get(target, [])

    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (child_chunk_id, "Parent"): {
            "relationship_type": "inherits",
            "line_number": 40,
            "confidence": 1.0,
        }
    }.get((source, target))

    # Source chunk not found
    mock_searcher.get_by_chunk_id.return_value = None

    # Execute
    result = impact_analyzer._extract_relationships(parent_chunk_id)

    # Verify: Should have partial info
    assert "child_classes" in result
    assert len(result["child_classes"]) == 1

    child_rel = result["child_classes"][0]
    assert child_rel["source_chunk_id"] == child_chunk_id
    assert child_rel["relationship_type"] == "inherits"
    assert "note" in child_rel
    assert "not found" in child_rel["note"].lower()


# ============================================================================
# REVERSE RELATIONSHIP TESTS - used_as_type_in
# ============================================================================


def test_reverse_uses_type_found_by_symbol_name(
    impact_analyzer, mock_graph, mock_searcher
):
    """Test used_as_type_in reverse relationship using symbol name lookup.

    Scenario:
        - Our chunk: models.py:50-70:class:User (defines User class)
        - Graph has edge: service.py:10-20:function:process → "User" (type name)
        - Should find process() when looking up reverse relationships for User
    """
    user_chunk_id = "models.py:50-70:class:User"
    process_chunk_id = "service.py:10-20:function:process"

    mock_graph.get_callees.return_value = []
    mock_graph.get_callers.side_effect = lambda target: {
        "User": [process_chunk_id]
    }.get(target, [])

    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (process_chunk_id, "User"): {
            "relationship_type": "uses_type",
            "line_number": 15,
            "confidence": 1.0,
            "metadata": {"annotation_location": "parameter"},
        }
    }.get((source, target))

    # Process chunk lookup
    mock_process = Mock()
    mock_process.chunk_id = process_chunk_id
    mock_process.metadata = {
        "file": "service.py",
        "start_line": 10,
        "end_line": 20,
        "chunk_type": "function",
    }
    mock_process.name = "process"

    mock_searcher.get_by_chunk_id.side_effect = lambda cid: {
        process_chunk_id: mock_process
    }.get(cid)

    # Execute
    result = impact_analyzer._extract_relationships(user_chunk_id)

    # Verify
    assert "used_as_type_in" in result
    assert len(result["used_as_type_in"]) == 1

    usage_rel = result["used_as_type_in"][0]
    assert usage_rel["chunk_id"] == process_chunk_id
    assert usage_rel["file"] == "service.py"
    assert usage_rel["relationship_type"] == "uses_type"
    assert usage_rel["line"] == 15


def test_reverse_uses_type_multiple_usages(impact_analyzer, mock_graph, mock_searcher):
    """Test multiple functions using the same type."""
    user_chunk_id = "models.py:50-70:class:User"
    func1_chunk_id = "service.py:10-20:function:create_user"
    func2_chunk_id = "service.py:30-40:function:update_user"
    func3_chunk_id = "api.py:15-25:function:get_user"

    mock_graph.get_callees.return_value = []
    mock_graph.get_callers.side_effect = lambda target: {
        "User": [func1_chunk_id, func2_chunk_id, func3_chunk_id]
    }.get(target, [])

    # Setup edge data for all three functions
    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (func1_chunk_id, "User"): {
            "relationship_type": "uses_type",
            "line_number": 10,
            "confidence": 1.0,
        },
        (func2_chunk_id, "User"): {
            "relationship_type": "uses_type",
            "line_number": 30,
            "confidence": 1.0,
        },
        (func3_chunk_id, "User"): {
            "relationship_type": "uses_type",
            "line_number": 15,
            "confidence": 1.0,
        },
    }.get((source, target))

    # Mock all three chunks
    mock_func1 = Mock(
        chunk_id=func1_chunk_id,
        metadata={
            "file": "service.py",
            "start_line": 10,
            "end_line": 20,
            "chunk_type": "function",
        },
        name="create_user",
    )
    mock_func2 = Mock(
        chunk_id=func2_chunk_id,
        metadata={
            "file": "service.py",
            "start_line": 30,
            "end_line": 40,
            "chunk_type": "function",
        },
        name="update_user",
    )
    mock_func3 = Mock(
        chunk_id=func3_chunk_id,
        metadata={
            "file": "api.py",
            "start_line": 15,
            "end_line": 25,
            "chunk_type": "function",
        },
        name="get_user",
    )

    mock_searcher.get_by_chunk_id.side_effect = lambda cid: {
        func1_chunk_id: mock_func1,
        func2_chunk_id: mock_func2,
        func3_chunk_id: mock_func3,
    }.get(cid)

    # Execute
    result = impact_analyzer._extract_relationships(user_chunk_id)

    # Verify
    assert "used_as_type_in" in result
    assert len(result["used_as_type_in"]) == 3

    # All three functions should be present
    chunk_ids = {rel["chunk_id"] for rel in result["used_as_type_in"]}
    assert chunk_ids == {func1_chunk_id, func2_chunk_id, func3_chunk_id}


# ============================================================================
# REVERSE RELATIONSHIP TESTS - imported_by
# ============================================================================


def test_reverse_imports_found_by_symbol_name(
    impact_analyzer, mock_graph, mock_searcher
):
    """Test imported_by reverse relationship using symbol name lookup.

    Scenario:
        - Our chunk: utils.py:1-10:function:helper (defines helper function)
        - Graph has edge: main.py:5-15:function:main → "utils.helper" (import name)
        - Should find main() when looking up reverse relationships for helper
    """
    helper_chunk_id = "utils.py:1-10:function:helper"
    main_chunk_id = "main.py:5-15:function:main"

    mock_graph.get_callees.return_value = []
    mock_graph.get_callers.side_effect = lambda target: {"helper": [main_chunk_id]}.get(
        target, []
    )

    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (main_chunk_id, "helper"): {
            "relationship_type": "imports",
            "line_number": 1,
            "confidence": 1.0,
            "metadata": {"import_type": "from", "module": "utils"},
        }
    }.get((source, target))

    # Main chunk lookup
    mock_main = Mock()
    mock_main.chunk_id = main_chunk_id
    mock_main.metadata = {
        "file": "main.py",
        "start_line": 5,
        "end_line": 15,
        "chunk_type": "function",
    }
    mock_main.name = "main"

    mock_searcher.get_by_chunk_id.side_effect = lambda cid: {
        main_chunk_id: mock_main
    }.get(cid)

    # Execute
    result = impact_analyzer._extract_relationships(helper_chunk_id)

    # Verify
    assert "imported_by" in result
    assert len(result["imported_by"]) == 1

    import_rel = result["imported_by"][0]
    assert import_rel["chunk_id"] == main_chunk_id
    assert import_rel["file"] == "main.py"
    assert import_rel["relationship_type"] == "imports"


# ============================================================================
# FORWARD RELATIONSHIP TESTS
# ============================================================================


def test_forward_uses_type(impact_analyzer, mock_graph, mock_searcher):
    """Test forward uses_type relationship (function using a type).

    Scenario:
        - Our chunk: service.py:10-20:function:process
        - Graph has edge: service.py:10-20:function:process → "User" (type name)
    """
    process_chunk_id = "service.py:10-20:function:process"

    mock_graph.get_callees.return_value = ["User", "int", "str"]
    mock_graph.get_callers.return_value = []

    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (process_chunk_id, "User"): {
            "relationship_type": "uses_type",
            "line_number": 10,
            "confidence": 1.0,
            "metadata": {"annotation_location": "parameter"},
        },
        (process_chunk_id, "int"): {
            "relationship_type": "uses_type",
            "line_number": 10,
            "confidence": 1.0,
            "metadata": {"annotation_location": "parameter"},
        },
        (process_chunk_id, "str"): {
            "relationship_type": "uses_type",
            "line_number": 12,
            "confidence": 1.0,
            "metadata": {"annotation_location": "return"},
        },
    }.get((source, target))

    # Execute
    result = impact_analyzer._extract_relationships(process_chunk_id)

    # Verify
    assert "uses_types" in result
    assert len(result["uses_types"]) == 3

    type_names = {rel["target_name"] for rel in result["uses_types"]}
    assert type_names == {"User", "int", "str"}

    # Verify metadata is preserved
    user_rel = next(r for r in result["uses_types"] if r["target_name"] == "User")
    assert user_rel["metadata"]["annotation_location"] == "parameter"


def test_forward_imports(impact_analyzer, mock_graph, mock_searcher):
    """Test forward imports relationship."""
    main_chunk_id = "main.py:1-50:function:main"

    mock_graph.get_callees.return_value = ["os", "sys", "typing.List"]
    mock_graph.get_callers.return_value = []

    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (main_chunk_id, "os"): {
            "relationship_type": "imports",
            "line_number": 1,
            "confidence": 1.0,
            "metadata": {"import_type": "import"},
        },
        (main_chunk_id, "sys"): {
            "relationship_type": "imports",
            "line_number": 2,
            "confidence": 1.0,
            "metadata": {"import_type": "import"},
        },
        (main_chunk_id, "typing.List"): {
            "relationship_type": "imports",
            "line_number": 3,
            "confidence": 1.0,
            "metadata": {"import_type": "from"},
        },
    }.get((source, target))

    # Execute
    result = impact_analyzer._extract_relationships(main_chunk_id)

    # Verify
    assert "imports" in result
    assert len(result["imports"]) == 3

    import_names = {rel["target_name"] for rel in result["imports"]}
    assert import_names == {"os", "sys", "typing.List"}


def test_forward_inherits_with_fallback(impact_analyzer, mock_graph, mock_searcher):
    """Test forward inherits relationship with graceful fallback.

    Scenario:
        - Our chunk: Child class
        - Inherits from "Parent" (name, not chunk_id)
        - Parent not found in index → should use graceful degradation
    """
    child_chunk_id = "models.py:40-60:class:Child"

    mock_graph.get_callees.return_value = ["Parent", "BaseMixin"]
    mock_graph.get_callers.return_value = []

    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (child_chunk_id, "Parent"): {
            "relationship_type": "inherits",
            "line_number": 40,
            "confidence": 1.0,
        },
        (child_chunk_id, "BaseMixin"): {
            "relationship_type": "inherits",
            "line_number": 40,
            "confidence": 1.0,
        },
    }.get((source, target))

    # Neither parent found in index
    mock_searcher.get_by_chunk_id.return_value = None

    # Execute
    result = impact_analyzer._extract_relationships(child_chunk_id)

    # Verify: Should use graceful degradation
    assert "parent_classes" in result
    assert len(result["parent_classes"]) == 2

    parent_rel = next(
        r for r in result["parent_classes"] if r["target_name"] == "Parent"
    )
    assert parent_rel["target_name"] == "Parent"
    assert "note" in parent_rel
    assert "not in index" in parent_rel["note"].lower()


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_no_graph_returns_empty(impact_analyzer, mock_searcher):
    """Test that when graph is None, empty dict is returned."""
    impact_analyzer.graph = None

    result = impact_analyzer._extract_relationships("some_chunk_id")

    assert result == {}


def test_edge_data_validation(impact_analyzer, mock_graph, mock_searcher):
    """Test that missing edge data is handled gracefully."""
    chunk_id = "test.py:1-10:function:test"

    mock_graph.get_callees.return_value = ["Target"]
    mock_graph.get_callers.return_value = []

    # Edge exists but get_edge_data returns None
    mock_graph.get_edge_data.return_value = None

    # Execute - should not crash
    result = impact_analyzer._extract_relationships(chunk_id)

    # Verify: No relationships added (edge data was None)
    assert all(len(v) == 0 for v in result.values())


def test_skip_legacy_calls_relationships(impact_analyzer, mock_graph, mock_searcher):
    """Test that legacy 'calls' relationships are skipped."""
    chunk_id = "test.py:1-10:function:test"

    mock_graph.get_callees.return_value = ["target1"]
    mock_graph.get_callers.return_value = ["source1"]

    # Both edges are legacy 'calls' type
    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (chunk_id, "target1"): {
            "relationship_type": "calls",
            "line_number": 5,
        },
        ("source1", chunk_id): {
            "type": "calls",  # Old format
            "line": 3,
        },
    }.get((source, target))

    # Execute
    result = impact_analyzer._extract_relationships(chunk_id)

    # Verify: All relationship lists should be empty (calls were skipped)
    assert all(len(v) == 0 for v in result.values())


def test_symbol_name_extraction(impact_analyzer, mock_graph, mock_searcher):
    """Test that symbol name is correctly extracted from chunk_id."""
    # Chunk with complex name
    chunk_id = "deep/path/file.py:100-200:class:ComplexClassName"

    mock_graph.get_callees.return_value = []
    mock_graph.get_callers.side_effect = lambda target: {
        "ComplexClassName": ["user_chunk"]  # Found by symbol name
    }.get(target, [])

    mock_graph.get_edge_data.side_effect = lambda source, target: {
        ("user_chunk", "ComplexClassName"): {
            "relationship_type": "uses_type",
            "line_number": 10,
            "confidence": 1.0,
        }
    }.get((source, target))

    mock_user = Mock(
        chunk_id="user_chunk",
        metadata={
            "file": "user.py",
            "start_line": 10,
            "end_line": 20,
            "chunk_type": "function",
        },
        name="use_it",
    )
    mock_searcher.get_by_chunk_id.return_value = mock_user

    # Execute
    result = impact_analyzer._extract_relationships(chunk_id)

    # Verify: Found by symbol name, not full chunk_id
    assert len(result["used_as_type_in"]) == 1


# ============================================================================
# EXCLUDE_DIRS FILTER TESTS (Issue #4)
# ============================================================================


def test_analyze_impact_filters_similar_code_by_exclude_dirs(
    impact_analyzer, mock_searcher, mock_graph
):
    """Test that similar_code results respect exclude_dirs filter (Issue #4)."""
    target_id = "src/main.py:10-20:function:process"

    # Mock direct callers (empty for this test)
    mock_graph.get_callers.return_value = []
    mock_graph.get_callees.return_value = []

    # Mock similar_code results - some from tests/, some from src/
    mock_similar_1 = Mock()
    mock_similar_1.chunk_id = "tests/test_main.py:5-15:function:test_process"
    mock_similar_1.file_path = "tests/test_main.py"
    mock_similar_1.relative_path = "tests/test_main.py"
    mock_similar_1.start_line = 5
    mock_similar_1.end_line = 15
    mock_similar_1.chunk_type = "function"
    mock_similar_1.similarity_score = 0.95

    mock_similar_2 = Mock()
    mock_similar_2.chunk_id = "src/utils.py:30-40:function:helper"
    mock_similar_2.file_path = "src/utils.py"
    mock_similar_2.relative_path = "src/utils.py"
    mock_similar_2.start_line = 30
    mock_similar_2.end_line = 40
    mock_similar_2.chunk_type = "function"
    mock_similar_2.similarity_score = 0.85

    mock_searcher.find_similar_to_chunk.return_value = [
        mock_similar_1,
        mock_similar_2,
    ]

    # Execute with exclude_dirs
    report = impact_analyzer.analyze_impact(chunk_id=target_id, exclude_dirs=["tests/"])

    # Verify: Only src/ result should be included, tests/ should be filtered out
    assert len(report.similar_code) == 1
    assert report.similar_code[0]["file"] == "src/utils.py"
    assert "tests/" not in report.similar_code[0]["file"]


def test_extract_relationships_filters_by_exclude_dirs(
    impact_analyzer, mock_graph, mock_searcher
):
    """Test that _extract_relationships applies exclude_dirs filter to all relationship types (Issue #4)."""
    chunk_id = "src/models.py:10-30:class:Parent"

    # Setup graph with relationships pointing to both src/ and tests/ files
    child_in_src = "src/child.py:40-60:class:ChildSrc"
    child_in_tests = "tests/test_child.py:10-30:class:ChildTest"

    mock_graph.get_callees.return_value = []
    mock_graph.get_callers.side_effect = lambda target: {
        chunk_id: [],
        "Parent": [child_in_src, child_in_tests],
    }.get(target, [])

    # Edge data for both children
    mock_graph.get_edge_data.side_effect = lambda source, target: {
        (child_in_src, "Parent"): {
            "relationship_type": "inherits",
            "line_number": 40,
            "confidence": 1.0,
        },
        (child_in_tests, "Parent"): {
            "relationship_type": "inherits",
            "line_number": 10,
            "confidence": 1.0,
        },
    }.get((source, target))

    # Mock chunk lookups
    mock_child_src = Mock()
    mock_child_src.chunk_id = child_in_src
    mock_child_src.metadata = {
        "file": "src/child.py",
        "start_line": 40,
        "end_line": 60,
        "chunk_type": "class",
    }
    mock_child_src.name = "ChildSrc"

    mock_child_tests = Mock()
    mock_child_tests.chunk_id = child_in_tests
    mock_child_tests.metadata = {
        "file": "tests/test_child.py",
        "start_line": 10,
        "end_line": 30,
        "chunk_type": "class",
    }
    mock_child_tests.name = "ChildTest"

    mock_searcher.get_by_chunk_id.side_effect = lambda cid: {
        child_in_src: mock_child_src,
        child_in_tests: mock_child_tests,
    }.get(cid)

    # Execute with exclude_dirs
    result = impact_analyzer._extract_relationships(chunk_id, exclude_dirs=["tests/"])

    # Verify: Only src/ child should be included, tests/ child filtered out
    assert "child_classes" in result
    assert len(result["child_classes"]) == 1
    assert result["child_classes"][0]["file"] == "src/child.py"
    # Ensure tests/ file is not in results
    for rel in result["child_classes"]:
        assert "tests/" not in rel.get("file", "")


def test_find_connections_filters_indirect_callers_with_missing_metadata(
    impact_analyzer, mock_graph, mock_searcher
):
    """Test indirect_callers filtering works even when chunk metadata is missing (Issue 3).

    Regression test for: Empty file path from missing metadata bypasses exclude_dirs filter.
    The fix extracts file path from chunk_id as fallback.
    """
    target_id = "src/api.py:10-20:function:endpoint"
    direct_caller = "src/service.py:30-40:function:service_call"
    # Indirect callers: one has metadata, one missing (empty file path)
    indirect_with_metadata = "tools/batch.py:50-60:function:batch_process"
    indirect_without_metadata = "tools/helper.py:70-80:function:helper"

    # Setup graph structure: target <- direct <- indirect_callers
    mock_graph.get_callers.side_effect = lambda target_name: {
        target_id: [direct_caller],
        direct_caller: [indirect_with_metadata, indirect_without_metadata],
        "service_call": [indirect_with_metadata, indirect_without_metadata],
    }.get(target_name, [])

    mock_graph.get_callees.return_value = []

    # Mock target chunk (the analyzed endpoint)
    mock_target = Mock()
    mock_target.chunk_id = target_id
    mock_target.metadata = {
        "file": "src/api.py",
        "start_line": 10,
        "end_line": 20,
        "chunk_type": "function",
    }
    mock_target.name = "endpoint"

    # Mock direct caller chunk (has metadata)
    mock_direct = Mock()
    mock_direct.chunk_id = direct_caller
    mock_direct.metadata = {
        "file": "src/service.py",
        "start_line": 30,
        "end_line": 40,
        "chunk_type": "function",
    }
    mock_direct.name = "service_call"

    # Mock indirect caller WITH metadata
    mock_indirect_1 = Mock()
    mock_indirect_1.chunk_id = indirect_with_metadata
    mock_indirect_1.metadata = {
        "file": "tools/batch.py",  # Has file in metadata
        "start_line": 50,
        "end_line": 60,
        "chunk_type": "function",
    }
    mock_indirect_1.name = "batch_process"

    # Mock indirect caller WITHOUT metadata (empty file path)
    mock_indirect_2 = Mock()
    mock_indirect_2.chunk_id = indirect_without_metadata
    mock_indirect_2.metadata = {
        # "file" key missing - THIS IS THE EDGE CASE
        "start_line": 70,
        "end_line": 80,
        "chunk_type": "function",
    }
    mock_indirect_2.name = "helper"

    mock_searcher.get_by_chunk_id.side_effect = lambda cid: {
        target_id: mock_target,
        direct_caller: mock_direct,
        indirect_with_metadata: mock_indirect_1,
        indirect_without_metadata: mock_indirect_2,
    }.get(cid)

    # Execute with exclude_dirs=["tools/"]
    report = impact_analyzer.analyze_impact(
        chunk_id=target_id, exclude_dirs=["tools/"], max_depth=3
    )

    # Verify: Both indirect callers should be filtered out (both in tools/)
    # BEFORE FIX: indirect_without_metadata would pass filter (empty file path)
    # AFTER FIX: File path extracted from chunk_id, properly filtered
    assert len(report.indirect_callers) == 0, (
        f"Expected 0 indirect callers (both in excluded 'tools/'), "
        f"got {len(report.indirect_callers)}: {[c['file'] for c in report.indirect_callers]}"
    )

    # Verify direct_callers still work (not in excluded dir)
    assert len(report.direct_callers) == 1
    assert report.direct_callers[0]["file"] == "src/service.py"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
