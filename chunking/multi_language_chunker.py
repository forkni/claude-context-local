"""Multi-language chunker that combines AST and tree-sitter approaches."""

import ast
import logging
import textwrap
from pathlib import Path
from typing import List, Optional

from .python_ast_chunker import CodeChunk
from .tree_sitter import TreeSitterChunk, TreeSitterChunker

# Import call graph extractor for Python (Phase 1)
try:
    from graph.call_graph_extractor import CallGraphExtractorFactory
    from graph.relationship_extractors.decorator_extractor import DecoratorExtractor
    from graph.relationship_extractors.exception_extractor import ExceptionExtractor
    from graph.relationship_extractors.import_extractor import ImportExtractor
    from graph.relationship_extractors.inheritance_extractor import InheritanceExtractor
    from graph.relationship_extractors.instantiation_extractor import (
        InstantiationExtractor,
    )
    from graph.relationship_extractors.type_extractor import TypeAnnotationExtractor

    CALL_GRAPH_AVAILABLE = True
except ImportError:
    CALL_GRAPH_AVAILABLE = False

logger = logging.getLogger(__name__)


def _smart_dedent(code: str) -> str:
    """Dedent code using the 'if True:' wrapper technique.

    This is the industry-standard solution (used by Scrapy, Numba)
    that handles ALL edge cases including:
    - Flush-left string continuations
    - Mixed tabs/spaces
    - Blank lines without whitespace
    - Decorators and nested structures

    Args:
        code: Source code string with potential leading indentation

    Returns:
        Dedented code that can be parsed by ast.parse()
    """
    if not code or not code.strip():
        return code

    # Strip leading/trailing blank lines
    lines = code.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return code

    code = "\n".join(lines)

    # Try standard dedent first (handles simple cases)
    dedented = textwrap.dedent(code)

    # Test if it parses
    try:
        ast.parse(dedented)
        return dedented
    except SyntaxError:
        pass

    # Fallback: wrap with "if True:" to create valid indented block
    # This handles flush-left content, mixed indentation, etc.
    indented = textwrap.indent(dedented, "    ")
    wrapped = "if True:\n" + indented

    try:
        ast.parse(wrapped)
        return wrapped
    except SyntaxError:
        # If still fails, return original - let extractor handle error
        return code


