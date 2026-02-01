"""Generate synthetic file-level module summary chunks."""

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from chunking.python_ast_chunker import CodeChunk


def generate_file_summaries(chunks: list["CodeChunk"]) -> list["CodeChunk"]:
    """Create one module-summary CodeChunk per file that has 2+ real chunks.

    Args:
        chunks: All CodeChunks from the indexing pass

    Returns:
        List of synthetic module CodeChunks (one per qualifying file)
    """
    # Group chunks by file
    by_file: dict[str, list["CodeChunk"]] = defaultdict(list)
    for chunk in chunks:
        by_file[chunk.relative_path].append(chunk)

    summaries = []
    for rel_path, file_chunks in by_file.items():
        if len(file_chunks) < 2:
            continue  # Skip single-chunk files (the chunk IS the file)
        summaries.append(_build_file_summary(rel_path, file_chunks))

    return summaries


def _build_file_summary(rel_path: str, file_chunks: list["CodeChunk"]) -> "CodeChunk":
    """Build a synthetic module CodeChunk from a file's chunks."""
    from chunking.python_ast_chunker import CodeChunk

    module_name = Path(rel_path).stem
    folder_structure = list(Path(rel_path).parent.parts)

    # Collect metadata
    classes = []
    functions = []
    methods = []
    all_imports = []
    docstring_lines = []

    for chunk in file_chunks:
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

    # Build summary text
    parts = [f"# {rel_path} | module {module_name}"]

    symbol_count = len(classes) + len(functions) + len(methods)
    package = folder_structure[0] if folder_structure else "root"
    parts.append(f"# Module containing {symbol_count} symbols in the {package} package")

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

    if docstring_lines:
        parts.extend(docstring_lines[:5])

    content = "\n".join(parts)

    # Aggregate docstring for embedding
    agg_docstring = "; ".join(
        f"{c.name}: {c.docstring.strip().split(chr(10))[0][:80]}"
        for c in file_chunks
        if c.docstring and c.name
    )[:500]

    chunk_id = f"{_normalize_path(rel_path)}:0-0:module:{module_name}"

    return CodeChunk(
        content=content,
        chunk_type="module",
        start_line=0,
        end_line=0,
        file_path=file_chunks[0].file_path,
        relative_path=rel_path,
        folder_structure=folder_structure,
        name=module_name,
        docstring=agg_docstring or None,
        language=file_chunks[0].language,
        chunk_id=chunk_id,
    )


def _normalize_path(path: str) -> str:
    """Normalize path separators to forward slashes."""
    return path.replace("\\", "/")
