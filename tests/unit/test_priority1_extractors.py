"""
Unit tests for Priority 1 relationship extractors.

Tests:
- InheritanceExtractor
- TypeAnnotationExtractor
- ImportExtractor
"""

import pytest

from graph.relationship_extractors.import_extractor import ImportExtractor
from graph.relationship_extractors.inheritance_extractor import InheritanceExtractor
from graph.relationship_extractors.type_extractor import TypeAnnotationExtractor
from graph.relationship_types import RelationshipType

# ===== Test Fixtures =====


@pytest.fixture
def chunk_metadata():
    """Standard chunk metadata for testing."""
    return {
        "chunk_id": "test.py:1-100:module:test",
        "file_path": "test.py",
        "name": "test",
        "chunk_type": "module",
    }


# ===== InheritanceExtractor Tests =====


def test_inheritance_single_parent(chunk_metadata):
    """Test extraction of single parent inheritance."""
    code = """
class Parent:
    pass

class Child(Parent):
    pass
"""

    extractor = InheritanceExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should find one inherits edge
    assert len(edges) == 1

    edge = edges[0]
    assert edge.relationship_type == RelationshipType.INHERITS
    assert edge.target_name == "Parent"
    assert "Child" in edge.source_id
    assert edge.confidence == 1.0


def test_inheritance_multiple_parents(chunk_metadata):
    """Test extraction of multiple inheritance."""
    code = """
class Mixin1:
    pass

class Mixin2:
    pass

class Child(Mixin1, Mixin2):
    pass
"""

    extractor = InheritanceExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should find two inherits edges
    assert len(edges) == 2

    targets = {edge.target_name for edge in edges}
    assert targets == {"Mixin1", "Mixin2"}

    # Both should have is_multiple metadata
    for edge in edges:
        assert edge.metadata.get("is_multiple") is True


def test_inheritance_qualified_parent(chunk_metadata):
    """Test inheritance from qualified parent (module.Class)."""
    code = """
class Child(module.Parent):
    pass
"""

    extractor = InheritanceExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "module.Parent"


def test_inheritance_generic_parent(chunk_metadata):
    """Test inheritance from generic parent."""
    code = """
from typing import Generic, TypeVar

T = TypeVar('T')

class MyList(list, Generic[T]):
    pass
"""

    extractor = InheritanceExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should find inheritance from 'list'
    # Generic should be skipped (not interesting)
    targets = {edge.target_name for edge in edges}
    assert "list" in targets


def test_inheritance_skips_builtins(chunk_metadata):
    """Test that uninteresting base classes are skipped."""
    code = """
class MyError(Exception):
    pass

class MyClass(object):
    pass
"""

    extractor = InheritanceExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # object is uninteresting and should be skipped
    # Exception is useful and should be tracked
    assert len(edges) == 1
    assert edges[0].target_name == "Exception"


def test_inheritance_no_parents(chunk_metadata):
    """Test class without inheritance produces no edges."""
    code = """
class Standalone:
    def method(self):
        pass
"""

    extractor = InheritanceExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 0


def test_inheritance_malformed_code(chunk_metadata):
    """Test that malformed code is handled gracefully."""
    code = """
class Broken(
    # Missing closing paren
"""

    extractor = InheritanceExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should return empty list, not crash
    assert edges == []


# ===== TypeAnnotationExtractor Tests =====


def test_type_annotation_parameter_types(chunk_metadata):
    """Test extraction of parameter type hints."""
    code = """
def process(user: User, count: int, data: str) -> None:
    pass
"""

    extractor = TypeAnnotationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should find User, int, str
    # None is skipped (no real value)
    type_names = {edge.target_name for edge in edges}

    assert "User" in type_names
    assert "int" in type_names
    assert "str" in type_names


def test_type_annotation_return_type(chunk_metadata):
    """Test extraction of return type hints."""
    code = """
def get_user() -> User:
    pass
"""

    extractor = TypeAnnotationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "User"
    assert edges[0].metadata["annotation_location"] == "return_type"


def test_type_annotation_generic_types(chunk_metadata):
    """Test extraction from generic types."""
    code = """
from typing import List, Dict

def process(items: List[User]) -> Dict[str, int]:
    pass
"""

    extractor = TypeAnnotationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should extract User, str, int
    # List and Dict are skipped (typing module constructs)
    type_names = {edge.target_name for edge in edges}

    assert "User" in type_names
    assert "str" in type_names
    assert "int" in type_names

    # Should NOT include typing constructs
    assert "List" not in type_names
    assert "Dict" not in type_names


def test_type_annotation_nested_generics(chunk_metadata):
    """Test extraction from nested generic types."""
    code = """
def process() -> Dict[str, List[User]]:
    pass
"""

    extractor = TypeAnnotationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    type_names = {edge.target_name for edge in edges}

    # Should find all nested types
    assert "str" in type_names
    assert "User" in type_names


def test_type_annotation_optional(chunk_metadata):
    """Test extraction from Optional type."""
    code = """
from typing import Optional

def find_user() -> Optional[User]:
    pass
"""

    extractor = TypeAnnotationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    type_names = {edge.target_name for edge in edges}

    assert "User" in type_names
    assert "Optional" not in type_names  # Typing construct, skipped


def test_type_annotation_qualified_types(chunk_metadata):
    """Test extraction of qualified type names."""
    code = """
def process(user: models.User) -> services.Result:
    pass
"""

    extractor = TypeAnnotationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    type_names = {edge.target_name for edge in edges}

    assert "models.User" in type_names
    assert "services.Result" in type_names


