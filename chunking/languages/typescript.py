"""TypeScript-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class TypeScriptChunker(LanguageChunker):
    """TypeScript-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None, use_tsx: bool = False) -> None:
        self.use_tsx = use_tsx
        language_name = "tsx" if use_tsx else "typescript"
        super().__init__(language_name, language)

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract TypeScript-specific metadata."""
        metadata: dict[str, Any] = {"node_type": node.type}

        name = self._extract_name(
            node, source, id_types=("identifier", "type_identifier")
        )
        if name is not None:
            metadata["name"] = name

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

        return metadata
