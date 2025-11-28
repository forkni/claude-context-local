"""
Graph-based code analysis module.

This module provides call graph extraction, storage, and querying capabilities
for code understanding and structural analysis.

Phase 1 Features:
- Call graph extraction (Python-first)
- NetworkX-based graph storage
- Graph persistence (JSON)
- Basic graph queries (callers, callees, neighbors)

Future Enhancements:
- Type information extraction
- Import dependency graphs
- PageRank-based ranking
- C++ and GLSL support
"""

from .call_graph_extractor import (
    CallEdge,
    CallGraphExtractor,
    CallGraphExtractorFactory,
    PythonCallGraphExtractor,
)
from .graph_queries import GraphQueryEngine
from .graph_storage import CodeGraphStorage

__all__ = [
    "CallEdge",
    "CallGraphExtractor",
    "PythonCallGraphExtractor",
    "CallGraphExtractorFactory",
    "CodeGraphStorage",
    "GraphQueryEngine",
]

__version__ = "0.1.0"  # Phase 1: Python call graph extraction
