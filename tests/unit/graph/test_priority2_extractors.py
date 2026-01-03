"""
Unit tests for Priority 2 relationship extractors.

Tests:
- DecoratorExtractor
- ExceptionExtractor
- InstantiationExtractor
"""

import pytest

from graph.relationship_extractors.decorator_extractor import DecoratorExtractor
from graph.relationship_extractors.exception_extractor import ExceptionExtractor
from graph.relationship_extractors.instantiation_extractor import InstantiationExtractor
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


# ===== DecoratorExtractor Tests =====


def test_decorator_simple(chunk_metadata):
    """Test extraction of simple decorator."""
    code = """
@decorator
def func():
    pass
"""

    extractor = DecoratorExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1

    edge = edges[0]
    assert edge.relationship_type == RelationshipType.DECORATES
    assert edge.target_name == "decorator"
    assert edge.confidence == 1.0


def test_decorator_with_module(chunk_metadata):
    """Test extraction of decorator with module prefix."""
    code = """
@module.decorator
def func():
    pass
"""

    extractor = DecoratorExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "module.decorator"


def test_decorator_with_args(chunk_metadata):
    """Test extraction of decorator with arguments."""
    code = """
@decorator(arg=value)
def func():
    pass
"""

    extractor = DecoratorExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "decorator"


def test_decorator_multiple(chunk_metadata):
    """Test extraction of multiple decorators."""
    code = """
@decorator1
@decorator2
@decorator3
def func():
    pass
"""

    extractor = DecoratorExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 3
    targets = {edge.target_name for edge in edges}
    assert targets == {"decorator1", "decorator2", "decorator3"}


def test_decorator_class(chunk_metadata):
    """Test extraction of decorator on class."""
    code = """
@dataclass
class MyClass:
    x: int
"""

    extractor = DecoratorExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "dataclass"


def test_decorator_async_function(chunk_metadata):
    """Test extraction of decorator on async function."""
    code = """
@async_decorator
async def async_func():
    pass
"""

    extractor = DecoratorExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "async_decorator"


def test_decorator_skips_builtins(chunk_metadata):
    """Test that common builtins are skipped."""
    code = """
class MyClass:
    @property
    def value(self):
        return self._value

    @staticmethod
    def static_method():
        pass

    @classmethod
    def class_method(cls):
        pass
"""

    extractor = DecoratorExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # property, staticmethod, classmethod should be skipped
    assert len(edges) == 0


def test_decorator_nested_attribute(chunk_metadata):
    """Test extraction of deeply nested decorator."""
    code = """
@outer.middle.inner.decorator
def func():
    pass
"""

    extractor = DecoratorExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "outer.middle.inner.decorator"


# ===== ExceptionExtractor Tests =====


def test_exception_raise_simple(chunk_metadata):
    """Test extraction of simple raise statement."""
    code = """
raise ValueError("error")
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1

    edge = edges[0]
    assert edge.relationship_type == RelationshipType.RAISES
    assert edge.target_name == "ValueError"
    assert edge.confidence == 1.0


def test_exception_raise_without_call(chunk_metadata):
    """Test extraction of raise without instantiation."""
    code = """
raise ValueError
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "ValueError"


def test_exception_raise_with_module(chunk_metadata):
    """Test extraction of raise with module prefix."""
    code = """
raise custom.CustomError("error")
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "custom.CustomError"


def test_exception_bare_raise_skipped(chunk_metadata):
    """Test that bare raise is skipped."""
    code = """
try:
    pass
except Exception:
    raise
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Only the except should be captured, not the bare raise
    assert len(edges) == 1
    assert edges[0].relationship_type == RelationshipType.CATCHES


def test_exception_catch_single(chunk_metadata):
    """Test extraction of single except handler."""
    code = """
try:
    pass
except ValueError:
    pass
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1

    edge = edges[0]
    assert edge.relationship_type == RelationshipType.CATCHES
    assert edge.target_name == "ValueError"


def test_exception_catch_multiple(chunk_metadata):
    """Test extraction of tuple except handler."""
    code = """
try:
    pass
except (TypeError, KeyError):
    pass
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 2
    targets = {edge.target_name for edge in edges}
    assert targets == {"TypeError", "KeyError"}
    assert all(edge.relationship_type == RelationshipType.CATCHES for edge in edges)


def test_exception_catch_with_alias(chunk_metadata):
    """Test extraction of except handler with alias."""
    code = """
try:
    pass
except ValueError as e:
    pass
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "ValueError"


def test_exception_catch_with_module(chunk_metadata):
    """Test extraction of except handler with module prefix."""
    code = """
try:
    pass
except custom.CustomError:
    pass
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "custom.CustomError"


def test_exception_bare_except_skipped(chunk_metadata):
    """Test that bare except is skipped."""
    code = """
try:
    pass
except:
    pass
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Bare except doesn't have a specific type
    assert len(edges) == 0


def test_exception_mixed_raise_and_catch(chunk_metadata):
    """Test extraction of both raises and catches."""
    code = """
try:
    raise ValueError("error")
except TypeError:
    pass
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 2

    raises = [e for e in edges if e.relationship_type == RelationshipType.RAISES]
    catches = [e for e in edges if e.relationship_type == RelationshipType.CATCHES]

    assert len(raises) == 1
    assert len(catches) == 1
    assert raises[0].target_name == "ValueError"
    assert catches[0].target_name == "TypeError"


