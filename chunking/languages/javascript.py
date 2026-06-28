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
        metadata: dict[str, Any] = {"node_type": node.type}

        name = self._extract_name(node, source)
        if name is not None:
            metadata["name"] = name

        # Check for async
        if node.children and self.get_node_text(node.children[0], source) == "async":
            metadata["is_async"] = True

        # Check for generator
        if "generator" in node.type:
            metadata["is_generator"] = True

        return metadata
