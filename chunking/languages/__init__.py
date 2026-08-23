"""Language-specific tree-sitter chunkers.

This package contains chunker implementations for different programming languages.
Each language has its own module with a LanguageChunker subclass.

Supported languages (9 total, all via tree-sitter):
- Python (.py)
- JavaScript (.js)
- TypeScript (.ts, .tsx)
- Go (.go)
- Rust (.rs)
- C (.c)
- C++ (.cpp, .cc, .cxx, .c++, .h, .hpp, .hh, .hxx, .inl, .ipp, .tpp)
- CUDA (.cu, .cuh) -- routed to the cpp grammar, see cpp.py's CudaChunker
- C# (.cs)
- GLSL (.glsl, .frag, .vert, .comp, .geom, .tesc, .tese, .glslinc)

Note: chunking/python_ast_chunker.py holds only the shared CodeChunk dataclass,
not a separate Python chunking path.
"""

from .base import LanguageChunker, TreeSitterChunk
from .c import CChunker
from .cpp import CppChunker, CudaChunker
from .csharp import CSharpChunker
from .glsl import GLSLChunker
from .go import GoChunker
from .javascript import JavaScriptChunker
from .python import PythonChunker
from .rust import RustChunker
from .typescript import TypeScriptChunker


__all__ = [
    # Base classes
    "TreeSitterChunk",
    "LanguageChunker",
    # Language chunkers
    "PythonChunker",
    "JavaScriptChunker",
    "TypeScriptChunker",
    "GoChunker",
    "RustChunker",
    "CChunker",
    "CppChunker",
    "CudaChunker",
    "CSharpChunker",
    "GLSLChunker",
]
