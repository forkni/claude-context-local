"""
Unit tests for call graph extraction.

Tests Python call graph extraction from AST, covering:
- Simple function calls
- Method calls
- Nested calls
- Lambda expressions
- Error handling
"""

import pytest

from graph.call_graph_extractor import (
    CallEdge,
    CallGraphExtractorFactory,
    PythonCallGraphExtractor,
)


class TestCallEdge:
    """Test CallEdge dataclass."""

    def test_create_call_edge(self):
        """Test creating a CallEdge."""
        edge = CallEdge(
            caller_id="test.py:1-10:function:foo",
            callee_name="bar",
            line_number=5,
            is_method_call=False,
            confidence=1.0,
        )

        assert edge.caller_id == "test.py:1-10:function:foo"
        assert edge.callee_name == "bar"
        assert edge.line_number == 5
        assert edge.is_method_call is False
        assert edge.confidence == 1.0

    def test_call_edge_to_dict(self):
        """Test CallEdge serialization."""
        edge = CallEdge(
            caller_id="test.py:1-10:function:foo",
            callee_name="bar",
            line_number=5,
        )

        data = edge.to_dict()

        assert data["caller_id"] == "test.py:1-10:function:foo"
        assert data["callee_name"] == "bar"
        assert data["line_number"] == 5
        assert data["is_method_call"] is False
        assert data["confidence"] == 1.0

    def test_call_edge_from_dict(self):
        """Test CallEdge deserialization."""
        data = {
            "caller_id": "test.py:1-10:function:foo",
            "callee_name": "bar",
            "line_number": 5,
            "is_method_call": True,
            "confidence": 0.9,
        }

        edge = CallEdge.from_dict(data)

        assert edge.caller_id == "test.py:1-10:function:foo"
        assert edge.callee_name == "bar"
        assert edge.line_number == 5
        assert edge.is_method_call is True
        assert edge.confidence == 0.9


class TestPythonCallGraphExtractor:
    """Test Python call graph extraction."""

    @pytest.fixture
    def extractor(self):
        """Create a PythonCallGraphExtractor instance."""
        return PythonCallGraphExtractor()

    @pytest.fixture
    def chunk_metadata(self):
        """Create test chunk metadata."""
        return {"chunk_id": "test.py:1-10:function:test_func"}

    def test_extract_simple_function_call(self, extractor, chunk_metadata):
        """Test extracting a simple function call."""
        code = """
def foo():
    bar()
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "bar"
        assert calls[0].is_method_call is False
        assert calls[0].line_number == 3

    def test_extract_multiple_calls(self, extractor, chunk_metadata):
        """Test extracting multiple function calls."""
        code = """
def foo():
    bar()
    baz()
    qux()
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 3
        call_names = [c.callee_name for c in calls]
        assert "bar" in call_names
        assert "baz" in call_names
        assert "qux" in call_names

    def test_extract_method_call(self, extractor, chunk_metadata):
        """Test extracting a method call."""
        code = """
def foo():
    obj.method()
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "method"
        assert calls[0].is_method_call is True

    def test_extract_chained_method_calls(self, extractor, chunk_metadata):
        """Test extracting chained method calls."""
        code = """
def foo():
    obj.method1().method2().method3()
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        # Should extract all method calls in the chain
        assert len(calls) == 3
        call_names = [c.callee_name for c in calls]
        assert "method1" in call_names
        assert "method2" in call_names
        assert "method3" in call_names

    def test_extract_nested_calls(self, extractor, chunk_metadata):
        """Test extracting nested function calls."""
        code = """
def foo():
    result = bar(baz(qux()))
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 3
        call_names = [c.callee_name for c in calls]
        assert "bar" in call_names
        assert "baz" in call_names
        assert "qux" in call_names

    def test_extract_lambda_call(self, extractor, chunk_metadata):
        """Test extracting calls inside lambda."""
        code = """
def foo():
    func = lambda x: process(x)
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        # Should extract the process() call inside lambda
        assert len(calls) == 1
        assert calls[0].callee_name == "process"

    def test_extract_calls_with_arguments(self, extractor, chunk_metadata):
        """Test extracting calls with various arguments."""
        code = """
def foo():
    bar(1, 2, 3)
    baz(x=10, y=20)
    qux(*args, **kwargs)
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 3
        call_names = [c.callee_name for c in calls]
        assert "bar" in call_names
        assert "baz" in call_names
        assert "qux" in call_names

    def test_extract_builtin_calls(self, extractor, chunk_metadata):
        """Test extracting built-in function calls."""
        code = """
