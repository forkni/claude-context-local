"""Rust-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class RustChunker(LanguageChunker):
    """Rust-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("rust", language)

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract Rust-specific metadata."""
        metadata: dict[str, Any] = {"node_type": node.type}

        name = self._extract_name(
            node, source, id_types=("identifier", "type_identifier")
        )
        if name is not None:
            metadata["name"] = name

        # Check for async functions
        if node.type == "function_item":
            for child in node.children:
                if (
                    child.type == "async"
                    or self.get_node_text(child, source) == "async"
                ):
                    metadata["is_async"] = True
                    break

        # Extract impl type for impl blocks
        if node.type == "impl_item":
            for child in node.children:
                if child.type in ["type_identifier", "generic_type"]:
                    metadata["impl_type"] = self.get_node_text(child, source)
                    break

        return metadata
