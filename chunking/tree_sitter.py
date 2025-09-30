"""Fixed tree-sitter based code chunker using correct API."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tree_sitter import Language, Parser

logger = logging.getLogger(__name__)

# Try to import language bindings
AVAILABLE_LANGUAGES = {}

try:
    import tree_sitter_python as tspython

    AVAILABLE_LANGUAGES["python"] = Language(tspython.language())
except ImportError:
    logger.debug("tree-sitter-python not installed")

try:
    import tree_sitter_javascript as tsjavascript

    AVAILABLE_LANGUAGES["javascript"] = Language(tsjavascript.language())
except ImportError:
    logger.debug("tree-sitter-javascript not installed")

try:
    import tree_sitter_typescript as tstypescript

    # TypeScript has two grammars: typescript and tsx
    AVAILABLE_LANGUAGES["typescript"] = Language(tstypescript.language_typescript())
    AVAILABLE_LANGUAGES["tsx"] = Language(tstypescript.language_tsx())
except ImportError:
    logger.debug("tree-sitter-typescript not installed")

try:
    # JavaScript also supports JSX
    import tree_sitter_javascript as tsjavascript

    if "javascript" not in AVAILABLE_LANGUAGES:
        AVAILABLE_LANGUAGES["javascript"] = Language(tsjavascript.language())
    # JSX uses the same parser as JavaScript
    AVAILABLE_LANGUAGES["jsx"] = AVAILABLE_LANGUAGES["javascript"]
except ImportError:
    logger.debug("tree-sitter-javascript not installed for JSX")

try:
    import tree_sitter_svelte as tssvelte

    AVAILABLE_LANGUAGES["svelte"] = Language(tssvelte.language())
except ImportError:
    logger.debug("tree-sitter-svelte not installed")

try:
    import tree_sitter_go as tsgo

    AVAILABLE_LANGUAGES["go"] = Language(tsgo.language())
except ImportError:
    logger.debug("tree-sitter-go not installed")

try:
    import tree_sitter_rust as tsrust

    AVAILABLE_LANGUAGES["rust"] = Language(tsrust.language())
except ImportError:
    logger.debug("tree-sitter-rust not installed")

try:
    import tree_sitter_java as tsjava

    AVAILABLE_LANGUAGES["java"] = Language(tsjava.language())
except ImportError:
    logger.debug("tree-sitter-java not installed")

try:
    import tree_sitter_c as tsc

    AVAILABLE_LANGUAGES["c"] = Language(tsc.language())
except ImportError:
    logger.debug("tree-sitter-c not installed")

try:
    import tree_sitter_cpp as tscpp

    AVAILABLE_LANGUAGES["cpp"] = Language(tscpp.language())
except ImportError:
    logger.debug("tree-sitter-cpp not installed")

try:
    import tree_sitter_c_sharp as tscsharp

    AVAILABLE_LANGUAGES["csharp"] = Language(tscsharp.language())
except ImportError:
    logger.debug("tree-sitter-c-sharp not installed")

try:
    import warnings

    import tree_sitter_glsl as tsglsl

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="int argument support is deprecated")
        AVAILABLE_LANGUAGES["glsl"] = Language(tsglsl.language())
except ImportError:
    logger.debug("tree-sitter-glsl not installed")


@dataclass
class TreeSitterChunk:
    """Represents a code chunk extracted using tree-sitter."""

    content: str
    start_line: int
    end_line: int
    node_type: str
    language: str
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None  # unique identifier for evaluation

    def to_dict(self) -> Dict:
        """Convert to dictionary format compatible with existing system."""
        return {
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "type": self.node_type,
            "language": self.language,
            "metadata": self.metadata,
        }


class LanguageChunker(ABC):
    """Abstract base class for language-specific chunkers."""

    def __init__(self, language_name: str):
        """Initialize language chunker.

        Args:
            language_name: Programming language name
        """
        self.language_name = language_name
        if language_name not in AVAILABLE_LANGUAGES:
            raise ValueError(
                f"Language {language_name} not available. Install tree-sitter-{language_name}"
            )

        self.language = AVAILABLE_LANGUAGES[language_name]
        self.parser = Parser(self.language)
        self.splittable_node_types = self._get_splittable_node_types()

    @abstractmethod
    def _get_splittable_node_types(self) -> Set[str]:
        """Get node types that should be split into chunks.

        Returns:
            Set of node type names
        """
        pass

    @abstractmethod
    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract metadata from a node.

        Args:
            node: Tree-sitter node
            source: Source code bytes

        Returns:
            Metadata dictionary
        """
        pass

    def should_chunk_node(self, node: Any) -> bool:
        """Check if a node should be chunked.

        Args:
            node: Tree-sitter node

        Returns:
            True if node should be chunked
        """
        return node.type in self.splittable_node_types

    def get_node_text(self, node: Any, source: bytes) -> str:
        """Get text content of a node.

        Args:
            node: Tree-sitter node
            source: Source code bytes

        Returns:
            Text content
        """
        return source[node.start_byte : node.end_byte].decode("utf-8")

    def get_line_numbers(self, node: Any) -> Tuple[int, int]:
        """Get start and end line numbers for a node.

        Args:
            node: Tree-sitter node

        Returns:
            Tuple of (start_line, end_line)
        """
        # Tree-sitter uses 0-based indexing, convert to 1-based
        return node.start_point[0] + 1, node.end_point[0] + 1

    def chunk_code(self, source_code: str) -> List[TreeSitterChunk]:
        """Chunk source code into semantic units.

        Args:
            source_code: Source code string

        Returns:
            List of TreeSitterChunk objects
        """
        source_bytes = bytes(source_code, "utf-8")
        tree = self.parser.parse(source_bytes)
        chunks = []

        def traverse(node, depth=0, parent_info=None):
            """Recursively traverse the tree and extract chunks."""
            if self.should_chunk_node(node):
                start_line, end_line = self.get_line_numbers(node)
                content = self.get_node_text(node, source_bytes)
                metadata = self.extract_metadata(node, source_bytes)

                # Add parent information if available
                if parent_info:
                    metadata.update(parent_info)

                chunk = TreeSitterChunk(
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    node_type=node.type,
                    language=self.language_name,
                    metadata=metadata,
                )
                chunks.append(chunk)

                # For classes, continue traversing to find methods
                # For other chunked nodes, stop traversal
                if node.type in ["class_definition", "class_declaration"]:
                    # Pass class info to children
                    class_info = {
                        "parent_name": metadata.get("name"),
                        "parent_type": "class",
                    }
                    for child in node.children:
                        traverse(child, depth + 1, class_info)
                return

            # Traverse children, passing along parent info
            for child in node.children:
                traverse(child, depth + 1, parent_info)

        traverse(tree.root_node)

        # If no chunks found, create a single module-level chunk
        if not chunks and source_code.strip():
            chunks.append(
                TreeSitterChunk(
                    content=source_code,
                    start_line=1,
                    end_line=len(source_code.split("\n")),
                    node_type="module",
                    language=self.language_name,
                    metadata={"type": "module"},
                )
            )

        return chunks


