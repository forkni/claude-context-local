"""Decorators for MCP tool handlers.

Provides consistent error handling and other cross-cutting concerns.
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, Callable, Optional

import anyio


logger = logging.getLogger(__name__)


def error_handler(
    action_name: str,
    error_context: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
) -> Callable[[Callable], Callable]:
    """Decorator for consistent error handling in MCP tool handlers.

    Provides unified error handling with:
    - Consistent logging format
    - Exception to error response conversion
    - Optional context enrichment for error responses

    Args:
        action_name: Human-readable action name for logging (e.g., "Search", "Index")
        error_context: Optional callable that takes handler arguments and returns
                       additional fields to include in error response.
                       Example: lambda args: {"available_models": list(MODEL_REGISTRY.keys())}

    Returns:
        Decorator function that wraps async handlers

    Example:
        >>> @error_handler("Search")
        >>> async def handle_search_code(arguments: Dict[str, Any]) -> Dict:
        >>>     # ... business logic ...
        >>>     return {"results": [...]}

        >>> @error_handler(
        >>>     "Switch model",
        >>>     error_context=lambda args: {"available_models": ["qwen3", "bge_m3"]}
        >>> )
        >>> async def handle_switch_embedding_model(arguments: Dict[str, Any]) -> Dict:
        >>>     # ... business logic ...
        >>>     return {"success": True}
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(arguments: dict[str, Any]) -> dict:
            try:
                return await func(arguments)
            except asyncio.CancelledError:
                # Don't catch CancelledError - let it propagate for proper cleanup
                logger.info(f"{action_name} cancelled by client")
                raise
            except (anyio.BrokenResourceError, anyio.ClosedResourceError) as e:
                # Client disconnected while processing - graceful degradation
                logger.warning(f"{action_name} failed - client disconnected: {e}")
                return {"error": "Client disconnected", "status": "cancelled"}
            except Exception as e:
                logger.error(f"{action_name} failed: {e}", exc_info=True)
                error_response = {"error": str(e)}
                if error_context:
                    try:
                        context_fields = error_context(arguments)
                        if context_fields:
                            error_response.update(context_fields)
                    except Exception as ctx_error:
                        # Don't let context enrichment failure break error reporting
                        logger.warning(
                            f"Failed to enrich error context: {ctx_error}",
                            exc_info=True,
                        )
                return error_response

        return wrapper

    return decorator
