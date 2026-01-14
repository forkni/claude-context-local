"""Go-specific chunker using tree-sitter."""

from typing import Any, Optional

from tree_sitter import Language

from .base import LanguageChunker


class GoChunker(LanguageChunker):
    """Go-specific chunker using tree-sitter."""

    def __init__(self, language: Optional[Language] = None) -> None:
        super().__init__("go", language)

    def _load_language(self) -> Language:
        """Load tree-sitter-go language binding."""
        try:
            import tree_sitter_go as tsgo

            return Language(tsgo.language())
        except ImportError as err:
            raise ValueError(
                "tree-sitter-go not installed. "
                "Install with: pip install tree-sitter-go"
            ) from err

    def _get_splittable_node_types(self) -> set[str]:
        """Go-specific splittable node types."""
        return {
            "function_declaration",
            "method_declaration",
            "type_declaration",
            "interface_declaration",
            "struct_declaration",
        }

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract Go-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract function/method/type name
        for child in node.children:
            if child.type == "identifier":
                metadata["name"] = self.get_node_text(child, source)
                break

        # For methods, extract receiver type
        if node.type == "method_declaration":
            for child in node.children:
                if child.type == "parameter_list":
                    # First parameter_list is the receiver
                    for receiver_child in child.children:
                        if receiver_child.type == "parameter_declaration":
                            for param_child in receiver_child.children:
                                if param_child.type in [
                                    "identifier",
                                    "pointer_type",
                                    "type_identifier",
                                ]:
                                    metadata["receiver_type"] = self.get_node_text(
                                        param_child, source
                                    )
                                    break
                            break
                    break

        return metadata
