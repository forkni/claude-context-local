"""Unit tests for GraphIntegration class."""

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from search.graph_integration import GraphIntegration


class TestGraphIntegration(TestCase):
    """Test GraphIntegration functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = Path(self.temp_dir) / "storage"
        self.storage_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_init_with_project_id(self, mock_graph_storage):
        """Test initialization with project ID."""
        project_id = "test_project"
        graph = GraphIntegration(project_id, self.storage_dir)

        # Should initialize graph storage
        mock_graph_storage.assert_called_once_with(
            project_id=project_id, storage_dir=self.storage_dir.parent
        )
        self.assertIsNotNone(graph.storage)
        self.assertTrue(graph.is_available)

    def test_init_without_project_id(self):
        """Test initialization without project ID."""
        graph = GraphIntegration(None, self.storage_dir)

        # Should not initialize graph storage
        self.assertIsNone(graph.storage)
        self.assertFalse(graph.is_available)
        self.assertEqual(graph.node_count, 0)

    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", False)
    def test_init_when_unavailable(self):
        """Test initialization when graph storage is unavailable."""
        graph = GraphIntegration("test_project", self.storage_dir)

        # Should not initialize graph storage
        self.assertIsNone(graph.storage)
        self.assertFalse(graph.is_available)

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_add_chunk_function(self, mock_graph_storage):
        """Test adding a function chunk to graph."""
        mock_storage = Mock()
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)

        metadata = {
            "chunk_type": "function",
            "name": "test_function",
            "file_path": "test.py",
            "language": "python",
            "calls": [
                {
                    "callee_name": "helper",
                    "line_number": 10,
                    "is_method_call": False,
                }
            ],
            "relationships": [],
        }

        graph.add_chunk("test.py:1-10:function:test_function", metadata)

        # Should add node
        mock_storage.add_node.assert_called_once_with(
            chunk_id="test.py:1-10:function:test_function",
            name="test_function",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )

        # Should add call edge
        mock_storage.add_call_edge.assert_called_once_with(
            caller_id="test.py:1-10:function:test_function",
            callee_name="helper",
            line_number=10,
            is_method_call=False,
        )

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_add_chunk_class(self, mock_graph_storage):
        """Test adding a class chunk to graph."""
        mock_storage = Mock()
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)

        metadata = {
            "chunk_type": "class",
            "name": "TestClass",
            "file_path": "test.py",
            "language": "python",
            "calls": [],
            "relationships": [],
        }

        graph.add_chunk("test.py:1-10:class:TestClass", metadata)

        # Should add node
        mock_storage.add_node.assert_called_once()

    def test_add_chunk_without_storage(self):
        """Test adding chunk when storage is not available."""
        graph = GraphIntegration(None, self.storage_dir)

        metadata = {
            "chunk_type": "function",
            "name": "test_function",
        }

        # Should not raise error
        graph.add_chunk("test.py:1-10:function:test_function", metadata)

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_add_chunk_non_semantic_type(self, mock_graph_storage):
        """Test adding non-semantic chunk type."""
        mock_storage = Mock()
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)

        metadata = {
            "chunk_type": "comment",
            "name": "test_comment",
            "file_path": "test.py",
            "language": "python",
            "calls": [],
            "relationships": [],
        }

        graph.add_chunk("test.py:1-10:comment:test_comment", metadata)

        # Should not add node for non-semantic type
        mock_storage.add_node.assert_not_called()

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_save_with_nodes(self, mock_graph_storage):
        """Test saving graph with nodes."""
        mock_storage = Mock()
        mock_storage.__len__ = Mock(return_value=5)
        mock_storage.graph_path = Path("/test/graph.db")
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)
        graph.save()

        # Should call save
        mock_storage.save.assert_called_once()

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_save_without_nodes(self, mock_graph_storage):
        """Test saving graph without nodes."""
        mock_storage = Mock()
        mock_storage.__len__ = Mock(return_value=0)
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)
        graph.save()

        # Should not call save for empty graph
        mock_storage.save.assert_not_called()

    def test_save_without_storage(self):
        """Test saving when storage is not available."""
        graph = GraphIntegration(None, self.storage_dir)

        # Should not raise error
        graph.save()

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_clear(self, mock_graph_storage):
        """Test clearing graph."""
        mock_storage = Mock()
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)
        graph.clear()

        # Should call clear
        mock_storage.clear.assert_called_once()

    def test_clear_without_storage(self):
        """Test clearing when storage is not available."""
        graph = GraphIntegration(None, self.storage_dir)

        # Should not raise error
        graph.clear()

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_node_count(self, mock_graph_storage):
        """Test node count property."""
        mock_storage = Mock()
        mock_storage.__len__ = Mock(return_value=10)
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)

        self.assertEqual(graph.node_count, 10)
        self.assertEqual(len(graph), 10)

    def test_node_count_without_storage(self):
        """Test node count when storage is not available."""
        graph = GraphIntegration(None, self.storage_dir)

        self.assertEqual(graph.node_count, 0)
        self.assertEqual(len(graph), 0)

    def test_split_block_disambiguation_logic(self):
        """Test that split_block disambiguation resolves to first block by start_line."""
        # Create test candidates that simulate split_blocks
        candidates = [
            "test.py:201-250:split_block:process_data",
            "test.py:100-150:split_block:process_data",
            "test.py:151-200:split_block:process_data",
        ]

        # Filter split_blocks (all candidates are split_blocks)
        split_blocks = [c for c in candidates if ":split_block:" in c]
        assert len(split_blocks) == len(candidates)  # All are split_blocks

        # Sort by start_line
        def _start_line(chunk_id: str) -> int:
            parts = chunk_id.split(":")
            if len(parts) >= 2:
                line_range = parts[1]
                try:
                    return int(line_range.split("-")[0])
                except (ValueError, IndexError):
                    pass
            return 2**31  # Sentinel for sort ordering

        split_blocks.sort(key=_start_line)

        # Should resolve to the one with lowest start_line (100)
        assert split_blocks[0] == "test.py:100-150:split_block:process_data"

    def test_mixed_candidates_not_all_split_blocks(self):
        """Test that mixed candidates don't trigger split_block disambiguation."""
        candidates = [
            "test.py:10-50:function:helper",
            "test.py:100-150:split_block:helper",
        ]

        # Only one is a split_block
        split_blocks = [c for c in candidates if ":split_block:" in c]
        assert len(split_blocks) != len(candidates)  # Not all are split_blocks

        # Disambiguation should NOT activate (would return None in real code)


