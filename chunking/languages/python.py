"""Python-specific chunker using tree-sitter.

Note: This is the tree-sitter based Python chunker for consistency with
other languages. The main Python chunker used by the system is the AST-based
one in chunking/python_chunker.py which provides better Python-specific analysis.
"""

from typing import Any, Dict, Optional, Set

from tree_sitter import Language

from .base import LanguageChunker


class PythonChunker(LanguageChunker):
    """Python-specific chunker using tree-sitter."""

    def __init__(self, language: Optional[Language] = None):
        super().__init__("python", language)

    def _load_language(self) -> Language:
        """Load tree-sitter-python language binding."""
        try:
            import tree_sitter_python as tspython

            return Language(tspython.language())
        except ImportError as err:
            raise ValueError(
                "tree-sitter-python not installed. "
                "Install with: pip install tree-sitter-python"
            ) from err

    def _get_splittable_node_types(self) -> Set[str]:
        """Python-specific splittable node types."""
        return {
            "function_definition",
            "class_definition",
            "decorated_definition",
        }

    def _get_block_boundary_types(self) -> Set[str]:
        """Python-specific block boundary types for splitting large functions.

        These node types represent logical split points in Python code.

        Returns:
            Set of Python tree-sitter node types
        """
        return {
            "for_statement",  # for loops
            "if_statement",  # if/elif/else blocks
            "while_statement",  # while loops
            "try_statement",  # try/except/finally blocks
            "with_statement",  # context managers
            "match_statement",  # match/case (Python 3.10+)
        }

    def _extract_signature(self, node: Any, source_bytes: bytes) -> str:
        """Extract Python function signature including decorators.

        Handles:
        - Simple functions: def foo(args):
        - Decorated functions: @decorator\\ndef foo(args):
        - Async functions: async def foo(args):

        Args:
            node: function_definition or decorated_definition node
            source_bytes: Source code bytes

        Returns:
            Complete signature string
        """
        content = self.get_node_text(node, source_bytes)
        lines = content.split("\n")

        sig_lines = []
        seen_def = False
        for line in lines:
            sig_lines.append(line)
            stripped = line.strip()

            # Track if we've seen the def line
            if stripped.startswith(("def ", "async def ")):
                seen_def = True

            # Stop after finding a line ending with ':' (after seeing def)
            if seen_def and stripped.endswith(":"):
                break

        return "\n".join(sig_lines)

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract Python-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract function/class name
        for child in node.children:
            if child.type == "identifier":
                metadata["name"] = self.get_node_text(child, source)
                break

        # Extract decorators if present
        if node.type == "decorated_definition":
            decorators = []
            for child in node.children:
                if child.type == "decorator":
                    decorators.append(self.get_node_text(child, source))
            metadata["decorators"] = decorators

            # Get the actual definition node
            for child in node.children:
                if child.type in ["function_definition", "class_definition"]:
                    # Get name from the actual definition
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            metadata["name"] = self.get_node_text(subchild, source)
                            break

        # Extract docstring for functions and classes
        docstring = self._extract_docstring(node, source)
        if docstring:
            metadata["docstring"] = docstring

        # Count parameters for functions
        if node.type == "function_definition" or (
            node.type == "decorated_definition"
            and any(c.type == "function_definition" for c in node.children)
        ):
            for child in node.children:
                if child.type == "parameters":
                    # Count parameter nodes
                    param_count = sum(
                        1
                        for c in child.children
                        if c.type
                        in ["identifier", "typed_parameter", "default_parameter"]
                    )
                    metadata["param_count"] = param_count
                    break

        return metadata

    def _extract_docstring(self, node: Any, source: bytes) -> Optional[str]:
        """Extract docstring from function or class definition."""
        # Find the body/block of the function or class
        body_node = None
        for child in node.children:
            if child.type == "block":
                body_node = child
                break
            elif child.type in ["function_definition", "class_definition"]:
                # Handle decorated definitions
                for subchild in child.children:
                    if subchild.type == "block":
                        body_node = subchild
                        break

        if not body_node or not body_node.children:
            return None

        # Check if the first statement in the body is a string literal
        first_statement = body_node.children[0]
        if first_statement.type == "expression_statement":
            # Check if it contains a string literal
            for child in first_statement.children:
                if child.type == "string":
                    docstring_text = self.get_node_text(child, source)
                    # Clean up the docstring - remove quotes and normalize whitespace
                    if docstring_text.startswith('"""') or docstring_text.startswith(
                        "'''"
                    ):
                        docstring_text = docstring_text[3:-3]
                    elif docstring_text.startswith('"') or docstring_text.startswith(
                        "'"
                    ):
                        docstring_text = docstring_text[1:-1]
                    return docstring_text.strip()

        return None
