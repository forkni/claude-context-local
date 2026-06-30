"""Unit tests for SnapshotManager.resolve_project_id (T1: hash-owner single-owner fix)."""

import pytest

from merkle.snapshot_manager import SnapshotManager
from search.filters import compute_drive_agnostic_hash, compute_legacy_hash


class TestResolveProjectId:
    """Tests for the resolve_project_id owner method.

    Derives expected ids from the canonical filter functions so the assertions are
    cross-platform: on Linux drive-agnostic == legacy (both branches pass); on
    Windows they differ (each branch exercises a distinct code path).
    """

    @pytest.fixture
    def sm(self, tmp_path):
        return SnapshotManager(storage_dir=tmp_path / "merkle")

    @pytest.fixture
    def project_path(self, tmp_path):
        """A real resolvable path."""
        p = tmp_path / "my_project"
        p.mkdir()
        return str(p)

    def test_no_short_hash_returns_drive_agnostic(self, sm, project_path):
        """Default (no short_hash) always returns the drive-agnostic id."""
        expected = compute_drive_agnostic_hash(project_path, length=32)
        assert sm.resolve_project_id(project_path) == expected

    def test_agnostic_prefix_returns_agnostic(self, sm, project_path):
        """v2 prefix (drive-agnostic short hash) → returns drive-agnostic 32-char id."""
        agn = compute_drive_agnostic_hash(project_path, length=32)
        assert sm.resolve_project_id(project_path, agn[:8]) == agn

    def test_legacy_prefix_returns_legacy(self, sm, project_path):
        """v1 prefix (legacy short hash) → returns legacy 32-char id.

        On Linux agn == leg so this is the same as the agnostic case;
        on Windows they differ and the legacy branch is exercised.
        """
        leg = compute_legacy_hash(project_path, length=32)
        result = sm.resolve_project_id(project_path, leg[:8])
        # Must return *some* 32-char id that starts with leg[:8]
        assert result is not None
        assert result[:8] == leg[:8]
        assert len(result) == 32

    def test_bogus_prefix_returns_none(self, sm, project_path):
        """Neither scheme matches → None."""
        assert sm.resolve_project_id(project_path, "zzzzzzzz") is None

    def test_returns_32_chars_without_short_hash(self, sm, project_path):
        result = sm.resolve_project_id(project_path)
        assert len(result) == 32  # type: ignore[arg-type]

    def test_short_hash_longer_than_8(self, sm, project_path):
        """resolve_project_id accepts a longer prefix (uses len(short_hash) chars)."""
        agn = compute_drive_agnostic_hash(project_path, length=32)
        # Use first 16 chars as short_hash
        assert sm.resolve_project_id(project_path, agn[:16]) == agn