def test_type_annotation_no_annotations(chunk_metadata):
    """Test function without type hints produces no edges."""
    code = """
def process(x, y):
    return x + y
"""

    extractor = TypeAnnotationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 0


def test_type_annotation_class_attribute(chunk_metadata):
    """Test extraction from class attribute annotations."""
    code = """
class MyClass:
    attr: int = 0
    user: User = None
"""

    extractor = TypeAnnotationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    type_names = {edge.target_name for edge in edges}

    assert "int" in type_names
    assert "User" in type_names


# ===== ImportExtractor Tests =====


def test_import_simple_import(chunk_metadata):
    """Test extraction of simple import statement."""
    code = """
import os
import sys
"""

    extractor = ImportExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 2

    import_names = {edge.target_name for edge in edges}
    assert "os" in import_names
    assert "sys" in import_names

    # Check metadata
    for edge in edges:
        assert edge.metadata["import_type"] == "import"


def test_import_with_alias(chunk_metadata):
    """Test import with alias."""
    code = """
import numpy as np
"""

    extractor = ImportExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "numpy"
    assert edges[0].metadata["alias"] == "np"


def test_import_from_module(chunk_metadata):
    """Test from module import statement."""
    code = """
from os import path
from typing import List, Dict
"""

    extractor = ImportExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 3

    import_names = {edge.target_name for edge in edges}
    assert "os.path" in import_names
    assert "typing.List" in import_names
    assert "typing.Dict" in import_names


def test_import_from_package(chunk_metadata):
    """Test from package.module import."""
    code = """
from package.submodule import function
"""

    extractor = ImportExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "package.submodule.function"


def test_import_relative_imports(chunk_metadata):
    """Test relative import statements."""
    code = """
from . import helper
from .. import util
from ...package import module
"""

    extractor = ImportExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 3

    import_names = {edge.target_name for edge in edges}
    assert ".helper" in import_names
    assert "..util" in import_names
    assert "...package.module" in import_names

    # Check relative import metadata
    for edge in edges:
        assert edge.metadata["is_relative"] is True
        assert edge.metadata["relative_level"] > 0


def test_import_star_import(chunk_metadata):
    """Test star import."""
    code = """
from module import *
"""

    extractor = ImportExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "module.*"
    assert edges[0].metadata["is_star_import"] is True


def test_import_multiple_from_same_module(chunk_metadata):
    """Test importing multiple symbols from same module."""
    code = """
from module import func1, func2, Class1
"""

    extractor = ImportExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 3

    import_names = {edge.target_name for edge in edges}
    assert "module.func1" in import_names
    assert "module.func2" in import_names
    assert "module.Class1" in import_names


def test_import_no_imports(chunk_metadata):
    """Test code without imports produces no edges."""
    code = """
def process():
    return 42
"""

    extractor = ImportExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 0


# ===== Edge Cases and Error Handling =====


def test_extractors_handle_syntax_errors(chunk_metadata):
    """Test that all extractors handle syntax errors gracefully."""
    code = """
def broken(
    # Missing closing paren
"""

    extractors = [InheritanceExtractor(), TypeAnnotationExtractor(), ImportExtractor()]

    for extractor in extractors:
        edges = extractor.extract(code, chunk_metadata)
        assert (
            edges == []
        ), f"{extractor.__class__.__name__} should return empty list on syntax error"


def test_extractors_handle_empty_code(chunk_metadata):
    """Test that all extractors handle empty code."""
    code = ""

    extractors = [InheritanceExtractor(), TypeAnnotationExtractor(), ImportExtractor()]

    for extractor in extractors:
        edges = extractor.extract(code, chunk_metadata)
        assert (
            edges == []
        ), f"{extractor.__class__.__name__} should return empty list for empty code"


def test_extractors_set_correct_relationship_type(chunk_metadata):
    """Test that each extractor sets the correct relationship type."""
    # Test inheritance
    code = "class Child(Parent): pass"
    extractor = InheritanceExtractor()
    edges = extractor.extract(code, chunk_metadata)
    if edges:
        assert all(e.relationship_type == RelationshipType.INHERITS for e in edges)

    # Test type annotations
    code = "def foo(x: int) -> str: pass"
    extractor = TypeAnnotationExtractor()
    edges = extractor.extract(code, chunk_metadata)
    if edges:
        assert all(e.relationship_type == RelationshipType.USES_TYPE for e in edges)

    # Test imports
    code = "import os"
    extractor = ImportExtractor()
    edges = extractor.extract(code, chunk_metadata)
    if edges:
        assert all(e.relationship_type == RelationshipType.IMPORTS for e in edges)


def test_extractors_set_line_numbers(chunk_metadata):
    """Test that extractors capture line numbers."""
    # Inheritance
    code = """# Line 1
class Parent:  # Line 2
    pass

class Child(Parent):  # Line 5
    pass
"""

    extractor = InheritanceExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].line_number == 5  # Child defined on line 5


def test_extractors_all_have_confidence_1_0(chunk_metadata):
    """Test that Priority 1 extractors all use confidence 1.0."""
    codes = [
        "class Child(Parent): pass",  # Inheritance
        "def foo(x: int): pass",  # Type annotation
        "import os",  # Import
    ]

    extractors = [InheritanceExtractor(), TypeAnnotationExtractor(), ImportExtractor()]

    for code, extractor in zip(codes, extractors, strict=False):
        edges = extractor.extract(code, chunk_metadata)
        if edges:
            assert all(
                e.confidence == 1.0 for e in edges
            ), f"{extractor.__class__.__name__} should use confidence 1.0"
