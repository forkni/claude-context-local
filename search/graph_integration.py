"""Graph integration layer for call graph storage operations."""

import ast
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, NamedTuple


# Import graph storage for call graph
try:
    from graph.graph_storage import CodeGraphStorage

    GRAPH_STORAGE_AVAILABLE = True
except ImportError:
    GRAPH_STORAGE_AVAILABLE = False
    CodeGraphStorage = None

from chunking.relationships.relationship_types import RelationshipEdge, RelationshipType
from search.chunk_id import is_chunk_id as _is_chunk_id


def is_chunk_id(node_id: str) -> bool:
    """Check if a graph node ID is a real chunk ID (not a bare symbol name).

    Real chunk IDs have format: "file.py:10-20:function:name" (3+ colons).
    Symbol names: "Exception", "login" (0-2 colons).

    Args:
        node_id: Graph node identifier to check

    Returns:
        True if node_id is a valid chunk ID, False if it's a bare symbol
    """
    return _is_chunk_id(node_id)


# Semantic chunk types that can have relationships
# Based on Codanna's approach: index ALL semantic symbols
SEMANTIC_TYPES = (
    "function",
    "method",
    "decorated_definition",
    "class",
    "struct",
    "interface",
    "enum",
    "trait",
    "impl",
    "constant",
    "variable",
    "merged",  # Community-merged chunks from Louvain detection
    "split_block",  # Large node split blocks (AST block splitting)
)

# Common Python method/attribute names that are almost certainly stdlib
# or built-in targets when the project itself does not define them.
# We drop these ONLY when `name_to_chunk_ids` has no matching project chunk.
# If the project defines its own `get`, `format`, etc., the edge is kept.
_COMMON_METHODS: frozenset[str] = frozenset(
    {
        "append",
        "extend",
        "get",
        "items",
        "keys",
        "values",
        "split",
        "join",
        "strip",
        "replace",
        "format",
        "lower",
        "upper",
    }
)


class _BuildSpec(NamedTuple):
    """Normalised, input-type-agnostic spec for a single chunk in a two-pass build.

    Produced by :meth:`GraphIntegration._make_spec_from_embedding` and
    :meth:`GraphIntegration._make_spec_from_chunk`; consumed by
    :meth:`GraphIntegration._two_pass_build`.  All fields are already resolved
    to the types that the graph-storage API expects — no isinstance checks or
    dict-vs-object branches inside the builder.
    """

    chunk_id: str
    name: str  # "unknown" when the original was missing/empty
    chunk_type: str
    file_path: str
    language: str
    parent_name: str | None
    calls: list  # list[dict]: callee_name, line_number, is_method_call
    relationships: list  # list[RelationshipEdge] — already constructed


