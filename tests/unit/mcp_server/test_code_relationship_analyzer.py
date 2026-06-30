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
    # Fix 2: source_chunk_id is cleared to "" when the chunk isn't in the store
    # so consumers can't accidentally re-query with a stale graph-node ID.
    assert child_rel["source_chunk_id"] == ""
    assert child_rel.get("resolvable") is False
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

    # similar_code results (thin SearchResult format) - one from tests/, one from src/
    mock_similar_1 = Mock()
    mock_similar_1.chunk_id = "tests/test_main.py:5-15:function:test_process"
    mock_similar_1.score = 0.95
    mock_similar_1.source = "similarity"
    mock_similar_1.metadata = {
        "relative_path": "tests/test_main.py",
        "file_path": "tests/test_main.py",
        "start_line": 5,
        "end_line": 15,
        "chunk_type": "function",
    }

    mock_similar_2 = Mock()
    mock_similar_2.chunk_id = "src/utils.py:30-40:function:helper"
    mock_similar_2.score = 0.85
    mock_similar_2.source = "similarity"
    mock_similar_2.metadata = {
        "relative_path": "src/utils.py",
        "file_path": "src/utils.py",
        "start_line": 30,
        "end_line": 40,
        "chunk_type": "function",
    }

    mock_searcher.find_similar_to_chunk.return_value = [
        mock_similar_1,
        mock_similar_2,
    ]

    report = impact_analyzer.analyze_impact(chunk_id=target_id, exclude_dirs=["tests/"])

    assert len(report.similar_code) == 1


# ============================================================================
# _resolve_target TESTS
# ============================================================================


def _make_mock_result(chunk_id: str, chunk_type: str = "function"):
    r = Mock()
    r.chunk_id = chunk_id
    r.metadata = {"chunk_type": chunk_type, "file": chunk_id.split(":")[0]}
    r.chunk_type = chunk_type
    r.file_path = chunk_id.split(":")[0]
    return r