class PythonChunker(LanguageChunker):
    """Python-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("python")

    def _get_splittable_node_types(self) -> Set[str]:
        """Python-specific splittable node types."""
        return {
            "function_definition",
            "class_definition",
            "decorated_definition",
        }

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


class JavaScriptChunker(LanguageChunker):
    """JavaScript-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("javascript")

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


class TypeScriptChunker(LanguageChunker):
    """TypeScript-specific chunker using tree-sitter."""

    def __init__(self, use_tsx: bool = False):
        super().__init__("tsx" if use_tsx else "typescript")
        self.use_tsx = use_tsx

    def _get_splittable_node_types(self) -> Set[str]:
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

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
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


class JSXChunker(JavaScriptChunker):
    """JSX-specific chunker (extends JavaScript chunker)."""

    def __init__(self):
        # JSX uses the JavaScript parser
        super().__init__()

    def _get_splittable_node_types(self) -> Set[str]:
        """JSX-specific splittable node types."""
        types = super()._get_splittable_node_types()
        # Add JSX-specific patterns
        types.add("jsx_element")
        types.add("jsx_self_closing_element")
        return types

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract JSX-specific metadata."""
        metadata = super().extract_metadata(node, source)

        # Check if it's a React component (function returning JSX)
        if node.type in ["function_declaration", "arrow_function", "function"]:
            # Simple heuristic: check if body contains JSX
            body_text = self.get_node_text(node, source)
            if "<" in body_text and (
                "jsx" in body_text.lower() or "return" in body_text
            ):
                metadata["is_component"] = True

        return metadata


class SvelteChunker(LanguageChunker):
    """Svelte-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("svelte")

    def _get_splittable_node_types(self) -> Set[str]:
        """Svelte-specific splittable node types."""
        return {
            "script_element",
            "style_element",
            "function_declaration",
            "function",
            "arrow_function",
            "class_declaration",
            "method_definition",
        }

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract Svelte-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract script type (module or instance)
        if node.type == "script_element":
            for child in node.children:
                if child.type == "start_tag":
                    tag_text = self.get_node_text(child, source)
                    if 'context="module"' in tag_text:
                        metadata["script_type"] = "module"
                    else:
                        metadata["script_type"] = "instance"
                    break

        # Extract style scope
        elif node.type == "style_element":
            for child in node.children:
                if child.type == "start_tag":
                    tag_text = self.get_node_text(child, source)
                    if "global" in tag_text:
                        metadata["style_scope"] = "global"
                    else:
                        metadata["style_scope"] = "component"
                    break

        # Extract function/class names
        for child in node.children:
            if child.type == "identifier":
                metadata["name"] = self.get_node_text(child, source)
                break

        return metadata


