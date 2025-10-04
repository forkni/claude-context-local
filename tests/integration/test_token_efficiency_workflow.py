"""Integration tests for token efficiency evaluation workflow."""

import json
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

import pytest

from evaluation.base_evaluator import EvaluationInstance
from evaluation.token_efficiency_evaluator import TokenEfficiencyEvaluator


class TestTokenEfficiencyWorkflow:
    """Test complete token efficiency evaluation workflow."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test fixtures for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()
        self.output_dir = Path(self.temp_dir) / "output"
        self.output_dir.mkdir()

        # Create realistic test project structure
        self._create_test_project()

        self.evaluator = TokenEfficiencyEvaluator(
            output_dir=str(self.output_dir),
            k=5,
            use_gpu=False,
            max_instances=3,  # Limit for testing
        )

    def _create_test_project(self):
        """Create a realistic test project for evaluation."""
        # Main application file
        (self.project_dir / "main.py").write_text(
            """
#!/usr/bin/env python3
\"\"\"Main application entry point.\"\"\"

import logging
import sys
from pathlib import Path

def setup_logging():
    \"\"\"Configure application logging.\"\"\"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    \"\"\"Main application function.\"\"\"
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting application")

    try:
        # Application logic here
        result = process_data()
        logger.info(f"Processing completed: {result}")
        return 0
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1

def process_data():
    \"\"\"Process application data.\"\"\"
    return "success"

if __name__ == "__main__":
    sys.exit(main())
"""
        )

        # Authentication module
        auth_dir = self.project_dir / "auth"
        auth_dir.mkdir()
        (auth_dir / "__init__.py").write_text("")
        (auth_dir / "login.py").write_text(
            """
\"\"\"User authentication and login functionality.\"\"\"

import hashlib
import secrets
from typing import Optional, Dict, Any

class AuthenticationError(Exception):
    \"\"\"Raised when authentication fails.\"\"\"
    pass

class LoginManager:
    \"\"\"Manages user login and authentication.\"\"\"

    def __init__(self):
        self.sessions = {}
        self.users = {
            "admin": self._hash_password("admin123"),
            "user": self._hash_password("user123")
        }

    def _hash_password(self, password: str) -> str:
        \"\"\"Hash password with salt.\"\"\"
        salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

    def authenticate(self, username: str, password: str) -> bool:
        \"\"\"Authenticate user credentials.\"\"\"
        if username not in self.users:
            raise AuthenticationError(f"User {username} not found")

        # In real implementation, would verify password hash
        return username in self.users

    def login(self, username: str, password: str) -> Optional[str]:
        \"\"\"Login user and return session token.\"\"\"
        try:
            if self.authenticate(username, password):
                session_token = secrets.token_urlsafe(32)
                self.sessions[session_token] = {
                    'username': username,
                    'timestamp': 1234567890
                }
                return session_token
            return None
        except AuthenticationError:
            return None

    def logout(self, session_token: str) -> bool:
        \"\"\"Logout user by invalidating session.\"\"\"
        return self.sessions.pop(session_token, None) is not None
"""
        )

        # Database utilities
        db_dir = self.project_dir / "database"
        db_dir.mkdir()
        (db_dir / "__init__.py").write_text("")
        (db_dir / "connection.py").write_text(
            """
\"\"\"Database connection and configuration.\"\"\"

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

class DatabaseError(Exception):
    \"\"\"Database operation error.\"\"\"
    pass

class DatabaseConnection:
    \"\"\"Manages database connections and operations.\"\"\"

    def __init__(self, db_path: str = "app.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self._connection = None

    def initialize_database(self):
        \"\"\"Initialize database schema.\"\"\"
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        token TEXT PRIMARY KEY,
                        user_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                conn.commit()
                self.logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}")

    @contextmanager
    def get_connection(self):
        \"\"\"Get database connection context manager.\"\"\"
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Optional[Dict] = None) -> list:
        \"\"\"Execute database query and return results.\"\"\"
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params or {})
                return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Query execution error: {e}")
            raise DatabaseError(f"Query failed: {e}")
