"""
Unit tests for Phase 2: Type Annotation Resolution.

Tests the extraction and resolution of type annotations for method calls.
"""

import ast

from graph.call_graph_extractor import PythonCallGraphExtractor
from graph.resolvers import TypeResolver


class TestExtractTypeAnnotations:
    """Tests for TypeResolver.extract_type_annotations() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()
        self.type_resolver = TypeResolver()

    def test_extract_simple_type_annotation(self):
        """Test extraction of simple type annotation."""
        code = """
def process(extractor: ExceptionExtractor):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert "extractor" in annotations
        assert annotations["extractor"] == "ExceptionExtractor"

    def test_extract_attribute_type_annotation(self):
        """Test extraction of qualified type annotation (module.Class)."""
        code = """
def process(extractor: graph.ExceptionExtractor):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert "extractor" in annotations
        # Should return just the class name for resolution
        assert annotations["extractor"] == "ExceptionExtractor"

    def test_extract_optional_type_annotation(self):
        """Test extraction of Optional[X] annotation."""
        code = """
def process(extractor: Optional[ExceptionExtractor]):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert "extractor" in annotations
        assert annotations["extractor"] == "ExceptionExtractor"

    def test_extract_list_type_annotation(self):
        """Test extraction of List[X] annotation."""
        code = """
def process(extractors: List[ExceptionExtractor]):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert "extractors" in annotations
        assert annotations["extractors"] == "ExceptionExtractor"

    def test_extract_forward_reference_annotation(self):
        """Test extraction of forward reference string annotation."""
        code = """
def process(extractor: "ExceptionExtractor"):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert "extractor" in annotations
        assert annotations["extractor"] == "ExceptionExtractor"

    def test_extract_multiple_annotations(self):
        """Test extraction of multiple parameter annotations."""
        code = """
def process(extractor: ExceptionExtractor, handler: ErrorHandler, count: int):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert len(annotations) == 3
        assert annotations["extractor"] == "ExceptionExtractor"
        assert annotations["handler"] == "ErrorHandler"
        assert annotations["count"] == "int"

    def test_extract_kwonly_args_annotation(self):
        """Test extraction of keyword-only argument annotations."""
        code = """
def process(*, extractor: ExceptionExtractor):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert "extractor" in annotations
        assert annotations["extractor"] == "ExceptionExtractor"

    def test_extract_posonly_args_annotation(self):
        """Test extraction of positional-only argument annotations (Python 3.8+)."""
        code = """
def process(extractor: ExceptionExtractor, /):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert "extractor" in annotations
        assert annotations["extractor"] == "ExceptionExtractor"

    def test_extract_vararg_annotation(self):
        """Test extraction of *args annotation."""
        code = """
def process(*args: ExceptionExtractor):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert "args" in annotations
        assert annotations["args"] == "ExceptionExtractor"

    def test_extract_kwarg_annotation(self):
        """Test extraction of **kwargs annotation."""
        code = """
def process(**kwargs: ExceptionExtractor):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert "kwargs" in annotations
        assert annotations["kwargs"] == "ExceptionExtractor"

    def test_no_annotations_returns_empty(self):
        """Test that functions without annotations return empty dict."""
        code = """
def process(extractor, handler):
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        annotations = self.type_resolver.extract_type_annotations(func_node)

        assert annotations == {}


class TestAnnotationToString:
    """Tests for TypeResolver.annotation_to_string() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.type_resolver = TypeResolver()

    def test_annotation_to_string_name(self):
        """Test conversion of simple Name annotation."""
        code = "def f(x: MyClass): pass"
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result == "MyClass"

    def test_annotation_to_string_attribute(self):
        """Test conversion of Attribute annotation."""
        code = "def f(x: module.MyClass): pass"
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result == "MyClass"

    def test_annotation_to_string_subscript_optional(self):
        """Test conversion of Optional[X] subscript annotation."""
        code = "def f(x: Optional[MyClass]): pass"
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result == "MyClass"

    def test_annotation_to_string_subscript_list(self):
        """Test conversion of List[X] subscript annotation."""
        code = "def f(x: List[MyClass]): pass"
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result == "MyClass"

    def test_annotation_to_string_subscript_sequence(self):
        """Test conversion of Sequence[X] subscript annotation."""
        code = "def f(x: Sequence[MyClass]): pass"
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result == "MyClass"

    def test_annotation_to_string_union_with_none(self):
        """Test conversion of Union[X, None] annotation."""
        code = "def f(x: Union[MyClass, None]): pass"
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result == "MyClass"

    def test_annotation_to_string_constant(self):
        """Test conversion of string constant (forward reference)."""
        code = 'def f(x: "MyClass"): pass'
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result == "MyClass"

    def test_annotation_to_string_qualified_forward_reference(self):
        """Test conversion of qualified forward reference."""
        code = 'def f(x: "module.MyClass"): pass'
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result == "MyClass"

    def test_annotation_to_string_dict_returns_none(self):
        """Test that Dict[K, V] returns None (unresolvable)."""
        code = "def f(x: Dict[str, MyClass]): pass"
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result is None

    def test_annotation_to_string_callable_returns_none(self):
        """Test that Callable returns None (unresolvable)."""
        code = "def f(x: Callable[[int], str]): pass"
        tree = ast.parse(code)
        annotation = tree.body[0].args.args[0].annotation

        result = self.type_resolver.annotation_to_string(annotation)

        assert result is None


class TestCallResolutionWithTypeAnnotations:
    """Tests for call resolution using type annotations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_call_resolution_with_type_annotation(self):
        """Test that method calls on typed parameters are resolved."""
        code = """
def process(extractor: ExceptionExtractor):
    extractor.extract()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "ExceptionExtractor.extract"

    def test_call_resolution_with_optional_annotation(self):
        """Test resolution with Optional[X] annotation."""
        code = """
