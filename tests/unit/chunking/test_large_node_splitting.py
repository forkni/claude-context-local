"""Unit tests for AST block splitting of large functions (Task 3.4)."""

import pytest

from chunking.languages.python import PythonChunker
from chunking.repo_profiler import RepoProfile
from search.config import ChunkingConfig


class TestGetBlockBoundaryTypes:
    """Test _get_block_boundary_types() method."""

    @pytest.fixture
    def chunker(self):
        """Create Python chunker."""
        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    def test_python_boundary_types(self, chunker):
        """Python returns correct boundary types."""
        types = chunker._get_block_boundary_types()
        assert "for_statement" in types
        assert "if_statement" in types
        assert "while_statement" in types
        assert "try_statement" in types
        assert "with_statement" in types
        assert "match_statement" in types

    def test_has_six_boundary_types(self, chunker):
        """Python defines 6 boundary types."""
        types = chunker._get_block_boundary_types()
        assert len(types) == 6


class TestExtractSignature:
    """Test _extract_signature() method."""

    @pytest.fixture
    def chunker(self):
        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    def test_simple_function_signature(self, chunker):
        """Extract simple function signature."""
        code = """def simple_func(a, b):
    return a + b"""
        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        sig = chunker._extract_signature(func_node, bytes(code, "utf-8"))
        assert sig == "def simple_func(a, b):"

    def test_decorated_function_signature(self, chunker):
        """Extract decorated function signature."""
        code = """@decorator
@another
def decorated_func():
    pass"""
        tree = chunker.parser.parse(bytes(code, "utf-8"))
        node = tree.root_node.children[0]

        sig = chunker._extract_signature(node, bytes(code, "utf-8"))
        assert "@decorator" in sig
        assert "@another" in sig
        assert "def decorated_func():" in sig

    def test_async_function_signature(self, chunker):
        """Extract async function signature."""
        code = """async def async_func(x):
    await x"""
        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        sig = chunker._extract_signature(func_node, bytes(code, "utf-8"))
        assert "async def async_func(x):" in sig

    def test_multiline_signature(self, chunker):
        """Extract multiline function signature."""
        code = """def long_func(
    param1,
    param2,
    param3,
):
    return param1"""
        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        sig = chunker._extract_signature(func_node, bytes(code, "utf-8"))
        assert "def long_func(" in sig
        assert sig.rstrip().endswith(":")
        assert "param1" in sig


class TestSplitLargeNode:
    """Test _split_large_node() method."""

    @pytest.fixture
    def chunker(self):
        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    def test_splits_at_for_loop(self, chunker):
        """Function with for loop is split at loop boundary."""
        code = """def process_items(items):
    result = []
    for item in items:
        processed = transform(item)
        result.append(processed)
    return result"""

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=3,
            split_size_method="lines",
        )

        assert len(chunks) >= 2
        for chunk in chunks:
            assert "def process_items(items):" in chunk.content

    def test_splits_at_if_statement(self, chunker):
        """Function with if statement is split at if boundary."""
        code = """def check_value(x):
    setup = initialize()
    if x > 0:
        return positive(x)
    else:
        return negative(x)"""

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=2,
            split_size_method="lines",
        )

        assert len(chunks) >= 2

    def test_preserves_signature_in_all_chunks(self, chunker):
        """Each split chunk has the function signature prefix."""
        code = """def multi_block(data):
    prep = prepare(data)
    for item in data:
        process(item)
    while has_more():
        fetch_more()
    return finalize()"""

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=2,
            split_size_method="lines",
        )

        for chunk in chunks:
            assert chunk.content.startswith("def multi_block(data):")

    def test_no_split_when_under_threshold(self, chunker):
        """Small function is not split."""
        code = """def small():
    return 42"""

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        # Set high max_lines so function is under threshold
        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=100,
            split_size_method="lines",
        )

        # Should return empty list (signal to use default)
        assert chunks == []

    def test_node_type_is_split_block(self, chunker):
        """Split chunks have node_type='split_block'."""
        code = """def example():
    a = 1
    for i in range(10):
        b = i
    c = 3"""

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=2,
            split_size_method="lines",
        )

        for chunk in chunks:
            assert chunk.node_type == "split_block"

    def test_metadata_includes_split_block_flag(self, chunker):
        """Metadata includes split_block=True."""
        code = """def tagged():
    x = 1
    if True:
        y = 2"""

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=2,
            split_size_method="lines",
        )

        for chunk in chunks:
            assert chunk.metadata.get("split_block") is True


