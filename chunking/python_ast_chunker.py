"""Python AST-based intelligent code chunking."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from graph.call_graph_extractor import CallEdge


@dataclass
class CodeChunk:
    """Represents a semantically meaningful chunk of code."""

    content: str
    chunk_type: str  # function, class, method, module_level, import_block
    start_line: int
    end_line: int

    # Rich metadata
    file_path: str
    relative_path: str  # path relative to project root
    folder_structure: List[str]  # ['src', 'utils', 'auth'] for nested folders

    # Code structure metadata
    name: Optional[str] = None  # function/class name
    parent_name: Optional[str] = None  # parent class name for methods
    docstring: Optional[str] = None
    decorators: List[str] = None
    imports: List[str] = None  # relevant imports for this chunk

    # Context metadata
    complexity_score: int = 0  # estimated complexity
    tags: List[str] = None  # semantic tags like 'database', 'auth', 'error_handling'

    # Call graph metadata (Phase 1: Python only)
    calls: Optional[List["CallEdge"]] = None  # function calls made by this chunk

    # Evaluation framework compatibility
    language: str = "python"  # programming language
    chunk_id: Optional[str] = None  # unique identifier for evaluation

    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []
        if self.imports is None:
            self.imports = []
        if self.tags is None:
            self.tags = []
        if self.calls is None:
            self.calls = []

        # Extract folder structure from path
        if self.file_path and not self.folder_structure:
            path_parts = Path(self.relative_path).parent.parts
            self.folder_structure = list(path_parts) if path_parts != (".",) else []


# python ast chunker removed
