#!/usr/bin/env python3
"""Cleanup utility for stale Merkle snapshots.

This script identifies and removes Merkle snapshots for projects that no longer
have corresponding indices in the projects directory.

Use cases:
- Clean up after deleting/moving projects
- Remove snapshots from old model dimensions
- Recover from orphaned snapshot issues
"""

import sys
from pathlib import Path


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from merkle.snapshot_manager import SnapshotManager  # noqa: E402


def _get_full_project_id(project_dir: Path, short_hash: str) -> str | None:
    """Get full 32-char project_id from project directory.

    Tries to extract project path from project_info.json and compute full MD5 hash.

    Args:
        project_dir: Path to project directory
        short_hash: 8-char truncated hash from directory name (for validation)

    Returns:
        Full 32-char MD5 hash of project path, or None if not found
    """
    import hashlib
    import json

    # Try to find project path from project_info.json
    project_info_file = project_dir / "project_info.json"
    if project_info_file.exists():
        try:
            project_info = json.loads(project_info_file.read_text())
            project_path = project_info.get("project_path")
            if project_path:
                # Compute full 32-char project_id from normalized path
                normalized = str(Path(project_path).resolve())
                full_hash = hashlib.md5(normalized.encode()).hexdigest()

                # Validate that short hash matches first 8 chars
                if full_hash[:8] == short_hash:
                    return full_hash
        except json.JSONDecodeError:
            # If we can't read/parse project_info, skip this project
            pass

    return None


def get_indexed_projects() -> dict[tuple[str, str], set[str]]:
    """Get all currently indexed projects with their model/dimension combos.

    Returns:
        Dict mapping (project_id, model_slug) to set of dimensions
        Example: {('abc123...', 'qwen3'): {'1024d'}, ('def456...', 'bge-m3'): {'768d', '1024d'}}
    """
    storage_dir = Path.home() / ".claude_code_search" / "projects"
    indexed = {}

    if not storage_dir.exists():
        return indexed

    # Parse directory names: {project_name}_{project_hash}_{model_slug}_{dimension}d
    for project_dir in storage_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Split from right to handle project names with underscores
        parts = project_dir.name.rsplit("_", 3)
        if len(parts) < 4:
            # Skip directories that don't match the expected format
            continue

        # Extract components: name_hash8_model_dimD
        _ = parts[0]  # project_name (may contain underscores, not used)
        project_hash = parts[1]  # 8-char truncated hash
        model_slug = parts[2]  # e.g., "qwen3", "bge-m3"
        dimension = parts[3]  # e.g., "1024d"

        # Validate dimension format
        if not (dimension.endswith("d") and dimension[:-1].isdigit()):
            continue

        # Get full 32-char project_id from metadata
        project_id = _get_full_project_id(project_dir, project_hash)
        if not project_id:
            # Skip if we can't determine full project_id
            continue

        # Store by (project_id, model_slug) key
        key = (project_id, model_slug)
        if key not in indexed:
            indexed[key] = set()
        indexed[key].add(dimension)

    return indexed


