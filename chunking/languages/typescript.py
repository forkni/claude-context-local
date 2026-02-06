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

    def _load_language(self) -> Language:
        """Load tree-sitter-typescript language binding."""
        try:
            import tree_sitter_typescript as tstypescript

            if self.use_tsx:
                return Language(tstypescript.language_tsx())
            return Language(tstypescript.language_typescript())
        except ImportError as err:
            raise ValueError(
                "tree-sitter-typescript not installed. "
                "Install with: pip install tree-sitter-typescript"
            ) from err

    def _get_splittable_node_types(self) -> set[str]:
        """TypeScript-specific splittable node types."""
        return {
            "function_declaration",
            "function",
            "arrow_function",
            "class_declaration",
            "method_definition",
            "generator_function",
            "generator_function_declaration",
            "interface_declaration",
            "type_alias_declaration",
            "enum_declaration",
        }

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract TypeScript-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract name
        for child in node.children:
            if child.type in ["identifier", "type_identifier"]:
                metadata["name"] = self.get_node_text(child, source)
                break

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
