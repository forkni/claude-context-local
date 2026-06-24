"""Unit tests for utils/atomic_io.py.

Tests cover:
- Happy path: file written with correct content.
- Temp file cleaned up when write fails mid-way.
- Temp file cleaned up when os.replace fails.
- Validation catches a corrupt .tmp and cleans up.
- validate=False skips the re-read step.
- SnapshotManager.save_snapshot leaves the caller's metadata dict unmutated.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.atomic_io import write_json_atomic


class TestWriteJsonAtomic:
    """Tests for write_json_atomic helper."""

    def test_happy_path(self, tmp_path):
        """Writes valid JSON and replaces destination atomically."""
        dest = tmp_path / "out.json"
        obj = {"key": "value", "num": 42}

        write_json_atomic(dest, obj)

        assert dest.exists()
        with open(dest, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == obj
        # Temp file must be gone after success
        assert not Path(str(dest) + ".tmp").exists()

    def test_accepts_str_path(self, tmp_path):
        """Accepts a plain string path as well as a Path object."""
        dest = str(tmp_path / "out.json")
        write_json_atomic(dest, {"a": 1})
        assert json.loads(Path(dest).read_text(encoding="utf-8")) == {"a": 1}

    def test_tmp_cleaned_up_on_write_failure(self, tmp_path):
        """Temp file is removed when the write itself raises."""
        dest = tmp_path / "out.json"
        tmp = Path(str(dest) + ".tmp")

        with (
            patch("builtins.open", side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            write_json_atomic(dest, {"x": 1})

        assert not tmp.exists()
        assert not dest.exists()

    def test_tmp_cleaned_up_on_replace_failure(self, tmp_path):
        """Temp file is removed when os.replace raises."""
        dest = tmp_path / "out.json"
        tmp = Path(str(dest) + ".tmp")

        with (
            patch("utils.atomic_io.os.replace", side_effect=OSError("replace failed")),
            pytest.raises(OSError, match="replace failed"),
        ):
            write_json_atomic(dest, {"x": 1})

        assert not tmp.exists()

    def test_validation_catches_corrupt_tmp(self, tmp_path):
        """When validate=True, a corrupt .tmp raises and is cleaned up."""
        dest = tmp_path / "out.json"
        tmp = Path(str(dest) + ".tmp")

        # Simulate json.load failing on the re-read
        original_open = open

        call_count = [0]

        def patched_open(path, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # second open = validation read
                raise json.JSONDecodeError("invalid", "", 0)
            return original_open(path, *args, **kwargs)

        with (
            patch("builtins.open", side_effect=patched_open),
            pytest.raises(json.JSONDecodeError),
        ):
            write_json_atomic(dest, {"x": 1}, validate=True)

        assert not tmp.exists()

    def test_validate_false_skips_reread(self, tmp_path):
        """validate=False writes without the extra json.load check."""
        dest = tmp_path / "out.json"
        obj = [1, 2, 3]

        open_calls = []
        original_open = open

        def tracking_open(path, *args, **kwargs):
            open_calls.append(path)
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=tracking_open):
            write_json_atomic(dest, obj, validate=False)

        # Only one open call (the write); no validation re-read
        assert len(open_calls) == 1
        assert json.loads(dest.read_text(encoding="utf-8")) == obj

    def test_original_preserved_when_write_fails(self, tmp_path):
        """Original file is not clobbered when the write fails."""
        dest = tmp_path / "out.json"
        original = {"original": True}
        dest.write_text(json.dumps(original), encoding="utf-8")

        with (
            patch("utils.atomic_io.os.replace", side_effect=OSError("fail")),
            pytest.raises(OSError),
        ):
            write_json_atomic(dest, {"new": True})

        # Original content must be intact
        assert json.loads(dest.read_text(encoding="utf-8")) == original

    def test_non_serializable_object_raises_before_open(self, tmp_path):
        """A non-JSON-serializable object raises TypeError before touching any file."""
        dest = tmp_path / "out.json"
        tmp = Path(str(dest) + ".tmp")

        with pytest.raises(TypeError):
            write_json_atomic(dest, object())  # plain object() is not serializable

        assert not dest.exists()
        assert not tmp.exists()

    def test_indent_respected(self, tmp_path):
        """The indent parameter is forwarded to json.dumps."""
        dest = tmp_path / "out.json"
        write_json_atomic(dest, {"a": 1}, indent=4)
        content = dest.read_text(encoding="utf-8")
        # With indent=4, top-level key should be indented 4 spaces
        assert "    " in content


class TestSnapshotManagerCallerDictUnmutated:
    """Assert save_snapshot does not mutate the caller's metadata dict."""

    def test_metadata_not_mutated(self, tmp_path):
        """Caller's metadata dict must be unchanged after save_snapshot."""
        from merkle.merkle_dag import MerkleDAG
        from merkle.snapshot_manager import SnapshotManager

        # Create a real file so build() has something to hash
        (tmp_path / "file.txt").write_text("hello")
        dag = MerkleDAG(str(tmp_path))
        dag.build()

        manager = SnapshotManager(storage_dir=tmp_path / "snapshots")

        original_metadata = {"custom_key": "custom_value"}
        caller_dict = dict(original_metadata)  # copy to compare later

        manager.save_snapshot(dag, caller_dict)

        # The dict passed in must be unchanged
        assert caller_dict == original_metadata
        # Specifically, the injected keys must NOT be present
        for injected_key in (
            "project_path",
            "project_id",
            "last_snapshot",
            "file_count",
            "root_hash",
        ):
            assert injected_key not in caller_dict
