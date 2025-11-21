"""Global pytest configuration and fixtures."""

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import numpy as np
import pytest

# Add the package to Python path for testing
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from chunking.multi_language_chunker import MultiLanguageChunker
    from embeddings.embedder import CodeEmbedder, EmbeddingResult
except ImportError:
    MultiLanguageChunker = None
    CodeEmbedder = None
    EmbeddingResult = None

try:
    from tests.fixtures.sample_code import (
        SAMPLE_API_MODULE,
        SAMPLE_AUTH_MODULE,
        SAMPLE_DATABASE_MODULE,
        SAMPLE_UTILS_MODULE,
    )
except ImportError:
    SAMPLE_AUTH_MODULE = SAMPLE_DATABASE_MODULE = SAMPLE_API_MODULE = (
        SAMPLE_UTILS_MODULE
    ) = None


def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "mcp: MCP server related tests")
    config.addinivalue_line("markers", "embeddings: Embedding generation tests")
    config.addinivalue_line("markers", "chunking: Code chunking tests")
    config.addinivalue_line("markers", "search: Search functionality tests")


def pytest_collection_modifyitems(config: Any, items: List[Any]) -> None:
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
def reset_global_state() -> Generator[None, None, None]:
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
def chunker(temp_project_dir: Path) -> Any:
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
def test_config() -> Dict[str, Any]:
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
def ensure_model_downloaded(test_config: Dict[str, Any]) -> bool:
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
def embedder_with_cleanup(mock_storage_dir: Path) -> Generator[Any, None, None]:
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


@pytest.fixture
def graph_storage(tmp_path: Path) -> Generator[Any, None, None]:
    """Create a CodeGraphStorage instance with isolated temporary directory.

    Prevents production directory pollution by storing graph data in pytest's
    temporary directory. Automatically cleans up after test.
    """
    try:
        from graph.graph_storage import CodeGraphStorage
    except ImportError:
        pytest.skip("CodeGraphStorage not available")

    storage_dir = tmp_path / "graphs"
    storage_dir.mkdir(parents=True)

    graph = CodeGraphStorage("test_project", storage_dir=storage_dir)

    yield graph

    # Cleanup is automatic via tmp_path fixture


@pytest.fixture
def snapshot_manager(tmp_path: Path) -> Generator[Any, None, None]:
    """Create a SnapshotManager instance with isolated temporary directory.

    Prevents production directory pollution by storing merkle snapshots in
    pytest's temporary directory. Automatically cleans up after test.
    """
    try:
        from merkle.snapshot_manager import SnapshotManager
    except ImportError:
        pytest.skip("SnapshotManager not available")

    storage_dir = tmp_path / "merkle"
    storage_dir.mkdir(parents=True)

    manager = SnapshotManager(storage_dir=str(storage_dir))

    yield manager

    # Cleanup is automatic via tmp_path fixture


@pytest.fixture(autouse=True)
def mock_snapshot_manager_for_unit_tests(
    tmp_path: Path, request
) -> Generator[Any, None, None]:
    """Mock SnapshotManager globally for unit tests to prevent production pollution.

    Only applies to tests in tests/unit/ directory.
    Integration tests may need real SnapshotManager behavior.

    Patches multiple import locations to catch all uses.
    """
    from unittest.mock import Mock, patch

    # Only apply to unit tests (handle both Unix and Windows path separators)
    test_path = str(request.fspath).replace("\\", "/")
    if "tests/unit" not in test_path:
        yield
        return

    # Create mock instance that uses tmp_path
    mock_instance = Mock()
    mock_instance.storage_dir = tmp_path / "merkle"
    mock_instance.has_snapshot.return_value = False
    mock_instance.get_snapshot_age.return_value = None
    mock_instance.save_snapshot.return_value = None
    mock_instance.delete_snapshot.return_value = None
    mock_instance.load_snapshot.return_value = None
    mock_instance.get_project_id.side_effect = (
        lambda path: f"test_{hash(path) & 0xFFFFFFFF:08x}"
    )

    # Patch at definition point
    with patch("merkle.snapshot_manager.SnapshotManager") as mock_def:
        mock_def.return_value = mock_instance

        # Patch at usage points (where it's already imported)
        with patch("search.incremental_indexer.SnapshotManager") as mock_usage:
            mock_usage.return_value = mock_instance
            yield mock_instance


# ============================================================================
# Shared Test Helper Functions
# ============================================================================


def generate_chunk_id(chunk: Any) -> str:
    """Generate chunk ID like the embedder does.

    Args:
        chunk: Code chunk with relative_path, start_line, end_line, chunk_type, and optional name

    Returns:
        Chunk ID string in format: "path:start-end:type" or "path:start-end:type:name"
    """
    chunk_id = (
        f"{chunk.relative_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
    )
    if chunk.name:
        chunk_id += f":{chunk.name}"
    return chunk_id


def create_test_embeddings(
    chunks: List[Any], embedder: Optional[Any] = None, embedding_dim: int = 768
) -> List[Any]:
    """Create embeddings from chunks for testing.

    Supports two modes:
    1. Deterministic mode (embedder=None): Fast, reproducible embeddings for unit tests
    2. Real embedder mode (embedder provided): Actual embeddings for integration tests

    Args:
        chunks: List of code chunks to embed
        embedder: Optional CodeEmbedder instance. If None, uses deterministic embeddings
        embedding_dim: Embedding dimension for deterministic mode (default: 768)

    Returns:
        List of EmbeddingResult objects with embeddings, chunk_ids, and metadata
    """
    if not EmbeddingResult:
        raise ImportError("EmbeddingResult not available")

    embeddings = []

    # Mode 1: Real embedder provided - use it for actual embeddings
    if embedder:
        texts = [chunk.content for chunk in chunks]
        chunk_ids = [generate_chunk_id(chunk) for chunk in chunks]

        # Use embedder to generate real embeddings
        embed_results = embedder.embed_batch(
            texts=texts,
            chunk_ids=chunk_ids,
            metadata=[
                {
                    "name": chunk.name,
                    "chunk_type": chunk.chunk_type,
                    "file_path": chunk.file_path,
                    "relative_path": chunk.relative_path,
                    "folder_structure": chunk.folder_structure,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "docstring": chunk.docstring,
                    "tags": chunk.tags,
                    "complexity_score": chunk.complexity_score,
                    "content_preview": (
                        chunk.content[:200] + "..."
                        if len(chunk.content) > 200
                        else chunk.content
                    ),
                }
                for chunk in chunks
            ],
        )
        return embed_results

    # Mode 2: No embedder - use deterministic embeddings for fast tests
    for chunk in chunks:
        # Create deterministic embedding based on content hash
        content_hash = abs(hash(chunk.content)) % 10000
        embedding = (
            np.random.RandomState(content_hash).random(embedding_dim).astype(np.float32)
        )

        chunk_id = generate_chunk_id(chunk)
        metadata = {
            "name": chunk.name,
            "chunk_type": chunk.chunk_type,
            "file_path": chunk.file_path,
            "relative_path": chunk.relative_path,
            "folder_structure": chunk.folder_structure,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "docstring": chunk.docstring,
            "tags": chunk.tags,
            "complexity_score": chunk.complexity_score,
            "content_preview": (
                chunk.content[:200] + "..."
                if len(chunk.content) > 200
                else chunk.content
            ),
        }

        result = EmbeddingResult(
            embedding=embedding, chunk_id=chunk_id, metadata=metadata
        )
        embeddings.append(result)

    return embeddings
