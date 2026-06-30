"""Go-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class GoChunker(LanguageChunker):
    """Go-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("go", language)

    def _extra_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Add Go-specific extras: receiver_type for method declarations."""
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
