"""Tests for hybrid search orchestrator.

Note: GPUMemoryMonitor tests have been moved to test_gpu_monitor.py (Phase 3.1 refactoring).

Phase 14.3 (docs/plans -- harden-test-suite): every test in this file used to
carry a `@patch("search.hybrid_searcher.CodeIndexManager")` +
`@patch("search.hybrid_searcher.BM25Index")` decorator pair returning bare
`Mock()` instances, so the RRF fusion this file is named for never ran
against real retrieval behaviour. The module-level `_patch_index_classes`
fixture below collapses all of those into one patch that swaps in
`FakeBM25Index`/`FakeDenseIndex` (tests/fixtures/search_fakes.py) --
in-memory fakes with real add/search/save/load semantics -- so
`HybridSearcher.__init__` naturally builds faithful collaborators instead of
scripted stubs.
"""

import contextlib
import tempfile
from unittest.mock import Mock, patch

import numpy as np
import pytest

from search.config import SearchConfig
from search.hybrid_searcher import HybridSearcher
from tests.fixtures.search_fakes import FakeBM25Index, FakeDenseIndex
from utils.otel_attributes import ATTR_CAPTURE_QUERY


@pytest.fixture(autouse=True)
def _patch_index_classes(monkeypatch):
    """Swap HybridSearcher's two construction-time collaborators for fakes.

    Patches at the same boundary the file used to patch per-test
    (`search.hybrid_searcher.CodeIndexManager` / `.BM25Index`) -- there is no
    constructor-injection seam and per Phase 14.3's plan none should be
    added. Autouse + module scope means every test in this file gets real,
    in-memory, faithful index collaborators with no per-test decorator.
    """
    monkeypatch.setattr("search.hybrid_searcher.CodeIndexManager", FakeDenseIndex)
    monkeypatch.setattr("search.hybrid_searcher.BM25Index", FakeBM25Index)


