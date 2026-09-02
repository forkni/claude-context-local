"""The resource-refresher seam: what a full reindex needs from MCP process state.

``IncrementalIndexer._full_index`` must release and reacquire MCP-managed
resources (embedder pool, searcher cache, GPU memory) before a full reindex —
but that lifecycle belongs to ``mcp_server/``, not to indexing logic.
:class:`ResourceRefresher` is the seam that lets ``search/`` depend on the
*shape* of that behaviour without importing ``mcp_server/`` (ADR-0004's
layering rule).

The two members are declared on one protocol, not two independent
``Callable`` parameters (contrast :class:`~search.index_write_stage.IndexWriteStage`'s
``build_metadata_fn``/``clear_gpu_fn``), because they are not independent:
``refresh_before_full_index`` acquires a ``load_existing=False`` searcher and
commits it to MCP process state, and ``invalidate_searcher_cache`` is its
compensating inverse on the error path. Wiring a real refresher with a
forgotten invalidator would leave a write-only searcher live in process state
after a failed reindex, with nothing to catch it — one object makes the pair
unwireable-apart.

Precedent: :class:`~chunking.relationships.call_edge_resolver.CallEdgeResolver`
is the existing example of a protocol declared in the lower layer and
implemented above it; its docstring records the matching rationale.

Concrete implementation: ``McpResourceRefresher``
(``mcp_server/resource_manager.py``), the one production adapter. It
satisfies this protocol structurally — no base class, no import of this
module — so no import arrow crosses from ``search/`` up into ``mcp_server/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable


if TYPE_CHECKING:
    from embeddings.embedder import CodeEmbedder


@runtime_checkable
class ResourceRefresher(Protocol):
    """What a full reindex needs from MCP process-state management.

    The consuming seam (``IncrementalIndexer``) only depends on this
    protocol — it never imports ``McpResourceRefresher`` or any other
    concrete implementation.
    """

    def refresh_before_full_index(
        self, project_path: str, embedder: CodeEmbedder, indexer: Any
    ) -> tuple[CodeEmbedder, Any]:
        """Release and reacquire resources before a full reindex.

        Args:
            project_path: Path to the project being indexed (needed to
                recreate the searcher).
            embedder: The caller's current embedder.
            indexer: The caller's current indexer.

        Returns:
            The ``(embedder, indexer)`` pair the caller must rebind onto
            itself — a real refresher may return fresh instances; a no-op
            refresher returns the pair unchanged.
        """
        ...

    def invalidate_searcher_cache(self) -> None:
        """Null out any cached searcher left live by a failed reindex.

        Compensating inverse of ``refresh_before_full_index``: called on
        the ``_full_index`` error path, since the searcher acquired there
        is a write-only instance (``load_existing=False``) that must not
        be served as a cached read searcher after a failure.
        """
        ...


class NullResourceRefresher:
    """No-op adapter: keeps the caller's own embedder/indexer, invalidates nothing.

    The default for callers that construct ``IncrementalIndexer`` outside
    the MCP process (unit tests, standalone scripts) and never go through
    the real release/verify/reacquire lifecycle.
    """

    def refresh_before_full_index(
        self, project_path: str, embedder: CodeEmbedder, indexer: Any
    ) -> tuple[CodeEmbedder, Any]:
        return embedder, indexer

    def invalidate_searcher_cache(self) -> None:
        return None
