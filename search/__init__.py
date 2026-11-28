"""Search and indexing module."""

from .exceptions import (
    CodeSearchError,
    ConfigurationError,
    DimensionMismatchError,
    IndexError,
    ModelLoadError,
    SearchError,
    VRAMExhaustedError,
)


# NOTE: IndexSynchronizer removed from __init__ to avoid circular import
# Import directly from search.index_sync when needed

# Loaded on first use (PEP 562): gpu_monitor imports torch (about 1.2 s), and
# light importers such as mcp_server.index_freshness (the launcher's index
# check) only need search.config / search.filters.
_LAZY = {
    "GPUMemoryMonitor": ".gpu_monitor",
    "MultiHopSearcher": ".multi_hop_searcher",
    "RerankingEngine": ".reranking_engine",
}


def __getattr__(name: str) -> object:
    """Import a heavy member the first time it is read, then cache it."""
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    value = getattr(importlib.import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))


__all__ = [
    "CodeSearchError",
    "ConfigurationError",
    "DimensionMismatchError",
    "GPUMemoryMonitor",
    "IndexError",
    "ModelLoadError",
    "MultiHopSearcher",
    "RerankingEngine",
    "SearchError",
    "VRAMExhaustedError",
]
