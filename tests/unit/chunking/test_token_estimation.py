"""
Unit tests for token estimation functionality.

Tests both whitespace and tiktoken estimation methods.
"""

import pytest

from chunking.languages.base import estimate_tokens


class TestEstimateTokens:
    """Test suite for estimate_tokens function."""

    def test_whitespace_estimation_simple(self):
        """Whitespace estimation counts space-separated words."""
        content = "hello world"
        tokens = estimate_tokens(content, method="whitespace")
        assert tokens == 2  # "hello" and "world"

    def test_whitespace_estimation_code(self):
        """Whitespace estimation works with code."""
        content = """def foo():
    return 42"""
        tokens = estimate_tokens(content, method="whitespace")
        # "def", "foo():", "return", "42"
        assert tokens == 4

    def test_whitespace_estimation_multiline(self):
        """Whitespace estimation handles multiline content."""
        content = """
        class MyClass:
            def method(self):
                pass
        """
        tokens = estimate_tokens(content, method="whitespace")
        # "class", "MyClass:", "def", "method(self):", "pass"
        assert tokens == 5

    def test_tiktoken_estimation_simple(self):
        """tiktoken estimation provides accurate token counts."""
        content = "hello world"
        tokens = estimate_tokens(content, method="tiktoken")
        # tiktoken typically gives 2 tokens for "hello world"
        assert tokens == 2

    def test_tiktoken_estimation_code(self):
        """tiktoken estimation works with code."""
        content = """def foo():
    return 42"""
        tokens = estimate_tokens(content, method="tiktoken")
        # tiktoken is more accurate for code tokens
        assert tokens > 0  # Exact count may vary

    def test_tiktoken_vs_whitespace_difference(self):
        """tiktoken and whitespace give different counts for complex content."""
        # Content with punctuation and special characters
        content = "self.config.get('key', default=None)"

        whitespace_count = estimate_tokens(content, method="whitespace")
        tiktoken_count = estimate_tokens(content, method="tiktoken")

        # Whitespace: "self.config.get('key',", "default=None)" = 2
        assert whitespace_count == 2

        # tiktoken breaks this differently (more granular)
        # "self", ".", "config", ".", "get", "('", "key", "',", "default", "=", "None", ")"
        assert tiktoken_count > whitespace_count

    def test_tiktoken_fallback_to_whitespace(self, monkeypatch):
        """tiktoken falls back to whitespace if import fails."""
        # Simulate tiktoken not being installed
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "tiktoken":
                raise ImportError("tiktoken not installed")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        content = "hello world test"
        tokens = estimate_tokens(content, method="tiktoken")
        # Should fall back to whitespace counting
        assert tokens == 3  # "hello", "world", "test"

    def test_empty_content_whitespace(self):
        """Empty content returns 0 tokens with whitespace method."""
        assert estimate_tokens("", method="whitespace") == 0

    def test_empty_content_tiktoken(self):
        """Empty content returns 0 tokens with tiktoken method."""
        assert estimate_tokens("", method="tiktoken") == 0

    def test_default_method_is_whitespace(self):
        """Default method is whitespace if not specified."""
        content = "hello world"
        # Function signature has default method="whitespace"
        tokens = estimate_tokens(content)
        assert tokens == 2

    def test_tiktoken_unicode_handling(self):
        """tiktoken handles unicode characters correctly."""
        content = "Hello 世界 🌍"
        tokens = estimate_tokens(content, method="tiktoken")
        # tiktoken handles unicode properly
        assert tokens > 0

    def test_tiktoken_long_content(self):
        """tiktoken handles longer content efficiently."""
        content = " ".join(["word"] * 1000)  # 1000 words

        whitespace_count = estimate_tokens(content, method="whitespace")
        tiktoken_count = estimate_tokens(content, method="tiktoken")

        assert whitespace_count == 1000
        assert tiktoken_count == 1000  # Same word repeated

    def test_tiktoken_code_symbols(self):
        """tiktoken handles code symbols correctly."""
        content = "x += 1; y *= 2; z //= 3"

        whitespace_count = estimate_tokens(content, method="whitespace")
        tiktoken_count = estimate_tokens(content, method="tiktoken")

        # Whitespace: "x", "+=", "1;", "y", "*=", "2;", "z", "//=", "3" = 9
        assert whitespace_count == 9

        # tiktoken breaks operators more granularly
        assert tiktoken_count >= whitespace_count


class TestTokenEstimationIntegration:
    """Integration tests showing token estimation works in real scenarios."""

    def test_tiktoken_with_real_code_sample(self):
        """Test tiktoken with realistic code sample."""
        code = """
def calculate_metrics(data: List[Dict[str, Any]]) -> Dict[str, float]:
    '''Calculate various metrics from input data.'''
    total = sum(item.get('value', 0) for item in data)
    average = total / len(data) if data else 0
    return {'total': total, 'average': average}
"""

        whitespace_count = estimate_tokens(code, method="whitespace")
        tiktoken_count = estimate_tokens(code, method="tiktoken")

        # Both methods should work and give reasonable counts
        assert whitespace_count > 0
        assert tiktoken_count > 0

        # tiktoken is more granular, so usually gives higher counts
        assert tiktoken_count >= whitespace_count

    def test_both_methods_consistent(self):
        """Both estimation methods are consistent for simple text."""
        simple_text = "hello world from python"

        # Run multiple times to ensure consistency
        for _ in range(3):
            whitespace = estimate_tokens(simple_text, method="whitespace")
            tiktoken = estimate_tokens(simple_text, method="tiktoken")

            assert whitespace == 4  # Always 4 words
            assert tiktoken == 4  # Also 4 tokens for simple text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
