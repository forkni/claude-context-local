"""C#-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class CSharpChunker(LanguageChunker):
    """C#-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("csharp", language)

    def _load_language(self) -> Language:
        """Load tree-sitter-c-sharp language binding."""
        try:
            import tree_sitter_c_sharp as tscsharp

            return Language(tscsharp.language())
        except ImportError as err:
            raise ValueError(
                "tree-sitter-c-sharp not installed. "
                "Install with: pip install tree-sitter-c-sharp"
            ) from err

    def _get_splittable_node_types(self) -> set[str]:
        """C#-specific splittable node types."""
        return {
            "method_declaration",
            "constructor_declaration",
            "destructor_declaration",
            "class_declaration",
            "struct_declaration",
            "interface_declaration",
            "enum_declaration",
            "namespace_declaration",
            "property_declaration",
            "event_declaration",
        }

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
