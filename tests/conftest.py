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

import builtins  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import socket  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import traceback  # noqa: E402
from collections.abc import Generator  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

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
except ImportError:
    MultiLanguageChunker = None

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

    Phase 10 (test-suite hardening): imports are unconditional, not wrapped in
    ``except ImportError: pass``. All four modules are hard dependencies of
    this suite — under randomized test order, a renamed symbol here would
    otherwise silently degrade to "reset nothing" instead of failing the run,
    which is exactly the class of integrity gap Phase 10 closes.
    """
    from mcp_server.model_pool_manager import reset_pool_manager
    from mcp_server.tools.job_registry import reset_job_registry
    from search.config import set_indexing_ram_fallback_override
    from search.intent_classifier import (
        _ANCHOR_EMBEDDINGS_CACHE,
        _load_anchor_config,
        _load_intent_rules,
    )

    reset_pool_manager()
    reset_job_registry()
    _ANCHOR_EMBEDDINGS_CACHE.clear()
    _load_anchor_config.cache_clear()
    _load_intent_rules.cache_clear()
    set_indexing_ram_fallback_override(None)


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

    # Fail loudly, and attribute correctly, if this test leaked a background
    # job (asyncio.create_task via JobRegistry.track_background_task) that
    # it never awaited. _reset_singleton_state() above gave this test a
    # *fresh* registry, so anything still pending here was created during
    # this test only -- cancelling it silently (as reset_job_registry()
    # does for its own, best-effort reasons) would let it keep running past
    # this point and touch real resources during a later, unrelated test's
    # mocked window instead. That's a real leak this project hit (2026-08-03):
    # an orphaned background-index task constructed a real, unmocked
    # SnapshotManager and wrote to real home storage during a completely
    # unrelated later test. Naming the actual offending test here, instead
    # of letting the write surface as someone else's storage-pollution
    # failure, is the fix -- see TestIndexDirectoryAsyncJob in
    # test_index_handlers.py for the "await the task before the patch
    # context exits" pattern the leaking test needs to adopt.
    from mcp_server.tools.job_registry import get_job_registry

    _leaked_jobs = get_job_registry()._background_tasks
    if _leaked_jobs:
        for _task in _leaked_jobs:
            _task.cancel()
        pytest.fail(
            f"{len(_leaked_jobs)} background job(s) were still running at "
            "test teardown -- await the task explicitly before the test "
            "ends instead of leaving it to finish (and touch real "
            "resources) after the test's own mocks have gone out of scope."
        )

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


# Real (unpatched) home directory, captured at module-import time — i.e.
# before any test/fixture has a chance to monkeypatch Path.home(). All
# comparisons below use this frozen value, never a live Path.home() call, so a
# test that legitimately redirects Path.home() to its own tmp_path (e.g.
# TestSnapshotManagerStorageDir.test_default_without_storage_manager_falls_back
# in tests/unit/merkle/test_merkle.py) is correctly seen as writing to *its*
# fake home, not the real one.
_REAL_HOME = Path.home()
_REAL_STORAGE_ROOT = (_REAL_HOME / ".claude_code_search").resolve()

# Windows hands out 8.3 short paths (C:\Users\RUNNER~1\...) and macOS symlinks
# /tmp -> /private/tmp. Production code normalises with Path.resolve(), so a
# test that compares a stored path against its raw mkdtemp()/tmp_path fixture
# path fails on CI but passes locally. Pinning the temp root to its resolved
# form up front makes those resolve() calls a no-op and removes the whole
# failure class. Must run at module import time, before any test can call
# tempfile.mkdtemp().
tempfile.tempdir = str(Path(tempfile.gettempdir()).resolve())

# Process-local ledger of writes that resolved under _REAL_STORAGE_ROOT.
# Populated by the wrapped primitives _install_real_storage_write_ledger
# installs for the whole session; drained per-test by _no_real_storage_pollution.
_real_storage_write_ledger: list[dict[str, str]] = []


def _record_if_real_storage(target: "str | Path | int") -> None:
    """Append a ledger entry if *target* resolves under real home storage."""
    # builtins.open also accepts an integer fd — multiprocessing's Windows spawn
    # calls open(wfd, "wb") to talk to the child. An fd has no path to attribute,
    # and Path(int) raises TypeError, which would otherwise escape into the caller
    # and break every ProcessPoolExecutor spawn for the rest of the session.
    if not isinstance(target, (str, bytes, os.PathLike)):
        return
    try:
        resolved = Path(target).resolve()
    except (OSError, ValueError, RuntimeError):
        return
    try:
        resolved.relative_to(_REAL_STORAGE_ROOT)
    except ValueError:
        return
    _real_storage_write_ledger.append(
        {"path": str(resolved), "stack": "".join(traceback.format_stack()[:-2])}
    )


@pytest.fixture(scope="session", autouse=True)
def _install_real_storage_write_ledger() -> Generator[None, None, None]:
    """Wrap this process's write primitives to attribute real-storage writes correctly.

    Phase 10.5 (test-suite hardening): the previous design
    (_no_real_storage_pollution, below) diffed a directory listing of
    ~/.claude_code_search/{projects,merkle,graphs} before/after each test. That
    has no notion of *which process* wrote a file — during this campaign, a
    live code-search MCP server was found to be concurrently auto-reindexing
    this very repo while the suite ran. Its writes (real deployed
    project-hash + model-slug filenames the autouse test project-id mock can
    never produce, landing in the real ~/.claude_code_search/merkle/, mtime-
    confirmed mid-run) were attributed to whichever unrelated test's teardown
    happened to straddle the write — one external write could surface as 1-3
    consecutive failures on completely innocent tests.

    This instead wraps the actual write primitives *this process* uses —
    builtins.open (write modes only), os.replace, os.rename, and Path.mkdir —
    which covers every atomic-write path in this repo (see
    utils/atomic_io.write_json_atomic: open(tmp, "w") then os.replace(tmp,
    path)) plus the unconditional mkdir in SnapshotManager.__init__ and
    CodeGraphStorage's default storage_dir (the case this guard originally
    existed for — CodeGraphStorage reads Path.home() directly and bypasses
    get_storage_dir(), see _redirect_test_storage's docstring above). Any call
    whose target resolves under the real ~/.claude_code_search is recorded in
    _real_storage_write_ledger with a stack trace: a leak now names its own
    call site instead of a bare filename, and a write by some *other* process
    on the machine never passes through these wrappers at all, so it can no
    longer be misattributed to this process's tests.

    _wrapped_open's mode check ("wax+") also matches multiprocessing's Windows
    spawn, which opens the child's pipe fd via open(wfd, "wb") — an integer,
    not a path. _record_if_real_storage must tolerate that (see its own
    isinstance guard) or every ProcessPoolExecutor spawn breaks under pytest.
    """
    real_open = builtins.open
    real_replace = os.replace
    real_rename = os.rename
    real_mkdir = Path.mkdir

    def _wrapped_open(file, mode="r", *args: Any, **kwargs: Any):
        if isinstance(mode, str) and any(c in mode for c in "wax+"):
            _record_if_real_storage(file)
        return real_open(file, mode, *args, **kwargs)

    def _wrapped_replace(src, dst, *args: Any, **kwargs: Any):
        _record_if_real_storage(dst)
        return real_replace(src, dst, *args, **kwargs)

    def _wrapped_rename(src, dst, *args: Any, **kwargs: Any):
        _record_if_real_storage(dst)
        return real_rename(src, dst, *args, **kwargs)

    def _wrapped_mkdir(self, *args: Any, **kwargs: Any):
        _record_if_real_storage(self)
        return real_mkdir(self, *args, **kwargs)

    mp = pytest.MonkeyPatch()
    mp.setattr(builtins, "open", _wrapped_open)
    mp.setattr(os, "replace", _wrapped_replace)
    mp.setattr(os, "rename", _wrapped_rename)
    mp.setattr(Path, "mkdir", _wrapped_mkdir)
    yield
    mp.undo()


_REAL_SOCKET_CONNECT = socket.socket.connect
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _guarded_socket_connect(self: socket.socket, address: Any) -> Any:
    """Block outbound connections to anything but loopback.

    AF_UNIX/AF_PIPE-style addresses are plain strings (a filesystem path),
    not a (host, port) tuple, and are never network egress — pass those
    through untouched.
    """
    host = address[0] if isinstance(address, tuple) and address else None
    if host is not None and host not in _LOOPBACK_HOSTS:
        raise RuntimeError(
            f"Blocked outbound network connection to {address!r}. "
            "tests/unit and tests/fast_integration must not reach the real "
            "network (HF Hub, PyPI, ...) -- inject a stub client/embedder "
            "instead of relying on a lazy real-model construction path (see "
            "TestHybridSearcher._stub_search_deps in "
            "tests/unit/search/test_hybrid_search.py for the pattern), or "
            "mark the test @pytest.mark.allow_network if it legitimately "
            "needs the network (tests/slow_integration/ downloads real "
            "models and is already exempt by path)."
        )
    return _REAL_SOCKET_CONNECT(self, address)


@pytest.fixture(autouse=True)
def _block_real_network(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail loudly, at the exact call site, instead of silently reaching the
    real network.

    Phase 11 (test-suite hardening): item 1's real finding was that a
    forgotten embedder/reranker stub in tests/unit/search/test_hybrid_search.py
    made real HTTPS calls to huggingface.co and loaded a real GPU model — a
    slow, easy-to-miss failure mode that only ever showed up as "this test is
    mysteriously taking 60s". This turns any future recurrence (in this file
    or anywhere else in tests/unit or tests/fast_integration) into an
    immediate, unambiguous RuntimeError naming the actual call site.

    Sets HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE so huggingface_hub/transformers
    fail fast on their own cache-miss path, and patches
    socket.socket.connect as a backstop for every other client (requests,
    urllib3, raw sockets). Loopback connections (local test servers, pipes)
    are unaffected.

    tests/slow_integration/ legitimately downloads real models, so it is
    exempted by path, matching this file's existing pattern (see
    mock_snapshot_manager_for_unit_tests above). Any other test that needs
    the real network can opt out with @pytest.mark.allow_network.

    Function-scoped rather than session-scoped (departing from a stricter
    read of the original plan) so the per-test opt-out marker/path check
    below can actually take effect — a session-scoped fixture only runs its
    setup once, before pytest knows which specific test is about to run.
    """
    test_path = normalize_path(str(request.fspath))
    if "tests/slow_integration/" in test_path:
        return
    if request.node.get_closest_marker("allow_network") is not None:
        return

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.setattr(socket.socket, "connect", _guarded_socket_connect)


