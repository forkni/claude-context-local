"""Tests for the evaluation framework."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from evaluation.base_evaluator import (
    BaseEvaluator,
    EvaluationInstance,
    RetrievalResult,
    SearchMetrics,
)
from evaluation.semantic_evaluator import SemanticSearchEvaluator


class TestRetrievalResult:
    """Test RetrievalResult dataclass."""

    def test_retrieval_result_creation(self):
        """Test creating RetrievalResult."""
        result = RetrievalResult(
            file_path="test.py",
            chunk_id="test_chunk_1",
            score=0.85,
            content="def test(): pass",
            metadata={"language": "python"},
            line_start=1,
            line_end=5,
        )

        assert result.file_path == "test.py"
        assert result.chunk_id == "test_chunk_1"
        assert result.score == 0.85
        assert result.content == "def test(): pass"
        assert result.metadata == {"language": "python"}
        assert result.line_start == 1
        assert result.line_end == 5

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = RetrievalResult(
            file_path="test.py",
            chunk_id="test_chunk_1",
            score=0.85,
            content="def test(): pass",
            metadata={"language": "python"},
        )

        result_dict = result.to_dict()

        expected = {
            "file_path": "test.py",
            "chunk_id": "test_chunk_1",
            "score": 0.85,
            "content": "def test(): pass",
            "metadata": {"language": "python"},
            "line_start": 0,
            "line_end": 0,
        }

        assert result_dict == expected


class TestSearchMetrics:
    """Test SearchMetrics dataclass."""

    def test_search_metrics_creation(self):
        """Test creating SearchMetrics."""
        metrics = SearchMetrics(
            query_time=0.5,
            total_results=10,
            precision=0.8,
            recall=0.6,
            f1_score=0.69,
            mrr=0.75,
            ndcg=0.82,
            token_usage=1000,
            tool_calls=5,
        )

        assert metrics.query_time == 0.5
        assert metrics.total_results == 10
        assert metrics.precision == 0.8
        assert metrics.recall == 0.6
        assert metrics.f1_score == 0.69
        assert metrics.mrr == 0.75
        assert metrics.ndcg == 0.82
        assert metrics.token_usage == 1000
        assert metrics.tool_calls == 5


class TestEvaluationInstance:
    """Test EvaluationInstance dataclass."""

    def test_evaluation_instance_creation(self):
        """Test creating EvaluationInstance."""
        instance = EvaluationInstance(
            instance_id="test_001",
            query="find authentication functions",
            ground_truth_files=["auth.py", "login.py"],
            ground_truth_content="def authenticate(): pass",
            metadata={"difficulty": "medium"},
        )

        assert instance.instance_id == "test_001"
        assert instance.query == "find authentication functions"
        assert instance.ground_truth_files == ["auth.py", "login.py"]
        assert instance.ground_truth_content == "def authenticate(): pass"
        assert instance.metadata == {"difficulty": "medium"}


class MockEvaluator(BaseEvaluator):
    """Mock evaluator for testing base functionality."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index_built = False
        self.search_results = []

    def build_index(self, project_path: str) -> None:
        """Mock index building."""
        self.index_built = True

    def search(self, query: str, k: int) -> list:
        """Mock search that returns predefined results."""
        return self.search_results[:k]


