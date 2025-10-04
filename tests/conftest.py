"""Global pytest configuration and fixtures."""

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Generator

import pytest

# Add the package to Python path for testing
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from chunking.multi_language_chunker import MultiLanguageChunker
    from embeddings.embedder import CodeEmbedder
except ImportError:
    MultiLanguageChunker = None
    CodeEmbedder = None

try:
    from tests.fixtures.sample_code import (SAMPLE_API_MODULE,
                                            SAMPLE_AUTH_MODULE,
                                            SAMPLE_DATABASE_MODULE,
                                            SAMPLE_UTILS_MODULE)
except ImportError:
    SAMPLE_AUTH_MODULE = SAMPLE_DATABASE_MODULE = SAMPLE_API_MODULE = (
        SAMPLE_UTILS_MODULE
    ) = None


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "mcp: MCP server related tests")
    config.addinivalue_line("markers", "embeddings: Embedding generation tests")
    config.addinivalue_line("markers", "chunking: Code chunking tests")
    config.addinivalue_line("markers", "search: Search functionality tests")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark tests based on file path and location
        path_str = str(item.fspath)

        # First, determine if it's unit or integration
        if "tests/unit/" in path_str or "test_system.py" in path_str:
            item.add_marker(pytest.mark.unit)
        elif "tests/integration/" in path_str:
            item.add_marker(pytest.mark.integration)

        # Then add specific markers based on test file name
        if "test_chunking" in path_str:
            item.add_marker(pytest.mark.chunking)
        elif "test_embeddings" in path_str:
            item.add_marker(pytest.mark.embeddings)
        elif "test_indexing" in path_str:
            item.add_marker(pytest.mark.search)
        elif "test_mcp_server" in path_str:
            item.add_marker(pytest.mark.mcp)


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    # Reset MCP server global state
    try:
        import mcp_server.server as server_module

        server_module._embedder = None
        server_module._index_manager = None
        server_module._searcher = None
        server_module._storage_dir = None
    except ImportError:
        pass  # Module might not be available in some tests

    # Reset config manager cache to ensure clean state
    try:
        from search.config import get_config_manager

        config_manager = get_config_manager()
        config_manager._config = None
    except ImportError:
        pass  # Module might not be available in some tests

    yield

    # Cleanup after test if needed
    pass


# Test fixtures
@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir) / "test_project"
    project_path.mkdir(parents=True)

    yield project_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_codebase(temp_project_dir: Path) -> Dict[str, Path]:
    """Create a sample codebase with various Python modules."""
    if not SAMPLE_AUTH_MODULE:
        pytest.skip("Sample code not available")

    # Create directory structure
    src_dir = temp_project_dir / "src"
    src_dir.mkdir()

    auth_dir = src_dir / "auth"
    auth_dir.mkdir()

    database_dir = src_dir / "database"
    database_dir.mkdir()

    api_dir = src_dir / "api"
    api_dir.mkdir()

    utils_dir = src_dir / "utils"
    utils_dir.mkdir()

    # Create Python files with sample code
    files = {}

    # Authentication module
    auth_file = auth_dir / "authenticator.py"
    auth_file.write_text(SAMPLE_AUTH_MODULE)
    files["auth"] = auth_file

    # Database module
    db_file = database_dir / "manager.py"
    db_file.write_text(SAMPLE_DATABASE_MODULE)
    files["database"] = db_file

    # API module
    api_file = api_dir / "endpoints.py"
    api_file.write_text(SAMPLE_API_MODULE)
    files["api"] = api_file

    # Utils module
    utils_file = utils_dir / "helpers.py"
    utils_file.write_text(SAMPLE_UTILS_MODULE)
    files["utils"] = utils_file

    # Add __init__.py files
    for directory in [src_dir, auth_dir, database_dir, api_dir, utils_dir]:
        init_file = directory / "__init__.py"
        init_file.write_text("# Package init file")

    return files


@pytest.fixture
def chunker(temp_project_dir: Path) -> "MultiLanguageChunker":
    """Create a MultiLanguageChunker instance."""
    if not MultiLanguageChunker:
        pytest.skip("MultiLanguageChunker not available")
    return MultiLanguageChunker(str(temp_project_dir))


@pytest.fixture
def mock_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir(parents=True)

    # Create subdirectories
    (storage_dir / "models").mkdir()
    (storage_dir / "index").mkdir()
    (storage_dir / "cache").mkdir()

    return storage_dir


@pytest.fixture(scope="session")
def test_config():
    """Test configuration settings."""
    return {
        "embedding_model": "google/embeddinggemma-300m",
        "test_batch_size": 2,  # Small batch size for tests
        "test_timeout": 30,  # Timeout for tests
        "mock_embeddings": False,  # Use real embeddings if available
        "embedding_dimension": 768,
        "max_chunks_for_test": 10,  # Limit chunks in tests
    }


@pytest.fixture(scope="session")
def ensure_model_downloaded(test_config):
    """Ensure the embedding model is downloaded before running tests."""
    import os
    import subprocess
    from pathlib import Path

    # Check if we should use mocks instead
    if os.environ.get("PYTEST_USE_MOCKS", "").lower() in ("1", "true", "yes"):
        pytest.skip("Using mocks instead of real model")

    # Try to download model
    script_path = Path(__file__).parent / "scripts" / "download_model.py"
    if script_path.exists():
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--model",
                    test_config["embedding_model"],
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            if result.returncode != 0:
                pytest.skip(f"Could not download model: {result.stderr}")
        except subprocess.TimeoutExpired:
            pytest.skip("Model download timed out")
        except Exception as e:
            pytest.skip(f"Error downloading model: {e}")
    else:
        pytest.skip("Download script not found")

    return True


@pytest.fixture
def embedder_with_cleanup(mock_storage_dir):
    """Create a CodeEmbedder with proper GPU memory cleanup."""
    if not CodeEmbedder:
        pytest.skip("CodeEmbedder not available")

    # Create embedder with CPU device to avoid GPU memory issues
    embedder = CodeEmbedder(
        cache_dir=str(mock_storage_dir / "models"),
        device="cpu",  # Force CPU for tests to avoid VRAM issues
    )

    yield embedder

    # Cleanup after test
    try:
        embedder.cleanup()
    except Exception:
        pass
