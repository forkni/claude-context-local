"""C++-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class CppChunker(LanguageChunker):
    """C++-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("cpp", language)

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract C++-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract name
        if node.type == "function_definition":
            # Look for function_declarator
            for child in node.children:
                if child.type == "function_declarator":
                    for declarator_child in child.children:
                        if declarator_child.type in [
                            "identifier",
                            "qualified_identifier",
                        ]:
                            metadata["name"] = self.get_node_text(
                                declarator_child, source
                            )
                            break
                    break

        elif node.type in [
            "class_specifier",
            "struct_specifier",
            "namespace_definition",
        ]:
            for child in node.children:
                if child.type in ["type_identifier", "identifier"]:
                    metadata["name"] = self.get_node_text(child, source)
                    break

        # Check for template parameters
        if node.type == "template_declaration":
            metadata["is_template"] = True
            # Get the templated entity name
            for child in node.children:
                if child.type in ["function_definition", "class_specifier"]:
                    child_metadata = self.extract_metadata(child, source)
                    if "name" in child_metadata:
                        metadata["name"] = child_metadata["name"]
                    break

        return metadata
