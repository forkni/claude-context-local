"""C-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class CChunker(LanguageChunker):
    """C-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("c", language)

    def _load_language(self) -> Language:
        """Load tree-sitter-c language binding."""
        try:
            import tree_sitter_c as tsc

            return Language(tsc.language())
        except ImportError as err:
            raise ValueError(
                "tree-sitter-c not installed. Install with: pip install tree-sitter-c"
            ) from err

    def _get_splittable_node_types(self) -> set[str]:
        """C-specific splittable node types."""
        return {
            "function_definition",
            "struct_specifier",
            "union_specifier",
            "enum_specifier",
            "type_definition",
        }

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract C-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract function name
        if node.type == "function_definition":
            # Look for function_declarator
            for child in node.children:
                if child.type == "function_declarator":
                    for declarator_child in child.children:
                        if declarator_child.type == "identifier":
                            metadata["name"] = self.get_node_text(
                                declarator_child, source
                            )
                            break
                    break

        # Extract struct/union/enum name
        elif node.type in ["struct_specifier", "union_specifier", "enum_specifier"]:
            for child in node.children:
                if child.type in ["type_identifier", "identifier"]:
                    metadata["name"] = self.get_node_text(child, source)
                    break

        # Extract typedef name
        elif node.type == "type_definition":
            # Look for the last identifier which is the new type name
            identifiers = []
            for child in node.children:
                if child.type == "identifier":
                    identifiers.append(self.get_node_text(child, source))
            if identifiers:
                metadata["name"] = identifiers[-1]

        return metadata
