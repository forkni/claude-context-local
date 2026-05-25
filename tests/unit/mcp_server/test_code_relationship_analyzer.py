"""Unit tests for RelationshipAnalyzer relationship extraction.

Tests the core relationship extraction logic including:
- Forward relationships (parent_classes, uses_types, imports)
- Reverse relationships (child_classes, used_as_type_in, imported_by)
- Edge case handling and graceful degradation
"""

from unittest.mock import Mock

import pytest

from graph.graph_queries import RelationshipEntry
from search.relationship_analyzer import RelationshipAnalyzer


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
def mock_graph_engine():
    """Create a mock GraphQueryEngine."""
    engine = Mock()
    engine.get_relationships.return_value = []
    engine.get_direct_successors.return_value = []
    engine.get_stats.return_value = {}
    return engine


@pytest.fixture
def impact_analyzer(mock_searcher, mock_graph_engine):
    """Create a RelationshipAnalyzer instance with mocked dependencies."""
    # Prevent symbol_cache auto-creation from mock attributes
    del mock_searcher.dense_index
    del mock_searcher.symbol_cache
    return RelationshipAnalyzer(searcher=mock_searcher, graph_engine=mock_graph_engine)


# ============================================================================
# REVERSE RELATIONSHIP TESTS - child_classes
# ============================================================================


def test_reverse_inherits_found_by_symbol_name(impact_analyzer, mock_searcher):
    """Test child_classes reverse relationship from an inbound inherits entry.

    Scenario:
        - Our chunk: models.py:10-30:class:Parent (defines Parent class)
        - Graph yields an inbound edge: models.py:40-60:class:Child → Parent
        - Should find Child in child_classes
    """
    parent_chunk_id = "models.py:10-30:class:Parent"
    child_chunk_id = "models.py:40-60:class:Child"

    inbound = [
        RelationshipEntry(
            chunk_id=child_chunk_id,
            relationship_type="inherits",
            direction="inbound",
            depth=1,
            edge_data={"line_number": 40, "confidence": 1.0},
        )
    ]

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

    result = impact_analyzer._build_graph_relationships(
        parent_chunk_id, inbound, [], None
    )

    assert "child_classes" in result
    assert len(result["child_classes"]) == 1

    child_rel = result["child_classes"][0]
    assert child_rel["chunk_id"] == child_chunk_id
    assert child_rel["file"] == "models.py"
    assert child_rel["relationship_type"] == "inherits"
    assert child_rel["line"] == 40


def test_reverse_inherits_graceful_degradation(impact_analyzer, mock_searcher):
    """Test graceful degradation when source chunk lookup fails.

    Scenario:
        - Graph has an inbound edge but source chunk not found in index
        - Should return partial info without crashing
    """
    parent_chunk_id = "models.py:10-30:class:Parent"
    child_chunk_id = "models.py:40-60:class:Child"

    inbound = [
        RelationshipEntry(
            chunk_id=child_chunk_id,
            relationship_type="inherits",
            direction="inbound",
            depth=1,
            edge_data={"line_number": 40, "confidence": 1.0},
        )
    ]

    mock_searcher.get_by_chunk_id.return_value = None

    result = impact_analyzer._build_graph_relationships(
        parent_chunk_id, inbound, [], None
    )

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


def test_reverse_uses_type_found_by_symbol_name(impact_analyzer, mock_searcher):
    """Test used_as_type_in reverse relationship from an inbound uses_type entry.

    Scenario:
        - Our chunk: models.py:50-70:class:User (defines User class)
        - Graph yields an inbound edge: service.py:10-20:function:process uses User
        - Should find process() in used_as_type_in
    """
    user_chunk_id = "models.py:50-70:class:User"
    process_chunk_id = "service.py:10-20:function:process"

    inbound = [
        RelationshipEntry(
            chunk_id=process_chunk_id,
            relationship_type="uses_type",
            direction="inbound",
            depth=1,
            edge_data={
                "line_number": 15,
                "confidence": 1.0,
                "metadata": {"annotation_location": "parameter"},
            },
        )
    ]

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

    result = impact_analyzer._build_graph_relationships(
        user_chunk_id, inbound, [], None
    )

    assert "used_as_type_in" in result
    assert len(result["used_as_type_in"]) == 1

    usage_rel = result["used_as_type_in"][0]
    assert usage_rel["chunk_id"] == process_chunk_id
    assert usage_rel["file"] == "service.py"
    assert usage_rel["relationship_type"] == "uses_type"
    assert usage_rel["line"] == 15


