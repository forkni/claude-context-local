"""Persistent content-hash cache for chunk embeddings.

Force reindex spends the majority of its wall-clock re-embedding chunks whose
*assembled* embedding content — the structural header, import context, class
signature, and chunk body that :meth:`CodeEmbedder.create_embedding_content`
composes — is byte-identical to the last indexed run. This cache stores
``{content_hash: vector}`` pairs on disk, keyed by that assembled string, so a
100% cache hit can skip the GPU embedding pass (and, in :meth:`CodeEmbedder.
embed_chunks`, the model load itself) entirely.

The cache file lives inside the project's own storage directory, which is
already namespaced by model name and dimension
(``mcp_server.storage_manager.get_project_storage_dir``), so switching models
or dimensions naturally lands on a fresh, empty cache rather than serving
incompatible vectors. The ``model_name``/``dimension`` recorded in this
file's header are a second, independent check against that same hazard.

Deliberately NOT built on top of two existing near-miss candidates:

- ``embeddings/query_cache.py``'s ``QueryEmbeddingCache`` is in-memory only
  (no disk persistence) — the right *shape* to mirror (hash key, LRU,
  hit/miss stats), but it disappears with the process.
- ``search/mmap_vectors.py``'s ``MmapVectorStorage`` is keyed by *FAISS index
  position*, not content hash — its stored per-record hash is written but
  never read back by anything. Its hash is 64-bit FNV-1a, too weak for a
  content-addressed cache (a collision here would silently serve the wrong
  embedding). And it sits on the live dense-search read path
  (``FaissVectorIndex.load``/``save``); widening its record format to fix
  the above would move this cache's blast radius into search retrieval.

Correctness note: the cache key MUST be derived from the final string handed
to ``model.encode()`` (``passage_prefix + create_embedding_content(chunk)``),
never from raw ``chunk.content``. ``create_embedding_content`` folds in the
file's import block and the parent class signature, so a chunk's correct
embedding changes when a *neighbouring* part of its file changes — hashing
raw chunk content would serve stale vectors for such chunks.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import struct
import traceback
from collections import OrderedDict
from pathlib import Path
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)

_MAGIC = b"CHNK"
_VERSION = 2
_KEY_BYTES = 16  # 128-bit truncated SHA-256 -> 32 hex chars
# version, dimension, entry_count, model_name_len, provenance_len
_HEADER_FIXED_STRUCT = "<IIIII"
_AUTO_MIN_ENTRIES = 2_000
_AUTO_MAX_BYTES = 32 * 1024 * 1024


class ChunkEmbeddingCache:
    """Persistent, content-hash-keyed cache of chunk embedding vectors.

    One instance per project index (see
    ``IndexWriteStage._resolve_chunk_cache``). Not thread-safe by design:
    ``embed_chunks`` is the sole writer, called from a single indexing
    thread; multi-project concurrency is handled by each project getting
    its own instance/file, not by locking within one.
    """

    def __init__(
        self,
        cache_path: Path,
        model_name: str,
        dimension: int,
        provenance: str,
        max_entries: int = 0,
    ) -> None:
        """Initialize and immediately (best-effort) load the on-disk cache.

        Args:
            cache_path: Path to the cache file (created on first save).
            model_name: Embedding model name — must match to reuse the file.
            dimension: Embedding dimension — must match to reuse the file.
            provenance: Stable description of the numerics (device/dtype/
                backend) that will produce new vectors — see
                ``ModelLoader.describe_numerics()``. Required with no
                default: a silent default is exactly how an unstable or
                wrong provenance string would ship undetected. Must match
                to reuse the file — this is what prevents a precision or
                backend change from silently re-serving cross-numerics
                vectors.
            max_entries: Eviction cap for :meth:`save`. ``0`` means auto —
                see :meth:`_evict`.
        """
        self._path = Path(cache_path)
        self._model_name = model_name
        self._dimension = dimension
        self._provenance = provenance
        self._max_entries = max_entries if max_entries > 0 else 0
        # Insertion order = LRU order (oldest first); get()/put() move the
        # touched key to the end. Mirrors QueryEmbeddingCache's OrderedDict use.
        self._entries: OrderedDict[str, np.ndarray] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.load()

    # -- key derivation -------------------------------------------------

    @staticmethod
    def key_for(content: str) -> str:
        """Derive the cache key from the *assembled* embedding content.

        Must be called with the exact string that would be passed to
        ``model.encode()`` — see the module docstring for why hashing raw
        chunk content instead would be incorrect.
        """
        digest = hashlib.sha256(content.encode("utf-8")).digest()
        return digest[:_KEY_BYTES].hex()

    # -- read / write -----------------------------------------------------

    def get(self, key: str) -> np.ndarray | None:
        """Return a copy of the cached vector for *key*, or None on a miss."""
        vector = self._entries.get(key)
        if vector is None:
            self.misses += 1
            return None
        self.hits += 1
        self._entries.move_to_end(key)
        return vector.copy()

    def put(self, key: str, vector: np.ndarray) -> None:
        """Insert or update the vector for *key* (marks it most-recently-used)."""
        if vector.dtype != np.float32:
            vector = vector.astype(np.float32)
        self._entries[key] = vector
        self._entries.move_to_end(key)

    # -- persistence -----------------------------------------------------

    def load(self) -> None:
        """Load the on-disk cache. Never raises — any problem starts empty.

        A missing file, wrong magic, unsupported version, dimension or
        model-name mismatch, or truncated/corrupt payload all fall through
        to the same outcome: an empty cache and an INFO-level log line. A
        cache problem must never fail an index.
        """
        self._entries = OrderedDict()
        if not self._path.exists():
            return
        try:
            data = self._path.read_bytes()
            if len(data) < 4:
                raise ValueError("file too short for magic bytes")
            if data[:4] != _MAGIC:
                raise ValueError(f"bad magic bytes {data[:4]!r}")
            # Version is field 0 at a fixed offset (4) in every format
            # version — check it before the wide unpack so a v1 file (which
            # used a narrower header) fails with a readable "unsupported
            # format version 1" instead of a struct-size error. This INFO
            # line is the only signal a user gets when a cache is discarded.
            (version,) = struct.unpack_from("<I", data, 4)
            if version != _VERSION:
                raise ValueError(f"unsupported format version {version}")
            offset = 4
            header_size = struct.calcsize(_HEADER_FIXED_STRUCT)
            version, dimension, entry_count, name_len, prov_len = struct.unpack_from(
                _HEADER_FIXED_STRUCT, data, offset
            )
            offset += header_size
            if dimension != self._dimension:
                raise ValueError(
                    f"dimension mismatch: file has {dimension}, expected {self._dimension}"
                )
            model_name = data[offset : offset + name_len].decode("utf-8")
            offset += name_len
            if model_name != self._model_name:
                raise ValueError(
                    f"model mismatch: file has {model_name!r}, expected {self._model_name!r}"
                )
            provenance = data[offset : offset + prov_len].decode("utf-8")
            offset += prov_len
            if provenance != self._provenance:
                raise ValueError(
                    f"provenance mismatch: file has {provenance!r}, "
                    f"expected {self._provenance!r}"
                )
            record_size = _KEY_BYTES + dimension * 4
            expected_size = offset + entry_count * record_size
            if expected_size != len(data):
                raise ValueError(
                    f"size mismatch: header claims {entry_count} entries "
                    f"({expected_size} bytes total) but file is {len(data)} bytes"
                )
            for i in range(entry_count):
                start = offset + i * record_size
                key = data[start : start + _KEY_BYTES].hex()
                vec_bytes = data[start + _KEY_BYTES : start + record_size]
                self._entries[key] = np.frombuffer(vec_bytes, dtype=np.float32).copy()
        except Exception as exc:  # noqa: BLE001 - fail-soft: any corruption starts an empty cache
            logger.info(
                "Chunk embedding cache at %s unreadable (%s) — starting empty",
                self._path,
                exc,
            )
            self._entries = OrderedDict()

    def save(self, live_keys: set[str], *, full_pass: bool = True) -> None:
        """Persist the cache to disk, atomically.

        Evicts down to the configured cap first (see :meth:`_evict`), always
        keeping every key in *live_keys* — the keys actually used by the run
        that just completed. Never raises: a save failure is logged and
        otherwise ignored, meaning only that the next run starts colder than
        it could have.

        Args:
            full_pass: Whether *live_keys* is the authoritative set for the
                whole project (a full index) or only a subset (an incremental
                update, a module-summary refresh). ``True`` allows
                eviction to target the entries-based cap derived from
                ``len(live_keys)`` — correct only when ``live_keys`` really is
                everything the project needs. ``False`` caps by the byte
                ceiling alone, so a small partial-run ``live_keys`` cannot
                collapse a cache built by prior full passes. See :meth:`_evict`.
        """
        tmp = Path(str(self._path) + ".tmp")
        try:
            self._evict(live_keys, full_pass=full_pass)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            name_bytes = self._model_name.encode("utf-8")
            prov_bytes = self._provenance.encode("utf-8")
            with open(tmp, "wb") as f:
                f.write(_MAGIC)
                f.write(
                    struct.pack(
                        _HEADER_FIXED_STRUCT,
                        _VERSION,
                        self._dimension,
                        len(self._entries),
                        len(name_bytes),
                        len(prov_bytes),
                    )
                )
                f.write(name_bytes)
                f.write(prov_bytes)
                for key, vector in self._entries.items():
                    f.write(bytes.fromhex(key))
                    f.write(vector.astype(np.float32).tobytes())
            os.replace(tmp, self._path)
        except Exception as exc:  # noqa: BLE001 - fail-soft: cache write failures must never fail an index
            logger.warning(
                "Failed to save chunk embedding cache to %s: %s", self._path, exc
            )
            # Cleanup of the partial .tmp file is best-effort — e.g. its parent may
            # itself not be a directory (the same failure mode that put us in this
            # except branch). Never let cleanup promote a fail-soft save() into a raise.
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)

    def _evict(self, live_keys: set[str], *, full_pass: bool = True) -> None:
        """Drop least-recently-used, non-live entries down to the cap.

        ``live_keys`` always survives eviction, even if that means staying
        over the nominal cap — correctness for the run just completed takes
        priority over the size target.

        The entries-based cap (``2 * len(live_keys)``, floored at
        ``_AUTO_MIN_ENTRIES``) is only sound when ``live_keys`` is the
        authoritative set for the whole project — i.e. ``full_pass=True``. A
        partial run (incremental update, module-summary refresh) touches
        only the handful of chunks that changed; naively applying the same
        formula would shrink a cache built by prior full passes down to
        roughly twice *that* handful. When ``full_pass=False`` the cap is
        instead the byte ceiling alone, so a small partial-run ``live_keys``
        only trims genuinely excess entries (oldest-first, via the
        ``OrderedDict``'s LRU order), never the bulk of an already-populated
        cache.
        """
        if self._max_entries > 0:
            cap = self._max_entries
        else:
            record_bytes = _KEY_BYTES + self._dimension * 4
            byte_cap = max(len(live_keys), _AUTO_MAX_BYTES // record_bytes)
            if full_pass:
                cap = min(max(2 * len(live_keys), _AUTO_MIN_ENTRIES), byte_cap)
            else:
                cap = byte_cap
        if len(self._entries) <= cap:
            return
        # OrderedDict iterates oldest-first; drop LRU non-live entries until
        # at cap (or until none remain to drop).
        for key in list(self._entries.keys()):
            if len(self._entries) <= cap:
                break
            if key in live_keys:
                continue
            del self._entries[key]

    def get_stats(self) -> dict[str, Any]:
        """Return hit/miss/size statistics, mirroring ``QueryEmbeddingCache.get_stats``."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "cache_size": len(self._entries),
            "max_entries": self._max_entries if self._max_entries > 0 else "auto",
        }