class TestPackBySize:
    """Direct tests for _pack_by_size, extracted from _split_large_node's
    accumulation loop (base.py). Uses SimpleNamespace fake nodes over a
    bytes buffer instead of real tree-sitter nodes, since the packer only
    ever touches start_byte/end_byte/type."""

    @pytest.fixture
    def chunker(self):
        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    @staticmethod
    def _fake_node(start_byte, end_byte, node_type="stmt"):
        from types import SimpleNamespace

        return SimpleNamespace(start_byte=start_byte, end_byte=end_byte, type=node_type)

    def test_empty_input_returns_no_groups(self, chunker):
        groups = chunker._pack_by_size(
            [],
            b"",
            threshold=10,
            split_size_method="characters",
            may_cut_before=lambda prev, node: True,
        )
        assert groups == []

    def test_below_threshold_stays_one_group(self, chunker):
        source = b"aaa bbb ccc"
        nodes = [
            self._fake_node(0, 3),
            self._fake_node(4, 7),
            self._fake_node(8, 11),
        ]
        groups = chunker._pack_by_size(
            nodes,
            source,
            threshold=1000,
            split_size_method="characters",
            may_cut_before=lambda prev, node: True,
        )
        assert groups == [nodes]

    def test_exact_cut_at_threshold(self, chunker):
        source = b"aaa bbb"
        n1 = self._fake_node(0, 3)
        n2 = self._fake_node(4, 7)
        # source[0:7] = "aaa bbb" -> non-whitespace chars = "aaabbb" = 6
        groups = chunker._pack_by_size(
            [n1, n2],
            source,
            threshold=6,
            split_size_method="characters",
            may_cut_before=lambda prev, node: True,
        )
        assert groups == [[n1], [n2]]

    def test_predicate_vetoes_cut(self, chunker):
        source = b"aaa bbb"
        n1 = self._fake_node(0, 3)
        n2 = self._fake_node(4, 7)
        groups = chunker._pack_by_size(
            [n1, n2],
            source,
            threshold=6,  # would cut per test_exact_cut_at_threshold
            split_size_method="characters",
            may_cut_before=lambda prev, node: False,
        )
        assert groups == [[n1, n2]]

    def test_single_oversized_node_stays_one_group(self, chunker):
        source = b"aaaaaaaaaa"
        n1 = self._fake_node(0, 10)
        groups = chunker._pack_by_size(
            [n1],
            source,
            threshold=1,  # n1 alone already exceeds this
            split_size_method="characters",
            may_cut_before=lambda prev, node: True,
        )
        assert groups == [[n1]]


