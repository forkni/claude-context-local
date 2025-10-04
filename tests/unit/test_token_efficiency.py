"""Unit tests for token efficiency evaluation."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from evaluation.base_evaluator import (EvaluationInstance, RetrievalResult,
                                       SearchMetrics)
from evaluation.token_efficiency_evaluator import (TokenCounter,
                                                   TokenEfficiencyEvaluator,
                                                   TokenEfficiencyMetrics,
                                                   TokenEfficiencyResult,
                                                   VanillaReadSimulator)


class TestTokenCounter:
    """Test token counting functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.token_counter = TokenCounter()

    def test_token_counter_initialization(self):
        """Test token counter initialization."""
        assert self.token_counter.encoding.name == "cl100k_base"

    def test_count_tokens_simple_text(self):
        """Test token counting for simple text."""
        text = "Hello world, this is a test."
        token_count = self.token_counter.count_tokens(text)

        # Should be approximately 8-10 tokens for this text
        assert 6 <= token_count <= 12
        assert isinstance(token_count, int)

    def test_count_tokens_empty_text(self):
        """Test token counting for empty text."""
        assert self.token_counter.count_tokens("") == 0
        assert self.token_counter.count_tokens(None) == 0

    def test_count_tokens_code_snippet(self):
        """Test token counting for code."""
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        token_count = self.token_counter.count_tokens(code)

        # Code typically has more tokens due to syntax
        assert token_count > 10
        assert isinstance(token_count, int)

    def test_count_tokens_batch(self):
        """Test batch token counting."""
        texts = [
            "Hello world",
            "def function(): pass",
            "",
            "A longer text with multiple words and punctuation.",
        ]

        token_counts = self.token_counter.count_tokens_batch(texts)

        assert len(token_counts) == 4
        assert all(isinstance(count, int) for count in token_counts)
        assert token_counts[2] == 0  # Empty text
        assert token_counts[3] > token_counts[0]  # Longer text has more tokens

    @patch("evaluation.token_efficiency_evaluator.tiktoken.get_encoding")
    def test_token_counter_error_handling(self, mock_get_encoding):
        """Test token counter error handling."""
        # Mock encoding that raises an error
        mock_encoding = Mock()
        mock_encoding.encode.side_effect = Exception("Encoding error")
        mock_get_encoding.return_value = mock_encoding

        counter = TokenCounter()

        # Should fall back to word-based estimation
        token_count = counter.count_tokens("Hello world test")
        assert token_count > 0  # Should still return a count


