"""Batch removal and index rebuilding operations."""

import logging
from collections.abc import Callable
from typing import Any, Optional

import numpy as np


class BatchOperations:
    """Handles batch removal and FAISS index rebuilding operations.

    This class isolates complex batch operations from CodeIndexManager,
    providing clean separation of concerns for file removal and index
    reconstruction.
    """

    def __init__(
        self,
        faiss_index: Any,  # FaissVectorIndex
        metadata_store: Any,  # MetadataStore
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize batch operations handler.

        Args:
            faiss_index: FAISS vector index instance
            metadata_store: Metadata storage instance
            logger: Optional logger (creates new if not provided)
        """
        self._faiss_index = faiss_index
        self._metadata_store = metadata_store
        self._logger = logger or logging.getLogger(__name__)

    def remove_files(
        self,
        file_paths: set[str],
        chunk_ids: list[str],
        project_name: Optional[str] = None,
        clear_index_callback: Optional[Callable] = None,
    ) -> int:
        """Remove chunks from multiple files in a single pass.

        This is much faster than calling remove_file_chunks() repeatedly,
        as it only scans through all chunks once instead of once per file.

        IMPORTANT: This method properly removes vectors from FAISS index by
        rebuilding it, which prevents index corruption and access violations.

        Args:
            file_paths: Set of file paths to remove
            chunk_ids: Current list of chunk IDs from the index
            project_name: Optional project name filter
            clear_index_callback: Callback to clear entire index if needed

        Returns:
            Total number of chunks removed
        """
        if not file_paths:
            return 0

        chunks_to_remove_ids = set()
        chunks_to_remove_positions = []

        # Single pass to identify chunks to remove
        for position, chunk_id in enumerate(chunk_ids):
            metadata_entry = self._metadata_store.get(chunk_id)
            if not metadata_entry:
                continue

            metadata = metadata_entry["metadata"]

            # Check if this chunk belongs to any of the files
            chunk_file = metadata.get("file_path") or metadata.get("relative_path")
            if not chunk_file:
                continue

            # Check if chunk matches any file in the set
            for file_path in file_paths:
                if file_path in chunk_file or chunk_file in file_path:
                    # Check project name if provided
                    if project_name and metadata.get("project_name") != project_name:
                        continue
                    chunks_to_remove_ids.add(chunk_id)
                    chunks_to_remove_positions.append(position)
                    break  # Found match, no need to check other files

        if not chunks_to_remove_ids:
            self._logger.info("No chunks found to remove")
            return 0

        self._logger.info(
            f"Removing {len(chunks_to_remove_ids)} chunks from {len(file_paths)} files"
        )

        try:
            # Rebuild FAISS index without removed chunks
            if (
                self._faiss_index.index is not None
                and self._faiss_index.index.ntotal > 0
            ):
                new_embeddings, new_chunk_ids = self._rebuild_index_without(
                    set(chunks_to_remove_positions), chunk_ids
                )

                if new_embeddings is not None and new_chunk_ids is not None:
                    # Index was successfully rebuilt
                    self._logger.info(
                        f"Rebuilt FAISS index: {self._faiss_index.ntotal} vectors "
                        f"(removed {len(chunks_to_remove_ids)})"
                    )
                else:
                    # All chunks removed, clear the index
                    self._logger.info("All chunks removed, clearing index")
                    if clear_index_callback:
                        clear_index_callback()
                    return len(chunks_to_remove_ids)

            # Remove chunks from metadata and update index_ids
            for chunk_id in chunks_to_remove_ids:
                if chunk_id in self._metadata_store:
                    self._metadata_store.delete(chunk_id)

            # Update metadata with new index positions
            # Note: chunk_ids are now from self._faiss_index.chunk_ids after rebuild
            for new_pos, chunk_id in enumerate(self._faiss_index.chunk_ids):
                if chunk_id in self._metadata_store:
                    self._metadata_store.update_index_id(chunk_id, new_pos)

            # Commit all changes
            try:
                self._metadata_store.commit()
            except Exception as e:
                self._logger.warning(f"Failed to commit metadata changes: {e}")

            self._logger.info(
                f"Successfully batch removed {len(chunks_to_remove_ids)} chunks from {len(file_paths)} files"
            )

            return len(chunks_to_remove_ids)

        except Exception as e:
            self._logger.error(f"Failed to batch remove chunks: {e}")
            import traceback

            self._logger.error(traceback.format_exc())
            # Don't leave index in corrupted state - if rebuild fails, clear it
            self._logger.warning(
                "Batch removal failed, clearing index to prevent corruption"
            )
            if clear_index_callback:
                clear_index_callback()
            raise

    def _rebuild_index_without(
        self, positions_to_remove: set[int], chunk_ids: list[str]
    ) -> tuple[Optional[np.ndarray], Optional[list[str]]]:
        """Rebuild FAISS index excluding specific positions.

        This method reconstructs the FAISS index by:
        1. Extracting embeddings at positions we want to keep
        2. Clearing the old index
        3. Creating a new index
        4. Adding back the kept embeddings

        Args:
            positions_to_remove: Set of positions to exclude
            chunk_ids: Current list of chunk IDs

        Returns:
            Tuple of (new_embeddings, new_chunk_ids) or (None, None) if all removed
        """
        # Get positions to keep (all except those being removed)
        positions_to_keep = [
            i for i in range(len(chunk_ids)) if i not in positions_to_remove
        ]

        if not positions_to_keep:
            # All chunks being removed
            return None, None

        # Reconstruct embeddings for chunks we want to keep
        embeddings_to_keep = []
        chunk_ids_to_keep = []
        for pos in positions_to_keep:
            try:
                embedding = self._faiss_index.reconstruct(int(pos))
                embeddings_to_keep.append(embedding)
                chunk_ids_to_keep.append(chunk_ids[pos])
            except Exception as e:
                self._logger.warning(
                    f"Failed to reconstruct embedding at position {pos}: {e}"
                )
                continue

        if not embeddings_to_keep:
            # No valid embeddings to keep
            self._logger.warning("No valid embeddings to keep, clearing index")
            return None, None

        # Save current state
        embeddings_array = np.array(embeddings_to_keep, dtype=np.float32)
        embedding_dim = embeddings_array.shape[1]
        was_on_gpu = self._faiss_index.is_on_gpu

        # Clear old index and create new one
        self._faiss_index.clear()
        self._faiss_index.create(embedding_dim, "flat")

        # Add kept embeddings and chunk IDs
        self._faiss_index.add(embeddings_array, chunk_ids_to_keep)

        # Restore GPU state if needed
        if was_on_gpu:
            self._faiss_index.move_to_gpu()

        return embeddings_array, chunk_ids_to_keep
