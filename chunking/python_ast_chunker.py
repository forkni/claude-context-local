"""Python AST-based intelligent code chunking."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from graph.call_graph_extractor import CallEdge


@dataclass(slots=True)
class CodeChunk:
    """Represents a semantically meaningful chunk of code."""

    content: str
    chunk_type: str  # function, class, method, module_level, import_block
    start_line: int
    end_line: int

    # Rich metadata
    file_path: str
    relative_path: str  # path relative to project root
    folder_structure: list[str]  # ['src', 'utils', 'auth'] for nested folders

    # Code structure metadata
    name: Optional[str] = None  # function/class name
    parent_name: Optional[str] = None  # parent class name for methods
    parent_chunk_id: Optional[str] = None  # parent class chunk_id for methods
    docstring: Optional[str] = None
    decorators: list[str] = None
    imports: list[str] = None  # relevant imports for this chunk

    # Context metadata
    complexity_score: int = 0  # estimated complexity
    tags: list[str] = None  # semantic tags like 'database', 'auth', 'error_handling'

    # Call graph metadata
    calls: Optional[list["CallEdge"]] = None  # function calls made by this chunk

    # Relationship tracking
    relationships: Optional[list] = (
        None  # All relationship types (RelationshipEdge objects)
    )

    # Evaluation framework compatibility
    language: str = "python"  # programming language
    chunk_id: Optional[str] = None  # unique identifier for evaluation

    # Community detection metadata
    community_id: Optional[int] = None  # Leiden community membership

    # Merged symbols for secondary symbol index (Phase A6)
    merged_from: Optional[list[str]] = None  # All symbol names in merged chunk

    # Internal metadata (for merge statistics tracking)
    _merge_stats: Optional[tuple] = None  # (original_count, merged_count)

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
