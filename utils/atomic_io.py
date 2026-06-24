"""Atomic JSON file writes to prevent data loss on partial writes."""

import json
import os
from pathlib import Path


def write_json_atomic(
    path: "str | Path",
    obj: object,
    *,
    indent: int = 2,
    validate: bool = True,
) -> None:
    """Write *obj* as JSON to *path* atomically (write-to-tmp, then os.replace).

    Prevents a corrupt or incomplete file being left behind when the process
    crashes or the disk fills mid-write.  The original file is never touched
    until the new content has been fully written and (optionally) validated.

    Args:
        path:     Destination path (str or Path).
        obj:      JSON-serializable object.
        indent:   JSON indentation level (default 2, matches existing codebase style).
        validate: If True (default), re-read and json.load the temp file before
                  replacing the original — catches truncated / corrupt writes.

    Raises:
        Any exception raised by json.dumps, file I/O, json.load (validation),
        or os.replace.  The temp file is always cleaned up on failure.
    """
    path = Path(path)
    tmp = Path(str(path) + ".tmp")
    try:
        # Serialize BEFORE opening the file so a non-serializable object never
        # truncates the destination.
        serialized = json.dumps(obj, indent=indent)

        with open(tmp, "w", encoding="utf-8") as f:
            f.write(serialized)

        if validate:
            with open(tmp, encoding="utf-8") as f:
                json.load(f)  # Verify valid JSON was written

        # Atomic rename — safe on the same filesystem (POSIX) and best-effort on
        # Windows (os.replace replaces atomically on NTFS when src/dst are on the
        # same volume).
        os.replace(tmp, path)

    except Exception:
        tmp.unlink(missing_ok=True)
        raise
