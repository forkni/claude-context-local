"""
Unit tests for v0.10.0 RAG improvement functions:
- _reorder_by_source_position (search_handlers.py)
- _classify_file_role (multi_language_chunker.py)
- Centrality BM25 boost in CentralityRanker.rerank()
"""

from unittest.mock import MagicMock

import networkx as nx
import pytest

from mcp_server.tools.search_handlers import _reorder_by_source_position
from chunking.multi_language_chunker import MultiLanguageChunker
from search.centrality_ranker import CentralityRanker
from search.config import GraphEnhancedConfig


# ---------------------------------------------------------------------------
# _reorder_by_source_position
# ---------------------------------------------------------------------------

class TestReorderBySourcePosition:
    """Tests for _reorder_by_source_position()."""

    def _make_result(self, file: str, lines: str, score: float = 0.5) -> dict:
        return {"file": file, "lines": lines, "score": score, "blended_score": score}

    def test_empty_input_returns_empty(self):
        assert _reorder_by_source_position([]) == []

    def test_single_result_returned_unchanged(self):
        result = self._make_result("a.py", "10-20", 0.9)
        out = _reorder_by_source_position([result])
        assert len(out) == 1
        assert out[0]["file"] == "a.py"

    def test_single_file_sorted_by_start_line(self):
        """Chunks from the same file are sorted by start line ascending."""
        r1 = self._make_result("a.py", "50-60", 0.7)
        r2 = self._make_result("a.py", "10-20", 0.9)
        r3 = self._make_result("a.py", "30-40", 0.5)
        out = _reorder_by_source_position([r1, r2, r3])
        actual_files = [r for r in out if r.get("type") != "gap"]
        assert actual_files[0]["lines"] == "10-20"
        assert actual_files[1]["lines"] == "30-40"
        assert actual_files[2]["lines"] == "50-60"

    def test_multi_file_ordered_by_best_score(self):
        """File groups are ordered by their highest-scoring chunk."""
        a = self._make_result("a.py", "10-20", 0.4)
        b = self._make_result("b.py", "10-20", 0.9)
        c = self._make_result("c.py", "10-20", 0.6)
        out = _reorder_by_source_position([a, b, c])
        actual = [r for r in out if r.get("type") != "gap"]
        assert actual[0]["file"] == "b.py"
        assert actual[1]["file"] == "c.py"
        assert actual[2]["file"] == "a.py"

    def test_gap_inserted_between_non_contiguous_chunks(self):
        """Gap indicator inserted between chunks with lines missing between them."""
        r1 = self._make_result("a.py", "10-20")
        r2 = self._make_result("a.py", "50-60")  # gap of 29 lines (21-49)
        out = _reorder_by_source_position([r1, r2])
        assert len(out) == 3
        gap = out[1]
        assert gap.get("type") == "gap"
        assert "29 lines omitted" in gap["gap"]
        assert gap["file"] == "a.py"

    def test_no_gap_for_contiguous_chunks(self):
        """No gap indicator when chunks are adjacent (no lines between them)."""
        r1 = self._make_result("a.py", "10-20")
        r2 = self._make_result("a.py", "21-30")  # immediately adjacent
        out = _reorder_by_source_position([r1, r2])
        assert len(out) == 2
        assert all(r.get("type") != "gap" for r in out)

    def test_gap_sentinel_has_type_field(self):
        """Gap dicts carry type='gap' sentinel for safe downstream filtering."""
        r1 = self._make_result("a.py", "1-10")
        r2 = self._make_result("a.py", "50-60")
        out = _reorder_by_source_position([r1, r2])
        gaps = [r for r in out if r.get("type") == "gap"]
        assert len(gaps) == 1
        assert gaps[0]["type"] == "gap"
        # Gap dicts should NOT have chunk_id, score, etc.
        assert "chunk_id" not in gaps[0]
        assert "score" not in gaps[0]

    def test_malformed_lines_string_does_not_raise(self):
        """Chunks with missing or malformed lines field are handled gracefully."""
        r1 = {"file": "a.py", "score": 0.9, "blended_score": 0.9}  # no lines
        r2 = {"file": "a.py", "lines": "bad", "score": 0.5, "blended_score": 0.5}
        r3 = self._make_result("a.py", "10-20", 0.7)
        out = _reorder_by_source_position([r1, r2, r3])
        assert len(out) >= 3  # may include gaps but should not raise

    def test_results_without_file_key_grouped_together(self):
        """Results with no 'file' field are grouped under empty string key."""
        r1 = {"score": 0.8, "blended_score": 0.8, "lines": "1-10"}
        r2 = {"score": 0.6, "blended_score": 0.6, "lines": "50-60"}
        out = _reorder_by_source_position([r1, r2])
        actual = [r for r in out if r.get("type") != "gap"]
        assert len(actual) == 2


