"""TypeScript-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class TypeScriptChunker(LanguageChunker):
    """TypeScript-specific chunker using tree-sitter."""

    # TS grammars use type_identifier for interface/enum/class names
    _NAME_ID_TYPES: tuple[str, ...] = ("identifier", "type_identifier")

    def __init__(self, language: Language | None = None, use_tsx: bool = False) -> None:
        self.use_tsx = use_tsx
        language_name = "tsx" if use_tsx else "typescript"
        super().__init__(language_name, language)

    def _extra_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Add TS-specific flags: is_async, is_export, has_generics."""
        # Check for async
        if node.children and self.get_node_text(node.children[0], source) == "async":
            metadata["is_async"] = True

        # Check for export
        if node.children and self.get_node_text(node.children[0], source) == "export":
            metadata["is_export"] = True

        # Check for generic parameters
        for child in node.children:
            if child.type == "type_parameters":
                metadata["has_generics"] = True
                break
