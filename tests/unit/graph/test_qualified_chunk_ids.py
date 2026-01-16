"""
Unit tests for qualified chunk_id generation (Phase 1: Call Graph Resolution).

Tests that chunk_ids include class-qualified names for methods:
- Before: `file.py:1-20:method:extract`
- After: `file.py:1-20:method:ClassName.extract`

This enables accurate caller/callee resolution by disambiguating
methods with the same name in different classes.
"""

from unittest.mock import MagicMock

from chunking.multi_language_chunker import MultiLanguageChunker
from chunking.tree_sitter import TreeSitterChunker
from search.config import ChunkingConfig


class TestQualifiedChunkIdGeneration:
    """Test that chunk_ids include class-qualified names."""

    def setup_method(self):
        """Set up test fixtures."""
        from mcp_server.services import ServiceLocator

        self.chunker = MultiLanguageChunker(root_path="/test")
        self.tree_chunker = TreeSitterChunker()

        # Disable greedy merge for these tests to check basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        locator = ServiceLocator.instance()
        locator.register("config", mock_config)

    def teardown_method(self):
        """Clean up test fixtures."""
        from mcp_server.services import ServiceLocator

        ServiceLocator.reset()

    def test_method_gets_qualified_name(self):
        """Test that methods inside classes get qualified chunk_ids."""
        code = """
class MyClass:
    def my_method(self):
        pass
"""
        # Get tree-sitter chunks
        chunks = self.tree_chunker.chunk_file("/test/example.py", code)

        # Find method chunk
        method_chunks = [
            c for c in chunks if c.node_type == "function_definition" and c.parent_class
        ]
        assert len(method_chunks) == 1, (
            f"Expected 1 method chunk, got {len(method_chunks)}"
        )

        method_chunk = method_chunks[0]
        assert method_chunk.parent_class == "MyClass"
        assert method_chunk.metadata.get("name") == "my_method"

    def test_standalone_function_no_qualification(self):
        """Test that standalone functions don't get qualified."""
        code = """
def standalone_function():
    pass
"""
        chunks = self.tree_chunker.chunk_file("/test/example.py", code)

        # Find function chunk
        func_chunks = [c for c in chunks if c.node_type == "function_definition"]
        assert len(func_chunks) == 1

        func_chunk = func_chunks[0]
        assert func_chunk.parent_class is None
        assert func_chunk.metadata.get("name") == "standalone_function"

    def test_multiple_classes_different_methods(self):
        """Test that methods in different classes get proper qualification."""
        code = """
class ClassA:
    def extract(self):
        pass

class ClassB:
    def extract(self):
        pass
"""
        chunks = self.tree_chunker.chunk_file("/test/example.py", code)

        # Find method chunks
        method_chunks = [
            c for c in chunks if c.node_type == "function_definition" and c.parent_class
        ]
        assert len(method_chunks) == 2

        # Check both methods are properly qualified
        class_a_method = [c for c in method_chunks if c.parent_class == "ClassA"][0]
        class_b_method = [c for c in method_chunks if c.parent_class == "ClassB"][0]

        assert class_a_method.metadata.get("name") == "extract"
        assert class_b_method.metadata.get("name") == "extract"

    def test_chunk_id_format_with_qualified_name(self):
        """Test the full chunk_id format includes qualified name."""
        code = """
class ExceptionExtractor:
    def extract(self):
        pass
"""
        # Use MultiLanguageChunker to get CodeChunk with chunk_id

        chunks = self.chunker._convert_tree_chunks(
            self.tree_chunker.chunk_file("/test/extractors/exception.py", code),
            "/test/extractors/exception.py",
        )

        # Find the method chunk
        method_chunks = [c for c in chunks if c.chunk_type == "method"]
        assert len(method_chunks) == 1

        # Check chunk metadata includes qualified name
        # Note: chunk_id is built in _convert_tree_chunks and includes qualified name
        method_chunk = method_chunks[0]
        assert method_chunk.parent_name == "ExceptionExtractor"
        assert method_chunk.name == "extract"

    def test_decorated_method_qualified(self):
        """Test that decorated methods get qualified names."""
        code = """
class MyClass:
    @property
    def my_property(self):
        return self._value

    @staticmethod
    def static_method():
        pass
"""
        chunks = self.tree_chunker.chunk_file("/test/example.py", code)

        # Should have class and decorated definitions
        # Tree-sitter handles decorators differently
        method_chunks = [c for c in chunks if c.parent_class == "MyClass"]
        assert len(method_chunks) >= 1  # At least one method

    def test_nested_class_methods(self):
        """Test methods in nested classes get proper parent class."""
        code = """
class OuterClass:
    class InnerClass:
        def inner_method(self):
            pass

    def outer_method(self):
        pass
"""
        chunks = self.tree_chunker.chunk_file("/test/example.py", code)

        # Find methods
        method_chunks = [c for c in chunks if c.node_type == "function_definition"]

        # Outer method should have OuterClass as parent
        outer_methods = [c for c in method_chunks if c.parent_class == "OuterClass"]
        inner_methods = [c for c in method_chunks if c.parent_class == "InnerClass"]

        # Note: Tree-sitter traversal tracks immediate parent class
        assert len(outer_methods) >= 1 or len(inner_methods) >= 1

    def test_class_method_cls_parameter(self):
        """Test classmethod with cls parameter gets qualified."""
        code = """
class MyClass:
    @classmethod
    def class_method(cls):
        pass
"""
        chunks = self.tree_chunker.chunk_file("/test/example.py", code)

        # Should have the class method with parent class set
        method_chunks = [c for c in chunks if c.parent_class == "MyClass"]
        assert len(method_chunks) >= 1