class TestFromStorage(TestCase):
    """Tests for GraphIntegration.from_storage classmethod."""

    def test_from_storage_wraps_existing_storage(self):
        """from_storage should expose the passed storage as .storage."""
        mock_storage = Mock()
        mock_storage.__len__ = Mock(return_value=5)

        graph = GraphIntegration.from_storage(mock_storage)

        self.assertIs(graph.storage, mock_storage)
        self.assertTrue(graph.is_available)
        self.assertEqual(len(graph), 5)

    def test_from_storage_none(self):
        """from_storage(None) should yield an instance with storage=None."""
        graph = GraphIntegration.from_storage(None)

        self.assertIsNone(graph.storage)
        self.assertFalse(graph.is_available)
        self.assertEqual(graph.node_count, 0)

    def test_from_storage_independent_of_init(self):
        """from_storage should not call CodeGraphStorage constructor."""
        with patch("search.graph_integration.CodeGraphStorage") as mock_cls:
            mock_storage = Mock()
            GraphIntegration.from_storage(mock_storage)
            mock_cls.assert_not_called()


def _make_result(
    chunk_id: str,
    chunk_type: str = "function",
    name: str = "foo",
    parent_name: str | None = None,
    calls: list | None = None,
    relationships: list | None = None,
    file_path: str = "src/module.py",
) -> Mock:
    """Build a mock EmbeddingResult for testing populate_from_embeddings."""
    result = Mock()
    result.chunk_id = chunk_id
    result.metadata = {
        "chunk_type": chunk_type,
        "name": name,
        "parent_name": parent_name,
        "file_path": file_path,
        "language": "python",
        "calls": calls or [],
        "relationships": relationships or [],
    }
    return result


