"""Global pytest configuration and fixtures."""

import logging
import warnings


# Suppress FAISS SWIG warnings at import time (before pytest/FAISS imports)
warnings.filterwarnings(
    "ignore", message=".*builtin type SwigPy.*", category=DeprecationWarning
)
warnings.filterwarnings(
    "ignore",
    message=".*builtin type.*has no __module__ attribute.*",
    category=DeprecationWarning,
)

import shutil  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
from collections.abc import Generator  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from search.filters import normalize_path  # noqa: E402


# CRITICAL: Ensure tests run from project .venv, not system Python
# This prevents silent failures when dependencies are missing from system install
_venv_path = Path(__file__).parent.parent / ".venv"
if _venv_path.exists():
    _venv_python = _venv_path / "Scripts" / "python.exe"
    if not _venv_python.exists():
        _venv_python = _venv_path / "bin" / "python"  # Linux/macOS

    _current_prefix = Path(sys.prefix).resolve()
    _expected_prefix = _venv_path.resolve()

    if not str(_current_prefix).startswith(str(_expected_prefix)):
        raise RuntimeError(
            f"Tests must run from project .venv, not system Python.\n"
            f"Current interpreter: {sys.executable}\n"
            f"Expected: {_venv_python}\n"
            f"Fix: Use ./scripts/test/run_tests.sh instead of 'python -m pytest'"
        )

# Note: sys.path manipulation removed — pythonpath = ["."] in pyproject.toml
# [tool.pytest.ini_options] and editable install handle package discovery.

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
    import warnings

    # Suppress FAISS SWIG warnings at import time (before pytest filterwarnings apply)
    warnings.filterwarnings(
        "ignore", message=".*builtin type.*", category=DeprecationWarning
    )

    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "mcp: MCP server related tests")
    config.addinivalue_line("markers", "embeddings: Embedding generation tests")
    config.addinivalue_line("markers", "chunking: Code chunking tests")
    config.addinivalue_line("markers", "search: Search functionality tests")
    config.addinivalue_line(
        "markers", "gpu: Requires CUDA device (skipped when absent)"
    )
    config.addinivalue_line("markers", "e2e: Full end-to-end workflow")


@pytest.fixture(scope="session", autouse=True)
def suppress_torch_dynamo_atexit_logging():
    """Suppress torch._dynamo atexit logging that fails during shutdown.

    torch._dynamo registers atexit handlers that try to log after stderr is closed,
    causing "I/O operation on closed file" errors. Replace handlers with no-ops.
    """
    yield  # Let tests run first

    # After all tests, replace logger handlers with no-ops before atexit runs
    import sys

    if "torch._dynamo" in sys.modules:
        try:
            # Replace all handlers with NullHandler to prevent closed file errors
            dynamo_logger = logging.getLogger("torch._dynamo")
            dynamo_logger.handlers = [logging.NullHandler()]
            dynamo_logger.propagate = False
        except Exception:
            pass  # Ignore errors during cleanup


