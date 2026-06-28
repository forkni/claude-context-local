"""JavaScript-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class JavaScriptChunker(LanguageChunker):
    """JavaScript-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("javascript", language)

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract JavaScript-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract function/class name
        for child in node.children:
            if child.type == "identifier":
                metadata["name"] = self.get_node_text(child, source)
                break

        # Check for async
        if node.children and self.get_node_text(node.children[0], source) == "async":
            metadata["is_async"] = True

        # Check for generator
        if "generator" in node.type:
            metadata["is_generator"] = True

        return metadata