class TestVanillaReadSimulator:
    """Test vanilla file reading simulation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        self.simulator = VanillaReadSimulator(str(self.project_path))

    def test_simulator_initialization(self):
        """Test simulator initialization."""
        assert self.simulator.project_path == self.project_path
        assert isinstance(self.simulator.token_counter, TokenCounter)

    def test_simulate_find_files_basic(self):
        """Test basic file finding simulation."""
        ground_truth = ["test.py", "utils/helper.py"]
        query = "test function"

        found_files = self.simulator.simulate_find_files(query, ground_truth)

        # Should at least include ground truth files
        assert all(gt_file in found_files for gt_file in ground_truth)
        assert len(found_files) >= len(ground_truth)

    def test_simulate_find_files_expansion(self):
        """Test that simulation finds additional related files."""
        # Create some test files
        test_dir = self.project_path / "auth"
        test_dir.mkdir(exist_ok=True)

        (test_dir / "login.py").write_text("# Login functionality")
        (test_dir / "auth.py").write_text("# Auth functionality")
        (test_dir / "utils.py").write_text("# Utils")

        ground_truth = ["auth/login.py"]
        query = "authentication"

        found_files = self.simulator.simulate_find_files(query, ground_truth)

        # Should find additional files in the same directory
        assert len(found_files) > 1
        assert "auth/login.py" in found_files

    def test_simulate_read_files_existing(self):
        """Test reading existing files."""
        # Create test files
        test_file = self.project_path / "test.py"
        test_content = "def test_function():\n    pass"
        test_file.write_text(test_content)

        content, tokens, read_time = self.simulator.simulate_read_files(["test.py"])

        assert "# File: test.py" in content
        assert test_content in content
        assert tokens > 0
        assert read_time >= 0

    def test_simulate_read_files_missing(self):
        """Test reading missing files."""
        content, tokens, read_time = self.simulator.simulate_read_files(["missing.py"])

        assert "# File not found: missing.py" in content
        assert tokens > 0  # Should still count placeholder tokens
        assert read_time >= 0

    def test_simulate_read_files_multiple(self):
        """Test reading multiple files."""
        # Create test files
        (self.project_path / "file1.py").write_text("# File 1 content")
        (self.project_path / "file2.py").write_text("# File 2 content")

        files = ["file1.py", "file2.py", "missing.py"]
        content, tokens, read_time = self.simulator.simulate_read_files(files)

        assert "# File: file1.py" in content
        assert "# File: file2.py" in content
        assert "# File not found: missing.py" in content
        assert tokens > 0
        assert read_time >= 0

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestTokenEfficiencyMetrics:
    """Test token efficiency metrics dataclass."""

    def test_token_efficiency_metrics_creation(self):
        """Test creating TokenEfficiencyMetrics."""
        metrics = TokenEfficiencyMetrics(
            search_tokens=100,
            vanilla_read_tokens=500,
            token_savings=400,
            efficiency_ratio=0.2,
            percentage_savings=80.0,
            search_time=0.5,
            read_time=2.0,
            time_savings=1.5,
            files_avoided=3,
        )

        assert metrics.search_tokens == 100
        assert metrics.vanilla_read_tokens == 500
        assert metrics.token_savings == 400
        assert metrics.efficiency_ratio == 0.2
        assert metrics.percentage_savings == 80.0
        assert metrics.search_time == 0.5
        assert metrics.read_time == 2.0
        assert metrics.time_savings == 1.5
        assert metrics.files_avoided == 3


class TestTokenEfficiencyResult:
    """Test token efficiency result dataclass."""

    def test_token_efficiency_result_creation(self):
        """Test creating TokenEfficiencyResult."""
        search_metrics = SearchMetrics(
            query_time=0.5,
            total_results=5,
            precision=0.8,
            recall=0.6,
            f1_score=0.69,
            mrr=0.75,
            ndcg=0.82,
            token_usage=100,
            tool_calls=1,
        )

        efficiency_metrics = TokenEfficiencyMetrics(
            search_tokens=100,
            vanilla_read_tokens=500,
            token_savings=400,
            efficiency_ratio=0.2,
            percentage_savings=80.0,
            search_time=0.5,
            read_time=2.0,
            time_savings=1.5,
            files_avoided=3,
        )

        result = TokenEfficiencyResult(
            scenario_id="test_001",
            query="test query",
            search_metrics=search_metrics,
            efficiency_metrics=efficiency_metrics,
            search_results=[],
            simulated_files=["file1.py", "file2.py"],
            metadata={"test": True},
        )

        assert result.scenario_id == "test_001"
        assert result.query == "test query"
        assert result.search_metrics == search_metrics
        assert result.efficiency_metrics == efficiency_metrics
        assert result.simulated_files == ["file1.py", "file2.py"]
        assert result.metadata == {"test": True}


class MockSemanticEvaluator:
    """Mock semantic evaluator for testing."""

    def __init__(self, *args, **kwargs):
        self.built = False
        self.search_results = []

    def build_index(self, project_path):
        self.built = True

    def search(self, query, k):
        return self.search_results[:k]


class TestTokenEfficiencyEvaluator:
    """Test token efficiency evaluator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()

        # Create some test files
        (self.project_dir / "main.py").write_text("def main(): pass")
        (self.project_dir / "utils.py").write_text("def helper(): pass")

        self.evaluator = TokenEfficiencyEvaluator(
            output_dir=self.temp_dir, k=5, use_gpu=False
        )

    def test_evaluator_initialization(self):
        """Test evaluator initialization."""
        assert self.evaluator.k == 5
        assert not self.evaluator.use_gpu
        assert isinstance(self.evaluator.token_counter, TokenCounter)
        assert self.evaluator.searcher is None

    @patch("evaluation.semantic_evaluator.SemanticSearchEvaluator")
    def test_build_index(self, mock_semantic_evaluator_class):
        """Test index building."""
        mock_evaluator = MockSemanticEvaluator()
        mock_semantic_evaluator_class.return_value = mock_evaluator

        self.evaluator.build_index(str(self.project_dir))

        assert self.evaluator.current_project_path == str(self.project_dir)
        assert mock_evaluator.built

    @patch("evaluation.semantic_evaluator.SemanticSearchEvaluator")
    def test_search(self, mock_semantic_evaluator_class):
        """Test search functionality."""
        mock_evaluator = MockSemanticEvaluator()
        mock_evaluator.search_results = [
            RetrievalResult(
                file_path="test.py",
                chunk_id="chunk1",
                score=0.9,
                content="def test(): pass",
                metadata={},
            )
        ]
        mock_semantic_evaluator_class.return_value = mock_evaluator

        self.evaluator.build_index(str(self.project_dir))
        results = self.evaluator.search("test query", 5)

        assert len(results) == 1
        assert results[0].file_path == "test.py"

    def test_search_without_index(self):
        """Test search without building index first."""
        with pytest.raises(ValueError, match="Index not built"):
            self.evaluator.search("test query", 5)

    @patch("evaluation.semantic_evaluator.SemanticSearchEvaluator")
    def test_evaluate_token_efficiency(self, mock_semantic_evaluator_class):
        """Test token efficiency evaluation for single query."""
        # Set up mock evaluator
        mock_evaluator = MockSemanticEvaluator()
        mock_evaluator.search_results = [
            RetrievalResult(
                file_path="main.py",
                chunk_id="chunk1",
                score=0.9,
                content="def main(): pass",
                metadata={},
            )
        ]
        mock_semantic_evaluator_class.return_value = mock_evaluator

        # Build index
        self.evaluator.build_index(str(self.project_dir))

        # Create test instance
        instance = EvaluationInstance(
            instance_id="test_001",
            query="main function",
            ground_truth_files=["main.py"],
        )

        # Evaluate
        result = self.evaluator.evaluate_token_efficiency(
            instance, str(self.project_dir)
        )

        assert isinstance(result, TokenEfficiencyResult)
        assert result.scenario_id == "test_001"
        assert result.query == "main function"
        assert result.efficiency_metrics.search_tokens > 0
        assert result.efficiency_metrics.vanilla_read_tokens > 0

    def test_calculate_token_efficiency_aggregates(self):
        """Test aggregate calculations."""
        # Create mock results
        results = [
            TokenEfficiencyResult(
                scenario_id="test_1",
                query="query 1",
                search_metrics=SearchMetrics(
                    0.5, 2, 0.8, 0.6, 0.69, 0.75, 0.82, 100, 1
                ),
                efficiency_metrics=TokenEfficiencyMetrics(
                    100, 500, 400, 0.2, 80.0, 0.5, 2.0, 1.5, 3
                ),
                search_results=[],
                simulated_files=[],
                metadata={},
            ),
            TokenEfficiencyResult(
                scenario_id="test_2",
                query="query 2",
                search_metrics=SearchMetrics(
                    0.3, 3, 0.9, 0.7, 0.79, 0.85, 0.88, 150, 1
                ),
                efficiency_metrics=TokenEfficiencyMetrics(
                    150, 600, 450, 0.25, 75.0, 0.3, 1.8, 1.5, 2
                ),
                search_results=[],
                simulated_files=[],
                metadata={},
            ),
        ]

        aggregates = self.evaluator._calculate_token_efficiency_aggregates(results)

        assert aggregates["count"] == 2
        assert "token_efficiency" in aggregates
        assert "time_efficiency" in aggregates
        assert "file_efficiency" in aggregates
        assert "search_quality" in aggregates

        # Check specific calculations
        token_eff = aggregates["token_efficiency"]
        assert token_eff["mean_percentage_savings"] == 77.5  # (80 + 75) / 2
        assert token_eff["total_token_savings"] == 850  # 400 + 450

    def test_calculate_token_efficiency_aggregates_empty(self):
        """Test aggregate calculations with empty results."""
        aggregates = self.evaluator._calculate_token_efficiency_aggregates([])
        assert aggregates == {}

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestTokenEfficiencyIntegration:
    """Integration tests for token efficiency components."""

    def test_end_to_end_token_counting(self):
        """Test end-to-end token counting workflow."""
        counter = TokenCounter()

        # Test various text types
        texts = [
            "Simple text",
            "def function():\n    return True",
            "# This is a comment\nclass MyClass:\n    pass",
            "",
        ]

        for text in texts:
            token_count = counter.count_tokens(text)
            assert isinstance(token_count, int)
            assert token_count >= 0

            if text:
                assert token_count > 0
            else:
                assert token_count == 0

    def test_vanilla_simulator_realistic_scenario(self):
        """Test vanilla simulator with realistic file structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create realistic project structure
            (project_path / "main.py").write_text("""
def main():
    print("Hello World")
    return 0

if __name__ == "__main__":
    main()
""")

            # Create utils directory first
            (project_path / "utils").mkdir(exist_ok=True)
            (project_path / "utils" / "helpers.py").write_text("""
def helper_function():
    return "helper"

def another_helper():
    return True
""")

            simulator = VanillaReadSimulator(str(project_path))

            # Test file finding and reading
            ground_truth = ["main.py"]
            found_files = simulator.simulate_find_files("main function", ground_truth)
            content, tokens, read_time = simulator.simulate_read_files(found_files)

            assert tokens > 0
            assert read_time >= 0
            assert "main.py" in content
            assert len(found_files) >= 1
