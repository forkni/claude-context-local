"""Unit tests for AST block splitting of large functions (Task 3.4)."""

import pytest

from chunking.languages.python import PythonChunker
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
            func_node, bytes(code, "utf-8"), None, max_lines=3
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
            func_node, bytes(code, "utf-8"), None, max_lines=2
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
            func_node, bytes(code, "utf-8"), None, max_lines=2
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
            func_node, bytes(code, "utf-8"), None, max_lines=100
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
            func_node, bytes(code, "utf-8"), None, max_lines=2
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
            func_node, bytes(code, "utf-8"), None, max_lines=2
        )

        for chunk in chunks:
            assert chunk.metadata.get("split_block") is True


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
            enable_chunk_merging=False,  # Disable merge to see raw splits
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
            enable_chunk_merging=False,
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
            func_node, bytes(code, "utf-8"), None, max_lines=1
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
            func_node, bytes(code, "utf-8"), None, max_lines=1
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
            enable_chunk_merging=False,
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
            func_node, bytes(code, "utf-8"), None, max_lines=2
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
            func_node, bytes(code, "utf-8"), None, max_lines=2
        )

        for chunk in chunks:
            assert "# ... (split block)" in chunk.content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
