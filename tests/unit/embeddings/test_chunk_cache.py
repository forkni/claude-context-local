"""Unit tests for ChunkEmbeddingCache (persistent content-hash embedding cache)."""

import sys
from pathlib import Path

import numpy as np


# Add project root to path to allow imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from embeddings import chunk_cache as chunk_cache_module  # noqa: E402
from embeddings.chunk_cache import ChunkEmbeddingCache  # noqa: E402


_PROV = "v1|device=cpu|dtype=fp32|backend=pytorch"


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
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )

        vectors = {
            "a" * 32: _vec(4, 1.0),
            "b" * 32: _vec(4, 2.5),
            "c" * 32: np.array([0.1, -0.2, 0.3, -0.4], dtype=np.float32),
        }
        for key, vec in vectors.items():
            cache.put(key, vec)
        cache.save(set(vectors.keys()))

        reloaded = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        for key, vec in vectors.items():
            got = reloaded.get(key)
            assert got is not None
            assert np.array_equal(got, vec)

    def test_missing_file_starts_empty(self, tmp_path):
        cache_path = tmp_path / "does_not_exist.bin"
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        assert cache.get_stats()["cache_size"] == 0
        assert cache.get("anything" * 4) is None

    def test_model_name_mismatch_starts_empty(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        key = ChunkEmbeddingCache.key_for("some content")
        cache = ChunkEmbeddingCache(
            cache_path, model_name="model-a", dimension=4, provenance=_PROV
        )
        cache.put(key, _vec(4, 1.0))
        cache.save({key})

        reloaded = ChunkEmbeddingCache(
            cache_path, model_name="model-b", dimension=4, provenance=_PROV
        )
        assert reloaded.get_stats()["cache_size"] == 0

    def test_dimension_mismatch_starts_empty(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        key = ChunkEmbeddingCache.key_for("some content")
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        cache.put(key, _vec(4, 1.0))
        cache.save({key})

        reloaded = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=8, provenance=_PROV
        )
        assert reloaded.get_stats()["cache_size"] == 0

    def test_corrupt_file_starts_empty_no_exception(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache_path.write_bytes(b"not a valid cache file at all")

        # Must not raise despite the garbage payload.
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        assert cache.get_stats()["cache_size"] == 0

    def test_truncated_file_starts_empty_no_exception(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        key = ChunkEmbeddingCache.key_for("some content")
        good = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        good.put(key, _vec(4, 1.0))
        good.save({key})

        # Truncate the saved file mid-record.
        data = cache_path.read_bytes()
        cache_path.write_bytes(data[: len(data) - 3])

        reloaded = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        assert reloaded.get_stats()["cache_size"] == 0

    def test_save_failure_does_not_raise(self, tmp_path, monkeypatch):
        # Point the cache at a path whose parent cannot be created (a file,
        # not a directory), forcing save() to hit its except branch.
        blocker = tmp_path / "blocker"
        blocker.write_text("i am a file, not a directory")
        cache_path = blocker / "chunk_embeddings.bin"

        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        cache.put("k" * 32, _vec(4, 1.0))
        cache.save({"k" * 32})  # must not raise


class TestProvenance:
    """The header must record the numerics that produced its vectors."""

    def test_provenance_mismatch_starts_empty(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        key = ChunkEmbeddingCache.key_for("some content")
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        cache.put(key, _vec(4, 1.0))
        cache.save({key})

        reloaded = ChunkEmbeddingCache(
            cache_path,
            model_name="BAAI/bge-m3",
            dimension=4,
            provenance="v1|device=cuda|dtype=fp16|backend=pytorch",
        )
        assert reloaded.get_stats()["cache_size"] == 0

    def test_v1_header_rejected(self, tmp_path, caplog):
        import struct

        cache_path = tmp_path / "chunk_embeddings.bin"
        name_bytes = b"BAAI/bge-m3"
        # Hand-pack the pre-provenance v1 format: magic + <IIII> header
        # (version, dimension, entry_count, model_name_len) + model name,
        # zero records. v2 adds a fifth field (provenance_len) the v1 reader
        # never wrote.
        data = b"CHNK" + struct.pack("<IIII", 1, 4, 0, len(name_bytes)) + name_bytes
        cache_path.write_bytes(data)

        with caplog.at_level("INFO"):
            cache = ChunkEmbeddingCache(
                cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
            )
        assert cache.get_stats()["cache_size"] == 0
        assert "unsupported format version 1" in caplog.text


class TestEviction:
    def test_live_keys_always_survive(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(
            cache_path,
            model_name="BAAI/bge-m3",
            dimension=4,
            provenance=_PROV,
            max_entries=2,
        )
        cache.put("a" * 32, _vec(4, 1.0))
        cache.put("b" * 32, _vec(4, 2.0))
        cache.put("c" * 32, _vec(4, 3.0))

        # live_keys includes all 3, exceeding the cap of 2 -> cap is exceeded
        # rather than dropping a live key.
        live_keys = {"a" * 32, "b" * 32, "c" * 32}
        cache.save(live_keys)

        reloaded = ChunkEmbeddingCache(
            cache_path,
            model_name="BAAI/bge-m3",
            dimension=4,
            provenance=_PROV,
            max_entries=2,
        )
        assert reloaded.get("a" * 32) is not None
        assert reloaded.get("b" * 32) is not None
        assert reloaded.get("c" * 32) is not None

    def test_non_live_lru_evicted_down_to_cap(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(
            cache_path,
            model_name="BAAI/bge-m3",
            dimension=4,
            provenance=_PROV,
            max_entries=2,
        )
        # Insert 3 keys, oldest first; only "c" is live this run.
        cache.put("a" * 32, _vec(4, 1.0))
        cache.put("b" * 32, _vec(4, 2.0))
        cache.put("c" * 32, _vec(4, 3.0))
        cache.save({"c" * 32})

        assert cache.get_stats()["cache_size"] <= 2
        reloaded = ChunkEmbeddingCache(
            cache_path,
            model_name="BAAI/bge-m3",
            dimension=4,
            provenance=_PROV,
            max_entries=2,
        )
        # "c" (live) must survive; "a" (oldest, non-live) should be the first evicted.
        assert reloaded.get("c" * 32) is not None
        assert reloaded.get("a" * 32) is None


class TestAutoEvictionCap:
    """max_entries=0 (the default) sizes the cap from live_keys, not a fixed floor.

    Each test monkeypatches the module constants to small values so the
    three branches of the formula (2x-live-keys, the entry floor, and the
    byte clamp) can each be forced to bind without allocating huge arrays.
    """

    def test_floor_dominates_when_live_keys_small(self, tmp_path, monkeypatch):
        monkeypatch.setattr(chunk_cache_module, "_AUTO_MIN_ENTRIES", 5)
        monkeypatch.setattr(chunk_cache_module, "_AUTO_MAX_BYTES", 10 * 1024 * 1024)
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        for i in range(10):
            cache.put(f"{i:032d}", _vec(4, float(i)))
        # 1 live key -> 2x-live (2) is below the floor (5).
        cache.save({f"{0:032d}"})
        assert cache.get_stats()["cache_size"] == 5

    def test_scales_with_live_keys_above_floor(self, tmp_path, monkeypatch):
        monkeypatch.setattr(chunk_cache_module, "_AUTO_MIN_ENTRIES", 2)
        monkeypatch.setattr(chunk_cache_module, "_AUTO_MAX_BYTES", 10 * 1024 * 1024)
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        for i in range(20):
            cache.put(f"{i:032d}", _vec(4, float(i)))
        live = {f"{i:032d}" for i in range(8)}
        # 2x-live (16) dominates the floor (2).
        cache.save(live)
        assert cache.get_stats()["cache_size"] == 16

    def test_byte_clamp_binds_below_the_floor(self, tmp_path, monkeypatch):
        monkeypatch.setattr(chunk_cache_module, "_AUTO_MIN_ENTRIES", 2_000)
        # record_bytes = 16 + 4*4 = 32 -> clamp to 5 entries regardless of
        # the (much larger) floor.
        monkeypatch.setattr(chunk_cache_module, "_AUTO_MAX_BYTES", 5 * 32)
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        for i in range(20):
            cache.put(f"{i:032d}", _vec(4, float(i)))
        live = {f"{i:032d}" for i in range(10)}
        # The clamp is max(live_count, byte_budget) = max(10, 5) = 10, well
        # under max(2*live, floor) = 2000 -- live keys never get evicted.
        cache.save(live)
        assert cache.get_stats()["cache_size"] == 10


class TestGetStats:
    def test_hit_miss_counts(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        cache.put("a" * 32, _vec(4, 1.0))

        assert cache.get("a" * 32) is not None
        assert cache.get("z" * 32) is None

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["cache_size"] == 1

    def test_max_entries_zero_reports_auto(self, tmp_path):
        cache_path = tmp_path / "chunk_embeddings.bin"
        cache = ChunkEmbeddingCache(
            cache_path, model_name="BAAI/bge-m3", dimension=4, provenance=_PROV
        )
        assert cache.get_stats()["max_entries"] == "auto"