class TestHybridSearcher:
    """Test hybrid search orchestrator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create mock documents and metadata
        self.documents = [
            "def calculate_sum(a, b): return a + b",
            "class UserManager: def get_user(self, user_id): return users[user_id]",
            "function processData(data) { return data.filter(x => x.valid); }",
            "SELECT name, email FROM users WHERE active = true",
            "async def fetch_data(): return await api_client.get('/data')",
        ]
        self.doc_ids = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        self.embeddings = [np.random.rand(768).tolist() for _ in self.documents]
        self.metadata = {
            doc_id: {
                "language": (
                    "python" if i < 2 or i == 4 else "javascript" if i == 2 else "sql"
                ),
                "type": "function" if i in [0, 4] else "class" if i == 1 else "query",
                "lines": i + 1,
            }
            for i, doc_id in enumerate(self.doc_ids)
        }

    def _stub_search_deps(self):
        """Build a stub embedder + config that keep search() on the mocked
        BM25/dense path without ever constructing a real CodeEmbedder or
        loading the real jina-reranker-v3 cross-encoder.

        Passing `embedder=` at HybridSearcher construction bypasses the lazy
        `SearchExecutor.search_dense()` branch (search_executor.py:434) that
        otherwise builds a real CodeEmbedder against real
        ~/.claude_code_search/models on first use. Disabling
        `config.reranker.enabled` and threading that config through
        `get_search_config` (rather than letting it read the
        real repo-root search_config.json) stops
        RerankingEngine._ensure_reranker() from loading the real neural
        reranker onto the GPU -- config threading (ADR-0018/C2) makes this a
        single injection point for every rerank pass (hop-1, multi-hop
        merge, and the single_pass tail).
        """
        embedder = Mock()
        embedder.embed_query.return_value = np.random.rand(768)
        config = SearchConfig()
        config.reranker.enabled = False
        return embedder, config

    def test_initialization(self):
        """Test hybrid searcher initialization."""
        searcher = HybridSearcher(self.temp_dir)

        assert searcher.max_workers == 2
        assert not searcher._is_shutdown

    def test_context_manager(self):
        """Test context manager functionality."""
        with HybridSearcher(self.temp_dir) as searcher:
            assert not searcher._is_shutdown

        assert searcher._is_shutdown

    def test_close_metadata_connections_delegates_to_dense_index_close(self):
        """close_metadata_connections collapses to dense_index.close()
        (ADR-0025) -- it used to reach past the public property into
        dense_index._metadata_store.close() directly.
        """
        searcher = HybridSearcher(self.temp_dir)
        searcher.dense_index.close = Mock(wraps=searcher.dense_index.close)

        searcher.close_metadata_connections()

        searcher.dense_index.close.assert_called_once()

    def test_is_ready_property(self):
        """Test is_ready property."""
        searcher = HybridSearcher(self.temp_dir)

        assert not searcher.is_ready

        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        assert searcher.is_ready

    def test_index_documents(self):
        """Indexing populates both real indices with the given data, not
        just call counts on scripted mocks.
        """
        searcher = HybridSearcher(self.temp_dir)

        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        assert searcher.bm25_index.size == len(self.documents)
        assert searcher.dense_index.ntotal == len(self.documents)
        assert set(searcher.dense_index.chunk_ids) == set(self.doc_ids)

        bm25_hits = searcher.bm25_index.search("calculate_sum", k=5)
        assert bm25_hits[0][0] == "doc1"

        dense_hits = searcher.dense_index.search(np.array(self.embeddings[1]), k=1)
        assert dense_hits[0][0] == "doc2"

    def test_weight_change_takes_effect_without_rebuild(self):
        """Direct proof that search_mode.bm25_weight/dense_weight are NOT
        construction_baked (Phase 2a, ADR-0018 follow-on): HybridSearcher
        takes no weight parameters at construction (hybrid_searcher.py:61-75)
        - both are resolved live from effective_config on every search() call
        (:731-739). Mutating the live config between two search() calls on
        the SAME instance, with no rebuild in between, must change the
        RetrievalRequest weights the second call is built with.
        """
        searcher = HybridSearcher(self.temp_dir)
        # Index real data so search() reaches weight resolution instead of
        # short-circuiting on is_ready.
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        live_config = SearchConfig()
        live_config.search_mode.bm25_weight = 0.35
        live_config.search_mode.dense_weight = 0.65
        # Force the single-hop branch so the patched _single_hop_search below
        # is what actually resolves the request - multi-hop is enabled by
        # default and would otherwise route through multi_hop_searcher instead.
        live_config.multi_hop.enabled = False

        captured_requests = []

        def fake_single_hop(request, query_embedding=None):
            captured_requests.append(request)
            return []

        with (
            patch(
                "search.config.get_search_config",
                return_value=live_config,
            ),
            patch.object(searcher, "_single_hop_search", side_effect=fake_single_hop),
        ):
            searcher.search("test query", use_parallel=False)

            # Mutate the live config in place - no HybridSearcher rebuild.
            live_config.search_mode.bm25_weight = 0.9
            live_config.search_mode.dense_weight = 0.1

            searcher.search("test query", use_parallel=False)

        assert len(captured_requests) == 2
        assert captured_requests[0].bm25_weight == 0.35
        assert captured_requests[0].dense_weight == 0.65
        assert captured_requests[1].bm25_weight == 0.9
        assert captured_requests[1].dense_weight == 0.1

    def test_search_not_ready(self):
        """Test search when indices are not ready."""
        searcher = HybridSearcher(self.temp_dir)

        results = searcher.search("test query")
        assert results == []

    def test_sequential_search(self):
        """Sequential (non-parallel) search fuses real BM25 + dense rankings."""
        embedder, config = self._stub_search_deps()
        config.multi_hop.enabled = False
        searcher = HybridSearcher(self.temp_dir, embedder=embedder, config=config)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )
        # Query embedding equal to doc2's own vector -- both BM25 (text
        # match) and dense (cosine 1.0) legs agree doc2 is the top hit, so
        # RRF fusion has an unambiguous expected winner.
        embedder.embed_query.return_value = np.array(self.embeddings[1])

        with patch("search.config.get_search_config", return_value=config):
            results = searcher.search(
                "class UserManager get_user", k=5, use_parallel=False
            )

        assert results
        assert results[0].chunk_id == "doc2"

    def test_parallel_search(self):
        """Parallel search execution fuses the same real rankings as sequential."""
        embedder, config = self._stub_search_deps()
        config.multi_hop.enabled = False
        searcher = HybridSearcher(self.temp_dir, embedder=embedder, config=config)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )
        embedder.embed_query.return_value = np.array(self.embeddings[1])

        with patch("search.config.get_search_config", return_value=config):
            results = searcher.search(
                "class UserManager get_user", k=5, use_parallel=True
            )

        assert results
        assert results[0].chunk_id == "doc2"

    def test_search_with_filters(self):
        """Filters passed to search() really constrain the dense leg's
        candidates, not just the call arguments a mock recorded.
        """
        embedder, config = self._stub_search_deps()
        config.multi_hop.enabled = False
        searcher = HybridSearcher(self.temp_dir, embedder=embedder, config=config)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )
        embedder.embed_query.return_value = np.array(self.embeddings[0])

        filters = {"language": "python"}
        with patch("search.config.get_search_config", return_value=config):
            results = searcher.search(
                "test query", k=5, use_parallel=False, filters=filters
            )

        assert results
        for result in results:
            assert self.metadata[result.chunk_id]["language"] == "python"

    def test_search_error_handling(self):
        """Test search error handling."""
        embedder, config = self._stub_search_deps()
        searcher = HybridSearcher(self.temp_dir, embedder=embedder, config=config)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        # Fault-inject on the real, already-indexed collaborators -- a
        # legitimate localized boundary-failure simulation, not a wholesale
        # mock replacement.
        searcher.bm25_index.search = Mock(side_effect=Exception("BM25 search failed"))
        searcher.dense_index.search = Mock(side_effect=Exception("Dense search failed"))

        with patch("search.config.get_search_config", return_value=config):
            results = searcher.search("test query", k=5)

        assert results == []

    def test_stats_collection(self):
        """Test statistics collection."""
        searcher = HybridSearcher(self.temp_dir)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        stats = searcher.stats

        assert "bm25_stats" in stats
        assert "dense_stats" in stats
        assert "gpu_memory" in stats
        assert stats["dense_stats"]["total_vectors"] == len(self.documents)
        assert stats["bm25_stats"]["total_documents"] == len(self.documents)

    def test_save_and_load_indices(self):
        """Test saving and loading indices."""
        searcher = HybridSearcher(self.temp_dir)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        searcher.save_indices()

        # Clear in place, then prove load_indices() genuinely repopulates
        # from what save_indices() wrote to disk.
        searcher.bm25_index.clear()
        searcher.dense_index.clear_index()
        assert searcher.bm25_index.is_empty
        assert searcher.dense_index.ntotal == 0

        success = searcher.load_indices()
        assert success

        assert searcher.bm25_index.size == len(self.documents)
        assert searcher.dense_index.ntotal == len(self.documents)
        assert set(searcher.dense_index.chunk_ids) == set(self.doc_ids)

    def test_search_mode_stats(self):
        """Test search mode statistics."""
        searcher = HybridSearcher(self.temp_dir)

        # Initially no searches
        stats = searcher.get_search_mode_stats()
        assert "No searches performed" in stats["message"]

        # Mock a search to generate stats
        searcher.search_executor._search_stats["total_searches"] = 10
        searcher.search_executor._search_stats["bm25_time"] = 1.0
        searcher.search_executor._search_stats["dense_time"] = 2.0
        searcher.search_executor._search_stats["rerank_time"] = 0.5

        stats = searcher.get_search_mode_stats()

        assert stats["total_searches"] == 10
        assert "average_times" in stats
        assert stats["average_times"]["bm25"] == 0.1
        assert stats["average_times"]["dense"] == 0.2
        assert stats["average_times"]["reranking"] == 0.05
        assert stats["average_times"]["total"] == pytest.approx(0.35)

    def test_performance_tracking(self):
        """Test performance tracking during searches."""
        embedder, config = self._stub_search_deps()
        config.multi_hop.enabled = False
        searcher = HybridSearcher(self.temp_dir, embedder=embedder, config=config)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        with patch("search.config.get_search_config", return_value=config):
            initial_searches = searcher.search_executor._search_stats["total_searches"]
            searcher.search("query 1", use_parallel=False)
            searcher.search("query 2", use_parallel=False)

        # Stats should be updated
        assert (
            searcher.search_executor._search_stats["total_searches"]
            == initial_searches + 2
        )
        # Times could legitimately be 0 on a fast in-memory run, so assert
        # type + non-negative rather than a positivity threshold.
        for key in ("bm25_time", "dense_time", "rerank_time"):
            assert key in searcher.search_executor._search_stats
            value = searcher.search_executor._search_stats[key]
            assert isinstance(value, (int, float)), (
                f"{key} should be a numeric duration, got {type(value)}"
            )
            assert value >= 0

    def test_batched_similar_chunks(self):
        """Batched search returns real per-anchor neighbor lists."""
        searcher = HybridSearcher(self.temp_dir)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        result = searcher.dense_index.get_similar_chunks_batched(["doc1", "doc2"], k=2)

        assert "doc1" in result
        assert "doc2" in result
        assert "doc1" not in {cid for cid, _, _ in result["doc1"]}
        assert "doc2" not in {cid for cid, _, _ in result["doc2"]}

    def test_batched_vs_individual_consistency(self):
        """Batched search produces the same results as individual searches."""
        searcher = HybridSearcher(self.temp_dir)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        individual_1 = searcher.dense_index.get_similar_chunks("doc1", k=2)
        individual_2 = searcher.dense_index.get_similar_chunks("doc2", k=2)
        batched = searcher.dense_index.get_similar_chunks_batched(["doc1", "doc2"], k=2)

        assert batched["doc1"] == individual_1
        assert batched["doc2"] == individual_2

    def test_batched_empty_input(self):
        """Test batched search with empty input."""
        searcher = HybridSearcher(self.temp_dir)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        result = searcher.dense_index.get_similar_chunks_batched([], k=5)

        assert result == {}

    def _metadata_with_paths(self):
        """A copy of self.metadata tagging every doc except doc5 as sharing
        one file, so exclude_same_file has a real same-file/cross-file split
        to filter on."""
        return {
            doc_id: {
                **meta,
                "relative_path": "same.py" if doc_id != "doc5" else "other.py",
            }
            for doc_id, meta in self.metadata.items()
        }

    def test_find_similar_default_forwards_exclude_false(self):
        """Default call includes same-file neighbors (exclude_same_file=False)."""
        searcher = HybridSearcher(self.temp_dir)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self._metadata_with_paths()
        )

        results = searcher.find_similar_to_chunk("doc1", k=4)

        result_ids = {r.chunk_id for r in results}
        assert "doc1" not in result_ids
        assert result_ids == {"doc2", "doc3", "doc4", "doc5"}

    def test_find_similar_forwards_exclude_same_file(self):
        """exclude_same_file=True removes same-file neighbors from the results."""
        searcher = HybridSearcher(self.temp_dir)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self._metadata_with_paths()
        )

        results = searcher.find_similar_to_chunk("doc1", k=4, exclude_same_file=True)

        result_ids = {r.chunk_id for r in results}
        assert result_ids == {"doc5"}

    def test_find_similar_exclude_composes_with_rerank_fetch_k(self):
        """rerank=True doubles fetch_k; the exclusion overfetch composes
        with that doubled budget, not a separately-configured one.
        """
        embedder, config = self._stub_search_deps()
        searcher = HybridSearcher(self.temp_dir, embedder=embedder, config=config)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )
        spy = Mock(wraps=searcher.dense_index.get_similar_chunks)
        searcher.dense_index.get_similar_chunks = spy

        searcher.find_similar_to_chunk("doc1", k=3, rerank=True, exclude_same_file=True)

        spy.assert_called_once_with("doc1", 6, exclude_same_file=True)

    def test_multi_hop_uses_batched_search(self):
        """Multi-hop expansion fans out neighbor lookups through
        get_similar_chunks_batched rather than one call per hop-1 result.
        """
        embedder, config = self._stub_search_deps()
        config.multi_hop.enabled = True
        config.multi_hop.hop_count = 2
        searcher = HybridSearcher(self.temp_dir, embedder=embedder, config=config)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )
        embedder.embed_query.return_value = np.array(self.embeddings[0])
        spy = Mock(wraps=searcher.dense_index.get_similar_chunks_batched)
        searcher.dense_index.get_similar_chunks_batched = spy

        with patch("search.config.get_search_config", return_value=config):
            results = searcher.search("test query", k=5, use_parallel=False)

        spy.assert_called()
        assert isinstance(results, list)

    def test_resync_bm25_from_dense_success(self):
        """Resync rebuilds the corpus in place (ADR-0025) -- bm25_index keeps
        its identity, so this asserts real outcomes (search hits, disk
        write) on the same instance searcher.bm25_index already points to,
        and that search_executor.bm25_index (cached once at construction)
        sees it too with no write-back.
        """
        searcher = HybridSearcher(self.temp_dir)
        original_bm25 = searcher.bm25_index

        searcher.dense_index.chunk_ids = ["chunk1", "chunk2", "chunk3"]
        searcher.dense_index.metadata_store.set(
            "chunk1", 0, {"bm25_text": "def func1(): pass"}
        )
        searcher.dense_index.metadata_store.set(
            "chunk2", 1, {"bm25_text": "class MyClass: pass"}
        )
        searcher.dense_index.metadata_store.set(
            "chunk3", 2, {"bm25_text": "async def async_func(): pass"}
        )

        count = searcher.resync_bm25_from_dense()

        assert count == 3
        assert searcher.bm25_index is original_bm25
        assert searcher.search_executor.bm25_index is original_bm25
        assert original_bm25.size == 3
        hits = original_bm25.search("MyClass", k=1)
        assert hits[0][0] == "chunk2"
        assert original_bm25.docs_path.exists()

    def test_resync_bm25_from_dense_empty_dense_index(self):
        """Test resync returns 0 when dense index has no chunks."""
        searcher = HybridSearcher(self.temp_dir)

        count = searcher.resync_bm25_from_dense()

        assert count == 0

    def test_resync_bm25_from_dense_no_content_in_metadata(self):
        """Phase 14.3 finding: production (search/index_sync.py:245-261)
        appends a document for every chunk with ANY metadata entry, reading
        entry["metadata"].get("bm25_text", "") -- defaulting to an empty
        string rather than skipping when bm25_text is absent. The
        pre-rewrite mocked version of this test asserted count == 1, which
        was stale against that behaviour; the real dense index used here
        proves count == 2.
        """
        searcher = HybridSearcher(self.temp_dir)
        searcher.dense_index.chunk_ids = ["chunk1", "chunk2"]
        searcher.dense_index.metadata_store.set(
            "chunk1", 0, {"bm25_text": "valid content"}
        )
        searcher.dense_index.metadata_store.set("chunk2", 1, {})

        count = searcher.resync_bm25_from_dense()

        assert count == 2
        assert set(searcher.bm25_index._doc_ids) == {"chunk1", "chunk2"}

    def test_clear_index_clears_both_indices(self):
        """Test clear_index clears both BM25 and dense indices in place (ADR-0025)."""
        searcher = HybridSearcher(self.temp_dir)
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        original_bm25 = searcher.bm25_index
        original_dense = searcher.dense_index

        searcher.clear_index()

        # ADR-0025: index object identity is stable across a clear -- no
        # swap, no repair list -- and the clear itself really emptied both.
        assert searcher.bm25_index is original_bm25
        assert searcher.dense_index is original_dense
        assert original_bm25.is_empty
        assert original_dense.ntotal == 0

    def test_clear_index_preserves_collaborator_identity(self):
        """ADR-0025 invariant: every collaborator that cached bm25_index/
        dense_index at construction time still resolves to the *same*
        objects after clear_index() -- search_executor, multi_hop_searcher
        and reranking_engine included. This is the regression commit
        db4c181 shipped without coverage: search_executor.bm25_index in
        particular used to go stale after a resync because nothing repaired
        it; under the stable-identity invariant there is nothing to repair.
        """
        searcher = HybridSearcher(self.temp_dir)

        original_bm25 = searcher.bm25_index
        original_dense = searcher.dense_index
        original_metadata_store = searcher.reranking_engine.metadata_store

        searcher.clear_index()

        assert searcher.search_executor.bm25_index is original_bm25
        assert searcher.search_executor.dense_index is original_dense
        assert searcher.multi_hop_searcher.dense_index is original_dense
        assert searcher.reranking_engine.metadata_store is original_metadata_store

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestCallEdgeResolution:
    """Test call edge resolution in HybridSearcher.add_embeddings() (Phase 2)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def test_unique_function_name_resolved(self):
        """Test that unique function names are resolved to full chunk_ids."""
        searcher = HybridSearcher(self.temp_dir)

        # Mock graph storage
        mock_graph = Mock()
        searcher.graph_storage = mock_graph

        # Create embedding results with unique function name
        embedding_results = [
            Mock(
                chunk_id="file_a.py:1-10:function:unique_func",
                metadata={
                    "name": "unique_func",
                    "chunk_type": "function",
                    "file_path": "file_a.py",
                    "language": "python",
                    "calls": [],
                },
                embedding=np.random.rand(768),
                document="def unique_func(): pass",
            ),
            Mock(
                chunk_id="file_b.py:5-15:function:caller",
                metadata={
                    "name": "caller",
                    "chunk_type": "function",
                    "file_path": "file_b.py",
                    "language": "python",
                    "calls": [
                        {
                            "callee_name": "unique_func",  # Should be resolved
                            "line_number": 7,
                            "is_method_call": False,
                        }
                    ],
                },
                embedding=np.random.rand(768),
                document="def caller(): unique_func()",
            ),
        ]

        # Call add_embeddings
        searcher.add_embeddings(embedding_results)

        # Verify add_call_edge was called with resolved chunk_id
        calls = mock_graph.add_call_edge.call_args_list
        assert len(calls) == 1

        # Check that the edge was added with resolved target
        call_kwargs = calls[0][1]  # keyword args
        assert call_kwargs["caller_id"] == "file_b.py:5-15:function:caller"
        assert (
            call_kwargs["callee_name"] == "file_a.py:1-10:function:unique_func"
        )  # Resolved!
        assert call_kwargs["is_resolved"] is True

    def test_ambiguous_function_name_keeps_all_candidates(self):
        """Phase 2: ambiguous function names (multiple project matches) now create
        confidence='ambiguous' edges to all candidates instead of dropping to phantom.
        This preserves recall while tagging low-confidence edges explicitly.
        """
        searcher = HybridSearcher(self.temp_dir)

        # Mock graph storage
        mock_graph = Mock()
        searcher.graph_storage = mock_graph

        # Create embedding results with duplicate function name
        embedding_results = [
            Mock(
                chunk_id="file_a.py:1-10:function:extract",
                metadata={
                    "name": "extract",
                    "chunk_type": "function",
                    "file_path": "file_a.py",
                    "language": "python",
                    "calls": [],
                },
                embedding=np.random.rand(768),
                document="def extract(): pass",
            ),
            Mock(
                chunk_id="file_b.py:1-10:function:extract",
                metadata={
                    "name": "extract",  # Duplicate name — ambiguous
                    "chunk_type": "function",
                    "file_path": "file_b.py",
                    "language": "python",
                    "calls": [],
                },
                embedding=np.random.rand(768),
                document="def extract(): pass",
            ),
            Mock(
                chunk_id="file_c.py:5-15:function:caller",
                metadata={
                    "name": "caller",
                    "chunk_type": "function",
                    "file_path": "file_c.py",
                    "language": "python",
                    "calls": [
                        {
                            "callee_name": "extract",  # Ambiguous: 2 candidates
                            "line_number": 7,
                            "is_method_call": False,
                        }
                    ],
                },
                embedding=np.random.rand(768),
                document="def caller(): extract()",
            ),
        ]

        # Call add_embeddings
        searcher.add_embeddings(embedding_results)

        # Phase 2: ambiguous call → 2 edges (one per candidate), each tagged
        calls = mock_graph.add_call_edge.call_args_list
        assert len(calls) == 2  # one edge per ambiguous candidate

        # All edges from the caller, all resolved, all confidence='ambiguous'
        callee_names = {c[1]["callee_name"] for c in calls}
        assert callee_names == {
            "file_a.py:1-10:function:extract",
            "file_b.py:1-10:function:extract",
        }
        for c in calls:
            kw = c[1]
            assert kw["caller_id"] == "file_c.py:5-15:function:caller"
            assert kw["is_resolved"] is True
            assert kw.get("confidence") == "ambiguous"

    def test_external_call_phantom(self):
        """Test that external library calls remain as phantom nodes."""
        searcher = HybridSearcher(self.temp_dir)

        # Mock graph storage
        mock_graph = Mock()
        searcher.graph_storage = mock_graph

        # Create embedding result calling external library
        embedding_results = [
            Mock(
                chunk_id="file_a.py:1-10:function:my_func",
                metadata={
                    "name": "my_func",
                    "chunk_type": "function",
                    "file_path": "file_a.py",
                    "language": "python",
                    "calls": [
                        {
                            "callee_name": "os.path.join",  # External call
                            "line_number": 5,
                            "is_method_call": True,
                        }
                    ],
                },
                embedding=np.random.rand(768),
                document="def my_func(): os.path.join('a', 'b')",
            )
        ]

        # Call add_embeddings
        searcher.add_embeddings(embedding_results)

        # Verify add_call_edge was called with unresolved name
        calls = mock_graph.add_call_edge.call_args_list
        assert len(calls) == 1

        call_kwargs = calls[0][1]
        assert call_kwargs["callee_name"] == "os.path.join"  # NOT resolved
        assert call_kwargs["is_resolved"] is False

    def test_no_calls_no_errors(self):
        """Test that functions with no calls don't cause errors."""
        searcher = HybridSearcher(self.temp_dir)

        # Mock graph storage
        mock_graph = Mock()
        searcher.graph_storage = mock_graph

        # Create embedding result with no calls
        embedding_results = [
            Mock(
                chunk_id="file_a.py:1-10:function:simple_func",
                metadata={
                    "name": "simple_func",
                    "chunk_type": "function",
                    "file_path": "file_a.py",
                    "language": "python",
                    "calls": [],  # No calls
                },
                embedding=np.random.rand(768),
                document="def simple_func(): return 42",
            )
        ]

        # Should not raise any errors
        searcher.add_embeddings(embedding_results)

        # Verify add_call_edge was never called
        mock_graph.add_call_edge.assert_not_called()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


