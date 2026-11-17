"""Build the PermissionError that Windows raises for a file held open elsewhere.

Production code tells a real lock (sharing violation, error 32; lock
violation, error 33) from any other PermissionError by its ``winerror``. A
bare ``PermissionError("[WinError 32] ...")`` carries no ``winerror`` and would
read as an ordinary permission failure, so tests that simulate a lock build the
error here. Setting the attribute by hand makes the same test pass on a
non-Windows platform, where ``OSError`` never sets it itself.
"""

from __future__ import annotations


_IN_USE_TEXT = (
    "The process cannot access the file because it is being used by another process"
)


def lock_violation(path: str | None = None, *, winerror: int = 32) -> PermissionError:
    """Return a PermissionError reporting Windows error *winerror* for *path*.

    Args:
        path: File name the error carries (``exc.filename``), or None.
        winerror: 32 (sharing violation) or 33 (lock violation) read as a lock.
            Any other value, such as 5 (access denied), reads as a plain
            permission failure.
    """
    error = PermissionError(13, _IN_USE_TEXT, path)
    error.winerror = winerror
    return error
