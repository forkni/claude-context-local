"""Unit tests for the fixed tree-sitter based chunking."""

import tempfile
from pathlib import Path
from unittest import TestCase

import pytest

from chunking.tree_sitter import (JavaScriptChunker, PythonChunker,
                                  TreeSitterChunker)


class TestPythonChunker(TestCase):
    """Test Python-specific tree-sitter chunking."""

    def setUp(self):
        try:
            self.chunker = PythonChunker()
        except ValueError:
            self.skipTest("tree-sitter-python not installed")

    def test_function_chunking(self):
        """Test chunking of Python functions."""
        code = '''
def simple_function():
    """A simple function."""
    return 42

def async_function():
    """An async function."""
    import asyncio
    await asyncio.sleep(1)
    
class MyClass:
    def method(self):
        return "method"
'''
        chunks = self.chunker.chunk_code(code)

        # Should find 2 functions and 1 class
        assert len(chunks) >= 2  # At minimum the functions and class

        # Check function names in metadata
        func_names = [c.metadata.get("name") for c in chunks if "name" in c.metadata]
        assert "simple_function" in func_names or any(
            "simple_function" in c.content for c in chunks
        )

    def test_class_chunking(self):
        """Test chunking of Python classes."""
        code = '''
class SimpleClass:
    """A simple class."""
    
    def __init__(self):
        self.value = 0
    
    def method(self):
        return self.value

@dataclass
class DataClass:
    field1: str
    field2: int
'''
        chunks = self.chunker.chunk_code(code)

        # Should find at least 1 class (SimpleClass)
        assert len(chunks) >= 1

        # Check for class in node types
        class_chunks = [
            c
            for c in chunks
            if "class" in c.node_type or c.node_type == "decorated_definition"
        ]
        assert len(class_chunks) > 0

    def test_decorated_definition(self):
        """Test chunking of decorated definitions."""
        code = """
@decorator1
@decorator2
def decorated_function():
    return "decorated"

@property
def my_property(self):
    return self._value
"""
        chunks = self.chunker.chunk_code(code)

        # Should find decorated definitions
        assert len(chunks) >= 1

        # Check for decorators in metadata or content
        has_decorator = any(
            "decorator" in str(c.metadata) or "@" in c.content for c in chunks
        )
        assert has_decorator

    def test_empty_file(self):
        """Test chunking of empty file."""
        code = ""
        chunks = self.chunker.chunk_code(code)
        assert len(chunks) == 0

    def test_module_only(self):
        """Test file with only module-level code."""
        code = """
import os
import sys

CONSTANT = 42
variable = "test"

print("Module level code")
"""
        chunks = self.chunker.chunk_code(code)

        # Should create a module chunk since no functions/classes
        assert len(chunks) == 1
        assert chunks[0].node_type == "module"


class TestJavaScriptChunker(TestCase):
    """Test JavaScript-specific tree-sitter chunking."""

    def setUp(self):
        try:
            self.chunker = JavaScriptChunker()
        except ValueError:
            self.skipTest("tree-sitter-javascript not installed")

    def test_function_types(self):
        """Test different JavaScript function types."""
        code = """
function normalFunction() {
    return 42;
}

const arrowFunction = () => {
    return "arrow";
};

const asyncFunc = async function() {
    await Promise.resolve();
};

class MyClass {
    method() {
        return "method";
    }
}
"""
        chunks = self.chunker.chunk_code(code)

        # Should find various function types
        assert len(chunks) >= 1

        # Check for different node types
        node_types = {c.node_type for c in chunks}
        assert len(node_types) > 0  # Should have at least some chunks


class TestTreeSitterChunker(TestCase):
    """Test main TreeSitterChunker class."""

    def setUp(self):
        self.chunker = TreeSitterChunker()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_language_detection(self):
        """Test language detection from file extension."""
        # Check if Python is supported (requires tree-sitter-python)
        import chunking.tree_sitter as tsf

        if "python" in tsf.AVAILABLE_LANGUAGES:
            assert self.chunker.is_supported("test.py")

        # These won't be supported without their packages
        assert not self.chunker.is_supported("test.txt")
        assert not self.chunker.is_supported("test.md")

    def test_chunk_python_file(self):
        """Test chunking a Python file."""
        import chunking.tree_sitter as tsf

        if "python" not in tsf.AVAILABLE_LANGUAGES:
            self.skipTest("tree-sitter-python not installed")

        file_path = Path(self.temp_dir) / "test.py"
        code = """
def test_function():
    return "test"

class TestClass:
    pass
"""
        file_path.write_text(code)

        chunks = self.chunker.chunk_file(str(file_path))

        assert len(chunks) >= 2
        assert all(c.language == "python" for c in chunks)

    def test_unsupported_file(self):
        """Test handling of unsupported file types."""
        chunks = self.chunker.chunk_file("test.txt", "some text content")
        assert len(chunks) == 0

    def test_get_supported_extensions(self):
        """Test getting list of supported extensions."""
        extensions = TreeSitterChunker.get_supported_extensions()

        # At minimum Python should be supported if tree-sitter-python is installed
        import chunking.tree_sitter as tsf

        if "python" in tsf.AVAILABLE_LANGUAGES:
            assert ".py" in extensions

    def test_get_available_languages(self):
        """Test getting available languages."""
        languages = TreeSitterChunker.get_available_languages()

        # Should have at least Python if installed
        import chunking.tree_sitter as tsf

        if "python" in tsf.AVAILABLE_LANGUAGES:
            assert "python" in languages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
