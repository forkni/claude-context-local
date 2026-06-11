"""Merkle DAG (Directed Acyclic Graph) implementation for file change tracking."""

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class MerkleNode:
    """Represents a node in the Merkle DAG."""

    path: str
    hash: str
    is_file: bool
    size: int = 0
    children: list["MerkleNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert node to dictionary for serialization."""
        return {
            "path": self.path,
            "hash": self.hash,
            "is_file": self.is_file,
            "size": self.size,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MerkleNode":
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

    def __init__(
        self,
        root_path: str,
        include_dirs=None,
        exclude_dirs=None,
        supported_extensions: set[str] | None = None,
    ) -> None:
        """Initialize Merkle DAG for a directory tree.

        Args:
            root_path: Root directory to track
            include_dirs: Optional list of directories to include
            exclude_dirs: Optional list of directories to exclude
            supported_extensions: If provided, files whose suffix is NOT in this
                set get a cheap stat-based hash instead of a full content hash,
                saving ~95% of I/O on projects with many non-code assets.
        """
        self.root_path = Path(root_path).resolve()
        self.nodes: dict[str, MerkleNode] = {}
        self.root_node: MerkleNode | None = None
        self.supported_extensions = supported_extensions

        # Initialize directory filter for custom include/exclude dirs
        from search.filters import DirectoryFilter

        self.directory_filter = DirectoryFilter(include_dirs, exclude_dirs)

        # Import default ignored directories from canonical source
        from chunking.multi_language_chunker import MultiLanguageChunker

        # Combine default ignored directories with file-specific patterns
        self.ignore_patterns: set[str] = set(
            MultiLanguageChunker.DEFAULT_IGNORED_DIRS
        ) | {
            "*.pyc",
            "*.pyo",
            ".DS_Store",
            "Thumbs.db",
            # Exclude server-managed config files — they are not source code and their mtime
            # changes whenever any MCP configure_* tool or reindex helper writes them, which
            # would otherwise trigger a spurious full reindex on the next search_code call.
            "search_config.json",
            ".search_config.json",
        }

    def should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        name = path.name

        # Check exact matches and patterns.
        # Patterns containing a path separator are matched against the path
        # relative to the project root (normalised to forward-slashes so they
        # work identically on Windows and POSIX).  Separator-free patterns
        # continue to match on the basename only, preserving existing behaviour
        # for entries like ".git", "__pycache__", and "*.pyc".
        for pattern in self.ignore_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif "/" in pattern or "\\" in pattern:
                # Multi-segment pattern — compare against the root-relative path.
                try:
                    rel = path.relative_to(self.root_path).as_posix()
                except ValueError:
                    # Path is not under root; ignore it.
                    return True
                if rel == pattern.replace("\\", "/"):
                    return True
            elif name == pattern:
                return True

        # Apply custom directory filters (for directories only)
        if path.is_dir() and self.directory_filter:
            try:
                relative_path = str(path.relative_to(self.root_path))
                # Root directory should never be filtered - only its contents
                # Use traversal mode to allow parent directories of include targets to pass through
                # This enables traversal to reach nested include_dirs like "Scripts/StreamDiffusionTD"
                if (
                    relative_path != "."
                    and not self.directory_filter.matches_for_traversal(
                        relative_path + "/"
                    )
                ):
                    return True
            except ValueError:
                # Path not under root, ignore it
                return True

        return False

    def hash_file(self, file_path: Path) -> tuple[str, int]:
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
        except OSError:
            # Handle permission errors or broken symlinks
            sha256.update(str(file_path).encode())

        return sha256.hexdigest(), size

    def hash_directory(self, dir_path: Path, child_hashes: list[str]) -> str:
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
        self, path: Path, base_path: Path | None = None
    ) -> MerkleNode | None:
        """Recursively build a Merkle node for a path.

        Args:
            path: Path to build node for
            base_path: Base path for relative path calculation

        Returns:
            MerkleNode or None if path should be ignored
        """
        # Never ignore the root itself, even if its name is in the ignore list.
        # Only apply should_ignore to paths *inside* the project root (#12).
        if path != self.root_path and self.should_ignore(path):
            return None

        if base_path is None:
            base_path = self.root_path

        # Calculate relative path
        if path == self.root_path:
            relative_path = "."
        else:
            relative_path = str(path.relative_to(self.root_path))

        if path.is_file():
            if (
                self.supported_extensions is not None
                and path.suffix.lower() not in self.supported_extensions
            ):
                # Stat-based hash for non-indexed files: ~100x cheaper than content
                # hash on Windows (no Defender scan, no content read). Detects
                # renames/moves via mtime+size; accurate enough for change tracking.
                try:
                    stat = path.stat()
                    fast_content = f"{path.name}:{stat.st_size}:{int(stat.st_mtime)}"
                except OSError:
                    fast_content = str(path)
                file_hash = hashlib.sha256(fast_content.encode()).hexdigest()
                size = 0
            else:
                file_hash, size = self.hash_file(path)
            node = MerkleNode(
                path=relative_path, hash=file_hash, is_file=True, size=size
            )
            self.nodes[relative_path] = node
            return node

        elif path.is_dir():
            # (a) Skip directory symlinks — following them risks infinite
            # recursion when a symlink points at an ancestor directory.
            if path.is_symlink():
                logger.warning("Skipping symlinked directory (cycle-safe): %s", path)
                return None

            children = []
            child_hashes = []

            # (b) Wrap the directory listing and each child separately so that
            # one unreadable entry does not silently drop its siblings.
            try:
                child_paths = sorted(path.iterdir())
            except (PermissionError, OSError) as exc:
                logger.warning(
                    "Cannot list directory %s (%s); skipping its children", path, exc
                )
                child_paths = []

            for child_path in child_paths:
                try:
                    child_node = self.build_node(child_path, base_path)
                except (PermissionError, OSError) as exc:
                    logger.warning("Skipping unreadable path %s (%s)", child_path, exc)
                    continue
                if child_node:
                    children.append(child_node)
                    child_hashes.append(child_node.hash)

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

    def get_file_hashes(self) -> dict[str, str]:
        """Get a dictionary of file paths to their hashes.

        Returns:
            Dictionary mapping file paths to hashes
        """
        return {path: node.hash for path, node in self.nodes.items() if node.is_file}

    def get_all_files(self) -> list[str]:
        """Get list of all tracked file paths.

        Returns:
            List of file paths
        """
        return [path for path, node in self.nodes.items() if node.is_file]

    def to_dict(self) -> dict:
        """Convert DAG to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "root_path": str(self.root_path),
            "root_node": self.root_node.to_dict() if self.root_node else None,
            "file_count": sum(1 for n in self.nodes.values() if n.is_file),
            "total_size": sum(n.size for n in self.nodes.values() if n.is_file),
            # Serialize directory filters for incremental indexing
            "include_dirs": (
                self.directory_filter.include_dirs if self.directory_filter else None
            ),
            "exclude_dirs": (
                self.directory_filter.exclude_dirs if self.directory_filter else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MerkleDAG":
        """Create DAG from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            MerkleDAG instance
        """
        # Restore directory filters from serialized snapshot
        dag = cls(
            data["root_path"],
            include_dirs=data.get("include_dirs"),
            exclude_dirs=data.get("exclude_dirs"),
        )
        if data["root_node"]:
            dag.root_node = MerkleNode.from_dict(data["root_node"])

            # Rebuild nodes dictionary
            def add_to_nodes(node: MerkleNode) -> None:
                dag.nodes[node.path] = node
                for child in node.children:
                    add_to_nodes(child)

            add_to_nodes(dag.root_node)

        return dag

    def get_root_hash(self) -> str | None:
        """Get the hash of the root node.

        Returns:
            Root hash or None if not built
        """
        return self.root_node.hash if self.root_node else None

    def find_node(self, path: str) -> MerkleNode | None:
        """Find a node by path.

        Args:
            path: Relative path to find

        Returns:
            MerkleNode or None if not found
        """
        return self.nodes.get(path)

    def get_stats(self) -> dict:
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
