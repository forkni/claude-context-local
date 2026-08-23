"""Multi-language chunker that combines AST and tree-sitter approaches."""

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from search.chunk_id import build as _build_chunk_id


if TYPE_CHECKING:
    from chunking.relationships.relation_filter import RepositoryRelationFilter

# Import utilities from new modules
from .dedent_utils import smart_dedent as _smart_dedent
from .language_registry import (
    DEFAULT_IGNORED_DIRS,
    LANGUAGE_NODE_TYPE_OVERRIDES,
    NODE_TYPE_MAP,
    SUPPORTED_EXTENSIONS,
)
from .python_ast_chunker import CodeChunk
from .tree_sitter import TreeSitterChunk, TreeSitterChunker


# Import call graph extractor for Python (also used to convert GLSL's plain
# metadata["calls"] pairs into CallEdge objects — see _extract_glsl_call_relationships).
# RelationshipEdge/RelationshipType are the analogous conversion target for GLSL's
# plain metadata["relationships"] dicts — see _extract_glsl_phase3_relationships.
try:
    from chunking.relationships.call_graph_extractor import (
        CallEdge,
        CallGraphExtractorFactory,
    )
    from chunking.relationships.edge_specs import EDGE_EMISSION_SPECS
    from chunking.relationships.relationship_extractors.registry import (
        ExtractorContext,
        build_relationship_extractors,
    )
    from chunking.relationships.relationship_types import (
        RelationshipEdge,
        RelationshipType,
    )

    CALL_GRAPH_AVAILABLE = True
except ImportError:
    CALL_GRAPH_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class _FailureTally:
    """Per-(extractor, exception type) failure count for one chunking pass."""

    count: int = 0
    first_chunk_id: str = ""
    first_message: str = ""