def find_stale_snapshots() -> dict[str, list[Path]]:
    """Find Merkle snapshots that don't have corresponding project indices.

    Returns:
        Dict mapping project_id to list of orphaned snapshot/metadata files
    """
    snapshot_manager = SnapshotManager()
    merkle_dir = snapshot_manager.storage_dir

    if not merkle_dir.exists():
        return {}

    # Get currently indexed projects: {(project_id, model_slug): {dimensions}}
    indexed_projects = get_indexed_projects()

    # Find all snapshot files
    stale = {}
    for snapshot_file in merkle_dir.glob("*_snapshot.json"):
        # Parse filename: {project_id}_{model_slug}_{dimension}d_snapshot.json
        name = snapshot_file.stem.replace("_snapshot", "")

        # Split from right to handle project_ids that may contain underscores
        parts = name.rsplit("_", 2)
        if len(parts) < 3:
            continue

        project_id = parts[0]  # Full 32-char MD5 hash
        model_slug = parts[1]  # e.g., "qwen3", "bge-m3"
        dimension = parts[2]  # e.g., "1024d"

        # Validate dimension format
        if not (dimension.endswith("d") and dimension[:-1].isdigit()):
            continue

        # Check if this (project_id, model_slug, dimension) combo exists
        key = (project_id, model_slug)
        is_orphaned = (
            key not in indexed_projects or dimension not in indexed_projects[key]
        )

        if is_orphaned:
            if project_id not in stale:
                stale[project_id] = []

            stale[project_id].append(snapshot_file)

            # Also include corresponding metadata file (with correct format)
            metadata_file = (
                snapshot_file.parent
                / f"{project_id}_{model_slug}_{dimension}_metadata.json"
            )
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
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup stale Merkle snapshots")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-confirm deletion (for CI/testing, silent mode)",
    )
    args = parser.parse_args()

    # Only show banner in interactive mode
    if not args.auto:
        print("=" * 70)
        print("Merkle Snapshot Cleanup Utility")
        print("=" * 70)
        print()

    # Find stale snapshots
    if not args.auto:
        print("Scanning for stale snapshots...")
    stale_snapshots = find_stale_snapshots()

    if not stale_snapshots:
        if not args.auto:
            print("✓ No stale snapshots found!")
            print()
            print("All Merkle snapshots have corresponding project indices.")
        return

    # Display findings
    total_files = sum(len(files) for files in stale_snapshots.values())
    total_size = sum(
        sum(f.stat().st_size for f in files) for files in stale_snapshots.values()
    )

    # Only show detailed output in interactive mode
    if not args.auto:
        print(f"Found {total_files} stale snapshot files ({format_size(total_size)})")
        print()

        print("Stale snapshots by project:")
        print("-" * 70)

        for project_id, files in sorted(stale_snapshots.items()):
            project_size = sum(f.stat().st_size for f in files)
            dimensions = set()
            models = set()
            for f in files:
                # Parse: {project_id}_{model_slug}_{dimension}d_{snapshot|metadata}.json
                name = f.stem.replace("_snapshot", "").replace("_metadata", "")
                parts = name.rsplit("_", 2)
                if len(parts) >= 3:
                    model_slug = parts[1]
                    dimension = parts[2]
                    models.add(model_slug)
                    dimensions.add(dimension)

            print(f"\nProject ID: {project_id}")
            print(f"  Models: {', '.join(sorted(models))}")
            print(f"  Dimensions: {', '.join(sorted(dimensions))}")
            print(f"  Files: {len(files)}")
            print(f"  Size: {format_size(project_size)}")
            for f in files:
                print(f"    - {f.name} ({format_size(f.stat().st_size)})")

        print()
        print("-" * 70)
        print()

    # Confirm deletion
    if args.auto:
        response = "y"
    else:
        response = input("Delete all stale snapshots? [y/N]: ").strip().lower()

    if response not in ["y", "yes"]:
        if not args.auto:
            print("Cancelled. No files were deleted.")
        return

    # Delete files
    if not args.auto:
        print()
        print("Deleting stale snapshots...")
    deleted_count = 0
    failed_count = 0

    for _project_id, files in stale_snapshots.items():
        for f in files:
            try:
                f.unlink()
                deleted_count += 1
                if not args.auto:
                    print(f"  ✓ Deleted: {f.name}")
            except Exception as e:
                failed_count += 1
                if not args.auto:
                    print(f"  ✗ Failed to delete {f.name}: {e}")

    # Only show summary in interactive mode
    if not args.auto:
        print()
        print("=" * 70)
        print("Cleanup complete!")
        print(f"  Deleted: {deleted_count} files")
        if failed_count > 0:
            print(f"  Failed: {failed_count} files")
        print(f"  Recovered: {format_size(total_size)}")
        print("=" * 70)


if __name__ == "__main__":
    main()
