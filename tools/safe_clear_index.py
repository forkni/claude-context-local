"""Path-safe rmtree for project indexes.

Refuses to delete anything outside the storage 'projects/' tree.
Invoked from start_mcp_server.cmd instead of inline python -c snippets
so that every rmtree is subject to path validation regardless of how
PROJECT_HASH arrives.
"""

import argparse
import gc
import shutil
import sys
import time

from mcp_server.storage_manager import (
    _PROJECT_MARKERS,
    STORAGE_SENTINEL,
    get_storage_dir,
)


def safe_rmtree_project(project_hash: str, retry: bool = False) -> int:
    """Delete one project index directory, with strict path validation.

    Returns 0 on success, non-zero on refusal or failure.
    """
    stripped = project_hash.strip() if project_hash else ""
    if not stripped or stripped in (".", ".."):
        print(
            f"[SAFE-RMTREE] REFUSED: empty or relative project_hash: {project_hash!r}",
            file=sys.stderr,
        )
        return 2

    storage = get_storage_dir().resolve()
    projects_root = (storage / "projects").resolve()
    target = (projects_root / stripped).resolve()

    if target in (projects_root, storage):
        print(
            f"[SAFE-RMTREE] REFUSED: target equals storage or projects root: {target}",
            file=sys.stderr,
        )
        return 3

    try:
        target.relative_to(projects_root)
    except ValueError:
        print(
            f"[SAFE-RMTREE] REFUSED: target outside projects root: {target}",
            file=sys.stderr,
        )
        return 4

    if not target.name or "_" not in target.name:
        print(
            f"[SAFE-RMTREE] REFUSED: target name not a valid project dir: {target.name!r}",
            file=sys.stderr,
        )
        return 5

    if not target.exists():
        print("Index: cleared")
        return 0

    gc.collect()
    time.sleep(0.5 if not retry else 1.0)
    shutil.rmtree(target, ignore_errors=retry)

    if target.exists() and not retry:
        return 1

    print("Index: cleared")
    return 0


def safe_rmtree_all() -> int:
    """Delete all project index directories, recreating the empty projects/ dir."""
    storage = get_storage_dir().resolve()
    projects_root = (storage / "projects").resolve()

    if projects_root == storage:
        print(
            "[SAFE-RMTREE] REFUSED: projects_root equals storage root",
            file=sys.stderr,
        )
        return 3

    # Verify storage looks like a legitimate storage root (sentinel file present)
    if not (storage / STORAGE_SENTINEL).exists():
        print(
            "[SAFE-RMTREE] REFUSED: storage root is missing sentinel marker "
            f"({STORAGE_SENTINEL}); refusing to clear a directory that was not "
            "initialized by get_storage_dir()",
            file=sys.stderr,
        )
        return 6

    # Verify storage is not inside a project source tree
    for marker in _PROJECT_MARKERS:
        if (storage / marker).exists():
            print(
                f"[SAFE-RMTREE] REFUSED: storage contains project marker '{marker}'; "
                "storage must not be inside a source tree",
                file=sys.stderr,
            )
            return 7

    if projects_root.exists():
        gc.collect()
        time.sleep(0.5)
        shutil.rmtree(projects_root, ignore_errors=True)

    projects_root.mkdir(exist_ok=True)
    print("[OK] All project indices cleared")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Path-safe index rmtree helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("project", help="Delete one project index")
    p.add_argument("hash", help="Project directory name (hash slug)")
    p.add_argument("--retry", action="store_true", help="Ignore errors (retry pass)")
    sub.add_parser("all", help="Delete all project indices")
    args = ap.parse_args()

    if args.cmd == "project":
        sys.exit(safe_rmtree_project(args.hash, retry=args.retry))
    elif args.cmd == "all":
        sys.exit(safe_rmtree_all())