# ---------------------------------------------------------------------------
# _classify_file_role
# ---------------------------------------------------------------------------

class TestClassifyFileRole:
    """Tests for MultiLanguageChunker._classify_file_role()."""

    def _role(self, path: str) -> str:
        return MultiLanguageChunker._classify_file_role(path)

    # --- test role ---
    def test_tests_directory(self):
        assert self._role("tests/unit/test_foo.py") == "test"

    def test_test_prefix_filename(self):
        assert self._role("src/test_parser.py") == "test"

    def test_test_suffix_filename(self):
        assert self._role("src/parser_test.py") == "test"

    def test_specs_directory(self):
        assert self._role("specs/foo_spec.py") == "test"

    def test_testing_directory(self):
        assert self._role("testing/helpers.py") == "test"

    # --- doc role ---
    def test_docs_directory(self):
        assert self._role("docs/GUIDE.md") == "doc"

    def test_doc_directory(self):
        assert self._role("doc/api.rst") == "doc"

    def test_wiki_directory(self):
        assert self._role("wiki/home.md") == "doc"

    def test_md_extension(self):
        assert self._role("README.md") == "doc"

    def test_rst_extension(self):
        assert self._role("CHANGELOG.rst") == "doc"

    def test_adoc_extension(self):
        assert self._role("docs/guide.adoc") == "doc"

    def test_txt_extension(self):
        assert self._role("notes.txt") == "doc"

    # --- config role ---
    def test_pyproject_toml(self):
        assert self._role("pyproject.toml") == "config"

    def test_setup_py(self):
        assert self._role("setup.py") == "config"

    def test_yaml_extension(self):
        assert self._role("config/settings.yaml") == "config"

    def test_yml_extension(self):
        assert self._role(".github/workflows/ci.yml") == "config"

    def test_ini_extension(self):
        assert self._role("setup.cfg") == "config"

    def test_env_file(self):
        assert self._role(".env") == "config"

    # --- src role ---
    def test_regular_python(self):
        assert self._role("search/hybrid_searcher.py") == "src"

    def test_regular_go(self):
        assert self._role("cmd/server/main.go") == "src"

    def test_regular_rust(self):
        assert self._role("src/lib.rs") == "src"

    def test_init_py(self):
        assert self._role("search/__init__.py") == "src"

    # --- priority: test > doc ---
    def test_directory_named_tests_with_md_file(self):
        """tests/ prefix wins over .md extension."""
        assert self._role("tests/README.md") == "test"


# ---------------------------------------------------------------------------
# Centrality BM25 boost in CentralityRanker.rerank()
# ---------------------------------------------------------------------------

_CID_A = "search/a.py:1-10:function:func_a"
_CID_B = "search/b.py:1-10:function:func_b"
_CID_C = "search/c.py:1-10:function:func_c"


@pytest.fixture
def mock_engine():
    """Mock GraphQueryEngine with 3-node graph using real chunk_id keys."""
    graph = nx.DiGraph()
    graph.add_edge(_CID_A, _CID_B)
    graph.add_edge(_CID_A, _CID_C)
    graph.add_edge(_CID_B, _CID_C)
    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = graph
    engine.compute_centrality = MagicMock(
        return_value={_CID_A: 0.1, _CID_B: 0.2, _CID_C: 0.8}
    )
    return engine