def test_search_accepts_per_call_weights():
    """Per-call bm25_weight/dense_weight resolve into the RetrievalRequest
    handed to SearchExecutor. There is no instance state left to mutate or
    leave untouched — C2 deleted the construction-time weight fields that
    this test used to also assert on."""
    import tempfile

    temp_dir = tempfile.mkdtemp()
    try:
        searcher = HybridSearcher(temp_dir)
        # A single real doc through both real fakes is enough to flip
        # is_ready True -- execute_single_hop is replaced below, so its
        # content never actually matters to the assertion.
        searcher.index_documents(
            ["def f(): pass"], ["doc0"], [[0.1, 0.2, 0.3, 0.4]], {"doc0": {}}
        )

        exec_mock = Mock(return_value=[])
        searcher.search_executor.execute_single_hop = exec_mock

        with patch("search.config.get_search_config") as mock_cfg:
            cfg = Mock()
            cfg.multi_hop.enabled = False
            cfg.ego_graph.enabled = False
            cfg.parent_retrieval.enabled = False
            cfg.reranker.single_pass = False
            mock_cfg.return_value = cfg
            searcher.search("test query", bm25_weight=0.9, dense_weight=0.1)

        exec_mock.assert_called_once()
        req = exec_mock.call_args.args[0]
        assert req.bm25_weight == 0.9
        assert req.dense_weight == 0.1
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def test_intent_weights_reach_the_leg_via_multihop():
    """D1 regression: per-call weights must reach the leg through the
    multi-hop branch — the branch production actually runs (MultiHopConfig
    defaults to enabled=True) and the one that used to drop them across the
    single_hop_callback seam before RetrievalRequest existed."""
    import tempfile

    temp_dir = tempfile.mkdtemp()
    try:
        searcher = HybridSearcher(temp_dir)
        searcher.index_documents(
            ["def f(): pass"], ["doc0"], [[0.1, 0.2, 0.3, 0.4]], {"doc0": {}}
        )

        leg = Mock(return_value=[])
        searcher.search_executor.execute_single_hop = leg

        with patch("search.config.get_search_config") as mock_cfg:
            cfg = Mock()
            cfg.multi_hop.enabled = True
            cfg.multi_hop.hop_count = 2
            cfg.multi_hop.expansion = 0.3
            cfg.multi_hop.edge_weights = None
            cfg.multi_hop.initial_k_multiplier = 2
            cfg.ego_graph.enabled = False
            cfg.parent_retrieval.enabled = False
            cfg.reranker.single_pass = False
            mock_cfg.return_value = cfg
            searcher.search("q", k=4, bm25_weight=0.9, dense_weight=0.1)

        leg.assert_called_once()
        req = leg.call_args.args[0]
        assert (req.bm25_weight, req.dense_weight) == (0.9, 0.1)
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


