"""Rust-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class RustChunker(LanguageChunker):
    """Rust-specific chunker using tree-sitter."""

    # Rust grammars use type_identifier for struct/enum/trait names
    _NAME_ID_TYPES: tuple[str, ...] = ("identifier", "type_identifier")

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("rust", language)

    def _extra_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Add Rust-specific extras: is_async for functions, impl_type for impl blocks."""
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
