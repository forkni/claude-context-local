"""Generate synthetic community-level summary chunks."""

from collections import Counter, defaultdict
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from chunking.python_ast_chunker import CodeChunk


def generate_community_summaries(
    chunks: list["CodeChunk"],
    community_map: dict[str, int],
) -> list["CodeChunk"]:
    """Create one community-summary CodeChunk per community with 2+ members.

    Args:
        chunks: All CodeChunks from indexing (pre-remerge chunk_ids match community_map)
        community_map: Mapping from chunk_id to community_id

    Returns:
        List of synthetic community CodeChunks (one per qualifying community)
    """
    # Group chunks by community_id
    by_community: dict[int, list["CodeChunk"]] = defaultdict(list)
    for chunk in chunks:
        if not chunk.chunk_id:
            continue
        community_id = community_map.get(chunk.chunk_id)
        if community_id is not None:
            by_community[community_id].append(chunk)

    summaries = []
    for community_id, community_chunks in by_community.items():
        if len(community_chunks) < 2:
            continue  # Skip single-chunk communities
        summaries.append(_build_community_summary(community_id, community_chunks))

    return summaries


def _build_community_summary(
    community_id: int, community_chunks: list["CodeChunk"]
) -> "CodeChunk":
    """Build a synthetic community CodeChunk from community chunks.

    Args:
        community_id: Unique community identifier
        community_chunks: All chunks belonging to this community

    Returns:
        Synthetic CodeChunk with chunk_type="community"
    """
    from chunking.python_ast_chunker import CodeChunk

    # Extract dominant directory for label
    directories = [
        chunk.relative_path.rsplit("/", 1)[0] if "/" in chunk.relative_path else "root"
        for chunk in community_chunks
    ]
    directory_counts = Counter(directories)
    dominant_directory = directory_counts.most_common(1)[0][0]

    # Collect metadata
    classes = []
    functions = []
    methods = []
    all_imports = []
    docstring_lines = []

    for chunk in community_chunks:
        if chunk.chunk_type == "class":
            classes.append(chunk.name or "?")
            if chunk.docstring:
                first_line = chunk.docstring.strip().split("\n")[0][:120]
                docstring_lines.append(f"# - {chunk.name}: {first_line}")
        elif chunk.chunk_type == "function":
            functions.append(chunk.name or "?")
        elif chunk.chunk_type in ("method", "decorated_definition"):
            qualified = (
                f"{chunk.parent_name}.{chunk.name}" if chunk.parent_name else chunk.name
            )
            methods.append(qualified or "?")

        if chunk.imports:
            all_imports.extend(chunk.imports[:5])  # Cap per-chunk imports

    # Find hub function (largest chunk as proxy for most connected)
    hub_chunk = max(
        community_chunks,
        key=lambda c: c.end_line - c.start_line if c.start_line else 0,
    )

    # Generate label from dominant directory + primary class/function
    if classes:
        primary_symbol = classes[0]
    elif functions:
        primary_symbol = functions[0]
    else:
        primary_symbol = f"comm{community_id}"

    label = f"{dominant_directory}_{primary_symbol}".replace("/", "_")

    # Build summary text
    parts = [f"# Community {community_id} | {label}"]

    symbol_count = len(classes) + len(functions) + len(methods)
    parts.append(
        f"# Community containing {symbol_count} symbols in {len(community_chunks)} chunks"
    )
    parts.append(f"# Dominant directory: {dominant_directory}")

    if classes:
        parts.append(f"# Classes: {', '.join(classes[:10])}")
    if functions:
        parts.append(f"# Functions: {', '.join(functions[:10])}")
    if methods:
        parts.append(f"# Key methods: {', '.join(methods[:15])}")

    # Deduplicate imports, show top-level modules
    unique_imports = sorted(set(all_imports))[:10]
    if unique_imports:
        parts.append(f"# Imports: {', '.join(unique_imports)}")

    if hub_chunk.name:
        parts.append(f"# Hub function: {hub_chunk.name}")

    if docstring_lines:
        parts.extend(docstring_lines[:5])

    content = "\n".join(parts)

    # Aggregate docstring for embedding
    agg_docstring = "; ".join(
        f"{c.name}: {c.docstring.strip().split(chr(10))[0][:80]}"
        for c in community_chunks
        if c.docstring and c.name
    )[:500]

    # Synthetic chunk_id and file_path
    chunk_id = f"__community__/{label}:0-0:community:{label}"
    file_path = f"__community__/{label}"

    return CodeChunk(
        content=content,
        chunk_type="community",
        start_line=0,
        end_line=0,
        file_path=file_path,
        relative_path=file_path,
        folder_structure=[],
        name=label,
        docstring=agg_docstring or None,
        language=community_chunks[0].language if community_chunks else "python",
        chunk_id=chunk_id,
    )
