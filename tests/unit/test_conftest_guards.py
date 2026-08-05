"""Tests for the session-wide write-tracking guards installed by tests/conftest.py.

_install_real_storage_write_ledger (autouse, session-scoped) wraps builtins.open,
os.replace, os.rename, and Path.mkdir for the whole test session to attribute any
write under the real ~/.claude_code_search to its call site. Because it patches
builtins.open globally, every write-mode open() in the process — including ones
made by the standard library, not just this repo's code — passes through
_record_if_real_storage. These tests cover call shapes that guard has previously
mishandled.
"""

import os

import pytest


def test_write_ledger_tolerates_integer_file_descriptor(tmp_path):
    """open(fd, "wb") on an int must not raise inside the wrapped open().

    multiprocessing's Windows spawn implementation opens the child process's
    pipe via `open(wfd, "wb", closefd=True)`, where wfd is a raw integer file
    descriptor, not a path. Before this test was added, the wrapped open()
    unconditionally called Path(target).resolve() on the fd, raising
    `TypeError: expected str, bytes or os.PathLike object, not int` — which
    escaped ProcessPoolExecutor.submit() and broke every process-pool resolver
    (pyan, libcst) under pytest on Windows, both locally and in CI (nightly run
    30986597353, job 92242674117).
    """
    target = tmp_path / "child_pipe.bin"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT)
    with open(fd, "wb", closefd=True) as fh:  # goes through the session-wide wrapper
        fh.write(b"x")

    assert target.read_bytes() == b"x"


def test_write_ledger_still_records_real_path_writes(tmp_path, monkeypatch):
    """Sanity check: the isinstance guard must not swallow legitimate path writes.

    Redirects the real-storage root to tmp_path so a normal path-based write is
    still recorded by the ledger, proving the fd guard only skips non-path
    targets rather than disabling the ledger outright.
    """
    import tests.conftest as conftest_module

    monkeypatch.setattr(conftest_module, "_REAL_STORAGE_ROOT", tmp_path)
    conftest_module._real_storage_write_ledger.clear()

    target = tmp_path / "some_file.json"
    with open(target, "w", encoding="utf-8") as fh:
        fh.write("{}")

    recorded_paths = [
        entry["path"] for entry in conftest_module._real_storage_write_ledger
    ]
    assert str(target.resolve()) in recorded_paths

    conftest_module._real_storage_write_ledger.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
