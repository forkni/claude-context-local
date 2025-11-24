"""Language-specific tree-sitter chunkers.

This package contains chunker implementations for different programming languages.
Each language has its own module with a LanguageChunker subclass.

Supported languages (9 total):
- Python (.py) - also available via AST-based chunker
- JavaScript (.js)
- TypeScript (.ts, .tsx)
- Go (.go)
- Rust (.rs)
- C (.c)
- C++ (.cpp, .cc, .cxx, .c++)
- C# (.cs)
- GLSL (.glsl, .frag, .vert, .comp, .geom, .tesc, .tese)

Note: Python also has a separate AST-based chunker (chunking/python_chunker.py)
"""

from .base import LanguageChunker, TreeSitterChunk
from .c import CChunker
from .cpp import CppChunker
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
    "CSharpChunker",
    "GLSLChunker",
]
