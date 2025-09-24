"""Unit tests for Merkle tree change detection."""

import tempfile
import time
from pathlib import Path
from unittest import TestCase

import pytest

from merkle.change_detector import ChangeDetector, FileChanges
from merkle.merkle_dag import MerkleDAG, MerkleNode
from merkle.snapshot_manager import SnapshotManager


class TestMerkleNode(TestCase):
    """Test MerkleNode class."""

    def test_node_creation(self):
        """Test creating a Merkle node."""
        node = MerkleNode(path="test.py", hash="abc123", is_file=True, size=100)

        assert node.path == "test.py"
        assert node.hash == "abc123"
        assert node.is_file is True
        assert node.size == 100
        assert len(node.children) == 0

    def test_node_serialization(self):
        """Test node to/from dict conversion."""
        # Create parent with children
        child1 = MerkleNode("child1.py", "hash1", True, 50)
        child2 = MerkleNode("child2.py", "hash2", True, 75)
        parent = MerkleNode("parent", "parent_hash", False, 0)
        parent.children = [child1, child2]

        # Serialize
        data = parent.to_dict()

        # Verify structure
        assert data["path"] == "parent"
        assert data["hash"] == "parent_hash"
        assert data["is_file"] is False
        assert len(data["children"]) == 2

        # Deserialize
        restored = MerkleNode.from_dict(data)

        # Verify restoration
        assert restored.path == parent.path
        assert restored.hash == parent.hash
        assert len(restored.children) == 2
        assert restored.children[0].path == "child1.py"
        assert restored.children[1].path == "child2.py"