def pytest_unconfigure(config: Any) -> None:
    """Pytest cleanup hook (intentionally empty - see suppress_torch_dynamo_atexit_logging)."""
    pass


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark tests based on file path and location. normalize_path() converts
        # backslashes to forward slashes first so this matches on Windows too.
        path_str = normalize_path(str(item.fspath))

        # Structural tier marking - one marker per tier, by directory, so
        # fast_integration/slow are no longer solely hand-decorated.
        if "tests/unit/" in path_str:
            item.add_marker(pytest.mark.unit)
        elif "tests/fast_integration/" in path_str or "tests/integration/" in path_str:
            item.add_marker(pytest.mark.integration)
        elif "tests/slow_integration/" in path_str:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)

        # test_system.py sits at tests/ root but exercises unit-level checks.
        if "test_system.py" in path_str:
            item.add_marker(pytest.mark.unit)

        # Then add specific markers based on test file name
        if "test_chunking" in path_str:
            item.add_marker(pytest.mark.chunking)
        elif "test_embeddings" in path_str:
            item.add_marker(pytest.mark.embeddings)
        elif "test_indexing" in path_str:
            item.add_marker(pytest.mark.search)
        elif "test_mcp_server" in path_str:
            item.add_marker(pytest.mark.mcp)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clean up test-created project indices and merkle trees after test session.

    Only runs cleanup_orphaned_projects.py which safely identifies test projects by
    checking if their project_path still exists. Test projects point to temporary
    directories (pytest's tmp_path) that are deleted after tests, so they can be
    safely cleaned up along with their merkle trees.

    NOTE: cleanup_stale_snapshots.py is NOT run automatically because it identifies
    "stale" snapshots by checking for missing indices, not by checking if the original
    project path exists. This could incorrectly delete merkle trees for real projects
    if their indices were temporarily affected by tests.

    Args:
        session: pytest session object
        exitstatus: Exit status code (0=passed, 1=some tests failed, 2=interrupted, etc.)
    """
    import subprocess
    import sys
    from pathlib import Path

    # Only run cleanup if tests passed or had some failures (not on collection errors)
    if exitstatus in (0, 1):  # 0=passed, 1=some tests failed
        # Only cleanup orphaned projects (those where project_path no longer exists)
        # This safely targets test projects (temp directories) while preserving
        # real projects (whose paths still exist on disk)
        orphan_cleanup_script = (
            Path(__file__).parent.parent / "tools" / "cleanup_orphaned_projects.py"
        )

        if orphan_cleanup_script.exists():
            try:
                # Run cleanup in non-interactive mode (auto-confirm deletion)
                subprocess.run(
                    [sys.executable, str(orphan_cleanup_script), "--auto"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                # Silent on success - no output
            except subprocess.TimeoutExpired:
                print("\n[Cleanup] Warning: Orphaned project cleanup timed out")
            except Exception as e:
                print(f"\n[Cleanup] Warning: Orphaned project cleanup failed: {e}")


def _reset_singleton_state() -> None:
    """Reset the module-level singletons known to leak state across tests.

    Phase 7 (test-suite hardening): these four survive ApplicationState.reset()
    because they live outside it — ModelPoolManager and JobRegistry are their
    own singletons, the intent-classifier anchor cache/config/rules are plain
    module globals and lru_cache'd loaders, and the RAM-fallback override is a
    module global by design (see its own docstring for why it must NOT be
    cleared by ApplicationState.reset() itself).
    """
    try:
        from mcp_server.model_pool_manager import reset_pool_manager

        reset_pool_manager()
    except ImportError:
        pass  # Module might not be available in some tests

    try:
        from mcp_server.tools.job_registry import reset_job_registry

        reset_job_registry()
    except ImportError:
        pass  # Module might not be available in some tests

    try:
        from search.intent_classifier import (
            _ANCHOR_EMBEDDINGS_CACHE,
            _load_anchor_config,
            _load_intent_rules,
        )

        _ANCHOR_EMBEDDINGS_CACHE.clear()
        _load_anchor_config.cache_clear()
        _load_intent_rules.cache_clear()
    except ImportError:
        pass  # Module might not be available in some tests

    try:
        from search.config import set_indexing_ram_fallback_override

        set_indexing_ram_fallback_override(None)
    except ImportError:
        pass  # Module might not be available in some tests


@pytest.fixture(autouse=True)
def reset_global_state() -> Generator[None, None, None]:
    """Reset global state before each test.

    Uses the centralized ApplicationState.reset() for clean state management.
    Also resets the module-level globals for backward compatibility during migration.
    Phase 4: Added ServiceLocator.reset() for DI pattern.
    Phase 7: Added the singleton resets in _reset_singleton_state(), run both
    before and after each test so a test that itself asserts on this state
    (e.g. the anchor cache) still sees a clean slate at the start.
    """
    # Reset MCP server global state via ApplicationState
    try:
        from mcp_server.state import reset_state

        reset_state()
    except ImportError:
        pass  # Module might not be available in some tests

    # Reset config manager cache to ensure clean state
    try:
        from search.config import get_config_manager

        config_manager = get_config_manager()
        config_manager._config = None
    except ImportError:
        pass  # Module might not be available in some tests

    _reset_singleton_state()

    yield

    # Cleanup after test if needed
    _reset_singleton_state()


@pytest.fixture(scope="session", autouse=True)
def detach_server_file_logging() -> Generator[None, None, None]:
    """Prevent mcp_server's root-logger file handler from capturing pytest output.

    mcp_server.server._configure_logging() attaches a DEBUG _SafeRotatingFileHandler to the
    ROOT logger at import time, so every test logger (including deliberate Simulated/Mock
    failure injections) would otherwise propagate into logs/mcp_server.log and masquerade as
    real server errors. Detach it for the duration of the test session; restore afterward.
    """
    root = logging.getLogger()
    try:
        import mcp_server.server as _srv  # force _configure_logging() to have run

        safe_cls = _srv._SafeRotatingFileHandler
    except ImportError:
        yield
        return

    detached = [h for h in list(root.handlers) if isinstance(h, safe_cls)]
    for h in detached:
        root.removeHandler(h)
    try:
        yield
    finally:
        for h in detached:
            root.addHandler(h)


@pytest.fixture(scope="session", autouse=True)
def _redirect_test_storage(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[Path, None, None]:
    """Redirect CODE_SEARCH_STORAGE to an isolated session-scoped tmp dir.

    Phase 8 (test-suite hardening): get_storage_dir() (mcp_server/storage_manager.py)
    and get_selection_file_path() (mcp_server/project_persistence.py) both read
    CODE_SEARCH_STORAGE directly and fall back to the real ~/.claude_code_search
    when it is unset. ApplicationState.reset() nulls storage_dir every test (see
    reset_global_state below), so the env var is re-read on first access each
    test — no extra plumbing needed beyond setting it once, here, for the whole
    session.

    This subsumes the old preserve_original_project_selection fixture: with
    CODE_SEARCH_STORAGE always redirected, save_project_selection/
    load_project_selection/clear_project_selection never touch the real
    project_selection.json in the first place, so there is nothing left to
    preserve or restore.

    Note: CodeGraphStorage's default storage_dir (graph/graph_storage.py) reads
    Path.home() directly rather than going through get_storage_dir(), so it does
    NOT honor this redirect — tests must still pass storage_dir= explicitly (see
    the graph_storage fixture below and TESTING_GUIDE.md's pitfalls table).
    _no_real_storage_pollution (below) is the backstop that catches that case.

    Uses pytest.MonkeyPatch directly (not the function-scoped `monkeypatch`
    fixture, which cannot be session-scoped) so the override is undone at
    session end even on error.
    """
    storage_dir = tmp_path_factory.mktemp("code_search_storage")
    mp = pytest.MonkeyPatch()
    mp.setenv("CODE_SEARCH_STORAGE", str(storage_dir))
    yield storage_dir
    mp.undo()


@pytest.fixture(autouse=True)
def _no_real_storage_pollution() -> Generator[None, None, None]:
    """Fail loudly if a test writes to real home storage.

    Phase 8 (test-suite hardening): promoted from
    tests/unit/mcp_server/conftest.py to apply to every test, not just
    tests/unit/mcp_server/ — now that _redirect_test_storage (above) redirects
    CODE_SEARCH_STORAGE for the whole session, this is the safety net for
    anything that bypasses it (e.g. CodeGraphStorage's default storage_dir,
    which reads Path.home() directly — see the note above).

    Snapshots ~/.claude_code_search/{projects,merkle,graphs} before the test and
    after; any new entry added during the test triggers an assertion failure.
    Tests that legitimately need real storage should patch/monkeypatch it
    explicitly rather than relying on an exemption here.
    """
    home_storage = Path.home() / ".claude_code_search"
    watched = [home_storage / sub for sub in ("projects", "merkle", "graphs")]
    before = {d: (set(d.iterdir()) if d.exists() else set()) for d in watched}
    yield
    after = {d: (set(d.iterdir()) if d.exists() else set()) for d in watched}
    leaked = {
        d.name: sorted(p.name for p in (after[d] - before[d]))
        for d in watched
        if after[d] - before[d]
    }
    assert not leaked, (
        "test wrote to real home storage — patch the storage writers or use "
        f"monkeypatch: {leaked}"
    )


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
def sample_codebase(temp_project_dir: Path) -> dict[str, Path]:
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
def test_config() -> dict[str, Any]:
    """Test configuration settings."""
    return {
        "embedding_model": "BAAI/bge-m3",
        "test_batch_size": 2,  # Small batch size for tests
        "test_timeout": 30,  # Timeout for tests
        "mock_embeddings": False,  # Use real embeddings if available
        "embedding_dimension": 1024,
        "max_chunks_for_test": 10,  # Limit chunks in tests
    }


@pytest.fixture(scope="session")
def ensure_model_downloaded(test_config: dict[str, Any]) -> bool:
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
    except Exception as e:
        # Test cleanup - log but don't fail test
        import warnings

        warnings.warn(f"Embedder cleanup failed: {e}", stacklevel=2)


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
    test_path = normalize_path(str(request.fspath))
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
    mock_instance.delete_all_snapshots.return_value = 0
    mock_instance.load_snapshot.return_value = None
    mock_instance.get_project_id.side_effect = lambda path: (
        f"test_{hash(path) & 0xFFFFFFFF:08x}"
    )

    # Patch at definition point (sufficient for all imports)
    with patch("merkle.snapshot_manager.SnapshotManager") as mock_def:
        mock_def.return_value = mock_instance
        yield mock_instance


# ============================================================================
# Shared Test Helper Functions (see tests/helpers/embeddings.py)
# ============================================================================
# generate_chunk_id and create_test_embeddings live in tests.helpers.embeddings.
# Import them directly in test files: from tests.helpers.embeddings import ...


@pytest.fixture
def mock_embedding_result_factory():
    """Factory for creating mock EmbeddingResult objects.

    Usage:
        def test_something(mock_embedding_result_factory):
            result = mock_embedding_result_factory(
                chunk_id="file.py:1-10:function:my_func",
                name="my_func",
                calls=[{"callee_name": "other_func", "line_number": 5}]
            )

    Args:
        chunk_id: Chunk identifier (default: "test.py:1-10:function:test_func")
        name: Function/class name (default: "test_func")
        chunk_type: Type of code chunk (default: "function")
        content: Code content (default: "def test_func(): pass")
        file_path: File path (extracted from chunk_id if not provided)
        calls: List of call dictionaries (default: [])
        relationships: List of relationship dictionaries (default: [])
        embedding_dim: Embedding dimension (default: 768)

    Returns:
        Callable that creates EmbeddingResult objects
    """

    def create(
        chunk_id: str = "test.py:1-10:function:test_func",
        name: str = "test_func",
        chunk_type: str = "function",
        content: str = "def test_func(): pass",
        file_path: str | None = None,
        calls: list[dict] | None = None,
        relationships: list[dict] | None = None,
        embedding_dim: int = 768,
    ):
        if not EmbeddingResult:
            pytest.skip("EmbeddingResult not available")

        # Deterministic embedding from chunk_id
        seed = hash(chunk_id) & 0xFFFFFFFF
        embedding = np.random.RandomState(seed).random(embedding_dim).astype(np.float32)

        # Extract file_path from chunk_id if not provided
        if file_path is None:
            file_path = chunk_id.split(":")[0]

        return EmbeddingResult(
            embedding=embedding,
            chunk_id=chunk_id,
            metadata={
                "name": name,
                "chunk_type": chunk_type,
                "content": content,
                "file_path": file_path,
                "calls": calls or [],
                "relationships": relationships or [],
            },
        )

    return create