def _in_split_block_window(chunk: CodeChunk, line: int) -> bool:
    """Whether `line` falls within `chunk`'s own `[start_line, end_line]` window.

    A large GLSL function's `split_block` fragments all share the *same*
    `metadata["calls"]` / `metadata["relationships"]`: `_create_split_chunk`
    (chunking/languages/base.py) calls `extract_metadata` on the original,
    unsplit node for every fragment. Filtering by each fragment's own
    `[chunk.start_line, chunk.end_line]` here (rather than in `GLSLChunker`,
    which has no per-fragment context) is what keeps every split fragment
    from reporting the whole function's calls/relationships.

    Used by both `_extract_glsl_call_relationships` and
    `_extract_glsl_phase3_relationships` — previously duplicated inline in each.
    """
    return chunk.start_line <= line <= chunk.end_line


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
        *,
        include_exclusive: bool = False,
    ):
        """Initialize multi-language chunker.

        Args:
            root_path: Optional root path for relative path calculation
            include_dirs: Optional list of directories to include
            exclude_dirs: Optional list of directories to exclude
            enable_entity_tracking: Enable P4-5 entity extractors (enums, defaults, context managers). Default False.
            relation_filter: Optional RepositoryRelationFilter for import classification
            include_exclusive: Forwarded to PathFilter (via chunk_directory) — when
                True, every include pattern is treated as narrowing (whitelist-only),
                even ones that reach into a dependency tree. Kept in sync with the
                MerkleDAG/IncrementalIndexer filter so direct chunk_directory() callers
                see the same scope as the live index path.
        """
        self.root_path = root_path
        self.enable_entity_tracking = enable_entity_tracking
        self.relation_filter = relation_filter
        self.include_exclusive = include_exclusive
        # All languages, including Python, route through tree-sitter.
        # chunking/python_ast_chunker.py holds only the shared CodeChunk
        # dataclass — it is not a separate Python chunking path.
        self.tree_sitter_chunker = TreeSitterChunker()

        # Initialize directory filter for index-time filtering
        from search.filters import DirectoryFilter

        self.directory_filter = DirectoryFilter(include_dirs, exclude_dirs)

        # Per-thread extractor instances: call graph extractor and relationship
        # extractors carry mutable state (edges, AST context dicts) that races
        # under concurrent chunk_file() calls.  Each worker thread lazily builds
        # its own set of extractors on first use via _ensure_thread_extractors().
        self._local = threading.local()
        # Guards `_extractor_init_logged` below -- worker threads can race into
        # _ensure_thread_extractors() concurrently on their first chunk_file() call.
        self._extractor_log_lock = threading.Lock()
        self._extractor_init_logged = False
        # Guards `_extractor_failures` below -- worker threads can race into
        # _record_extractor_failure() concurrently. Instance-scoped (not
        # module-scoped) so two concurrent indexes on different projects can't
        # cross-contaminate each other's tallies. Mutated only in the `except`
        # branch of the extractor loop, a cold path, so the lock costs nothing
        # on the hot path.
        self._extractor_failure_lock = threading.Lock()
        self._extractor_failures: dict[tuple[str, str], _FailureTally] = {}
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
        include_exclusive: bool = False,
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
            include_exclusive=include_exclusive,
        )

    def _init_thread_extractors(self) -> None:
        """Build and store per-thread extractor instances on ``self._local``.

        Called once per thread (main thread in ``__init__``; worker threads on
        first ``chunk_file`` call via ``_ensure_thread_extractors``). Only the
        first call across all threads logs at INFO — one extractor set per
        worker thread is expected, not a per-file event, so repeating the same
        line once per thread (8x on a typical 8-worker index run) just reads
        as noise; later calls log the identical message at DEBUG instead.
        """
        with self._extractor_log_lock:
            first_init = not self._extractor_init_logged
            self._extractor_init_logged = True
        log = logger.info if first_init else logger.debug

        # Call graph extractor
        call_graph_extractor = None
        if CALL_GRAPH_AVAILABLE:
            try:
                call_graph_extractor = CallGraphExtractorFactory.create("python")
                log(
                    "Call graph extraction enabled for Python (thread-local); "
                    "GLSL calls are extracted inline via chunker metadata "
                    "instead (no separate extractor instance to log here)"
                )
            except Exception as e:  # noqa: BLE001 - resilience: call graph extraction is optional, degrade to None
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
                log(
                    f"Initialized {len(relationship_extractors)} relationship extractors "
                    f"(foundation + core + data models + entity tracking)"
                )
            else:
                log(
                    f"Initialized {len(relationship_extractors)} relationship extractors "
                    f"(foundation + core + data models; entity tracking disabled)"
                )
        except Exception as e:  # noqa: BLE001 - resilience: relationship extraction is optional, degrade to empty list
            logger.warning(
                f"Failed to initialize relationship extractors: {e}", exc_info=True
            )
        self._local.relationship_extractors = relationship_extractors

    def _ensure_thread_extractors(self) -> None:
        """Lazily initialize per-thread extractors for worker threads."""
        if not hasattr(self._local, "call_graph_extractor"):
            self._init_thread_extractors()

    def reset_extractor_failures(self) -> None:
        """Clear per-pass relationship-extractor failure tallies.

        Call before a chunking pass starts (``ParallelChunker.chunk_files``,
        ``chunk_directory``) so a second index in the same process -- or a
        retried full index -- never inherits stale counts from a prior pass.
        """
        with self._extractor_failure_lock:
            self._extractor_failures.clear()

    def log_extractor_failure_summary(self) -> None:
        """Emit one ``[REL_EXTRACT]`` line per (extractor, exception type)
        that failed during the pass. No-op when there were no failures.

        Call once, after the pass's chunking work has fully joined (e.g.
        after the ``ThreadPoolExecutor`` context manager exits), so the
        tally is final.
        """
        with self._extractor_failure_lock:
            failures = dict(self._extractor_failures)

        for (extractor_name, exc_name), tally in failures.items():
            logger.warning(
                f"[REL_EXTRACT] {extractor_name}: {tally.count} chunks failed "
                f"({exc_name}) — first: {tally.first_chunk_id}: {tally.first_message}"
            )

    def _record_extractor_failure(
        self, extractor: object, exc: Exception, chunk_id: str
    ) -> None:
        """Record one extractor's failure and log it per the escalation policy.

        | occurrence                       | level                        |
        |-----------------------------------|-------------------------------|
        | 1st per (extractor, exc type)     | WARNING, with traceback       |
        | 2nd-3rd                           | WARNING, single line          |
        | 4th+                              | DEBUG, tallied only           |
        | any "recursion depth mismatch"    | DEBUG always, still counted   |

        The recursion-depth-mismatch case mirrors the CPython 3.11.0-3.11.3
        AST limitation special-cased in the outer handler of
        ``_extract_phase3_relationships`` -- if an extractor hits the same
        bug independently (e.g. via its own recursive AST walk), it stays at
        DEBUG here too rather than newly surfacing as a WARNING now that
        isolation lets each extractor fail on its own.
        """
        extractor_name = type(extractor).__name__
        exc_name = type(exc).__name__
        key = (extractor_name, exc_name)
        is_recursion_bug = "recursion depth mismatch" in str(exc)

        with self._extractor_failure_lock:
            tally = self._extractor_failures.setdefault(key, _FailureTally())
            tally.count += 1
            if tally.count == 1:
                tally.first_chunk_id = chunk_id
                tally.first_message = str(exc)
            occurrence = tally.count

        if is_recursion_bug:
            logger.debug(
                f"Skipping {extractor_name} for {chunk_id} (Python 3.11 AST limitation)"
            )
        elif occurrence == 1:
            logger.warning(
                f"{extractor_name} failed for {chunk_id}: {exc}", exc_info=True
            )
        elif occurrence <= 3:
            logger.warning(f"{extractor_name} failed for {chunk_id}: {exc}")
        else:
            logger.debug(f"{extractor_name} failed for {chunk_id}: {exc}")

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
            # Workstream C3: this branch does not fire on the production
            # path — every caller (parallel_chunker.py, incremental_indexer
            # via _get_supported_files) pre-filters with is_supported()
            # before calling chunk_file(), so the debug log that used to
            # live here never printed. Kept as a defensive early return for
            # any caller that skips the pre-filter (e.g. direct test calls).
            return []

        max_file_size_bytes = self._max_file_size_bytes()
        if max_file_size_bytes is not None:
            try:
                file_size = os.path.getsize(file_path)
            except OSError as e:
                logger.warning(f"Could not stat {file_path}, skipping: {e}")
                return []
            if file_size > max_file_size_bytes:
                logger.info(
                    f"Skipping {file_path}: {file_size:,}B exceeds "
                    f"max_file_size_bytes cap ({max_file_size_bytes:,}B)"
                )
                return []

        # Use tree-sitter for all  languages
        try:
            tree_chunks = self.tree_sitter_chunker.chunk_file(file_path)
            # Convert TreeSitterChunk to CodeChunk
            return self._convert_tree_chunks(tree_chunks, file_path)
        except Exception as e:
            logger.error(f"Failed to chunk file {file_path}: {e}", exc_info=True)
            return []

    def _max_file_size_bytes(self) -> int | None:
        """Read ``ChunkingConfig.max_file_size_bytes``, or ``None`` if the search
        config is unavailable (e.g. in isolated unit tests).

        Lazily imported -- mirrors ``chunking/languages/base.py``'s
        ``_get_chunking_config`` -- to avoid a ``search.config`` <-> ``chunking``
        import cycle.
        """
        from search.config import get_chunking_config

        chunking_config = get_chunking_config()
        return chunking_config.max_file_size_bytes if chunking_config else None

    def _map_node_type(
        self,
        node_type: str,
        parent_name: str | None,
        parent_type: str | None = None,
        language: str | None = None,
    ) -> str:
        """Map tree-sitter node type to chunk type.

        Args:
            node_type: Tree-sitter node type
            parent_name: Parent class name (if any)
            parent_type: Kind of the enclosing container ("class", "namespace",
                or None for no container) -- distinguishes a class member from
                a namespace-scoped free function so the latter isn't promoted
                to "method". Defaults to None, which preserves pre-v0.24
                behaviour (promote whenever parent_name is truthy).
            language: Chunk's language, used to look up
                LANGUAGE_NODE_TYPE_OVERRIDES before falling back to the
                global NODE_TYPE_MAP -- needed because some languages map the
                same node_type to different chunk types (e.g. cpp's
                `declaration` is a function, GLSL's is not).

        Returns:
            Mapped chunk type (function, method, class, etc.)
        """
        # Get base chunk type from mapping -- language-scoped override first,
        # then the global mapping.
        overrides = LANGUAGE_NODE_TYPE_OVERRIDES.get(language, {}) if language else {}
        if node_type in overrides:
            chunk_type = overrides[node_type]
        else:
            chunk_type = self.NODE_TYPE_MAP.get(node_type, node_type)

        # A function directly inside a class (or a language with no
        # container-type distinction, i.e. parent_type is None) is a method.
        # A function inside a namespace stays a function.
        if parent_name and chunk_type == "function" and parent_type in (None, "class"):
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
          - "shader" : GLSL shader files (.glsl/.frag/.vert/.comp/.geom/.tesc/.tese/.glslinc)
          - "src"    : everything else (implementation code)

        Args:
            relative_path: File path relative to project root

        Returns:
            One of "src", "test", "doc", "config", "shader"
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

        # Shader files — kept in sync with EXT_TO_LANGUAGE's "glsl" entries
        # (language_registry.py); not imported from there since this
        # function otherwise inlines its category extensions literally.
        if ext in (
            ".glsl",
            ".frag",
            ".vert",
            ".comp",
            ".geom",
            ".tesc",
            ".tese",
            ".glslinc",
        ):
            return "shader"

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
        if metadata.get("has_builtin_vars"):
            tags.append("builtin-vars")
        if metadata.get("has_texture_ops"):
            tags.append("texture-ops")
        if metadata.get("has_math_ops"):
            tags.append("math-ops")

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
        self,
        chunk: CodeChunk,
        tchunk: TreeSitterChunk,
        chunk_id: str,
        dedented_content: str | None = None,
    ) -> None:
        """Extract call graph relationships.

        Args:
            chunk: CodeChunk to populate with call relationships
            tchunk: Tree-sitter chunk with source code
            chunk_id: Chunk identifier for logging
            dedented_content: Pre-computed ``_smart_dedent(tchunk.content)``, shared
                with ``_extract_phase3_relationships`` so identical content isn't
                dedented twice per chunk. Computed lazily when None (e.g. direct
                unit-test callers).
        """
        if tchunk.language == "python":
            self._ensure_thread_extractors()
            call_graph_extractor = self._local.call_graph_extractor
            if call_graph_extractor is None or chunk.chunk_type not in (
                "function",
                "method",
                "decorated_definition",
                "split_block",
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
                    "file_path": getattr(chunk, "file_path", None)
                    or chunk.relative_path,
                    "name": chunk.name,
                    "chunk_type": chunk.chunk_type,
                    "parent_class": chunk.parent_name,
                }
                # Extract function calls from this chunk
                if dedented_content is None:
                    dedented_content = _smart_dedent(tchunk.content)
                calls = call_graph_extractor.extract_calls(
                    dedented_content, chunk_metadata
                )
                chunk.calls = calls

                if calls:
                    logger.debug(f"Extracted {len(calls)} calls from {chunk_id}")
            except Exception as e:  # noqa: BLE001 - parse-recovery: AST parsing of chunk content can fail (e.g. Python 3.11 recursion bug), skip this chunk
                # Handle AST recursion depth limitation in Python 3.11.0-3.11.3
                if "recursion depth mismatch" in str(e):
                    logger.debug(
                        f"Skipping call extraction for {chunk.name} (Python 3.11 AST bug)"
                    )
                else:
                    logger.warning(
                        f"Failed to extract calls for {chunk.name}: {e}", exc_info=True
                    )
        elif tchunk.language == "glsl" and CALL_GRAPH_AVAILABLE:
            self._extract_glsl_call_relationships(chunk, tchunk, chunk_id)

    def _extract_glsl_call_relationships(
        self, chunk: CodeChunk, tchunk: TreeSitterChunk, chunk_id: str
    ) -> None:
        """Convert GLSLChunker's metadata["calls"] pairs into CallEdge objects.

        `GLSLChunker.extract_metadata` (chunking/languages/glsl.py) already
        walks `call_expression` nodes and filters builtins, type
        constructors, and (by default) TD-prefixed globals at parse time —
        this just materializes the surviving `(callee_name, line_number)`
        pairs into `CallEdge`s, with no re-parse and no
        `chunking/relationships/` import inside the language chunker.

        `metadata["calls"]` is only set for `function_definition` nodes
        (see `GLSLChunker._extract_call_metadata`), so only "function" and
        "split_block" chunk types can carry it — GLSL has no methods or
        decorators, so the allowlist is narrower than Python's.

        See `_in_split_block_window` for why every candidate call is also
        filtered by the chunk's own line range.

        Args:
            chunk: CodeChunk to populate with call relationships.
            tchunk: Tree-sitter chunk carrying GLSLChunker's metadata.
            chunk_id: Chunk identifier, becomes CallEdge.caller_id.
        """
        spec = EDGE_EMISSION_SPECS["glsl"]
        raw_calls = tchunk.metadata.get("calls")
        if raw_calls is None or chunk.chunk_type not in spec.call_chunk_types:
            return

        chunk.calls = [
            CallEdge(
                caller_id=chunk_id,
                callee_name=name,
                line_number=line,
                is_method_call=False,
                confidence=spec.call_confidence,
                callee_qualified=None,
            )
            for name, line in raw_calls
            if _in_split_block_window(chunk, line)
        ]
        if chunk.calls:
            logger.debug(f"Extracted {len(chunk.calls)} calls from {chunk_id}")

    def _extract_glsl_phase3_relationships(
        self, chunk: CodeChunk, tchunk: TreeSitterChunk, chunk_id: str
    ) -> None:
        """Convert GLSLChunker's metadata["relationships"] dicts into RelationshipEdge objects.

        Mirrors `_extract_glsl_call_relationships`: `GLSLChunker.extract_metadata`
        (chunking/languages/glsl.py) already walks the parse tree and classifies
        each relationship (imports, uses_type, instantiates, defines_field,
        defines_constant) at parse time — this just materializes the surviving
        plain dicts into `RelationshipEdge` objects, with no re-parse and no
        `chunking/relationships/` import inside the language chunker.

        Unlike calls, GLSL relationships originate from several chunk types
        (function/split_block for uses_type+instantiates, struct/union/enum for
        defines_field+uses_type, declaration/macro for defines_constant, include
        for imports) — so there is no single chunk_type allowlist here; presence
        of `metadata["relationships"]` is the only gate.

        See `_in_split_block_window` for why every candidate relationship is
        also filtered by the chunk's own line range.

        Args:
            chunk: CodeChunk to populate with relationship edges.
            tchunk: Tree-sitter chunk carrying GLSLChunker's metadata.
            chunk_id: Chunk identifier, becomes RelationshipEdge.source_id.
        """
        raw_relationships = tchunk.metadata.get("relationships")
        if not raw_relationships:
            return

        relationships: list[RelationshipEdge] = []
        for rel in raw_relationships:
            line = rel.get("line_number", 0)
            if not _in_split_block_window(chunk, line):
                continue
            try:
                relationships.append(
                    RelationshipEdge(
                        source_id=chunk_id,
                        target_name=rel.get("target_name", "unknown"),
                        relationship_type=RelationshipType(
                            rel.get("relationship_type", "calls")
                        ),
                        line_number=line,
                        metadata=rel.get("metadata", {}),
                    )
                )
            except (ValueError, KeyError, TypeError) as e:
                logger.debug(
                    f"Skipping malformed GLSL relationship dict for {chunk_id}: {e}"
                )

        if relationships:
            chunk.relationships = relationships
            logger.debug(
                f"Extracted {len(relationships)} relationships from {chunk_id}"
            )

    def _extract_phase3_relationships(
        self,
        chunk: CodeChunk,
        tchunk: TreeSitterChunk,
        chunk_id: str,
        dedented_content: str | None = None,
    ) -> None:
        """Extract relationship edges (inheritance, types, etc.).

        Args:
            chunk: CodeChunk to populate with relationships
            tchunk: Tree-sitter chunk with source code
            chunk_id: Chunk identifier for logging
            dedented_content: Pre-computed ``_smart_dedent(tchunk.content)``, shared
                with ``_extract_call_relationships`` so identical content isn't
                dedented twice per chunk. Computed lazily when None (e.g. direct
                unit-test callers).
        """
        if tchunk.language == "glsl" and CALL_GRAPH_AVAILABLE:
            self._extract_glsl_phase3_relationships(chunk, tchunk, chunk_id)
            return
        if tchunk.language != "python":
            return

        self._ensure_thread_extractors()
        relationship_extractors = self._local.relationship_extractors
        if not relationship_extractors:
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
            # Use smart_dedent to properly dedent nested code (shared with
            # _extract_call_relationships via the caller-supplied dedented_content).
            if dedented_content is None:
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
                    try:
                        edges = extractor.extract_from_tree(
                            ast_tree, dedented_content, chunk_metadata
                        )
                    except Exception as exc:  # noqa: BLE001 - per-extractor isolation: one extractor raising must cost only its own edges; the other 15 still contribute and chunk.relationships is still assigned below
                        self._record_extractor_failure(extractor, exc, chunk_id)
                        continue
                    all_relationships.extend(edges)

            chunk.relationships = all_relationships

            if all_relationships:
                logger.debug(
                    f"Extracted {len(all_relationships)} relationships from {chunk_id}"
                )
        except Exception as e:  # noqa: BLE001 - parse-recovery: AST parsing of chunk content can fail (e.g. Python 3.11 recursion bug), skip this chunk
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

    @staticmethod
    def _resolve_parent_chunk_id(
        spans: list[tuple[int, int, str]] | None, start_line: int
    ) -> str | None:
        """Resolve the innermost enclosing container span for a child chunk.

        `spans` is every same-named container chunk registered so far (see
        `class_chunk_map` in `_convert_tree_chunks`), in traversal order.
        Among those whose line range contains `start_line`, picks the one
        with the greatest `start_line` -- the most deeply nested, i.e.
        innermost, enclosing match. This is what disambiguates same-named
        nested containers (e.g. a reopened C++ namespace) instead of always
        returning whichever container was registered last.

        Falls back to the last-registered span when none contains
        `start_line`: Python's `split_block` chunks can truncate a class's
        own recorded span short of a method's actual line (the class header
        chunk ends before the method starts), so a strict containment
        requirement would silently drop `parent_chunk_id` for that
        pre-existing, non-colliding case. This fallback keeps that case
        exactly as it behaved before this fix.

        Args:
            spans: (start_line, end_line, chunk_id) tuples for every chunk
                registered under the same (relative_path, name) key so far,
                or None if no container with that name has been seen.
            start_line: The child chunk's start line.

        Returns:
            The resolved parent chunk_id, or None if `spans` is empty/None.
        """
        if not spans:
            return None
        enclosing = [span for span in spans if span[0] <= start_line <= span[1]]
        if enclosing:
            return max(enclosing, key=lambda span: span[0])[2]
        return spans[-1][2]

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
        # Maps (relative_path, class_name) -> list of (start_line, end_line,
        # chunk_id) spans, in traversal order. Classes are processed before
        # their methods in tree traversal order.
        #
        # This was a flat (relative_path, class_name) -> chunk_id dict until
        # PR #57 review surfaced a collision: same-named nested containers
        # (most reachable via C++ namespaces reopened at different nesting
        # depths, e.g. `namespace A { namespace A { void f(); } void g(); }`)
        # silently resolved every lookup to whichever container was
        # registered *last* in traversal order -- last-write-wins, not
        # innermost-enclosing. `g`'s real parent is the outer `A`, but once
        # the inner `A` is visited a flat dict's lookup returns the inner
        # namespace's chunk_id for every subsequent same-named lookup,
        # including `g`'s. Storing every same-named span and resolving via
        # `_resolve_parent_chunk_id` (innermost span whose range contains the
        # child, by start_line) fixes this while leaving every
        # non-colliding case -- the overwhelming majority -- unchanged.
        class_chunk_map: dict[tuple[str, str], list[tuple[int, int, str]]] = {}

        for tchunk in tree_chunks:
            # Extract metadata
            name = tchunk.metadata.get("name")
            docstring = tchunk.metadata.get("docstring")
            decorators = tchunk.metadata.get("decorators", [])

            # Extract parent class from chunk (prefer explicit field, fallback to metadata)
            parent_name = tchunk.parent_class or tchunk.metadata.get("parent_name")
            parent_type = tchunk.metadata.get("parent_type")

            # Map node type to chunk type (handles parent class logic)
            chunk_type = self._map_node_type(
                tchunk.node_type, parent_name, parent_type, tchunk.language
            )

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

            # Track class/struct/union (and namespace) chunks for
            # parent-child linking. Namespace-scoped free functions carry
            # parent_type="namespace" (base.py's container traversal) and
            # stay chunk_type "function" rather than being promoted to
            # "method" -- registering the namespace chunk here lets the
            # parent_chunk_id lookup below resolve for them instead of
            # dead-ending. "struct"/"union" were added alongside C++ header
            # parity, which made `struct_specifier`/`union_specifier`
            # containers -- before that, struct/union members never chunked
            # separately, so this gap was unreachable.
            if chunk_type in ("class", "struct", "union", "namespace") and name:
                class_chunk_map.setdefault((relative_path, name), []).append(
                    (tchunk.start_line, tchunk.end_line, chunk_id)
                )

            # Determine parent_chunk_id for methods
            parent_chunk_id = None
            if parent_name and chunk_type in ("method", "function"):
                # Look up the enclosing class's chunk_id (innermost span
                # containing this chunk, among same-named containers)
                parent_chunk_id = self._resolve_parent_chunk_id(
                    class_chunk_map.get((relative_path, parent_name)),
                    tchunk.start_line,
                )

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

            # Dedent once and share between call-graph and phase-3 relationship
            # extraction — both operate on identical Python source (perf: dedent-once).
            dedented_content = (
                _smart_dedent(tchunk.content) if tchunk.language == "python" else None
            )

            # Extract call graph relationships
            self._extract_call_relationships(chunk, tchunk, chunk_id, dedented_content)

            # Extract relationship edges
            self._extract_phase3_relationships(
                chunk, tchunk, chunk_id, dedented_content
            )

            # GLSL's IMPORTS edges (from #include) are the only relationship
            # type that also populates CodeChunk.imports. The general
            # "imports=[] for every tree-sitter language" gap above predates
            # this and is left alone here — flipping it for Python too would
            # change _build_file_summary's "# Imports:" section for every
            # Python file, which needs its own before/after review, not a
            # GLSL-scoped one.
            if tchunk.language == "glsl" and chunk.relationships:
                chunk.imports = [
                    rel.target_name
                    for rel in chunk.relationships
                    if rel.relationship_type == RelationshipType.IMPORTS
                ]

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

        Note:
            No production caller uses this method (both live index paths go
            through ``ParallelChunker.chunk_files`` instead, which wires the
            same reset/flush around ``_chunk_files_parallel`` /
            ``_add_new_chunks``). The reset/flush calls here exist for API
            completeness so a direct caller still gets a correct, non-leaking
            ``[REL_EXTRACT]`` summary.
        """
        all_chunks = []
        self.reset_extractor_failures()
        dir_path = Path(directory_path)

        if not dir_path.exists() or not dir_path.is_dir():
            logger.error(f"Directory does not exist: {directory_path}")
            return []

        # Use provided extensions or all supported
        if extensions:
            valid_extensions = set(extensions) & self.SUPPORTED_EXTENSIONS
        else:
            valid_extensions = self.SUPPORTED_EXTENSIONS

        # Collect all file paths, applying the single include/exclude/default
        # precedence resolver (PathFilter) — replaces the old two-stage
        # basename-ignore + strict-mode DirectoryFilter check, which could not
        # let an include_dirs pattern override a default-ignored directory
        # (e.g. "venv", "site-packages"). Relative paths are computed against
        # self.root_path when set (so a chunk_directory call scanning a
        # subdirectory, e.g. an include_dirs target, still resolves patterns
        # against the project root) and fall back to the scan directory
        # itself otherwise.
        from search.filters import PathFilter

        effective_root = Path(self.root_path) if self.root_path else dir_path
        path_filter = PathFilter(
            self.directory_filter.include_dirs,
            self.directory_filter.exclude_dirs,
            effective_root,
            include_exclusive=self.include_exclusive,
        )

        file_paths = []
        skipped = 0
        for ext in valid_extensions:
            for file_path in dir_path.rglob(f"*{ext}"):
                try:
                    relative_path = str(file_path.relative_to(effective_root))
                except ValueError:
                    # File not under the effective root; skip it.
                    skipped += 1
                    continue
                if path_filter.should_index_file(relative_path):
                    file_paths.append(file_path)
                else:
                    skipped += 1

        for unmatched in path_filter.unmatched_patterns():
            logger.warning(f"Directory filter pattern matched 0 files: {unmatched!r}")

        logger.info(f"Found {len(file_paths)} files to chunk ({skipped} filtered out)")

        # Process files in parallel or sequentially
        if enable_parallel and len(file_paths) > 1:
            all_chunks = self._chunk_files_parallel(file_paths, max_workers)
        else:
            all_chunks = self._chunk_files_sequential(file_paths)

        logger.info(f"Total chunks from directory: {len(all_chunks)}")
        self.log_extractor_failure_summary()
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
            except Exception as e:  # noqa: BLE001 - parse-recovery: one file failing to chunk shouldn't abort the whole batch
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
                except Exception as e:  # noqa: BLE001 - parse-recovery: one file failing to chunk shouldn't abort the whole batch
                    logger.warning(f"Failed to chunk {file_path}: {e}", exc_info=True)

        return all_chunks