class TestResolveTarget:
    """_resolve_target should prefer exact lookups over semantic search."""

    def _make_analyzer_with_caches(
        self, mock_searcher, symbol_cache=None, graph_storage=None
    ):
        """Build a RelationshipAnalyzer with optional pre-wired caches."""
        from graph.graph_queries import GraphQueryEngine
        from search.relationship_analyzer import RelationshipAnalyzer

        engine = None
        if graph_storage is not None:
            engine = Mock(spec=GraphQueryEngine)
            engine.storage = graph_storage

        # Inject symbol_cache by patching the constructor check
        analyzer = RelationshipAnalyzer(searcher=mock_searcher, graph_engine=engine)
        analyzer.symbol_cache = symbol_cache
        return analyzer

    def test_resolve_via_symbol_cache_does_not_call_search(self, mock_searcher):
        """Tier-1 exact lookup: symbol cache hit avoids calling searcher.search."""
        mock_cache = Mock()
        mock_cache.get_by_symbol_name.return_value = "pkg/mod.py:10-20:function:my_func"

        mock_result = _make_mock_result("pkg/mod.py:10-20:function:my_func", "function")
        mock_searcher.get_by_chunk_id.return_value = mock_result

        analyzer = self._make_analyzer_with_caches(
            mock_searcher, symbol_cache=mock_cache
        )
        result, cid = analyzer._resolve_target(None, "my_func", None)

        assert cid == "pkg/mod.py:10-20:function:my_func"
        mock_searcher.search.assert_not_called()

    def test_resolve_via_graph_lookup_does_not_call_search(self, mock_searcher):
        """Tier-2 exact lookup: graph name index hit avoids searcher.search."""
        # Symbol cache misses
        mock_cache = Mock()
        mock_cache.get_by_symbol_name.return_value = None

        # Graph storage hits
        mock_gs = Mock()
        mock_gs.get_nodes_by_name.return_value = ["pkg/mod.py:30-50:method:Foo.bar"]

        mock_result = _make_mock_result("pkg/mod.py:30-50:method:Foo.bar", "method")
        mock_searcher.get_by_chunk_id.return_value = mock_result

        analyzer = self._make_analyzer_with_caches(
            mock_searcher, symbol_cache=mock_cache, graph_storage=mock_gs
        )
        result, cid = analyzer._resolve_target(None, "bar", None)

        assert cid == "pkg/mod.py:30-50:method:Foo.bar"
        mock_searcher.search.assert_not_called()

    def test_resolve_via_graph_suffix_scan_class_qualified(self, mock_searcher):
        """Tier-2 suffix scan: chunk_id ending with '.method_name' is matched."""
        # Symbol cache misses; graph exact-name lookup also misses (key is qualified)
        mock_cache = Mock()
        mock_cache.get_by_symbol_name.return_value = None

        mock_gs = Mock()
        mock_gs.get_nodes_by_name.return_value = []  # "get_project_storage_dir" not in _name_index as bare

        # Graph nodes include the qualified chunk_id
        qualified_cid = "mcp_server/storage_manager.py:206-340:method:StorageManager.get_project_storage_dir"
        mock_gs.graph.nodes.return_value = [
            "scripts/list_projects_parseable.py:27-78:function:main",  # caller — should NOT match
            qualified_cid,
        ]

        mock_result = _make_mock_result(qualified_cid, "method")
        mock_searcher.get_by_chunk_id.return_value = mock_result

        analyzer = self._make_analyzer_with_caches(
            mock_searcher, symbol_cache=mock_cache, graph_storage=mock_gs
        )
        result, cid = analyzer._resolve_target(None, "get_project_storage_dir", None)

        assert cid == qualified_cid
        mock_searcher.search.assert_not_called()

    def test_resolve_semantic_fallback_prefers_method_over_class(self, mock_searcher):
        """Tier-3 semantic: inverted type priority picks method/function before class."""
        # Both exact tiers miss
        mock_cache = Mock()
        mock_cache.get_by_symbol_name.return_value = None
        mock_gs = Mock()
        mock_gs.get_nodes_by_name.return_value = []
        mock_gs.graph.nodes.return_value = []

        class_result = _make_mock_result("a.py:1-200:class:SearchFactory", "class")
        method_result = _make_mock_result(
            "b.py:10-20:method:StorageManager.get_project_storage_dir", "method"
        )
        mock_searcher.search.return_value = [class_result, method_result]
        mock_searcher.get_by_chunk_id.return_value = None

        analyzer = self._make_analyzer_with_caches(
            mock_searcher, symbol_cache=mock_cache, graph_storage=mock_gs
        )
        result, cid = analyzer._resolve_target(None, "get_project_storage_dir", None)

        assert "method" in cid or "method_result" not in cid
        assert result.chunk_type == "method"

    def test_resolve_name_matching_handles_class_qualified_method(self, mock_searcher):
        """Name-match filter accepts 'Foo.bar' when querying bare 'bar'."""
        # Both exact tiers miss → falls to semantic
        mock_cache = Mock()
        mock_cache.get_by_symbol_name.return_value = None
        mock_gs = Mock()
        mock_gs.get_nodes_by_name.return_value = []
        mock_gs.graph.nodes.return_value = []

        # chunk_id last segment is qualified
        qualified_method = _make_mock_result("file.py:10-20:method:Foo.bar", "method")
        # class result would win under old priority
        class_result = _make_mock_result("file.py:1-100:class:Foo", "class")
        mock_searcher.search.return_value = [class_result, qualified_method]
        mock_searcher.get_by_chunk_id.return_value = None

        analyzer = self._make_analyzer_with_caches(
            mock_searcher, symbol_cache=mock_cache, graph_storage=mock_gs
        )
        result, cid = analyzer._resolve_target(None, "bar", None)

        # The qualified method matches via .split(".")[-1] == "bar"; class does not match
        # so matching = [qualified_method], candidates = [qualified_method]
        assert cid == "file.py:10-20:method:Foo.bar"

    def test_resolve_symbol_not_found_raises(self, mock_searcher):
        """All tiers miss → SearchError raised."""
        from search.exceptions import SearchError

        mock_cache = Mock()
        mock_cache.get_by_symbol_name.return_value = None
        mock_gs = Mock()
        mock_gs.get_nodes_by_name.return_value = []
        mock_gs.graph.nodes.return_value = []
        mock_searcher.search.return_value = []

        analyzer = self._make_analyzer_with_caches(
            mock_searcher, symbol_cache=mock_cache, graph_storage=mock_gs
        )

        import pytest

        with pytest.raises(SearchError):
            analyzer._resolve_target(None, "nonexistent_symbol", None)

    # ------------------------------------------------------------------
    # Fix 1: stale chunk_id falls back to symbol resolution
    # ------------------------------------------------------------------

    def test_stale_chunk_id_falls_back_via_symbol_cache(self, mock_searcher):
        """A chunk_id that misses the store but whose symbol is in the cache resolves.

        Reproduces: find_connections('path:339-342:method:Cls.method') where the
        file was edited and the current chunk is at 'path:350-353:method:Cls.method'.
        The symbol cache maps 'Cls.method' → current chunk_id.
        """
        stale_id = "td_exporter/CUDAIPCExtension.py:339-342:method:CUDAIPCExtension.verbose_performance"
        current_id = "td_exporter/CUDAIPCExtension.py:350-353:method:CUDAIPCExtension.verbose_performance"

        mock_cache = Mock()
        mock_cache.get_by_symbol_name.return_value = current_id

        current_result = _make_mock_result(current_id, "method")
        mock_searcher.get_by_chunk_id.side_effect = lambda cid: (
            current_result if cid == current_id else None
        )

        analyzer = self._make_analyzer_with_caches(
            mock_searcher, symbol_cache=mock_cache
        )
        result, cid = analyzer._resolve_target(stale_id, None, None)

        assert cid == current_id
        assert result is current_result

    def test_stale_chunk_id_falls_back_via_semantic_search(self, mock_searcher):
        """A stale chunk_id falls through all the way to semantic search."""

        stale_id = "src/auth.py:10-20:method:AuthManager.validate"

        mock_cache = Mock()
        mock_cache.get_by_symbol_name.return_value = None
        mock_gs = Mock()
        mock_gs.get_nodes_by_name.return_value = []
        mock_gs.graph.nodes.return_value = []

        current_result = _make_mock_result(
            "src/auth.py:15-25:method:AuthManager.validate", "method"
        )
        mock_searcher.get_by_chunk_id.return_value = None
        mock_searcher.search.return_value = [current_result]

        analyzer = self._make_analyzer_with_caches(
            mock_searcher, symbol_cache=mock_cache, graph_storage=mock_gs
        )
        result, cid = analyzer._resolve_target(stale_id, None, None)

        assert cid == "src/auth.py:15-25:method:AuthManager.validate"
        mock_searcher.search.assert_called_once()

    def test_stale_chunk_id_with_too_few_parts_still_raises(self, mock_searcher):
        """A chunk_id with < 4 colon-parts that misses the store raises immediately."""
        from search.exceptions import SearchError

        short_id = "src/auth.py:10-20"  # only 2 parts — no symbol derivable
        mock_searcher.get_by_chunk_id.return_value = None

        analyzer = self._make_analyzer_with_caches(mock_searcher)
        with pytest.raises(SearchError, match="Chunk not found"):
            analyzer._resolve_target(short_id, None, None)


