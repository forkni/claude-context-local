#!/usr/bin/env python3
"""
Clean up orphaned and stale test projects

Removes two types of projects:
1. Orphaned: Projects without project_info.json
2. Stale: Projects with project_info.json where the project_path no longer exists
"""

import contextlib
import gc
import json
import shutil
import time
from pathlib import Path


def find_orphaned_projects():
    """Find project directories without project_info.json or with non-existent project_path.

    Returns:
        List of Path objects for orphaned project directories.
    """
    storage_dir = Path.home() / ".claude_code_search" / "projects"

    if not storage_dir.exists():
        print("No projects directory found")
        return []

    orphaned = []
    for project_dir in storage_dir.iterdir():
        if project_dir.is_dir():
            info_file = project_dir / "project_info.json"

            # Case 1: No project_info.json (truly orphaned)
            if not info_file.exists():
                orphaned.append(project_dir)
                continue

            # Case 2: Has project_info.json but project_path doesn't exist (stale)
            try:
                with open(info_file, encoding="utf-8") as f:
                    project_info = json.load(f)
                    project_path = project_info.get("project_path", "")

                    if project_path and not Path(project_path).exists():
                        orphaned.append(project_dir)
            except json.JSONDecodeError:
                # If we can't read project_info.json, treat as orphaned
                orphaned.append(project_dir)

    return orphaned


def get_project_size(project_dir):
    """Calculate total size of project directory in MB.

    Args:
        project_dir: Path to the project directory to measure.

    Returns:
        Total size in megabytes as a float.
    """
    total_size = 0
    try:
        for file in project_dir.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
    except OSError:
        pass
    return total_size / (1024 * 1024)  # Convert to MB


def _get_full_project_id(project_dir: Path) -> str | None:
    """Get full 32-char project_id from project_info.json.

    Args:
        project_dir: Path to project directory

    Returns:
        Full 32-char MD5 hash project_id, or None if not found
    """
    import hashlib

    info_file = project_dir / "project_info.json"
    if not info_file.exists():
        return None

    try:
        with open(info_file, encoding="utf-8") as f:
            project_info = json.load(f)
            project_path = project_info.get("project_path", "")
            if project_path:
                # Compute full 32-char project_id from normalized path
                normalized = str(Path(project_path).resolve())
                return hashlib.md5(normalized.encode()).hexdigest()
    except json.JSONDecodeError:
        pass

    return None


def cleanup_project(project_dir):
    """Remove a project directory and its merkle snapshots safely.

    Args:
        project_dir: Path to the project directory to remove.

    Returns:
        Tuple of (success: bool, message: str) indicating cleanup result.
    """
    try:
        # Get full 32-char project_id from project_info.json BEFORE deleting
        full_project_id = _get_full_project_id(project_dir)

        # Force garbage collection to release any handles
        gc.collect()
        time.sleep(0.5)

        # Remove merkle snapshots using full 32-char project_id
        if full_project_id:
            merkle_dir = Path.home() / ".claude_code_search" / "merkle"
            if merkle_dir.exists():
                # Match files like: {project_id}_{model}_{dim}d_snapshot.json
                for merkle_file in merkle_dir.glob(f"{full_project_id}_*"):
                    # Ignore errors removing merkle files
                    with contextlib.suppress(OSError):
                        merkle_file.unlink()

        # Remove directory
        shutil.rmtree(project_dir, ignore_errors=False)
        return True, "Success"
    except PermissionError as e:
        # Try with ignore_errors if permission denied
        shutil.rmtree(project_dir, ignore_errors=True)
        if not project_dir.exists():
            return True, "Success (with ignore_errors)"
        else:
            return False, f"Permission denied: {e}"
    except Exception as e:
        return False, str(e)


def main():
    """Entry point for orphaned projects cleanup utility."""
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup orphaned test projects")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-confirm deletion (for CI/testing, silent mode)",
    )
    args = parser.parse_args()

    # Only show banner in interactive mode
    if not args.auto:
        print("=" * 70)
        print("ORPHANED PROJECTS CLEANUP")
        print("=" * 70)
        print()
        print("Scanning for projects without project_info.json...")
        print()

    orphaned = find_orphaned_projects()

    if not orphaned:
        if not args.auto:
            print("No orphaned projects found.")
            print()
            print("All projects have proper project_info.json files.")
        return

    # Display orphaned projects in interactive mode only
    if not args.auto:
        print(f"Found {len(orphaned)} orphaned project(s):")
        print()

        for i, project_dir in enumerate(orphaned, 1):
            size_mb = get_project_size(project_dir)
            print(f"{i}. {project_dir.name}")
            print(f"   Size: {size_mb:.2f} MB")
            print(f"   Path: {project_dir}")
            print()

        # Ask for confirmation
        print("=" * 70)
        print()
        choice = input("Delete all orphaned projects? (y/N): ").strip().lower()

        if choice != "y":
            print("Cancelled.")
            return

        # Delete orphaned projects
        print()
        print("Deleting orphaned projects...")
        print()

    # Delete orphaned projects (silent in auto mode)
    deleted_count = 0
    failed_count = 0

    for project_dir in orphaned:
        if not args.auto:
            print(f"Removing: {project_dir.name}...", end=" ")

        success, message = cleanup_project(project_dir)

        if success:
            if not args.auto:
                print(f"OK ({message})")
            deleted_count += 1
        else:
            if not args.auto:
                print(f"FAILED ({message})")
            failed_count += 1

    # Summary in interactive mode only
    if not args.auto:
        print()
        print("=" * 70)
        print("CLEANUP SUMMARY")
        print("=" * 70)
        print(f"Deleted: {deleted_count}")
        print(f"Failed: {failed_count}")
        print()

        if failed_count > 0:
            print("Note: Some projects could not be deleted due to file locks.")
            print("      Close all Python processes and try again.")
            print()


if __name__ == "__main__":
    main()
