"""Unit tests for MmapVectorStorage."""

import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from search.mmap_vectors import MmapVectorStorage
from search.symbol_cache import SymbolHashCache


class TestMmapVectorStorage(unittest.TestCase):
    """Test MmapVectorStorage functionality."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.test_file = self.temp_path / "test_vectors.mmap"
        self.dimension = 768

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # === Binary Format Tests ===

    def test_header_format(self):
        """Test binary header format is correct."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]

        storage.save(embeddings, chunk_ids)

        # Read and verify header
        with open(self.test_file, "rb") as f:
            magic = f.read(4)
            version, dim, count = struct.unpack("<III", f.read(12))
            reserved = struct.unpack("<Q", f.read(8))[0]

        self.assertEqual(magic, b"CVEC")
        self.assertEqual(version, 1)
        self.assertEqual(dim, self.dimension)
        self.assertEqual(count, 5)
        self.assertEqual(reserved, 0)

    def test_entry_format(self):
        """Test per-vector entry format is correct."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(3, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(3)]

        storage.save(embeddings, chunk_ids)

        # Read and verify first entry
        with open(self.test_file, "rb") as f:
            f.seek(24)  # Skip header
            idx = struct.unpack("<I", f.read(4))[0]
            hash_val = struct.unpack("<Q", f.read(8))[0]
            vector_data = f.read(self.dimension * 4)

        self.assertEqual(idx, 0)
        self.assertEqual(hash_val, SymbolHashCache.fnv1a_hash(chunk_ids[0]))
        self.assertEqual(len(vector_data), self.dimension * 4)

    # === Save/Load Tests ===

    def test_save_and_load(self):
        """Test basic save and load cycle."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(10, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(10)]

        # Save
        storage.save(embeddings, chunk_ids)
        self.assertTrue(self.test_file.exists())

        # Load
        storage2 = MmapVectorStorage(self.test_file, self.dimension)
        self.assertTrue(storage2.load())
        self.assertTrue(storage2.is_loaded)
        self.assertEqual(storage2.count, 10)
        self.assertEqual(storage2.dimension, self.dimension)

    def test_save_creates_parent_directory(self):
        """Test save creates parent directories if needed."""
        nested_path = self.temp_path / "nested" / "path" / "vectors.mmap"
        storage = MmapVectorStorage(nested_path, self.dimension)
        embeddings = np.random.randn(3, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(3)]

        storage.save(embeddings, chunk_ids)
        self.assertTrue(nested_path.exists())

    def test_load_nonexistent_file(self):
        """Test load returns False for nonexistent file."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        self.assertFalse(storage.load())
        self.assertFalse(storage.is_loaded)
        self.assertEqual(storage.count, 0)

    # === Vector Retrieval Tests ===

    def test_get_vector_valid_index(self):
        """Test retrieving vector with valid index."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]

        storage.save(embeddings, chunk_ids)
        storage.load()

        for i in range(5):
            retrieved = storage.get_vector(i)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.shape, (self.dimension,))
            np.testing.assert_array_almost_equal(retrieved, embeddings[i], decimal=5)

    def test_get_vector_invalid_index(self):
        """Test retrieving vector with invalid index returns None."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]

        storage.save(embeddings, chunk_ids)
        storage.load()

        # Out of range indices
        self.assertIsNone(storage.get_vector(-1))
        self.assertIsNone(storage.get_vector(5))
        self.assertIsNone(storage.get_vector(100))

    def test_get_vector_not_loaded(self):
        """Test get_vector returns None when not loaded."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        self.assertIsNone(storage.get_vector(0))

    # === Validation Tests ===

    def test_save_embeddings_chunk_ids_mismatch(self):
        """Test save raises error when counts don't match."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(3)]

        with self.assertRaises(ValueError) as cm:
            storage.save(embeddings, chunk_ids)
        self.assertIn("doesn't match chunk_ids count", str(cm.exception))

    def test_save_wrong_dimension(self):
        """Test save raises error when dimension doesn't match."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(5, 1024).astype(np.float32)  # Wrong dimension
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]

        with self.assertRaises(ValueError) as cm:
            storage.save(embeddings, chunk_ids)
        self.assertIn("doesn't match expected dimension", str(cm.exception))

    def test_save_indices_chunk_ids_mismatch(self):
        """Test save raises error when indices count doesn't match."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]
        indices = [0, 1, 2]  # Wrong count

        with self.assertRaises(ValueError) as cm:
            storage.save(embeddings, chunk_ids, indices)
        self.assertIn("doesn't match chunk_ids count", str(cm.exception))

    def test_load_invalid_magic(self):
        """Test load fails with invalid magic bytes."""
        # Create file with wrong magic
        with open(self.test_file, "wb") as f:
            f.write(b"XXXX")  # Wrong magic
            f.write(struct.pack("<III", 1, self.dimension, 5))
            f.write(struct.pack("<Q", 0))

        storage = MmapVectorStorage(self.test_file, self.dimension)
        self.assertFalse(storage.load())
        self.assertFalse(storage.is_loaded)

    def test_load_unsupported_version(self):
        """Test load fails with unsupported version."""
        # Create file with wrong version
        with open(self.test_file, "wb") as f:
            f.write(b"CVEC")
            f.write(struct.pack("<III", 999, self.dimension, 5))  # Wrong version
            f.write(struct.pack("<Q", 0))

        storage = MmapVectorStorage(self.test_file, self.dimension)
        self.assertFalse(storage.load())
        self.assertFalse(storage.is_loaded)

    def test_load_dimension_mismatch(self):
        """Test load fails when dimension doesn't match."""
        # Create file with different dimension
        storage = MmapVectorStorage(self.test_file, 1024)  # Different dimension
        embeddings = np.random.randn(5, 1024).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]
        storage.save(embeddings, chunk_ids)

        # Try to load with different dimension
        storage2 = MmapVectorStorage(self.test_file, self.dimension)  # 768
        self.assertFalse(storage2.load())
        self.assertFalse(storage2.is_loaded)

    # === Resource Management Tests ===

    def test_close(self):
        """Test close releases resources."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]

        storage.save(embeddings, chunk_ids)
        storage.load()

        self.assertTrue(storage.is_loaded)
        self.assertEqual(storage.count, 5)

        storage.close()

        self.assertFalse(storage.is_loaded)
        self.assertEqual(storage.count, 0)
        self.assertIsNone(storage.get_vector(0))

    def test_multiple_close(self):
        """Test calling close multiple times is safe."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]

        storage.save(embeddings, chunk_ids)
        storage.load()

        storage.close()
        storage.close()  # Should not raise
        storage.close()  # Should not raise

    def test_destructor_cleanup(self):
        """Test destructor calls close."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]

        storage.save(embeddings, chunk_ids)
        storage.load()

        # Trigger destructor
        del storage
        # No assertion - just verify no errors

    # === Custom Indices Tests ===

    def test_save_with_custom_indices(self):
        """Test save with custom index values."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.random.randn(3, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(3)]
        indices = [10, 20, 30]

        storage.save(embeddings, chunk_ids, indices)
        storage.load()

        # Verify vectors are retrievable by their custom indices
        for i, _idx in enumerate(indices):
            vector = storage.get_vector(i)  # Still use sequential access
            self.assertIsNotNone(vector)
            np.testing.assert_array_almost_equal(vector, embeddings[i], decimal=5)

    # === Edge Cases ===

    def test_empty_storage(self):
        """Test saving/loading empty storage."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        embeddings = np.array([]).reshape(0, self.dimension).astype(np.float32)
        chunk_ids = []

        storage.save(embeddings, chunk_ids)
        storage.load()

        self.assertTrue(storage.is_loaded)
        self.assertEqual(storage.count, 0)
        self.assertIsNone(storage.get_vector(0))

    def test_large_storage(self):
        """Test saving/loading many vectors."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        count = 1000
        embeddings = np.random.randn(count, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(count)]

        storage.save(embeddings, chunk_ids)
        storage.load()

        self.assertEqual(storage.count, count)

        # Spot check a few vectors
        for i in [0, count // 2, count - 1]:
            retrieved = storage.get_vector(i)
            np.testing.assert_array_almost_equal(retrieved, embeddings[i], decimal=5)

    def test_different_dimensions(self):
        """Test with different embedding dimensions."""
        for dim in [384, 768, 1024, 2048]:
            test_file = self.temp_path / f"vectors_{dim}d.mmap"
            storage = MmapVectorStorage(test_file, dim)
            embeddings = np.random.randn(5, dim).astype(np.float32)
            chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]

            storage.save(embeddings, chunk_ids)
            storage.load()

            self.assertEqual(storage.dimension, dim)
            self.assertEqual(storage.count, 5)

            vector = storage.get_vector(0)
            self.assertEqual(vector.shape, (dim,))

    # === Properties Tests ===

    def test_properties(self):
        """Test property accessors."""
        storage = MmapVectorStorage(self.test_file, self.dimension)

        # Before save/load
        self.assertEqual(storage.dimension, self.dimension)
        self.assertEqual(storage.count, 0)
        self.assertFalse(storage.is_loaded)

        # After save
        embeddings = np.random.randn(7, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(7)]
        storage.save(embeddings, chunk_ids)

        # After load
        storage.load()
        self.assertEqual(storage.dimension, self.dimension)
        self.assertEqual(storage.count, 7)
        self.assertTrue(storage.is_loaded)

    def test_repr(self):
        """Test string representation."""
        storage = MmapVectorStorage(self.test_file, self.dimension)
        repr_str = repr(storage)

        self.assertIn("MmapVectorStorage", repr_str)
        self.assertIn(str(self.test_file.name), repr_str)
        self.assertIn(str(self.dimension), repr_str)
        self.assertIn("closed", repr_str)

        # After load
        embeddings = np.random.randn(5, self.dimension).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(5)]
        storage.save(embeddings, chunk_ids)
        storage.load()

        repr_str = repr(storage)
        self.assertIn("loaded", repr_str)
        self.assertIn(str(5), repr_str)


if __name__ == "__main__":
    unittest.main()