class TestSearchTailDedup:
    """Q1: split_block dedup at the tail of HybridSearcher.search()."""

    def _make_searcher_and_config(self, dedupe: bool):
        from search.config import (
            MultiHopConfig,
            RerankerConfig,
            SearchConfig,
        )

        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["def f(): pass"], ["doc0"], [[0.1, 0.2, 0.3, 0.4]], {"doc0": {}}
        )

        # Single-hop only: no multi-hop, no ego, no parent expansion — the
        # tail dedup is the ONLY dedup site on this path.
        config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            reranker=RerankerConfig(dedupe_split_blocks=dedupe),
        )
        config.ego_graph.enabled = False
        config.parent_retrieval.enabled = False
        return searcher, config

    def _dup_results(self):
        from search.reranker import SearchResult

        return [
            SearchResult(
                chunk_id="src/big.py:10-40:split_block:Cls.long_method",
                score=0.9,
                metadata={},
            ),
            SearchResult(
                chunk_id="src/big.py:41-80:split_block:Cls.long_method",
                score=0.8,
                metadata={},
            ),
            SearchResult(
                chunk_id="src/other.py:5-15:function:helper",
                score=0.7,
                metadata={},
            ),
        ]

    def test_tail_dedup_collapses_fragments(self):
        """Fragments of one function collapse even when no rerank_by_query fires
        (single-hop path with ego expansion disabled)."""
        searcher, config = self._make_searcher_and_config(dedupe=True)
        with (
            patch(
                "search.config.get_search_config",
                return_value=config,
            ),
            patch.object(
                searcher, "_single_hop_search", return_value=self._dup_results()
            ),
        ):
            results = searcher.search("query", k=5)

        assert [r.chunk_id for r in results] == [
            "src/big.py:10-40:split_block:Cls.long_method",
            "src/other.py:5-15:function:helper",
        ]

    def test_tail_dedup_disabled_keeps_fragments(self):
        """dedupe_split_blocks=False preserves the pre-Q1 behaviour."""
        searcher, config = self._make_searcher_and_config(dedupe=False)
        with (
            patch(
                "search.config.get_search_config",
                return_value=config,
            ),
            patch.object(
                searcher, "_single_hop_search", return_value=self._dup_results()
            ),
        ):
            results = searcher.search("query", k=5)

        assert [r.chunk_id for r in results] == [
            "src/big.py:10-40:split_block:Cls.long_method",
            "src/big.py:41-80:split_block:Cls.long_method",
            "src/other.py:5-15:function:helper",
        ]