def process(extractor: Optional[ExceptionExtractor]):
    extractor.extract()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "ExceptionExtractor.extract"

    def test_call_resolution_multiple_annotated_params(self):
        """Test resolution with multiple annotated parameters."""
        code = """
def process(extractor: ExceptionExtractor, handler: ErrorHandler):
    extractor.extract()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 2
        callee_names = {call.callee_name for call in calls}
        assert "ExceptionExtractor.extract" in callee_names
        assert "ErrorHandler.handle" in callee_names

    def test_call_resolution_mixed_annotated_unannotated(self):
        """Test resolution with both annotated and unannotated parameters."""
        code = """
def process(extractor: ExceptionExtractor, handler):
    extractor.extract()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 2
        # Annotated parameter should be resolved
        annotated_call = [c for c in calls if "ExceptionExtractor" in c.callee_name][0]
        assert annotated_call.callee_name == "ExceptionExtractor.extract"
        # Unannotated parameter should fall back to bare name
        unannotated_call = [
            c for c in calls if "ExceptionExtractor" not in c.callee_name
        ][0]
        assert unannotated_call.callee_name == "handle"

    def test_call_resolution_async_function(self):
        """Test resolution works with async functions."""
        code = """
async def process(extractor: ExceptionExtractor):
    await extractor.extract()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "ExceptionExtractor.extract"

    def test_self_call_takes_priority_over_annotation(self):
        """Test that self.method() uses class context, not type annotation."""
        code = """
class MyClass:
    def process(self: MyClass):
        self.helper()

    def helper(self):
        pass
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-6:method:MyClass.process",
            "parent_class": "MyClass",
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        # Should use class context from parent_class, not from self annotation
        assert calls[0].callee_name == "MyClass.helper"

    def test_unannotated_param_falls_back_to_bare_name(self):
        """Test that unannotated parameters fall back to bare method name."""
        code = """
def process(extractor):
    extractor.extract()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "extract"

    def test_call_resolution_multiple_calls_same_param(self):
        """Test resolution of multiple calls on the same annotated parameter."""
        code = """
def process(extractor: ExceptionExtractor):
    extractor.extract()
    extractor.validate()
    extractor.finalize()
"""
        chunk_metadata = {"chunk_id": "test.py:1-5:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 3
        callee_names = [call.callee_name for call in calls]
        assert "ExceptionExtractor.extract" in callee_names
        assert "ExceptionExtractor.validate" in callee_names
        assert "ExceptionExtractor.finalize" in callee_names

    def test_call_resolution_with_list_annotation(self):
        """Test resolution with List[X] annotation."""
        code = """
def process(extractors: List[ExceptionExtractor]):
    extractors.append(None)  # This should resolve to List.append, but we extract ExceptionExtractor
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        # List[X] extracts X, so this resolves to ExceptionExtractor.append
        # This is a known limitation - container types are simplified
        assert calls[0].callee_name == "ExceptionExtractor.append"

    def test_call_resolution_chained_calls(self):
        """Test that only the first receiver is resolved."""
        code = """
def process(extractor: ExceptionExtractor):
    extractor.get_handler().handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Should have two calls: get_handler and handle
        assert len(calls) == 2
        callee_names = {call.callee_name for call in calls}
        # First call is resolved
        assert "ExceptionExtractor.get_handler" in callee_names
        # Second call (on result of first) is bare name
        assert "handle" in callee_names

    def test_call_resolution_preserves_line_numbers(self):
        """Test that line numbers are preserved in resolved calls."""
        code = """
def process(extractor: ExceptionExtractor):
    extractor.extract()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].line_number == 3

    def test_call_resolution_with_kwonly_annotation(self):
        """Test resolution with keyword-only annotated parameter."""
        code = """
def process(*, extractor: ExceptionExtractor):
    extractor.extract()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "ExceptionExtractor.extract"


class TestEdgeCases:
    """Tests for edge cases in type annotation resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_empty_function_no_calls(self):
        """Test that empty function returns no calls."""
        code = """
def process(extractor: ExceptionExtractor):
    pass
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 0

    def test_nested_function_uses_outer_annotations(self):
        """Test that nested functions use outer function's annotations."""
        code = """
def outer(extractor: ExceptionExtractor):
    def inner():
        extractor.extract()
    inner()
"""
        chunk_metadata = {"chunk_id": "test.py:1-5:function:outer"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Should find both calls: extract and inner
        assert len(calls) == 2
        callee_names = {call.callee_name for call in calls}
        assert "ExceptionExtractor.extract" in callee_names
        assert "inner" in callee_names

    def test_syntax_error_returns_empty_list(self):
        """Test that syntax errors are handled gracefully."""
        code = """
def process(extractor: ExceptionExtractor
    extractor.extract()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert calls == []

    def test_none_annotation_handled(self):
        """Test that literal None annotation falls back to bare method name.

        Annotating a parameter as None type isn't useful for method calls,
        so this correctly falls back to the bare method name.
        """
        code = """
def process(value: None):
    value.something()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        # None annotation is not useful for resolution, falls back to bare name
        assert calls[0].callee_name == "something"

    def test_builtin_type_annotation(self):
        """Test resolution with builtin type annotations."""
        code = """
def process(text: str):
    text.upper()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "str.upper"