class TestMerkleDAG(TestCase):
    """Test MerkleDAG class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_files(self):
        """Create test file structure."""
        # Create directories
        (self.test_path / "src").mkdir()
        (self.test_path / "tests").mkdir()

        # Create files
        (self.test_path / "README.md").write_text("# Test Project")
        (self.test_path / "src" / "main.py").write_text("def main(): pass")
        (self.test_path / "src" / "utils.py").write_text("def helper(): pass")
        (self.test_path / "tests" / "test_main.py").write_text("def test_main(): pass")

    def test_dag_building(self):
        """Test building a Merkle DAG from directory."""
        self.create_test_files()

        dag = MerkleDAG(self.temp_dir)
        dag.build()

        # Check root node exists
        assert dag.root_node is not None
        assert dag.root_node.is_file is False

        # Check files are tracked
        all_files = dag.get_all_files()
        assert len(all_files) == 4

        # Check specific files (normalize paths for cross-platform compatibility)
        import os

        normalized_files = [os.path.normpath(f) for f in all_files]
        assert "README.md" in all_files
        assert os.path.normpath("src/main.py") in normalized_files
        assert os.path.normpath("src/utils.py") in normalized_files
        assert os.path.normpath("tests/test_main.py") in normalized_files

    def test_file_hashing(self):
        """Test file hash calculation."""
        self.create_test_files()

        dag = MerkleDAG(self.temp_dir)
        dag.build()

        file_hashes = dag.get_file_hashes()

        # All files should have hashes
        assert len(file_hashes) == 4

        # Hashes should be consistent
        dag2 = MerkleDAG(self.temp_dir)
        dag2.build()
        file_hashes2 = dag2.get_file_hashes()

        assert file_hashes == file_hashes2

    def test_directory_hashing(self):
        """Test directory hash changes with content."""
        self.create_test_files()

        dag1 = MerkleDAG(self.temp_dir)
        dag1.build()
        root_hash1 = dag1.get_root_hash()

        # Modify a file
        (self.test_path / "src" / "main.py").write_text("def main(): return 1")

        dag2 = MerkleDAG(self.temp_dir)
        dag2.build()
        root_hash2 = dag2.get_root_hash()

        # Root hash should change
        assert root_hash1 != root_hash2

        # Src directory hash should change
        src_node1 = dag1.find_node("src")
        src_node2 = dag2.find_node("src")
        assert src_node1.hash != src_node2.hash

        # Tests directory hash should remain same
        tests_node1 = dag1.find_node("tests")
        tests_node2 = dag2.find_node("tests")
        assert tests_node1.hash == tests_node2.hash

    def test_ignore_patterns(self):
        """Test ignore patterns in DAG building."""
        self.create_test_files()

        # Create files that should be ignored
        (self.test_path / ".git").mkdir()
        (self.test_path / ".git" / "config").write_text("config")
        (self.test_path / "__pycache__").mkdir()
        (self.test_path / "__pycache__" / "cache.pyc").write_text("cache")
        (self.test_path / "test.pyc").write_text("pyc")

        dag = MerkleDAG(self.temp_dir)
        dag.build()

        all_files = dag.get_all_files()

        # Ignored files should not be in DAG
        assert ".git/config" not in all_files
        assert "__pycache__/cache.pyc" not in all_files
        assert "test.pyc" not in all_files

        # Regular files should be present
        assert "README.md" in all_files

    def test_dag_serialization(self):
        """Test DAG to/from dict conversion."""
        self.create_test_files()

        dag1 = MerkleDAG(self.temp_dir)
        dag1.build()

        # Serialize
        data = dag1.to_dict()

        # Verify structure
        assert data["root_path"] == str(self.test_path)
        assert data["root_node"] is not None
        assert data["file_count"] == 4
        assert data["total_size"] > 0

        # Deserialize
        dag2 = MerkleDAG.from_dict(data)

        # Verify restoration
        assert dag2.root_path == dag1.root_path
        assert dag2.get_root_hash() == dag1.get_root_hash()
        assert dag2.get_all_files() == dag1.get_all_files()


class TestSnapshotManager(TestCase):
    """Test SnapshotManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir) / "project"
        self.test_path.mkdir()

        self.storage_dir = Path(self.temp_dir) / "snapshots"
        self.manager = SnapshotManager(self.storage_dir)

        # Create test files
        (self.test_path / "test.py").write_text('print("test")')

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_project_id_generation(self):
        """Test project ID generation."""
        id1 = self.manager.get_project_id("/path/to/project")
        id2 = self.manager.get_project_id("/path/to/project")
        id3 = self.manager.get_project_id("/different/path")

        # Same path should produce same ID
        assert id1 == id2

        # Different path should produce different ID
        assert id1 != id3

    def test_save_and_load_snapshot(self):
        """Test saving and loading snapshots."""
        # Create DAG
        dag = MerkleDAG(str(self.test_path))
        dag.build()

        # Save snapshot
        self.manager.save_snapshot(dag, {"test": "metadata"})

        # Load snapshot
        loaded_dag = self.manager.load_snapshot(str(self.test_path))

        assert loaded_dag is not None
        assert loaded_dag.get_root_hash() == dag.get_root_hash()
        assert loaded_dag.get_all_files() == dag.get_all_files()

    def test_metadata_handling(self):
        """Test metadata save and load."""
        dag = MerkleDAG(str(self.test_path))
        dag.build()

        # Save with metadata
        custom_metadata = {"version": "1.0", "author": "test"}
        self.manager.save_snapshot(dag, custom_metadata)

        # Load metadata
        metadata = self.manager.load_metadata(str(self.test_path))

        assert metadata is not None
        assert metadata["version"] == "1.0"
        assert metadata["author"] == "test"
        assert metadata["project_path"] == str(self.test_path)
        assert metadata["file_count"] == 1

    def test_snapshot_existence_check(self):
        """Test checking if snapshot exists."""
        assert not self.manager.has_snapshot(str(self.test_path))

        dag = MerkleDAG(str(self.test_path))
        dag.build()
        self.manager.save_snapshot(dag)

        assert self.manager.has_snapshot(str(self.test_path))

    def test_list_snapshots(self):
        """Test listing all snapshots."""
        # Create multiple project snapshots
        for i in range(3):
            project_path = self.test_path.parent / f"project{i}"
            project_path.mkdir()
            (project_path / "file.txt").write_text(f"content{i}")

            dag = MerkleDAG(str(project_path))
            dag.build()
            self.manager.save_snapshot(dag)

            time.sleep(0.1)  # Ensure different timestamps

        snapshots = self.manager.list_snapshots()

        assert len(snapshots) == 3
        # Should be sorted by timestamp (most recent first)
        assert "project2" in snapshots[0]["project_path"]


