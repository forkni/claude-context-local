"""Merkle DAG (Directed Acyclic Graph) implementation for file change tracking."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class MerkleNode:
    """Represents a node in the Merkle DAG."""

    path: str
    hash: str
    is_file: bool
    size: int = 0
    children: List["MerkleNode"] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert node to dictionary for serialization."""
        return {
            "path": self.path,
            "hash": self.hash,
            "is_file": self.is_file,
            "size": self.size,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MerkleNode":
        """Create node from dictionary."""
        node = cls(
            path=data["path"],
            hash=data["hash"],
            is_file=data["is_file"],
            size=data.get("size", 0),
        )
        node.children = [cls.from_dict(child) for child in data.get("children", [])]
        return node


class MerkleDAG:
    """Merkle DAG for tracking file system changes."""

    def __init__(self, root_path: str):
        """Initialize Merkle DAG for a directory tree.

        Args:
            root_path: Root directory to track
        """
        self.root_path = Path(root_path).resolve()
        self.nodes: Dict[str, MerkleNode] = {}
        self.root_node: Optional[MerkleNode] = None
        self.ignore_patterns: Set[str] = {
            "__pycache__",
            ".git",
            ".hg",
            ".svn",
            ".venv",
            "venv",
            "env",
            ".env",
            ".direnv",
            "node_modules",
            ".pnpm-store",
            ".yarn",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".pytype",
            ".ipynb_checkpoints",
            "build",
            "dist",
            "out",
            "public",
            ".next",
            ".nuxt",
            ".svelte-kit",
            ".angular",
            ".astro",
            ".vite",
            ".cache",
            ".parcel-cache",
            ".turbo",
            "coverage",
            ".coverage",
            ".nyc_output",
            ".gradle",
            ".idea",
            ".vscode",
            ".docusaurus",
            ".vercel",
            ".serverless",
            ".terraform",
            ".mvn",
            ".tox",
            "target",
            "bin",
            "obj",
            "*.pyc",
            "*.pyo",
            ".DS_Store",
            "Thumbs.db",
        }

    def should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        name = path.name

        # Check exact matches and patterns
        for pattern in self.ignore_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True

        return False

    def hash_file(self, file_path: Path) -> Tuple[str, int]:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (hash, file_size)
        """
        sha256 = hashlib.sha256()
        size = 0

        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
                    size += len(chunk)
        except (IOError, OSError):
            # Handle permission errors or broken symlinks
            sha256.update(str(file_path).encode())

        return sha256.hexdigest(), size

    def hash_directory(self, dir_path: Path, child_hashes: List[str]) -> str:
        """Calculate hash for a directory based on its children.

        Args:
            dir_path: Path to directory
            child_hashes: List of child hashes

        Returns:
            Directory hash
        """
        sha256 = hashlib.sha256()

        # Include directory name
        sha256.update(dir_path.name.encode())

        # Include sorted child hashes for deterministic results
        for child_hash in sorted(child_hashes):
            sha256.update(child_hash.encode())

        return sha256.hexdigest()

    def build_node(
        self, path: Path, base_path: Optional[Path] = None
    ) -> Optional[MerkleNode]:
        """Recursively build a Merkle node for a path.

        Args:
            path: Path to build node for
            base_path: Base path for relative path calculation

        Returns:
            MerkleNode or None if path should be ignored
        """
        if self.should_ignore(path):
            return None

        if base_path is None:
            base_path = self.root_path

        # Calculate relative path
        if path == self.root_path:
            relative_path = "."
        else:
            relative_path = str(path.relative_to(self.root_path))

        if path.is_file():
            file_hash, size = self.hash_file(path)
            node = MerkleNode(
                path=relative_path, hash=file_hash, is_file=True, size=size
            )
            self.nodes[relative_path] = node
            return node

        elif path.is_dir():
            children = []
            child_hashes = []

            try:
                for child_path in sorted(path.iterdir()):
                    child_node = self.build_node(child_path, base_path)
                    if child_node:
                        children.append(child_node)
                        child_hashes.append(child_node.hash)
            except (PermissionError, OSError):
                pass

            dir_hash = self.hash_directory(path, child_hashes)
            node = MerkleNode(
                path=relative_path, hash=dir_hash, is_file=False, children=children
            )
            self.nodes[relative_path] = node
            return node

        return None

    def build(self) -> None:
        """Build the complete Merkle DAG for the root directory."""
        self.nodes.clear()
        self.root_node = self.build_node(self.root_path)
        # For the root node, use "." as its path
        if self.root_node:
            self.root_node.path = "."
            self.nodes["."] = self.root_node

    def get_file_hashes(self) -> Dict[str, str]:
        """Get a dictionary of file paths to their hashes.

        Returns:
            Dictionary mapping file paths to hashes
        """
        return {path: node.hash for path, node in self.nodes.items() if node.is_file}

    def get_all_files(self) -> List[str]:
        """Get list of all tracked file paths.

        Returns:
            List of file paths
        """
        return [path for path, node in self.nodes.items() if node.is_file]

    def to_dict(self) -> Dict:
        """Convert DAG to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "root_path": str(self.root_path),
            "root_node": self.root_node.to_dict() if self.root_node else None,
            "file_count": sum(1 for n in self.nodes.values() if n.is_file),
            "total_size": sum(n.size for n in self.nodes.values() if n.is_file),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MerkleDAG":
        """Create DAG from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            MerkleDAG instance
        """
        dag = cls(data["root_path"])
        if data["root_node"]:
            dag.root_node = MerkleNode.from_dict(data["root_node"])

            # Rebuild nodes dictionary
            def add_to_nodes(node: MerkleNode):
                dag.nodes[node.path] = node
                for child in node.children:
                    add_to_nodes(child)

            add_to_nodes(dag.root_node)

        return dag

    def get_root_hash(self) -> Optional[str]:
        """Get the hash of the root node.

        Returns:
            Root hash or None if not built
        """
        return self.root_node.hash if self.root_node else None

    def find_node(self, path: str) -> Optional[MerkleNode]:
        """Find a node by path.

        Args:
            path: Relative path to find

        Returns:
            MerkleNode or None if not found
        """
        return self.nodes.get(path)

    def get_stats(self) -> Dict:
        """Get statistics about the DAG.

        Returns:
            Dictionary with statistics
        """
        file_nodes = [n for n in self.nodes.values() if n.is_file]
        dir_nodes = [n for n in self.nodes.values() if not n.is_file]

        return {
            "total_nodes": len(self.nodes),
            "file_count": len(file_nodes),
            "directory_count": len(dir_nodes),
            "total_size": sum(n.size for n in file_nodes),
            "root_hash": self.get_root_hash(),
        }