class TestSinglePassTailRerank:
    """Q3: single_pass runs exactly one listwise rerank at the search() tail."""

    def _make_searcher_and_config(self, single_pass: bool):
        from search.config import (
            MultiHopConfig,
            RerankerConfig,
            SearchConfig,
        )

        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["def f(): pass"], ["doc0"], [[0.1, 0.2, 0.3, 0.4]], {"doc0": {}}
        )

        # Single-hop only, ego/parent expansion off: on the default path the
        # tail rerank never fires here; under single_pass it must fire anyway.
        config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            reranker=RerankerConfig(single_pass=single_pass),
        )
        config.ego_graph.enabled = False
        config.parent_retrieval.enabled = False
        return searcher, config

    def _results(self):
        from search.reranker import SearchResult

        return [
            SearchResult(
                chunk_id="src/a.py:1-10:function:alpha", score=0.9, metadata={}
            ),
            SearchResult(
                chunk_id="src/b.py:1-10:function:beta", score=0.8, metadata={}
            ),
            SearchResult(
                chunk_id="src/c.py:1-10:function:gamma", score=0.7, metadata={}
            ),
        ]

    def test_single_pass_reranks_once_with_k(self):
        """The tail pass fires exactly once with k=k even though ego expansion
        never grew results past k (the default path's trigger condition)."""
        searcher, config = self._make_searcher_and_config(single_pass=True)
        engine = Mock()
        engine.rerank_by_query.side_effect = lambda **kw: kw["results"][: kw["k"]]
        searcher.reranking_engine = engine
        with (
            patch(
                "search.config.get_search_config",
                return_value=config,
            ),
            patch.object(searcher, "_single_hop_search", return_value=self._results()),
        ):
            results = searcher.search("query", k=2)

        engine.rerank_by_query.assert_called_once()
        assert engine.rerank_by_query.call_args.kwargs["k"] == 2
        assert [r.chunk_id for r in results] == [
            "src/a.py:1-10:function:alpha",
            "src/b.py:1-10:function:beta",
        ]

    def test_default_path_unchanged_when_single_pass_off(self):
        """single_pass=False preserves pre-Q3 behaviour: no tail rerank when
        ego expansion is disabled."""
        searcher, config = self._make_searcher_and_config(single_pass=False)
        engine = Mock()
        searcher.reranking_engine = engine
        with (
            patch(
                "search.config.get_search_config",
                return_value=config,
            ),
            patch.object(searcher, "_single_hop_search", return_value=self._results()),
        ):
            results = searcher.search("query", k=2)

        engine.rerank_by_query.assert_not_called()
        assert [r.chunk_id for r in results] == [
            "src/a.py:1-10:function:alpha",
            "src/b.py:1-10:function:beta",
            "src/c.py:1-10:function:gamma",
        ]


