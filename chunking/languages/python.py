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

        # Calculate cyclomatic complexity for functions
        if node.type == "function_definition" or (
            node.type == "decorated_definition"
            and any(c.type == "function_definition" for c in node.children)
        ):
            complexity = self._calculate_complexity(node)
            metadata["complexity_score"] = complexity

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

    def _calculate_complexity(self, node: Any) -> int:
        """Calculate cyclomatic complexity for a function.

        Cyclomatic complexity measures the number of linearly independent paths
        through a program's source code.

        Formula: CC = E - N + 2P
        Simplified for single method: CC = decision_points + 1

        Decision points in Python:
        - if/elif statements (+1 each)
        - for/while loops (+1 each)
        - except handlers (+1 each)
        - boolean operators: and, or (+1 each)
        - conditional expressions (ternary): x if cond else y (+1)
        - match/case statements (+1 per case)
        - list/dict/set comprehensions with if clause (+1)

        Args:
            node: function_definition or decorated_definition tree-sitter node

        Returns:
            Cyclomatic complexity score (minimum 1)

        Examples:
            def simple():        # CC = 1 (no branches)
                return 1

            def with_if(x):      # CC = 2 (1 if)
                if x > 0:
                    return x
                return 0

            def complex(x, y):   # CC = 4 (2 if + 1 for + 1 and)
                if x > 0:
                    for i in range(y):
                        if i % 2 == 0 and i > 10:
                            return i
                return 0
        """
        # Base complexity for the function itself
        complexity = 1

        # Find the function body
        body_node = None
        if node.type == "decorated_definition":
            # Find the function_definition child
            for child in node.children:
                if child.type == "function_definition":
                    node = child
                    break

        # Get the block (body) of the function
        for child in node.children:
            if child.type == "block":
                body_node = child
                break

        if not body_node:
            return complexity  # No body, return base complexity

        # Recursively count decision points in the function body
        complexity += self._count_decision_points(body_node)

        return complexity

    def _count_decision_points(self, node: Any) -> int:
        """Recursively count decision points in an AST node.

        Args:
            node: Tree-sitter node to analyze

        Returns:
            Number of decision points found
        """
        count = 0

        # Check current node type
        if node.type in {
            "if_statement",  # if/elif
            "for_statement",  # for loop
            "while_statement",  # while loop
            "except_clause",  # except handler
            "case_clause",  # match/case clause (Python 3.10+)
        }:
            count += 1

        # Special handling for if_statement with elif
        if node.type == "if_statement":
            # Count elif clauses (each elif is an additional decision point)
            for child in node.children:
                if child.type == "elif_clause":
                    count += 1

        # Boolean operators: and, or
        if node.type in {"boolean_operator"}:
            # Each and/or adds a decision point
            count += 1

        # Conditional expression (ternary): x if cond else y
        if node.type == "conditional_expression":
            count += 1

        # List/dict/set comprehensions with if clause
        if node.type in {
            "list_comprehension",
            "dictionary_comprehension",
            "set_comprehension",
        }:
            # Check if comprehension has an if clause
            for child in node.children:
                if child.type == "if_clause":
                    count += 1

        # Recursively process all children
        for child in node.children:
            count += self._count_decision_points(child)

        return count
