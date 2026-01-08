"""Unit tests for parent_chunk_id generation in chunking."""

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker


class TestParentChunkIdGeneration:
    """Test parent_chunk_id generation during chunking."""

    @pytest.fixture
    def chunker(self, tmp_path):
        """Create a multi-language chunker with tmp_path as root."""
        return MultiLanguageChunker(str(tmp_path))

    def test_method_has_parent_chunk_id(self, chunker, tmp_path):
        """Test that methods have parent_chunk_id pointing to their class."""
        test_file = tmp_path / "test_class.py"
        test_file.write_text(
            '''
class MyClass:
    """A test class."""

    def my_method(self):
        """A test method."""
        pass
'''
        )

        chunks = chunker.chunk_file(str(test_file))

        # Find class and method chunks
        class_chunk = next((c for c in chunks if c.chunk_type == "class"), None)
        method_chunk = next((c for c in chunks if c.chunk_type == "method"), None)

        assert class_chunk is not None, "Class chunk should exist"
        assert method_chunk is not None, "Method chunk should exist"

        # Verify parent_chunk_id
        assert (
            method_chunk.parent_chunk_id is not None
        ), "Method should have parent_chunk_id"
        assert method_chunk.parent_chunk_id == class_chunk.chunk_id, (
            f"Method's parent_chunk_id should match class chunk_id. "
            f"Got {method_chunk.parent_chunk_id}, expected {class_chunk.chunk_id}"
        )
        assert method_chunk.parent_name == "MyClass", "Parent name should be MyClass"

    def test_standalone_function_no_parent_id(self, chunker, tmp_path):
        """Test that standalone functions have no parent_chunk_id."""
        test_file = tmp_path / "test_func.py"
        test_file.write_text(
            '''
def standalone_function():
    """A standalone function."""
    pass
'''
        )

        chunks = chunker.chunk_file(str(test_file))

        func_chunk = next((c for c in chunks if c.chunk_type == "function"), None)
        assert func_chunk is not None, "Function chunk should exist"
        assert (
            func_chunk.parent_chunk_id is None
        ), "Standalone function should have no parent_chunk_id"
        assert (
            func_chunk.parent_name is None
        ), "Standalone function should have no parent_name"

    def test_multiple_methods_same_parent(self, chunker, tmp_path):
        """Test that multiple methods in the same class share the same parent_chunk_id.

        Note: This test verifies the parent_chunk_id generation logic.
        Greedy merging may merge small methods, so this test checks that IF
        method chunks exist, they correctly point to their parent.
        """
        test_file = tmp_path / "test_class.py"
        test_file.write_text(
            '''
class MyClass:
    """A test class."""

    def method1(self):
        """First method with substantial code to prevent merging."""
        # Longer method to prevent greedy merging
        result = []
        for i in range(10):
            result.append(i * 2)
        return sum(result)

    def method2(self):
        """Second method with substantial code to prevent merging."""
        # Longer method to prevent greedy merging
        data = {"a": 1, "b": 2, "c": 3}
        total = sum(data.values())
        return total * 2
'''
        )

        chunks = chunker.chunk_file(str(test_file))

        class_chunk = next((c for c in chunks if c.chunk_type == "class"), None)
        method_chunks = [c for c in chunks if c.chunk_type == "method"]

        assert class_chunk is not None, "Class chunk should exist"

        # If method chunks exist (not merged), verify they have correct parent_chunk_id
        if method_chunks:
            for method in method_chunks:
                assert (
                    method.parent_chunk_id == class_chunk.chunk_id
                ), f"Method {method.name} should point to class chunk_id"
                assert (
                    method.parent_name == "MyClass"
                ), f"Method {method.name} should have parent_name=MyClass"
        # If no method chunks (all merged into class), that's also fine -
        # this test is about parent_chunk_id generation, not chunking strategy

    def test_nested_class_methods(self, chunker, tmp_path):
        """Test methods in nested classes have correct parent_chunk_id."""
        test_file = tmp_path / "nested.py"
        test_file.write_text(
            '''
class Outer:
    """Outer class."""

    class Inner:
        """Inner class."""

        def inner_method(self):
            """Inner method."""
            pass

    def outer_method(self):
        """Outer method."""
        pass
'''
        )

        chunks = chunker.chunk_file(str(test_file))

        # Find all chunks
        outer_class = next(
            (c for c in chunks if c.name == "Outer" and c.chunk_type == "class"), None
        )
        inner_class = next(
            (c for c in chunks if c.name == "Inner" and c.chunk_type == "class"), None
        )
        outer_method = next((c for c in chunks if c.name == "outer_method"), None)
        inner_method = next((c for c in chunks if c.name == "inner_method"), None)

        assert outer_class is not None, "Outer class should exist"
        assert outer_method is not None, "Outer method should exist"

        # Outer method should point to outer class
        assert (
            outer_method.parent_chunk_id == outer_class.chunk_id
        ), "Outer method should point to outer class"

        # Note: Nested classes might not be fully supported yet,
        # but outer_method should definitely work
        if inner_class and inner_method:
            # If nested classes are supported, check inner method
            assert (
                inner_method.parent_chunk_id == inner_class.chunk_id
            ), "Inner method should point to inner class"

    def test_class_with_no_methods(self, chunker, tmp_path):
        """Test that empty classes work correctly."""
        test_file = tmp_path / "empty_class.py"
        test_file.write_text(
            '''
class EmptyClass:
    """An empty class."""
    pass
'''
        )

        chunks = chunker.chunk_file(str(test_file))

        class_chunk = next((c for c in chunks if c.chunk_type == "class"), None)
        assert class_chunk is not None, "Class chunk should exist"
        assert (
            class_chunk.parent_chunk_id is None
        ), "Class should have no parent_chunk_id"

    def test_parent_chunk_id_format(self, chunker, tmp_path):
        """Test that parent_chunk_id follows the expected format."""
        test_file = tmp_path / "format_test.py"
        test_file.write_text(
            """
class TestClass:
    def test_method(self):
        pass
"""
        )

        chunks = chunker.chunk_file(str(test_file))

        class_chunk = next((c for c in chunks if c.chunk_type == "class"), None)
        method_chunk = next((c for c in chunks if c.chunk_type == "method"), None)

        assert class_chunk is not None
        assert method_chunk is not None

        # Verify chunk_id format: relative_path:start-end:type:name
        assert class_chunk.chunk_id is not None
        assert ":" in class_chunk.chunk_id
        parts = class_chunk.chunk_id.split(":")
        assert len(parts) == 4, f"chunk_id should have 4 parts, got {parts}"
        assert parts[2] == "class", "Third part should be 'class'"
        assert parts[3] == "TestClass", "Fourth part should be class name"

        # Verify parent_chunk_id points to class
        assert method_chunk.parent_chunk_id == class_chunk.chunk_id