# -- shared resolution helpers --------------------------------------------
#
# Module-level so every embed_chunks() call site (full index, incremental
# update, module-summary refresh) resolves a cache the same fail-soft
# way instead of each reimplementing it. Originally lived as private methods
# on IndexWriteStage, which only ever wired the full-index path.


def resolve_embedding_provenance(embedder: Any) -> str:
    """Best-effort provenance string for *embedder*, never raising.

    A constant sentinel (``"unavailable"``) on failure — not a
    config-derived approximation, which would differ from the real
    provenance string and manufacture a permanent 0%-hit-rate mismatch. The
    ``isinstance`` guard matters: tests routinely construct a ``Mock``
    embedder, whose auto-attribute would otherwise return a ``Mock`` that
    reaches ``provenance.encode("utf-8")`` in :meth:`ChunkEmbeddingCache.save`
    and fail-soft into a cache that silently never persists.
    """
    getter = getattr(embedder, "get_embedding_provenance", None)
    if callable(getter):
        try:
            value = getter()
            if isinstance(value, str) and value:
                return value
        except Exception:  # noqa: BLE001 - fail-soft: provenance is best-effort
            logger.debug("[CHUNK_CACHE] provenance unavailable", exc_info=True)
    # A missing get_embedding_provenance(), an intermittent failure, or a
    # non-str/empty return all land here and silently rewrite the cache with
    # the sentinel on every run — a permanent 0% hit rate that otherwise
    # looks identical to a healthy cold cache. WARNING (not DEBUG/INFO)
    # because this degrades every subsequent run, not just this one.
    logger.warning(
        "[CHUNK_CACHE] Embedding provenance unavailable — persistent chunk "
        "cache will use the 'unavailable' sentinel and may never hit"
    )
    return "unavailable"


