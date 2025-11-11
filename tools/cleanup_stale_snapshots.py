#!/usr/bin/env python3
"""Cleanup utility for stale Merkle snapshots.

This script identifies and removes Merkle snapshots for projects that no longer
have corresponding indices in the projects directory.

Use cases:
- Clean up after deleting/moving projects
- Remove snapshots from old model dimensions
- Recover from orphaned snapshot issues
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from merkle.snapshot_manager import SnapshotManager


def get_indexed_projects() -> Dict[str, Set[str]]:
    """Get all currently indexed projects and their dimensions.

    Returns:
        Dict mapping project_id to set of dimensions (e.g., {'abc123': {'768d', '1024d'}})
    """
    storage_dir = Path.home() / ".claude_code_search" / "projects"
    indexed = {}

    if not storage_dir.exists():
        return indexed

    # Parse directory names: {project_name}_{project_id}_{dimension}d
    for project_dir in storage_dir.iterdir():
        if not project_dir.is_dir():
            continue

        parts = project_dir.name.split("_")
        if len(parts) < 2:
            continue

        # Extract project_id and dimension
        # Format: name_id_dimD or name_id (old format)
        if parts[-1].endswith("d") and parts[-1][:-1].isdigit():
            dimension = parts[-1]
            project_id = parts[-2]
        else:
            # Old format without dimension
            project_id = parts[-1]
            dimension = "unknown"

        if project_id not in indexed:
            indexed[project_id] = set()
        indexed[project_id].add(dimension)

    return indexed


def find_stale_snapshots() -> Dict[str, List[Path]]:
    """Find Merkle snapshots that don't have corresponding project indices.

    Returns:
        Dict mapping project_id to list of orphaned snapshot/metadata files
    """
    snapshot_manager = SnapshotManager()
    merkle_dir = snapshot_manager.storage_dir

    if not merkle_dir.exists():
        return {}

    # Get currently indexed projects
    indexed_projects = get_indexed_projects()
    indexed_ids = set(indexed_projects.keys())

    # Find all snapshot files
    stale = {}
    for snapshot_file in merkle_dir.glob("*_snapshot.json"):
        # Extract project_id from filename: {project_id}_{dimension}d_snapshot.json
        name = snapshot_file.stem  # Remove .json
        parts = name.split("_")

        if len(parts) < 3:
            continue

        project_id = parts[0]
        dimension = parts[1]  # e.g., "1024d"

        # Check if project exists with this dimension
        is_orphaned = False
        if project_id not in indexed_ids:
            is_orphaned = True
        elif dimension not in indexed_projects.get(project_id, set()):
            is_orphaned = True

        if is_orphaned:
            if project_id not in stale:
                stale[project_id] = []

            stale[project_id].append(snapshot_file)

            # Also include corresponding metadata file
            metadata_file = snapshot_file.parent / f"{project_id}_{dimension}_metadata.json"
            if metadata_file.exists():
                stale[project_id].append(metadata_file)

    return stale


def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def main():
    """Main cleanup utility."""
    print("=" * 70)
    print("Merkle Snapshot Cleanup Utility")
    print("=" * 70)
    print()

    # Find stale snapshots
    print("Scanning for stale snapshots...")
    stale_snapshots = find_stale_snapshots()

    if not stale_snapshots:
        print("✓ No stale snapshots found!")
        print()
        print("All Merkle snapshots have corresponding project indices.")
        return

    # Display findings
    total_files = sum(len(files) for files in stale_snapshots.values())
    total_size = sum(
        sum(f.stat().st_size for f in files) for files in stale_snapshots.values()
    )

    print(f"Found {total_files} stale snapshot files ({format_size(total_size)})")
    print()

    print("Stale snapshots by project:")
    print("-" * 70)

    for project_id, files in sorted(stale_snapshots.items()):
        project_size = sum(f.stat().st_size for f in files)
        dimensions = set()
        for f in files:
            parts = f.stem.split("_")
            if len(parts) >= 2:
                dimensions.add(parts[1])

        print(f"\nProject ID: {project_id}")
        print(f"  Dimensions: {', '.join(sorted(dimensions))}")
        print(f"  Files: {len(files)}")
        print(f"  Size: {format_size(project_size)}")
        for f in files:
            print(f"    - {f.name} ({format_size(f.stat().st_size)})")

    print()
    print("-" * 70)
    print()

    # Confirm deletion
    response = input("Delete all stale snapshots? [y/N]: ").strip().lower()

    if response not in ["y", "yes"]:
        print("Cancelled. No files were deleted.")
        return

    # Delete files
    print()
    print("Deleting stale snapshots...")
    deleted_count = 0
    failed_count = 0

    for project_id, files in stale_snapshots.items():
        for f in files:
            try:
                f.unlink()
                deleted_count += 1
                print(f"  ✓ Deleted: {f.name}")
            except Exception as e:
                failed_count += 1
                print(f"  ✗ Failed to delete {f.name}: {e}")

    print()
    print("=" * 70)
    print(f"Cleanup complete!")
    print(f"  Deleted: {deleted_count} files")
    if failed_count > 0:
        print(f"  Failed: {failed_count} files")
    print(f"  Recovered: {format_size(total_size)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
