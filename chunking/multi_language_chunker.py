"""Multi-language chunker that combines AST and tree-sitter approaches."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from search.filters import normalize_path

if TYPE_CHECKING:
    from graph.relation_filter import RepositoryRelationFilter

# Import utilities from new modules
from .dedent_utils import smart_dedent as _smart_dedent
from .language_registry import (
    DEFAULT_IGNORED_DIRS,
    NODE_TYPE_MAP,
    SUPPORTED_EXTENSIONS,
)
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


class MultiLanguageChunker:
    """Unified chunker supporting multiple programming languages."""

    # Backward compatibility - reference registry constants
    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS
    DEFAULT_IGNORED_DIRS = DEFAULT_IGNORED_DIRS
    NODE_TYPE_MAP = NODE_TYPE_MAP

    def __init__(
        self,
        root_path: Optional[str] = None,
        include_dirs: Optional[list] = None,
        exclude_dirs: Optional[list] = None,
        enable_entity_tracking: bool = False,
        relation_filter: Optional["RepositoryRelationFilter"] = None,
    ):
        """Initialize multi-language chunker.

        Args:
            root_path: Optional root path for relative path calculation
            include_dirs: Optional list of directories to include
            exclude_dirs: Optional list of directories to exclude
            enable_entity_tracking: Enable P4-5 entity extractors (enums, defaults, context managers). Default False.
            relation_filter: Optional RepositoryRelationFilter for import classification
        """
        self.root_path = root_path
        self.enable_entity_tracking = enable_entity_tracking
        self.relation_filter = relation_filter
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
                ImportExtractor(
                    relation_filter=self.relation_filter
                ),  # Pass filter for import classification
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

        Now includes parent_chunk_id generation for method-class linking.

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

        # Build class chunk_id lookup map for parent-child linking
        # Maps (relative_path, class_name) -> class_chunk_id
        # Classes are processed before their methods in tree traversal order
        class_chunk_map: Dict[Tuple[str, str], str] = {}

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

            # Compute relative_path for use in chunk_id and parent lookup
            relative_path = (
                str(path.relative_to(self.root_path)) if self.root_path else str(path)
            )

            # Generate chunk_id BEFORE creating CodeChunk (needed for parent lookup)
            chunk_id = self._create_chunk_id(
                relative_path,
                tchunk.start_line,
                tchunk.end_line,
                chunk_type,
                qualified_name,
            )

            # Track class chunks for parent-child linking
            if chunk_type == "class" and name:
                class_chunk_map[(relative_path, name)] = chunk_id

            # Determine parent_chunk_id for methods
            parent_chunk_id = None
            if parent_name and chunk_type in ("method", "function"):
                # Look up the enclosing class's chunk_id
                parent_chunk_id = class_chunk_map.get((relative_path, parent_name))

            # Create CodeChunk with parent_chunk_id
            chunk = CodeChunk(
                file_path=str(path),
                relative_path=relative_path,
                folder_structure=folder_parts,
                chunk_type=chunk_type,
                content=tchunk.content,
                start_line=tchunk.start_line,
                end_line=tchunk.end_line,
                name=name,
                parent_name=parent_name,
                parent_chunk_id=parent_chunk_id,
                docstring=docstring,
                decorators=decorators,
                imports=[],  # Tree-sitter doesn't extract imports yet
                complexity_score=tchunk.metadata.get("complexity_score", 0),
                tags=tags,
                language=tchunk.language,
            )

            # Assign chunk_id to the chunk
            chunk.chunk_id = chunk_id

            # Extract call graph relationships
            self._extract_call_relationships(chunk, tchunk, chunk_id)

            # Extract relationship edges
            self._extract_phase3_relationships(chunk, tchunk, chunk_id)

            code_chunks.append(chunk)

        # Propagate merge stats from TreeSitterChunk to CodeChunk
        # (ParallelChunker checks chunks[0]._merge_stats for logging)
        if tree_chunks and code_chunks and hasattr(tree_chunks[0], "_merge_stats"):
            code_chunks[0]._merge_stats = tree_chunks[0]._merge_stats

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
