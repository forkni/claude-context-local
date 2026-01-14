"""Index synchronization and management for hybrid search.

Handles saving, loading, validation, and synchronization
of both BM25 and dense FAISS indices.
"""

import logging
import shutil
from pathlib import Path
from typing import Any, Optional

from .bm25_index import BM25Index
from .indexer import CodeIndexManager


class IndexSynchronizer:
    """Manages synchronization and persistence of BM25 and dense indices."""

    def __init__(
        self,
        storage_dir: Path,
        bm25_index: BM25Index,
        dense_index: CodeIndexManager,
        bm25_use_stopwords: bool = True,
        bm25_use_stemming: bool = True,
        project_id: Optional[str] = None,
        config=None,
        embedder=None,
    ):
        """
        Initialize index synchronizer.

        Args:
            storage_dir: Root storage directory
            bm25_index: BM25 sparse index instance
            dense_index: Dense vector index instance
            bm25_use_stopwords: BM25 stopwords configuration
            bm25_use_stemming: BM25 stemming configuration
            project_id: Project identifier for index recreation
            config: SearchConfig instance for mmap storage and other settings
            embedder: Code embedder for dimension validation during index recreation
        """
        self.storage_dir = Path(storage_dir)
        self.bm25_index = bm25_index
        self.dense_index = dense_index
        self.bm25_use_stopwords = bm25_use_stopwords
        self.bm25_use_stemming = bm25_use_stemming
        self.project_id = project_id
        self.config = config
        self.embedder = embedder
        self._logger = logging.getLogger(__name__)

    def save_indices(self) -> dict[str, Any]:
        """
        Save both BM25 and dense indices.

        Returns:
            Dictionary with save status information
        """
        try:
            self._logger.info("[SAVE] Starting save operation")

            # Log comprehensive state before save
            bm25_dir = self.storage_dir / "bm25"
            dense_size = self.dense_index.index.ntotal if self.dense_index.index else 0

            self._logger.info("[SAVE] === PRE-SAVE STATE ===")
            self._logger.info(f"[SAVE] BM25 directory exists: {bm25_dir.exists()}")
            self._logger.info(
                f"[SAVE] BM25 index size: {self.bm25_index.size} documents"
            )
            self._logger.info(
                f"[SAVE] BM25 has index: {self.bm25_index._bm25 is not None}"
            )
            self._logger.info(
                f"[SAVE] BM25 tokenized docs: {len(self.bm25_index._tokenized_docs)}"
            )
            self._logger.info(f"[SAVE] Dense index size: {dense_size} vectors")
            self._logger.info(
                f"[SAVE] Dense has index: {self.dense_index.index is not None}"
            )
            self._logger.info("[SAVE] === END PRE-SAVE STATE ===")

            # Save BM25 index
            if hasattr(self.bm25_index, "save"):
                self._logger.info("[SAVE] Calling BM25 index save...")
                self.bm25_index.save()
                self._logger.info("[SAVE] BM25 index save completed")
            else:
                self._logger.warning("[SAVE] BM25 index does not support saving")

            # Save dense index
            if hasattr(self.dense_index, "save_index"):
                self._logger.info("[SAVE] Calling dense index save_index...")
                self.dense_index.save_index()
                self._logger.info("[SAVE] Dense index save completed")
            elif hasattr(self.dense_index, "save"):
                self._logger.info("[SAVE] Calling dense index save...")
                self.dense_index.save()
                self._logger.info("[SAVE] Dense index save completed")
            else:
                self._logger.warning("[SAVE] Dense index does not support saving")

            # Verify files after save
            self._verify_bm25_files()

            # Log comprehensive state after save
            dense_size_after = (
                self.dense_index.index.ntotal if self.dense_index.index else 0
            )

            self._logger.info("[SAVE] === POST-SAVE STATE ===")
            self._logger.info(f"[SAVE] BM25 directory exists: {bm25_dir.exists()}")
            if bm25_dir.exists():
                files = list(bm25_dir.iterdir())
                self._logger.info(f"[SAVE] BM25 files: {[f.name for f in files]}")
            self._logger.info(
                f"[SAVE] BM25 index size: {self.bm25_index.size} documents"
            )
            self._logger.info(
                f"[SAVE] BM25 has index: {self.bm25_index._bm25 is not None}"
            )
            self._logger.info(f"[SAVE] Dense index size: {dense_size_after} vectors")
            self._logger.info(
                f"[SAVE] Dense has index: {self.dense_index.index is not None}"
            )
            self._logger.info("[SAVE] === END POST-SAVE STATE ===")

            self._logger.info("[SAVE] Hybrid indices saved successfully")

            # Validate sync after save
            is_synced = self.validate_index_sync()

            return {
                "success": True,
                "bm25_size": self.bm25_index.size,
                "dense_size": dense_size_after,
                "synced": is_synced,
            }

        except Exception as e:
            self._logger.error(f"[SAVE] Failed to save indices: {e}")
            raise

    def validate_index_sync(self) -> bool:
        """
        Validate BM25 and Dense indices are synchronized.

        Checks if both indices have the same number of documents. If desynchronization
        is detected, logs a warning with the counts.

        Returns:
            True if indices are synced, False otherwise
        """
        bm25_count = len(self.bm25_index._doc_ids) if self.bm25_index else 0
        dense_count = (
            self.dense_index.ntotal
            if self.dense_index and self.dense_index.index
            else 0
        )

        if bm25_count != dense_count:
            self._logger.warning(
                f"[SYNC_CHECK] Index desync detected: BM25={bm25_count}, Dense={dense_count}"
            )
            return False

        self._logger.info(f"[SYNC_CHECK] Indices synced at {bm25_count} documents")
        return True

    def resync_bm25_from_dense(self) -> int:
        """
        Rebuild BM25 index from dense index metadata.
        Called automatically when desync detected during incremental indexing.

        Returns:
            Number of documents synced to BM25
        """
        self._logger.info("[RESYNC] Starting BM25 resync from dense metadata...")

        # Get all chunk IDs from dense index
        if not hasattr(self.dense_index, "chunk_ids") or not self.dense_index.chunk_ids:
            self._logger.warning("[RESYNC] No chunks in dense index")
            return 0

        documents = []
        doc_ids = []
        metadata = {}

        for chunk_id in self.dense_index.chunk_ids:
            entry = self.dense_index.metadata_store.get(chunk_id)
            if entry:
                content = entry["metadata"].get("content", "")
                if content:
                    documents.append(content)
                    doc_ids.append(chunk_id)
                    metadata[chunk_id] = entry["metadata"]

        if not documents:
            self._logger.error("[RESYNC] No content found in dense metadata")
            return 0

        self._logger.info(f"[RESYNC] Found {len(documents)} documents to sync")

        # Rebuild BM25 index
        self.bm25_index = BM25Index(
            str(self.storage_dir / "bm25"),
            use_stopwords=self.bm25_use_stopwords,
            use_stemming=self.bm25_use_stemming,
        )
        self.bm25_index.index_documents(documents, doc_ids, metadata)
        self.bm25_index.save()

        self._logger.info(f"[RESYNC] BM25 rebuilt: {self.bm25_index.size} documents")
        return self.bm25_index.size

    def load_indices(self) -> bool:
        """
        Load both BM25 and dense indices.

        Returns:
            True if both loaded successfully, False otherwise
        """
        try:
            bm25_loaded = self.bm25_index.load()
            dense_loaded = self.dense_index.load()

            success = bm25_loaded and dense_loaded
            if success:
                self._logger.info("Hybrid indices loaded successfully")
            else:
                self._logger.warning(
                    f"Index loading partial: BM25={bm25_loaded}, Dense={dense_loaded}"
                )

            return success

        except Exception as e:
            self._logger.error(f"Failed to load indices: {e}")
            return False

    def clear_index(self) -> None:
        """
        Clear both BM25 and dense indices.
        Compatible with incremental indexer interface.
        """
        self._logger.info("Clearing hybrid indices")

        try:
            # DELETE BM25 files from disk FIRST
            bm25_dir = self.storage_dir / "bm25"
            if bm25_dir.exists():
                shutil.rmtree(bm25_dir)
                self._logger.info(f"Deleted BM25 directory: {bm25_dir}")

            # Recreate empty BM25 index with same configuration
            self.bm25_index = BM25Index(
                str(self.storage_dir / "bm25"),
                use_stopwords=self.bm25_use_stopwords,
                use_stemming=self.bm25_use_stemming,
            )

            # Clear dense index - MUST close metadata before recreating
            if self.dense_index is not None:
                self.dense_index.clear_index()

                # CRITICAL: Close metadata store AGAIN (clear_index reopens it at the end)
                # This prevents file lock [WinError 32] on Windows when creating new CodeIndexManager
                if (
                    hasattr(self.dense_index, "_metadata_store")
                    and self.dense_index._metadata_store is not None
                ):
                    self.dense_index._metadata_store.close()
                    self._logger.debug(
                        "Closed old dense_index metadata store before recreation"
                    )

                # Release reference to allow garbage collection
                self.dense_index = None

            # Force garbage collection to release file handles (Windows)
            import gc

            gc.collect()

            # Recreate with clean state (preserve project_id, config, and embedder for dimension validation)
            # NOW safe - old metadata store is closed and garbage collected
            self.dense_index = CodeIndexManager(
                str(self.storage_dir),
                embedder=self.embedder,
                project_id=self.project_id,
                config=self.config,
            )

            self._logger.info("Successfully cleared hybrid indices")
        except Exception as e:
            self._logger.error(f"Failed to clear hybrid indices: {e}")
            raise

    def remove_file_chunks(self, file_path: str, project_name: str) -> int:
        """
        Remove chunks for a specific file from both indices.
        Compatible with incremental indexer interface.

        Args:
            file_path: Relative path of the file
            project_name: Name of the project

        Returns:
            Number of chunks removed
        """
        self._logger.debug(f"Removing chunks for file: {file_path}")

        try:
            removed_count = 0

            # Remove from dense index
            if hasattr(self.dense_index, "remove_file_chunks"):
                removed_dense = self.dense_index.remove_file_chunks(
                    file_path, project_name
                )
                removed_count += removed_dense
                self._logger.debug(f"Removed {removed_dense} chunks from dense index")

            # Remove from BM25 index
            if hasattr(self.bm25_index, "remove_file_chunks"):
                removed_bm25 = self.bm25_index.remove_file_chunks(
                    file_path, project_name
                )
                removed_count += removed_bm25
                self._logger.debug(f"Removed {removed_bm25} chunks from BM25 index")
            else:
                self._logger.warning("BM25 index does not support file chunk removal")

            self._logger.info(
                f"Removed {removed_count} total chunks for file: {file_path}"
            )
            return removed_count

        except Exception as e:
            self._logger.error(f"Failed to remove chunks for file {file_path}: {e}")
            return 0

    def remove_multiple_files(self, file_paths: set, project_name: str) -> int:
        """
        Remove chunks for multiple files from both indices in a single pass.
        Much faster than calling remove_file_chunks repeatedly.

        IMPORTANT: This method properly removes chunks from both FAISS and BM25 indices,
        preventing index corruption.

        Args:
            file_paths: Set of file paths to remove
            project_name: Name of the project

        Returns:
            Total number of chunks removed
        """
        self._logger.info(
            f"Batch removing chunks for {len(file_paths)} files from hybrid indices"
        )

        removed_count = 0
        dense_failed = False
        bm25_failed = False

        # Remove from dense index
        if hasattr(self.dense_index, "remove_multiple_files"):
            try:
                removed_dense = self.dense_index.remove_multiple_files(
                    file_paths, project_name
                )
                removed_count += removed_dense
                self._logger.info(
                    f"Batch removed {removed_dense} chunks from dense (FAISS) index"
                )
            except Exception as e:
                self._logger.error(f"Failed to batch remove from dense index: {e}")
                import traceback

                self._logger.error(traceback.format_exc())
                dense_failed = True

        # Remove from BM25 index
        if hasattr(self.bm25_index, "remove_multiple_files"):
            try:
                removed_bm25 = self.bm25_index.remove_multiple_files(
                    file_paths, project_name
                )
                removed_count += removed_bm25
                self._logger.info(
                    f"Batch removed {removed_bm25} chunks from BM25 index"
                )
            except Exception as e:
                self._logger.error(f"Failed to batch remove from BM25 index: {e}")
                import traceback

                self._logger.error(traceback.format_exc())
                bm25_failed = True
        else:
            self._logger.warning("BM25 index does not support batch file chunk removal")

        # If both failed, raise exception to trigger error recovery
        if dense_failed and bm25_failed:
            raise RuntimeError(
                "Batch removal failed for both dense and BM25 indices. "
                "Indices may be in corrupted state."
            )

        self._logger.info(
            f"Batch removed {removed_count} total chunks for {len(file_paths)} files"
        )
        return removed_count

    def _verify_bm25_files(self) -> None:
        """Verify BM25 files exist and are non-empty."""
        bm25_dir = Path(self.bm25_index.storage_dir)
        expected_files = ["bm25.index", "bm25_docs.json", "bm25_metadata.json"]

        self._logger.info(f"[VERIFY] Checking BM25 files in: {bm25_dir}")

        for filename in expected_files:
            filepath = bm25_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                if size == 0:
                    self._logger.error(f"[VERIFY] {filename} exists but is EMPTY")
                else:
                    self._logger.info(f"[VERIFY] {filename} exists ({size} bytes)")
            else:
                self._logger.warning(f"[VERIFY] {filename} NOT FOUND")
