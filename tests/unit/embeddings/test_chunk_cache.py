"""Unit tests for ChunkEmbeddingCache (persistent content-hash embedding cache)."""

import sys
from pathlib import Path

import numpy as np


# Add project root to path to allow imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from embeddings.chunk_cache import ChunkEmbeddingCache  # noqa: E402


def _vec(dim: int, value: float) -> np.ndarray:
    return np.full(dim, value, dtype=np.float32)


class TestKeyFor:
    """key_for() must be a pure, deterministic hash of the assembled content."""

    def test_deterministic(self):
        content = "some assembled embedding content"
        assert ChunkEmbeddingCache.key_for(content) == ChunkEmbeddingCache.key_for(
            content
        )

    def test_different_content_different_key(self):
        assert ChunkEmbeddingCache.key_for("a") != ChunkEmbeddingCache.key_for("b")

    def test_key_is_32_hex_chars(self):
        # 128-bit truncated SHA-256 -> 32 hex chars.
        key = ChunkEmbeddingCache.key_for("anything")
        assert len(key) == 32
        int(key, 16)  # raises ValueError if not valid hex


class TestSaveLoadRoundTrip:
    def test_round_trip_bit_identical(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(cache_path, model_name="BAAI/bge-m3", dimension=4)

        vectors = {
            "a" * 32: _vec(4, 1.0),
            "b" * 32: _vec(4, 2.5),
            "c" * 32: np.array([0.1, -0.2, 0.3, -0.4], dtype=np.float32),
        }
        for key, vec in vectors.items():
            cache.put(key, vec)
        cache.save(set(vectors.keys()))

        reloaded = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4
        )
        for key, vec in vectors.items():
            got = reloaded.get(key)
            assert got is not None
            assert np.array_equal(got, vec)

    def test_missing_file_starts_empty(self, tmp_path):
        cache_path = tmp_path / "does_not_exist.bin"
        cache = ChunkEmbeddingCache(cache_path, model_name="BAAI/bge-m3", dimension=4)
        assert cache.get_stats()["cache_size"] == 0
        assert cache.get("anything" * 4) is None

    def test_model_name_mismatch_starts_empty(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        key = ChunkEmbeddingCache.key_for("some content")
        cache = ChunkEmbeddingCache(cache_path, model_name="model-a", dimension=4)
        cache.put(key, _vec(4, 1.0))
        cache.save({key})

        reloaded = ChunkEmbeddingCache(cache_path, model_name="model-b", dimension=4)
        assert reloaded.get_stats()["cache_size"] == 0

    def test_dimension_mismatch_starts_empty(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        key = ChunkEmbeddingCache.key_for("some content")
        cache = ChunkEmbeddingCache(cache_path, model_name="BAAI/bge-m3", dimension=4)
        cache.put(key, _vec(4, 1.0))
        cache.save({key})

        reloaded = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=8
        )
        assert reloaded.get_stats()["cache_size"] == 0

    def test_corrupt_file_starts_empty_no_exception(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache_path.write_bytes(b"not a valid cache file at all")

        # Must not raise despite the garbage payload.
        cache = ChunkEmbeddingCache(cache_path, model_name="BAAI/bge-m3", dimension=4)
        assert cache.get_stats()["cache_size"] == 0

    def test_truncated_file_starts_empty_no_exception(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        key = ChunkEmbeddingCache.key_for("some content")
        good = ChunkEmbeddingCache(cache_path, model_name="BAAI/bge-m3", dimension=4)
        good.put(key, _vec(4, 1.0))
        good.save({key})

        # Truncate the saved file mid-record.
        data = cache_path.read_bytes()
        cache_path.write_bytes(data[: len(data) - 3])

        reloaded = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4
        )
        assert reloaded.get_stats()["cache_size"] == 0

    def test_save_failure_does_not_raise(self, tmp_path, monkeypatch):
        # Point the cache at a path whose parent cannot be created (a file,
        # not a directory), forcing save() to hit its except branch.
        blocker = tmp_path / "blocker"
        blocker.write_text("i am a file, not a directory")
        cache_path = blocker / "chunk_embeddings.bin"

        cache = ChunkEmbeddingCache(cache_path, model_name="BAAI/bge-m3", dimension=4)
        cache.put("k" * 32, _vec(4, 1.0))
        cache.save({"k" * 32})  # must not raise


class TestEviction:
    def test_live_keys_always_survive(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, max_entries=2
        )
        cache.put("a" * 32, _vec(4, 1.0))
        cache.put("b" * 32, _vec(4, 2.0))
        cache.put("c" * 32, _vec(4, 3.0))

        # live_keys includes all 3, exceeding the cap of 2 -> cap is exceeded
        # rather than dropping a live key.
        live_keys = {"a" * 32, "b" * 32, "c" * 32}
        cache.save(live_keys)

        reloaded = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, max_entries=2
        )
        assert reloaded.get("a" * 32) is not None
        assert reloaded.get("b" * 32) is not None
        assert reloaded.get("c" * 32) is not None

    def test_non_live_lru_evicted_down_to_cap(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, max_entries=2
        )
        # Insert 3 keys, oldest first; only "c" is live this run.
        cache.put("a" * 32, _vec(4, 1.0))
        cache.put("b" * 32, _vec(4, 2.0))
        cache.put("c" * 32, _vec(4, 3.0))
        cache.save({"c" * 32})

        assert cache.get_stats()["cache_size"] <= 2
        reloaded = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, max_entries=2
        )
        # "c" (live) must survive; "a" (oldest, non-live) should be the first evicted.
        assert reloaded.get("c" * 32) is not None
        assert reloaded.get("a" * 32) is None


class TestGetStats:
    def test_hit_miss_counts(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(cache_path, model_name="BAAI/bge-m3", dimension=4)
        cache.put("a" * 32, _vec(4, 1.0))

        assert cache.get("a" * 32) is not None
        assert cache.get("z" * 32) is None

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["cache_size"] == 1