class TestEgoOutputBounding:
    """Fix #4: drop_nonpositive_output bounds ego-graph output to the
    cross-encoder's own non-negative judgments (search.hybrid_searcher's
    wiring; see test_ego_output_bounding.py for the pure-function cases)."""

    def _make_searcher_and_config(self, drop: bool):
        from search.config import MultiHopConfig, SearchConfig

        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["def f(): pass"], ["doc0"], [[0.1, 0.2, 0.3, 0.4]], {"doc0": {}}
        )

        # Single-hop only: results are injected directly via
        # _single_hop_search with source/reranker_score pre-set, so no real
        # ego expansion or rerank pass needs to run for the filter itself
        # to be exercised.
        config = SearchConfig(multi_hop=MultiHopConfig(enabled=False))
        config.ego_graph.enabled = False
        config.ego_graph.drop_nonpositive_output = drop
        config.parent_retrieval.enabled = False
        return searcher, config

    def _mixed_results(self):
        from search.reranker import SearchResult

        return [
            SearchResult(
                chunk_id="src/a.py:1-10:function:alpha",
                score=0.9,
                metadata={"reranker_score": 0.4},
                source="hybrid",
            ),
            SearchResult(
                chunk_id="src/b.py:1-10:function:beta",
                score=0.5,
                metadata={"reranker_score": -0.12},
                source="ego_graph",
            ),
            SearchResult(
                chunk_id="src/c.py:1-10:function:gamma",
                score=0.4,
                metadata={"reranker_score": 0.0},
                source="ego_graph",
            ),
            SearchResult(
                chunk_id="src/d.py:1-10:function:delta",
                score=0.3,
                metadata={"reranker_score": 0.02},
                source="ego_graph",
            ),
            SearchResult(
                chunk_id="src/e.py:1-10:function:epsilon",
                score=0.2,
                metadata={},  # no reranker_score yet -- left alone
                source="ego_graph",
            ),
            SearchResult(
                chunk_id="src/f.py:1-10:function:phi",
                score=-0.9,
                metadata={"reranker_score": -0.9},
                source="multi_hop",
            ),
        ]

    def test_disabled_is_byte_identical(self):
        """drop_nonpositive_output=False preserves pre-fix behaviour."""
        searcher, config = self._make_searcher_and_config(drop=False)
        mixed = self._mixed_results()
        with (
            patch("search.config.get_search_config", return_value=config),
            patch.object(searcher, "_single_hop_search", return_value=mixed),
        ):
            results = searcher.search("query", k=10)

        assert [r.chunk_id for r in results] == [r.chunk_id for r in mixed]

    def test_enabled_drops_only_nonpositive_ego_results(self):
        """Drops ego_graph with reranker_score <= 0 (including exact 0.0);
        keeps positive-scored ego_graph, unset-score ego_graph, and every
        non-ego_graph result (including a negatively-scored multi_hop one)."""
        searcher, config = self._make_searcher_and_config(drop=True)
        with (
            patch("search.config.get_search_config", return_value=config),
            patch.object(
                searcher, "_single_hop_search", return_value=self._mixed_results()
            ),
        ):
            results = searcher.search("query", k=10)

        assert [r.chunk_id for r in results] == [
            "src/a.py:1-10:function:alpha",
            "src/d.py:1-10:function:delta",
            "src/e.py:1-10:function:epsilon",
            "src/f.py:1-10:function:phi",
        ]


class TestConfigThreadedToReranker:
    """C2 (docs/adr/0018): the config a caller passes to search() must be
    what RerankingEngine actually acts on, not silently replaced by the
    process-global singleton reranking_engine.rerank_by_query() re-fetches
    internally when no config kwarg is threaded through.

    Before this refactor rerank_by_query() had no config parameter at all,
    so `call_args.kwargs["config"]` would KeyError — this assertion was
    unwritable until search()'s call sites threaded the request-scoped
    config through (search/hybrid_searcher.py:799, :812).
    """

    def test_passed_config_reaches_reranking_engine_not_the_singleton(self):
        from search.config import MultiHopConfig, RerankerConfig, SearchConfig
        from search.reranker import SearchResult

        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["def f(): pass"], ["doc0"], [[0.1, 0.2, 0.3, 0.4]], {"doc0": {}}
        )

        # The service-locator default (what a stale re-fetch would read) —
        # deliberately a different top_k_candidates than the config passed
        # to search(), so the two are distinguishable.
        singleton_config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            reranker=RerankerConfig(single_pass=True, top_k_candidates=11),
        )
        singleton_config.ego_graph.enabled = False
        singleton_config.parent_retrieval.enabled = False

        passed_config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            reranker=RerankerConfig(single_pass=True, top_k_candidates=99),
        )
        passed_config.ego_graph.enabled = False
        passed_config.parent_retrieval.enabled = False

        results = [
            SearchResult(
                chunk_id="src/a.py:1-10:function:alpha", score=0.9, metadata={}
            ),
            SearchResult(
                chunk_id="src/b.py:1-10:function:beta", score=0.8, metadata={}
            ),
        ]

        engine = Mock()
        engine.rerank_by_query.side_effect = lambda **kw: kw["results"][: kw["k"]]
        searcher.reranking_engine = engine

        with (
            patch(
                "search.config.get_search_config",
                return_value=singleton_config,
            ),
            patch.object(searcher, "_single_hop_search", return_value=results),
        ):
            searcher.search("query", k=2, config=passed_config)

        engine.rerank_by_query.assert_called_once()
        # Identity, not just equal fields — proves the engine received the
        # request-scoped object the caller passed rather than a value that
        # happens to match it.
        assert engine.rerank_by_query.call_args.kwargs["config"] is passed_config
        assert (
            engine.rerank_by_query.call_args.kwargs["config"].reranker.top_k_candidates
            == 99
        )


class TestCaptureQueryText:
    """observability.capture_query_text gates ATTR_CAPTURE_QUERY on the
    search.hybrid span (:688-695 fails closed unless config opts in)."""

    def _make_ready_searcher(self):
        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["def f(): pass"], ["doc0"], [[0.1, 0.2, 0.3, 0.4]], {"doc0": {}}
        )
        return searcher

    def _make_config(self, *, capture: bool):
        from search.config import MultiHopConfig, ObservabilityConfig, SearchConfig

        config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            observability=ObservabilityConfig(capture_query_text=capture),
        )
        config.ego_graph.enabled = False
        config.parent_retrieval.enabled = False
        return config

    def _run_search_capturing_spans(self, searcher, config, query):
        spans: list[Mock] = []

        @contextlib.contextmanager
        def _fake_traced_block(name, **attrs):  # noqa: ARG001 - matches traced_block signature
            span = Mock()
            spans.append(span)
            yield span

        with (
            patch(
                "search.config.get_search_config",
                return_value=config,
            ),
            patch.object(searcher, "_single_hop_search", return_value=[]),
            patch("search.hybrid_searcher.traced_block", _fake_traced_block),
        ):
            searcher.search(query, k=5)

        assert spans, "search.hybrid span was never opened"
        return spans[0]

    def test_capture_query_text_true_sets_span_attribute(self):
        searcher = self._make_ready_searcher()
        config = self._make_config(capture=True)

        span = self._run_search_capturing_spans(searcher, config, "secret query text")

        span.set_attribute.assert_any_call(ATTR_CAPTURE_QUERY, "secret query text")

    def test_capture_query_text_false_does_not_set_span_attribute(self):
        searcher = self._make_ready_searcher()
        config = self._make_config(capture=False)

        span = self._run_search_capturing_spans(searcher, config, "secret query text")

        calls = [
            c
            for c in span.set_attribute.call_args_list
            if c.args[0] == ATTR_CAPTURE_QUERY
        ]
        assert calls == []