class GoChunker(LanguageChunker):
    """Go-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("go")

    def _get_splittable_node_types(self) -> Set[str]:
        """Go-specific splittable node types."""
        return {
            "function_declaration",
            "method_declaration",
            "type_declaration",
            "interface_declaration",
            "struct_declaration",
        }

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract Go-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract function/method/type name
        for child in node.children:
            if child.type == "identifier":
                metadata["name"] = self.get_node_text(child, source)
                break

        # For methods, extract receiver type
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

        return metadata


class RustChunker(LanguageChunker):
    """Rust-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("rust")

    def _get_splittable_node_types(self) -> Set[str]:
        """Rust-specific splittable node types."""
        return {
            "function_item",
            "impl_item",
            "struct_item",
            "enum_item",
            "trait_item",
            "mod_item",
            "macro_definition",
        }

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract Rust-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract name (identifier or type_identifier)
        for child in node.children:
            if child.type in ["identifier", "type_identifier"]:
                metadata["name"] = self.get_node_text(child, source)
                break

        # Check for async functions
        if node.type == "function_item":
            for child in node.children:
                if (
                    child.type == "async"
                    or self.get_node_text(child, source) == "async"
                ):
                    metadata["is_async"] = True
                    break

        # Extract impl type for impl blocks
        if node.type == "impl_item":
            for child in node.children:
                if child.type in ["type_identifier", "generic_type"]:
                    metadata["impl_type"] = self.get_node_text(child, source)
                    break

        return metadata


