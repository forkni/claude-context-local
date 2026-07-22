"""Decorators for MCP tool handlers.

Provides consistent error handling and other cross-cutting concerns.
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any

import anyio

from mcp_server.services import get_state
from mcp_server.tools import responses
from utils.observability import traced_block
from utils.otel_attributes import ATTR_TOOL_NAME


logger = logging.getLogger(__name__)


def error_handler(
    action_name: str,
    error_context: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
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
        >>>     error_context=lambda args: {"available_models": ["qwen3_0.6b", "bge_m3"]}
        >>> )
        >>> async def handle_switch_embedding_model(arguments: Dict[str, Any]) -> Dict:
        >>>     # ... business logic ...
        >>>     return {"success": True}
    """

    def decorator(func: Callable) -> Callable:
        span_name = f"mcp.tool.{action_name.lower().replace(' ', '_')}"

        @functools.wraps(func)
        async def wrapper(arguments: dict[str, Any]) -> dict:
            with traced_block(span_name, **{ATTR_TOOL_NAME: action_name}):
                try:
                    return await func(arguments)
                except asyncio.CancelledError:
                    # Don't catch CancelledError - let it propagate for proper cleanup
                    logger.info(f"{action_name} cancelled by client")
                    raise
                except (anyio.BrokenResourceError, anyio.ClosedResourceError) as e:
                    # Client disconnected while processing - graceful degradation
                    logger.warning(f"{action_name} failed - client disconnected: {e}")
                    return responses.client_disconnected()
                except Exception as e:
                    logger.error(f"{action_name} failed: {e}", exc_info=True)
                    error_response = responses.error(str(e))
                    if error_context:
                        try:
                            context_fields = error_context(arguments)
                            if context_fields:
                                error_response.update(context_fields)
                        except Exception as ctx_error:  # noqa: BLE001 - api-boundary: context enrichment failure must not break error response
                            # Don't let context enrichment failure break error reporting
                            logger.warning(
                                f"Failed to enrich error context: {ctx_error}",
                                exc_info=True,
                            )
                    return error_response

        return wrapper

    return decorator


def with_mutation_lock(func: Callable) -> Callable:
    """Decorator that serializes a state-mutating handler on the global lock.

    §IV-C hardening: the server holds global mutable state (active project,
    model, search config — see mcp_server/state.py) and HTTP transport runs
    ``stateless=True``, so concurrent clients share it. Without this, one
    client's ``switch_project``/``configure_*``/``clear_index``/
    ``delete_project`` call could interleave with *another mutation*,
    corrupting shared state mid-write.

    Scope: this lock serializes mutations against each other ONLY. Searches
    never acquire it, so it provides no mutation-vs-search protection —
    handlers that tear down search resources or rewrite/delete index files
    must additionally take the per-project
    ``get_reindex_rwlock(project).write()`` to drain in-flight searches
    (see handle_clear_index / handle_delete_project / handle_index_directory).

    Lock order: mutation lock (outermost) → reindex rwlock. No code may
    acquire the mutation lock while already holding a reindex rwlock — that
    would invert the order and risk deadlock against the handlers above.
    (SearchOrchestrator takes only the rwlock, never this lock.)

    Uses ``ApplicationState.get_mutation_lock()`` — a single process-wide
    ``asyncio.Lock`` shared by all state-mutating tools, following the same
    lazy-creation pattern as the per-project ``get_reindex_rwlock()``. This
    only prevents *interleaving*; it does not add session-scoped isolation
    (a full Stateful Session Server is a separate, larger change).

    Apply inside @error_handler so a failure while the lock is held still
    gets the standard error-response treatment after the lock releases:

        @error_handler("Project switch")
        @with_mutation_lock
        async def handle_switch_project(arguments): ...
    """

    @functools.wraps(func)
    async def wrapper(arguments: dict[str, Any]) -> dict:
        async with get_state().get_mutation_lock():
            return await func(arguments)

    return wrapper


def require_indexed_project(func: Callable) -> Callable:
    """Decorator that short-circuits with an error when no project is indexed.

    Apply inside @error_handler so the outer handler covers any unexpected
    failure from the state check itself:

        @error_handler("Search")
        @require_indexed_project
        async def handle_search_code(arguments): ...
    """

    @functools.wraps(func)
    async def wrapper(arguments: dict[str, Any]) -> dict:
        if not get_state().current_project:
            return responses.no_indexed_project()
        return await func(arguments)

    return wrapper
