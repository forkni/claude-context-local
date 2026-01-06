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
from .gpu_monitor import GPUMemoryMonitor
from .multi_hop_searcher import MultiHopSearcher
from .reranking_engine import RerankingEngine

# NOTE: IndexSynchronizer removed from __init__ to avoid circular import
# Import directly from search.index_sync when needed

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
