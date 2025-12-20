"""
Unit tests for Tier 1 entity tracking extractors.

Tests ClassAttributeExtractor, DataclassFieldExtractor, and ContextManagerExtractor
to ensure they correctly identify and track class attributes, dataclass fields,
and context manager usage.
"""

import pytest

from graph.relationship_extractors.class_attr_extractor import ClassAttributeExtractor
from graph.relationship_extractors.context_manager_extractor import (
    ContextManagerExtractor,
)
from graph.relationship_extractors.dataclass_field_extractor import (
    DataclassFieldExtractor,
)
from graph.relationship_types import RelationshipType


class TestClassAttributeExtractor:
    """Test ClassAttributeExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create ClassAttributeExtractor instance."""
        return ClassAttributeExtractor()

    @pytest.fixture
    def chunk_metadata(self):
        """Create test chunk metadata."""
        return {
            "chunk_id": "test.py:1-10:class:TestClass",
            "chunk_type": "class",
            "file_path": "test.py",
        }

    def test_simple_class_attribute(self, extractor, chunk_metadata):
        """Test extracting simple class attribute."""
        code = """
class Config:
    timeout = 30
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "Config.timeout"
        assert edges[0].relationship_type == RelationshipType.DEFINES_CLASS_ATTR
        assert edges[0].metadata["class_name"] == "Config"
        assert edges[0].metadata["attr_name"] == "timeout"

    def test_annotated_class_attribute(self, extractor, chunk_metadata):
        """Test extracting annotated class attribute."""
        code = """
class Config:
    timeout: int = 30
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "Config.timeout"
        assert edges[0].metadata["has_annotation"] is True

    def test_multiple_class_attributes(self, extractor, chunk_metadata):
        """Test extracting multiple class attributes."""
        code = """
class Config:
    timeout = 30
    retries: int = 3
    debug = False
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 3
        target_names = {e.target_name for e in edges}
        assert target_names == {"Config.timeout", "Config.retries", "Config.debug"}

    def test_ignores_methods(self, extractor, chunk_metadata):
        """Test that methods are ignored."""
        code = """
class Config:
    timeout = 30

    def get_timeout(self):
        return self.timeout
"""
        edges = extractor.extract(code, chunk_metadata)

        # Should only get the class attribute, not the method
        assert len(edges) == 1
        assert edges[0].target_name == "Config.timeout"

    def test_ignores_instance_attributes(self, extractor, chunk_metadata):
        """Test that instance attributes are ignored."""
        code = """
class Config:
    timeout = 30  # Class attribute

    def __init__(self):
        self.instance_attr = 1  # Instance attribute (not tracked)
"""
        edges = extractor.extract(code, chunk_metadata)

        # Should only get the class attribute
        assert len(edges) == 1
        assert edges[0].target_name == "Config.timeout"

    def test_multiple_classes(self, extractor, chunk_metadata):
        """Test extracting attributes from multiple classes."""
        code = """
class Config:
    timeout = 30

class Settings:
    debug = True
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 2
        target_names = {e.target_name for e in edges}
        assert target_names == {"Config.timeout", "Settings.debug"}


class TestDataclassFieldExtractor:
    """Test DataclassFieldExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create DataclassFieldExtractor instance."""
        return DataclassFieldExtractor()

    @pytest.fixture
    def chunk_metadata(self):
        """Create test chunk metadata."""
        return {
            "chunk_id": "test.py:1-10:class:User",
            "chunk_type": "class",
            "file_path": "test.py",
        }

    def test_basic_dataclass_field(self, extractor, chunk_metadata):
        """Test extracting basic dataclass field."""
        code = """
@dataclass
class User:
    name: str
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "User.name"
        assert edges[0].relationship_type == RelationshipType.DEFINES_FIELD
        assert edges[0].metadata["class_name"] == "User"
        assert edges[0].metadata["field_name"] == "name"
        assert edges[0].metadata["has_default"] is False

    def test_field_with_default(self, extractor, chunk_metadata):
        """Test extracting dataclass field with default value."""
        code = """
@dataclass
class User:
    age: int = 0
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "User.age"
        assert edges[0].metadata["has_default"] is True

    def test_multiple_fields(self, extractor, chunk_metadata):
        """Test extracting multiple dataclass fields."""
        code = """
@dataclass
class User:
    name: str
    age: int = 0
    email: str = ""
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 3
        target_names = {e.target_name for e in edges}
        assert target_names == {"User.name", "User.age", "User.email"}

    def test_dataclass_with_parentheses(self, extractor, chunk_metadata):
        """Test dataclass with arguments."""
        code = """
@dataclass(frozen=True)
class Point:
    x: float
    y: float
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 2
        target_names = {e.target_name for e in edges}
        assert target_names == {"Point.x", "Point.y"}

    def test_non_dataclass_ignored(self, extractor, chunk_metadata):
        """Test that non-dataclass classes are ignored."""
        code = """
class Regular:
    name: str = "test"
"""
        edges = extractor.extract(code, chunk_metadata)

        # No @dataclass decorator, should be ignored
        assert len(edges) == 0

    def test_dataclass_without_fields(self, extractor, chunk_metadata):
        """Test dataclass without fields."""
        code = """
@dataclass
class Empty:
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0


class TestContextManagerExtractor:
    """Test ContextManagerExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create ContextManagerExtractor instance."""
        return ContextManagerExtractor()

    @pytest.fixture
    def chunk_metadata(self):
        """Create test chunk metadata."""
        return {
            "chunk_id": "test.py:1-10:function:test_func",
            "chunk_type": "function",
            "file_path": "test.py",
        }

    def test_simple_context_manager(self, extractor, chunk_metadata):
        """Test extracting simple context manager usage."""
        code = """
def test_func():
    with Progress() as p:
        pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "Progress"
        assert edges[0].relationship_type == RelationshipType.USES_CONTEXT_MANAGER

    def test_builtin_excluded(self, extractor, chunk_metadata):
        """Test that builtin context managers are excluded."""
        code = """
def test_func():
    with open("file.txt") as f:
        pass
"""
        edges = extractor.extract(code, chunk_metadata)

        # 'open' is builtin, should be excluded
        assert len(edges) == 0

    def test_multiple_context_managers(self, extractor, chunk_metadata):
        """Test extracting multiple context manager usages."""
        code = """
def test_func():
    with Progress() as p:
        pass
    with transaction.atomic():
        pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 2
        target_names = {e.target_name for e in edges}
        assert target_names == {"Progress", "atomic"}

    def test_async_context_manager(self, extractor, chunk_metadata):
        """Test extracting async context manager."""
        code = """
async def test_func():
    async with session.get(url) as resp:
        pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "get"

    def test_context_manager_name_only(self, extractor, chunk_metadata):
        """Test context manager used by name (not call)."""
        code = """
def test_func():
    manager = Manager()
    with manager:
        pass
"""
        edges = extractor.extract(code, chunk_metadata)

        # Should extract 'manager' name usage
        assert len(edges) == 1
        assert edges[0].target_name == "manager"

    def test_multiple_items_in_with(self, extractor, chunk_metadata):
        """Test with statement with multiple items."""
        code = """
def test_func():
    with Progress() as p1, Progress() as p2:
        pass
"""
        edges = extractor.extract(code, chunk_metadata)

        # Should extract both
        assert len(edges) == 2
        assert all(e.target_name == "Progress" for e in edges)
