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
        assert method_chunk.parent_chunk_id is not None, (
            "Method should have parent_chunk_id"
        )
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
        assert func_chunk.parent_chunk_id is None, (
            "Standalone function should have no parent_chunk_id"
        )
        assert func_chunk.parent_name is None, (
            "Standalone function should have no parent_name"
        )

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

        # With this method body length, greedy merge should NOT absorb the methods
        # into the class chunk — verify the precondition before checking parent_chunk_id.
        assert method_chunks, (
            "No method chunks found — greedy merge absorbed both methods into "
            "the class chunk; test no longer exercises parent_chunk_id generation"
        )
        for method in method_chunks:
            assert method.parent_chunk_id == class_chunk.chunk_id, (
                f"Method {method.name} should point to class chunk_id"
            )
            assert method.parent_name == "MyClass", (
                f"Method {method.name} should have parent_name=MyClass"
            )

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
        assert outer_method.parent_chunk_id == outer_class.chunk_id, (
            "Outer method should point to outer class"
        )

        # Nested classes are fully supported by the chunker — verify the
        # precondition before checking the inner method's parent_chunk_id.
        assert inner_class is not None and inner_method is not None, (
            "Inner class or inner method chunk missing — test no longer "
            "exercises the nested-class parent_chunk_id path"
        )
        assert inner_method.parent_chunk_id == inner_class.chunk_id, (
            "Inner method should point to inner class"
        )

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
        assert class_chunk.parent_chunk_id is None, (
            "Class should have no parent_chunk_id"
        )

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

    def test_decorated_method_has_parent_chunk_id(self, chunker, tmp_path):
        """Test that a decorated method (chunk_type="decorated_definition")
        gets a parent_chunk_id, same as a plain method."""
        test_file = tmp_path / "deco_method.py"
        test_file.write_text(
            '''
class Plain:
    """A plain (undecorated) class."""

    @property
    def prop_meth(self):
        """Decorated method with a substantial body."""
        result = []
        for i in range(10):
            result.append(i * 2)
        return sum(result)
'''
        )
        chunks = chunker.chunk_file(str(test_file))

        class_chunk = next((c for c in chunks if c.chunk_type == "class"), None)
        deco = next((c for c in chunks if c.name == "prop_meth"), None)

        assert class_chunk is not None, "Class chunk should exist"
        assert deco is not None, "Decorated method chunk should exist"
        # Precondition: the decorator is what makes this chunk_type, not
        # "method" -- without this assertion the test would silently degrade
        # into a duplicate of test_method_has_parent_chunk_id if NODE_TYPE_MAP
        # ever gained a "decorated_definition" key.
        assert deco.chunk_type == "decorated_definition", (
            "chunk kind changed -- this test no longer exercises the widened gate"
        )
        assert deco.parent_name == "Plain"
        assert deco.parent_chunk_id == class_chunk.chunk_id

    def test_module_level_decorated_function_no_parent_id(self, chunker, tmp_path):
        """Test that a module-level decorated function stays unparented --
        the parent_name conjunct must still gate the widened arm."""
        test_file = tmp_path / "deco_func.py"
        test_file.write_text(
            '''
import functools


@functools.cache
def cached_helper(value):
    """Module-level decorated function with a substantial body."""
    result = []
    for i in range(10):
        result.append(i * value)
    return sum(result)
'''
        )
        chunks = chunker.chunk_file(str(test_file))

        fn = next((c for c in chunks if c.name == "cached_helper"), None)
        assert fn is not None, "Decorated function chunk should exist"
        assert fn.chunk_type == "decorated_definition"
        assert fn.parent_name is None, (
            "Module-level decorated function should have no parent_name"
        )
        assert fn.parent_chunk_id is None, (
            "Widening the gate must not parent module-level decorated functions"
        )

    def test_multi_decorator_and_async_methods_share_parent(self, chunker, tmp_path):
        """Test that stacked decorators, an async decorated method, and a
        plain sibling method all resolve to the same class parent_chunk_id --
        guards against the widened arm and the pre-existing "method" arm
        diverging."""
        test_file = tmp_path / "deco_variants.py"
        test_file.write_text(
            '''
import functools


class Service:
    """Host class."""

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def stacked(value):
        """Two stacked decorators, substantial body."""
        data = {"a": 1, "b": 2, "c": 3}
        total = sum(data.values())
        return total * value

    @functools.wraps(print)
    async def async_deco(self, payload):
        """Async decorated method, substantial body."""
        result = []
        for item in payload:
            result.append(item)
        return result

    def plain(self):
        """Undecorated control, substantial body."""
        acc = 0
        for i in range(10):
            acc += i
        return acc
'''
        )
        chunks = chunker.chunk_file(str(test_file))

        cls = next(c for c in chunks if c.chunk_type == "class" and c.name == "Service")
        stacked = next(c for c in chunks if c.name == "stacked")
        async_deco = next(c for c in chunks if c.name == "async_deco")
        plain = next(c for c in chunks if c.name == "plain")

        assert stacked.chunk_type == "decorated_definition"
        assert async_deco.chunk_type == "decorated_definition"
        assert plain.chunk_type == "method"  # control: pre-existing arm
        assert len(stacked.decorators) == 2, "both decorators recorded on the chunk"

        for member in (stacked, async_deco, plain):
            assert member.parent_name == "Service"
            assert member.parent_chunk_id == cls.chunk_id

    def test_decorated_method_in_nested_class(self, chunker, tmp_path):
        """Test that a decorated method on a nested class resolves to the
        innermost enclosing class, exercising _resolve_parent_chunk_id's
        innermost-span selection on the new code path."""
        test_file = tmp_path / "nested_deco.py"
        test_file.write_text(
            '''
class Outer:
    """Outer."""

    class Inner:
        """Inner."""

        @property
        def value(self):
            """Decorated method on the inner class."""
            acc = 0
            for i in range(10):
                acc += i
            return acc

    def outer_method(self):
        """Undecorated outer method."""
        return 1
'''
        )
        chunks = chunker.chunk_file(str(test_file))

        inner = next(c for c in chunks if c.chunk_type == "class" and c.name == "Inner")
        value = next(c for c in chunks if c.name == "value")

        assert value.chunk_type == "decorated_definition"
        assert value.parent_chunk_id == inner.chunk_id, (
            "must resolve to the innermost enclosing class, not the outer one"
        )

    def test_decorated_method_chunk_id_unchanged_shape(self, chunker, tmp_path):
        """Test that chunk_id keeps its "decorated_definition" kind segment --
        golden datasets reference decorated methods by this exact kind (see
        e.g. golden_dataset_expanded.json's
        "...:decorated_definition:MultiLanguageChunker._classify_file_role"),
        so remapping the kind would break golden-dataset references."""
        test_file = tmp_path / "deco_id.py"
        test_file.write_text(
            '''
class Holder:
    """Holder."""

    @property
    def thing(self):
        """Decorated method."""
        acc = 0
        for i in range(10):
            acc += i
        return acc
'''
        )
        chunks = chunker.chunk_file(str(test_file))
        deco = next(c for c in chunks if c.name == "thing")

        parts = deco.chunk_id.split(":")
        assert len(parts) == 4
        assert parts[2] == "decorated_definition", (
            "kind segment must stay 'decorated_definition' -- golden-dataset "
            "IDs reference decorated methods by this exact kind"
        )
        assert parts[3] == "Holder.thing"

    def test_split_blocks_of_large_decorated_method_stay_unparented(
        self, chunker, tmp_path
    ):
        """Scope pin: the gate widening covers decorated_definition, not the
        split_block fragments a large decorated method is split into.

        _create_split_chunk (chunking/languages/base.py) hardcodes
        node_type="split_block" while still setting parent_class from
        parent_info, so only the chunk-type gate keeps these out.
        """
        loop = "\n".join(
            f"        for kkkkkkkkkkkkkkkk{i} in range(1000000):\n"
            f"            total_aaaaaaaaaaaaaaaaaaaa += kkkkkkkkkkkkkkkk{i} * {i} "
            f"+ helper_bbbbbbbbbbbbbbbbbb({i})"
            for i in range(1, 90)
        )
        test_file = tmp_path / "big_deco.py"
        test_file.write_text(
            f'''
class Host:
    """Host."""

    @measure
    def big_deco_method(self):
        """Large decorated method that exceeds the split threshold."""
        total_aaaaaaaaaaaaaaaaaaaa = 0
{loop}
        return total_aaaaaaaaaaaaaaaaaaaa
'''
        )
        chunks = chunker.chunk_file(str(test_file))

        fragments = [c for c in chunks if c.chunk_type == "split_block"]
        assert len(fragments) > 1, (
            "large-node splitting did not fire -- test no longer exercises split_block"
        )
        for frag in fragments:
            assert frag.parent_name == "Host", "split fragments do carry parent_name"
            assert frag.parent_chunk_id is None, (
                "split_block fragments are deliberately out of scope for the "
                "decorated_definition gate widening"
            )

    def test_decorated_class_parenting_is_container_scoped(self, chunker, tmp_path):
        """Characterization: decorated_definition is shape-agnostic (it wraps
        a decorated *class* as readily as a decorated method), so widening
        the gate parents a nested decorated class too -- while a nested
        *plain* class still gets None, because chunk_type == "class" is not
        in the gate.

        Asymmetry is deliberate and currently unpopulated (0 nested decorated
        classes in this repo). Making decorated classes containers, and
        widening the class-registration gate, are tracked separately (see
        docs/adr/0038-cpp-only-container-traversal-seam.md). If that lands,
        revisit this test rather than deleting it.
        """
        test_file = tmp_path / "deco_classes.py"
        test_file.write_text(
            '''
from dataclasses import dataclass


@dataclass
class ModuleLevel:
    """Decorated class at module level."""
    x: int = 0


class Owner:
    """Owner."""

    @dataclass
    class NestedDecorated:
        """Decorated class nested in a plain class."""
        y: int = 0

    class NestedPlain:
        """Undecorated class nested in a plain class."""
        z: int = 0
'''
        )
        chunks = chunker.chunk_file(str(test_file))

        owner = next(c for c in chunks if c.chunk_type == "class" and c.name == "Owner")
        module_level = next(c for c in chunks if c.name == "ModuleLevel")
        nested_deco = next(c for c in chunks if c.name == "NestedDecorated")
        nested_plain = next(c for c in chunks if c.name == "NestedPlain")

        # A decorated class is emitted as "decorated_definition", not "class".
        assert module_level.chunk_type == "decorated_definition"
        assert nested_deco.chunk_type == "decorated_definition"
        assert nested_plain.chunk_type == "class"

        # Module level: no container, unchanged.
        assert module_level.parent_chunk_id is None

        # Nested: decorated gets an edge, plain does not (the known asymmetry).
        assert nested_deco.parent_chunk_id == owner.chunk_id
        assert nested_plain.parent_chunk_id is None
