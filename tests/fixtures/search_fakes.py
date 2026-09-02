"""In-memory fakes for HybridSearcher's two index collaborators.

``HybridSearcher.__init__`` constructs ``self.bm25_index`` and
``self.dense_index`` by calling the module-level names
``search.hybrid_searcher.BM25Index`` / ``search.hybrid_searcher.CodeIndexManager``
directly -- there is no constructor-injection seam, and per
docs/plans (Phase 14.3) none should be added. ``FakeBM25Index`` and
``FakeDenseIndex`` are patched in at that same construction boundary in
tests/unit/search/test_hybrid_search.py, so ``HybridSearcher`` naturally
builds real, in-memory, faithful objects instead of ``Mock()`` instances with
hard-coded ``.search.return_value``s.

Real add/search/save/load semantics -- ``rank_bm25.BM25Okapi`` scoring for
BM25, cosine similarity for dense (mathematically identical to FAISS
``IndexFlatIP`` on L2-normalized vectors) -- mean RRF fusion and tail-rerank
logic in the module under test run against genuine rank lists instead of
scripted stubs. Disk I/O (``save``/``load``) round-trips through plain JSON
to the test's own ``tempfile.mkdtemp()`` directory, since real filesystem
access -- not the scoring/ranking logic -- is the genuine boundary here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    """Word-level tokenization for code-shaped text.

    Deliberately simpler than BM25Index's real TextPreprocessor (no
    stemming/stopwords/camelCase-splitting) -- just enough to let queries
    like "calculate_sum" match punctuation-adjacent identifiers in document
    text like "def calculate_sum(a, b):" without depending on the real
    preprocessing pipeline's internals.
    """
    return _TOKEN_RE.findall(text.lower())


def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    return all(metadata.get(key) == value for key, value in filters.items())


class FakeBM25Index:
    """In-memory stand-in for search.bm25_index.BM25Index."""

    def __init__(
        self,
        storage_dir: str,
        use_stopwords: bool = True,
        use_stemming: bool = True,
        tokenizer: str = "legacy",
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_dir / "bm25.index"
        self.metadata_path = self.storage_dir / "bm25_metadata.json"
        self.docs_path = self.storage_dir / "bm25_docs.json"
        self.use_stopwords = use_stopwords
        self.use_stemming = use_stemming
        self.tokenizer = tokenizer
        self.k1 = k1
        self.b = b

        self._bm25: BM25Okapi | None = None
        self._documents: list[str] = []
        self._doc_ids: list[str] = []
        self._tokenized_docs: list[list[str]] = []
        self._metadata: dict[str, dict[str, Any]] = {}

    @property
    def is_empty(self) -> bool:
        return len(self._documents) == 0

    @property
    def size(self) -> int:
        return len(self._documents)

    def index_documents(
        self,
        documents: list[str],
        doc_ids: list[str],
        metadata: dict[str, dict] | None = None,
    ) -> None:
        if len(documents) != len(doc_ids):
            raise ValueError("Number of documents must match number of IDs")
        if not documents:
            return

        self._documents.extend(documents)
        self._doc_ids.extend(doc_ids)
        if metadata:
            for doc_id, meta in metadata.items():
                self._metadata[doc_id] = dict(meta)

        self._tokenized_docs.extend(_tokenize(doc) for doc in documents)
        self._bm25 = BM25Okapi(self._tokenized_docs, k1=self.k1, b=self.b)

    def clear(self) -> None:
        self._bm25 = None
        self._documents = []
        self._doc_ids = []
        self._tokenized_docs = []
        self._metadata = {}

    def search(
        self, query: str, k: int = 5, min_score: float = 0.0
    ) -> list[tuple[str, float, dict]]:
        if self._bm25 is None or self.is_empty:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        top_indices = scores.argsort()[-k:][::-1]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < min_score:
                continue
            doc_id = self._doc_ids[idx]
            metadata = dict(self._metadata.get(doc_id, {}))
            if "content" not in metadata and idx < len(self._documents):
                metadata["content"] = self._documents[idx]
            results.append((doc_id, score, metadata))
        return results

    def remove_files(
        self, file_paths: set[str], project_name: str | None = None
    ) -> int:
        if not self._doc_ids or not file_paths:
            return 0

        keep = [
            i
            for i, doc_id in enumerate(self._doc_ids)
            if doc_id.split(":", 1)[0] not in file_paths
        ]
        removed = len(self._doc_ids) - len(keep)
        if removed == 0:
            return 0

        removed_ids = {
            self._doc_ids[i] for i in range(len(self._doc_ids)) if i not in keep
        }
        self._documents = [self._documents[i] for i in keep]
        self._doc_ids = [self._doc_ids[i] for i in keep]
        self._tokenized_docs = [self._tokenized_docs[i] for i in keep]
        for doc_id in removed_ids:
            self._metadata.pop(doc_id, None)

        self._bm25 = (
            BM25Okapi(self._tokenized_docs, k1=self.k1, b=self.b)
            if self._tokenized_docs
            else None
        )
        return removed

    def save(self) -> None:
        self.docs_path.write_text(
            json.dumps(
                {
                    "documents": self._documents,
                    "doc_ids": self._doc_ids,
                    "tokenized_docs": self._tokenized_docs,
                }
            )
        )
        self.metadata_path.write_text(
            json.dumps({"size": self.size, "doc_metadata": self._metadata})
        )

    def load(self) -> bool:
        if not self.docs_path.exists() or not self.metadata_path.exists():
            return False

        docs_data = json.loads(self.docs_path.read_text())
        meta_data = json.loads(self.metadata_path.read_text())
        self._documents = docs_data["documents"]
        self._doc_ids = docs_data["doc_ids"]
        self._tokenized_docs = docs_data["tokenized_docs"]
        self._metadata = meta_data.get("doc_metadata", {})
        self._bm25 = (
            BM25Okapi(self._tokenized_docs, k1=self.k1, b=self.b)
            if self._tokenized_docs
            else None
        )
        return True

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_documents": self.size,
            "has_index": self._bm25 is not None,
            "use_stopwords": self.use_stopwords,
            "tokenizer": self.tokenizer,
        }


class _FakeFaissIndex:
    """Minimal stand-in exposing only what production code reads off the
    real compiled FAISS index: ``.d`` and ``.ntotal``."""

    def __init__(self, d: int, ntotal: int) -> None:
        self.d = d
        self.ntotal = ntotal


class _FakeMetadataStore:
    """Dict-backed stand-in for search.metadata.MetadataStore.

    Matches the real store's ``{"index_id": int, "metadata": dict}`` entry
    shape (search/metadata.py:107) so callers like
    ``IndexSynchronizer.resync_bm25_from_dense`` that read
    ``entry["metadata"]`` work unchanged against the fake.
    """

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}

    def get(self, chunk_id: str) -> dict[str, Any] | None:
        return self._entries.get(chunk_id)

    def set(self, chunk_id: str, index_id: int, metadata: dict[str, Any]) -> None:
        self._entries[chunk_id] = {"index_id": index_id, "metadata": dict(metadata)}

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass


class FakeDenseIndex:
    """In-memory stand-in for search.indexer.CodeIndexManager.

    Cosine similarity over an in-memory vector array is mathematically
    identical to FAISS ``IndexFlatIP`` on L2-normalized vectors, so ranking
    genuinely reflects the embeddings a test hands it.
    """

    def __init__(
        self,
        storage_dir: str,
        embedder: Any = None,
        project_id: str | None = None,
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.stats_path = self.storage_dir / "dense_vectors.json"
        self.metadata_path = self.storage_dir / "metadata.db"
        self.embedder = embedder
        self.project_id = project_id

        self.chunk_ids: list[str] = []
        self._vectors: np.ndarray | None = None
        self.metadata_store = _FakeMetadataStore()

    @property
    def index(self) -> _FakeFaissIndex | None:
        if self._vectors is None or len(self.chunk_ids) == 0:
            return None
        return _FakeFaissIndex(d=self._vectors.shape[1], ntotal=len(self.chunk_ids))

    @property
    def ntotal(self) -> int:
        return len(self.chunk_ids)

    @property
    def is_on_gpu(self) -> bool:
        return False

    def add_embeddings(self, embedding_results: list[Any]) -> None:
        if not embedding_results:
            return

        new_vectors = np.array(
            [np.asarray(r.embedding, dtype=np.float32) for r in embedding_results]
        )
        norms = np.linalg.norm(new_vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        new_vectors = new_vectors / norms

        start_id = len(self.chunk_ids)
        self._vectors = (
            new_vectors
            if self._vectors is None
            else np.vstack([self._vectors, new_vectors])
        )

        for i, result in enumerate(embedding_results):
            chunk_id = result.chunk_id
            self.chunk_ids.append(chunk_id)
            metadata = {k: v for k, v in result.metadata.items() if k != "content"}
            self.metadata_store.set(chunk_id, start_id + i, metadata)

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        if self._vectors is None or len(self.chunk_ids) == 0:
            return []

        query = np.asarray(query_embedding, dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        similarities = self._vectors @ query
        order = np.argsort(similarities)[::-1]

        results = []
        for idx in order:
            chunk_id = self.chunk_ids[idx]
            entry = self.metadata_store.get(chunk_id)
            if entry is None:
                continue
            metadata = entry["metadata"]
            if not _matches_filters(metadata, filters):
                continue
            results.append((chunk_id, float(similarities[idx]), metadata))
            if len(results) >= k:
                break
        return results

    def get_chunk_by_id(
        self, chunk_id: str, warn_on_miss: bool = True
    ) -> dict[str, Any] | None:
        entry = self.metadata_store.get(chunk_id)
        return entry["metadata"] if entry else None

    def get_similar_chunks(
        self, chunk_id: str, k: int = 5, exclude_same_file: bool = False
    ) -> list[tuple[str, float, dict[str, Any]]]:
        entry = self.metadata_store.get(chunk_id)
        if not entry or self._vectors is None:
            return []
        index_id = entry["index_id"]
        if index_id >= len(self.chunk_ids):
            return []
        anchor_embedding = self._vectors[index_id]

        if exclude_same_file:
            anchor_path = entry["metadata"].get("relative_path")
            candidates = self.search(anchor_embedding, k * 3 + 1)
            filtered = [
                (cid, score, meta)
                for cid, score, meta in candidates
                if cid != chunk_id and meta.get("relative_path") != anchor_path
            ]
        else:
            candidates = self.search(anchor_embedding, k + 1)
            filtered = [
                (cid, score, meta) for cid, score, meta in candidates if cid != chunk_id
            ]
        return filtered[:k]

    def get_similar_chunks_batched(
        self, chunk_ids: list[str], k: int = 5
    ) -> dict[str, list[tuple[str, float, dict[str, Any]]]]:
        return {cid: self.get_similar_chunks(cid, k) for cid in chunk_ids}

    def remove_files(
        self, file_paths: set[str], project_name: str | None = None
    ) -> int:
        if not self.chunk_ids or not file_paths:
            return 0

        keep_indices = [
            i
            for i, cid in enumerate(self.chunk_ids)
            if cid.split(":", 1)[0] not in file_paths
        ]
        removed = len(self.chunk_ids) - len(keep_indices)
        if removed == 0:
            return 0

        removed_ids = {
            self.chunk_ids[i]
            for i in range(len(self.chunk_ids))
            if i not in keep_indices
        }
        self.chunk_ids = [self.chunk_ids[i] for i in keep_indices]
        self._vectors = (
            self._vectors[keep_indices]
            if self._vectors is not None and keep_indices
            else None
        )
        for chunk_id in removed_ids:
            self.metadata_store._entries.pop(chunk_id, None)
        # Re-sync surviving entries' index_id to the compacted vector array.
        for new_idx, chunk_id in enumerate(self.chunk_ids):
            entry = self.metadata_store.get(chunk_id)
            if entry is not None:
                entry["index_id"] = new_idx
        return removed

    def save_index(self) -> None:
        self.save()

    def save(self) -> None:
        payload = {
            "chunk_ids": self.chunk_ids,
            "vectors": self._vectors.tolist() if self._vectors is not None else None,
        }
        self.stats_path.write_text(json.dumps(payload))

    def load(self) -> bool:
        if not self.stats_path.exists():
            return False
        payload = json.loads(self.stats_path.read_text())
        self.chunk_ids = payload["chunk_ids"]
        self._vectors = (
            np.array(payload["vectors"], dtype=np.float32)
            if payload["vectors"] is not None
            else None
        )
        return True

    def preflight_clear(self) -> Path:
        return self.metadata_path

    def clear_index(self) -> None:
        self.chunk_ids = []
        self._vectors = None
        self.metadata_store = _FakeMetadataStore()

    def close(self) -> None:
        pass