def resolve_chunk_cache(storage_dir: Any, embedder: Any) -> ChunkEmbeddingCache | None:
    """Resolve a run's persistent chunk-embedding cache, if enabled.

    Resolve lazily, per-run — never hold the result across runs — for two
    reasons. First, the embedder/indexer a caller builds this from may be
    rebuilt between runs (e.g. after resource release and verification), so
    a cache captured once could outlive that rebind stale. Second, tests
    routinely construct a ``Mock`` indexer, so eagerly building a ``Path``
    from ``storage_dir`` at construction time would raise on a ``Mock``.

    Fail-soft: disabled by config, a missing/non-path ``storage_dir``, or
    any other error while resolving all return ``None`` — ``embed_chunks``
    then behaves exactly as it does without a cache. A cache problem must
    never fail an index.
    """
    try:
        from search.config import get_search_config

        embedding_cfg = get_search_config().embedding
        if not embedding_cfg.enable_chunk_cache:
            return None

        cache_path = Path(storage_dir) / "chunk_embeddings.bin"
        return ChunkEmbeddingCache(
            cache_path=cache_path,
            model_name=embedding_cfg.model_name,
            dimension=embedding_cfg.dimension,
            provenance=resolve_embedding_provenance(embedder),
            max_entries=embedding_cfg.chunk_cache_max_entries,
        )
    except Exception:  # noqa: BLE001 - fail-soft: a cache problem must never fail an index
        logger.warning(
            "[CHUNK_CACHE] Unable to resolve persistent embedding cache "
            "(non-fatal):\n%s",
            traceback.format_exc(),
        )
        return None
