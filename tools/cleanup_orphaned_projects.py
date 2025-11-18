#!/usr/bin/env python3
"""
Clean up orphaned test projects without project_info.json

Orphaned projects are those created manually or by test scripts
that don't have the proper project_info.json file and won't appear
in the Project Management menu.
"""

import gc
import shutil
import time
from pathlib import Path


def find_orphaned_projects():
    """Find project directories without project_info.json."""
    storage_dir = Path.home() / ".claude_code_search" / "projects"

    if not storage_dir.exists():
        print("No projects directory found")
        return []

    orphaned = []
    for project_dir in storage_dir.iterdir():
        if project_dir.is_dir():
            info_file = project_dir / "project_info.json"
            if not info_file.exists():
                orphaned.append(project_dir)

    return orphaned


def get_project_size(project_dir):
    """Calculate total size of project directory in MB."""
    total_size = 0
    try:
        for file in project_dir.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
    except Exception:
        pass
    return total_size / (1024 * 1024)  # Convert to MB


def cleanup_project(project_dir):
    """Remove a project directory safely."""
    try:
        # Force garbage collection to release any handles
        gc.collect()
        time.sleep(0.5)

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
    print("=" * 70)
    print("ORPHANED PROJECTS CLEANUP")
    print("=" * 70)
    print()
    print("Scanning for projects without project_info.json...")
    print()

    orphaned = find_orphaned_projects()

    if not orphaned:
        print("No orphaned projects found.")
        print()
        print("All projects have proper project_info.json files.")
        return

    print(f"Found {len(orphaned)} orphaned project(s):")
    print()

    # Display orphaned projects
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

    deleted_count = 0
    failed_count = 0

    for project_dir in orphaned:
        print(f"Removing: {project_dir.name}...", end=" ")
        success, message = cleanup_project(project_dir)

        if success:
            print(f"OK ({message})")
            deleted_count += 1
        else:
            print(f"FAILED ({message})")
            failed_count += 1

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
