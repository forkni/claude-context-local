"""Unit tests for MCP tool handler decorators."""

from unittest.mock import patch

import pytest

from mcp_server.tools.decorators import error_handler


class TestErrorHandlerDecorator:
    """Test @error_handler decorator for MCP handlers."""

    @pytest.fixture(autouse=True)
    def setup_logger_mock(self):
        """Mock logger for each test."""
        with patch("mcp_server.tools.decorators.logger") as mock_logger:
            self.mock_logger = mock_logger
            yield

    @pytest.mark.asyncio
    async def test_successful_handler_returns_result(self):
        """Test that decorator passes through successful handler results."""

        @error_handler("Test Action")
        async def successful_handler(arguments: dict) -> dict:
            return {"status": "success", "data": arguments.get("value")}

        result = await successful_handler({"value": 42})

        assert result == {"status": "success", "data": 42}
        # Should not log errors on success
        self.mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_successful_handler_with_complex_return(self):
        """Test decorator with complex return values."""

        @error_handler("Complex Action")
        async def complex_handler(arguments: dict) -> dict:
            return {
                "results": [1, 2, 3],
                "metadata": {"count": 3, "total_time": 1.5},
                "nested": {"deep": {"value": "test"}},
            }

        result = await complex_handler({})

        assert result["results"] == [1, 2, 3]
        assert result["metadata"]["count"] == 3
        assert result["nested"]["deep"]["value"] == "test"

    @pytest.mark.asyncio
    async def test_exception_returns_error_dict(self):
        """Test that exceptions are converted to error response dicts."""

        @error_handler("Failing Action")
        async def failing_handler(arguments: dict) -> dict:
            raise ValueError("Something went wrong")

        result = await failing_handler({})

        assert "error" in result
        assert result["error"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_exception_logs_with_exc_info(self):
        """Test that exceptions are logged with exc_info=True."""

        @error_handler("Failing Action")
        async def failing_handler(arguments: dict) -> dict:
            raise RuntimeError("Critical failure")

        await failing_handler({"param": "value"})

        # Verify error was logged with traceback
        self.mock_logger.error.assert_called_once()
        call_args = self.mock_logger.error.call_args
        assert "Failing Action failed: Critical failure" in call_args[0][0]
        assert call_args[1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_error_context_enrichment(self):
        """Test that error responses can be enriched with context."""

        def get_context(arguments: dict) -> dict:
            return {
                "available_options": ["opt1", "opt2", "opt3"],
                "provided_value": arguments.get("value"),
            }

        @error_handler("Action With Context", error_context=get_context)
        async def handler_with_context(arguments: dict) -> dict:
            raise ValueError("Invalid option")

        result = await handler_with_context({"value": "invalid"})

        # Error response should contain both error and context
        assert result["error"] == "Invalid option"
        assert result["available_options"] == ["opt1", "opt2", "opt3"]
        assert result["provided_value"] == "invalid"

    @pytest.mark.asyncio
    async def test_error_context_enrichment_with_no_context(self):
        """Test that None/empty context is handled gracefully."""

        def empty_context(arguments: dict) -> dict:
            return {}

        @error_handler("Action With Empty Context", error_context=empty_context)
        async def handler_with_empty_context(arguments: dict) -> dict:
            raise ValueError("Test error")

        result = await handler_with_empty_context({})

        # Should only have error field, no extra context
        assert result == {"error": "Test error"}

    @pytest.mark.asyncio
    async def test_error_context_callback_failure_is_failsafe(self):
        """Test that error context callback failure doesn't break error handling."""

        def failing_context(arguments: dict) -> dict:
            raise RuntimeError("Context enrichment failed")

        @error_handler("Action With Failing Context", error_context=failing_context)
        async def handler_with_failing_context(arguments: dict) -> dict:
            raise ValueError("Original error")

        result = await handler_with_failing_context({})

        # Should still return error response with original error
        assert result["error"] == "Original error"
        # Should not have any context fields
        assert len(result) == 1

        # Should log warning about context enrichment failure
        self.mock_logger.warning.assert_called_once()
        warning_call = self.mock_logger.warning.call_args
        assert "Failed to enrich error context" in warning_call[0][0]
        assert warning_call[1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_different_exception_types(self):
        """Test that different exception types are handled correctly."""
        test_cases = [
            (ValueError, "Value error message", "Value error message"),
            (KeyError, "missing_key", "'missing_key'"),  # KeyError adds quotes
            (TypeError, "Type error message", "Type error message"),
            (RuntimeError, "Runtime error message", "Runtime error message"),
            (Exception, "Generic exception", "Generic exception"),
        ]

        for exc_class, message, expected_error in test_cases:
            # Bind loop variables to avoid closure issues (B023)
            @error_handler("Test Action")
            async def handler(arguments: dict, _exc=exc_class, _msg=message) -> dict:
                raise _exc(_msg)

            result = await handler({})
            assert result["error"] == expected_error

    @pytest.mark.asyncio
    async def test_action_name_in_log_message(self):
        """Test that action_name appears in log messages."""

        @error_handler("Custom Action Name")
        async def handler(arguments: dict) -> dict:
            raise ValueError("Test error")

        await handler({})

        # Verify action name is in log message
        log_call = self.mock_logger.error.call_args[0][0]
        assert "Custom Action Name failed" in log_call

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test that @functools.wraps preserves function metadata."""

        @error_handler("Test")
        async def documented_handler(arguments: dict) -> dict:
            """This is a documented handler."""
            return {"result": "success"}

        # Function name and docstring should be preserved
        assert documented_handler.__name__ == "documented_handler"
        assert documented_handler.__doc__ == "This is a documented handler."

    @pytest.mark.asyncio
    async def test_multiple_handlers_independent(self):
        """Test that multiple decorated handlers are independent."""

        @error_handler("Handler 1")
        async def handler1(arguments: dict) -> dict:
            return {"handler": 1}

        @error_handler("Handler 2")
        async def handler2(arguments: dict) -> dict:
            return {"handler": 2}

        result1 = await handler1({})
        result2 = await handler2({})

        assert result1["handler"] == 1
        assert result2["handler"] == 2

    @pytest.mark.asyncio
    async def test_arguments_passed_to_context_callback(self):
        """Test that handler arguments are passed to context callback."""
        captured_args = {}

        def capture_args_context(arguments: dict) -> dict:
            captured_args.update(arguments)
            return {"captured": True}

        @error_handler("Test", error_context=capture_args_context)
        async def handler(arguments: dict) -> dict:
            raise ValueError("Test")

        await handler({"key1": "value1", "key2": 42})

        # Context callback should have received the arguments
        assert captured_args["key1"] == "value1"
        assert captured_args["key2"] == 42

    @pytest.mark.asyncio
    async def test_error_response_format_consistency(self):
        """Test that error responses have consistent format across scenarios."""

        @error_handler("Action 1")
        async def handler1(arguments: dict) -> dict:
            raise ValueError("Error 1")

        @error_handler("Action 2", error_context=lambda args: {"extra": "field"})
        async def handler2(arguments: dict) -> dict:
            raise ValueError("Error 2")

        result1 = await handler1({})
        result2 = await handler2({})

        # Both should be dicts with "error" key
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        assert "error" in result1
        assert "error" in result2


class TestErrorHandlerIntegration:
    """Integration tests for error_handler with realistic use cases."""

    @pytest.mark.asyncio
    async def test_search_handler_pattern(self):
        """Test decorator with search handler pattern."""

        @error_handler("Search")
        async def search_handler(arguments: dict) -> dict:
            query = arguments.get("query")
            if not query:
                raise ValueError("Query is required")
            return {"results": [f"result for {query}"], "count": 1}

        # Success case
        result = await search_handler({"query": "test"})
        assert result["count"] == 1

        # Error case
        error_result = await search_handler({})
        assert error_result["error"] == "Query is required"

    @pytest.mark.asyncio
    async def test_model_selection_handler_pattern(self):
        """Test decorator with model selection pattern including context."""
        available_models = ["qwen3", "bge_m3", "coderank"]

        @error_handler(
            "Switch model",
            error_context=lambda args: {"available_models": available_models},
        )
        async def switch_model_handler(arguments: dict) -> dict:
            model = arguments.get("model_name")
            if model not in available_models:
                raise ValueError(f"Model '{model}' not found")
            return {"success": True, "model": model}

        # Error case with context enrichment
        error_result = await switch_model_handler({"model_name": "invalid"})
        assert "Model 'invalid' not found" in error_result["error"]
        assert error_result["available_models"] == available_models


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