class TestChangeDetector(TestCase):
    """Test ChangeDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir)

        self.storage_dir = Path(self.temp_dir) / "snapshots"
        self.snapshot_manager = SnapshotManager(self.storage_dir)
        self.detector = ChangeDetector(self.snapshot_manager)

        self.create_initial_files()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_initial_files(self):
        """Create initial file structure."""
        (self.test_path / "src").mkdir()
        (self.test_path / "unchanged.py").write_text("# unchanged")
        (self.test_path / "to_modify.py").write_text("# original")
        (self.test_path / "to_remove.py").write_text("# remove me")
        (self.test_path / "src" / "module.py").write_text("# module")

    def test_detect_changes_between_dags(self):
        """Test detecting changes between two DAGs."""
        # Create initial DAG
        dag1 = MerkleDAG(str(self.test_path))
        dag1.build()

        # Modify files
        (self.test_path / "to_modify.py").write_text("# modified")
        (self.test_path / "to_remove.py").unlink()
        (self.test_path / "added.py").write_text("# new file")

        # Create new DAG
        dag2 = MerkleDAG(str(self.test_path))
        dag2.build()

        # Detect changes
        changes = self.detector.detect_changes(dag1, dag2)

        import os

        assert "added.py" in changes.added
        assert "to_remove.py" in changes.removed
        assert "to_modify.py" in changes.modified
        assert "unchanged.py" in changes.unchanged
        # Normalize path for cross-platform compatibility
        normalized_unchanged = [os.path.normpath(f) for f in changes.unchanged]
        assert os.path.normpath("src/module.py") in normalized_unchanged

        assert changes.has_changes()
        assert changes.total_changed() == 3

    def test_detect_changes_from_snapshot(self):
        """Test detecting changes from saved snapshot."""
        # Create and save initial snapshot
        dag1 = MerkleDAG(str(self.test_path))
        dag1.build()
        self.snapshot_manager.save_snapshot(dag1)

        # Modify files
        (self.test_path / "to_modify.py").write_text("# modified content")
        (self.test_path / "new_file.py").write_text("# new")

        # Detect changes from snapshot
        changes, current_dag = self.detector.detect_changes_from_snapshot(
            str(self.test_path)
        )

        assert "new_file.py" in changes.added
        assert "to_modify.py" in changes.modified
        assert len(changes.removed) == 0
        assert changes.has_changes()

    def test_no_changes_detection(self):
        """Test when no changes occur."""
        dag1 = MerkleDAG(str(self.test_path))
        dag1.build()

        dag2 = MerkleDAG(str(self.test_path))
        dag2.build()

        changes = self.detector.detect_changes(dag1, dag2)

        assert not changes.has_changes()
        assert changes.total_changed() == 0
        assert len(changes.unchanged) == 4

    def test_quick_check(self):
        """Test quick change detection."""
        # No snapshot exists - should return True
        assert self.detector.quick_check(str(self.test_path))

        # Save snapshot - excluding snapshots directory
        dag = MerkleDAG(str(self.test_path))
        dag.ignore_patterns.add("snapshots")  # Ignore the snapshots directory
        dag.build()
        self.snapshot_manager.save_snapshot(dag)

        # No changes - should return False
        assert not self.detector.quick_check(str(self.test_path))

        # Make a change
        (self.test_path / "to_modify.py").write_text("# changed")

        # Should detect change
        assert self.detector.quick_check(str(self.test_path))

    def test_files_to_reindex(self):
        """Test getting files that need reindexing."""
        changes = FileChanges(
            added=["new1.py", "new2.py"],
            removed=["old.py"],
            modified=["changed.py"],
            unchanged=["same.py"],
        )

        files_to_reindex = self.detector.get_files_to_reindex(changes)

        assert len(files_to_reindex) == 3
        assert "new1.py" in files_to_reindex
        assert "new2.py" in files_to_reindex
        assert "changed.py" in files_to_reindex
        assert "old.py" not in files_to_reindex

    def test_files_to_remove(self):
        """Test getting files to remove from index."""
        changes = FileChanges(
            added=["new.py"],
            removed=["deleted.py"],
            modified=["changed.py"],
            unchanged=["same.py"],
        )

        files_to_remove = self.detector.get_files_to_remove(changes)

        assert len(files_to_remove) == 2
        assert "deleted.py" in files_to_remove
        assert "changed.py" in files_to_remove  # Modified files need old chunks removed
        assert "new.py" not in files_to_remove


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
