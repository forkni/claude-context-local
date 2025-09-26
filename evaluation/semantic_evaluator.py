"""Semantic search evaluator for the Claude Context MCP system."""

import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from .base_evaluator import BaseEvaluator, RetrievalResult
from search.hybrid_searcher import HybridSearcher
from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder


class SemanticSearchEvaluator(BaseEvaluator):
    """Evaluator for semantic search using our hybrid search system."""

    def __init__(
        self,
        output_dir: str,
        storage_dir: Optional[str] = None,
        max_instances: Optional[int] = None,
        k: int = 10,
        use_gpu: bool = True,
        bm25_weight: float = 0.4,
        dense_weight: float = 0.6
    ):
        """
        Initialize semantic search evaluator.

        Args:
            output_dir: Output directory for results
            storage_dir: Directory for storing search indices
            max_instances: Maximum number of instances to evaluate
            k: Number of top results to consider
            use_gpu: Whether to use GPU acceleration
            bm25_weight: Weight for BM25 results in hybrid search
            dense_weight: Weight for dense vector results in hybrid search
        """
        super().__init__(output_dir, max_instances, k)

        self.storage_dir = storage_dir or str(Path(output_dir) / "search_indices")
        self.use_gpu = use_gpu
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

        # Initialize components
        self.hybrid_searcher: Optional[HybridSearcher] = None
        self.chunker = MultiLanguageChunker()
        device = "auto" if use_gpu else "cpu"
        self.embedder = CodeEmbedder(device=device)

        self.logger = logging.getLogger(self.__class__.__name__)

    def build_index(self, project_path: str) -> None:
        """
        Build search index for the given project.

        Args:
            project_path: Path to project directory
        """
        self.logger.info(f"Building index for project: {project_path}")

        # Initialize hybrid searcher
        self.hybrid_searcher = HybridSearcher(
            storage_dir=self.storage_dir,
            bm25_weight=self.bm25_weight,
            dense_weight=self.dense_weight
        )

        # Check if index already exists and is recent
        if self._should_rebuild_index(project_path):
            self.logger.info("Rebuilding search index...")
            self._build_fresh_index(project_path)
        else:
            self.logger.info("Loading existing search index...")
            success = self.hybrid_searcher.load_indices()
            if not success:
                self.logger.warning("Failed to load existing index, building new one...")
                self._build_fresh_index(project_path)

    def _should_rebuild_index(self, project_path: str) -> bool:
        """Check if we should rebuild the index."""
        try:
            # Check if indices exist
            storage_path = Path(self.storage_dir)
            bm25_path = storage_path / "bm25"
            dense_path = storage_path / "dense"

            if not (bm25_path.exists() and dense_path.exists()):
                return True

            # For now, always rebuild for fresh evaluation
            # In production, you might want to check modification times
            return True

        except Exception as e:
            self.logger.warning(f"Error checking index status: {e}")
            return True

    def _build_fresh_index(self, project_path: str) -> None:
        """Build a fresh index from scratch."""
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_path}")

        # Find all supported files
        supported_files = []
        for file_path in project_dir.rglob("*"):
            if file_path.is_file() and self.chunker.is_supported(str(file_path)):
                supported_files.append(file_path)

        self.logger.info(f"Found {len(supported_files)} supported files")

        if not supported_files:
            raise ValueError(f"No supported files found in {project_path}")

        # Chunk all files
        all_chunks = []
        documents = []
        doc_ids = []
        metadata = {}

        for file_path in supported_files:
            try:
                chunks = self.chunker.chunk_file(str(file_path))
                if chunks:
                    for i, chunk in enumerate(chunks):
                        # Generate chunk_id if not present
                        if not chunk.chunk_id:
                            chunk.chunk_id = f"{file_path.name}:{chunk.start_line}-{chunk.end_line}:{i}"

                        all_chunks.append(chunk)
                        documents.append(chunk.content)
                        doc_ids.append(chunk.chunk_id)

                        # Build metadata
                        chunk_metadata = {
                            'file_path': str(file_path.relative_to(project_dir)),
                            'language': chunk.language,
                            'chunk_type': chunk.chunk_type,
                            'start_line': chunk.start_line,
                            'end_line': chunk.end_line
                        }
                        metadata[chunk.chunk_id] = chunk_metadata

                        self.logger.debug(f"Added chunk: {chunk.chunk_id}")

            except Exception as e:
                self.logger.warning(f"Failed to chunk file {file_path}: {e}")

        self.logger.info(f"Generated {len(all_chunks)} chunks from {len(supported_files)} files")

        if not all_chunks:
            raise ValueError("No chunks generated from project files")

        # Generate embeddings
        self.logger.info("Generating embeddings for chunks...")
        start_time = time.time()
        embedding_results = self.embedder.embed_chunks(all_chunks)
        embed_time = time.time() - start_time
        self.logger.info(f"Generated {len(embedding_results)} embeddings in {embed_time:.2f}s")

        # Extract embeddings list
        embeddings = []
        for result in embedding_results:
            embeddings.append(result.embedding.tolist())

        # Index in hybrid searcher
        self.logger.info("Building hybrid search index...")
        self.hybrid_searcher.index_documents(
            documents=documents,
            doc_ids=doc_ids,
            embeddings=embeddings,
            metadata=metadata
        )

        # Save indices
        self.hybrid_searcher.save_indices()
        self.logger.info("Index building completed successfully")

    def search(self, query: str, k: int) -> List[RetrievalResult]:
        """
        Execute semantic search and return results.

        Args:
            query: Search query
            k: Number of top results to return

        Returns:
            List of retrieval results
        """
        if not self.hybrid_searcher:
            raise RuntimeError("Index not built. Call build_index() first.")

        self.logger.debug(f"Searching for: '{query}' (k={k})")

        try:
            # Execute hybrid search
            search_results = self.hybrid_searcher.search(
                query=query,
                k=k,
                use_parallel=True
            )

            # Convert to RetrievalResult format
            retrieval_results = []
            for result in search_results:
                # Extract metadata
                file_path = result.metadata.get('file_path', 'unknown')
                start_line = result.metadata.get('start_line', 0)
                end_line = result.metadata.get('end_line', 0)

                retrieval_result = RetrievalResult(
                    file_path=file_path,
                    chunk_id=result.doc_id,
                    score=result.score,
                    content=result.metadata.get('content', ''),
                    metadata=result.metadata,
                    line_start=start_line,
                    line_end=end_line
                )
                retrieval_results.append(retrieval_result)

            self.logger.debug(f"Found {len(retrieval_results)} results")
            return retrieval_results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    def get_search_stats(self) -> Dict[str, Any]:
        """Get search performance statistics."""
        if not self.hybrid_searcher:
            return {}

        return self.hybrid_searcher.get_search_mode_stats()

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.hybrid_searcher:
                self.hybrid_searcher.shutdown()
            if hasattr(self.embedder, 'cleanup'):
                self.embedder.cleanup()
            self.logger.info("Evaluator cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


class BM25OnlyEvaluator(SemanticSearchEvaluator):
    """Evaluator using only BM25 search (no dense vectors)."""

    def __init__(self, *args, **kwargs):
        kwargs.update({
            'bm25_weight': 1.0,
            'dense_weight': 0.0
        })
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _build_fresh_index(self, project_path: str) -> None:
        """Build index with only BM25 component."""
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_path}")

        # Find all supported files
        supported_files = []
        for file_path in project_dir.rglob("*"):
            if file_path.is_file() and self.chunker.is_supported(str(file_path)):
                supported_files.append(file_path)

        self.logger.info(f"Found {len(supported_files)} supported files for BM25-only index")

        # Chunk files and build documents for BM25
        documents = []
        doc_ids = []
        metadata = {}

        for file_path in supported_files:
            try:
                chunks = self.chunker.chunk_file(str(file_path))
                if chunks:
                    for chunk in chunks:
                        documents.append(chunk.content)
                        doc_ids.append(chunk.chunk_id)

                        chunk_metadata = {
                            'file_path': str(file_path.relative_to(project_dir)),
                            'language': chunk.language,
                            'chunk_type': chunk.chunk_type,
                            'start_line': chunk.start_line,
                            'end_line': chunk.end_line,
                            'content': chunk.content
                        }
                        metadata[chunk.chunk_id] = chunk_metadata

            except Exception as e:
                self.logger.warning(f"Failed to chunk file {file_path}: {e}")

        # Index only in BM25 (no embeddings)
        self.logger.info("Building BM25-only index...")
        self.hybrid_searcher.bm25_index.index_documents(
            documents=documents,
            doc_ids=doc_ids,
            metadata=metadata
        )

        # Save only BM25 index
        self.hybrid_searcher.bm25_index.save()
        self.logger.info("BM25-only index building completed")


class DenseOnlyEvaluator(SemanticSearchEvaluator):
    """Evaluator using only dense vector search (no BM25)."""

    def __init__(self, *args, **kwargs):
        kwargs.update({
            'bm25_weight': 0.0,
            'dense_weight': 1.0
        })
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)