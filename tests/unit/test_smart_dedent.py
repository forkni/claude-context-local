"""Unit tests for _smart_dedent function.

Tests the dedentation logic for decorated definitions and nested code.
This addresses the issue where 50+ decorated definitions fail with
"unexpected indent" errors during call graph extraction.

References:
    - Scrapy GitHub issue #4477 (flush-left docstring fix)
    - Scrapy PR #4935 (first-line baseline approach)
"""

import ast

from chunking.multi_language_chunker import _smart_dedent, _wrap_with_if_true


class TestSmartDedentBasicCases:
    """Test basic dedentation scenarios."""

    def test_already_dedented_code(self):
        """Test code that's already at column 0."""
        code = """def foo():
    return 42
"""
        result = _smart_dedent(code)
        assert "def foo():" in result
        ast.parse(result)  # Should not raise

    def test_simple_indented_function(self):
        """Test simple function with 4-space indent."""
        code = """    def foo():
        return 42
"""
        result = _smart_dedent(code)
        assert result.startswith("def foo():")
        ast.parse(result)

    def test_class_method_indentation(self):
        """Test method extracted from class (8-space indent)."""
        code = """        def method(self):
            return self.value
"""
        result = _smart_dedent(code)
        assert result.startswith("def method(self):")
        ast.parse(result)

    def test_function_with_docstring(self):
        """Test function with multi-line docstring."""
        code = """    def greet(name):
        \"\"\"Greet a person.

        Args:
            name: Person's name
        \"\"\"
        return f"Hello {name}"
"""
        result = _smart_dedent(code)
        assert result.startswith("def greet(name):")
        ast.parse(result)


class TestSmartDedentDecoratedDefinitions:
    """Test decorated definition scenarios (the main failing case)."""

    def test_classmethod_with_docstring(self):
        """Test @classmethod with multi-line docstring (CRITICAL CASE).

        This is one of the 50+ failing cases from the production logs.
        """
        code = """    @classmethod
    def instance(cls) -> "ServiceLocator":
        \"\"\"Get the singleton ServiceLocator instance.

        Returns:
            The global ServiceLocator instance, creating it if needed.
        \"\"\"
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
"""
        result = _smart_dedent(code)
        assert result.startswith("@classmethod")
        assert "def instance" in result
        ast.parse(result)  # Should not raise

    def test_property_decorator(self):
        """Test @property decorated method."""
        code = """    @property
    def value(self):
        \"\"\"Return the value.\"\"\"
        return self._value
"""
        result = _smart_dedent(code)
        assert result.startswith("@property")
        ast.parse(result)

    def test_staticmethod_decorator(self):
        """Test @staticmethod decorated method."""
        code = """    @staticmethod
    def create():
        \"\"\"Create a new instance.\"\"\"
        return MyClass()
"""
        result = _smart_dedent(code)
        assert result.startswith("@staticmethod")
        ast.parse(result)

    def test_multiple_decorators(self):
        """Test method with multiple stacked decorators."""
        code = """    @decorator1
    @decorator2("arg")
    @decorator3
    def multi_decorated(self):
        return True
"""
        result = _smart_dedent(code)
        assert result.startswith("@decorator1")
        ast.parse(result)

    def test_decorator_with_arguments(self):
        """Test decorator with complex arguments."""
        code = """    @router.get(
        "/path/{id}",
        response_model=Response
    )
    async def handler(id: int):
        return {"id": id}
"""
        result = _smart_dedent(code)
        assert result.startswith("@router.get(")
        ast.parse(result)

    def test_property_with_type_hint(self):
        """Test @property with return type annotation."""
        code = """    @property
    def index(self) -> Optional[Any]:
        \"\"\"Get the underlying FAISS index.\"\"\"
        return self._index
"""
        result = _smart_dedent(code)
        assert result.startswith("@property")
        ast.parse(result)


class TestSmartDedentEdgeCases:
    """Test edge cases that cause textwrap.dedent to fail."""

    def test_mixed_tabs_and_spaces(self):
        """Test code with mixed tabs and spaces.

        Tabs are normalized to 4 spaces by expandtabs().
        """
        # Tab followed by spaces (a common mistake)
        code = "\tdef foo():\n\t    return 42\n"
        result = _smart_dedent(code)
        ast.parse(result)

    def test_blank_lines_without_indentation(self):
        """Test code with blank lines that have no spaces."""
        code = """    def foo():
        x = 1

        y = 2
        return x + y
"""
        result = _smart_dedent(code)
        assert result.startswith("def foo():")
        ast.parse(result)

    def test_trailing_blank_lines(self):
        """Test code with trailing blank lines."""
        code = """    def foo():
        return 42


"""
        result = _smart_dedent(code)
        ast.parse(result)

    def test_leading_blank_lines(self):
        """Test code with leading blank lines."""
        code = """

    def foo():
        return 42
"""
        result = _smart_dedent(code)
        ast.parse(result)

    def test_deeply_nested_code(self):
        """Test deeply indented code (12+ spaces)."""
        code = """            def deeply_nested():
                if True:
                    for i in range(10):
                        print(i)
"""
        result = _smart_dedent(code)
        assert result.startswith("def deeply_nested():")
        ast.parse(result)

    def test_only_whitespace_lines(self):
        """Test code where some lines are only whitespace."""
        code = """    def foo():
        x = 1

        y = 2
        return x + y
"""
        result = _smart_dedent(code)
        ast.parse(result)


