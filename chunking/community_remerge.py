"""Community-remerge pipeline: assign community IDs, round-trip via TreeSitterChunk, merge.

P5: lifted from LanguageChunker @staticmethods in chunking/languages/base.py.

Ownership rationale
-------------------
The four functions here operate exclusively on ``CodeChunk`` / ``TreeSitterChunk``
AST types and community maps — they have no business living on the tree-sitter
base class.  Moving them here:

  * removes the ``PythonChunker()`` function-bag hack from ``base.py`` (where it
    lived only so ``remerge_chunks_with_communities`` could borrow its merge
    primitive without a circular import),
  * consolidates the three hand-rolled ``"{path}:{start}-{end}:{kind}[:{name}]"``
    chunk-id literals into a single ``search.chunk_id.build()`` call each, and
  * makes the module graph acyclic: ``chunking/languages/base.py`` no longer
    imports ``chunking.languages.python``.

The merge primitive (``_greedy_merge_small_chunks``) genuinely belongs on the
chunker (it uses ``self._create_merged_chunk``), so it stays there.  The default
``merger=None`` path in :func:`remerge_chunks_with_communities` lazily instantiates
a ``PythonChunker`` only when needed; pass an explicit ``merger`` to avoid
construction costs or to inject a test double.

Public API
----------
All four functions are importable directly:

    from chunking.community_remerge import (
        assign_community_ids,
        to_treesitter_chunks,
        from_treesitter_chunks,
        remerge_chunks_with_communities,
    )
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace as dc_replace
from typing import TYPE_CHECKING, Any

from search.chunk_id import build as build_chunk_id
from utils.path_utils import normalize_path


if TYPE_CHECKING:
    from chunking.languages.base import TreeSitterChunk
    from chunking.python_ast_chunker import CodeChunk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def assign_community_ids(
    chunks: list[CodeChunk],
    community_map: dict[str, int],
) -> list[CodeChunk]:
    """Return a copy of each chunk with its community_id resolved from *community_map*.

    Generates the lookup key that maps a raw AST chunk to a community:
    ``chunk_id`` when already set; otherwise a composite built by
    :func:`search.chunk_id.build` from
    ``relative_path:start-end:chunk_type[:parent.name]``.

    This is the single source of truth for the chunk→community lookup semantics
    used in :func:`remerge_chunks_with_communities`.
    """
    result = []
    for chunk in chunks:
        chunk_id = chunk.chunk_id
        if chunk_id is None:
            normalized_path = normalize_path(chunk.relative_path)
            if chunk.parent_name and chunk.name:
                qualified = f"{chunk.parent_name}.{chunk.name}"
            elif chunk.name:
                qualified = chunk.name
            else:
                qualified = None
            lookup_key = build_chunk_id(
                normalized_path,
                chunk.start_line,
                chunk.end_line,
                chunk.chunk_type,
                qualified,
            )
        else:
            lookup_key = chunk_id
        community_id = community_map.get(lookup_key)
        if community_id is None:
            logger.debug(f"[REMERGE] No community found for {lookup_key}")
        result.append(dc_replace(chunk, community_id=community_id))
    return result


def to_treesitter_chunks(chunks: list[CodeChunk]) -> list[TreeSitterChunk]:
    """Convert *CodeChunk*s to *TreeSitterChunk*s for the greedy-merge algorithm.

    Preserves call-graph data, relationships, and ``community_id`` in the
    metadata dict so they survive the merge pass and can be recovered by
    :func:`from_treesitter_chunks`.
    """
    # pyrefly: ignore [missing-module-attribute]
    from chunking.languages.base import TreeSitterChunk as _TSChunk  # noqa: PLC0415

    return [
        _TSChunk(
            content=chunk.content,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            node_type=chunk.chunk_type,
            language=chunk.language,
            metadata={
                "name": chunk.name,
                "file_path": chunk.file_path,
                "relative_path": chunk.relative_path,
                "calls": chunk.calls,
                "relationships": chunk.relationships,
                "docstring": chunk.docstring,
                "decorators": chunk.decorators,
                "imports": chunk.imports,
                "complexity_score": chunk.complexity_score,
                "tags": chunk.tags,
            },
            chunk_id=chunk.chunk_id,
            parent_class=getattr(chunk, "parent_name", None),
            community_id=chunk.community_id,
        )
        for chunk in chunks
    ]


def from_treesitter_chunks(
    merged_ts_chunks: list[TreeSitterChunk],
    original_chunks: list[CodeChunk],
) -> list[CodeChunk]:
    """Convert merged *TreeSitterChunk*s back to *CodeChunk*s using original metadata.

    Uses a 2-pass lookup:

    1. **Members** — all originals whose range is contained within the merged
       range (same file, ``original ⊆ merged``).  For ``"merged"`` node_type all
       members contribute calls/relationships/imports/decorators/tags (union,
       deduplicated).  Building the per-file index once removes the O(M×N)
       full-list rescan that previously ran for every merged chunk (#16).
    2. **File fallback** — if no contained members are found, any chunk from the
       same file is used as the sole representative (handles edge-case line
       shifts).
    3. **Skip** — logs a warning and omits the merged chunk if no original found.

    *original_chunks* should be the community-annotated list produced by
    :func:`assign_community_ids` so that ``community_id`` is available.
    """
    from chunking.python_ast_chunker import CodeChunk as _CodeChunk  # noqa: PLC0415

    result: list[_CodeChunk] = []

    # Build file → chunks index once (O(M+N)) instead of rescanning per merged chunk
    originals_by_file: dict[str, list] = {}
    for c in original_chunks:
        originals_by_file.setdefault(c.file_path, []).append(c)

    for ts_chunk in merged_ts_chunks:
        merged_file: str | None = ts_chunk.metadata.get("file_path")
        file_originals = originals_by_file.get(merged_file or "", [])

        # Collect every original whose range is fully contained within this merged chunk
        members = [
            c
            for c in file_originals
            if c.start_line >= ts_chunk.start_line and c.end_line <= ts_chunk.end_line
        ]

        if not members:
            if file_originals:
                # File fallback: use first same-file chunk as scalar-field representative
                members = [file_originals[0]]
                logger.debug(
                    f"[REMERGE] Using fallback for {merged_file}:"
                    f"{ts_chunk.start_line}-{ts_chunk.end_line}"
                )
            else:
                logger.warning(
                    f"[REMERGE] No original chunk found for merged chunk at "
                    f"{merged_file}:{ts_chunk.start_line}-{ts_chunk.end_line}, skipping"
                )
                continue

        representative = members[0]

        if ts_chunk.node_type == "merged":
            # Compute the merged chunk_id so relationship edges are attributed to the
            # right graph node.  Mirrors Embedder._build_chunk_id via chunk_id.build():
            #   "{relative_path}:{start}-{end}:merged[:{qualified_name}]"
            rel_path = normalize_path(
                str(representative.relative_path or merged_file or "")
            )
            name = ts_chunk.metadata.get("name") or ""
            parent = ts_chunk.parent_class or ""
            qualified = f"{parent}.{name}" if parent and name else name
            merged_chunk_id = build_chunk_id(
                rel_path,
                ts_chunk.start_line,
                ts_chunk.end_line,
                "merged",
                qualified or None,
            )

            # Union calls (CallEdge objects) — dedupe by (callee_name, line_number)
            seen_call: set[tuple] = set()
            unioned_calls: list = []
            for m in members:
                for call in m.calls or []:
                    key = (
                        getattr(call, "callee_name", str(call)),
                        getattr(call, "line_number", 0),
                    )
                    if key not in seen_call:
                        seen_call.add(key)
                        unioned_calls.append(call)

            # Union relationships (RelationshipEdge objects) — dedupe by
            # (target_name, relationship_type, line_number).  Rewrite source_id to the
            # merged chunk_id so graph edges resolve from the correct node.
            seen_rel: set[tuple] = set()
            unioned_rels: list = []
            for m in members:
                for rel in m.relationships or []:
                    rt = getattr(rel, "relationship_type", None)
                    rt_val = rt.value if hasattr(rt, "value") else str(rt)
                    key = (
                        getattr(rel, "target_name", ""),
                        rt_val,
                        getattr(rel, "line_number", 0),
                    )
                    if key not in seen_rel:
                        seen_rel.add(key)
                        try:
                            unioned_rels.append(
                                dc_replace(rel, source_id=merged_chunk_id)
                            )
                        except Exception as e:  # noqa: BLE001 - resilience: keep original relationship if dc_replace fails
                            logger.warning(
                                "dc_replace failed for %s during community "
                                "remerge, keeping original source_id: %s",
                                merged_chunk_id,
                                e,
                            )
                            unioned_rels.append(rel)

            # Union list fields (imports, decorators) — dedupe by string value
            seen_imports: set[str] = set()
            unioned_imports: list = []
            for m in members:
                for item in m.imports or []:
                    k = str(item)
                    if k not in seen_imports:
                        seen_imports.add(k)
                        unioned_imports.append(item)

            seen_decs: set[str] = set()
            unioned_decs: list = []
            for m in members:
                for item in m.decorators or []:
                    k = str(item)
                    if k not in seen_decs:
                        seen_decs.add(k)
                        unioned_decs.append(item)

            # Union tags (list[str] or set in practice)
            seen_tags: set[str] = set()
            unioned_tags: list = []
            for m in members:
                for tag in m.tags or []:
                    if tag not in seen_tags:
                        seen_tags.add(tag)
                        unioned_tags.append(tag)

            calls: Any = unioned_calls
            relationships: Any = unioned_rels
            imports: Any = unioned_imports
            decorators: Any = unioned_decs
            tags: Any = unioned_tags
            docstring = representative.docstring
            complexity_score = representative.complexity_score
        else:
            # Non-merged node: preserve single-representative behavior
            calls = representative.calls
            relationships = representative.relationships
            docstring = representative.docstring
            decorators = representative.decorators
            imports = representative.imports
            complexity_score = representative.complexity_score
            tags = representative.tags

        result.append(
            _CodeChunk(
                content=ts_chunk.content,
                chunk_type=(
                    ts_chunk.node_type if ts_chunk.node_type != "merged" else "merged"
                ),
                start_line=ts_chunk.start_line,
                end_line=ts_chunk.end_line,
                file_path=representative.file_path,
                relative_path=representative.relative_path,
                folder_structure=representative.folder_structure,
                name=ts_chunk.metadata.get("name"),
                parent_name=ts_chunk.parent_class,
                language=representative.language,
                chunk_id=None,
                community_id=ts_chunk.community_id,
                merged_from=ts_chunk.metadata.get("merged_from"),
                calls=calls,
                relationships=relationships,
                docstring=docstring,
                decorators=decorators,
                imports=imports,
                complexity_score=complexity_score,
                tags=tags,
            )
        )
    return result


def remerge_chunks_with_communities(
    chunks: list[CodeChunk],
    community_map: dict[str, int],
    merger: Callable[..., tuple[list, int, int]] | None = None,
    min_tokens: int = 50,
    max_merged_tokens: int = 1000,
    token_method: str = "whitespace",
    size_method: str = "tokens",
) -> list[CodeChunk]:
    """Re-merge chunks using community boundaries (community-based remerging).

    Called AFTER community detection to re-merge chunks using ``community_id``
    as merge boundaries instead of ``parent_class``.  Solves the circular
    dependency: chunking needs communities, but communities need chunks.

    Community merge flow::

        1. Chunk with AST boundaries → Build graph → Detect communities
        2. Re-merge using community_id boundaries  ← THIS FUNCTION

    Args:
        chunks: List of CodeChunk (raw AST chunks).
        community_map: Dict mapping chunk_id to community_id from Louvain
            detection.
        merger: Callable with the same signature as
            ``LanguageChunker._greedy_merge_small_chunks`` — i.e.
            ``(ts_chunks, *, min_tokens, max_merged_tokens, token_method,
            use_community_boundary, size_method) → (merged, orig_count, final_count)``.
            When ``None`` (default), a ``PythonChunker`` is instantiated lazily
            and its bound method is used.  Pass an explicit callable to avoid
            construction costs, prevent circular-import issues in tests, or
            inject a test double.
        min_tokens: Minimum tokens before considering merge (default: 50).
        max_merged_tokens: Maximum tokens for merged chunk (default: 1000).
        token_method: Token estimation method (``"whitespace"`` or
            ``"tiktoken"``).
        size_method: Size calculation method — ``"tokens"`` (default) or
            ``"characters"`` (cAST paper).

    Returns:
        List of CodeChunk re-merged with community boundaries.

    Example::

        >>> # After community detection assigns IDs
        >>> community_map = {"file.py:1-10:method:foo": 0, "file.py:11-20:method:bar": 1}
        >>> remerged = remerge_chunks_with_communities(chunks, community_map)
        >>> # Methods from different communities won't merge
    """
    if not chunks or not community_map:
        return chunks

    if merger is None:
        # Lazy default: PythonChunker owns _greedy_merge_small_chunks (uses
        # self._create_merged_chunk).  Deferred import avoids a circular
        # dependency at module level: base → community_remerge → python.
        from chunking.languages.python import PythonChunker  # noqa: PLC0415

        merger = PythonChunker()._greedy_merge_small_chunks

    logger.info(f"[REMERGE] Re-merging {len(chunks)} chunks with community boundaries")

    # Step 1: Assign community_id to chunks from map
    chunks_with_community = assign_community_ids(chunks, community_map)

    # Step 2: Convert CodeChunk → TreeSitterChunk for merge algorithm
    ts_chunks = to_treesitter_chunks(chunks_with_community)

    # Step 3: Re-run merge with use_community_boundary=True
    merged_ts_chunks, orig_count, merged_count = merger(
        ts_chunks,
        min_tokens=min_tokens,
        max_merged_tokens=max_merged_tokens,
        token_method=token_method,
        use_community_boundary=True,
        size_method=size_method,
    )

    logger.info(
        f"[REMERGE] Community-based merge: {orig_count} → {merged_count} chunks "
        f"({100 * (orig_count - merged_count) / orig_count:.1f}% reduction)"
    )

    # Step 4: Convert TreeSitterChunk → CodeChunk
    return from_treesitter_chunks(merged_ts_chunks, chunks_with_community)
