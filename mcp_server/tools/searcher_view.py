"""Uniform read adapter over HybridSearcher / IntelligentSearcher.

P7: Instead of each handler resolving polymorphism itself (hasattr soup,
    isinstance checks, 3 different `dense_index` vs `index_manager` chains),
    all attribute extraction goes through this single seam.

Usage::

    from mcp_server.tools.searcher_view import SearcherView

    view = SearcherView(get_searcher())
    im = view.index_manager          # always a CodeIndexManager | None
    gs = view.graph_storage          # always a CodeGraphStorage | None
    if view.is_ready and view.total_chunks > 0:
        ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from graph.graph_storage import CodeGraphStorage
    from search.indexer import CodeIndexManager


class SearcherView:
    """Read-only uniform view over HybridSearcher or IntelligentSearcher.

    Hides the single structural asymmetry between the two searcher types:
    the index manager is ``.dense_index`` on HybridSearcher and
    ``.index_manager`` on IntelligentSearcher.  Everything else
    (``graph_storage``, ``is_ready``) is already a uniform property on both.
    """

    __slots__ = ("_s",)

    def __init__(self, searcher: Any) -> None:
        self._s = searcher

    # ------------------------------------------------------------------
    # Core attribute accessors
    # ------------------------------------------------------------------

    @property
    def index_manager(self) -> CodeIndexManager | None:
        """Return the CodeIndexManager regardless of searcher type.

        - ``IntelligentSearcher`` exposes it as ``.index_manager``.
        - ``HybridSearcher`` exposes it as ``.dense_index``.
        """
        return getattr(self._s, "index_manager", None) or getattr(
            self._s, "dense_index", None
        )

    @property
    def graph_storage(self) -> CodeGraphStorage | None:
        """Return graph storage, or None when the graph is not initialised.

        Both searcher types already expose ``.graph_storage`` as a property,
        so no branching is needed.
        """
        return getattr(self._s, "graph_storage", None)

    @property
    def is_ready(self) -> bool:
        """Return True when the searcher has a loaded, non-empty index."""
        return bool(getattr(self._s, "is_ready", False))

    @property
    def total_chunks(self) -> int:
        """Return the number of vectors in the dense FAISS index.

        Uses ``index_manager.index.ntotal`` (works for both searcher types
        once the index_manager asymmetry is resolved above).
        """
        im = self.index_manager
        if im is None:
            return 0
        idx = getattr(im, "index", None)
        return int(getattr(idx, "ntotal", 0) or 0)

    @property
    def is_hybrid(self) -> bool:
        """Return True when the underlying searcher is a HybridSearcher.

        Used by handlers that need to access Hybrid-only stats (bm25_documents,
        dense_vectors, synced) via ``searcher.get_stats()``.  Isolates the
        isinstance check in one place.
        """
        # Local import avoids pulling search.hybrid_searcher into the
        # top-level mcp_server import graph (mirrors the lazy-import pattern
        # already used in search_orchestrator.py).
        from search.hybrid_searcher import HybridSearcher

        return isinstance(self._s, HybridSearcher)