class TestPopulateFromEmbeddings(TestCase):
    """Tests for GraphIntegration.populate_from_embeddings."""

    def _make_graph(self) -> tuple[GraphIntegration, Mock]:
        storage = Mock()
        storage.__len__ = Mock(return_value=0)
        graph = GraphIntegration.from_storage(storage)
        return graph, storage

    def test_no_storage_is_noop(self):
        """populate_from_embeddings on a None-storage instance should be silent."""
        graph = GraphIntegration.from_storage(None)
        result = _make_result("f.py:1-5:function:foo")
        graph.populate_from_embeddings([result])  # must not raise

    def test_empty_list_is_noop(self):
        """Empty embedding_results list should not touch storage."""
        graph, storage = self._make_graph()
        graph.populate_from_embeddings([])
        storage.add_node.assert_not_called()
        storage.add_call_edge.assert_not_called()

    def test_nodes_added_for_semantic_types(self):
        """Only semantic-type chunks get nodes; non-semantic types are skipped."""
        graph, storage = self._make_graph()

        semantic = _make_result(
            "f.py:1-5:function:do_thing", chunk_type="function", name="do_thing"
        )
        non_semantic = _make_result("f.py:6-8:module:f", chunk_type="module")

        graph.populate_from_embeddings([semantic, non_semantic])

        # Exactly one node added (the function, not the module)
        storage.add_node.assert_called_once_with(
            chunk_id="f.py:1-5:function:do_thing",
            name="do_thing",
            chunk_type="function",
            file_path="src/module.py",
            language="python",
        )

    def test_unique_call_target_resolved(self):
        """A callee whose name maps to exactly one chunk_id resolves with is_resolved=True."""
        graph, storage = self._make_graph()

        callee = _make_result("f.py:10-15:function:helper", name="helper")
        caller = _make_result(
            "f.py:20-30:function:main",
            name="main",
            calls=[
                {"callee_name": "helper", "line_number": 25, "is_method_call": False}
            ],
        )

        graph.populate_from_embeddings([callee, caller])

        call_args = storage.add_call_edge.call_args_list
        assert len(call_args) == 1
        kwargs = call_args[0].kwargs
        self.assertEqual(kwargs["callee_name"], "f.py:10-15:function:helper")
        self.assertTrue(kwargs["is_resolved"])

    def test_common_method_name_resolves_when_project_defines_it(self):
        """Phase 2 refinement: common method names (get, join, append) now resolve to
        project definitions when the project actually defines a symbol of that name.
        The old behavior was to always drop them; the new behavior only drops them
        when NO project definition exists (i.e. the call is definitely stdlib/builtin).
        """
        graph, storage = self._make_graph()

        # A project function named "get" exists in the batch
        project_get = _make_result("f.py:1-5:function:get", name="get")
        # A caller that calls "get" — now resolves to the project's "get" definition
        caller = _make_result(
            "f.py:10-20:function:process",
            name="process",
            calls=[{"callee_name": "get", "line_number": 15, "is_method_call": True}],
        )

        graph.populate_from_embeddings([project_get, caller])

        call_args = storage.add_call_edge.call_args_list
        assert len(call_args) == 1
        kwargs = call_args[0].kwargs
        # With exactly one project definition, "get" now resolves
        self.assertEqual(kwargs["callee_name"], "f.py:1-5:function:get")
        self.assertTrue(kwargs["is_resolved"])
        self.assertEqual(kwargs.get("confidence"), "exact")

    def test_common_method_name_stays_phantom_without_project_definition(self):
        """Common method names (get, join, append) that have NO matching project
        definition stay phantom — they are assumed to be stdlib/builtin targets."""
        graph, storage = self._make_graph()

        # No project function named "get" — only a caller that calls "get"
        caller = _make_result(
            "f.py:10-20:function:process",
            name="process",
            calls=[{"callee_name": "get", "line_number": 15, "is_method_call": True}],
        )

        graph.populate_from_embeddings([caller])

        call_args = storage.add_call_edge.call_args_list
        assert len(call_args) == 1
        kwargs = call_args[0].kwargs
        # No project definition for "get" — stays phantom
        self.assertEqual(kwargs["callee_name"], "get")
        self.assertFalse(kwargs["is_resolved"])

    def test_qualified_parent_name_resolves_intra_class_calls(self):
        """Calls to 'ClassName.method' should resolve via the qualified-name index
        that populate_from_embeddings builds. The inline copy lacked this indexing
        and would leave intra-class self.method() calls as phantom."""
        graph, storage = self._make_graph()

        method = _make_result(
            "c.py:10-20:method:MyClass.process",
            chunk_type="method",
            name="process",
            parent_name="MyClass",
        )
        caller = _make_result(
            "c.py:30-40:method:MyClass.run",
            chunk_type="method",
            name="run",
            parent_name="MyClass",
            calls=[
                {
                    "callee_name": "MyClass.process",
                    "line_number": 35,
                    "is_method_call": True,
                }
            ],
        )

        graph.populate_from_embeddings([method, caller])

        call_args = storage.add_call_edge.call_args_list
        assert len(call_args) == 1
        kwargs = call_args[0].kwargs
        self.assertEqual(kwargs["callee_name"], "c.py:10-20:method:MyClass.process")
        self.assertTrue(kwargs["is_resolved"])

    def test_relationship_edges_added(self):
        """Relationship edges in metadata should be forwarded to add_relationship_edge."""
        graph, storage = self._make_graph()

        result = _make_result(
            "child.py:1-10:class:Child",
            chunk_type="class",
            name="Child",
            relationships=[
                {
                    "source_id": "child.py:1-10:class:Child",
                    "target_name": "Base",
                    "relationship_type": "inherits",
                    "line_number": 1,
                    "confidence": 1.0,
                    "metadata": {},
                }
            ],
        )

        graph.populate_from_embeddings([result])
        storage.add_relationship_edge.assert_called_once()

    def test_ambiguous_same_file_preferred(self):
        """When two candidates share a name, the one in the caller's file is preferred."""
        graph, storage = self._make_graph()

        local_helper = _make_result(
            "src/module.py:1-5:function:helper",
            name="helper",
            file_path="src/module.py",
        )
        other_helper = _make_result(
            "src/other.py:10-15:function:helper",
            name="helper",
            file_path="src/other.py",
        )
        caller = _make_result(
            "src/module.py:20-30:function:main",
            name="main",
            file_path="src/module.py",
            calls=[
                {"callee_name": "helper", "line_number": 25, "is_method_call": False}
            ],
        )

        graph.populate_from_embeddings([local_helper, other_helper, caller])

        call_args = storage.add_call_edge.call_args_list
        assert len(call_args) == 1
        kwargs = call_args[0].kwargs
        # Same-file preference: resolves to local_helper, not other_helper
        self.assertEqual(kwargs["callee_name"], "src/module.py:1-5:function:helper")
        self.assertTrue(kwargs["is_resolved"])