class TestSmartDedentMultiLineStrings:
    """Test handling of multi-line strings."""

    def test_triple_quoted_string_in_function(self):
        """Test function with triple-quoted string."""
        code = """    def template():
        return \"\"\"
Hello,
World!
\"\"\"
"""
        result = _smart_dedent(code)
        ast.parse(result)

    def test_f_string_multiline(self):
        """Test f-string spanning multiple lines."""
        code = """    def greet(name):
        return f\"\"\"
Hello {name}!
Welcome.
\"\"\"
"""
        result = _smart_dedent(code)
        ast.parse(result)

    def test_docstring_with_code_examples(self):
        """Test docstring containing code examples."""
        code = """    def example():
        \"\"\"Example function.

        Example:
            >>> example()
            42
        \"\"\"
        return 42
"""
        result = _smart_dedent(code)
        ast.parse(result)


class TestSmartDedentRealWorldExamples:
    """Test real-world code patterns from the codebase."""

    def test_service_locator_instance(self):
        """Test actual ServiceLocator.instance method structure.

        This exact pattern fails in production (mcp_server/services.py:51-60).
        """
        code = """    @classmethod
    def instance(cls) -> "ServiceLocator":
        \"\"\"Get the singleton ServiceLocator instance.

        Returns:
            The global ServiceLocator instance, creating it if needed.
        \"\"\"
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
"""
        result = _smart_dedent(code)
        assert "@classmethod" in result
        assert "def instance" in result
        # Critical: Must parse without SyntaxError
        ast.parse(result)

    def test_faiss_index_property(self):
        """Test actual FAISS index property structure.

        This exact pattern fails in production (search/faiss_index.py:134-137).
        """
        code = """    @property
    def index(self) -> Optional[Any]:
        \"\"\"Get the underlying FAISS index.\"\"\"
        return self._index
"""
        result = _smart_dedent(code)
        assert "@property" in result
        ast.parse(result)

    def test_hybrid_searcher_is_ready(self):
        """Test complex property with conditionals.

        Pattern from search/hybrid_searcher.py:253-271.
        """
        code = """    @property
    def is_ready(self) -> bool:
        \"\"\"Check if the searcher is ready for queries.

        Returns:
            True if both BM25 and FAISS indices exist and are ready.
        \"\"\"
        if self._bm25_index is None or self._faiss_index is None:
            return False
        return not self._bm25_index.is_empty and self._faiss_index.ntotal > 0
"""
        result = _smart_dedent(code)
        assert "@property" in result
        ast.parse(result)

    def test_relationship_extractor_extract(self):
        """Test decorated definition with abstract method.

        Pattern from graph/relationship_extractors/base_extractor.py:44-78.
        """
        code = """    @abstractmethod
    def extract(
        self, code: str, chunk_metadata: Dict[str, Any]
    ) -> List[RelationshipEdge]:
        \"\"\"Extract relationships from code.

        Args:
            code: Source code to analyze
            chunk_metadata: Metadata about the code chunk

        Returns:
            List of extracted relationship edges
        \"\"\"
        pass
"""
        result = _smart_dedent(code)
        assert "@abstractmethod" in result
        ast.parse(result)


class TestSmartDedentFailureRecovery:
    """Test graceful failure handling."""

    def test_invalid_syntax_returns_something(self):
        """Test that invalid syntax returns something (not crash)."""
        code = """    def broken(
        return None  # Missing closing paren
"""
        result = _smart_dedent(code)
        # Should return something (either original or wrapped attempt)
        assert len(result) > 0
        # Note: We don't assert it parses, as the original is invalid

    def test_empty_string(self):
        """Test empty string input."""
        assert _smart_dedent("") == ""

    def test_whitespace_only(self):
        """Test whitespace-only input."""
        result = _smart_dedent("   \n   \n   ")
        # Should return original since no actual code
        assert result == "   \n   \n   "