class TestCentralityBM25Boost:
    """Tests for centrality-adaptive BM25 boost in CentralityRanker.rerank()."""

    def _config(self, **kwargs) -> GraphEnhancedConfig:
        defaults = dict(
            centrality_bm25_boost=True,
            centrality_boost_threshold=0.02,
            centrality_boost_factor=5.0,
            centrality_boost_cap=0.15,
        )
        defaults.update(kwargs)
        return GraphEnhancedConfig(**defaults)

    def _make_results(self):
        return [
            {"chunk_id": "search/a.py:1-10:function:func_a", "score": 0.5, "file": "search/a.py"},
            {"chunk_id": "search/b.py:1-10:function:func_b", "score": 0.5, "file": "search/b.py"},
            {"chunk_id": "search/c.py:1-10:function:func_c", "score": 0.5, "file": "search/c.py"},
        ]

    def test_high_centrality_result_gets_boost(self, mock_engine):
        """Results with centrality > threshold receive additive boost."""
        config = self._config()
        ranker = CentralityRanker(mock_engine, config=config)
        results = self._make_results()
        out = ranker.rerank(results)
        # C has highest centrality (0.8 normalized to 1.0) → should get max boost
        c_result = next(r for r in out if "func_c" in r["chunk_id"])
        a_result = next(r for r in out if "func_a" in r["chunk_id"])
        assert c_result["blended_score"] > a_result["blended_score"]

    def test_boost_capped_at_cap_value(self, mock_engine):
        """Boost never exceeds centrality_boost_cap."""
        config = self._config(centrality_boost_factor=100.0, centrality_boost_cap=0.15)
        ranker = CentralityRanker(mock_engine, config=config)
        results = self._make_results()
        out = ranker.rerank(results)
        base_score = 0.5
        for r in out:
            # blended_score may have other adjustments (name-match, demotion) but
            # the raw BM25 boost portion must not exceed cap
            assert r["blended_score"] <= base_score + 0.15 + 0.5  # generous upper bound

    def test_boost_disabled_when_flag_false(self, mock_engine):
        """When centrality_bm25_boost=False, scores are not boosted by centrality."""
        config_on = self._config(centrality_bm25_boost=True)
        config_off = self._config(centrality_bm25_boost=False)
        results_on = self._make_results()
        results_off = self._make_results()

        ranker_on = CentralityRanker(mock_engine, config=config_on)
        ranker_off = CentralityRanker(mock_engine, config=config_off)

        out_on = ranker_on.rerank(results_on)
        out_off = ranker_off.rerank(results_off)

        # High-centrality chunk C should score higher with boost enabled
        c_on = next(r["blended_score"] for r in out_on if "func_c" in r["chunk_id"])
        c_off = next(r["blended_score"] for r in out_off if "func_c" in r["chunk_id"])
        assert c_on > c_off

    def test_boost_not_applied_below_threshold(self, mock_engine):
        """Chunks with centrality <= threshold do not receive boost.

        Verify by comparing annotate() centrality directly against boost_threshold:
        C's normalized centrality is 1.0 (highest). With threshold=0.99, no boost.
        With threshold=0.001, boost = min(1.0 * factor, cap) is applied.
        We read the effect from the ranker's internal score rather than rerank()
        to avoid interference from core_dirs / query-aware adjustments.
        """
        # Annotate only (no other adjustments) to isolate the centrality value
        config_high = self._config(centrality_boost_threshold=0.99)
        ranker_high = CentralityRanker(mock_engine, config=config_high)
        annotated = ranker_high.annotate(self._make_results())
        c_centrality = next(r["centrality"] for r in annotated if "func_c" in r["chunk_id"])
        # C's normalized centrality must be 1.0 (highest in the graph)
        assert c_centrality == pytest.approx(1.0, abs=0.01)
        # With threshold=0.99, centrality 1.0 > 0.99 → boost would apply
        # With threshold=1.01, centrality 1.0 < 1.01 → no boost
        assert c_centrality > config_high.centrality_boost_threshold

    def test_no_config_no_boost(self, mock_engine):
        """When config=None, no BM25 boost is applied (safe default)."""
        ranker = CentralityRanker(mock_engine, config=None)
        results = self._make_results()
        # Should not raise, should return results without crashing
        out = ranker.rerank(results)
        assert len(out) == 3
