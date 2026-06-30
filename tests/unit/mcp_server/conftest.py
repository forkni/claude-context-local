"""Shared fixtures for mcp_server unit tests.

Key fixture: _no_real_storage_pollution — autouse guard that fails any test
that accidentally writes to the real ~/.claude_code_search/projects directory.
Unit tests must never escape to real home storage; use monkeypatch or tmp_path.
"""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _no_real_storage_pollution() -> object:
    """Fail loudly if a unit test writes a new project to real home storage.

    Snapshots ~/.claude_code_search/projects before the test and after; any
    new directory added during the test triggers an assertion failure.  Tests
    that legitimately redirect storage via ``monkeypatch.setenv("CODE_SEARCH_STORAGE", ...)``
    won't touch this directory, so they are unaffected.
    """
    projects = Path.home() / ".claude_code_search" / "projects"
    before = set(projects.iterdir()) if projects.exists() else set()
    yield
    after = set(projects.iterdir()) if projects.exists() else set()
    leaked = after - before
    assert not leaked, (
        f"unit test wrote to real home storage — "
        f"patch the storage writers or use monkeypatch: "
        f"{sorted(p.name for p in leaked)}"
    )
