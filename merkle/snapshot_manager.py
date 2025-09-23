"""Manages Merkle tree snapshots for persistent change tracking."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .merkle_dag import MerkleDAG


class SnapshotManager:
    """Manages loading and saving of Merkle DAG snapshots."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize snapshot manager.

        Args:
            storage_dir: Directory to store snapshots (default: ~/.claude_code_search/merkle)
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".claude_code_search" / "merkle"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def get_project_id(self, project_path: str) -> str:
        """Generate a unique ID for a project based on its path.

        Args:
            project_path: Path to project

        Returns:
            MD5 hash of the normalized path
        """
        normalized_path = str(Path(project_path).resolve())
        return hashlib.md5(normalized_path.encode()).hexdigest()

    def get_snapshot_path(self, project_path: str) -> Path:
        """Get the snapshot file path for a project.

        Args:
            project_path: Path to project

        Returns:
            Path to snapshot file
        """
        project_id = self.get_project_id(project_path)
        return self.storage_dir / f"{project_id}_snapshot.json"

    def get_metadata_path(self, project_path: str) -> Path:
        """Get the metadata file path for a project.

        Args:
            project_path: Path to project

        Returns:
            Path to metadata file
        """
        project_id = self.get_project_id(project_path)
        return self.storage_dir / f"{project_id}_metadata.json"

    def save_snapshot(self, dag: MerkleDAG, metadata: Optional[Dict] = None) -> None:
        """Save a Merkle DAG snapshot to disk.

        Args:
            dag: MerkleDAG to save
            metadata: Optional metadata to save alongside
        """
        project_path = str(dag.root_path)

        # Save the DAG structure
        snapshot_path = self.get_snapshot_path(project_path)
        snapshot_data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "dag": dag.to_dict(),
        }

        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f, indent=2)

        # Save metadata
        metadata_path = self.get_metadata_path(project_path)
        metadata_data = metadata or {}
        metadata_data.update(
            {
                "project_path": project_path,
                "project_id": self.get_project_id(project_path),
                "last_snapshot": datetime.now().isoformat(),
                "file_count": len(dag.get_all_files()),
                "root_hash": dag.get_root_hash(),
            }
        )

        with open(metadata_path, "w") as f:
            json.dump(metadata_data, f, indent=2)

    def load_snapshot(self, project_path: str) -> Optional[MerkleDAG]:
        """Load a Merkle DAG snapshot from disk.

        Args:
            project_path: Path to project

        Returns:
            MerkleDAG or None if no snapshot exists
        """
        snapshot_path = self.get_snapshot_path(project_path)

        if not snapshot_path.exists():
            return None

        try:
            with open(snapshot_path, "r") as f:
                snapshot_data = json.load(f)

            # Check version compatibility
            if snapshot_data.get("version") != "1.0":
                print(
                    f"Warning: Snapshot version mismatch: {snapshot_data.get('version')}"
                )

            return MerkleDAG.from_dict(snapshot_data["dag"])

        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"Error loading snapshot: {e}")
            return None

    def load_metadata(self, project_path: str) -> Optional[Dict]:
        """Load metadata for a project.

        Args:
            project_path: Path to project

        Returns:
            Metadata dictionary or None if not found
        """
        metadata_path = self.get_metadata_path(project_path)

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading metadata: {e}")
            return None

    def has_snapshot(self, project_path: str) -> bool:
        """Check if a snapshot exists for a project.

        Args:
            project_path: Path to project

        Returns:
            True if snapshot exists
        """
        return self.get_snapshot_path(project_path).exists()

    def delete_snapshot(self, project_path: str) -> None:
        """Delete snapshot and metadata for a project.

        Args:
            project_path: Path to project
        """
        snapshot_path = self.get_snapshot_path(project_path)
        metadata_path = self.get_metadata_path(project_path)

        if snapshot_path.exists():
            snapshot_path.unlink()

        if metadata_path.exists():
            metadata_path.unlink()

    def list_snapshots(self) -> List[Dict]:
        """List all available snapshots.

        Returns:
            List of snapshot metadata
        """
        snapshots = []

        for metadata_file in self.storage_dir.glob("*_metadata.json"):
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    snapshots.append(metadata)
            except Exception:
                continue

        return sorted(snapshots, key=lambda x: x.get("last_snapshot", ""), reverse=True)

    def cleanup_old_snapshots(self, keep_count: int = 5) -> None:
        """Remove old snapshots, keeping only the most recent ones.

        Args:
            keep_count: Number of snapshots to keep per project
        """
        # Group snapshots by project
        project_snapshots: Dict[str, List[Path]] = {}

        for snapshot_file in self.storage_dir.glob("*_snapshot.json"):
            project_id = snapshot_file.stem.replace("_snapshot", "")
            if project_id not in project_snapshots:
                project_snapshots[project_id] = []
            project_snapshots[project_id].append(snapshot_file)

        # Clean up old snapshots for each project
        for project_id, files in project_snapshots.items():
            # Sort by modification time
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Delete old snapshots
            for old_file in files[keep_count:]:
                old_file.unlink()

                # Also delete corresponding metadata
                metadata_file = old_file.parent / f"{project_id}_metadata.json"
                if metadata_file.exists():
                    metadata_file.unlink()

    def get_snapshot_age(self, project_path: str) -> Optional[float]:
        """Get the age of a snapshot in seconds.

        Args:
            project_path: Path to project

        Returns:
            Age in seconds or None if no snapshot exists
        """
        snapshot_path = self.get_snapshot_path(project_path)

        if not snapshot_path.exists():
            return None

        age = datetime.now().timestamp() - snapshot_path.stat().st_mtime
        return age