def test_reverse_uses_type_multiple_usages(impact_analyzer, mock_searcher):
    """Test multiple functions using the same type."""
    user_chunk_id = "models.py:50-70:class:User"
    func1_chunk_id = "service.py:10-20:function:create_user"
    func2_chunk_id = "service.py:30-40:function:update_user"
    func3_chunk_id = "api.py:15-25:function:get_user"

    inbound = [
        RelationshipEntry(
            func1_chunk_id,
            "uses_type",
            "inbound",
            1,
            {"line_number": 10, "confidence": 1.0},
        ),
        RelationshipEntry(
            func2_chunk_id,
            "uses_type",
            "inbound",
            1,
            {"line_number": 30, "confidence": 1.0},
        ),
        RelationshipEntry(
            func3_chunk_id,
            "uses_type",
            "inbound",
            1,
            {"line_number": 15, "confidence": 1.0},
        ),
    ]

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

    result = impact_analyzer._build_graph_relationships(
        user_chunk_id, inbound, [], None
    )

    assert "used_as_type_in" in result
    assert len(result["used_as_type_in"]) == 3

    chunk_ids = {rel["chunk_id"] for rel in result["used_as_type_in"]}
    assert chunk_ids == {func1_chunk_id, func2_chunk_id, func3_chunk_id}


# ============================================================================
# REVERSE RELATIONSHIP TESTS - imported_by
# ============================================================================


def test_reverse_imports_found_by_symbol_name(impact_analyzer, mock_searcher):
    """Test imported_by reverse relationship from an inbound imports entry.

    Scenario:
        - Our chunk: utils.py:1-10:function:helper (defines helper function)
        - Graph yields an inbound edge: main.py:5-15:function:main imports helper
        - Should find main() in imported_by
    """
    helper_chunk_id = "utils.py:1-10:function:helper"
    main_chunk_id = "main.py:5-15:function:main"

    inbound = [
        RelationshipEntry(
            chunk_id=main_chunk_id,
            relationship_type="imports",
            direction="inbound",
            depth=1,
            edge_data={
                "line_number": 1,
                "confidence": 1.0,
                "metadata": {"import_type": "from", "module": "utils"},
            },
        )
    ]

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

    result = impact_analyzer._build_graph_relationships(
        helper_chunk_id, inbound, [], None
    )

    assert "imported_by" in result
    assert len(result["imported_by"]) == 1

    import_rel = result["imported_by"][0]
    assert import_rel["chunk_id"] == main_chunk_id
    assert import_rel["file"] == "main.py"
    assert import_rel["relationship_type"] == "imports"


# ============================================================================
# FORWARD RELATIONSHIP TESTS
# ============================================================================


def test_forward_uses_type(impact_analyzer, mock_searcher):
    """Test forward uses_type relationship (function using a type).

    Scenario:
        - Our chunk: service.py:10-20:function:process
        - Outbound edges to "User", "int", "str" (uses_type)
    """
    process_chunk_id = "service.py:10-20:function:process"

    outbound = [
        RelationshipEntry(
            "User",
            "uses_type",
            "outbound",
            1,
            {
                "line_number": 10,
                "confidence": 1.0,
                "metadata": {"annotation_location": "parameter"},
            },
        ),
        RelationshipEntry(
            "int",
            "uses_type",
            "outbound",
            1,
            {
                "line_number": 10,
                "confidence": 1.0,
                "metadata": {"annotation_location": "parameter"},
            },
        ),
        RelationshipEntry(
            "str",
            "uses_type",
            "outbound",
            1,
            {
                "line_number": 12,
                "confidence": 1.0,
                "metadata": {"annotation_location": "return"},
            },
        ),
    ]

    result = impact_analyzer._build_graph_relationships(
        process_chunk_id, [], outbound, None
    )

    assert "uses_types" in result
    assert len(result["uses_types"]) == 3

    type_names = {rel["target_name"] for rel in result["uses_types"]}
    assert type_names == {"User", "int", "str"}

    user_rel = next(r for r in result["uses_types"] if r["target_name"] == "User")
    assert user_rel["metadata"]["annotation_location"] == "parameter"