class JavaChunker(LanguageChunker):
    """Java-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("java")

    def _get_splittable_node_types(self) -> Set[str]:
        """Java-specific splittable node types."""
        return {
            "method_declaration",
            "constructor_declaration",
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "annotation_type_declaration",
        }

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract Java-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract name
        for child in node.children:
            if child.type == "identifier":
                metadata["name"] = self.get_node_text(child, source)
                break

        # Extract access modifiers
        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type in [
                        "public",
                        "private",
                        "protected",
                        "static",
                        "final",
                        "abstract",
                        "synchronized",
                    ]:
                        modifiers.append(self.get_node_text(modifier, source))

        if modifiers:
            metadata["modifiers"] = modifiers

        # Check for generic parameters
        for child in node.children:
            if child.type == "type_parameters":
                metadata["has_generics"] = True
                break

        return metadata


class CChunker(LanguageChunker):
    """C-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("c")

    def _get_splittable_node_types(self) -> Set[str]:
        """C-specific splittable node types."""
        return {
            "function_definition",
            "struct_specifier",
            "union_specifier",
            "enum_specifier",
            "type_definition",
        }

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract C-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract function name
        if node.type == "function_definition":
            # Look for function_declarator
            for child in node.children:
                if child.type == "function_declarator":
                    for declarator_child in child.children:
                        if declarator_child.type == "identifier":
                            metadata["name"] = self.get_node_text(
                                declarator_child, source
                            )
                            break
                    break

        # Extract struct/union/enum name
        elif node.type in ["struct_specifier", "union_specifier", "enum_specifier"]:
            for child in node.children:
                if child.type in ["type_identifier", "identifier"]:
                    metadata["name"] = self.get_node_text(child, source)
                    break

        # Extract typedef name
        elif node.type == "type_definition":
            # Look for the last identifier which is the new type name
            identifiers = []
            for child in node.children:
                if child.type == "identifier":
                    identifiers.append(self.get_node_text(child, source))
            if identifiers:
                metadata["name"] = identifiers[-1]

        return metadata


class CppChunker(LanguageChunker):
    """C++-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("cpp")

    def _get_splittable_node_types(self) -> Set[str]:
        """C++-specific splittable node types."""
        return {
            "function_definition",
            "class_specifier",
            "struct_specifier",
            "union_specifier",
            "enum_specifier",
            "namespace_definition",
            "template_declaration",
            "concept_definition",
        }

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
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


class CSharpChunker(LanguageChunker):
    """C#-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("csharp")

    def _get_splittable_node_types(self) -> Set[str]:
        """C#-specific splittable node types."""
        return {
            "method_declaration",
            "constructor_declaration",
            "destructor_declaration",
            "class_declaration",
            "struct_declaration",
            "interface_declaration",
            "enum_declaration",
            "namespace_declaration",
            "property_declaration",
            "event_declaration",
        }

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract C#-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract name
        for child in node.children:
            if child.type == "identifier":
                metadata["name"] = self.get_node_text(child, source)
                break

        # Extract access modifiers
        modifiers = []
        for child in node.children:
            if child.type == "modifier":
                modifier_text = self.get_node_text(child, source)
                if modifier_text in [
                    "public",
                    "private",
                    "protected",
                    "internal",
                    "static",
                    "virtual",
                    "abstract",
                    "override",
                    "async",
                ]:
                    modifiers.append(modifier_text)

        if modifiers:
            metadata["modifiers"] = modifiers
            if "async" in modifiers:
                metadata["is_async"] = True

        # Check for generic parameters
        for child in node.children:
            if child.type == "type_parameter_list":
                metadata["has_generics"] = True
                break

        return metadata


class GLSLChunker(LanguageChunker):
    """GLSL-specific chunker using tree-sitter."""

    def __init__(self):
        super().__init__("glsl")

    def _get_splittable_node_types(self) -> Set[str]:
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

    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
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