class TestEgoGraphExpansion:
    """_apply_ego_graph_expansion (search.hybrid_searcher:791-880) -- every
    other test in this file sets ego_graph.enabled=False, so this method's
    combine (867) and neighbor-cap (855-856) logic was entirely unexercised.
    Phase 14.3 mutation testing surfaced ~35 surviving mutants here."""

    def test_combines_anchors_then_neighbors_in_that_order(self):
        from search.config import EgoGraphConfig
        from search.reranker import SearchResult

        searcher = HybridSearcher(tempfile.mkdtemp())
        anchor = SearchResult(chunk_id="a.py:1-5:function:f", score=0.9, metadata={})
        neighbor = SearchResult(chunk_id="b.py:1-5:function:g", score=0.5, metadata={})

        searcher.ego_graph_retriever = Mock()
        searcher.ego_graph_retriever.expand_search_results.return_value = (
            [neighbor.chunk_id],
            {},
        )
        searcher.ego_graph_retriever.score_neighbors.return_value = [neighbor]

        combined = searcher._apply_ego_graph_expansion(
            [anchor],
            EgoGraphConfig(enabled=True, max_neighbors_per_hop=10, k_hops=2),
            original_k=5,
            query="test",
        )

        assert [r.chunk_id for r in combined] == [anchor.chunk_id, neighbor.chunk_id]

    def test_forwards_policy_to_retriever(self):
        """The TraversalPolicy handed in reaches expand_search_results
        untouched; None resolves inside the retriever, not here."""
        from graph.traversal_policy import TraversalPolicy
        from search.config import EgoGraphConfig
        from search.reranker import SearchResult

        searcher = HybridSearcher(tempfile.mkdtemp())
        anchor = SearchResult(chunk_id="a.py:1-5:function:f", score=0.9, metadata={})
        searcher.ego_graph_retriever = Mock()
        searcher.ego_graph_retriever.expand_search_results.return_value = ([], {})
        ego_config = EgoGraphConfig(enabled=True)
        policy = TraversalPolicy(drop_ambiguous=True, min_confidence=0.65)

        searcher._apply_ego_graph_expansion(
            [anchor], ego_config, original_k=5, query="test", policy=policy
        )

        searcher.ego_graph_retriever.expand_search_results.assert_called_once_with(
            [{"chunk_id": anchor.chunk_id, "score": anchor.score}], ego_config, policy
        )

    def test_caps_neighbors_to_min_of_hop_budget_and_k_multiple(self):
        from search.config import EgoGraphConfig
        from search.reranker import SearchResult

        searcher = HybridSearcher(tempfile.mkdtemp())
        anchor = SearchResult(
            chunk_id="anchor.py:1-5:function:f", score=0.9, metadata={}
        )
        # max_neighbors_per_hop(4) * k_hops(3) = 12; original_k(10) * 3 = 30
        # -- min is 12, the hop-budget term. Chosen so the two terms diverge
        # under Add-for-Mul mutation of the hop-budget term (4+3=7 != 4*3=12)
        # while the k-multiple term (30) stays clearly non-binding either way.
        neighbors = [
            SearchResult(
                chunk_id=f"n{i}.py:1-5:function:g", score=1.0 - i * 0.05, metadata={}
            )
            for i in range(15)
        ]

        searcher.ego_graph_retriever = Mock()
        searcher.ego_graph_retriever.expand_search_results.return_value = (
            [n.chunk_id for n in neighbors],
            {},
        )
        searcher.ego_graph_retriever.score_neighbors.return_value = list(neighbors)

        combined = searcher._apply_ego_graph_expansion(
            [anchor],
            EgoGraphConfig(enabled=True, max_neighbors_per_hop=4, k_hops=3),
            original_k=10,
            query="test",
        )

        # Anchor plus the top-12 (by score, descending) neighbors, capped at
        # min(max_neighbors_per_hop * k_hops, original_k * 3) == min(12, 30) == 12.
        assert [r.chunk_id for r in combined] == [anchor.chunk_id] + [
            f"n{i}.py:1-5:function:g" for i in range(12)
        ]


class TestParentExpansion:
    """_apply_parent_expansion (search.hybrid_searcher:883-960) -- every
    other test in this file sets parent_retrieval.enabled=False, so this
    method's combine (946) and results-to-expand slice (909-914) logic was
    entirely unexercised. Phase 14.3 mutation testing surfaced ~35 surviving
    mutants here."""

    def test_combines_original_then_parent_chunk_in_that_order(self):
        from search.config import ParentRetrievalConfig
        from search.reranker import SearchResult

        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["class Widget: ...", "def render(self): ..."],
            ["widget.py:1-20:class:Widget", "widget.py:5-8:method:render"],
            [[0.1, 0.2, 0.3, 0.4], [0.4, 0.3, 0.2, 0.1]],
            {
                "widget.py:1-20:class:Widget": {"kind": "class"},
                "widget.py:5-8:method:render": {
                    "kind": "method",
                    "parent_chunk_id": "widget.py:1-20:class:Widget",
                },
            },
        )
        child = SearchResult(
            chunk_id="widget.py:5-8:method:render",
            score=0.9,
            metadata={"parent_chunk_id": "widget.py:1-20:class:Widget"},
        )

        combined = searcher._apply_parent_expansion(
            [child], ParentRetrievalConfig(enabled=True, include_parent_content=True)
        )

        assert [r.chunk_id for r in combined] == [
            "widget.py:5-8:method:render",
            "widget.py:1-20:class:Widget",
        ]
        assert combined[1].metadata.get("kind") == "class"

    def test_max_results_to_expand_limits_which_children_are_scanned(self):
        from search.config import ParentRetrievalConfig
        from search.reranker import SearchResult

        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            [
                "class A: ...",
                "class B: ...",
                "def a_m(self): ...",
                "def b_m(self): ...",
            ],
            [
                "a.py:1-5:class:A",
                "b.py:1-5:class:B",
                "a.py:6-8:method:m",
                "b.py:6-8:method:m",
            ],
            [[0.1] * 4, [0.2] * 4, [0.3] * 4, [0.4] * 4],
            {
                "a.py:1-5:class:A": {"kind": "class"},
                "b.py:1-5:class:B": {"kind": "class"},
                "a.py:6-8:method:m": {"parent_chunk_id": "a.py:1-5:class:A"},
                "b.py:6-8:method:m": {"parent_chunk_id": "b.py:1-5:class:B"},
            },
        )
        children = [
            SearchResult(
                chunk_id="a.py:6-8:method:m",
                score=0.9,
                metadata={"parent_chunk_id": "a.py:1-5:class:A"},
            ),
            SearchResult(
                chunk_id="b.py:6-8:method:m",
                score=0.8,
                metadata={"parent_chunk_id": "b.py:1-5:class:B"},
            ),
        ]

        combined = searcher._apply_parent_expansion(
            children,
            ParentRetrievalConfig(enabled=True, include_parent_content=True),
            max_results_to_expand=1,
        )

        # Only the first child (within the max_results_to_expand=1 slice)
        # gets its parent looked up and appended.
        assert [r.chunk_id for r in combined] == [
            "a.py:6-8:method:m",
            "b.py:6-8:method:m",
            "a.py:1-5:class:A",
        ]


class TestRemoveFilesCacheEviction:
    """remove_files (search.hybrid_searcher:1216-1223) delegates removal to
    IndexSynchronizer and must evict the metadata cache only when something
    was actually removed (#44 -- a stale cache entry surviving a no-op
    remove would return wrong results after re-indexing the same path)."""

    def test_clears_cache_when_files_were_removed(self):
        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher._metadata_cache["stale.py:1-5:function:f"] = None
        searcher.index_sync.remove_files = Mock(return_value=3)

        removed = searcher.remove_files({"stale.py"}, "proj")

        assert removed == 3
        assert searcher._metadata_cache == {}

    def test_leaves_cache_untouched_when_nothing_removed(self):
        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher._metadata_cache["kept.py:1-5:function:f"] = None
        searcher.index_sync.remove_files = Mock(return_value=0)

        removed = searcher.remove_files({"missing.py"}, "proj")

        assert removed == 0
        assert "kept.py:1-5:function:f" in searcher._metadata_cache


