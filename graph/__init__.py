"""
Graph-based code analysis module.

This module provides call graph extraction, storage, and querying capabilities
for code understanding and structural analysis.

Current Features:
- Call graph extraction (Python)
- NetworkX-based graph storage
- Graph persistence (JSON format)
- Graph queries (callers, callees, neighbors)

Planned Enhancements:
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

__version__ = "0.1.0"  # Python call graph extraction