class TreeSitterChunker:
    """Main tree-sitter chunker that delegates to language-specific implementations."""

    # Map file extensions to chunker classes and language names
    LANGUAGE_MAP = {
        ".py": ("python", PythonChunker),
        ".js": ("javascript", JavaScriptChunker),
        ".jsx": ("jsx", JSXChunker),
        ".ts": ("typescript", lambda: TypeScriptChunker(use_tsx=False)),
        ".tsx": ("tsx", lambda: TypeScriptChunker(use_tsx=True)),
        ".svelte": ("svelte", SvelteChunker),
        ".go": ("go", GoChunker),
        ".rs": ("rust", RustChunker),
        ".java": ("java", JavaChunker),
        ".c": ("c", CChunker),
        ".cpp": ("cpp", CppChunker),
        ".cc": ("cpp", CppChunker),
        ".cxx": ("cpp", CppChunker),
        ".c++": ("cpp", CppChunker),
        ".cs": ("csharp", CSharpChunker),
        ".glsl": ("glsl", GLSLChunker),
        ".frag": ("glsl", GLSLChunker),
        ".vert": ("glsl", GLSLChunker),
        ".comp": ("glsl", GLSLChunker),
        ".geom": ("glsl", GLSLChunker),
        ".tesc": ("glsl", GLSLChunker),
        ".tese": ("glsl", GLSLChunker),
    }

    def __init__(self):
        """Initialize the tree-sitter chunker."""
        self.chunkers = {}

    def get_chunker(self, file_path: str) -> Optional[LanguageChunker]:
        """Get the appropriate chunker for a file.

        Args:
            file_path: Path to the file

        Returns:
            LanguageChunker instance or None if unsupported
        """
        suffix = Path(file_path).suffix.lower()

        if suffix not in self.LANGUAGE_MAP:
            return None

        language_name, chunker_class = self.LANGUAGE_MAP[suffix]

        # Check if language is available
        if language_name not in AVAILABLE_LANGUAGES:
            logger.debug(
                f"Language {language_name} not available. Install tree-sitter-{language_name}"
            )
            return None

        # Lazy initialization of chunkers
        if suffix not in self.chunkers:
            try:
                # Handle both class and lambda/factory function
                if callable(chunker_class):
                    self.chunkers[suffix] = chunker_class()
                else:
                    self.chunkers[suffix] = chunker_class
            except Exception as e:
                logger.warning(f"Failed to initialize chunker for {suffix}: {e}")
                return None

        return self.chunkers[suffix]

    def chunk_file(
        self, file_path: str, content: Optional[str] = None
    ) -> List[TreeSitterChunk]:
        """Chunk a file into semantic units.

        Args:
            file_path: Path to the file
            content: Optional file content (will read from file if not provided)

        Returns:
            List of TreeSitterChunk objects
        """
        chunker = self.get_chunker(file_path)

        if not chunker:
            logger.debug(f"No tree-sitter chunker available for {file_path}")
            return []

        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                logger.warning(f"UTF-8 decode failed for {file_path}, trying with error handling")
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Failed to read file {file_path}: {e}")
                    return []
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                return []

        try:
            return chunker.chunk_code(content)
        except Exception as e:
            logger.warning(f"Tree-sitter parsing failed for {file_path}: {e}")
            return []

    def is_supported(self, file_path: str) -> bool:
        """Check if a file type is supported.

        Args:
            file_path: Path to the file

        Returns:
            True if file type is supported
        """
        suffix = Path(file_path).suffix.lower()
        if suffix not in self.LANGUAGE_MAP:
            return False

        language_name, _ = self.LANGUAGE_MAP[suffix]
        return language_name in AVAILABLE_LANGUAGES

    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get list of supported file extensions.

        Returns:
            List of file extensions
        """
        supported = []
        for ext, (lang_name, _) in cls.LANGUAGE_MAP.items():
            if lang_name in AVAILABLE_LANGUAGES:
                supported.append(ext)
        return supported

    @classmethod
    def get_available_languages(cls) -> List[str]:
        """Get list of available languages.

        Returns:
            List of language names
        """
        return list(AVAILABLE_LANGUAGES.keys())