def test_forward_imports(impact_analyzer, mock_searcher):
    """Test forward imports relationship."""
    main_chunk_id = "main.py:1-50:function:main"

    outbound = [
        RelationshipEntry(
            "os",
            "imports",
            "outbound",
            1,
            {
                "line_number": 1,
                "confidence": 1.0,
                "metadata": {"import_type": "import"},
            },
        ),
        RelationshipEntry(
            "sys",
            "imports",
            "outbound",
            1,
            {
                "line_number": 2,
                "confidence": 1.0,
                "metadata": {"import_type": "import"},
            },
        ),
        RelationshipEntry(
            "typing.List",
            "imports",
            "outbound",
            1,
            {"line_number": 3, "confidence": 1.0, "metadata": {"import_type": "from"}},
        ),
    ]

    result = impact_analyzer._build_graph_relationships(
        main_chunk_id, [], outbound, None
    )

    assert "imports" in result
    assert len(result["imports"]) == 3

    import_names = {rel["target_name"] for rel in result["imports"]}
    assert import_names == {"os", "sys", "typing.List"}


def test_forward_inherits_with_fallback(impact_analyzer, mock_searcher):
    """Test forward inherits relationship with graceful fallback.

    Scenario:
        - Our chunk: Child class with two outbound inherits edges
        - Parent and BaseMixin not found in index → graceful degradation
    """
    child_chunk_id = "models.py:40-60:class:Child"

    outbound = [
        RelationshipEntry(
            "Parent", "inherits", "outbound", 1, {"line_number": 40, "confidence": 1.0}
        ),
        RelationshipEntry(
            "BaseMixin",
            "inherits",
            "outbound",
            1,
            {"line_number": 40, "confidence": 1.0},
        ),
    ]

    mock_searcher.get_by_chunk_id.return_value = None

    result = impact_analyzer._build_graph_relationships(
        child_chunk_id, [], outbound, None
    )

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


def test_no_relationships_returns_empty_lists(impact_analyzer):
    """Test that empty input produces all-empty relationship lists."""
    result = impact_analyzer._build_graph_relationships("some_chunk_id", [], [], None)

    assert all(len(v) == 0 for v in result.values())


def test_unknown_relationship_type_skipped(impact_analyzer):
    """Test that entries with unknown relationship types are skipped gracefully."""
    chunk_id = "test.py:1-10:function:test"

    outbound = [RelationshipEntry("Target", "unknown_edge_type", "outbound", 1, {})]

    result = impact_analyzer._build_graph_relationships(chunk_id, [], outbound, None)

    assert all(len(v) == 0 for v in result.values())


def test_skip_legacy_calls_relationships(impact_analyzer):
    """Test that 'calls' relationship entries are skipped (handled by caller enrichment)."""
    chunk_id = "test.py:1-10:function:test"

    outbound = [
        RelationshipEntry("target1", "calls", "outbound", 1, {"line_number": 5})
    ]
    inbound = [RelationshipEntry("source1", "calls", "inbound", 1, {"line_number": 3})]

    result = impact_analyzer._build_graph_relationships(
        chunk_id, inbound, outbound, None
    )

    assert all(len(v) == 0 for v in result.values())


def test_symbol_name_extraction(impact_analyzer, mock_searcher):
    """Test that inbound entries with arbitrary chunk_ids are correctly enriched."""
    chunk_id = "deep/path/file.py:100-200:class:ComplexClassName"

    inbound = [
        RelationshipEntry(
            "user_chunk",
            "uses_type",
            "inbound",
            1,
            {"line_number": 10, "confidence": 1.0},
        )
    ]

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

    result = impact_analyzer._build_graph_relationships(chunk_id, inbound, [], None)

    assert len(result["used_as_type_in"]) == 1


# ============================================================================
# EXCLUDE_DIRS FILTER TESTS (Issue #4)
# ============================================================================


def test_analyze_impact_filters_similar_code_by_exclude_dirs(
    impact_analyzer, mock_searcher, mock_graph_engine
):
    """Test that similar_code results respect exclude_dirs filter (Issue #4)."""
    target_id = "src/main.py:10-20:function:process"

    # Target chunk must be findable
    mock_target = Mock()
    mock_target.metadata = {
        "file": "src/main.py",
        "start_line": 10,
        "end_line": 20,
        "chunk_type": "function",
    }
    mock_searcher.get_by_chunk_id.return_value = mock_target

    # No callers from graph
    mock_graph_engine.get_relationships.return_value = []

    # similar_code results - one from tests/, one from src/
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

    report = impact_analyzer.analyze_impact(chunk_id=target_id, exclude_dirs=["tests/"])

    assert len(report.similar_code) == 1