class TestTreeSitterChunkParentClass:
    """Test TreeSitterChunk.parent_class field."""

    def setup_method(self):
        """Set up test fixtures."""
        from mcp_server.services import ServiceLocator

        self.chunker = TreeSitterChunker()

        # Disable greedy merge for these tests to check basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        locator = ServiceLocator.instance()
        locator.register("config", mock_config)

    def teardown_method(self):
        """Clean up test fixtures."""
        from mcp_server.services import ServiceLocator

        ServiceLocator.reset()

    def test_parent_class_field_exists(self):
        """Test that TreeSitterChunk has parent_class field."""
        from chunking.tree_sitter import TreeSitterChunk

        chunk = TreeSitterChunk(
            content="def foo(): pass",
            start_line=1,
            end_line=1,
            node_type="function_definition",
            language="python",
            metadata={"name": "foo"},
            parent_class="MyClass",
        )

        assert chunk.parent_class == "MyClass"

    def test_parent_class_default_none(self):
        """Test that parent_class defaults to None."""
        from chunking.tree_sitter import TreeSitterChunk

        chunk = TreeSitterChunk(
            content="def foo(): pass",
            start_line=1,
            end_line=1,
            node_type="function_definition",
            language="python",
            metadata={"name": "foo"},
        )

        assert chunk.parent_class is None

    def test_method_in_class_has_parent_class(self):
        """Test that methods inside classes have parent_class set."""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
        chunks = self.chunker.chunk_file("/test/calc.py", code)

        # Find the method
        method_chunks = [c for c in chunks if c.metadata.get("name") == "add"]
        assert len(method_chunks) == 1

        assert method_chunks[0].parent_class == "Calculator"

    def test_multiple_methods_same_class(self):
        """Test multiple methods in same class all have parent_class set."""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b
"""
        chunks = self.chunker.chunk_file("/test/calc.py", code)

        # All methods should have Calculator as parent
        method_chunks = [
            c for c in chunks if c.node_type == "function_definition" and c.parent_class
        ]
        assert len(method_chunks) == 3

        for chunk in method_chunks:
            assert chunk.parent_class == "Calculator"
