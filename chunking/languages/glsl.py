"""GLSL-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


class GLSLChunker(LanguageChunker):
    """GLSL-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("glsl", language)

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