def test_exception_multiple_handlers(chunk_metadata):
    """Test extraction of multiple except handlers."""
    code = """
try:
    pass
except ValueError:
    pass
except TypeError:
    pass
except KeyError:
    pass
"""

    extractor = ExceptionExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 3
    targets = {edge.target_name for edge in edges}
    assert targets == {"ValueError", "TypeError", "KeyError"}


# ===== InstantiationExtractor Tests =====


def test_instantiation_simple(chunk_metadata):
    """Test extraction of simple class instantiation."""
    code = """
obj = MyClass()
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1

    edge = edges[0]
    assert edge.relationship_type == RelationshipType.INSTANTIATES
    assert edge.target_name == "MyClass"
    assert edge.confidence == 0.8  # Heuristic-based


def test_instantiation_with_args(chunk_metadata):
    """Test extraction of class instantiation with arguments."""
    code = """
obj = MyClass(arg1, arg2=value)
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "MyClass"


def test_instantiation_with_module(chunk_metadata):
    """Test extraction of class instantiation with module prefix."""
    code = """
obj = module.MyClass()
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "module.MyClass"


def test_instantiation_nested_module(chunk_metadata):
    """Test extraction of class instantiation with nested module."""
    code = """
obj = outer.inner.MyClass()
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "outer.inner.MyClass"


def test_instantiation_lowercase_skipped(chunk_metadata):
    """Test that lowercase function calls are skipped."""
    code = """
result = my_function()
data = get_data()
value = calculate_value(arg)
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # All lowercase - likely functions, not classes
    assert len(edges) == 0


def test_instantiation_all_caps_skipped(chunk_metadata):
    """Test that all-caps calls are skipped."""
    code = """
LOGGER()
CONFIG()
DATABASE()
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # All caps - likely constants, not classes
    assert len(edges) == 0


def test_instantiation_multiple(chunk_metadata):
    """Test extraction of multiple instantiations."""
    code = """
obj1 = ClassOne()
obj2 = ClassTwo()
obj3 = ClassThree()
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 3
    targets = {edge.target_name for edge in edges}
    assert targets == {"ClassOne", "ClassTwo", "ClassThree"}


def test_instantiation_inline(chunk_metadata):
    """Test extraction of inline instantiation."""
    code = """
process(MyClass())
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "MyClass"


def test_instantiation_chained(chunk_metadata):
    """Test extraction with method chaining."""
    code = """
result = MyClass().method()
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].target_name == "MyClass"


def test_instantiation_skips_common_builtins(chunk_metadata):
    """Test that common builtins are skipped."""
    code = """
from pathlib import Path
p = Path("/some/path")
"""

    extractor = InstantiationExtractor()
    edges = extractor.extract(code, chunk_metadata)

    # Path should be skipped as it's a common stdlib class
    assert len(edges) == 0


# ===== Common Tests =====


def test_extractors_handle_syntax_errors(chunk_metadata):
    """Test that extractors handle syntax errors gracefully."""
    bad_code = "def broken("

    extractors = [DecoratorExtractor(), ExceptionExtractor(), InstantiationExtractor()]

    for extractor in extractors:
        edges = extractor.extract(bad_code, chunk_metadata)
        assert (
            edges == []
        ), f"{extractor.__class__.__name__} should return empty list on syntax error"


def test_extractors_handle_empty_code(chunk_metadata):
    """Test that extractors handle empty code gracefully."""
    extractors = [DecoratorExtractor(), ExceptionExtractor(), InstantiationExtractor()]

    for extractor in extractors:
        edges = extractor.extract("", chunk_metadata)
        assert (
            edges == []
        ), f"{extractor.__class__.__name__} should return empty list on empty code"


def test_decorator_extractor_relationship_type(chunk_metadata):
    """Test DecoratorExtractor sets correct relationship type."""
    extractor = DecoratorExtractor()
    code = "@test\ndef func(): pass"
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].relationship_type == RelationshipType.DECORATES


def test_exception_extractor_relationship_types(chunk_metadata):
    """Test ExceptionExtractor sets correct relationship types."""
    extractor = ExceptionExtractor()
    code = """
try:
    raise ValueError()
except TypeError:
    pass
"""
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 2
    types = {edge.relationship_type for edge in edges}
    assert types == {RelationshipType.RAISES, RelationshipType.CATCHES}


def test_instantiation_extractor_relationship_type(chunk_metadata):
    """Test InstantiationExtractor sets correct relationship type."""
    extractor = InstantiationExtractor()
    code = "obj = MyClass()"
    edges = extractor.extract(code, chunk_metadata)

    assert len(edges) == 1
    assert edges[0].relationship_type == RelationshipType.INSTANTIATES


def test_extractors_all_have_correct_confidence(chunk_metadata):
    """Test that all extractors set confidence correctly."""
    decorator_extractor = DecoratorExtractor()
    exception_extractor = ExceptionExtractor()
    instantiation_extractor = InstantiationExtractor()

    # DecoratorExtractor should have confidence 1.0
    edges = decorator_extractor.extract("@test\ndef f(): pass", chunk_metadata)
    assert edges[0].confidence == 1.0

    # ExceptionExtractor should have confidence 1.0
    edges = exception_extractor.extract("raise ValueError()", chunk_metadata)
    assert edges[0].confidence == 1.0

    # InstantiationExtractor should have confidence 0.8 (heuristic)
    edges = instantiation_extractor.extract("obj = MyClass()", chunk_metadata)
    assert edges[0].confidence == 0.8
