"""Multi-language chunker that combines AST and tree-sitter approaches."""

import ast
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

from search.filters import normalize_path

from .python_ast_chunker import CodeChunk
from .tree_sitter import TreeSitterChunk, TreeSitterChunker

# Import call graph extractor for Python
try:
    from graph.call_graph_extractor import CallGraphExtractorFactory
    from graph.relationship_extractors.class_attr_extractor import (
        ClassAttributeExtractor,
    )
    from graph.relationship_extractors.constant_extractor import ConstantExtractor
    from graph.relationship_extractors.context_manager_extractor import (
        ContextManagerExtractor,
    )
    from graph.relationship_extractors.dataclass_field_extractor import (
        DataclassFieldExtractor,
    )
    from graph.relationship_extractors.decorator_extractor import DecoratorExtractor
    from graph.relationship_extractors.default_param_extractor import (
        DefaultParameterExtractor,
    )
    from graph.relationship_extractors.enum_extractor import EnumMemberExtractor
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
    """Dedent code by removing the indentation of the first non-blank line.

    Uses first-line baseline approach (Scrapy method) which handles:
    - Flush-left string continuations (docstrings with flush-left text)
    - Mixed tabs/spaces (tabs normalized to 4 spaces)
    - Blank lines without whitespace
    - Decorators and nested structures

    This solves the textwrap.dedent() failure for decorated definitions.

    Args:
        code: Source code string with potential leading indentation

    Returns:
        Dedented code that can be parsed by ast.parse()

    References:
        Scrapy GitHub issue #4477, PR #4935
    """
    if not code or not code.strip():
        return code

    # Normalize line endings (CRLF → LF, CR → LF)
    # This handles Windows files and mixed line endings
    code = code.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize tabs to 4 spaces for consistent handling
    code = code.expandtabs(4)

    lines = code.split("\n")

    # Strip leading/trailing blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return code

    # Find indentation of first non-blank line (baseline)
    first_line = lines[0]
    baseline_indent = len(first_line) - len(first_line.lstrip())

    if baseline_indent == 0:
        # First line is flush-left, try parsing directly
        dedented = "\n".join(lines)
        try:
            ast.parse(dedented)
            return dedented
        except SyntaxError:
            # First line is at column 0 but subsequent lines may be indented
            # (common with decorated definitions extracted by tree-sitter)
            # Find minimum indent from subsequent lines
            subsequent_indents = []
            for line in lines[1:]:  # Skip first line
                if line.strip():  # Non-blank line
                    indent = len(line) - len(line.lstrip())
                    if indent > 0:
                        subsequent_indents.append(indent)

            if subsequent_indents:
                # Dedent subsequent lines by their minimum common indent
                min_indent = min(subsequent_indents)
                dedented_lines = [lines[0]]  # Keep first line as-is
                for line in lines[1:]:
                    if not line.strip():
                        dedented_lines.append("")
                    elif len(line) >= min_indent and line[:min_indent].strip() == "":
                        dedented_lines.append(line[min_indent:])
                    else:
                        dedented_lines.append(line.lstrip())

                dedented = "\n".join(dedented_lines)
                try:
                    ast.parse(dedented)
                    return dedented
                except SyntaxError:
                    pass  # Fall through to wrap_with_if_true

            return _wrap_with_if_true(dedented)

    # Remove baseline indentation from all lines
    dedented_lines = []
    for line in lines:
        if not line.strip():
            # Preserve blank lines as empty
            dedented_lines.append("")
        elif len(line) >= baseline_indent and line[:baseline_indent].strip() == "":
            # Line has at least baseline_indent spaces, remove them
            dedented_lines.append(line[baseline_indent:])
        else:
            # Line has less indentation than baseline (flush-left content)
            # This happens with multi-line string continuations
            dedented_lines.append(line.lstrip())

    dedented = "\n".join(dedented_lines)

    try:
        ast.parse(dedented)
        return dedented
    except SyntaxError:
        return _wrap_with_if_true(dedented)


def _wrap_with_if_true(code: str) -> str:
    """Wrap code with 'if True:' block as fallback for flush-left content.

    This is the industry-standard fallback (used by Scrapy, Numba) for handling
    code with flush-left content that can't be dedented normally.

    Args:
        code: Dedented code that may still have parsing issues

    Returns:
        Wrapped code or original if wrapping fails
    """
    # Indent all lines by 4 spaces
    indented_lines = []
    for line in code.split("\n"):
        if line.strip():
            indented_lines.append("    " + line)
        else:
            indented_lines.append("")

    wrapped = "if True:\n" + "\n".join(indented_lines)

    try:
        ast.parse(wrapped)
        return wrapped
    except SyntaxError as e:
        # If even wrapping fails, return original code
        # Log for debugging - helps identify edge cases not handled
        logger.warning(
            f"_smart_dedent: Both dedent and wrap failed. "
            f"Error: {e}. First 100 chars: {repr(code[:100])}"
        )
        # Let the caller handle the syntax error
        return code


