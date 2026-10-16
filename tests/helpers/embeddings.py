"""Shared embedding helper functions for the test suite.

Moved from tests/conftest.py so they can be imported as a real module
(``from tests.helpers.embeddings import create_test_embeddings``) rather than
via the ``from conftest import`` anti-pattern that relies on accidental sys.path.
"""

import hashlib
from typing import Any

import numpy as np


try:
    from embeddings.embedder import EmbeddingResult
except ImportError:
    EmbeddingResult = None  # type: ignore[assignment]


def generate_chunk_id(chunk: Any) -> str:
    """Generate chunk ID like the embedder does.

    Args:
        chunk: Code chunk with relative_path, start_line, end_line, chunk_type,
               and optional name

    Returns:
        Chunk ID string in format: "path:start-end:type" or "path:start-end:type:name"
    """
    chunk_id = (
        f"{chunk.relative_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
    )
    if chunk.name:
        chunk_id += f":{chunk.name}"
    return chunk_id


class DeterministicQueryEmbedder:
    """Query-side stub matching create_test_embeddings' deterministic mode.

    Pass this instead of embedder=None when a test indexes deterministic
    embeddings and then searches. With embedder=None, SearchExecutor.search_dense
    lazily builds a real CodeEmbedder under get_storage_dir()/"models", which the
    session storage redirect points at an empty tmp dir, so every run downloads
    the full BAAI/bge-m3 checkpoint (~2.3 GB) and trips pytest-timeout. The real
    model's 1024-d vectors would not match a 768-d deterministic index anyway.
    """

    model_name = "deterministic-test-embedder"

    def __init__(self, embedding_dim: int = 768) -> None:
        self.embedding_dim = embedding_dim

    def embed_query(self, query: str) -> np.ndarray:
        seed = int(hashlib.sha256(query.encode()).hexdigest(), 16) % 10000
        return np.random.RandomState(seed).random(self.embedding_dim).astype(np.float32)

    def get_model_info(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
        }


def create_test_embeddings(
    chunks: list[Any], embedder: Any | None = None, embedding_dim: int = 768
) -> list[Any]:
    """Create embeddings from chunks for testing.

    Supports two modes:
    1. Deterministic mode (embedder=None): Fast, reproducible embeddings for unit tests
    2. Real embedder mode (embedder provided): Actual embeddings for integration tests

    Args:
        chunks: List of code chunks to embed
        embedder: Optional CodeEmbedder instance. If None, uses deterministic embeddings
        embedding_dim: Embedding dimension for deterministic mode (default: 768)

    Returns:
        List of EmbeddingResult objects with embeddings, chunk_ids, and metadata
    """
    if not EmbeddingResult:
        raise ImportError("EmbeddingResult not available")

    embeddings = []

    # Mode 1: Real embedder provided - use it for actual embeddings
    if embedder:
        # CodeEmbedder.embed_chunks() builds chunk_id/metadata itself from the
        # CodeChunk objects (embeddings/embedder.py _build_chunk_id /
        # _build_chunk_metadata) — there is no embed_batch(texts=..., ...)
        # API to hand-assemble those for; embed_chunks is the current surface
        # (see also the indexed_project fixture in
        # test_relationship_extraction_integration.py).
        return embedder.embed_chunks(chunks)

    # Mode 2: No embedder - use deterministic embeddings for fast tests
    for chunk in chunks:
        # Create deterministic embedding based on content hash. hash() is
        # randomized per-process (PYTHONHASHSEED), which would make this
        # "deterministic" embedding vary across test runs/workers -- use
        # hashlib.sha256 for a genuinely stable seed.
        content_hash = (
            int(hashlib.sha256(chunk.content.encode()).hexdigest(), 16) % 10000
        )
        embedding = (
            np.random.RandomState(content_hash).random(embedding_dim).astype(np.float32)
        )

        chunk_id = generate_chunk_id(chunk)
        metadata = {
            "name": chunk.name,
            "chunk_type": chunk.chunk_type,
            "file_path": chunk.file_path,
            "relative_path": chunk.relative_path,
            "folder_structure": chunk.folder_structure,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "docstring": chunk.docstring,
            "tags": chunk.tags,
            "complexity_score": chunk.complexity_score,
            "content": chunk.content,  # Full content for BM25 indexing
            "content_preview": (
                chunk.content[:200] + "..."
                if len(chunk.content) > 200
                else chunk.content
            ),
        }

        result = EmbeddingResult(
            embedding=embedding, chunk_id=chunk_id, metadata=metadata
        )
        embeddings.append(result)

    return embeddings
