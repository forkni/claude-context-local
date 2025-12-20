"""Unit tests for BatchOperations class."""

from unittest import TestCase
from unittest.mock import Mock

import numpy as np

from search.batch_operations import BatchOperations


class TestBatchOperations(TestCase):
    """Test BatchOperations functionality."""

    def setUp(self):
        """Set up test environment."""
        self.mock_faiss_index = Mock()
        self.mock_metadata_store = Mock()
        self.batch_ops = BatchOperations(
            self.mock_faiss_index, self.mock_metadata_store
        )

    def test_remove_files_empty_set(self):
        """Test removing empty file set."""
        result = self.batch_ops.remove_files(set(), [])

        self.assertEqual(result, 0)
        self.mock_metadata_store.get.assert_not_called()

    def test_remove_files_single_file(self):
        """Test removing chunks from a single file."""
        # Setup
        chunk_ids = [
            "file1.py:1-10:function:func1",
            "file2.py:1-10:function:func2",
            "file1.py:11-20:function:func3",
        ]

        # Mock metadata store responses
        def get_metadata(chunk_id):
            if "file1.py" in chunk_id:
                return {
                    "metadata": {
                        "file_path": "file1.py",
                        "relative_path": "file1.py",
                    }
                }
            else:
                return {
                    "metadata": {
                        "file_path": "file2.py",
                        "relative_path": "file2.py",
                    }
                }

        self.mock_metadata_store.get.side_effect = get_metadata
        self.mock_metadata_store.__contains__ = lambda self, x: True

        # Mock FAISS index
        self.mock_faiss_index.index = Mock()
        self.mock_faiss_index.index.ntotal = 3
        self.mock_faiss_index.is_on_gpu = False
        self.mock_faiss_index.chunk_ids = ["file2.py:1-10:function:func2"]

        def mock_reconstruct(pos):
            return np.ones(768, dtype=np.float32) * pos

        self.mock_faiss_index.reconstruct.side_effect = mock_reconstruct

        # Execute
        result = self.batch_ops.remove_files({"file1.py"}, chunk_ids)

        # Verify
        self.assertEqual(result, 2)  # Should remove 2 chunks from file1.py
        self.mock_faiss_index.clear.assert_called_once()
        self.mock_faiss_index.create.assert_called_once()
        self.mock_metadata_store.delete.assert_called()

    def test_remove_files_no_matching_chunks(self):
        """Test removing files with no matching chunks."""
        chunk_ids = ["file1.py:1-10:function:func1"]

        self.mock_metadata_store.get.return_value = {
            "metadata": {"file_path": "file1.py", "relative_path": "file1.py"}
        }

        result = self.batch_ops.remove_files({"file2.py"}, chunk_ids)

        self.assertEqual(result, 0)
        self.mock_faiss_index.clear.assert_not_called()

    def test_remove_files_with_project_filter(self):
        """Test removing files with project name filter."""
        chunk_ids = ["file1.py:1-10:function:func1"]

        self.mock_metadata_store.get.return_value = {
            "metadata": {
                "file_path": "file1.py",
                "relative_path": "file1.py",
                "project_name": "project_a",
            }
        }

        # Should not match because project name differs
        result = self.batch_ops.remove_files(
            {"file1.py"}, chunk_ids, project_name="project_b"
        )

        self.assertEqual(result, 0)

    def test_remove_files_all_chunks(self):
        """Test removing all chunks (should invoke clear callback)."""
        chunk_ids = ["file1.py:1-10:function:func1", "file1.py:11-20:function:func2"]

        self.mock_metadata_store.get.return_value = {
            "metadata": {"file_path": "file1.py", "relative_path": "file1.py"}
        }

        self.mock_faiss_index.index = Mock()
        self.mock_faiss_index.index.ntotal = 2

        clear_callback = Mock()

        result = self.batch_ops.remove_files(
            {"file1.py"}, chunk_ids, clear_index_callback=clear_callback
        )

        # All chunks removed, should invoke clear callback
        self.assertEqual(result, 2)
        clear_callback.assert_called_once()

    def test_rebuild_index_without_partial(self):
        """Test rebuilding index with some chunks removed."""
        chunk_ids = [
            "file1.py:1-10:function:func1",
            "file2.py:1-10:function:func2",
            "file3.py:1-10:function:func3",
        ]

        # Remove position 1 (file2.py)
        positions_to_remove = {1}

        # Mock reconstruct to return different embeddings
        def mock_reconstruct(pos):
            return np.ones(768, dtype=np.float32) * pos

        self.mock_faiss_index.reconstruct.side_effect = mock_reconstruct
        self.mock_faiss_index.is_on_gpu = False

        new_embeddings, new_chunk_ids = self.batch_ops._rebuild_index_without(
            positions_to_remove, chunk_ids
        )

        # Verify
        self.assertIsNotNone(new_embeddings)
        self.assertIsNotNone(new_chunk_ids)
        self.assertEqual(len(new_chunk_ids), 2)  # Should have 2 chunks left
        self.assertIn("file1.py:1-10:function:func1", new_chunk_ids)
        self.assertIn("file3.py:1-10:function:func3", new_chunk_ids)
        self.assertNotIn("file2.py:1-10:function:func2", new_chunk_ids)

        # Should clear and recreate index
        self.mock_faiss_index.clear.assert_called_once()
        self.mock_faiss_index.create.assert_called_once()
        self.mock_faiss_index.add.assert_called_once()

    def test_rebuild_index_without_all_chunks(self):
        """Test rebuilding when all chunks are removed."""
        chunk_ids = ["file1.py:1-10:function:func1", "file2.py:1-10:function:func2"]

        # Remove all positions
        positions_to_remove = {0, 1}

        new_embeddings, new_chunk_ids = self.batch_ops._rebuild_index_without(
            positions_to_remove, chunk_ids
        )

        # Should return None when all chunks removed
        self.assertIsNone(new_embeddings)
        self.assertIsNone(new_chunk_ids)

    def test_rebuild_index_without_gpu_preservation(self):
        """Test that GPU state is preserved during rebuild."""
        chunk_ids = ["file1.py:1-10:function:func1", "file2.py:1-10:function:func2"]

        positions_to_remove = {1}

        self.mock_faiss_index.reconstruct.return_value = np.ones(768, dtype=np.float32)
        self.mock_faiss_index.is_on_gpu = True  # Index was on GPU

        self.batch_ops._rebuild_index_without(positions_to_remove, chunk_ids)

        # Should move back to GPU after rebuild
        self.mock_faiss_index.move_to_gpu.assert_called_once()

    def test_rebuild_index_without_failed_reconstruction(self):
        """Test rebuild handles failed embedding reconstruction."""
        chunk_ids = ["file1.py:1-10:function:func1", "file2.py:1-10:function:func2"]

        positions_to_remove = {0}

        # First reconstruction succeeds, but we're removing it
        # Second reconstruction fails
        def mock_reconstruct(pos):
            if pos == 1:
                raise Exception("Reconstruction failed")
            return np.ones(768, dtype=np.float32)

        self.mock_faiss_index.reconstruct.side_effect = mock_reconstruct

        new_embeddings, new_chunk_ids = self.batch_ops._rebuild_index_without(
            positions_to_remove, chunk_ids
        )

        # Should return None because no valid embeddings to keep
        self.assertIsNone(new_embeddings)
        self.assertIsNone(new_chunk_ids)

    def test_remove_files_error_handling(self):
        """Test error handling during batch removal."""
        chunk_ids = ["file1.py:1-10:function:func1"]

        self.mock_metadata_store.get.return_value = {
            "metadata": {"file_path": "file1.py"}
        }

        # Force an error during rebuild (all reconstructions fail)
        self.mock_faiss_index.index = Mock()
        self.mock_faiss_index.index.ntotal = 1
        self.mock_faiss_index.reconstruct.side_effect = Exception("Test error")

        clear_callback = Mock()

        # When all reconstructions fail, it should invoke clear callback and return
        result = self.batch_ops.remove_files(
            {"file1.py"}, chunk_ids, clear_index_callback=clear_callback
        )

        # Should have removed 1 chunk and cleared the index
        self.assertEqual(result, 1)
        clear_callback.assert_called_once()

    def test_remove_files_metadata_cleanup(self):
        """Test metadata is properly cleaned up after removal."""
        chunk_ids = ["file1.py:1-10:function:func1", "file2.py:1-10:function:func2"]

        def get_metadata(chunk_id):
            if "file1.py" in chunk_id:
                return {"metadata": {"file_path": "file1.py"}}
            else:
                return {"metadata": {"file_path": "file2.py"}}

        self.mock_metadata_store.get.side_effect = get_metadata
        self.mock_metadata_store.__contains__ = lambda self, x: True

        self.mock_faiss_index.index = Mock()
        self.mock_faiss_index.index.ntotal = 2
        self.mock_faiss_index.is_on_gpu = False
        self.mock_faiss_index.chunk_ids = ["file2.py:1-10:function:func2"]

        def mock_reconstruct(pos):
            return np.ones(768, dtype=np.float32)

        self.mock_faiss_index.reconstruct.side_effect = mock_reconstruct

        self.batch_ops.remove_files({"file1.py"}, chunk_ids)

        # Verify metadata deletion was called
        self.mock_metadata_store.delete.assert_called()
        # Verify commit was called
        self.mock_metadata_store.commit.assert_called_once()


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