class TestSmartDedentCRLF:
    """Test CRLF line ending handling (Windows files)."""

    def test_crlf_line_endings(self):
        """Test code with Windows CRLF line endings."""
        code = "    def foo():\r\n        return 42\r\n"
        result = _smart_dedent(code)
        assert result.startswith("def foo():")
        ast.parse(result)

    def test_mixed_line_endings(self):
        """Test code with mixed LF and CRLF."""
        code = "    def foo():\n        x = 1\r\n        return x\n"
        result = _smart_dedent(code)
        ast.parse(result)

    def test_cr_only_line_endings(self):
        """Test code with old Mac CR-only endings."""
        code = "    def foo():\r        return 42\r"
        result = _smart_dedent(code)
        ast.parse(result)

    def test_decorated_with_crlf(self):
        """Test decorated definition with CRLF (critical production case)."""
        code = "    @classmethod\r\n    def instance(cls):\r\n        return cls()\r\n"
        result = _smart_dedent(code)
        assert result.startswith("@classmethod")
        ast.parse(result)

    def test_multiline_decorator_with_crlf(self):
        """Test multi-line decorator with CRLF."""
        code = '    @deprecated(\r\n        version="1.0"\r\n    )\r\n    def old_func():\r\n        pass\r\n'
        result = _smart_dedent(code)
        assert result.startswith("@deprecated(")
        ast.parse(result)

    def test_property_with_crlf_docstring(self):
        """Test property with CRLF in docstring."""
        code = '    @property\r\n    def value(self):\r\n        """Get value."""\r\n        return self._value\r\n'
        result = _smart_dedent(code)
        assert result.startswith("@property")
        ast.parse(result)


class TestWrapWithIfTrue:
    """Test the _wrap_with_if_true helper function."""

    def test_wrap_simple_code(self):
        """Test wrapping simple code with if True."""
        code = """def foo():
    return 42
"""
        result = _wrap_with_if_true(code)
        assert result.startswith("if True:")
        assert "    def foo():" in result
        ast.parse(result)

    def test_wrap_decorated_definition(self):
        """Test wrapping decorated definition."""
        code = """@property
def value(self):
    return self._value
"""
        result = _wrap_with_if_true(code)
        assert result.startswith("if True:")
        ast.parse(result)

    def test_wrap_preserves_blank_lines(self):
        """Test that wrapping preserves blank lines correctly."""
        code = """def foo():
    x = 1

    y = 2
    return x + y
"""
        result = _wrap_with_if_true(code)
        ast.parse(result)
        # Check that blank lines are preserved as empty (not indented)
        assert "\n\n" in result


class TestSmartDedentDecoratorAtColumn0:
    """Test tree-sitter extracted decorated definitions (decorator at column 0)."""

    def test_decorator_at_column0_with_indented_def(self):
        """Test the exact pattern tree-sitter produces for decorated methods.

        This is the CRITICAL CASE that was failing in production.
        Tree-sitter extracts:
        - Decorator at column 0
        - Function def still indented
        """
        code = "@abstractmethod\n    def _get_splittable_node_types(self) -> Set[str]:\n        pass\n"
        result = _smart_dedent(code)
        assert result.startswith("@abstractmethod")
        assert "\ndef " in result or result.startswith("@abstractmethod\ndef")
        ast.parse(result)

    def test_property_at_column0(self):
        """Test @property with def indented (tree-sitter pattern)."""
        code = "@property\n    def value(self):\n        return self._value\n"
        result = _smart_dedent(code)
        ast.parse(result)

    def test_classmethod_at_column0_with_docstring(self):
        """Test @classmethod with indented def and docstring."""
        code = '@classmethod\n    def instance(cls) -> "ServiceLocator":\n        """Get the singleton."""\n        return cls._instance\n'
        result = _smart_dedent(code)
        ast.parse(result)

    def test_multiple_decorators_at_column0(self):
        """Test stacked decorators all at column 0 with indented def."""
        code = "@decorator1\n@decorator2\n    def method(self):\n        pass\n"
        result = _smart_dedent(code)
        ast.parse(result)


class TestSmartDedentIntegration:
    """Integration tests with ast.parse to verify end-to-end functionality."""

    def test_all_decorated_types_parse(self):
        """Test that all common decorator types parse correctly."""
        decorators = [
            "@property",
            "@classmethod",
            "@staticmethod",
            "@abstractmethod",
            "@dataclass",
            "@lru_cache",
            "@pytest.fixture",
        ]

        for decorator in decorators:
            code = f"""    {decorator}
    def method(self):
        return True
"""
            result = _smart_dedent(code)
            # Should not raise SyntaxError
            ast.parse(result)

    def test_nested_decorators_with_arguments(self):
        """Test complex nested decorators with arguments."""
        code = """    @app.route("/api/search", methods=["GET", "POST"])
    @require_auth
    @rate_limit(calls=100, period=60)
    async def search_endpoint(request):
        \"\"\"Handle search requests.\"\"\"
        return await process_search(request)
"""
        result = _smart_dedent(code)
        ast.parse(result)

    def test_class_with_decorated_methods(self):
        """Test multiple decorated methods (as they appear in extraction)."""
        # Note: Individual methods are extracted, not the whole class
        # But we test the pattern to ensure consistency
        methods = [
            """    @property
    def index(self):
        return self._index
""",
            """    @classmethod
    def create(cls):
        return cls()
""",
            """    @staticmethod
    def validate(data):
        return bool(data)
""",
        ]

        for method in methods:
            result = _smart_dedent(method)
            ast.parse(result)
