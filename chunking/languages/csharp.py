"""C#-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class CSharpChunker(LanguageChunker):
    """C#-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("csharp", language)

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract C#-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract name
        for child in node.children:
            if child.type == "identifier":
                metadata["name"] = self.get_node_text(child, source)
                break

        # Extract access modifiers
        modifiers = []
        for child in node.children:
            if child.type == "modifier":
                modifier_text = self.get_node_text(child, source)
                if modifier_text in [
                    "public",
                    "private",
                    "protected",
                    "internal",
                    "static",
                    "virtual",
                    "abstract",
                    "override",
                    "async",
                ]:
                    modifiers.append(modifier_text)

        if modifiers:
            metadata["modifiers"] = modifiers
            if "async" in modifiers:
                metadata["is_async"] = True

        # Check for generic parameters
        for child in node.children:
            if child.type == "type_parameter_list":
                metadata["has_generics"] = True
                break

        return metadata
