"""Language and file type registry for code chunking.

Centralizes supported extensions, ignored directories, and node type mappings
used across the chunking and indexing subsystems.
"""

from typing import Dict, Set

# Supported file extensions for code chunking
SUPPORTED_EXTENSIONS: Set[str] = {
    ".py",  # Python
    ".js",  # JavaScript
    ".ts",  # TypeScript
    ".tsx",  # TSX
    ".go",  # Go
    ".rs",  # Rust
    ".c",  # C
    ".cpp",  # C++
    ".cc",  # C++
    ".cxx",  # C++
    ".c++",  # C++
    ".cs",  # C#
    ".glsl",  # GLSL shader
    ".frag",  # Fragment shader
    ".vert",  # Vertex shader
    ".comp",  # Compute shader
    ".geom",  # Geometry shader
    ".tesc",  # Tessellation control shader
    ".tese",  # Tessellation evaluation shader
}


# Common large/build/tooling directories to skip during traversal
DEFAULT_IGNORED_DIRS: Set[str] = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    ".env",
    ".direnv",
    "site-packages",  # Python package installations
    "node_modules",
    ".pnpm-store",
    ".yarn",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".pytype",
    ".ipynb_checkpoints",
    "build",
    "dist",
    "out",
    "public",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".angular",
    ".astro",
    ".vite",
    ".cache",
    ".parcel-cache",
    ".turbo",
    "coverage",
    ".coverage",
    ".nyc_output",
    ".gradle",
    ".idea",
    ".vscode",
    ".claude",
    ".docusaurus",
    ".vercel",
    ".serverless",
    ".terraform",
    ".mvn",
    ".tox",
    "target",
    "bin",
    "obj",
}


# Node type to chunk type mapping (tree-sitter → CodeChunk)
NODE_TYPE_MAP: Dict[str, str] = {
    "function_declaration": "function",
    "function_definition": "function",
    "arrow_function": "function",
    "function": "function",
    "function_item": "function",  # Rust
    "method_declaration": "method",  # Go, Java
    "method_definition": "method",
    "class_declaration": "class",
    "class_definition": "class",
    "class_specifier": "class",  # C++
    "interface_declaration": "interface",
    "type_alias_declaration": "type",
    "type_declaration": "type",  # Go
    "enum_declaration": "enum",
    "enum_specifier": "enum",  # C
    "enum_item": "enum",  # Rust
    "struct_declaration": "struct",  # C#
    "struct_specifier": "struct",  # C/C++
    "struct_item": "struct",  # Rust
    "union_specifier": "union",  # C/C++
    "namespace_definition": "namespace",  # C++
    "namespace_declaration": "namespace",  # C#
    "impl_item": "impl",  # Rust
    "trait_item": "trait",  # Rust
    "mod_item": "module",  # Rust
    "macro_definition": "macro",  # Rust
    "constructor_declaration": "constructor",  # Java/C#
    "destructor_declaration": "destructor",  # C#
    "property_declaration": "property",  # C#
    "event_declaration": "event",  # C#
    "template_declaration": "template",  # C++
    "concept_definition": "concept",  # C++
    "annotation_type_declaration": "annotation",  # Java
    "script_element": "script",  # Svelte
    "style_element": "style",  # Svelte
    "variable_declaration": "variable",  # GLSL uniforms, varying, attributes
    "preprocessor_define": "define",  # GLSL preprocessor defines
    "preprocessor_function_def": "define",  # GLSL preprocessor function defines
    "block_statement": "block",  # GLSL code blocks
    "compound_statement": "block",  # GLSL compound statements
}
