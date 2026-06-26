"""Single owner of the chunk-metadata record shape.

``CodeEmbedder._build_chunk_metadata`` produces a ``ChunkMetadata`` dict from
every ``CodeChunk``.  This module documents that shape once, so:

* ``pyrefly`` can validate key access across all consumers statically.
* Adding a key or changing a type is a single-file edit surfaced by the
  type-checker rather than a hunt through callers.
* The duplicated ``file_path or relative_path`` path-resolution fallback is
  centralised in :func:`resolve_chunk_path`.

Pipeline lifecycle
------------------
The dict mutates as it flows through the pipeline:

1. **Build** (``_build_chunk_metadata``): all keys present, including
   ``content`` (full source text; large).
2. **Persist** (``MetadataStore``): ``content`` is stripped before storage so
   only ``content_preview`` survives on disk (#55).  ``content`` is therefore
   ``NotRequired``.
3. **Index augmentation** (``CodeIndexManager.add_embeddings`` /
   ``IncrementalIndexer``): ``project_name`` is injected.  It is absent at
   build time, hence ``NotRequired``.

Using a ``TypedDict`` (rather than a frozen ``dataclass``) preserves zero
runtime overhead — the dict stays a plain ``dict`` at all callsites; the
type information is erased at runtime and only affects static analysis.
"""

from typing import Any, NotRequired, TypedDict


class ChunkMetadata(TypedDict):
    """Typed shape of the metadata dict produced by ``_build_chunk_metadata``.

    All keys are required unless annotated ``NotRequired``.
    """

    # -----------------------------------------------------------------------
    # Path keys — note the dual-key ambiguity: file_path is the absolute OS
    # path; relative_path is relative to the project root.  Use
    # resolve_chunk_path() to pick the right one instead of inlining the
    # fallback logic.
    # -----------------------------------------------------------------------
    file_path: str
    relative_path: str

    # -----------------------------------------------------------------------
    # Structural metadata
    # -----------------------------------------------------------------------
    folder_structure: list[str]  # path components, e.g. ["src", "utils"]
    chunk_type: str  # "function" | "class" | "method" | "module" | …
    start_line: int
    end_line: int
    name: str | None  # symbol name; None for anonymous / module-level chunks
    parent_name: str | None  # enclosing class name for methods
    parent_chunk_id: str | None  # parent chunk_id for methods

    # -----------------------------------------------------------------------
    # Content metadata
    # -----------------------------------------------------------------------
    docstring: str | None
    decorators: list[str]
    imports: list[str]
    complexity_score: int
    tags: list[str]
    content_preview: str  # first 200 chars of content; always persisted

    # -----------------------------------------------------------------------
    # Relationship metadata
    # -----------------------------------------------------------------------
    calls: list[dict[str, Any]]  # CallEdge.to_dict() entries
    relationships: list[dict[str, Any]]  # RelationshipEdge.to_dict() entries

    # -----------------------------------------------------------------------
    # Language
    # -----------------------------------------------------------------------
    language: str  # e.g. "python"

    # -----------------------------------------------------------------------
    # Stage-dependent keys (NotRequired)
    # -----------------------------------------------------------------------
    content: NotRequired[str]
    """Full source text.  Present in-memory at build time; stripped before
    persist by MetadataStore (#55).  Consumers that run after persist must
    not assume this key exists."""

    project_name: NotRequired[str]
    """Injected by ``CodeIndexManager.add_embeddings`` / ``IncrementalIndexer``
    at index time.  Absent at build time and in freshly loaded metadata."""


def resolve_chunk_path(meta: "ChunkMetadata") -> str | None:
    """Return the best available file path from a ``ChunkMetadata`` dict.

    Prefers ``file_path`` (absolute) over ``relative_path``; returns ``None``
    if both are absent or empty.

    This is the single, canonical replacement for the duplicated inline pattern::

        chunk_file = metadata.get("file_path") or metadata.get("relative_path")

    Args:
        meta: A ``ChunkMetadata`` dict (or any mapping with those keys).

    Returns:
        A non-empty path string, or ``None``.
    """
    return meta.get("file_path") or meta.get("relative_path") or None  # type: ignore[return-value]