class TestExtractSplitBlockCalls(TestCase):
    """Regression tests for _extract_split_block_calls whole-method-from-file fix.

    The correct implementation reads the full source file (not the split_block
    content fragment) and locates the enclosing method by line-range containment.
    This ensures that split_block chunks — whose stored ``content`` is not valid
    Python — still contribute call edges to the persisted call graph.
    """

    def _make_gi(self) -> GraphIntegration:
        """Create a GraphIntegration with no real graph storage."""
        return GraphIntegration.from_storage(None)

    def test_extract_calls_from_real_file(self):
        """Recovering calls from a real split_block locator yields the expected callee.

        Scenario: analyze_impact is large enough to be split into split_block chunks.
        The helper must re-read relationship_analyzer.py, locate the FunctionDef
        whose lineno <= start_line, and return call edges that include the qualified
        callee ``RelationshipAnalyzer._enrich_callers``.
        """
        import os

        # Locate the real file relative to this test file's directory
        repo_root = Path(__file__).parent.parent.parent.parent
        file_path = str(repo_root / "search" / "relationship_analyzer.py")
        if not os.path.isfile(file_path):
            self.skipTest(f"Source file not found: {file_path}")

        gi = self._make_gi()
        # analyze_impact starts at line 75; pick a start_line deep inside the method
        # (simulating a split_block chunk that covers the _enrich_callers call site)
        calls = gi._extract_split_block_calls(
            file_path=file_path,
            parent_name="RelationshipAnalyzer",
            name="analyze_impact",
            start_line=100,  # well inside the method body
            language="python",
        )

        callee_names = {c["callee_name"] for c in calls}
        self.assertIn(
            "RelationshipAnalyzer._enrich_callers",
            callee_names,
            f"Expected 'RelationshipAnalyzer._enrich_callers' in callee names; "
            f"got: {sorted(callee_names)}",
        )

    def test_non_python_language_returns_empty(self):
        """Non-Python chunks are skipped (no AST extractor for them)."""
        gi = self._make_gi()
        calls = gi._extract_split_block_calls(
            file_path="/some/file.js",
            parent_name=None,
            name="doSomething",
            start_line=10,
            language="javascript",
        )
        self.assertEqual(calls, [])

    def test_missing_file_returns_empty(self):
        """A missing file path returns [] without raising."""
        gi = self._make_gi()
        calls = gi._extract_split_block_calls(
            file_path="/nonexistent/totally_fake_path.py",
            parent_name="Foo",
            name="bar",
            start_line=5,
            language="python",
        )
        self.assertEqual(calls, [])

    def test_per_method_dedup_across_split_blocks(self):
        """Two split_block chunks for the same method emit edges only once.

        The seen_split_methods set should suppress the second call for the
        same (file_path, name, func.lineno) tuple.
        """
        import os

        repo_root = Path(__file__).parent.parent.parent.parent
        file_path = str(repo_root / "search" / "relationship_analyzer.py")
        if not os.path.isfile(file_path):
            self.skipTest(f"Source file not found: {file_path}")

        gi = self._make_gi()
        # Warm the cache and record first-call result
        calls_first = gi._extract_split_block_calls(
            file_path=file_path,
            parent_name="RelationshipAnalyzer",
            name="analyze_impact",
            start_line=100,
            language="python",
        )
        # Second split_block of the same method: must return [] (deduped)
        calls_second = gi._extract_split_block_calls(
            file_path=file_path,
            parent_name="RelationshipAnalyzer",
            name="analyze_impact",
            start_line=150,  # different fragment, same method
            language="python",
        )
        self.assertGreater(len(calls_first), 0, "First split_block should return calls")
        self.assertEqual(
            calls_second, [], "Second split_block of same method should be deduped"
        )


