"""GLSL-specific chunker using tree-sitter."""

import warnings
from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class GLSLChunker(LanguageChunker):
    """GLSL-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("glsl", language)

    def _load_language(self) -> Language:
        """Load tree-sitter-glsl language binding."""
        try:
            import tree_sitter_glsl as tsglsl

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", message="int argument support is deprecated"
                )
                return Language(tsglsl.language())
        except ImportError as err:
            raise ValueError(
                "tree-sitter-glsl not installed. "
                "Install with: pip install tree-sitter-glsl"
            ) from err

    def _get_splittable_node_types(self) -> set[str]:
        """GLSL-specific splittable node types."""
        return {
            "function_definition",  # Function definitions (main, custom functions)
            "struct_declaration",  # Struct definitions
            "variable_declaration",  # Uniform, varying, attribute declarations
            "preprocessor_define",  # #define statements
            "preprocessor_function_def",  # #define with parameters
            "preprocessor_include",  # #include statements
            "preprocessor_ifdef",  # Conditional compilation
            "preprocessor_ifndef",  # Conditional compilation
            "layout_qualifier_statement",  # Layout qualifiers
            "uniform_block",  # Uniform buffer objects
            "interface_block",  # Interface blocks
            "block_statement",  # Large code blocks
            "compound_statement",  # Compound statements
            "subroutine_definition",  # Subroutine definitions
            "precision_statement",  # Precision qualifiers
        }

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract GLSL-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract function name
        if node.type == "function_definition":
            # Look for function_declarator or identifier
            for child in node.children:
                if child.type == "function_declarator":
                    for declarator_child in child.children:
                        if declarator_child.type == "identifier":
                            metadata["name"] = self.get_node_text(
                                declarator_child, source
                            )
                            break
                    break
                elif child.type == "identifier":
                    metadata["name"] = self.get_node_text(child, source)
                    break

        # Extract struct name
        elif node.type == "struct_declaration":
            for child in node.children:
                if child.type in ["type_identifier", "identifier"]:
                    metadata["name"] = self.get_node_text(child, source)
                    break

        # Extract variable declarations (uniforms, varying, attributes)
        elif node.type == "variable_declaration":
            # Look for storage qualifiers and variable names
            storage_qualifiers = []
            var_names = []

            for child in node.children:
                if child.type in [
                    "uniform",
                    "varying",
                    "attribute",
                    "in",
                    "out",
                    "const",
                ]:
                    storage_qualifiers.append(self.get_node_text(child, source))
                elif child.type == "identifier":
                    var_names.append(self.get_node_text(child, source))

            if storage_qualifiers:
                metadata["storage_qualifiers"] = storage_qualifiers
            if var_names:
                metadata["name"] = ", ".join(var_names)
                metadata["variable_names"] = var_names

        # Extract preprocessor definitions
        elif node.type in ["preprocessor_define", "preprocessor_function_def"]:
            for child in node.children:
                if child.type == "identifier":
                    metadata["name"] = self.get_node_text(child, source)
                    break

        # Check for GLSL-specific features
        node_text = self.get_node_text(node, source).lower()

        # Check for shader stage indicators
        if any(
            keyword in node_text
            for keyword in ["gl_position", "gl_fragcoord", "gl_fragcolor"]
        ):
            metadata["has_builtin_vars"] = True

        # Check for texture operations
        if any(
            keyword in node_text
            for keyword in ["texture", "texturelod", "texture2d", "sampler"]
        ):
            metadata["has_texture_ops"] = True

        # Check for mathematical operations
        if any(
            keyword in node_text
            for keyword in ["dot", "cross", "normalize", "length", "mix", "smoothstep"]
        ):
            metadata["has_math_ops"] = True

        return metadata