"""
        )

        # API handlers
        api_dir = self.project_dir / "api"
        api_dir.mkdir()
        (api_dir / "__init__.py").write_text("")
        (api_dir / "handlers.py").write_text(
            """
\"\"\"API endpoint handlers.\"\"\"

import json
import logging
from typing import Dict, Any, Optional
from http.server import BaseHTTPRequestHandler

class APIError(Exception):
    \"\"\"API operation error.\"\"\"
    pass

class APIHandler(BaseHTTPRequestHandler):
    \"\"\"HTTP API request handler.\"\"\"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.routes = {
            '/api/login': self.handle_login,
            '/api/logout': self.handle_logout,
            '/api/users': self.handle_users,
            '/api/health': self.handle_health
        }

    def handle_login(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Handle user login request.\"\"\"
        try:
            username = request_data.get('username')
            password = request_data.get('password')

            if not username or not password:
                raise APIError("Username and password required")

            # Mock authentication
            if username == "admin" and password == "admin123":
                return {
                    'status': 'success',
                    'token': 'mock_session_token_12345',
                    'user': {'username': username, 'role': 'admin'}
                }
            else:
                raise APIError("Invalid credentials")

        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_logout(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Handle user logout request.\"\"\"
        try:
            token = request_data.get('token')
            if not token:
                raise APIError("Session token required")

            # Mock logout
            return {'status': 'success', 'message': 'Logged out successfully'}

        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_users(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Handle user management requests.\"\"\"
        try:
            # Mock user data
            users = [
                {'id': 1, 'username': 'admin', 'email': 'admin@example.com'},
                {'id': 2, 'username': 'user', 'email': 'user@example.com'}
            ]
            return {'status': 'success', 'users': users}

        except Exception as e:
            self.logger.error(f"Users API error: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_health(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Handle health check request.\"\"\"
        return {
            'status': 'healthy',
            'timestamp': 1234567890,
            'version': '1.0.0'
        }
"""
        )

        # Utilities
        utils_dir = self.project_dir / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text("")
        (utils_dir / "helpers.py").write_text(
            """
\"\"\"Utility helper functions.\"\"\"

import logging
import json
import hashlib
from typing import Any, Dict, List, Optional
from pathlib import Path

def setup_logging(level: str = "INFO") -> logging.Logger:
    \"\"\"Setup application logging configuration.\"\"\"
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    \"\"\"Load configuration from JSON file.\"\"\"
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, 'r') as f:
            config = json.load(f)

        return config
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Configuration loading error: {e}")
        raise

def calculate_hash(data: str, algorithm: str = "sha256") -> str:
    \"\"\"Calculate hash of string data.\"\"\"
    if algorithm not in hashlib.algorithms_available:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data.encode('utf-8'))
    return hash_obj.hexdigest()

def validate_email(email: str) -> bool:
    \"\"\"Basic email validation.\"\"\"
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def paginate_results(items: List[Any], page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    \"\"\"Paginate list of items.\"\"\"
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    return {
        'items': items[start_idx:end_idx],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }

# TODO: Refactor this function - it's getting too complex
def process_file_batch(file_paths: List[str], processor_func) -> Dict[str, Any]:
    \"\"\"Process multiple files in batch.\"\"\"
    results = {}
    errors = {}

    for file_path in file_paths:
        try:
            result = processor_func(file_path)
            results[file_path] = result
        except Exception as e:
            errors[file_path] = str(e)
            logging.error(f"Error processing {file_path}: {e}")

    return {
        'results': results,
        'errors': errors,
        'success_count': len(results),
        'error_count': len(errors)
    }
"""
        )

        # Test files
        tests_dir = self.project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_auth.py").write_text(
            """
\"\"\"Tests for authentication module.\"\"\"

import pytest
from unittest.mock import Mock, patch

from auth.login import LoginManager, AuthenticationError

class TestLoginManager:
    \"\"\"Test user authentication functionality.\"\"\"

    def setup_method(self):
        \"\"\"Set up test fixtures.\"\"\"
        self.login_manager = LoginManager()

    def test_authentication_success(self):
        \"\"\"Test successful user authentication.\"\"\"
        result = self.login_manager.authenticate("admin", "admin123")
        assert result == True

    def test_authentication_invalid_user(self):
        \"\"\"Test authentication with invalid user.\"\"\"
        with pytest.raises(AuthenticationError):
            self.login_manager.authenticate("invalid", "password")

    def test_login_success(self):
        \"\"\"Test successful login.\"\"\"
        token = self.login_manager.login("admin", "admin123")
        assert token is not None
        assert len(token) > 0
        assert token in self.login_manager.sessions

    def test_login_failure(self):
        \"\"\"Test failed login.\"\"\"
        token = self.login_manager.login("invalid", "password")
        assert token is None

    def test_logout(self):
        \"\"\"Test user logout.\"\"\"
        token = self.login_manager.login("admin", "admin123")
        assert token is not None

        logout_result = self.login_manager.logout(token)
        assert logout_result == True
        assert token not in self.login_manager.sessions

@pytest.fixture
def mock_login_manager():
    \"\"\"Fixture providing mock login manager.\"\"\"
    manager = Mock(spec=LoginManager)
    manager.authenticate.return_value = True
    manager.login.return_value = "mock_token_123"
    manager.logout.return_value = True
    return manager

def test_authentication_integration(mock_login_manager):
    \"\"\"Integration test for authentication workflow.\"\"\"
    # Test complete authentication flow
    auth_result = mock_login_manager.authenticate("test_user", "password")
    assert auth_result == True

    token = mock_login_manager.login("test_user", "password")
    assert token == "mock_token_123"

    logout_result = mock_login_manager.logout(token)
    assert logout_result == True
"""
        )

    def _create_test_instances(self) -> List[EvaluationInstance]:
        """Create test evaluation instances."""
        return [
            EvaluationInstance(
                instance_id="auth_test",
                query="authentication login functions",
                ground_truth_files=["auth/login.py"],
                metadata={"category": "authentication"},
            ),
            EvaluationInstance(
                instance_id="db_test",
                query="database connection setup",
                ground_truth_files=["database/connection.py"],
                metadata={"category": "database"},
            ),
            EvaluationInstance(
                instance_id="api_test",
                query="API endpoint handlers HTTP",
                ground_truth_files=["api/handlers.py"],
                metadata={"category": "api"},
            ),
            EvaluationInstance(
                instance_id="config_test",
                query="configuration loading settings",
                ground_truth_files=["utils/helpers.py"],
                metadata={"category": "configuration"},
            ),
            EvaluationInstance(
                instance_id="error_test",
                query="error handling exception try catch",
                ground_truth_files=[
                    "main.py",
                    "database/connection.py",
                    "api/handlers.py",
                ],
                metadata={"category": "error_handling"},
            ),
        ]

    @patch("evaluation.semantic_evaluator.SemanticSearchEvaluator")
    def test_full_workflow_with_mock_search(self, mock_semantic_evaluator_class):
        """Test complete token efficiency evaluation workflow with mocked search."""
        from evaluation.base_evaluator import RetrievalResult

        # Create mock evaluator
        mock_evaluator = Mock()
        mock_evaluator.search.return_value = [
            RetrievalResult(
                file_path="auth/login.py",
                chunk_id="chunk1",
                score=0.9,
                content="def authenticate(username, password): ...",
                metadata={"language": "python"},
            ),
            RetrievalResult(
                file_path="database/connection.py",
                chunk_id="chunk2",
                score=0.8,
                content="class DatabaseConnection: ...",
                metadata={"language": "python"},
            ),
        ]
        mock_semantic_evaluator_class.return_value = mock_evaluator

        # Create test instances
        instances = self._create_test_instances()[:2]  # Limit for testing

        # Run evaluation
        results = self.evaluator.run_token_efficiency_evaluation(
            instances, str(self.project_dir)
        )

        # Verify results structure
        assert "metadata" in results
        assert "aggregate_metrics" in results
        assert "results_by_instance" in results

        metadata = results["metadata"]
        assert metadata["total_instances"] == 2
        assert metadata["successful_evaluations"] >= 0
        assert str(self.project_dir) in metadata["project_path"]

        # Verify output files were created
        assert (self.output_dir / "token_efficiency_results.json").exists()
        assert (self.output_dir / "token_efficiency_summary.json").exists()
        assert (self.output_dir / "token_efficiency_report.txt").exists()

    def test_token_efficiency_calculation_accuracy(self):
        """Test accuracy of token efficiency calculations."""
        from evaluation.token_efficiency_evaluator import (
            TokenCounter,
            VanillaReadSimulator,
        )

        # Test token counting accuracy
        counter = TokenCounter()

        # Test with known text
        simple_text = "Hello world"
        tokens = counter.count_tokens(simple_text)
        assert tokens > 0

        # Test with code
        code_text = """
def hello():
    print("Hello, World!")
    return True
"""
        code_tokens = counter.count_tokens(code_text)
        assert code_tokens > tokens  # Code should have more tokens

        # Test vanilla simulator
        simulator = VanillaReadSimulator(str(self.project_dir))

        # Test file simulation
        ground_truth = ["main.py"]
        found_files = simulator.simulate_find_files("main function", ground_truth)
        assert len(found_files) >= 1
        assert "main.py" in found_files

        # Test reading simulation
        content, total_tokens, read_time = simulator.simulate_read_files(found_files)
        assert total_tokens > 0
        assert read_time >= 0
        assert "main.py" in content

    def test_error_handling_and_recovery(self):
        """Test error handling and recovery in evaluation workflow."""
        # Test with invalid project path
        invalid_evaluator = TokenEfficiencyEvaluator(
            output_dir=str(self.output_dir), use_gpu=False
        )

        # This should handle the error gracefully
        instances = [
            EvaluationInstance(
                instance_id="error_test",
                query="test query",
                ground_truth_files=["nonexistent.py"],
            )
        ]

        # Should not crash, but handle errors gracefully
        try:
            results = invalid_evaluator.run_token_efficiency_evaluation(
                instances, "/nonexistent/path"
            )
            # Should still return a result structure, even if evaluation failed
            assert "metadata" in results
        except Exception as e:
            # Some exceptions are expected for invalid paths
            error_msg = str(e)
            expected_errors = [
                "Index not built",
                "No such file",
                "Project directory not found",
            ]
            assert any(
                msg in error_msg for msg in expected_errors
            ), f"Unexpected error: {error_msg}"

    def test_output_file_generation(self):
        """Test that all expected output files are generated."""
        from evaluation.base_evaluator import SearchMetrics
        from evaluation.token_efficiency_evaluator import (
            TokenEfficiencyMetrics,
            TokenEfficiencyResult,
        )

        # Create mock results
        mock_result = TokenEfficiencyResult(
            scenario_id="test_001",
            query="test query",
            search_metrics=SearchMetrics(0.5, 2, 0.8, 0.6, 0.69, 0.75, 0.82, 100, 1),
            efficiency_metrics=TokenEfficiencyMetrics(
                100, 500, 400, 0.2, 80.0, 0.5, 2.0, 1.5, 3
            ),
            search_results=[],
            simulated_files=["file1.py", "file2.py"],
            metadata={"test": True},
        )

        mock_results = {
            "metadata": {
                "total_instances": 1,
                "successful_evaluations": 1,
                "project_path": str(self.project_dir),
                "k": 5,
                "build_time": 1.0,
                "evaluation_timestamp": 1234567890.0,
                "encoding_name": "cl100k_base",
            },
            "aggregate_metrics": self.evaluator._calculate_token_efficiency_aggregates(
                [mock_result]
            ),
            "results_by_instance": {
                "test_001": {
                    "scenario_id": "test_001",
                    "query": "test query",
                    "search_metrics": mock_result.search_metrics.to_dict(),
                    "efficiency_metrics": mock_result.efficiency_metrics.__dict__,
                    "metadata": {"test": True},
                    "timestamp": 1234567890.0,
                }
            },
        }

        # Test file saving
        self.evaluator._save_token_efficiency_results(mock_results)

        # Verify files exist and have content
        results_file = self.output_dir / "token_efficiency_results.json"
        summary_file = self.output_dir / "token_efficiency_summary.json"

        assert results_file.exists()
        assert summary_file.exists()

        # Verify file contents
        with open(results_file) as f:
            saved_results = json.load(f)
            assert saved_results["metadata"]["total_instances"] == 1

        with open(summary_file) as f:
            saved_summary = json.load(f)
            assert "metadata" in saved_summary
            assert "aggregate_metrics" in saved_summary

        # Test report generation
        report = self.evaluator.create_efficiency_report(mock_results)
        assert "TOKEN EFFICIENCY EVALUATION REPORT" in report
        assert "Mean Token Savings" in report

        report_file = self.output_dir / "token_efficiency_report.txt"
        assert report_file.exists()

    def test_dataset_loading_integration(self):
        """Test loading and using the token efficiency scenarios dataset."""
        # Load the actual scenarios file
        scenarios_file = (
            Path(__file__).parent.parent.parent
            / "evaluation"
            / "datasets"
            / "token_efficiency_scenarios.json"
        )

        if scenarios_file.exists():
            instances = self.evaluator.load_dataset(str(scenarios_file))

            assert len(instances) > 0
            assert all(isinstance(instance.instance_id, str) for instance in instances)
            assert all(isinstance(instance.query, str) for instance in instances)
            assert all(
                isinstance(instance.ground_truth_files, list) for instance in instances
            )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestTokenEfficiencyRegression:
    """Regression tests to ensure existing functionality still works."""

    def test_base_evaluator_compatibility(self):
        """Test that TokenEfficiencyEvaluator is compatible with BaseEvaluator interface."""
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluator = TokenEfficiencyEvaluator(output_dir=temp_dir, use_gpu=False)

            # Test that all required abstract methods are implemented
            assert hasattr(evaluator, "build_index")
            assert hasattr(evaluator, "search")
            assert callable(evaluator.build_index)
            assert callable(evaluator.search)

            # Test that base methods are inherited
            assert hasattr(evaluator, "calculate_precision_recall")
            assert hasattr(evaluator, "calculate_f1_score")
            assert hasattr(evaluator, "calculate_mrr")
            assert hasattr(evaluator, "calculate_ndcg")

    def test_search_metrics_integration(self):
        """Test that SearchMetrics token_usage field is properly utilized."""
        from evaluation.base_evaluator import SearchMetrics

        # Test that token_usage field exists and works
        metrics = SearchMetrics(
            query_time=0.5,
            total_results=5,
            precision=0.8,
            recall=0.6,
            f1_score=0.69,
            mrr=0.75,
            ndcg=0.82,
            token_usage=150,  # This should be populated by token efficiency evaluator
            tool_calls=1,
        )

        assert metrics.token_usage == 150

        # Test conversion to dict
        metrics_dict = metrics.to_dict()
        assert "token_usage" in metrics_dict
        assert metrics_dict["token_usage"] == 150

    def test_no_regression_in_existing_tests(self):
        """Ensure that adding token efficiency doesn't break existing functionality."""
        # This test would be expanded to run existing test suites
        # For now, just verify that imports work correctly

        try:
            from evaluation.base_evaluator import BaseEvaluator  # noqa: F401
            from evaluation.base_evaluator import EvaluationInstance  # noqa: F401
            from evaluation.base_evaluator import SearchMetrics  # noqa: F401
            from evaluation.semantic_evaluator import (
                SemanticSearchEvaluator,
            )  # noqa: F401
            from evaluation.token_efficiency_evaluator import (
                TokenEfficiencyEvaluator,
            )  # noqa: F401

            # All imports should work without errors
            assert True
        except ImportError as e:
            pytest.fail(f"Import error indicating regression: {e}")