class TestChunkCodeWithSplitting:
    """Test chunk_code() integration with large node splitting."""

    @pytest.fixture
    def chunker(self):
        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    def _make_large_function(self, num_loops: int = 5) -> str:
        """Generate a large function with multiple blocks."""
        lines = ["def large_function(data):"]
        lines.append("    result = []")
        for i in range(num_loops):
            lines.append(f"    for item{i} in data:")
            lines.append(f"        result.append(process{i}(item{i}))")
        lines.append("    return result")
        return "\n".join(lines)

    def test_splitting_disabled_by_default(self, chunker):
        """Large node splitting is disabled by default."""
        code = self._make_large_function(num_loops=10)
        config = ChunkingConfig()  # Default: enable_large_node_splitting=False

        chunks = chunker.chunk_code(code, config=config)

        # Should be single function chunk (no splits)
        split_chunks = [c for c in chunks if c.node_type == "split_block"]
        assert len(split_chunks) == 0

    def test_splitting_enabled_splits_large_function(self, chunker):
        """Large function is split when enabled."""
        code = self._make_large_function(num_loops=10)
        config = ChunkingConfig(
            enable_large_node_splitting=True,
            max_chunk_lines=10,  # Force splitting
            split_size_method="lines",
        )

        chunks = chunker.chunk_code(code, config=config)

        # Should have multiple split chunks
        split_chunks = [c for c in chunks if c.node_type == "split_block"]
        assert len(split_chunks) > 1

    def test_small_function_unchanged_when_enabled(self, chunker):
        """Small functions are not split even when enabled."""
        code = """def tiny():
    return 42"""
        config = ChunkingConfig(
            enable_large_node_splitting=True,
            max_chunk_lines=100,
            split_size_method="lines",
        )

        chunks = chunker.chunk_code(code, config=config)

        # Should not be split (under threshold)
        split_chunks = [c for c in chunks if c.node_type == "split_block"]
        assert len(split_chunks) == 0

    def test_class_methods_split_correctly(self, chunker):
        """Methods inside classes are split with correct parent_class."""
        code = """class MyClass:
    def large_method(self, data):
        result = []
        for item in data:
            result.append(item)
        while has_more():
            fetch()
        for x in range(10):
            process(x)
        return result"""

        config = ChunkingConfig(
            enable_large_node_splitting=True,
            max_chunk_lines=3,
            split_size_method="lines",
        )

        chunks = chunker.chunk_code(code, config=config)

        # Find split method chunks
        method_splits = [
            c
            for c in chunks
            if c.node_type == "split_block" and c.parent_class == "MyClass"
        ]
        assert len(method_splits) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def chunker(self):
        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    def test_empty_function_body(self, chunker):
        """Function with only pass is not split."""
        code = """def empty():
    pass"""

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=1,
            split_size_method="lines",
        )

        # Should not split a single statement
        assert len(chunks) <= 1

    def test_function_with_only_docstring(self, chunker):
        """Function with only docstring is not split."""
        code = '''def documented():
    """This is a docstring."""
    pass'''

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=1,
            split_size_method="lines",
        )

        assert len(chunks) <= 1

    def test_nested_functions_not_split(self, chunker):
        """Nested functions are handled correctly."""
        code = """def outer():
    def inner():
        for x in range(10):
            process(x)
    return inner"""

        config = ChunkingConfig(
            enable_large_node_splitting=True,
            max_chunk_lines=3,
            split_size_method="lines",
        )

        chunks = chunker.chunk_code(code, config=config)

        # Should chunk outer and inner as separate chunks
        # Outer may or may not be split depending on line count
        assert len(chunks) >= 1

    def test_try_except_block_as_boundary(self, chunker):
        """Try-except blocks are treated as boundaries."""
        code = """def error_handler():
    setup()
    try:
        risky_operation()
        another_operation()
    except Exception as e:
        handle_error(e)
    cleanup()"""

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=2,
            split_size_method="lines",
        )

        # try_statement should be a boundary
        for chunk in chunks:
            # Each chunk should start with signature
            assert chunk.content.startswith("def error_handler():")

    def test_split_chunk_has_marker_comment(self, chunker):
        """Split chunks include the '# ... (split block)' marker."""
        code = """def example():
    a = 1
    for i in range(10):
        b = i
    c = 3"""

        tree = chunker.parser.parse(bytes(code, "utf-8"))
        func_node = tree.root_node.children[0]

        chunks = chunker._split_large_node(
            func_node,
            bytes(code, "utf-8"),
            None,
            max_lines=2,
            split_size_method="lines",
        )

        for chunk in chunks:
            assert "# ... (split block)" in chunk.content