def _make_chunk(
    chunk_id: str,
    chunk_type: str = "function",
    name: str = "foo",
    parent_name: str | None = None,
    calls: list | None = None,
    relationships: list | None = None,
    file_path: str = "src/module.py",
    language: str = "python",
    start_line: int = 1,
) -> Mock:
    """Build a mock CodeChunk for testing build_graph_from_chunks."""
    chunk = Mock()
    chunk.chunk_id = chunk_id
    chunk.chunk_type = chunk_type
    chunk.name = name
    chunk.parent_name = parent_name
    chunk.calls = calls or []
    chunk.relationships = relationships or []
    chunk.file_path = file_path
    chunk.language = language
    chunk.start_line = start_line
    return chunk


class TestTwoPassBuild(TestCase):
    """Direct tests for GraphIntegration._two_pass_build."""

    def _make_graph(self) -> tuple[GraphIntegration, Mock]:
        storage = Mock()
        storage.__len__ = Mock(return_value=0)
        graph = GraphIntegration.from_storage(storage)
        return graph, storage

    def test_empty_specs_returns_empty_dict(self):
        """_two_pass_build([]) should return {} without touching storage."""
        graph, storage = self._make_graph()

        stats = graph._two_pass_build([], clear=False)
        self.assertEqual(stats, {})
        storage.add_node.assert_not_called()

    def test_no_storage_returns_empty_dict(self):
        """_two_pass_build on a None-storage instance returns {}."""
        graph = GraphIntegration.from_storage(None)
        from search.graph_integration import _BuildSpec

        spec = _BuildSpec(
            chunk_id="f.py:1-5:function:foo",
            name="foo",
            chunk_type="function",
            file_path="f.py",
            language="python",
            parent_name=None,
            calls=[],
            relationships=[],
        )
        stats = graph._two_pass_build([spec], clear=False)
        self.assertEqual(stats, {})

    def test_clear_true_calls_storage_clear(self):
        """clear=True must call storage.clear() before adding nodes."""
        graph, storage = self._make_graph()
        from search.graph_integration import _BuildSpec

        spec = _BuildSpec(
            chunk_id="f.py:1-5:function:foo",
            name="foo",
            chunk_type="function",
            file_path="f.py",
            language="python",
            parent_name=None,
            calls=[],
            relationships=[],
        )
        graph._two_pass_build([spec], clear=True)
        storage.clear.assert_called_once()

    def test_clear_false_skips_storage_clear(self):
        """clear=False must NOT call storage.clear()."""
        graph, storage = self._make_graph()
        from search.graph_integration import _BuildSpec

        spec = _BuildSpec(
            chunk_id="f.py:1-5:function:foo",
            name="foo",
            chunk_type="function",
            file_path="f.py",
            language="python",
            parent_name=None,
            calls=[],
            relationships=[],
        )
        graph._two_pass_build([spec], clear=False)
        storage.clear.assert_not_called()

    def test_stats_keys_present(self):
        """_two_pass_build returns all expected stat keys."""
        graph, storage = self._make_graph()
        from search.graph_integration import _BuildSpec

        spec = _BuildSpec(
            chunk_id="f.py:1-5:function:foo",
            name="foo",
            chunk_type="function",
            file_path="f.py",
            language="python",
            parent_name=None,
            calls=[],
            relationships=[],
        )
        stats = graph._two_pass_build([spec], clear=False)
        for key in (
            "nodes_added",
            "call_edges",
            "resolved_edges",
            "phantom_edges",
            "rel_edges",
        ):
            self.assertIn(key, stats)
        self.assertEqual(stats["nodes_added"], 1)

    def test_resolved_call_edge_counted(self):
        """A call whose callee appears in the spec list is counted as resolved."""
        graph, storage = self._make_graph()
        from search.graph_integration import _BuildSpec

        callee_spec = _BuildSpec(
            chunk_id="f.py:10-15:function:helper",
            name="helper",
            chunk_type="function",
            file_path="f.py",
            language="python",
            parent_name=None,
            calls=[],
            relationships=[],
        )
        caller_spec = _BuildSpec(
            chunk_id="f.py:20-30:function:main",
            name="main",
            chunk_type="function",
            file_path="f.py",
            language="python",
            parent_name=None,
            calls=[
                {"callee_name": "helper", "line_number": 25, "is_method_call": False}
            ],
            relationships=[],
        )
        stats = graph._two_pass_build([callee_spec, caller_spec], clear=False)
        self.assertEqual(stats["resolved_edges"], 1)
        self.assertEqual(stats["call_edges"], 1)
        self.assertEqual(stats["phantom_edges"], 0)


