"""
Unit tests for Priority 3 relationship extractors.

Tests:
- OverrideExtractor: Method override detection
- ImplementsExtractor: Protocol/ABC implementation detection
"""

import pytest

from graph.relationship_extractors.implements_extractor import ImplementsExtractor
from graph.relationship_extractors.override_extractor import OverrideExtractor
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


# ===== OverrideExtractor Tests =====


def test_override_with_decorator(chunk_metadata):
    """Test detection of override with @override decorator (Python 3.12+)."""
    code = """
class Parent:
    def foo(self):
        pass

class Child(Parent):
    @override
    def foo(self):
        pass
"""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect the @override decorator
    assert len(edges) == 1
    edge = edges[0]
    assert edge.relationship_type == RelationshipType.OVERRIDES
    assert edge.target_name == "foo"
    assert edge.confidence == 1.0
    assert edge.metadata.get("detection_method") == "override_decorator"


def test_override_with_typing_override(chunk_metadata):
    """Test detection of @typing.override decorator."""
    code = """
from typing import override

class Parent:
    def process(self):
        pass

class Child(Parent):
    @typing.override
    def process(self):
        pass
"""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "process"
    assert edges[0].metadata.get("detection_method") == "override_decorator"


def test_override_with_super_call(chunk_metadata):
    """Test detection of override via super() call."""
    code = """
class Parent:
    def foo(self):
        pass

class Child(Parent):
    def foo(self):
        super().foo()
"""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect super().foo() call
    assert len(edges) == 1
    edge = edges[0]
    assert edge.relationship_type == RelationshipType.OVERRIDES
    assert edge.target_name == "foo"
    assert edge.confidence == 1.0
    assert edge.metadata.get("detection_method") == "super_call"


def test_override_multiple_super_calls(chunk_metadata):
    """Test detection of multiple super() calls in same method."""
    code = """
class Parent:
    def process(self):
        pass
    def cleanup(self):
        pass

class Child(Parent):
    def process(self):
        super().process()
        super().cleanup()
"""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect both super() calls
    assert len(edges) == 2
    targets = {edge.target_name for edge in edges}
    assert targets == {"process", "cleanup"}


def test_override_skips_private_methods(chunk_metadata):
    """Test that private methods (single underscore) are skipped."""
    code = """
class Parent:
    def _private_method(self):
        pass

class Child(Parent):
    def _private_method(self):
        super()._private_method()
"""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should skip private methods
    assert len(edges) == 0


def test_override_detects_dunder_methods(chunk_metadata):
    """Test that dunder methods are detected."""
    code = """
class Parent:
    def __init__(self):
        pass

class Child(Parent):
    def __init__(self):
        super().__init__()
"""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect __init__ override
    assert len(edges) == 1
    assert edges[0].target_name == "__init__"


def test_override_no_inheritance(chunk_metadata):
    """Test that classes without inheritance don't produce overrides."""
    code = """
class StandaloneClass:
    def foo(self):
        pass
"""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # No inheritance, no overrides
    assert len(edges) == 0


def test_override_decorator_priority(chunk_metadata):
    """Test that @override decorator takes priority over super() detection."""
    code = """
class Parent:
    def foo(self):
        pass

class Child(Parent):
    @override
    def foo(self):
        super().foo()  # Should not create duplicate edge
"""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should only create one edge (decorator takes priority)
    assert len(edges) == 1
    assert edges[0].metadata.get("detection_method") == "override_decorator"


# ===== ImplementsExtractor Tests =====


def test_implements_protocol(chunk_metadata):
    """Test detection of Protocol implementation."""
    code = """
from typing import Protocol

class LoggingProtocol(Protocol):
    def log(self, msg: str): ...

class FileHandler(LoggingProtocol):
    def log(self, msg: str):
        print(msg)
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect LoggingProtocol -> Protocol (direct protocol definition)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.relationship_type == RelationshipType.IMPLEMENTS
    assert edge.target_name == "Protocol"
    assert edge.confidence == 1.0
    assert edge.metadata.get("is_protocol") is True


def test_implements_abc(chunk_metadata):
    """Test detection of ABC implementation."""
    code = """
from abc import ABC, abstractmethod

