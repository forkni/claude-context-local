"""JavaScript-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class JavaScriptChunker(LanguageChunker):
    """JavaScript-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("javascript", language)

    def _extra_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Add JS-specific flags: is_async, is_generator."""
        # Check for async
        if node.children and self.get_node_text(node.children[0], source) == "async":
            metadata["is_async"] = True

        # Check for generator
        if "generator" in node.type:
            metadata["is_generator"] = True
