"""Multi-language chunker that combines AST and tree-sitter approaches."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from search.chunk_id import build as _build_chunk_id


if TYPE_CHECKING:
    from chunking.relationships.relation_filter import RepositoryRelationFilter

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
    from chunking.relationships.call_graph_extractor import CallGraphExtractorFactory
    from chunking.relationships.relationship_extractors.registry import (
        ExtractorContext,
        build_relationship_extractors,
    )

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
        root_path: str | None = None,
        include_dirs: list | None = None,
        exclude_dirs: list | None = None,
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
        # Use AST chunker for Python (chunking/python_ast_chunker.py — more mature).
        # Use tree-sitter for all other languages.
        self.tree_sitter_chunker = TreeSitterChunker()

        # Initialize directory filter for index-time filtering
        from search.filters import DirectoryFilter

        self.directory_filter = DirectoryFilter(include_dirs, exclude_dirs)

        # Per-thread extractor instances: call graph extractor and relationship
        # extractors carry mutable state (edges, AST context dicts) that races
        # under concurrent chunk_file() calls.  Each worker thread lazily builds
        # its own set of extractors on first use via _ensure_thread_extractors().
        self._local = threading.local()
        # Pre-populate the main thread's slot so callers on the main thread never
        # trigger a lazy-init on the hot path.
        self._init_thread_extractors()

    @classmethod
    def for_project(
        cls,
        root_path: str,
        include_dirs: list | None = None,
        exclude_dirs: list | None = None,
        *,
        enable_entity_tracking: bool = False,
    ) -> "MultiLanguageChunker":
        """Build a project chunker with import classification wired in.

        Single owner of the RepositoryRelationFilter construction so every live
        index path classifies import edges (stdlib/builtin/third_party/local)
        instead of leaving them as ``"unknown"`` — which defeats ego-graph
        stdlib/third-party import exclusion in
        ``graph/graph_storage.py:_should_exclude_edge``.

        Always prefer this over the bare constructor when chunking a real
        project on disk. Use the bare constructor only when ``project_root``
        is unavailable (e.g. in-memory test fixtures, the rootless
        ``IncrementalIndexer.__init__`` chunker fallback).
        """
        from chunking.relationships.relation_filter import RepositoryRelationFilter

        relation_filter = RepositoryRelationFilter(project_root=Path(root_path))
        return cls(
            root_path,
            include_dirs,
            exclude_dirs,
            enable_entity_tracking=enable_entity_tracking,
            relation_filter=relation_filter,
        )

    def _init_thread_extractors(self) -> None:
        """Build and store per-thread extractor instances on ``self._local``.

        Called once per thread (main thread in ``__init__``; worker threads on
        first ``chunk_file`` call via ``_ensure_thread_extractors``).
        """
        # Call graph extractor
        call_graph_extractor = None
        if CALL_GRAPH_AVAILABLE:
            try:
                call_graph_extractor = CallGraphExtractorFactory.create("python")
                logger.info("Call graph extraction enabled for Python (thread-local)")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize call graph extractor: {e}", exc_info=True
                )
        self._local.call_graph_extractor = call_graph_extractor

        # Relationship extractors
        relationship_extractors: list = []
        try:
            ctx = ExtractorContext(relation_filter=self.relation_filter)
            relationship_extractors = build_relationship_extractors(
                ctx, enable_entity_tracking=self.enable_entity_tracking
            )
            if self.enable_entity_tracking:
                logger.info(
                    f"Initialized {len(relationship_extractors)} relationship extractors "
                    f"(foundation + core + data models + entity tracking)"
                )
            else:
                logger.info(
                    f"Initialized {len(relationship_extractors)} relationship extractors "
                    f"(foundation + core + data models; entity tracking disabled)"
                )
        except Exception as e:
            logger.warning(
                f"Failed to initialize relationship extractors: {e}", exc_info=True
            )
        self._local.relationship_extractors = relationship_extractors

    def _ensure_thread_extractors(self) -> None:
        """Lazily initialize per-thread extractors for worker threads."""
        if not hasattr(self._local, "call_graph_extractor"):
            self._init_thread_extractors()

    def is_supported(self, file_path: str) -> bool:
        """Check if file type is supported.

        Args:
            file_path: Path to file

        Returns:
            True if file type is supported
        """
        suffix = Path(file_path).suffix.lower()
        return suffix in self.SUPPORTED_EXTENSIONS

    def chunk_file(self, file_path: str) -> list[CodeChunk]:
        """Chunk a file into semantic units.

        Args:
            file_path: Path to the file

        Returns:
            List of CodeChunk objects
        """
        if not self.is_supported(file_path):
            logger.debug(f"File type not supported: {file_path}")
            return []

        # Use tree-sitter for all  languages
        try:
            tree_chunks = self.tree_sitter_chunker.chunk_file(file_path)
            # Convert TreeSitterChunk to CodeChunk
            return self._convert_tree_chunks(tree_chunks, file_path)
        except Exception as e:
            logger.error(f"Failed to chunk file {file_path}: {e}", exc_info=True)
            return []

    def _map_node_type(self, node_type: str, parent_name: str | None) -> str:
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

    def _build_folder_structure(self, file_path: str) -> list[str]:
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

    @staticmethod
    def _classify_file_role(relative_path: str) -> str:
        """Classify a file's role for search boosting (ConDB file-role tagging).

        Categories:
          - "test"   : files in test/tests directories or named test_*.py / *_test.py
          - "doc"    : markdown/rst/txt files or files under docs/ directories
          - "config" : project configuration files (pyproject.toml, Dockerfile, etc.)
          - "src"    : everything else (implementation code)

        Args:
            relative_path: File path relative to project root

        Returns:
            One of "src", "test", "doc", "config"
        """
        parts = Path(relative_path).parts
        name = Path(relative_path).name.lower()
        ext = Path(relative_path).suffix.lower()

        # Test files
        if any(
            p.lower() in ("test", "tests", "testing", "__tests__", "spec", "specs")
            for p in parts
        ):
            return "test"
        if (
            name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith(".spec.py")
        ):
            return "test"

        # Documentation files
        if any(p.lower() in ("docs", "doc", "documentation", "wiki") for p in parts):
            return "doc"
        if ext in (".md", ".rst", ".txt", ".adoc"):
            return "doc"

        # Config/infrastructure files
        config_names = {
            "setup.py",
            "setup.cfg",
            "pyproject.toml",
            "poetry.lock",
            "requirements.txt",
            "requirements-dev.txt",
            "dockerfile",
            ".gitignore",
            ".gitattributes",
            ".editorconfig",
            "makefile",
            "tox.ini",
            "pytest.ini",
            ".flake8",
            ".pylintrc",
            "mypy.ini",
            ".env",
            ".env.example",
            ".env.local",
            ".env.production",
        }
        if name in config_names or ext in (".yaml", ".yml", ".toml", ".cfg", ".ini"):
            return "config"

        return "src"

    def _extract_semantic_tags(self, metadata: dict, language: str) -> list[str]:
        """Extract semantic tags from chunk metadata.

        Args:
            metadata: Chunk metadata dictionary
            language: Programming language

        Returns:
            List of semantic tags (async, generator, export, role:xxx, etc.)
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

        # Add file-role tag (ConDB insight: src/test/doc/config classification)
        relative_path = metadata.get("relative_path", "")
        if relative_path:
            role = self._classify_file_role(relative_path)
            tags.append(f"role:{role}")

        return tags

    def _create_chunk_id(
        self,
        relative_path: str,
        start_line: int,
        end_line: int,
        chunk_type: str,
        qualified_name: str | None,
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
        # Route through the canonical wire-format builder (P5: chunk_id.build).
        return _build_chunk_id(
            str(relative_path), start_line, end_line, chunk_type, qualified_name or None
        )

    def _extract_call_relationships(
        self, chunk: CodeChunk, tchunk: TreeSitterChunk, chunk_id: str
    ) -> None:
        """Extract call graph relationships.

        Args:
            chunk: CodeChunk to populate with call relationships
            tchunk: Tree-sitter chunk with source code
            chunk_id: Chunk identifier for logging
        """
        self._ensure_thread_extractors()
        call_graph_extractor = self._local.call_graph_extractor
        if (
            call_graph_extractor is None
            or tchunk.language != "python"
            or chunk.chunk_type
            not in ("function", "method", "decorated_definition", "split_block")
        ):
            return

        try:
            chunk_metadata = {
                "chunk_id": chunk_id,
                # Prefer the absolute file_path (set by _convert_to_code_chunks)
                # so import_resolver.read_file_imports can open the file regardless
                # of the process CWD (#8).  Fall back to relative_path when the
                # chunk was constructed without file_path (e.g. in unit tests that
                # use CodeChunk.__new__ to avoid the full constructor).
                "file_path": getattr(chunk, "file_path", None) or chunk.relative_path,
                "name": chunk.name,
                "chunk_type": chunk.chunk_type,
                "parent_class": chunk.parent_name,
            }
            # Extract function calls from this chunk
            calls = call_graph_extractor.extract_calls(
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
                logger.warning(
                    f"Failed to extract calls for {chunk.name}: {e}", exc_info=True
                )

    def _extract_phase3_relationships(
        self, chunk: CodeChunk, tchunk: TreeSitterChunk, chunk_id: str
    ) -> None:
        """Extract relationship edges (inheritance, types, etc.).

        Args:
            chunk: CodeChunk to populate with relationships
            tchunk: Tree-sitter chunk with source code
            chunk_id: Chunk identifier for logging
        """
        self._ensure_thread_extractors()
        relationship_extractors = self._local.relationship_extractors
        if tchunk.language != "python" or not relationship_extractors:
            return

        try:
            chunk_metadata = {
                "chunk_id": chunk_id,
                # Prefer the absolute file_path (set by _convert_to_code_chunks)
                # so import_resolver.read_file_imports can open the file regardless
                # of the process CWD (#8).  Fall back to relative_path when the
                # chunk was constructed without file_path (e.g. in unit tests that
                # use CodeChunk.__new__ to avoid the full constructor).
                "file_path": getattr(chunk, "file_path", None) or chunk.relative_path,
                "name": chunk.name,
                "chunk_type": chunk.chunk_type,
                "parent_class": chunk.parent_name,
            }

            all_relationships = []
            # Use smart_dedent to properly dedent nested code
            dedented_content = _smart_dedent(tchunk.content)

            # split_block bodies may be syntactically incomplete (dangling else/except).
            # Restrict extraction to the signature portion, which is always valid Python.
            if chunk.chunk_type == "split_block":
                marker_pos = dedented_content.find("# ... (split block)")
                if marker_pos != -1:
                    dedented_content = (
                        dedented_content[:marker_pos].rstrip() + "\n    pass\n"
                    )

            # Parse once; each extractor receives the shared tree via extract_from_tree
            # (avoids 13–16× redundant ast.parse per chunk, #15).
            try:
                import ast as _ast

                ast_tree = _ast.parse(dedented_content)
            except SyntaxError as _syn_err:
                # DEBUG: Method chunks often fail to parse standalone
                logger.debug(f"[REL] SyntaxError in {chunk_id}: {_syn_err}")
                ast_tree = None

            if ast_tree is not None:
                for extractor in relationship_extractors:
                    edges = extractor.extract_from_tree(
                        ast_tree, dedented_content, chunk_metadata
                    )
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
                logger.warning(
                    f"Failed to extract relationships for {chunk.name}: {e}",
                    exc_info=True,
                )

    def _convert_tree_chunks(
        self, tree_chunks: list[TreeSitterChunk], file_path: str
    ) -> list[CodeChunk]:
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
        class_chunk_map: dict[tuple[str, str], str] = {}

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
        extensions: list[str] | None = None,
        enable_parallel: bool = True,
        max_workers: int = 4,
    ) -> list[CodeChunk]:
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
                # Skip common large/build/tooling directories.
                # Scope the check to components *relative to the scan root*
                # so ancestor directories named "build", "env", etc. don't
                # suppress the entire project (#12).
                try:
                    rel_parts = file_path.relative_to(dir_path).parts
                except ValueError:
                    rel_parts = file_path.parts
                if any(part in self.DEFAULT_IGNORED_DIRS for part in rel_parts):
                    continue
                file_paths.append(file_path)

        # Apply custom directory filters (include_dirs/exclude_dirs)
        if self.root_path and self.directory_filter:
            root = Path(self.root_path)
            filtered_paths = []
            for file_path in file_paths:
                try:
                    relative_path = str(file_path.relative_to(root))
                    # Use strict mode for file filtering (no ancestor passthrough)
                    if self.directory_filter.matches_for_file(relative_path):
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

    def _chunk_files_sequential(self, file_paths: list[Path]) -> list[CodeChunk]:
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
                logger.warning(f"Failed to chunk {file_path}: {e}", exc_info=True)
        return all_chunks

    def _chunk_files_parallel(
        self, file_paths: list[Path], max_workers: int
    ) -> list[CodeChunk]:
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
                    logger.warning(f"Failed to chunk {file_path}: {e}", exc_info=True)

        return all_chunks