class AbstractBase(ABC):
    @abstractmethod
    def process(self):
        pass

class Concrete(AbstractBase):
    def process(self):
        return "processed"
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect AbstractBase -> ABC (direct ABC definition)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "ABC"
    assert edge.metadata.get("is_abc") is True


def test_implements_collections_abc(chunk_metadata):
    """Test detection of collections.abc implementations."""
    code = """
from collections.abc import Iterable, Iterator

class MyIterable(Iterable):
    def __iter__(self):
        return iter([1, 2, 3])

class MyContainer(Iterable, Iterator):
    def __iter__(self):
        return self
    def __next__(self):
        raise StopIteration
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect both Iterable and Iterator
    assert (
        len(edges) == 3
    )  # MyIterable -> Iterable, MyContainer -> Iterable, MyContainer -> Iterator
    targets = {edge.target_name for edge in edges}
    assert "Iterable" in targets
    assert "Iterator" in targets


def test_implements_typing_protocol(chunk_metadata):
    """Test detection of typing.Protocol qualified name."""
    code = """
import typing

class Comparable(typing.Protocol):
    def __lt__(self, other): ...

class Number(Comparable):
    def __lt__(self, other):
        return True
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect Protocol implementation (extracts "Protocol" from typing.Protocol)
    protocol_edges = [e for e in edges if e.target_name == "Protocol"]
    assert len(protocol_edges) >= 1


def test_implements_multiple_protocols(chunk_metadata):
    """Test detection of multiple protocol implementations."""
    code = """
from typing import Protocol
from abc import ABC

class Protocol1(Protocol):
    pass

class Protocol2(Protocol):
    pass

class Implementation(Protocol1, Protocol2, ABC):
    pass
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect Protocol1 -> Protocol, Protocol2 -> Protocol, Implementation -> ABC
    assert len(edges) == 3
    targets = {edge.target_name for edge in edges}
    assert targets == {"Protocol", "ABC"}


def test_implements_no_protocols(chunk_metadata):
    """Test that regular inheritance doesn't produce implement edges."""
    code = """
class Parent:
    pass

class Child(Parent):
    pass
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Regular inheritance should not create implement edges
    assert len(edges) == 0


def test_implements_generic_protocol(chunk_metadata):
    """Test detection of generic protocol (Protocol[T])."""
    code = """
from typing import Protocol, TypeVar

T = TypeVar('T')

class Generic(Protocol[T]):
    def get(self) -> T: ...

class StringGetter(Generic):
    def get(self) -> str:
        return "hello"
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect Generic -> Protocol (extracts base from Protocol[T])
    assert len(edges) == 1
    assert edges[0].target_name == "Protocol"


def test_implements_supports_protocols(chunk_metadata):
    """Test detection of SupportsXXX typing protocols."""
    code = """
from typing import SupportsInt, SupportsFloat

class Number(SupportsInt, SupportsFloat):
    def __int__(self):
        return 42
    def __float__(self):
        return 42.0
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should detect both Supports protocols
    assert len(edges) == 2
    targets = {edge.target_name for edge in edges}
    assert targets == {"SupportsInt", "SupportsFloat"}


def test_implements_no_bases(chunk_metadata):
    """Test that classes without base classes don't produce edges."""
    code = """
class StandaloneClass:
    def method(self):
        pass
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # No base classes, no implementation edges
    assert len(edges) == 0


# ===== Edge Cases and Error Handling =====


def test_override_syntax_error(chunk_metadata):
    """Test that syntax errors are handled gracefully."""
    code = """
class Invalid(
    def foo(self):  # Syntax error
"""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should return empty list on syntax error
    assert len(edges) == 0


def test_implements_syntax_error(chunk_metadata):
    """Test that syntax errors are handled gracefully."""
    code = """
class Invalid(Protocol
    def foo  # Syntax error
"""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Should return empty list on syntax error
    assert len(edges) == 0


def test_override_empty_code(chunk_metadata):
    """Test handling of empty code."""
    code = ""

    extractor = OverrideExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 0


def test_implements_empty_code(chunk_metadata):
    """Test handling of empty code."""
    code = ""

    extractor = ImplementsExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 0
