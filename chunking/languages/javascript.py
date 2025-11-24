"""JavaScript-specific chunker using tree-sitter."""

from typing import Any, Dict, Optional, Set

from tree_sitter import Language

from .base import LanguageChunker


class JavaScriptChunker(LanguageChunker):
    """JavaScript-specific chunker using tree-sitter."""

    def __init__(self, language: Optional[Language] = None):
        super().__init__("javascript", language)

    def _load_language(self) -> Language:
        """Load tree-sitter-javascript language binding."""
        try:
            import tree_sitter_javascript as tsjavascript

            return Language(tsjavascript.language())
        except ImportError as err:
            raise ValueError(
                "tree-sitter-javascript not installed. "
                "Install with: pip install tree-sitter-javascript"
            ) from err

    def _get_splittable_node_types(self) -> Set[str]:
        """JavaScript-specific splittable node types."""
        return {
            "function_declaration",
            "function",
            "arrow_function",
            "class_declaration",
            "method_definition",
            "generator_function",
            "generator_function_declaration",
        }

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract JavaScript-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract function/class name
        for child in node.children:
            if child.type == "identifier":
                metadata["name"] = self.get_node_text(child, source)
                break

        # Check for async
        if node.children and self.get_node_text(node.children[0], source) == "async":
            metadata["is_async"] = True

        # Check for generator
        if "generator" in node.type:
            metadata["is_generator"] = True

        return metadata