@pytest.fixture(autouse=True)
def _no_real_storage_pollution() -> Generator[None, None, None]:
    """Fail loudly if THIS test wrote to real home storage.

    Phase 8: promoted from tests/unit/mcp_server/conftest.py to apply to every
    test. Phase 10.5: reads the process-local write ledger populated by
    _install_real_storage_write_ledger instead of diffing a shared directory
    listing — see that fixture's docstring for why the old diff-based design
    misattributed a concurrent external process's writes to unrelated tests.

    Clears the ledger before the test body runs so only this test's own
    writes are in scope, then asserts it is still empty after teardown,
    printing the recorded call site(s) on failure. Tests that legitimately
    need real storage should patch/monkeypatch it explicitly rather than
    relying on an exemption here.
    """
    _real_storage_write_ledger.clear()
    yield
    leaked = list(_real_storage_write_ledger)
    _real_storage_write_ledger.clear()
    assert not leaked, (
        "test wrote to real home storage — patch the storage writers or use "
        "monkeypatch. Call site(s):\n"
        + "\n---\n".join(f"{e['path']}:\n{e['stack']}" for e in leaked)
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
    """Redirect every bare SnapshotManager() default in unit tests to tmp_path.

    Only applies to tests in tests/unit/ directory. Integration tests may need
    real SnapshotManager behavior.

    Phase 10.5 (test-suite hardening): previously patched
    "merkle.snapshot_manager.SnapshotManager" — the *definition module's*
    attribute — with a docstring claiming this was "sufficient for all
    imports". It was not: five production modules
    (search/incremental_indexer.py, search/index_write_stage.py,
    mcp_server/tools/status_handlers.py, merkle/change_detector.py,
    merkle/__init__.py, plus this test suite's own tests/unit/merkle/
    test_merkle.py) do `from merkle.snapshot_manager import SnapshotManager`
    at their own import time, binding their own local name to the class
    object before this fixture ever runs — patching the definition module's
    attribute afterwards never reaches those bindings. This was latent rather
    than a live leak because CODE_SEARCH_STORAGE (see _redirect_test_storage
    above) already redirects SnapshotManager's own default resolution.

    Patches SnapshotManager.__init__ itself — a class-level attribute shared
    by every one of those bindings, since they all still point at the same
    class object — so a bare SnapshotManager() call (what every production
    call site above actually does; see the grep in TESTING_GUIDE.md's Phase
    10 record) gets this test's tmp_path regardless of which module
    constructed it. Explicit storage_dir= callers are left untouched, so
    tests that build their own SnapshotManager against a directory they
    inspect afterwards keep working unchanged.

    Exemption: tests/unit/merkle/test_merkle.py's TestSnapshotManagerStorageDir
    calls bare SnapshotManager() specifically to exercise the class's *own*
    default-resolution logic (the get_storage_dir() branch and the
    Path.home() fallback branch) — forcing storage_dir there would defeat
    the test. Those two tests already protect themselves against real-home
    pollution independently (faking mcp_server.storage_manager / monkeypatching
    Path.home()), so this fixture skips that one file rather than patching
    it and immediately un-patching around those tests.

    This fixture's yielded value has no consumers (nothing requests it by
    name via fixture injection) — its internals are free to change.
    """
    from unittest.mock import patch

    from merkle.snapshot_manager import SnapshotManager

    # Only apply to unit tests (handle both Unix and Windows path separators)
    test_path = normalize_path(str(request.fspath))
    if "tests/unit" not in test_path:
        yield
        return
    if test_path.endswith("tests/unit/merkle/test_merkle.py"):
        yield
        return

    default_storage_dir = tmp_path / "merkle"
    real_init = SnapshotManager.__init__

    def _redirected_init(self: Any, storage_dir: Path | None = None) -> None:
        if storage_dir is None:
            storage_dir = default_storage_dir
        real_init(self, storage_dir=storage_dir)

    with patch.object(SnapshotManager, "__init__", _redirected_init):
        yield


# ============================================================================
# Shared Test Helper Functions (see tests/helpers/embeddings.py)
# ============================================================================
# generate_chunk_id and create_test_embeddings live in tests.helpers.embeddings.
# Import them directly in test files: from tests.helpers.embeddings import ...