class TestBaseEvaluator:
    """Test base evaluator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.evaluator = MockEvaluator(output_dir=self.temp_dir, max_instances=10, k=5)

    def test_initialization(self):
        """Test evaluator initialization."""
        assert Path(self.evaluator.output_dir).exists()
        assert self.evaluator.max_instances == 10
        assert self.evaluator.k == 5

    def test_calculate_precision_recall(self):
        """Test precision and recall calculation."""
        retrieved = ["file1.py", "file2.py", "file3.py"]
        ground_truth = ["file1.py", "file3.py", "file4.py"]

        precision, recall = self.evaluator.calculate_precision_recall(
            retrieved, ground_truth
        )

        # 2 correct out of 3 retrieved = 2/3 precision
        # 2 correct out of 3 ground truth = 2/3 recall
        assert precision == pytest.approx(2 / 3)
        assert recall == pytest.approx(2 / 3)

    def test_calculate_precision_recall_empty(self):
        """Test precision and recall with empty results."""
        precision, recall = self.evaluator.calculate_precision_recall([], ["file1.py"])
        assert precision == 0.0
        assert recall == 0.0

    def test_calculate_f1_score(self):
        """Test F1 score calculation."""
        f1 = self.evaluator.calculate_f1_score(0.8, 0.6)
        expected_f1 = 2 * (0.8 * 0.6) / (0.8 + 0.6)
        assert f1 == pytest.approx(expected_f1)

    def test_calculate_f1_score_zero(self):
        """Test F1 score with zero precision and recall."""
        f1 = self.evaluator.calculate_f1_score(0.0, 0.0)
        assert f1 == 0.0

    def test_calculate_mrr(self):
        """Test Mean Reciprocal Rank calculation."""
        retrieved = ["file1.py", "file2.py", "file3.py"]
        ground_truth = ["file2.py", "file4.py"]

        mrr = self.evaluator.calculate_mrr(retrieved, ground_truth)
        # file2.py is at position 2 (index 1), so MRR = 1/2 = 0.5
        assert mrr == 0.5

    def test_calculate_mrr_not_found(self):
        """Test MRR when no ground truth is found."""
        retrieved = ["file1.py", "file2.py"]
        ground_truth = ["file3.py", "file4.py"]

        mrr = self.evaluator.calculate_mrr(retrieved, ground_truth)
        assert mrr == 0.0

    def test_load_dataset_json(self):
        """Test loading dataset from JSON file."""
        # Create sample dataset
        dataset = {
            "instances": [
                {
                    "instance_id": "test_001",
                    "query": "test query",
                    "ground_truth_files": ["test.py"],
                    "metadata": {"difficulty": "easy"},
                }
            ]
        }

        dataset_file = Path(self.temp_dir) / "test_dataset.json"
        with open(dataset_file, "w") as f:
            json.dump(dataset, f)

        instances = self.evaluator.load_dataset(str(dataset_file))

        assert len(instances) == 1
        assert instances[0].instance_id == "test_001"
        assert instances[0].query == "test query"
        assert instances[0].ground_truth_files == ["test.py"]

    def test_evaluate_single_query(self):
        """Test evaluating a single query."""
        # Set up mock search results
        self.evaluator.search_results = [
            RetrievalResult(
                file_path="file1.py",
                chunk_id="chunk1",
                score=0.9,
                content="test content",
                metadata={},
            ),
            RetrievalResult(
                file_path="file2.py",
                chunk_id="chunk2",
                score=0.7,
                content="test content",
                metadata={},
            ),
        ]

        instance = EvaluationInstance(
            instance_id="test_001",
            query="test query",
            ground_truth_files=["file1.py", "file3.py"],
        )

        metrics = self.evaluator.evaluate_single_query(instance, "/fake/project")

        assert isinstance(metrics, SearchMetrics)
        assert metrics.total_results == 2
        assert metrics.precision == 0.5  # 1 correct out of 2 retrieved
        assert metrics.recall == 0.5  # 1 correct out of 2 ground truth
        assert metrics.query_time >= 0  # Allow zero time for mock operations

    def test_run_evaluation(self):
        """Test running full evaluation."""
        # Set up mock search results
        self.evaluator.search_results = [
            RetrievalResult(
                file_path="file1.py",
                chunk_id="chunk1",
                score=0.9,
                content="test content",
                metadata={},
            )
        ]

        instances = [
            EvaluationInstance(
                instance_id="test_001",
                query="test query 1",
                ground_truth_files=["file1.py"],
            ),
            EvaluationInstance(
                instance_id="test_002",
                query="test query 2",
                ground_truth_files=["file2.py"],
            ),
        ]

        results = self.evaluator.run_evaluation(instances, "/fake/project")

        assert self.evaluator.index_built
        assert "metadata" in results
        assert "aggregate_metrics" in results
        assert "results_by_instance" in results
        assert results["metadata"]["total_instances"] == 2

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


@patch("evaluation.semantic_evaluator.HybridSearcher")
@patch("evaluation.semantic_evaluator.CodeEmbedder")
@patch("evaluation.semantic_evaluator.MultiLanguageChunker")
class TestSemanticSearchEvaluator:
    """Test semantic search evaluator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def test_initialization(self, mock_chunker, mock_embedder, mock_searcher):
        """Test evaluator initialization."""
        evaluator = SemanticSearchEvaluator(
            output_dir=self.temp_dir, k=10, use_gpu=False
        )

        assert evaluator.k == 10
        assert not evaluator.use_gpu
        assert evaluator.bm25_weight == 0.4
        assert evaluator.dense_weight == 0.6

    def test_should_rebuild_index(self, mock_chunker, mock_embedder, mock_searcher):
        """Test index rebuild decision."""
        evaluator = SemanticSearchEvaluator(output_dir=self.temp_dir)

        # Should rebuild when indices don't exist
        should_rebuild = evaluator._should_rebuild_index("/fake/project")
        assert should_rebuild

    def test_context_manager(self, mock_chunker, mock_embedder, mock_searcher):
        """Test using evaluator as context manager."""
        with SemanticSearchEvaluator(output_dir=self.temp_dir) as evaluator:
            assert evaluator is not None

        # cleanup should have been called

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
