"""
Call graph extraction for code analysis.

Extracts function call relationships from source code using AST parsing.
Supports Python (Phase 1) with planned support for C++/GLSL (Phase 5).
"""

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class CallEdge:
    """
    Represents a function call relationship.

    Attributes:
        caller_id: Chunk ID of the calling function
        callee_name: Name of the called function
        line_number: Line number where the call occurs
        is_method_call: Whether this is a method call (obj.method())
        confidence: Confidence score (0.0-1.0) for the call detection
    """
    caller_id: str
    callee_name: str
    line_number: int
    is_method_call: bool = False
    confidence: float = 1.0  # Static analysis has high confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "caller_id": self.caller_id,
            "callee_name": self.callee_name,
            "line_number": self.line_number,
            "is_method_call": self.is_method_call,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallEdge":
        """Create from dictionary."""
        return cls(
            caller_id=data["caller_id"],
            callee_name=data["callee_name"],
            line_number=data["line_number"],
            is_method_call=data.get("is_method_call", False),
            confidence=data.get("confidence", 1.0),
        )


class CallGraphExtractor:
    """
    Base class for language-specific call graph extractors.

    Subclasses implement extract_calls() for specific languages.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_calls(
        self,
        code: str,
        chunk_metadata: Dict[str, Any]
    ) -> List[CallEdge]:
        """
        Extract function calls from code.

        Args:
            code: Source code to analyze
            chunk_metadata: Metadata about the code chunk (chunk_id, file_path, etc.)

        Returns:
            List of CallEdge objects representing function calls
        """
        raise NotImplementedError("Subclasses must implement extract_calls()")


class PythonCallGraphExtractor(CallGraphExtractor):
    """
    Extract call graph from Python source code using AST.

    Features:
    - Function calls: foo()
    - Method calls: obj.method()
    - Nested calls: foo(bar())
    - Lambda calls: (lambda x: process(x))(value)
    - Decorator detection (not counted as calls)
    """

    def extract_calls(
        self,
        code: str,
        chunk_metadata: Dict[str, Any]
    ) -> List[CallEdge]:
        """
        Extract function calls from Python code.

        Args:
            code: Python source code
            chunk_metadata: Must contain 'chunk_id' key

        Returns:
            List of CallEdge objects
        """
        chunk_id = chunk_metadata.get("chunk_id", "unknown")

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.logger.warning(
                f"Syntax error parsing code for {chunk_id}: {e}. "
                f"Returning empty call list."
            )
            return []

        calls = []

        # Walk AST to find all Call nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_edge = self._extract_call_from_node(node, chunk_id)
                if call_edge:
                    calls.append(call_edge)

        return calls

    def _extract_call_from_node(
        self,
        node: ast.Call,
        chunk_id: str
    ) -> Optional[CallEdge]:
        """
        Extract CallEdge from an ast.Call node.

        Args:
            node: AST Call node
            chunk_id: Chunk ID of the calling code

        Returns:
            CallEdge if call could be extracted, None otherwise
        """
        callee_name = self._get_call_name(node.func)

        if not callee_name:
            return None

        # Determine if this is a method call
        is_method = isinstance(node.func, ast.Attribute)

        # Get line number
        line_number = getattr(node, "lineno", 0)

        return CallEdge(
            caller_id=chunk_id,
            callee_name=callee_name,
            line_number=line_number,
            is_method_call=is_method,
            confidence=1.0,  # Static AST analysis has high confidence
        )

    def _get_call_name(self, func_node: ast.AST) -> Optional[str]:
        """
        Extract function name from Call node's func attribute.

        Handles:
        - Simple calls: foo() -> "foo"
        - Method calls: obj.method() -> "method"
        - Attribute chains: obj.attr.method() -> "method"
        - Nested calls: foo(bar())() -> "foo" (for outer call)
        - Lambda: (lambda x: x)() -> "lambda"

        Args:
            func_node: The func attribute of an ast.Call node

        Returns:
            Function name or None if it couldn't be determined
        """
        if isinstance(func_node, ast.Name):
            # Simple function call: foo()
            return func_node.id

        elif isinstance(func_node, ast.Attribute):
            # Method call: obj.method()
            # Return just the method name, not the full chain
            return func_node.attr

        elif isinstance(func_node, ast.Call):
            # Nested call: foo(bar())()
            # This is a call on the result of another call
            # Mark as "call_result" to indicate dynamic call
            return "call_result"

        elif isinstance(func_node, ast.Lambda):
            # Lambda call: (lambda x: x)()
            return "lambda"

        elif isinstance(func_node, ast.Subscript):
            # Subscript call: obj[key]()
            # This is calling the result of a subscript operation
            return "subscript_result"

        else:
            # Unknown call type
            self.logger.debug(
                f"Unknown call type: {func_node.__class__.__name__}. "
                f"Skipping call extraction."
            )
            return None

    def extract_calls_from_ast_node(
        self,
        ast_node: ast.AST,
        chunk_id: str
    ) -> List[CallEdge]:
        """
        Extract calls from a specific AST node (for integration with chunking).

        This method is useful when you already have an AST node from chunking
        and want to extract calls without re-parsing.

        Args:
            ast_node: AST node to analyze (e.g., FunctionDef, ClassDef)
            chunk_id: Chunk ID for the node

        Returns:
            List of CallEdge objects
        """
        calls = []

        for node in ast.walk(ast_node):
            if isinstance(node, ast.Call):
                call_edge = self._extract_call_from_node(node, chunk_id)
                if call_edge:
                    calls.append(call_edge)

        return calls


class CallGraphExtractorFactory:
    """
    Factory for creating language-specific call graph extractors.

    Phase 1: Python only
    Phase 5: Add C++, GLSL support
    """

    _extractors = {
        "python": PythonCallGraphExtractor,
        # Future: "cpp": CppCallGraphExtractor,
        # Future: "glsl": GLSLCallGraphExtractor,
    }

    @classmethod
    def create(cls, language: str) -> CallGraphExtractor:
        """
        Create appropriate extractor for language.

        Args:
            language: Language name (e.g., "python", "cpp", "glsl")

        Returns:
            CallGraphExtractor instance

        Raises:
            ValueError: If language is not supported
        """
        language_lower = language.lower()
        extractor_class = cls._extractors.get(language_lower)

        if not extractor_class:
            supported = ", ".join(cls._extractors.keys())
            raise ValueError(
                f"No call graph extractor for language: {language}. "
                f"Supported languages: {supported}"
            )

        return extractor_class()

    @classmethod
    def is_supported(cls, language: str) -> bool:
        """Check if language is supported."""
        return language.lower() in cls._extractors

    @classmethod
    def supported_languages(cls) -> List[str]:
        """Get list of supported languages."""
        return list(cls._extractors.keys())