class TestSplitBlockRelationshipExtraction:
    """split_block chunks must extract relationship edges from their signature."""

    @pytest.fixture
    def chunker(self):
        try:
            from chunking.multi_language_chunker import MultiLanguageChunker

            return MultiLanguageChunker()
        except Exception:
            pytest.skip("MultiLanguageChunker unavailable (missing deps)")

    def _make_split_block_tchunk(self, signature: str, body_fragment: str):
        from chunking.languages.base import TreeSitterChunk

        content = f"{signature}\n    # ... (split block)\n{body_fragment}"
        return TreeSitterChunk(
            content=content,
            start_line=10,
            end_line=50,
            node_type="split_block",
            language="python",
            metadata={},
        )

    def _make_code_chunk(self, name: str = "_process", chunk_type: str = "split_block"):
        from chunking.python_ast_chunker import CodeChunk

        chunk = CodeChunk.__new__(CodeChunk)
        chunk.name = name
        chunk.chunk_type = chunk_type
        chunk.relative_path = "search/indexer.py"
        chunk.parent_name = "Indexer"
        chunk.relationships = []
        return chunk

    def test_split_block_extracts_type_annotations_from_signature(self, chunker):
        """split_block with typed signature gets uses_type edges despite incomplete body."""
        signature = (
            "def _process(\n"
            "    self,\n"
            "    entry: RelationshipEntry,\n"
            "    should_include: Any,\n"
            ") -> dict[str, Any] | None:"
        )
        # Dangling else — would cause SyntaxError on ast.parse without the fix
        body = "    else:\n        return None\n"

        tchunk = self._make_split_block_tchunk(signature, body)
        chunk = self._make_code_chunk()
        chunk_id = "search/indexer.py:10-50:split_block:Indexer._process#1"

        chunker._extract_phase3_relationships(chunk, tchunk, chunk_id)

        rel_targets = {r.target_name for r in chunk.relationships}
        assert rel_targets & {"RelationshipEntry", "Any"}, (
            f"Expected type annotations in relationships, got: {rel_targets}"
        )

    def test_split_block_no_crash_on_incomplete_body(self, chunker):
        """_extract_phase3_relationships must not raise even with broken body."""
        signature = "def _run(self, items: list[str]) -> None:"
        body = "    except ValueError:\n        raise\n    finally:\n"

        tchunk = self._make_split_block_tchunk(signature, body)
        chunk = self._make_code_chunk("_run")
        chunk_id = "search/indexer.py:10-50:split_block:Indexer._run#1"

        chunker._extract_phase3_relationships(chunk, tchunk, chunk_id)
        assert isinstance(chunk.relationships, list)

    def test_regular_method_extraction_unchanged(self, chunker):
        """Non-split_block method extraction is unaffected by the fix."""
        from chunking.languages.base import TreeSitterChunk

        code = "def compute(self, value: int) -> str:\n    return str(value)\n"
        tchunk = TreeSitterChunk(
            content=code,
            start_line=1,
            end_line=3,
            node_type="method",
            language="python",
            metadata={},
        )
        chunk = self._make_code_chunk("compute", chunk_type="method")
        chunk_id = "search/indexer.py:1-3:method:Indexer.compute"

        chunker._extract_phase3_relationships(chunk, tchunk, chunk_id)
        assert isinstance(chunk.relationships, list)