class MultiLanguageChunker:
    """Unified chunker supporting multiple programming languages."""

    # Supported extensions
    SUPPORTED_EXTENSIONS = {
        ".py",  # Python
        ".js",  # JavaScript
        ".jsx",  # JSX
        ".ts",  # TypeScript
        ".tsx",  # TSX
        ".svelte",  # Svelte
        ".go",  # Go
        ".rs",  # Rust
        ".java",  # Java
        ".c",  # C
        ".cpp",  # C++
        ".cc",  # C++
        ".cxx",  # C++
        ".c++",  # C++
        ".cs",  # C#
        ".glsl",  # GLSL shader
        ".frag",  # Fragment shader
        ".vert",  # Vertex shader
        ".comp",  # Compute shader
        ".geom",  # Geometry shader
        ".tesc",  # Tessellation control shader
        ".tese",  # Tessellation evaluation shader
    }

    # Common large/build/tooling directories to skip during traversal
    DEFAULT_IGNORED_DIRS = {
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        ".env",
        ".direnv",
        "site-packages",  # Python package installations
        "node_modules",
        ".pnpm-store",
        ".yarn",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".pytype",
        ".ipynb_checkpoints",
        "build",
        "dist",
        "out",
        "public",
        ".next",
        ".nuxt",
        ".svelte-kit",
        ".angular",
        ".astro",
        ".vite",
        ".cache",
        ".parcel-cache",
        ".turbo",
        "coverage",
        ".coverage",
        ".nyc_output",
        ".gradle",
        ".idea",
        ".vscode",
        ".docusaurus",
        ".vercel",
        ".serverless",
        ".terraform",
        ".mvn",
        ".tox",
        "target",
        "bin",
        "obj",
        "_archive",
        "backups",  # Development backup directories
    }

    def __init__(self, root_path: Optional[str] = None):
        """Initialize multi-language chunker.

        Args:
            root_path: Optional root path for relative path calculation
        """
        self.root_path = root_path
        # Use AST chunker for Python (more mature implementation)
        # Use tree-sitter for other languages
        self.tree_sitter_chunker = TreeSitterChunker()

        # Initialize call graph extractor for Python (Phase 1)
        self.call_graph_extractor = None
        if CALL_GRAPH_AVAILABLE:
            try:
                self.call_graph_extractor = CallGraphExtractorFactory.create("python")
                logger.info("Call graph extraction enabled for Python")
            except Exception as e:
                logger.warning(f"Failed to initialize call graph extractor: {e}")

        # Initialize Phase 3 relationship extractors
        self.relationship_extractors = []
        try:
            self.relationship_extractors = [
                # Priority 1 (Foundation)
                InheritanceExtractor(),
                TypeAnnotationExtractor(),
                ImportExtractor(),
                # Priority 2 (Core)
                DecoratorExtractor(),
                ExceptionExtractor(),
                InstantiationExtractor(),
            ]
            logger.info(
                f"Phase 3: Initialized {len(self.relationship_extractors)} relationship extractors"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Phase 3 extractors: {e}")

    def is_supported(self, file_path: str) -> bool:
        """Check if file type is supported.

        Args:
            file_path: Path to file

        Returns:
            True if file type is supported
        """
        suffix = Path(file_path).suffix.lower()
        return suffix in self.SUPPORTED_EXTENSIONS

    def chunk_file(self, file_path: str) -> List[CodeChunk]:
        """Chunk a file into semantic units.

        Args:
            file_path: Path to the file

        Returns:
            List of CodeChunk objects
        """
        if not self.is_supported(file_path):
            logger.debug(f"File type not supported: {file_path}")
            return []

        Path(file_path).suffix.lower()

        # Use tree-sitter for all  languages
        try:
            tree_chunks = self.tree_sitter_chunker.chunk_file(file_path)
            # Convert TreeSitterChunk to CodeChunk
            return self._convert_tree_chunks(tree_chunks, file_path)
        except Exception as e:
            logger.error(f"Failed to chunk file {file_path}: {e}")
            return []

    def _convert_tree_chunks(
        self, tree_chunks: List[TreeSitterChunk], file_path: str
    ) -> List[CodeChunk]:
        """Convert tree-sitter chunks to CodeChunk format.

        Args:
            tree_chunks: List of TreeSitterChunk objects
            file_path: Path to the source file

        Returns:
            List of CodeChunk objects
        """
        code_chunks = []

        for tchunk in tree_chunks:
            # Extract metadata
            name = tchunk.metadata.get("name")
            docstring = tchunk.metadata.get("docstring")
            decorators = tchunk.metadata.get("decorators", [])

            # Map tree-sitter node types to our chunk types
            chunk_type_map = {
                "function_declaration": "function",
                "function_definition": "function",
                "arrow_function": "function",
                "function": "function",
                "function_item": "function",  # Rust
                "method_declaration": "method",  # Go, Java
                "method_definition": "method",
                "class_declaration": "class",
                "class_definition": "class",
                "class_specifier": "class",  # C++
                "interface_declaration": "interface",
                "type_alias_declaration": "type",
                "type_declaration": "type",  # Go
                "enum_declaration": "enum",
                "enum_specifier": "enum",  # C
                "enum_item": "enum",  # Rust
                "struct_declaration": "struct",  # C#
                "struct_specifier": "struct",  # C/C++
                "struct_item": "struct",  # Rust
                "union_specifier": "union",  # C/C++
                "namespace_definition": "namespace",  # C++
                "namespace_declaration": "namespace",  # C#
                "impl_item": "impl",  # Rust
                "trait_item": "trait",  # Rust
                "mod_item": "module",  # Rust
                "macro_definition": "macro",  # Rust
                "constructor_declaration": "constructor",  # Java/C#
                "destructor_declaration": "destructor",  # C#
                "property_declaration": "property",  # C#
                "event_declaration": "event",  # C#
                "template_declaration": "template",  # C++
                "concept_definition": "concept",  # C++
                "annotation_type_declaration": "annotation",  # Java
                "script_element": "script",  # Svelte
                "style_element": "style",  # Svelte
                "variable_declaration": "variable",  # GLSL uniforms, varying, attributes
                "preprocessor_define": "define",  # GLSL preprocessor defines
                "preprocessor_function_def": "define",  # GLSL preprocessor function defines
                "block_statement": "block",  # GLSL code blocks
                "compound_statement": "block",  # GLSL compound statements
            }

            chunk_type = chunk_type_map.get(tchunk.node_type, tchunk.node_type)

            # Extract parent name and adjust chunk type for methods
            parent_name = tchunk.metadata.get("parent_name")

            # If we have a parent_name and it's a function, it's actually a method
            if parent_name and chunk_type == "function":
                chunk_type = "method"

            # Build folder structure from file path
            path = Path(file_path)
            folder_parts = []
            if self.root_path:
                try:
                    rel_path = path.relative_to(self.root_path)
                    folder_parts = list(rel_path.parent.parts)
                except ValueError:
                    folder_parts = [path.parent.name] if path.parent.name else []
            else:
                folder_parts = [path.parent.name] if path.parent.name else []

            # Extract semantic tags from metadata
            tags = []
            if tchunk.metadata.get("is_async"):
                tags.append("async")
            if tchunk.metadata.get("is_generator"):
                tags.append("generator")
            if tchunk.metadata.get("is_export"):
                tags.append("export")
            if tchunk.metadata.get("has_generics"):
                tags.append("generic")
            if tchunk.metadata.get("is_component"):
                tags.append("component")

            # Add language tag
            tags.append(tchunk.language)

            # Create CodeChunk
            chunk = CodeChunk(
                file_path=str(path),
                relative_path=(
                    str(path.relative_to(self.root_path))
                    if self.root_path
                    else str(path)
                ),
                folder_structure=folder_parts,
                chunk_type=chunk_type,
                content=tchunk.content,
                start_line=tchunk.start_line,
                end_line=tchunk.end_line,
                name=name,
                parent_name=parent_name,
                docstring=docstring,
                decorators=decorators,
                imports=[],  # Tree-sitter doesn't extract imports yet
                complexity_score=0,  # Not calculated for tree-sitter chunks
                tags=tags,
                language=tchunk.language,
            )

            # Build chunk_id for relationship extraction (Phase 1 + Phase 3)
            # Normalize path to forward slashes (cross-platform)
            normalized_path = str(chunk.relative_path).replace("\\", "/")
            chunk_id = (
                f"{normalized_path}:{chunk.start_line}-{chunk.end_line}:{chunk_type}"
            )
            if name:
                chunk_id += f":{name}"
            chunk_metadata = {
                "chunk_id": chunk_id,
                "file_path": chunk.relative_path,
                "name": name,
                "chunk_type": chunk_type,
            }

            # Extract call graph for Python chunks (Phase 1)
            if (
                self.call_graph_extractor is not None
                and tchunk.language == "python"
                and chunk_type in ("function", "method")
            ):
                try:
                    # Extract function calls from this chunk
                    calls = self.call_graph_extractor.extract_calls(
                        tchunk.content, chunk_metadata
                    )
                    chunk.calls = calls

                    if calls:
                        logger.debug(f"Extracted {len(calls)} calls from {chunk_id}")
                except Exception as e:
                    logger.warning(f"Failed to extract calls for {name}: {e}")

            # Phase 3: Extract all relationship types (for ALL Python chunks)
            if tchunk.language == "python" and self.relationship_extractors:
                try:
                    all_relationships = []
                    # Use smart_dedent to properly dedent nested code
                    # Handles blank lines correctly while preserving relative indentation
                    dedented_content = _smart_dedent(tchunk.content)
                    for extractor in self.relationship_extractors:
                        edges = extractor.extract(dedented_content, chunk_metadata)
                        all_relationships.extend(edges)

                    chunk.relationships = all_relationships

                    if all_relationships:
                        logger.debug(
                            f"Extracted {len(all_relationships)} Phase 3 relationships from {chunk_id}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to extract Phase 3 relationships for {name}: {e}"
                    )

            code_chunks.append(chunk)

        return code_chunks

    def chunk_directory(
        self, directory_path: str, extensions: Optional[List[str]] = None
    ) -> List[CodeChunk]:
        """Chunk all supported files in a directory.

        Args:
            directory_path: Path to directory
            extensions: Optional list of extensions to process (default: all supported)

        Returns:
            List of CodeChunk objects from all files
        """
        all_chunks = []
        dir_path = Path(directory_path)

        if not dir_path.exists() or not dir_path.is_dir():
            logger.error(f"Directory does not exist: {directory_path}")
            return []

        # Use provided extensions or all supported
        if extensions:
            valid_extensions = set(extensions) & self.SUPPORTED_EXTENSIONS
        else:
            valid_extensions = self.SUPPORTED_EXTENSIONS

        # Find all files with supported extensions
        for ext in valid_extensions:
            for file_path in dir_path.rglob(f"*{ext}"):
                # Skip common large/build/tooling directories
                if any(part in self.DEFAULT_IGNORED_DIRS for part in file_path.parts):
                    continue

                try:
                    chunks = self.chunk_file(str(file_path))
                    all_chunks.extend(chunks)
                    logger.debug(f"Chunked {len(chunks)} from {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to chunk {file_path}: {e}")

        logger.info(f"Total chunks from directory: {len(all_chunks)}")
        return all_chunks