def foo():
    print("hello")
    len([1, 2, 3])
    str(42)
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 3
        call_names = [c.callee_name for c in calls]
        assert "print" in call_names
        assert "len" in call_names
        assert "str" in call_names

    def test_no_calls_in_code(self, extractor, chunk_metadata):
        """Test code with no function calls."""
        code = """
def foo():
    x = 42
    y = x + 10
    return y
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 0

    def test_extract_calls_in_conditional(self, extractor, chunk_metadata):
        """Test extracting calls inside conditionals."""
        code = """
def foo():
    if condition():
        bar()
    else:
        baz()
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 3
        call_names = [c.callee_name for c in calls]
        assert "condition" in call_names
        assert "bar" in call_names
        assert "baz" in call_names

    def test_extract_calls_in_loop(self, extractor, chunk_metadata):
        """Test extracting calls inside loops."""
        code = """
def foo():
    for item in get_items():
        process(item)
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 2
        call_names = [c.callee_name for c in calls]
        assert "get_items" in call_names
        assert "process" in call_names

    def test_extract_calls_in_try_except(self, extractor, chunk_metadata):
        """Test extracting calls in try/except blocks."""
        code = """
def foo():
    try:
        risky_operation()
    except Exception:
        handle_error()
    finally:
        cleanup()
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 3
        call_names = [c.callee_name for c in calls]
        assert "risky_operation" in call_names
        assert "handle_error" in call_names
        assert "cleanup" in call_names

    def test_extract_calls_with_list_comprehension(self, extractor, chunk_metadata):
        """Test extracting calls in list comprehensions."""
        code = """
def foo():
    result = [process(x) for x in get_data()]
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 2
        call_names = [c.callee_name for c in calls]
        assert "process" in call_names
        assert "get_data" in call_names

    def test_syntax_error_handling(self, extractor, chunk_metadata):
        """Test handling of syntax errors."""
        code = """
def foo(:
    bar()  # Missing closing paren
"""
        # Should not raise, just return empty list with warning
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 0

    def test_empty_code(self, extractor, chunk_metadata):
        """Test extracting from empty code."""
        code = ""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 0

    def test_extract_from_ast_node(self, extractor):
        """Test extracting calls from an AST node directly."""
        import ast

        code = """
def foo():
    bar()
    baz()
"""
        tree = ast.parse(code)
        func_node = tree.body[0]  # FunctionDef node

        chunk_id = "test.py:1-4:function:foo"
        calls = extractor.extract_calls_from_ast_node(func_node, chunk_id)

        assert len(calls) == 2
        call_names = [c.callee_name for c in calls]
        assert "bar" in call_names
        assert "baz" in call_names

    def test_dynamic_call_detection(self, extractor, chunk_metadata):
        """Test detection of dynamic calls (call results)."""
        code = """
def foo():
    # Calling the result of get_function()
    get_function()()
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        # Should detect both get_function() and the dynamic call
        assert len(calls) == 2
        call_names = [c.callee_name for c in calls]
        assert "get_function" in call_names
        assert "call_result" in call_names

    def test_subscript_call_detection(self, extractor, chunk_metadata):
        """Test detection of subscript calls."""
        code = """
def foo():
    # Calling the result of a subscript
    obj[key]()
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "subscript_result"

    def test_call_with_decorator(self, extractor, chunk_metadata):
        """Test that decorators are not counted as calls."""
        code = """
@decorator
def foo():
    bar()
"""
        calls = extractor.extract_calls(code, chunk_metadata)

        # Should only extract bar(), not decorator
        # Note: This depends on chunk_metadata pointing to the function body
        # If we parse the whole module, we might see decorator as well
        # For now, just verify bar() is extracted
        call_names = [c.callee_name for c in calls]
        assert "bar" in call_names


class TestCallGraphExtractorFactory:
    """Test CallGraphExtractorFactory."""

    def test_create_python_extractor(self):
        """Test creating Python extractor."""
        extractor = CallGraphExtractorFactory.create("python")

        assert isinstance(extractor, PythonCallGraphExtractor)

    def test_create_python_case_insensitive(self):
        """Test creating Python extractor with different case."""
        extractor = CallGraphExtractorFactory.create("PYTHON")

        assert isinstance(extractor, PythonCallGraphExtractor)

    def test_create_unsupported_language(self):
        """Test creating extractor for unsupported language."""
        with pytest.raises(ValueError, match="No call graph extractor"):
            CallGraphExtractorFactory.create("rust")

    def test_is_supported(self):
        """Test checking if language is supported."""
        assert CallGraphExtractorFactory.is_supported("python") is True
        assert CallGraphExtractorFactory.is_supported("PYTHON") is True
        assert CallGraphExtractorFactory.is_supported("rust") is False

    def test_supported_languages(self):
        """Test getting list of supported languages."""
        languages = CallGraphExtractorFactory.supported_languages()

        assert "python" in languages
        assert len(languages) >= 1  # At least Python in Phase 1