class TestSplitBoundaryCharacterization:
    """Pin exact split-block boundaries for fixed vs. adaptive `sizing_mode`.

    Only languages that override `_get_block_boundary_types()` can split at
    all -- the base default returns an empty set, and `_split_large_node`
    bails immediately when `split_types` is empty (base.py:758-761). Today
    that's Python and GLSL; C/C++/Rust/Go/C#/JS/TS never override it, so a
    C `function_definition` is structurally unsplittable regardless of size.
    These tests use Python and GLSL for that reason.

    The adaptive-mode tests prove `base.py:953-971` (the
    `compute_adaptive_threshold` branch) is actually live and produces
    boundaries different from fixed mode for the same source -- not just
    that the branch is reachable.
    """

    @staticmethod
    def _make_python_source(num_loops: int = 8) -> str:
        lines = ["def large_function(data):", "    result = []"]
        for i in range(num_loops):
            lines.append(f"    for item{i} in data:")
            lines.append(f"        result.append(process{i}(item{i}))")
        lines.append("    return result")
        return "\n".join(lines)

    @staticmethod
    def _make_glsl_source(num_ifs: int = 8) -> str:
        lines = ["vec3 large_function(vec3 data) {", "    vec3 result = vec3(0.0);"]
        for i in range(num_ifs):
            lines.append(f"    if (data.x > {i}.0) {{")
            lines.append(f"        result += process{i}(data);")
            lines.append("    }")
        lines.append("    return result;")
        lines.append("}")
        return "\n".join(lines)

    @pytest.fixture
    def python_chunker(self):
        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    @pytest.fixture
    def glsl_chunker(self):
        try:
            from chunking.languages.glsl import GLSLChunker

            return GLSLChunker()
        except ValueError:
            pytest.skip("tree-sitter-glsl not installed")

    @staticmethod
    def _split_boundaries(chunker, code, config, repo_profile=None):
        chunks = chunker.chunk_code(code, config=config, repo_profile=repo_profile)
        return [
            (c.start_line, c.end_line) for c in chunks if c.node_type == "split_block"
        ]

    def test_python_fixed_mode_boundaries(self, python_chunker):
        """Fixed sizing_mode pins exact split-block ranges (static max_split_chars)."""
        code = self._make_python_source(8)
        config = ChunkingConfig(
            sizing_mode="fixed",
            enable_large_node_splitting=True,
            max_chunk_lines=5,
            split_size_method="characters",
            max_split_chars=60,
        )
        boundaries = self._split_boundaries(python_chunker, code, config)
        assert boundaries == [
            (2, 4),
            (5, 6),
            (7, 8),
            (9, 10),
            (11, 12),
            (13, 14),
            (15, 16),
            (17, 19),
        ]

    def test_python_adaptive_mode_boundaries_differ_from_fixed(self, python_chunker):
        """Adaptive sizing_mode produces different boundaries than fixed mode
        for the identical source and max_chunk_lines."""
        code = self._make_python_source(8)
        repo_profile = RepoProfile(
            function_count=20,
            p25_chars=20,
            p50_chars=30,
            p75_chars=40,
            p90_chars=60,
            mean_chars=35,
            max_complexity=10,
        )
        fixed_config = ChunkingConfig(
            sizing_mode="fixed",
            enable_large_node_splitting=True,
            max_chunk_lines=5,
            split_size_method="characters",
            max_split_chars=60,
        )
        adaptive_config = ChunkingConfig(
            sizing_mode="adaptive",
            enable_large_node_splitting=True,
            max_chunk_lines=5,
            split_size_method="characters",
            max_split_chars=60,  # ignored: repo_profile.p75_chars > 0 drives adaptive mode
        )
        fixed_boundaries = self._split_boundaries(python_chunker, code, fixed_config)
        adaptive_boundaries = self._split_boundaries(
            python_chunker, code, adaptive_config, repo_profile=repo_profile
        )

        assert adaptive_boundaries == [
            (2, 2),
            (3, 4),
            (5, 6),
            (7, 8),
            (9, 10),
            (11, 12),
            (13, 14),
            (15, 16),
            (17, 19),
        ]
        assert adaptive_boundaries != fixed_boundaries

    def test_glsl_fixed_mode_boundaries(self, glsl_chunker):
        """Fixed sizing_mode pins exact split-block ranges for GLSL too --
        the same _split_large_node accumulation loop, a different
        boundary-type set (glsl.py:558-565)."""
        code = self._make_glsl_source(8)
        config = ChunkingConfig(
            sizing_mode="fixed",
            enable_large_node_splitting=True,
            max_chunk_lines=5,
            split_size_method="characters",
            max_split_chars=60,
        )
        boundaries = self._split_boundaries(glsl_chunker, code, config)
        assert boundaries == [
            (1, 2),
            (3, 5),
            (6, 8),
            (9, 11),
            (12, 14),
            (15, 17),
            (18, 20),
            (21, 23),
            (24, 28),
        ]

    def test_glsl_adaptive_mode_boundaries_differ_from_fixed(self, glsl_chunker):
        """Adaptive sizing_mode is live for GLSL as well (get_node_complexity
        is overridden at glsl.py:468) and yields different boundaries."""
        code = self._make_glsl_source(8)
        repo_profile = RepoProfile(
            function_count=20,
            p25_chars=20,
            p50_chars=30,
            p75_chars=40,
            p90_chars=60,
            mean_chars=35,
            max_complexity=10,
        )
        fixed_config = ChunkingConfig(
            sizing_mode="fixed",
            enable_large_node_splitting=True,
            max_chunk_lines=5,
            split_size_method="characters",
            max_split_chars=60,
        )
        adaptive_config = ChunkingConfig(
            sizing_mode="adaptive",
            enable_large_node_splitting=True,
            max_chunk_lines=5,
            split_size_method="characters",
            max_split_chars=60,
        )
        fixed_boundaries = self._split_boundaries(glsl_chunker, code, fixed_config)
        adaptive_boundaries = self._split_boundaries(
            glsl_chunker, code, adaptive_config, repo_profile=repo_profile
        )

        assert adaptive_boundaries == [
            (1, 2),
            (3, 5),
            (6, 8),
            (9, 11),
            (12, 14),
            (15, 17),
            (18, 20),
            (21, 23),
            (24, 26),
            (27, 28),
        ]
        assert adaptive_boundaries != fixed_boundaries