class MultiLanguageChunker:
    """Unified chunker supporting multiple programming languages."""

    # Supported extensions
    SUPPORTED_EXTENSIONS = {
        ".py",  # Python
        ".js",  # JavaScript
        ".ts",  # TypeScript
        ".tsx",  # TSX
        ".go",  # Go
        ".rs",  # Rust
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
    }

    # Node type to chunk type mapping (tree-sitter → CodeChunk)
    NODE_TYPE_MAP = {
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

    def __init__(
        self,
        root_path: Optional[str] = None,
        include_dirs: Optional[list] = None,
        exclude_dirs: Optional[list] = None,
        enable_entity_tracking: bool = False,
    ):
        """Initialize multi-language chunker.

        Args:
            root_path: Optional root path for relative path calculation
            include_dirs: Optional list of directories to include
            exclude_dirs: Optional list of directories to exclude
            enable_entity_tracking: Enable P4-5 entity extractors (enums, defaults, context managers). Default False.
        """
        self.root_path = root_path
        self.enable_entity_tracking = enable_entity_tracking
        # Use AST chunker for Python (more mature implementation)
        # Use tree-sitter for other languages
        self.tree_sitter_chunker = TreeSitterChunker()

        # Initialize directory filter for index-time filtering
        from search.filters import DirectoryFilter

        self.directory_filter = DirectoryFilter(include_dirs, exclude_dirs)

        # Initialize call graph extractor for Python
        self.call_graph_extractor = None
        if CALL_GRAPH_AVAILABLE:
            try:
                self.call_graph_extractor = CallGraphExtractorFactory.create("python")
                logger.info("Call graph extraction enabled for Python")
            except Exception as e:
                logger.warning(f"Failed to initialize call graph extractor: {e}")

        # Initialize relationship extractors
        self.relationship_extractors = []
        try:
            self.relationship_extractors = [
                # Priority 1 (Foundation) - always enabled
                InheritanceExtractor(),
                TypeAnnotationExtractor(),
                ImportExtractor(),
                # Priority 2 (Core) - always enabled
                DecoratorExtractor(),
                ExceptionExtractor(),
                InstantiationExtractor(),
                # Promoted to P2 - essential for understanding code structure
                ClassAttributeExtractor(),  # Class data models (self.x = ...)
                DataclassFieldExtractor(),  # Dataclass fields (field(...))
                ConstantExtractor(),  # Module-level UPPER_CASE constants
            ]

            # Priority 4-5 (Entity Tracking) - conditional
            if enable_entity_tracking:
                self.relationship_extractors.extend(
                    [
                        EnumMemberExtractor(),
                        DefaultParameterExtractor(),
                        ContextManagerExtractor(),
                    ]
                )
                logger.info(
                    f"Initialized {len(self.relationship_extractors)} relationship extractors "
                    f"(foundation + core + data models + entity tracking)"
                )
            else:
                logger.info(
                    f"Initialized {len(self.relationship_extractors)} relationship extractors "
                    f"(foundation + core + data models; entity tracking disabled)"
                )
        except Exception as e:
            logger.warning(f"Failed to initialize relationship extractors: {e}")

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

    def _map_node_type(self, node_type: str, parent_name: Optional[str]) -> str:
        """Map tree-sitter node type to chunk type.

        Args:
            node_type: Tree-sitter node type
            parent_name: Parent class name (if any)

        Returns:
            Mapped chunk type (function, method, class, etc.)
        """
        # Get base chunk type from mapping
        chunk_type = self.NODE_TYPE_MAP.get(node_type, node_type)

        # If we have a parent_name and it's a function, it's actually a method
        if parent_name and chunk_type == "function":
            chunk_type = "method"

        return chunk_type

    def _build_folder_structure(self, file_path: str) -> List[str]:
        """Build folder parts from file path.

        Args:
            file_path: Path to the source file

        Returns:
            List of folder parts for the file
        """
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

        return folder_parts

    def _extract_semantic_tags(self, metadata: dict, language: str) -> List[str]:
        """Extract semantic tags from chunk metadata.

        Args:
            metadata: Chunk metadata dictionary
            language: Programming language

        Returns:
            List of semantic tags (async, generator, export, etc.)
        """
        tags = []

        if metadata.get("is_async"):
            tags.append("async")
        if metadata.get("is_generator"):
            tags.append("generator")
        if metadata.get("is_export"):
            tags.append("export")
        if metadata.get("has_generics"):
            tags.append("generic")
        if metadata.get("is_component"):
            tags.append("component")

        # Add language tag
        tags.append(language)

        return tags

    def _create_chunk_id(
        self,
        relative_path: str,
        start_line: int,
        end_line: int,
        chunk_type: str,
        qualified_name: Optional[str],
    ) -> str:
        """Generate normalized chunk ID for relationship extraction.

        Args:
            relative_path: Relative path to source file
            start_line: Start line number
            end_line: End line number
            chunk_type: Type of chunk (function, method, class, etc.)
            qualified_name: Qualified name (e.g., ClassName.method_name)

        Returns:
            Normalized chunk ID string
        """
        # Normalize path to forward slashes (cross-platform)
        normalized_path = normalize_path(str(relative_path))
        chunk_id = f"{normalized_path}:{start_line}-{end_line}:{chunk_type}"

        # Use qualified name (ClassName.method_name) for better disambiguation
        if qualified_name:
            chunk_id += f":{qualified_name}"

        return chunk_id

    def _extract_call_relationships(
        self, chunk: CodeChunk, tchunk: TreeSitterChunk, chunk_id: str
    ) -> None:
        """Extract call graph relationships.

        Args:
            chunk: CodeChunk to populate with call relationships
            tchunk: Tree-sitter chunk with source code
            chunk_id: Chunk identifier for logging
        """
        if (
            self.call_graph_extractor is None
            or tchunk.language != "python"
            or chunk.chunk_type not in ("function", "method", "decorated_definition")
        ):
            return

        try:
            chunk_metadata = {
                "chunk_id": chunk_id,
                "file_path": chunk.relative_path,
                "name": chunk.name,
                "chunk_type": chunk.chunk_type,
                "parent_class": chunk.parent_name,
            }
            # Extract function calls from this chunk
            calls = self.call_graph_extractor.extract_calls(
                _smart_dedent(tchunk.content), chunk_metadata
            )
            chunk.calls = calls

            if calls:
                logger.debug(f"Extracted {len(calls)} calls from {chunk_id}")
        except Exception as e:
            # Handle AST recursion depth limitation in Python 3.11.0-3.11.3
            if "recursion depth mismatch" in str(e):
                logger.debug(
                    f"Skipping call extraction for {chunk.name} (Python 3.11 AST bug)"
                )
            else:
                logger.warning(f"Failed to extract calls for {chunk.name}: {e}")

    def _extract_phase3_relationships(
        self, chunk: CodeChunk, tchunk: TreeSitterChunk, chunk_id: str
    ) -> None:
        """Extract relationship edges (inheritance, types, etc.).

        Args:
            chunk: CodeChunk to populate with relationships
            tchunk: Tree-sitter chunk with source code
            chunk_id: Chunk identifier for logging
        """
        if tchunk.language != "python" or not self.relationship_extractors:
            return

        try:
            chunk_metadata = {
                "chunk_id": chunk_id,
                "file_path": chunk.relative_path,
                "name": chunk.name,
                "chunk_type": chunk.chunk_type,
                "parent_class": chunk.parent_name,
            }

            all_relationships = []
            # Use smart_dedent to properly dedent nested code
            dedented_content = _smart_dedent(tchunk.content)

            for extractor in self.relationship_extractors:
                edges = extractor.extract(dedented_content, chunk_metadata)
                all_relationships.extend(edges)

            chunk.relationships = all_relationships

            if all_relationships:
                logger.debug(
                    f"Extracted {len(all_relationships)} relationships from {chunk_id}"
                )
        except Exception as e:
            # Handle AST recursion depth limitation in Python 3.11.0-3.11.3
            if "recursion depth mismatch" in str(e):
                logger.debug(
                    f"Skipping relationship extraction for {chunk.name} (Python 3.11 AST limitation)"
                )
            else:
                logger.warning(f"Failed to extract relationships for {chunk.name}: {e}")

    def _convert_tree_chunks(
        self, tree_chunks: List[TreeSitterChunk], file_path: str
    ) -> List[CodeChunk]:
        """Convert tree-sitter chunks to CodeChunk format.

        Orchestrates the conversion process by delegating to helper methods
        for node type mapping, folder structure building, semantic tag extraction,
        chunk ID generation, and relationship extraction.

        Args:
            tree_chunks: List of TreeSitterChunk objects
            file_path: Path to the source file

        Returns:
            List of CodeChunk objects
        """
        code_chunks = []

        # Build folder structure once for all chunks
        folder_parts = self._build_folder_structure(file_path)
        path = Path(file_path)

        for tchunk in tree_chunks:
            # Extract metadata
            name = tchunk.metadata.get("name")
            docstring = tchunk.metadata.get("docstring")
            decorators = tchunk.metadata.get("decorators", [])

            # Extract parent class from chunk (prefer explicit field, fallback to metadata)
            parent_name = tchunk.parent_class or tchunk.metadata.get("parent_name")

            # Map node type to chunk type (handles parent class logic)
            chunk_type = self._map_node_type(tchunk.node_type, parent_name)

            # Build qualified name for methods/functions inside classes
            qualified_name = f"{parent_name}.{name}" if parent_name and name else name

            # Extract semantic tags from metadata
            tags = self._extract_semantic_tags(tchunk.metadata, tchunk.language)

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

            # Generate chunk_id for relationship extraction
            chunk_id = self._create_chunk_id(
                chunk.relative_path,
                chunk.start_line,
                chunk.end_line,
                chunk_type,
                qualified_name,
            )

            # Extract call graph relationships
            self._extract_call_relationships(chunk, tchunk, chunk_id)

            # Extract relationship edges
            self._extract_phase3_relationships(chunk, tchunk, chunk_id)

            code_chunks.append(chunk)

        return code_chunks

    def chunk_directory(
        self,
        directory_path: str,
        extensions: Optional[List[str]] = None,
        enable_parallel: bool = True,
        max_workers: int = 4,
    ) -> List[CodeChunk]:
        """Chunk all supported files in a directory.

        Args:
            directory_path: Path to directory
            extensions: Optional list of extensions to process (default: all supported)
            enable_parallel: Enable parallel file chunking (default: True)
            max_workers: Number of ThreadPoolExecutor workers (default: 4)

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

        # Collect all file paths first
        file_paths = []
        for ext in valid_extensions:
            for file_path in dir_path.rglob(f"*{ext}"):
                # Skip common large/build/tooling directories
                if any(part in self.DEFAULT_IGNORED_DIRS for part in file_path.parts):
                    continue
                file_paths.append(file_path)

        # Apply custom directory filters (include_dirs/exclude_dirs)
        if self.root_path and self.directory_filter:
            root = Path(self.root_path)
            filtered_paths = []
            for file_path in file_paths:
                try:
                    relative_path = str(file_path.relative_to(root))
                    if self.directory_filter.matches(relative_path):
                        filtered_paths.append(file_path)
                except ValueError:
                    # File not under root, skip it
                    continue
            logger.info(
                f"Applied directory filters: {len(file_paths)} files -> {len(filtered_paths)} files"
            )
            file_paths = filtered_paths

        logger.info(f"Found {len(file_paths)} files to chunk")

        # Process files in parallel or sequentially
        if enable_parallel and len(file_paths) > 1:
            all_chunks = self._chunk_files_parallel(file_paths, max_workers)
        else:
            all_chunks = self._chunk_files_sequential(file_paths)

        logger.info(f"Total chunks from directory: {len(all_chunks)}")
        return all_chunks

    def _chunk_files_sequential(self, file_paths: List[Path]) -> List[CodeChunk]:
        """Chunk files sequentially without parallelization.

        Args:
            file_paths: List of file paths to chunk

        Returns:
            List of CodeChunk objects from all files
        """
        all_chunks = []
        for file_path in file_paths:
            try:
                chunks = self.chunk_file(str(file_path))
                all_chunks.extend(chunks)
                logger.debug(f"Chunked {len(chunks)} from {file_path}")
            except Exception as e:
                logger.warning(f"Failed to chunk {file_path}: {e}")
        return all_chunks

    def _chunk_files_parallel(
        self, file_paths: List[Path], max_workers: int
    ) -> List[CodeChunk]:
        """Chunk files in parallel using ThreadPoolExecutor.

        Args:
            file_paths: List of file paths to chunk
            max_workers: Number of ThreadPoolExecutor workers

        Returns:
            List of CodeChunk objects from all files
        """
        all_chunks = []

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chunking tasks
            future_to_path = {
                executor.submit(self.chunk_file, str(file_path)): file_path
                for file_path in file_paths
            }

            # Collect results as they complete
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    chunks = future.result()
                    all_chunks.extend(chunks)
                    logger.debug(f"Chunked {len(chunks)} from {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to chunk {file_path}: {e}")

        return all_chunks
