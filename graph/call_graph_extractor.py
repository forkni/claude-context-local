"""
Call graph extraction for code analysis.

Extracts function call relationships from source code using AST parsing.
Supports Python with planned support for C++/GLSL.
"""

import ast
import logging
from dataclasses import dataclass
from typing import Any

from .resolvers import AssignmentTracker, ImportResolver, TypeResolver


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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "caller_id": self.caller_id,
            "callee_name": self.callee_name,
            "line_number": self.line_number,
            "is_method_call": self.is_method_call,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CallEdge":
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

    def __init__(self) -> None:
        """Initialize the base call graph extractor.

        Attributes:
            logger: Logger instance for the extractor class.
        """
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_calls(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[CallEdge]:
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
    - Self calls: self.method() -> ClassName.method (resolved)
    - Super calls: super().method() -> ParentClass.method (resolved)
    - Nested calls: foo(bar())
    - Lambda calls: (lambda x: process(x))(value)
    - Decorator detection (not counted as calls)
    """

    def __init__(self) -> None:
        """Initialize the Python call graph extractor.

        Sets up class context tracking and initializes resolvers for type,
        import, and assignment resolution.

        Attributes:
            _current_class: Current class name being processed (for self/super resolution).
            _class_bases: Mapping of class names to their list of base classes.
            _type_resolver: TypeResolver instance for type annotation resolution.
            _import_resolver: ImportResolver instance for import statement resolution.
            _assignment_tracker: AssignmentTracker instance for variable assignment tracking.
            _type_annotations: Mapping of parameter names to their type names.
            _imports: Mapping of imported names/aliases to qualified names.
        """
        super().__init__()
        # Class context tracking for self/super resolution
        self._current_class: str | None = None
        self._class_bases: dict[
            str, list[str]
        ] = {}  # class_name -> list of base classes

        # Initialize resolvers
        self._type_resolver = TypeResolver()
        self._import_resolver = ImportResolver()
        self._assignment_tracker = AssignmentTracker()

        # Type annotation tracking - populated by resolvers
        self._type_annotations: dict[str, str] = {}  # param_name -> type_name
        # Import tracking - populated by import resolver
        self._imports: dict[str, str] = {}  # imported_name/alias -> qualified_name

    def extract_calls(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[CallEdge]:
        """
        Extract function calls from Python code.

        Args:
            code: Python source code
            chunk_metadata: Must contain 'chunk_id' key, optionally 'parent_class'

        Returns:
            List of CallEdge objects
        """
        chunk_id = chunk_metadata.get("chunk_id", "unknown")
        # Get parent class from chunk metadata (passed from chunker)
        parent_class = chunk_metadata.get("parent_class")

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.logger.debug(
                f"Syntax error parsing code for {chunk_id}: {e}. "
                f"Returning empty call list."
            )
            return []

        # Reset class context, type annotations, and imports
        self._class_bases = {}
        self._type_annotations = {}
        self._imports = {}

        # First pass: extract class hierarchy for super() resolution
        self._extract_class_hierarchy(tree)

        # Set current class context from metadata or detect from code
        if parent_class:
            self._current_class = parent_class
        else:
            # Try to detect class context from the code itself
            self._current_class = self._detect_enclosing_class(tree)

        # Extract imports for type resolution
        # Read from full file (not just chunk) to get all module-level imports
        # Must be done BEFORE local assignments since assignment tracker uses imports
        file_path = chunk_metadata.get("file_path", "")
        if file_path:
            self._imports = self._import_resolver.read_file_imports(file_path)
        else:
            # Fall back to extracting imports from chunk code (limited)
            self._imports = self._import_resolver.extract_imports(tree)

        # Update assignment tracker with current imports for alias resolution
        self._assignment_tracker.set_imports(self._imports)

        # Extract type annotations from function definition
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._type_annotations = self._type_resolver.extract_type_annotations(
                    node
                )
                break  # Only process the top-level function

        # Extract type information from local assignments
        # Note: Local assignments can shadow parameter annotations for same-named variables
        local_assignments = self._assignment_tracker.extract_local_assignments(tree)
        self._type_annotations.update(local_assignments)

        calls = []

        # Walk AST to find all Call nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_edge = self._extract_call_from_node(node, chunk_id)
                if call_edge:
                    calls.append(call_edge)

        return calls

    def _extract_class_hierarchy(self, tree: ast.AST) -> None:
        """Extract class inheritance relationships for super() resolution."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(base.attr)
                self._class_bases[node.name] = bases

    def _detect_enclosing_class(self, tree: ast.AST) -> str | None:
        """Detect if code is inside a class from AST structure."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                return node.name
        return None

    def _get_parent_class(self, class_name: str) -> str | None:
        """Get the first base class for super() resolution."""
        bases = self._class_bases.get(class_name, [])
        if bases:
            return bases[0]
        return None

    def _extract_call_from_node(self, node: ast.Call, chunk_id: str) -> CallEdge | None:
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

    def _get_call_name(self, func_node: ast.AST) -> str | None:
        """
        Extract function name from Call node's func attribute.

        Handles:
        - Simple calls: foo() -> "foo"
        - Self calls: self.method() -> "ClassName.method" (resolved)
        - Super calls: super().method() -> "ParentClass.method" (resolved)
        - Type-annotated calls: param.method() -> "TypeName.method" (resolved)
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
            receiver = func_node.value
            method_name = func_node.attr

            # Check for self/cls call - resolve to qualified name
            if isinstance(receiver, ast.Name) and receiver.id in ("self", "cls"):
                if self._current_class:
                    return f"{self._current_class}.{method_name}"
                # Fallback to bare name if no class context
                return method_name

            # Check for super() call - resolve to parent class
            if isinstance(receiver, ast.Call):
                if isinstance(receiver.func, ast.Name) and receiver.func.id == "super":
                    if self._current_class:
                        parent_class = self._get_parent_class(self._current_class)
                        if parent_class:
                            return f"{parent_class}.{method_name}"
                        # No parent class found, but we know it's a super call
                        # Return with indicator for documentation
                        return f"super.{method_name}"
                    return method_name

            # Check for type-annotated parameter or local assignment
            if isinstance(receiver, ast.Name):
                var_name = receiver.id
                if var_name in self._type_annotations:
                    type_name = self._type_annotations[var_name]
                    return f"{type_name}.{method_name}"

                # Check for imported name
                # Handles: from handlers import Handler; Handler.class_method()
                # Also handles aliased: from x import Y as Z; Z.method()
                if var_name in self._imports:
                    qualified = self._imports[var_name]
                    # Extract the class name from qualified import
                    # e.g., "handlers.Handler" -> "Handler"
                    class_name = qualified.split(".")[-1]
                    return f"{class_name}.{method_name}"

            # Check for self.attr.method() pattern
            # e.g., self.handler.handle() where self.handler = Handler()
            if isinstance(receiver, ast.Attribute):
                if isinstance(receiver.value, ast.Name):
                    if receiver.value.id in ("self", "cls"):
                        attr_key = f"{receiver.value.id}.{receiver.attr}"
                        if attr_key in self._type_annotations:
                            type_name = self._type_annotations[attr_key]
                            return f"{type_name}.{method_name}"

            # Regular method call - return bare method name
            return method_name

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
        self, ast_node: ast.AST, chunk_id: str
    ) -> list[CallEdge]:
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

    Python only
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
    def supported_languages(cls) -> list[str]:
        """Get list of supported languages."""
        return list(cls._extractors.keys())