class GraphIntegration:
    """Wrapper for call graph storage operations.

    This class isolates all graph-related logic from CodeIndexManager,
    providing a clean interface for graph operations.
    """

    def __init__(self, project_id: str | None, storage_dir: Path) -> None:
        """Initialize graph storage if available.

        Args:
            project_id: Unique project identifier for graph storage
            storage_dir: Directory where index is stored (graph will be in parent dir)
        """
        self._setup_from_storage(None)

        if GRAPH_STORAGE_AVAILABLE and project_id:
            try:
                # Store graph in same directory as vector index
                graph_dir = storage_dir.parent
                # pyrefly: ignore [not-callable]
                self.storage = CodeGraphStorage(
                    project_id=project_id, storage_dir=graph_dir
                )
                self._logger.info(
                    f"Call graph storage initialized for project: {project_id}"
                )
            except Exception as e:
                self._logger.warning(f"Failed to initialize graph storage: {e}")

    @classmethod
    def from_storage(cls, storage: Any) -> "GraphIntegration":
        """Create a GraphIntegration wrapping an existing CodeGraphStorage instance.

        Use this when the storage was constructed externally (e.g. reused from
        another manager) and you need a seam handle without re-initialising storage.

        Args:
            storage: An existing CodeGraphStorage instance, or None.
        """
        instance = cls.__new__(cls)
        instance._setup_from_storage(storage)
        return instance

    def _setup_from_storage(self, storage: Any) -> None:
        """Set the instance attributes shared by __init__ and from_storage.

        Keeping these in one place ensures the two construction paths never drift:
        any attribute added here is set whether the instance was built normally or
        via from_storage()'s cls.__new__ bypass.
        """
        self._logger = logging.getLogger(__name__)
        self.storage = storage
        self._call_extractor: Any = None  # lazy-initialized on first split_block call
        # Per-build caches reset at the start of each populate_from_embeddings /
        # build_graph_from_chunks call.
        self._file_ast_cache: dict[str, tuple[str, ast.Module | None]] = {}
        # (file_path, name, func_lineno) → already emitted; dedup across split_block pieces
        self._seen_split_methods: set[tuple[str, str, int]] = set()

    def _extract_split_block_calls(
        self,
        file_path: str,
        parent_name: str | None,
        name: str,
        start_line: int,
        language: str = "python",
    ) -> list[dict[str, Any]]:
        """Extract call edges for a split_block chunk by re-reading its source file.

        Split_block chunks have empty ``calls`` because the AST extractor only runs
        on the *whole* node before splitting, and the stored ``content`` fragment is
        NOT valid Python (it's a bare body slice — ``ast.parse`` fails with
        "expected an indented block after function definition").

        This method avoids that problem by locating the **enclosing method in the
        source file** via line-range containment, then running the extractor on the
        full method source exactly once per (file, method) pair.

        Algorithm
        ---------
        1. Guard: non-Python languages are skipped (return []).
        2. Per-file AST cache: read + parse each file at most once per build pass
           (cache key = file_path; value = (source_text, ast.Module | None)).
        3. Find the deepest ``FunctionDef``/``AsyncFunctionDef`` whose
           ``lineno <= start_line <= end_lineno`` and whose ``name == bare_name``
           (and optionally ``parent_name`` for secondary disambiguation).
        4. Per-method dedup: track ``_seen_split_methods`` so only the *first*
           split_block of each logical method emits edges.  Subsequent pieces return [].
        5. Extract via ``PythonCallGraphExtractor.extract_calls`` on the full
           method source (``ast.get_source_segment``).

        Args:
            file_path: Absolute path to the source file containing the method.
            parent_name: Class name that owns the method, or None for module-level.
            name: Bare method name (e.g. ``"analyze_impact"``), *not* qualified.
            start_line: First line of this split_block fragment (1-based, same as
                the AST ``lineno`` convention).
            language: Chunk language tag; only ``"python"`` is processed.

        Returns:
            List of call dicts with keys ``callee_name``, ``line_number``,
            ``is_method_call`` — compatible with the PASS 2 call-resolution loop.
            Returns [] when the method is not found, the file is missing/unreadable,
            the language is not Python, or this is a duplicate split_block piece.
        """
        if language != "python":
            return []
        if not file_path or not name:
            return []

        # Lazy-init the extractor
        if self._call_extractor is None:
            from chunking.relationships.call_graph_extractor import (
                PythonCallGraphExtractor,
            )

            self._call_extractor = PythonCallGraphExtractor()

        # --- Per-file AST cache ---
        if file_path not in self._file_ast_cache:
            try:
                src = Path(file_path).read_text(encoding="utf-8", errors="replace")
                try:
                    tree = ast.parse(src)
                except SyntaxError:
                    tree = None
                self._file_ast_cache[file_path] = (src, tree)
            except OSError as e:
                self._logger.debug(f"split_block: cannot read {file_path}: {e}")
                self._file_ast_cache[file_path] = ("", None)

        src, tree = self._file_ast_cache[file_path]
        if tree is None:
            return []

        # --- Locate the enclosing FunctionDef by line-range + name ---
        # Use bare name (split_block stores bare, not qualified)
        bare_name = name.split(".")[-1] if "." in name else name
        best_func: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        best_span = -1  # prefer the smallest enclosing span (innermost match)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name != bare_name:
                continue
            end_lineno = getattr(node, "end_lineno", None)
            if end_lineno is None:
                continue
            if node.lineno <= start_line <= end_lineno:
                span = end_lineno - node.lineno
                if best_func is None or span < best_span:
                    best_func = node  # type: ignore[assignment]
                    best_span = span

        if best_func is None:
            self._logger.debug(
                f"split_block: no FunctionDef '{bare_name}' enclosing line "
                f"{start_line} in {file_path}"
            )
            return []

        # --- Per-method dedup: only first split_block emits edges ---
        dedup_key = (file_path, bare_name, best_func.lineno)
        if dedup_key in self._seen_split_methods:
            return []
        self._seen_split_methods.add(dedup_key)

        # --- Extract calls from full method source ---
        method_src = ast.get_source_segment(src, best_func)
        if not method_src:
            return []

        # Build a fake chunk_id for the extractor (only used internally)
        fake_chunk_id = (
            f"{file_path}:{best_func.lineno}-{best_func.end_lineno}:method:{bare_name}"  # type: ignore[attr-defined]
        )
        try:
            call_edges = self._call_extractor.extract_calls(
                method_src,
                {"chunk_id": fake_chunk_id, "parent_class": parent_name},
            )
            result = [
                {
                    "callee_name": ce.callee_name,
                    "line_number": ce.line_number,
                    "is_method_call": ce.is_method_call,
                }
                for ce in call_edges
            ]
            self._logger.debug(
                f"split_block call extraction: {len(result)} calls from "
                f"'{parent_name}.{bare_name}' in {file_path}"
            )
            return result
        except Exception as e:
            self._logger.debug(
                f"split_block call extraction failed for {file_path}:{bare_name}: {e}"
            )
            return []

    # ------------------------------------------------------------------
    # Two-pass build helpers (T2 single-owner refactor)
    # ------------------------------------------------------------------

    def _make_spec_from_embedding(self, result: Any) -> "_BuildSpec | None":
        """Normalise an EmbeddingResult into a _BuildSpec.

        Returns None if the result should be skipped (non-semantic chunk_type).
        Converts call dicts and relationship dicts to the canonical forms used
        by _two_pass_build so the builder is input-type-agnostic.
        """
        meta = result.metadata
        chunk_type = meta.get("chunk_type")
        if chunk_type not in SEMANTIC_TYPES:
            return None

        chunk_id = result.chunk_id
        file_path = meta.get("file_path", "")

        # Normalise calls: handle split_block extraction fallback
        raw_calls: list[Any] = meta.get("calls", [])
        if chunk_type == "split_block" and not raw_calls:
            raw_calls = self._extract_split_block_calls(
                file_path=file_path,
                parent_name=meta.get("parent_name"),
                name=meta.get("name", ""),
                start_line=meta.get("start_line", 0),
                language=meta.get("language", "python"),
            )
        calls = [
            {
                "callee_name": c.get("callee_name", "unknown"),
                "line_number": c.get("line_number", 0),
                "is_method_call": c.get("is_method_call", False),
            }
            for c in raw_calls
        ]

        # Normalise relationships: dict → RelationshipEdge
        relationships: list[RelationshipEdge] = []
        for rel_dict in meta.get("relationships", []):
            try:
                relationships.append(
                    RelationshipEdge(
                        source_id=rel_dict.get("source_id", chunk_id),
                        target_name=rel_dict.get("target_name", "unknown"),
                        relationship_type=RelationshipType(
                            rel_dict.get("relationship_type", "calls")
                        ),
                        line_number=rel_dict.get("line_number", 0),
                        confidence=rel_dict.get("confidence", 1.0),
                        metadata=rel_dict.get("metadata", {}),
                    )
                )
            except (ValueError, KeyError, TypeError) as e:
                self._logger.debug(
                    f"Failed to normalise relationship from {chunk_id}: {e}"
                )

        return _BuildSpec(
            chunk_id=chunk_id,
            name=meta.get("name", "unknown") or "unknown",
            chunk_type=chunk_type,
            file_path=file_path,
            language=meta.get("language", "python"),
            parent_name=meta.get("parent_name"),
            calls=calls,
            relationships=relationships,
        )

    def _make_spec_from_chunk(self, chunk: Any) -> "_BuildSpec | None":
        """Normalise a CodeChunk into a _BuildSpec.

        Returns None if the chunk should be skipped (missing chunk_id, or
        synthetic module/community chunk_type).  Handles both CallEdge objects
        and dicts for calls, and both RelationshipEdge objects and dicts for
        relationships, so the builder is input-type-agnostic.
        """
        if not chunk.chunk_id:
            return None
        if chunk.chunk_type in ("module", "community"):
            return None

        file_path = chunk.file_path or ""
        chunk_type = chunk.chunk_type

        # Normalise calls: handle both object and dict forms + split_block fallback
        raw_calls: list[Any] = list(chunk.calls or [])
        if chunk_type == "split_block" and not raw_calls:
            raw_calls = self._extract_split_block_calls(
                file_path=file_path,
                parent_name=chunk.parent_name,
                name=chunk.name or "",
                start_line=chunk.start_line or 0,
                language=chunk.language or "python",
            )
        calls = []
        for call in raw_calls:
            if hasattr(call, "callee_name"):
                calls.append(
                    {
                        "callee_name": call.callee_name,
                        "line_number": call.line_number,  # pyrefly: ignore [missing-attribute]
                        "is_method_call": call.is_method_call,  # pyrefly: ignore [missing-attribute]
                    }
                )
            else:
                calls.append(
                    {
                        "callee_name": call.get("callee_name", "unknown"),
                        "line_number": call.get("line_number", 0),
                        "is_method_call": call.get("is_method_call", False),
                    }
                )

        # Normalise relationships: accept objects and dicts
        relationships: list[RelationshipEdge] = []
        for rel in chunk.relationships or []:
            if isinstance(rel, RelationshipEdge):
                relationships.append(rel)
            elif isinstance(rel, dict):
                try:
                    relationships.append(
                        RelationshipEdge(
                            source_id=rel.get(
                                "source_id", chunk.chunk_id
                            ),  # pyrefly: ignore [bad-argument-type]
                            target_name=rel.get("target_name", "unknown"),
                            relationship_type=RelationshipType(
                                rel.get("relationship_type", "calls")
                            ),
                            line_number=rel.get("line_number", 0),
                            confidence=rel.get("confidence", 1.0),
                            metadata=rel.get("metadata", {}),
                        )
                    )
                except (ValueError, KeyError, TypeError) as e:
                    self._logger.debug(
                        f"Failed to normalise relationship from {chunk.chunk_id}: {e}"
                    )

        return _BuildSpec(
            chunk_id=chunk.chunk_id,
            name=chunk.name or "unknown",
            chunk_type=chunk_type,
            file_path=file_path,
            language=chunk.language or "python",
            parent_name=chunk.parent_name,
            calls=calls,
            relationships=relationships,
        )

    def _two_pass_build(
        self, specs: "list[_BuildSpec]", *, clear: bool
    ) -> "dict[str, int]":
        """Single owner of the two-pass node-then-edge graph build algorithm.

        Pass 1 adds all nodes and builds the symbol-resolution map.
        Pass 2 resets per-build caches and adds call + relationship edges.

        Args:
            specs: Pre-normalised _BuildSpec items (None already filtered out).
            clear: When True, clears the graph before Pass 1 (used by
                build_graph_from_chunks for a fresh build).  When False, appends
                (used by populate_from_embeddings for incremental add).

        Returns:
            Stats dict with keys: ``nodes_added``, ``call_edges``,
            ``resolved_edges``, ``phantom_edges``, ``rel_edges``.
        """
        if self.storage is None:
            return {}

        if clear:
            self.storage.clear()

        if not specs:
            return {}

        # === PASS 1: add nodes + build symbol-resolution map ===
        name_to_chunk_ids: dict[str, list[str]] = defaultdict(list)
        nodes_added = 0

        for spec in specs:
            try:
                self.storage.add_node(
                    chunk_id=spec.chunk_id,
                    name=spec.name,
                    chunk_type=spec.chunk_type,
                    file_path=spec.file_path,
                    language=spec.language,
                )
                nodes_added += 1

                # Index names for call-target resolution (skip "unknown" placeholder)
                if spec.name and spec.name != "unknown":
                    name_to_chunk_ids[spec.name].append(spec.chunk_id)
                    if "." in spec.name:
                        name_to_chunk_ids[spec.name.split(".")[-1]].append(
                            spec.chunk_id
                        )
                    if spec.parent_name:
                        name_to_chunk_ids[f"{spec.parent_name}.{spec.name}"].append(
                            spec.chunk_id
                        )
            except (AttributeError, KeyError, TypeError) as e:
                self._logger.warning(
                    f"Failed to add node {spec.chunk_id} to graph: {e}"
                )

        # === PASS 2: add call + relationship edges ===
        self._file_ast_cache = {}
        self._seen_split_methods = set()
        call_edges = 0
        resolved_edges = 0
        phantom_edges = 0
        rel_edges = 0

        for spec in specs:
            try:
                for call in spec.calls:
                    callee_name = call["callee_name"]
                    line_number = call["line_number"]
                    is_method_call = call["is_method_call"]
                    resolved = self._resolve_call_target(
                        callee_name, name_to_chunk_ids, caller_file=spec.file_path
                    )
                    if resolved:
                        self.storage.add_call_edge(
                            caller_id=spec.chunk_id,
                            callee_name=resolved,
                            line_number=line_number,
                            is_method_call=is_method_call,
                            is_resolved=True,
                            confidence="exact",
                        )
                        call_edges += 1
                        resolved_edges += 1
                    else:
                        ambiguous = self._get_ambiguous_candidates(
                            callee_name, name_to_chunk_ids, caller_file=spec.file_path
                        )
                        if ambiguous:
                            for candidate_id in ambiguous:
                                self.storage.add_call_edge(
                                    caller_id=spec.chunk_id,
                                    callee_name=candidate_id,
                                    line_number=line_number,
                                    is_method_call=is_method_call,
                                    is_resolved=True,
                                    confidence="ambiguous",
                                )
                            call_edges += 1
                            phantom_edges += 1
                        else:
                            self.storage.add_call_edge(
                                caller_id=spec.chunk_id,
                                callee_name=callee_name,
                                line_number=line_number,
                                is_method_call=is_method_call,
                                is_resolved=False,
                            )
                            call_edges += 1
                            phantom_edges += 1

                for rel in spec.relationships:
                    self.storage.add_relationship_edge(rel)
                    rel_edges += 1

            except Exception as e:
                self._logger.warning(f"Failed to add edges for {spec.chunk_id}: {e}")

        return {
            "nodes_added": nodes_added,
            "call_edges": call_edges,
            "resolved_edges": resolved_edges,
            "phantom_edges": phantom_edges,
            "rel_edges": rel_edges,
        }

    def add_chunk(self, chunk_id: str, metadata: dict[str, Any]) -> None:
        """Add chunk to call graph storage.

        Args:
            chunk_id: Unique chunk identifier
            metadata: Chunk metadata including calls and relationships
        """
        if self.storage is None:
            self._logger.debug(f"add_chunk: graph storage is None, skipping {chunk_id}")
            return

        try:
            # Process all semantic chunk types for relationships
            # - Functions/methods: call relationships
            # - Classes/structs/interfaces/etc: inheritance, type usage
            chunk_type = metadata.get("chunk_type")
            chunk_name = metadata.get("name")
            relationships = metadata.get("relationships", [])

            self._logger.debug(
                f"add_chunk called: chunk_id={chunk_id}, type={chunk_type}, name={chunk_name}"
            )

            if chunk_type not in SEMANTIC_TYPES:
                # Allow through if it has relationships (edge case)
                if not relationships:
                    self._logger.debug(
                        f"Skipping non-semantic chunk: {chunk_id} (type={chunk_type})"
                    )
                    return
                else:
                    self._logger.debug(
                        f"Processing non-semantic chunk with relationships: {chunk_id} (type={chunk_type}, rels={len(relationships)})"
                    )

            self._logger.debug(f"Adding {chunk_type} '{metadata.get('name')}' to graph")

            # Add node for this chunk
            self.storage.add_node(
                chunk_id=chunk_id,
                name=metadata.get("name", "unknown"),
                # pyrefly: ignore [bad-argument-type]
                chunk_type=chunk_type,
                file_path=metadata.get("file_path", ""),
                language=metadata.get("language", "python"),
            )

            # Add call edges from function call extraction
            calls = metadata.get("calls", [])
            for call_dict in calls:
                self.storage.add_call_edge(
                    caller_id=chunk_id,
                    callee_name=call_dict.get("callee_name", "unknown"),
                    line_number=call_dict.get("line_number", 0),
                    is_method_call=call_dict.get("is_method_call", False),
                )

            # Add all relationship edges
            relationships = metadata.get("relationships", [])
            if relationships:
                self._logger.debug(
                    f"Processing {len(relationships)} relationship edges for {chunk_id}"
                )
                for rel_dict in relationships:
                    try:
                        # Reconstruct RelationshipEdge from dict
                        edge = RelationshipEdge(
                            source_id=rel_dict.get("source_id", chunk_id),
                            target_name=rel_dict.get("target_name", "unknown"),
                            relationship_type=RelationshipType(
                                rel_dict.get("relationship_type", "calls")
                            ),
                            line_number=rel_dict.get("line_number", 0),
                            confidence=rel_dict.get("confidence", 1.0),
                            metadata=rel_dict.get("metadata", {}),
                        )

                        # Add to graph storage
                        self.storage.add_relationship_edge(edge)

                    except (ValueError, KeyError, TypeError) as e:
                        self._logger.warning(
                            f"Failed to add relationship edge from {chunk_id}: {e}"
                        )

        except (KeyError, TypeError) as e:
            self._logger.warning(f"Failed to add {chunk_id} to graph: {e}")

    def populate_from_embeddings(self, embedding_results: list[Any]) -> None:
        """Populate call graph from a list of EmbeddingResult objects.

        Batch two-pass method: builds a symbol-resolution map first, then adds
        edges using _resolve_call_target (canonical builtins-filter + same-file
        + split_block disambiguation + qualified-name indexing).

        Incremental-add counterpart to build_graph_from_chunks: does NOT clear
        the graph first (build_graph_from_chunks clears; this appends).

        Args:
            embedding_results: List of EmbeddingResult with .chunk_id and .metadata.
        """
        if self.storage is None or not embedding_results:
            return
        specs = [
            s
            for r in embedding_results
            if (s := self._make_spec_from_embedding(r)) is not None
        ]
        stats = self._two_pass_build(specs, clear=False)
        self._logger.info(
            f"Populated graph from embeddings: {stats.get('nodes_added', 0)} nodes, "
            f"{stats.get('call_edges', 0)} call edges "
            f"({stats.get('resolved_edges', 0)} resolved, "
            f"{stats.get('phantom_edges', 0)} phantom), "
            f"{stats.get('rel_edges', 0)} relationship edges"
        )

    def build_graph_from_chunks(self, chunks) -> None:
        """Build graph from chunks WITHOUT embeddings (for pre-embedding community detection).

        This enables the two-pass chunking flow:
        1. Chunk WITHOUT merging
        2. Build graph from unmerged chunks
        3. Detect communities
        4. Remerge with community boundaries
        5. Embed and index

        Uses NetworkX DiGraph API:
        - G.add_node(chunk_id, **attrs)
        - G.add_edge(caller, callee, **attrs)

        Reference: https://networkx.org/documentation/stable/reference/classes/digraph.html

        Two-pass approach for symbol resolution:
        - Pass 1: Add all chunk nodes + build name→chunk_id mapping
        - Pass 2: Add edges with call target resolution (creates direct chunk-chunk edges)

        Args:
            chunks: List of CodeChunk with chunk_id, calls, relationships populated from AST
        """
        if self.storage is None:
            self._logger.warning(
                "Graph storage not initialized, cannot build from chunks"
            )
            return
        specs = [
            s
            for chunk in chunks
            if (s := self._make_spec_from_chunk(chunk)) is not None
        ]
        stats = self._two_pass_build(specs, clear=True)
        self._logger.info(
            f"Built graph from {stats.get('nodes_added', 0)} chunks: "
            f"{len(self.storage)} nodes, "
            f"{stats.get('resolved_edges', 0)} direct edges, "
            f"{stats.get('phantom_edges', 0)} phantom edges"
        )

    def _resolve_call_target(
        self,
        callee_name: str,
        name_to_chunk_ids: dict[str, list[str]],
        caller_file: str | None = None,
    ) -> str | None:
        """Resolve a call target name to its chunk_id.

        Returns a chunk_id when exactly one project match exists (or after
        same-file / split_block disambiguation).  Returns ``None`` when the call
        should become a phantom node (true builtin, common stdlib name with no
        project definition, or still-ambiguous multi-candidate).  For the
        still-ambiguous case, call ``_get_ambiguous_candidates`` to obtain all
        candidates and create ``confidence="ambiguous"`` edges instead.

        Args:
            callee_name: Symbol name from the call (e.g., "foo", "ClassName.method")
            name_to_chunk_ids: Mapping from symbol names to chunk_ids
            caller_file: Optional file path of caller for disambiguation

        Returns:
            chunk_id if exactly one match, None otherwise
        """
        # Skip builtins (len, print, etc.) -- they never resolve to project code
        import builtins

        if hasattr(builtins, callee_name):
            return None  # Create phantom node (will be filtered in traversals)

        # Refined common-method blocklist: drop the name ONLY when the project has
        # no definition for it.  If the project defines its own `get`, `format`,
        # etc., we keep the edge (resolved below via same-file / unique-match).
        base_name = callee_name.split(".")[-1] if "." in callee_name else callee_name
        if base_name in _COMMON_METHODS and callee_name not in name_to_chunk_ids:
            return None

        candidates = name_to_chunk_ids.get(callee_name, [])

        if len(candidates) == 1:
            return candidates[0]

        # Context-aware disambiguation: prefer same-file match for ambiguous calls
        if len(candidates) > 1 and caller_file:
            # Try same-file preference - overwhelmingly the intended target
            same_file = [c for c in candidates if caller_file in c]
            if len(same_file) == 1:
                return same_file[0]

            # Split block disambiguation: when all candidates are split_blocks
            # of the same function (same file, same name), resolve to the first
            # block (lowest start line = function entry point). This fixes graph
            # isolation for large split functions.
            if len(candidates) > 1:
                split_blocks = [c for c in candidates if ":split_block:" in c]
                if len(split_blocks) == len(candidates):
                    # All candidates are split_blocks - pick the entry block
                    def _start_line(chunk_id: str) -> int:
                        parts = chunk_id.split(":")
                        if len(parts) >= 2:
                            line_range = parts[1]  # e.g., "793-860"
                            try:
                                return int(line_range.split("-")[0])
                            except (ValueError, IndexError):
                                pass
                        return 2**31  # Sentinel for sort ordering

                    split_blocks.sort(key=_start_line)
                    return split_blocks[0]

        # No match or still ambiguous — caller should check _get_ambiguous_candidates
        return None

    def _get_ambiguous_candidates(
        self,
        callee_name: str,
        name_to_chunk_ids: dict[str, list[str]],
        caller_file: str | None = None,
    ) -> list[str]:
        """Return all candidate chunk_ids for a callee name that has multiple matches.

        Used by the call-site in ``_build_graph_from_chunks`` when
        ``_resolve_call_target`` returns ``None`` but the name *does* appear in
        ``name_to_chunk_ids`` — meaning the call is ambiguous rather than a true
        phantom.  The caller creates ``confidence="ambiguous"`` edges to each
        candidate so they are retained in the graph and surfaced at query time.

        Returns an empty list when the name is not in ``name_to_chunk_ids`` (true
        phantom / builtin / common-stdlib name with no project definition).

        Args:
            callee_name: Symbol name from the call.
            name_to_chunk_ids: Full symbol → chunk_ids map for the indexed project.
            caller_file: Caller file path (unused here, reserved for future use).

        Returns:
            List of candidate chunk_ids (possibly empty).
        """
        return list(name_to_chunk_ids.get(callee_name, []))

    def save(self) -> None:
        """Save call graph to disk."""
        # Check if graph storage exists and has nodes
        graph_status = "not None" if self.storage is not None else "None"
        graph_nodes = len(self.storage) if self.storage else 0
        self._logger.info(
            f"[SAVE] Graph storage check: storage={graph_status}, nodes={graph_nodes}"
        )

        if self.storage is not None and len(self.storage) > 0:
            try:
                self._logger.info(
                    f"[SAVE] Saving call graph with {len(self.storage)} nodes to {self.storage.graph_path}"
                )
                self.storage.save()
                self._logger.info("[SAVE] Successfully saved call graph")
            except (OSError, RuntimeError) as e:
                self._logger.warning(f"[SAVE] Failed to save call graph: {e}")
        else:
            skip_reason = "None" if self.storage is None else "empty (0 nodes)"
            self._logger.info(f"[SAVE] Skipping graph save: storage is {skip_reason}")

    def clear(self) -> None:
        """Clear call graph."""
        if self.storage is not None:
            try:
                self.storage.clear()
                self._logger.info("Call graph cleared")
            except (RuntimeError, AttributeError) as e:
                self._logger.warning(f"Failed to clear call graph: {e}")

    @property
    def is_available(self) -> bool:
        """Check if graph storage is available and initialized."""
        return self.storage is not None

    @property
    def node_count(self) -> int:
        """Get number of nodes in graph."""
        return len(self.storage) if self.storage else 0

    def __len__(self) -> int:
        """Return node count for len() support."""
        return self.node_count