# ============================================================================
# Fix 2: unresolvable graph-edge IDs marked as non-queryable
# ============================================================================


class TestLeakPrevention:
    """_enrich_forward/_enrich_reverse should not emit queryable dead chunk_ids."""

    def _make_analyzer(self, get_by_chunk_id_return=None):
        """Build a minimal RelationshipAnalyzer with a mock searcher."""
        from search.relationship_analyzer import RelationshipAnalyzer

        searcher = Mock()
        # Set symbol_cache to None so RelationshipAnalyzer doesn't pick up
        # a live Mock from dense_index.symbol_cache (which would auto-return
        # Mocks instead of None and confuse the resolution tiers).
        searcher.dense_index = Mock()
        searcher.dense_index.symbol_cache = None
        searcher.symbol_cache = None
        searcher.get_by_chunk_id.return_value = get_by_chunk_id_return

        engine = Mock()
        engine.get_relationships.return_value = []
        engine.get_direct_successors.return_value = []
        engine.get_stats.return_value = {}

        return RelationshipAnalyzer(searcher=searcher, graph_engine=engine)

    def test_enrich_reverse_miss_has_empty_source_chunk_id(self):
        """_enrich_reverse: when source chunk is not in store, source_chunk_id must be ''."""
        analyzer = self._make_analyzer(get_by_chunk_id_return=None)
        entry = RelationshipEntry(
            chunk_id="some/file.py:100-120:method:Cls.gone",
            relationship_type="inherits",
            direction="inbound",
            depth=1,
            edge_data={"line_number": 100, "confidence": 1.0},
        )

        result = analyzer._enrich_reverse(entry, lambda fp: True)

        assert result is not None
        assert result.get("source_chunk_id") == ""
        assert result.get("resolvable") is False
        assert "note" in result

    def test_enrich_forward_inherits_miss_has_no_live_chunk_id(self):
        """_enrich_forward: when target chunk is not in store, chunk_id must not be a live ID."""
        analyzer = self._make_analyzer(get_by_chunk_id_return=None)
        entry = RelationshipEntry(
            chunk_id="some/file.py:50-60:class:MissingBase",
            relationship_type="inherits",
            direction="outbound",
            depth=1,
            edge_data={"line_number": 50, "confidence": 1.0},
        )

        result = analyzer._enrich_forward(entry, lambda fp: True)

        assert result is not None
        # chunk_id must be absent or empty — never a non-empty unresolvable id
        chunk_id = result.get("chunk_id", "")
        assert chunk_id == ""
        assert result.get("resolvable") is False