class TestBuildGraphFromChunks(TestCase):
    """Tests for GraphIntegration.build_graph_from_chunks."""

    def _make_graph(self) -> tuple[GraphIntegration, Mock]:
        storage = Mock()
        storage.__len__ = Mock(return_value=0)
        graph = GraphIntegration.from_storage(storage)
        return graph, storage

    def test_no_storage_warns_and_returns(self):
        """build_graph_from_chunks with None storage logs a warning but does not raise."""
        graph = GraphIntegration.from_storage(None)
        chunk = _make_chunk("f.py:1-5:function:foo")
        graph.build_graph_from_chunks([chunk])  # must not raise

    def test_clears_graph_on_call(self):
        """build_graph_from_chunks always calls storage.clear() for a fresh build."""
        graph, storage = self._make_graph()
        graph.build_graph_from_chunks([])
        storage.clear.assert_called_once()

    def test_skips_module_and_community(self):
        """module and community chunk types are not added as nodes."""
        graph, storage = self._make_graph()
        chunks = [
            _make_chunk("f.py:0-0:module:f", chunk_type="module"),
            _make_chunk("f.py:0-0:community:grp", chunk_type="community"),
        ]
        graph.build_graph_from_chunks(chunks)
        storage.add_node.assert_not_called()

    def test_skips_chunks_without_id(self):
        """Chunks with empty chunk_id are silently skipped."""
        graph, storage = self._make_graph()
        chunk = _make_chunk("", chunk_type="function")
        graph.build_graph_from_chunks([chunk])
        storage.add_node.assert_not_called()

    def test_nodes_added_for_valid_chunks(self):
        """Valid function chunks produce add_node calls with correct kwargs."""
        graph, storage = self._make_graph()
        chunk = _make_chunk(
            "f.py:1-10:function:do_work", name="do_work", file_path="f.py"
        )
        graph.build_graph_from_chunks([chunk])
        storage.add_node.assert_called_once_with(
            chunk_id="f.py:1-10:function:do_work",
            name="do_work",
            chunk_type="function",
            file_path="f.py",
            language="python",
        )


