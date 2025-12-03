"""Detects changes between Merkle tree snapshots."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .merkle_dag import MerkleDAG
from .snapshot_manager import SnapshotManager


@dataclass
class FileChanges:
    """Container for file change information."""

    added: List[str]
    removed: List[str]
    modified: List[str]
    unchanged: List[str]

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.added or self.removed or self.modified)

    def total_changed(self) -> int:
        """Get total number of changed files."""
        return len(self.added) + len(self.removed) + len(self.modified)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "unchanged": self.unchanged,
            "summary": {
                "added_count": len(self.added),
                "removed_count": len(self.removed),
                "modified_count": len(self.modified),
                "unchanged_count": len(self.unchanged),
                "total_changed": self.total_changed(),
            },
        }


class ChangeDetector:
    """Detects changes between Merkle DAGs."""

    def __init__(
        self,
        snapshot_manager: SnapshotManager = None,
        include_dirs: List[str] = None,
        exclude_dirs: List[str] = None,
    ):
        """Initialize change detector.

        Args:
            snapshot_manager: Snapshot manager instance
            include_dirs: Optional list of directories to include
            exclude_dirs: Optional list of directories to exclude
        """
        self.snapshot_manager = snapshot_manager or SnapshotManager()
        self.include_dirs = include_dirs
        self.exclude_dirs = exclude_dirs

    def detect_changes(self, old_dag: MerkleDAG, new_dag: MerkleDAG) -> FileChanges:
        """Detect file changes between two Merkle DAGs.

        Args:
            old_dag: Previous state DAG
            new_dag: Current state DAG

        Returns:
            FileChanges object with lists of changed files
        """
        old_files = old_dag.get_file_hashes()
        new_files = new_dag.get_file_hashes()

        old_paths = set(old_files.keys())
        new_paths = set(new_files.keys())

        # Find added and removed files
        added = sorted(new_paths - old_paths)
        removed = sorted(old_paths - new_paths)

        # Find modified files (same path, different hash)
        common_paths = old_paths & new_paths
        modified = []
        unchanged = []

        for path in sorted(common_paths):
            if old_files[path] != new_files[path]:
                modified.append(path)
            else:
                unchanged.append(path)

        return FileChanges(
            added=added, removed=removed, modified=modified, unchanged=unchanged
        )

    def detect_changes_from_snapshot(
        self, project_path: str
    ) -> Tuple[FileChanges, MerkleDAG]:
        """Detect changes between saved snapshot and current state.

        Args:
            project_path: Path to project

        Returns:
            Tuple of (FileChanges, current MerkleDAG)
        """
        # Build current DAG
        current_dag = MerkleDAG(project_path, self.include_dirs, self.exclude_dirs)

        # Add snapshot directory to ignore patterns if it's inside the project
        snapshot_dir = self.snapshot_manager.storage_dir
        try:
            relative_snapshot = snapshot_dir.relative_to(Path(project_path))
            current_dag.ignore_patterns.add(str(relative_snapshot))
        except ValueError:
            # Snapshot dir is not inside the project, no need to ignore
            pass

        current_dag.build()

        # Load previous snapshot
        old_dag = self.snapshot_manager.load_snapshot(project_path)

        if old_dag is None:
            # No previous snapshot, treat all files as added
            all_files = current_dag.get_all_files()
            changes = FileChanges(
                added=all_files, removed=[], modified=[], unchanged=[]
            )
        else:
            # Compare with previous snapshot
            changes = self.detect_changes(old_dag, current_dag)

        return changes, current_dag

    def quick_check(self, project_path: str) -> bool:
        """Quick check if project has changed by comparing root hashes.

        Args:
            project_path: Path to project

        Returns:
            True if project has changed or no snapshot exists
        """
        # Load previous snapshot
        old_dag = self.snapshot_manager.load_snapshot(project_path)
        if old_dag is None:
            return True

        # Build current DAG
        current_dag = MerkleDAG(project_path, self.include_dirs, self.exclude_dirs)

        # Add snapshot directory to ignore patterns if it's inside the project
        snapshot_dir = self.snapshot_manager.storage_dir
        try:
            relative_snapshot = snapshot_dir.relative_to(Path(project_path))
            current_dag.ignore_patterns.add(str(relative_snapshot))
        except ValueError:
            # Snapshot dir is not inside the project, no need to ignore
            pass

        current_dag.build()

        # Compare root hashes
        return old_dag.get_root_hash() != current_dag.get_root_hash()

    def get_changed_directories(
        self, old_dag: MerkleDAG, new_dag: MerkleDAG
    ) -> List[str]:
        """Get list of directories that have changed.

        Args:
            old_dag: Previous state DAG
            new_dag: Current state DAG

        Returns:
            List of changed directory paths
        """
        changed_dirs = []

        for path, new_node in new_dag.nodes.items():
            if not new_node.is_file:
                old_node = old_dag.find_node(path)
                if old_node is None or old_node.hash != new_node.hash:
                    changed_dirs.append(path)

        return sorted(changed_dirs)

    def analyze_change_patterns(self, changes: FileChanges) -> Dict:
        """Analyze patterns in file changes.

        Args:
            changes: FileChanges object

        Returns:
            Dictionary with change analysis
        """
        analysis = {
            "file_extensions": {},
            "directories": {},
            "change_types": {
                "added": len(changes.added),
                "removed": len(changes.removed),
                "modified": len(changes.modified),
            },
        }

        all_changed = changes.added + changes.removed + changes.modified

        for file_path in all_changed:
            path = Path(file_path)

            # Count by extension
            ext = path.suffix or "no_extension"
            analysis["file_extensions"][ext] = (
                analysis["file_extensions"].get(ext, 0) + 1
            )

            # Count by directory
            dir_path = str(path.parent) if path.parent != Path(".") else "root"
            analysis["directories"][dir_path] = (
                analysis["directories"].get(dir_path, 0) + 1
            )

        # Sort by frequency
        analysis["file_extensions"] = dict(
            sorted(
                analysis["file_extensions"].items(), key=lambda x: x[1], reverse=True
            )
        )
        analysis["directories"] = dict(
            sorted(analysis["directories"].items(), key=lambda x: x[1], reverse=True)
        )

        return analysis

    def get_files_to_reindex(self, changes: FileChanges) -> List[str]:
        """Get list of files that need to be reindexed.

        Args:
            changes: FileChanges object

        Returns:
            List of file paths to reindex (added + modified)
        """
        return sorted(changes.added + changes.modified)

    def get_files_to_remove(self, changes: FileChanges) -> List[str]:
        """Get list of files whose chunks should be removed from index.

        Args:
            changes: FileChanges object

        Returns:
            List of file paths to remove (removed + modified)
        """
        # Modified files need their old chunks removed before adding new ones
        return sorted(changes.removed + changes.modified)
