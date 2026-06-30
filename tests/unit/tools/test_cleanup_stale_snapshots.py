"""Regression tests for cleanup_stale_snapshots — T1 bug fix.

Before the fix: _get_full_project_id used a legacy-only md5(resolve(path)), which
mismatches the drive-agnostic (v2) short hash stored in the project dir name on
Windows. This caused get_indexed_projects() to drop all v2 projects, making
find_stale_snapshots() flag their live snapshots as orphaned (destructive false-positive).

After the fix: _get_full_project_id delegates to SnapshotManager.resolve_project_id
which tries drive-agnostic first then legacy, so v2 projects are recognised correctly.
"""

import json
import sys
from pathlib import Path

import pytest


# Ensure project root is importable when running tests from any working directory.
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from search.filters import compute_drive_agnostic_hash  # noqa: E402

# Import after path fixup
from tools.cleanup_stale_snapshots import (  # noqa: E402
    _get_full_project_id,
    find_stale_snapshots,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MODEL_SLUG = "bge-m3"
DIMENSION = "1024d"


def _build_v2_project(
    storage_root: Path,
    project_path: Path,
    *,
    model_slug: str = MODEL_SLUG,
    dimension: str = DIMENSION,
) -> tuple[Path, str, str]:
    """Create an on-disk v2 project dir + matching merkle snapshot.

    Returns (project_dir, agn8, agn32).
    """
    p_str = str(project_path.resolve())
    agn32 = compute_drive_agnostic_hash(p_str, length=32)
    agn8 = agn32[:8]
    name = project_path.name

    # projects/{name}_{agn8}_{model}_{dim}/project_info.json
    project_dir = storage_root / "projects" / f"{name}_{agn8}_{model_slug}_{dimension}"
    project_dir.mkdir(parents=True, exist_ok=True)
    info = {
        "project_name": name,
        "project_path": p_str,
        "project_hash": agn8,
        "hash_version": 2,
    }
    (project_dir / "project_info.json").write_text(json.dumps(info), encoding="utf-8")

    # merkle/{agn32}_{model}_{dim}_snapshot.json
    merkle_dir = storage_root / "merkle"
    merkle_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = merkle_dir / f"{agn32}_{model_slug}_{dimension}_snapshot.json"
    snapshot_file.write_text(json.dumps({"version": 1}), encoding="utf-8")

    return project_dir, agn8, agn32


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetFullProjectId:
    """Unit tests for _get_full_project_id routing."""

    def test_v2_project_returns_drive_agnostic_id(self, tmp_path, monkeypatch):
        """_get_full_project_id returns the drive-agnostic 32-char id for a v2 project."""
        monkeypatch.setenv("CODE_SEARCH_STORAGE", str(tmp_path))
        storage = tmp_path

        project_path = tmp_path / "my_project"
        project_path.mkdir()
        _, agn8, agn32 = _build_v2_project(storage, project_path)

        project_dir = (
            storage / "projects" / f"my_project_{agn8}_{MODEL_SLUG}_{DIMENSION}"
        )
        result = _get_full_project_id(project_dir, agn8)
        assert result == agn32

    def test_missing_info_file_returns_none(self, tmp_path):
        project_dir = tmp_path / "ghost_project"
        project_dir.mkdir()
        assert _get_full_project_id(project_dir, "abcd1234") is None

    def test_bogus_short_hash_returns_none(self, tmp_path):
        """When neither hash scheme matches the short_hash, returns None."""
        project_path = tmp_path / "some_project"
        project_path.mkdir()
        _, agn8, _ = _build_v2_project(tmp_path, project_path)
        project_dir = (
            tmp_path / "projects" / f"some_project_{agn8}_{MODEL_SLUG}_{DIMENSION}"
        )
        assert _get_full_project_id(project_dir, "zzzzzzzz") is None


class TestFindStaleSnapshots:
    """Regression tests for the T1 correctness bug.

    The core assertion: a live v2 project's snapshot is NOT flagged stale.
    Before the fix this assertion failed on Windows because the legacy-only hash
    mismatched the drive-agnostic short_hash in the dir name.
    """

    @pytest.fixture(autouse=True)
    def _set_storage(self, tmp_path, monkeypatch):
        """Point CODE_SEARCH_STORAGE at tmp_path for each test."""
        monkeypatch.setenv("CODE_SEARCH_STORAGE", str(tmp_path))
        self.storage = tmp_path

    def test_v2_project_snapshot_is_not_stale(self, tmp_path):
        """The key regression: a v2 project's live snapshot is NOT orphaned."""
        project_path = tmp_path / "live_project"
        project_path.mkdir()
        _build_v2_project(self.storage, project_path)

        stale = find_stale_snapshots()
        assert stale == {}, (
            f"find_stale_snapshots() falsely flagged v2 project as stale: {stale}"
        )

    def test_genuinely_missing_project_is_stale(self, tmp_path):
        """A snapshot with no matching project dir IS correctly flagged."""
        # Write a dangling snapshot (no matching project dir)
        agn32 = "a" * 32
        merkle_dir = self.storage / "merkle"
        merkle_dir.mkdir(parents=True, exist_ok=True)
        dangling = merkle_dir / f"{agn32}_{MODEL_SLUG}_{DIMENSION}_snapshot.json"
        dangling.write_text("{}", encoding="utf-8")
        # No corresponding project dir → should appear in stale
        stale = find_stale_snapshots()
        assert agn32 in stale

    def test_multiple_v2_projects_none_stale(self, tmp_path):
        """Multiple v2 projects — none of their snapshots are flagged."""
        for name in ("alpha", "beta", "gamma"):
            p = tmp_path / name
            p.mkdir()
            _build_v2_project(self.storage, p)

        stale = find_stale_snapshots()
        assert stale == {}

    def test_mix_live_and_dangling(self, tmp_path):
        """Live v2 project not flagged; dangling snapshot is."""
        # Live
        project_path = tmp_path / "live"
        project_path.mkdir()
        _build_v2_project(self.storage, project_path)

        # Dangling
        agn32 = "b" * 32
        merkle_dir = self.storage / "merkle"
        merkle_dir.mkdir(parents=True, exist_ok=True)
        dangling = merkle_dir / f"{agn32}_{MODEL_SLUG}_{DIMENSION}_snapshot.json"
        dangling.write_text("{}", encoding="utf-8")

        stale = find_stale_snapshots()
        assert agn32 in stale
        # The live project's 32-char id must NOT be in stale
        p_str = str(project_path.resolve())
        live_agn32 = compute_drive_agnostic_hash(p_str, length=32)
        assert live_agn32 not in stale