class TestBuildVsPopulateParity(TestCase):
    """Parity: build_graph_from_chunks and populate_from_embeddings produce the same
    node additions when fed equivalent data.

    Both go through _two_pass_build; this test pins the contract that neither
    entry point silently drops or duplicates nodes relative to the other.
    """

    def _make_graph(self) -> tuple[GraphIntegration, Mock]:
        storage = Mock()
        storage.__len__ = Mock(return_value=0)
        graph = GraphIntegration.from_storage(storage)
        return graph, storage

    def test_same_add_node_calls(self):
        """add_node is called with identical kwargs from both entry points."""
        chunk_id = "pkg/mod.py:1-10:function:compute"
        name = "compute"
        file_path = "pkg/mod.py"

        # --- build_graph_from_chunks path ---
        graph_b, storage_b = self._make_graph()
        chunk = _make_chunk(chunk_id, name=name, file_path=file_path)
        graph_b.build_graph_from_chunks([chunk])

        # --- populate_from_embeddings path ---
        graph_e, storage_e = self._make_graph()
        result = _make_result(chunk_id, name=name, file_path=file_path)
        graph_e.populate_from_embeddings([result])

        # Both should have called add_node exactly once
        self.assertEqual(storage_b.add_node.call_count, 1)
        self.assertEqual(storage_e.add_node.call_count, 1)

        # Kwargs must match
        kwargs_b = storage_b.add_node.call_args.kwargs
        kwargs_e = storage_e.add_node.call_args.kwargs
        self.assertEqual(kwargs_b, kwargs_e)

    def test_resolved_edge_from_both_entry_points(self):
        """A resolved call edge appears via both entry points with is_resolved=True."""
        callee_id = "pkg/mod.py:1-5:function:helper"
        caller_id = "pkg/mod.py:10-20:function:main"
        call = {"callee_name": "helper", "line_number": 15, "is_method_call": False}

        # --- build_graph_from_chunks path ---
        graph_b, storage_b = self._make_graph()
        chunks = [
            _make_chunk(callee_id, name="helper", file_path="pkg/mod.py"),
            _make_chunk(caller_id, name="main", file_path="pkg/mod.py", calls=[call]),
        ]
        graph_b.build_graph_from_chunks(chunks)

        # --- populate_from_embeddings path ---
        graph_e, storage_e = self._make_graph()
        results = [
            _make_result(callee_id, name="helper", file_path="pkg/mod.py"),
            _make_result(caller_id, name="main", file_path="pkg/mod.py", calls=[call]),
        ]
        graph_e.populate_from_embeddings(results)

        # Both should produce exactly one resolved call edge
        b_calls = storage_b.add_call_edge.call_args_list
        e_calls = storage_e.add_call_edge.call_args_list
        self.assertEqual(len(b_calls), 1)
        self.assertEqual(len(e_calls), 1)
        self.assertTrue(b_calls[0].kwargs["is_resolved"])
        self.assertTrue(e_calls[0].kwargs["is_resolved"])
        self.assertEqual(b_calls[0].kwargs["callee_name"], callee_id)
        self.assertEqual(e_calls[0].kwargs["callee_name"], callee_id)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
