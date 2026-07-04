"""Tests for reranking engine functionality.

Extracted from test_hybrid_search.py (Phase 3.2 refactoring).
De-mocked in Phase 4.2 Tier-3 (2026-06-30):
  - FakeMetadataStore replaces MagicMock for metadata_store
  - Real SearchConfig/RerankerConfig dataclasses replace MagicMock configs
  - patch.object(engine, "should_enable_neural_reranking") replaced by
    engine._session_oom_detected = True (drives the real method to return False
    without patching; no disk I/O because _session_oom_detected is checked first)
  - test_should_enable_neural_reranking_insufficient_vram fixed to configure
    mem_get_info (the actual API path) instead of the unused get_device_properties
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from search.config import PerformanceConfig, RerankerConfig, SearchConfig
from search.reranker import SearchResult
from search.reranking_engine import RerankingEngine


class FakeMetadataStore:
    """In-memory metadata store for testing (replaces MagicMock).

    Implements the single method called by RerankingEngine: .get(chunk_id).
    Pre-populate ._data before exercising embedding-based re-scoring.
    """

    def __init__(self, data: dict | None = None) -> None:
        self._data: dict = data or {}

    def get(self, chunk_id: str) -> dict | None:
        return self._data.get(chunk_id)


class TestRerankingEngine:
    """Test reranking engine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_embedder = MagicMock()  # true boundary: wraps neural model
        self.fake_metadata_store = FakeMetadataStore()
        self.engine = RerankingEngine(
            embedder=self.mock_embedder, metadata_store=self.fake_metadata_store
        )

    @patch("search.reranking_engine.torch")
    def test_should_enable_neural_reranking_no_gpu(self, mock_torch):
        """Test neural reranking disabled when no GPU available."""
        mock_torch.cuda.is_available.return_value = False

        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = SearchConfig(
                reranker=RerankerConfig(enabled=True)
            )

            result = self.engine.should_enable_neural_reranking()
            assert result is False

    @patch("search.reranking_engine.torch")
    def test_should_enable_neural_reranking_insufficient_vram(self, mock_torch):
        """Test neural reranking disabled with insufficient VRAM.

        Previously this test mocked cuda.get_device_properties / memory_allocated,
        but the implementation calls cuda.mem_get_info(0). The test passed
        accidentally via the exception-catch path. Now fixed to use the real API.
        """
        mock_torch.cuda.is_available.return_value = True
        # 1 GB free < 4 GB required → should return False
        mock_torch.cuda.mem_get_info.return_value = (
            1 * 1024**3,  # 1 GB free
            8 * 1024**3,  # 8 GB total
        )

        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = SearchConfig(
                reranker=RerankerConfig(enabled=True, min_vram_gb=4.0)
            )

            result = self.engine.should_enable_neural_reranking()
            assert result is False

    @patch("search.reranking_engine.torch")
    def test_should_enable_neural_reranking_sufficient_vram(self, mock_torch):
        """Test neural reranking enabled with sufficient VRAM."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            5 * 1024**3,  # 5 GB free
            8 * 1024**3,  # 8 GB total
        )

        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = SearchConfig(
                reranker=RerankerConfig(enabled=True, min_vram_gb=4.0)
            )

            result = self.engine.should_enable_neural_reranking()
            assert result is True
            # Device index must be 0 (kills NumberReplacer 0→1 mutant)
            mock_torch.cuda.mem_get_info.assert_called_with(0)

    def test_rerank_by_query_empty_results(self):
        """Test reranking with empty results."""
        results = self.engine.rerank_by_query("test query", [], k=5)
        assert results == []

    def test_rerank_by_query_embedding_based(self):
        """Test embedding-based reranking.

        Uses engine._session_oom_detected = True so should_enable_neural_reranking
        returns False immediately (no GPU/config I/O), keeping neural path inactive
        and letting the pure cosine/sort/truncate island run unobstructed.
        """
        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.7, metadata={}),
            SearchResult(chunk_id="chunk3", score=0.6, metadata={}),
        ]

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        # chunk1: sim = dot([1,0,0],[0.8,0.6,0]) / (1 * 1) ≈ 0.8
        # chunk2: sim = dot([1,0,0],[0,1,0]) / (1 * 1) = 0.0
        # chunk3: sim = dot([1,0,0],[1,0,0]) / (1 * 1) = 1.0
        chunk_embeddings = {
            "chunk1": np.array([0.8, 0.6, 0.0]),
            "chunk2": np.array([0.0, 1.0, 0.0]),
            "chunk3": np.array([1.0, 0.0, 0.0]),
        }
        self.fake_metadata_store._data = {
            cid: {"embedding": emb.tolist()} for cid, emb in chunk_embeddings.items()
        }

        # Prevent neural reranking without patching the method:
        # _session_oom_detected is checked first in should_enable_neural_reranking,
        # returning False before any config/GPU calls.
        self.engine._session_oom_detected = True

        reranked = self.engine.rerank_by_query(
            "test query", results, k=3, search_mode="semantic"
        )

        # chunk3 should be first (cosine similarity = 1.0)
        assert len(reranked) == 3
        assert reranked[0].chunk_id == "chunk3"
        assert reranked[0].score > reranked[1].score

    def test_rerank_by_query_no_embedder(self):
        """Test reranking without embedder (keeps original scores)."""
        engine = RerankingEngine(embedder=None, metadata_store=FakeMetadataStore())

        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.7, metadata={}),
        ]

        # No embedder → embedding path skipped; neural path bypassed via OOM flag.
        engine._session_oom_detected = True
        reranked = engine.rerank_by_query(
            "test query", results, k=2, search_mode="bm25"
        )

        # Should keep original ordering (sorted by score)
        assert len(reranked) == 2
        assert reranked[0].chunk_id == "chunk2"  # higher original score
        assert reranked[1].chunk_id == "chunk1"

    # ------------------------------------------------------------------
    # Kill-tests: mutation-targeted (Phase 4.2 Tier-3 hardening)
    # ------------------------------------------------------------------

    @patch("search.reranking_engine.torch")
    def test_should_enable_ram_fallback_kills_true_false_mutant(self, mock_torch):
        """RAM fallback path must return True (kills L80 ReplaceTrueWithFalse mutant).

        When allow_ram_fallback=True the VRAM threshold check is bypassed.
        The mutant returns False instead — this test pinpoints that gap.
        """
        mock_torch.cuda.is_available.return_value = True

        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = SearchConfig(
                reranker=RerankerConfig(enabled=True),
                performance=PerformanceConfig(allow_ram_fallback=True),
            )
            result = self.engine.should_enable_neural_reranking()

        assert result is True

    @patch("search.reranking_engine.torch")
    def test_should_enable_vram_nonmultiple_kills_floordiv_mutant(self, mock_torch):
        """Non-multiple VRAM distinguishes / from // (kills L84 Div_FloorDiv mutant).

        4.5 GB / 1024**3 = 4.5 >= 4.3 → True.
        4.5 GB // 1024**3 = 4   < 4.3 → False (mutant fails).
        """
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            int(4.5 * 1024**3),  # 4.5 GB free — not a multiple of 1 GiB
            8 * 1024**3,
        )

        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = SearchConfig(
                reranker=RerankerConfig(enabled=True, min_vram_gb=4.3)
            )
            result = self.engine.should_enable_neural_reranking()

        assert result is True

    def test_rerank_bm25_mode_skips_embedding_kills_or_mutant(self):
        """bm25 mode must NOT invoke embedder even when one is present.

        Kills L185 ReplaceAndWithOr mutant: with 'or', any truthy embedder
        would enter the embedding loop even for bm25 queries.
        """
        results = [SearchResult(chunk_id="c1", score=0.5, metadata={})]
        self.engine._session_oom_detected = True

        self.engine.rerank_by_query("query", results, k=1, search_mode="bm25")

        # embedder is present (set in setup_method) but must NOT be called for bm25
        self.mock_embedder.embed_query.assert_not_called()

    def test_rerank_missing_first_metadata_kills_or_and_exception_mutants(self):
        """None metadata on first chunk must not abort the loop for later chunks.

        Kills:
          L196 ReplaceAndWithOr: 'None or "embedding" in None' raises TypeError
          L205 ExceptionReplacer: wrong except type lets TypeError propagate
        Both are killed when the second chunk's score IS updated despite the first being absent.
        """
        results = [
            SearchResult(
                chunk_id="no_meta", score=0.3, metadata={}
            ),  # no metadata → skip
            SearchResult(
                chunk_id="has_meta", score=0.1, metadata={}
            ),  # has embedding → update
        ]
        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        # has_meta chunk is perfectly aligned → cosine = 1.0
        self.fake_metadata_store._data = {
            "has_meta": {"embedding": [1.0, 0.0, 0.0]}
            # no_meta returns None → must short-circuit cleanly via 'and', not crash
        }
        self.engine._session_oom_detected = True

        reranked = self.engine.rerank_by_query(
            "q", results, k=2, search_mode="semantic"
        )

        # has_meta must win: cosine 1.0 > no_meta's original 0.3
        assert reranked[0].chunk_id == "has_meta"
        assert reranked[1].chunk_id == "no_meta"

    def test_rerank_cosine_exact_score_kills_denominator_mutants(self):
        """Exact cosine scores distinguish correct / from *, **, +, // denominator mutants.

        Kills:
          L199 Div_Mul:      dot * norm_q * norm_c (wildly different)
          L200 Mul_Add:      dot / (norm_q + norm_c)  (≠ correct for asymmetric norms)
          L200 Mul_Pow:      dot / (norm_q ** norm_c) (≠ correct when norm_c ≠ 0 or 1)
          L200 Mul_FloorDiv: dot / (norm_q // norm_c) (integer floor changes result)

        Setup: query=[2,0,0] (norm=2), so norm_q varies from norm_c:
          'aligned'  [1,0,0]: dot=2, norm_c=1 → cosine=2/(2×1)=1.0
          'diagonal' [0.5,0.5,0]: dot=1, norm_c≈0.707 → cosine=1/(2×0.707)≈0.707
        """
        results = [
            SearchResult(chunk_id="aligned", score=0.1, metadata={}),
            SearchResult(chunk_id="diagonal", score=0.9, metadata={}),
        ]
        query_emb = np.array([2.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        self.fake_metadata_store._data = {
            "aligned": {"embedding": [1.0, 0.0, 0.0]},
            "diagonal": {"embedding": [0.5, 0.5, 0.0]},
        }
        self.engine._session_oom_detected = True

        reranked = self.engine.rerank_by_query(
            "q", results, k=2, search_mode="semantic"
        )

        assert reranked[0].chunk_id == "aligned"
        assert reranked[0].score == pytest.approx(
            1.0, abs=0.002
        )  # kills Mul_Add (0.667), Div_Mul (4.0)
        assert reranked[1].chunk_id == "diagonal"
        assert reranked[1].score == pytest.approx(
            0.707, abs=0.003
        )  # kills Mul_Pow (0.612), Mul_FloorDiv (0.5)

    @patch("search.neural_reranker.NeuralReranker")
    def test_shutdown_cleans_up_neural_reranker(self, mock_neural_reranker_class):
        """Test shutdown method cleans up neural reranker."""
        mock_reranker = MagicMock()
        self.engine.neural_reranker = mock_reranker

        self.engine.shutdown()

        mock_reranker.cleanup.assert_called_once()
        assert self.engine.neural_reranker is None

    def test_shutdown_without_neural_reranker(self):
        """Test shutdown without neural reranker doesn't error."""
        self.engine.neural_reranker = None
        self.engine.shutdown()  # Should not raise

    def test_rerank_with_precomputed_embedding(self):
        """Test reranking with pre-computed query embedding."""
        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
        ]

        query_emb = np.array([1.0, 0.0, 0.0])
        chunk_emb = np.array([1.0, 0.0, 0.0])

        self.fake_metadata_store._data["chunk1"] = {"embedding": chunk_emb.tolist()}

        # Bypass neural path (same OOM-flag pattern) to isolate the pure island.
        self.engine._session_oom_detected = True

        # Pass pre-computed embedding — embedder.embed_query must NOT be called
        reranked = self.engine.rerank_by_query(
            "test query", results, k=1, search_mode="hybrid", query_embedding=query_emb
        )

        self.mock_embedder.embed_query.assert_not_called()
        assert len(reranked) == 1

    def test_rerank_handles_missing_embeddings(self):
        """Test reranking gracefully handles missing chunk embeddings."""
        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.7, metadata={}),
        ]

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        # chunk1 has an embedding; chunk2 is absent → get() returns None → keeps score
        self.fake_metadata_store._data = {"chunk1": {"embedding": [0.8, 0.6, 0.0]}}

        # Bypass neural path to keep test fast and focused on the missing-embedding branch.
        self.engine._session_oom_detected = True

        # Should not raise; chunk2 keeps its original score 0.7
        reranked = self.engine.rerank_by_query(
            "test query", results, k=2, search_mode="semantic"
        )

        assert len(reranked) == 2

    @patch("search.reranking_engine.torch")
    @patch("search.neural_reranker.NeuralReranker")
    def test_neural_reranker_reload_after_disable_reenable(
        self, mock_neural_reranker_class, mock_torch
    ):
        """Test neural reranker properly reloads after disable/re-enable cycle.

        Regression test for Issue 1: Reranker doesn't reload after disable/re-enable.
        The cached _neural_reranking_enabled flag prevented config re-evaluation.
        """
        # GPU with sufficient VRAM
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            5 * 1024**3,  # 5 GB free
            8 * 1024**3,  # 8 GB total
        )

        mock_reranker_instance = MagicMock()
        mock_neural_reranker_class.return_value = mock_reranker_instance

        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.7, metadata={}),
        ]

        # Phase 1: Enable neural reranking
        enabled_config = SearchConfig(
            reranker=RerankerConfig(
                enabled=True,
                model_name="BAAI/bge-reranker-v2-m3",
                batch_size=16,
                top_k_candidates=50,
                min_vram_gb=4.0,
            )
        )
        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = enabled_config

            mock_reranker_instance.rerank.return_value = results
            self.engine.rerank_by_query("test query", results, k=2)

            assert self.engine.neural_reranker is not None
            assert mock_neural_reranker_class.call_count == 1

        # Phase 2: Disable neural reranking
        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = SearchConfig(
                reranker=RerankerConfig(enabled=False)
            )

            self.engine.rerank_by_query("test query", results, k=2)

            mock_reranker_instance.cleanup.assert_called_once()
            assert self.engine.neural_reranker is None

        # Phase 3: Re-enable (THIS WAS BROKEN BEFORE FIX)
        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = enabled_config

            mock_reranker_instance.rerank.return_value = results
            self.engine.rerank_by_query("test query", results, k=2)

            # Reranker must be re-initialised (not remain None)
            assert self.engine.neural_reranker is not None
            assert mock_neural_reranker_class.call_count == 2  # init + re-init
            assert mock_reranker_instance.rerank.call_count == 2  # phase 1 + 3

    @patch("search.reranking_engine.torch")
    @patch("search.neural_reranker.NeuralReranker")
    def test_neural_reranker_swaps_on_model_name_change(
        self, mock_neural_reranker_class, mock_torch
    ):
        """Test neural reranker reloads when configure_reranking() changes model_name.

        Regression test: RerankingEngine._ensure_reranker() previously only checked
        `self.neural_reranker is None` before creating an instance — switching
        model_name via configure_reranking() while a reranker was already loaded was
        silently a no-op (the MCP tool's "changes take effect on next search" message
        was false in that state). Fixed by comparing self.neural_reranker.model_name
        against the newly-configured model_name and reloading (cleanup + recreate) on
        mismatch.
        """
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            5 * 1024**3,  # 5 GB free
            8 * 1024**3,  # 8 GB total
        )

        model_a_instance = MagicMock()
        model_a_instance.model_name = "model-a"
        model_b_instance = MagicMock()
        model_b_instance.model_name = "model-b"
        mock_neural_reranker_class.side_effect = [model_a_instance, model_b_instance]

        results = [SearchResult(chunk_id="chunk1", score=0.5, metadata={})]

        # Phase 1: load model A
        config_a = SearchConfig(
            reranker=RerankerConfig(
                enabled=True,
                model_name="model-a",
                batch_size=16,
                top_k_candidates=50,
                min_vram_gb=4.0,
            )
        )
        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = config_a
            model_a_instance.rerank.return_value = results
            self.engine.rerank_by_query("test query", results, k=1)

            assert self.engine.neural_reranker is model_a_instance
            assert mock_neural_reranker_class.call_count == 1

        # Phase 2: configure_reranking() switches to model B while A is still loaded
        config_b = SearchConfig(
            reranker=RerankerConfig(
                enabled=True,
                model_name="model-b",
                batch_size=16,
                top_k_candidates=50,
                min_vram_gb=4.0,
            )
        )
        with patch("search.reranking_engine.get_search_config") as mock_config:
            mock_config.return_value = config_b
            model_b_instance.rerank.return_value = results
            self.engine.rerank_by_query("test query", results, k=1)

            # Old instance must be released before the new one takes over
            model_a_instance.cleanup.assert_called_once()
            assert self.engine.neural_reranker is model_b_instance
            assert self.engine.neural_reranker.model_name == "model-b"
            assert mock_neural_reranker_class.call_count == 2