class TestIndexStats:
    """get_stats (search.hybrid_searcher:501-515) and get_index_size
    (:517-521) -- the MCP-facing stats surface -- had zero tests: only the
    `.stats` property (test_stats_collection) and per-search-mode timing
    (test_search_mode_stats) were covered. Both methods share the same
    `dense_count = ... if self.dense_index.index else 0` ternary, which a
    populated-index test is required to exercise the True branch of."""

    def test_get_stats_with_populated_indices(self):
        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["def f(): ...", "def g(): ..."],
            ["a.py:1-2:function:f", "b.py:1-2:function:g"],
            [[0.1, 0.2], [0.3, 0.4]],
        )

        stats = searcher.get_stats()

        assert stats["total_chunks"] == 2
        assert stats["bm25_documents"] == 2
        assert stats["dense_vectors"] == 2
        assert stats["synced"] is True
        assert stats["is_ready"] is True
        assert stats["bm25_ready"] is True
        assert stats["dense_ready"] is True

    def test_get_stats_on_empty_index(self):
        searcher = HybridSearcher(tempfile.mkdtemp())

        stats = searcher.get_stats()

        assert stats["total_chunks"] == 0
        assert stats["synced"] is True
        assert stats["is_ready"] is False
        assert stats["bm25_ready"] is False
        assert stats["dense_ready"] is False

    def test_get_index_size_reflects_populated_dense_index(self):
        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["def f(): ...", "def g(): ...", "def h(): ..."],
            ["a.py:1-2:function:f", "b.py:1-2:function:g", "c.py:1-2:function:h"],
            [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
        )

        assert searcher.get_index_size() == 3

    def test_get_index_size_on_empty_index(self):
        """The populated test above always takes the ternary's if-branch
        (index is truthy either way), so it can't distinguish `else 0` from
        `else 1`/`else -1` -- only an empty (falsy) index reaches the else."""
        searcher = HybridSearcher(tempfile.mkdtemp())

        assert searcher.get_index_size() == 0

    def test_get_stats_synced_false_when_dense_exceeds_bm25(self):
        """The equal-count populated test above can't distinguish `==` from
        `<=`/`>=`/`is` on "synced" -- all four agree when counts are equal.
        Dense > bm25 catches `<=` (which would wrongly report True)."""
        from embeddings.embedder import EmbeddingResult

        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["def f(): ...", "def g(): ..."],
            ["a.py:1-2:function:f", "b.py:1-2:function:g"],
            [[0.1, 0.2], [0.3, 0.4]],
        )
        searcher.dense_index.add_embeddings(
            [
                EmbeddingResult(
                    embedding=np.array([0.5, 0.6], dtype=np.float32),
                    chunk_id="c.py:1-2:function:h",
                    metadata={},
                )
            ]
        )

        stats = searcher.get_stats()

        assert stats["bm25_documents"] == 2
        assert stats["dense_vectors"] == 3
        assert stats["synced"] is False

    def test_get_stats_synced_false_when_bm25_exceeds_dense(self):
        """Bm25 > dense catches `>=` (which would wrongly report True)."""
        searcher = HybridSearcher(tempfile.mkdtemp())
        searcher.index_documents(
            ["def f(): ...", "def g(): ...", "def h(): ..."],
            ["a.py:1-2:function:f", "b.py:1-2:function:g", "c.py:1-2:function:h"],
            [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
        )
        searcher.dense_index.remove_files({"c.py"})

        stats = searcher.get_stats()

        assert stats["bm25_documents"] == 3
        assert stats["dense_vectors"] == 2
        assert stats["synced"] is False


class TestIndexDocumentsLengthValidation:
    """index_documents (search.hybrid_searcher:564-573) raises ValueError
    when documents/doc_ids/embeddings lengths disagree -- entirely
    untested, so mutating either `!=` to `<` or the `or` to `and` survived."""

    def test_raises_when_doc_ids_shorter_than_documents(self):
        searcher = HybridSearcher(tempfile.mkdtemp())

        with pytest.raises(ValueError, match="same length"):
            searcher.index_documents(
                ["def f(): ...", "def g(): ..."],
                ["a.py:1-2:function:f"],
                [[0.1, 0.2], [0.3, 0.4]],
            )

    def test_raises_when_embeddings_shorter_than_documents(self):
        searcher = HybridSearcher(tempfile.mkdtemp())

        with pytest.raises(ValueError, match="same length"):
            searcher.index_documents(
                ["def f(): ...", "def g(): ..."],
                ["a.py:1-2:function:f", "b.py:1-2:function:g"],
                [[0.1, 0.2]],
            )


class TestSemanticModeEmptyIndexGuard:
    """execute (search.hybrid_searcher:666-672) short-circuits semantic-mode
    search to [] when the dense index is empty -- every other test either
    uses hybrid/bm25 mode or a populated index, so this branch and its
    `search_mode == SearchMode.SEMANTIC` condition were never reached."""

    def test_semantic_search_on_empty_dense_index_returns_empty(self):
        searcher = HybridSearcher(tempfile.mkdtemp())

        results = searcher.search("test query", k=5, search_mode="semantic")

        assert results == []

    def test_semantic_search_ignores_empty_bm25_when_dense_is_populated(self):
        """Distinguishes the semantic-only guard (dense-only readiness) from
        the `else` (hybrid) branch's `not is_ready`, which requires BOTH
        indices -- an all-empty searcher can't tell these apart since both
        branches return [] there. BM25 stays empty; only dense is
        populated, bypassing index_documents (which populates both)."""
        from embeddings.embedder import EmbeddingResult

        embedder = Mock()
        embedder.embed_query.return_value = np.array([0.1, 0.2], dtype=np.float32)
        config = SearchConfig()
        config.reranker.enabled = False
        config.multi_hop.enabled = False
        searcher = HybridSearcher(tempfile.mkdtemp(), embedder=embedder, config=config)
        searcher.dense_index.add_embeddings(
            [
                EmbeddingResult(
                    embedding=np.array([0.1, 0.2], dtype=np.float32),
                    chunk_id="a.py:1-2:function:f",
                    metadata={},
                )
            ]
        )
        assert searcher.bm25_index.is_empty

        with patch("search.config.get_search_config", return_value=config):
            results = searcher.search("test query", k=5, search_mode="semantic")

        assert results
        assert results[0].chunk_id == "a.py:1-2:function:f"


class TestParentExpansionContentStripping:
    """_apply_parent_expansion's include_parent_content=False branch
    (search.hybrid_searcher:929-933) filters "content" out of parent
    metadata. FakeDenseIndex.add_embeddings already strips "content" at
    indexing time, so exercising this branch through a real index round
    trip can't distinguish it -- get_chunk_by_id is mocked directly here,
    a legitimate boundary since the fake cannot produce this input."""

    def test_include_parent_content_false_strips_content_key(self):
        from search.config import ParentRetrievalConfig
        from search.reranker import SearchResult

        searcher = HybridSearcher(tempfile.mkdtemp())
        child = SearchResult(
            chunk_id="widget.py:5-8:method:render",
            score=0.9,
            metadata={"parent_chunk_id": "widget.py:1-20:class:Widget"},
        )
        searcher.dense_index.get_chunk_by_id = Mock(
            return_value={"content": "class Widget: ...", "kind": "class"}
        )

        combined = searcher._apply_parent_expansion(
            [child], ParentRetrievalConfig(enabled=True, include_parent_content=False)
        )

        assert "content" not in combined[1].metadata
        assert combined[1].metadata.get("kind") == "class"
