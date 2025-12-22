"""Manages Merkle tree snapshots for persistent change tracking."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from search.filters import compute_drive_agnostic_hash, compute_legacy_hash

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
        """Generate a unique ID for a project based on its path (drive-agnostic).

        Args:
            project_path: Path to project

        Returns:
            MD5 hash of the drive-agnostic path (32 chars)
        """
        return compute_drive_agnostic_hash(project_path, length=32)

    def _get_legacy_project_id(self, project_path: str) -> str:
        """Generate project ID using original hashing algorithm.

        Args:
            project_path: Path to project

        Returns:
            MD5 hash of the full resolved path (32 chars)
        """
        return compute_legacy_hash(project_path, length=32)

    def _get_model_slug_and_dimension(
        self, dimension: Optional[int] = None
    ) -> Tuple[str, int]:
        """Get model slug and dimension, auto-detecting from config if needed.

        Args:
            dimension: Optional explicit dimension. If None, auto-detects from config.

        Returns:
            Tuple of (model_slug, dimension)
        """
        if dimension is None:
            try:
                # Use ServiceLocator to avoid circular dependency
                from mcp_server.services import ServiceLocator
                from search.config import get_model_slug

                config = ServiceLocator.instance().get_config()
                dimension = config.embedding.dimension
                model_slug = get_model_slug(config.embedding.model_name)
            except Exception:
                # Fallback to default if config unavailable
                dimension = 768
                model_slug = "unknown"
        else:
            # If dimension is provided explicitly, we need to get the current model slug
            try:
                # Use ServiceLocator to avoid circular dependency
                from mcp_server.services import ServiceLocator
                from search.config import get_model_slug

                config = ServiceLocator.instance().get_config()
                model_slug = get_model_slug(config.embedding.model_name)
            except Exception:
                model_slug = "unknown"

        return model_slug, dimension

    def get_snapshot_path(
        self, project_path: str, dimension: Optional[int] = None
    ) -> Path:
        """Get the snapshot file path for a project, checking both new and legacy hashes.

        Args:
            project_path: Path to project
            dimension: Model dimension (768 for Gemma, 1024 for BGE-M3).
                      If None, auto-detects from current config.

        Returns:
            Path to snapshot file with model slug and dimension suffix
        """
        model_slug, dimension = self._get_model_slug_and_dimension(dimension)

        # Try new hash first (drive-agnostic)
        new_id = self.get_project_id(project_path)
        new_path = (
            self.storage_dir / f"{new_id}_{model_slug}_{dimension}d_snapshot.json"
        )
        if new_path.exists():
            return new_path

        # Fallback to legacy hash for existing projects
        legacy_id = self._get_legacy_project_id(project_path)
        legacy_path = (
            self.storage_dir / f"{legacy_id}_{model_slug}_{dimension}d_snapshot.json"
        )
        if legacy_path.exists():
            return legacy_path

        # Return new path for creation
        return new_path

    def get_metadata_path(
        self, project_path: str, dimension: Optional[int] = None
    ) -> Path:
        """Get the metadata file path for a project, checking both new and legacy hashes.

        Args:
            project_path: Path to project
            dimension: Model dimension (768 for Gemma, 1024 for BGE-M3).
                      If None, auto-detects from current config.

        Returns:
            Path to metadata file with model slug and dimension suffix
        """
        model_slug, dimension = self._get_model_slug_and_dimension(dimension)

        # Try new hash first (drive-agnostic)
        new_id = self.get_project_id(project_path)
        new_path = (
            self.storage_dir / f"{new_id}_{model_slug}_{dimension}d_metadata.json"
        )
        if new_path.exists():
            return new_path

        # Fallback to legacy hash for existing projects
        legacy_id = self._get_legacy_project_id(project_path)
        legacy_path = (
            self.storage_dir / f"{legacy_id}_{model_slug}_{dimension}d_metadata.json"
        )
        if legacy_path.exists():
            return legacy_path

        # Return new path for creation
        return new_path

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

    def delete_snapshot_by_slug(
        self, project_path: str, model_slug: str, dimension: int
    ) -> int:
        """Delete snapshot for a specific model/dimension only.

        This deletes only the snapshot matching the exact model_slug and dimension,
        leaving other model variants intact.

        Args:
            project_path: Path to project
            model_slug: Model slug (e.g., 'bge-m3', 'coderank')
            dimension: Model dimension (e.g., 768, 1024)

        Returns:
            Number of files deleted (0-2: snapshot + metadata)
        """
        project_id = self.get_project_id(project_path)
        deleted_count = 0

        snapshot_file = (
            self.storage_dir / f"{project_id}_{model_slug}_{dimension}d_snapshot.json"
        )
        metadata_file = (
            self.storage_dir / f"{project_id}_{model_slug}_{dimension}d_metadata.json"
        )

        if snapshot_file.exists():
            snapshot_file.unlink()
            deleted_count += 1

        if metadata_file.exists():
            metadata_file.unlink()
            deleted_count += 1

        return deleted_count

    def delete_all_snapshots(self, project_path: str) -> int:
        """Delete ALL dimension snapshots and metadata for a project.

        This removes snapshots for all model dimensions (768d, 1024d, etc.),
        ensuring complete cleanup when clearing indices.

        Args:
            project_path: Path to project

        Returns:
            Number of files deleted
        """
        project_id = self.get_project_id(project_path)
        deleted_count = 0

        # Delete all snapshot files for this project (all dimensions)
        for snapshot_file in self.storage_dir.glob(f"{project_id}_*d_snapshot.json"):
            try:
                snapshot_file.unlink()
                deleted_count += 1
            except Exception:
                pass  # Continue even if one file fails

        # Delete all metadata files for this project (all dimensions)
        for metadata_file in self.storage_dir.glob(f"{project_id}_*d_metadata.json"):
            try:
                metadata_file.unlink()
                deleted_count += 1
            except Exception:
                pass  # Continue even if one file fails

        return deleted_count

    def clear_all_snapshots(self) -> int:
        """Delete ALL snapshots for ALL projects.

        This removes all snapshot and metadata files from the storage directory.
        Use with caution - this is a destructive operation.

        Returns:
            Number of files deleted
        """
        deleted_count = 0

        # Delete all snapshot files
        for snapshot_file in self.storage_dir.glob("*_snapshot.json"):
            try:
                snapshot_file.unlink()
                deleted_count += 1
            except Exception:
                pass  # Continue even if one file fails

        # Delete all metadata files
        for metadata_file in self.storage_dir.glob("*_metadata.json"):
            try:
                metadata_file.unlink()
                deleted_count += 1
            except Exception:
                pass  # Continue even if one file fails

        return deleted_count

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
