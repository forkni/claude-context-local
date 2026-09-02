"""Unit tests for mcp_server.index_freshness -- the content-only freshness verdict.

Exercises the real ChangeDetector/SnapshotManager/MerkleDAG machinery against
real temp-directory project files (no mocking at the merkle layer) so these
tests can actually catch the bug this module was extracted to fix. Mocking
SnapshotManager wholesale here would only prove a Mock's return value gets
copied into a dict -- the same failure mode documented as defect 1 in
docs/adr/0058-index-freshness-verdict.md. Only the storage *location* is
redirected to a scratch directory, to avoid touching the developer's real
~/.claude_code_search.

Lives under tests/unit/mcp_server/, matching mcp_server/index_freshness.py's
placement -- the module depends on mcp_server.storage_manager, which search/
may not import at runtime (ADR-0004).
"""

from unittest.mock import patch

import pytest

from mcp_server.index_freshness import build_change_detector, compute_index_freshness
from merkle.snapshot_manager import SnapshotManager


@pytest.fixture
def project(tmp_path):
    """A real, minimal project directory with two source files."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("# main")
    (project_dir / "util.py").write_text("# util")
    return project_dir


@pytest.fixture
def scratch_snapshot_manager(tmp_path):
    """A real SnapshotManager rooted in a scratch dir, never the real one."""
    return SnapshotManager(tmp_path / "merkle_storage")


@pytest.fixture(autouse=True)
def _redirect_storage(scratch_snapshot_manager, tmp_path):
    """Redirect index_freshness's module-level lookups off real storage.

    ``SnapshotManager()`` (no-args) inside build_change_detector must resolve
    to the scratch instance, and get_project_storage_dir must never touch
    the real ~/.claude_code_search -- project_info.json simply won't exist
    under the scratch path, which is fine: build_change_detector degrades to
    no include/exclude filters, same as a project registered without any.
    """
    with (
        patch(
            "mcp_server.index_freshness.SnapshotManager",
            return_value=scratch_snapshot_manager,
        ),
        patch(
            "mcp_server.index_freshness.get_project_storage_dir",
            return_value=tmp_path / "project_storage",
        ),
    ):
        yield


def test_compute_index_freshness_returns_none_without_snapshot(project):
    """Never indexed -- must be None, distinct from a False (stale) verdict."""
    result = compute_index_freshness(str(project))

    assert result is None


def test_compute_index_freshness_true_when_unchanged(project, scratch_snapshot_manager):
    """A snapshot saved against the current tree, with nothing touched since,
    must report current with zero pending changes -- the exact case the
    original bug misreported as stale from a registration timestamp alone.
    """
    detector, snapshot_mgr = build_change_detector(str(project))
    changes, current_dag = detector.detect_changes_from_snapshot(str(project))
    snapshot_mgr.save_snapshot(current_dag)

    result = compute_index_freshness(str(project))

    assert result == {
        "index_is_current": True,
        "pending_changes": {"added": 0, "modified": 0, "removed": 0},
    }


def test_compute_index_freshness_false_when_file_modified(
    project, scratch_snapshot_manager
):
    """Editing one file after the snapshot was taken must flip the verdict to
    not-current and report exactly one modified file.
    """
    detector, snapshot_mgr = build_change_detector(str(project))
    changes, current_dag = detector.detect_changes_from_snapshot(str(project))
    snapshot_mgr.save_snapshot(current_dag)

    (project / "main.py").write_text("# main, edited")

    result = compute_index_freshness(str(project))

    assert result == {
        "index_is_current": False,
        "pending_changes": {"added": 0, "modified": 1, "removed": 0},
    }


def test_build_change_detector_is_constructed_with_supported_extensions(project):
    """Guard against the false-positive trap this module exists to close:
    without supported_extensions, non-code files fall onto content hashing
    that doesn't match the snapshot's stat-based scheme, and an untouched
    tree reports every file as changed. See ADR-0058's measured numbers
    (supported_extensions=None: changed=True on an untouched tree).
    """
    detector, _snapshot_mgr = build_change_detector(str(project))

    assert detector.supported_extensions
    assert ".py" in detector.supported_extensions
