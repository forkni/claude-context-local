"""Language and file type registry for code chunking.

Centralizes supported extensions, ignored directories, node type mappings,
and per-language grammar specs used across the chunking and indexing subsystems.
"""

from __future__ import annotations

import importlib
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal


WarningAction = Literal["default", "error", "ignore", "always", "module", "once"]


# Extension → tree-sitter grammar name.  Single source of truth for both
# SUPPORTED_EXTENSIONS (used by the file-walker) and LANGUAGE_MAP (used by
# TreeSitterChunker to select the grammar).  Add a new language here only.
EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c++": "cpp",
    ".cs": "csharp",
    ".glsl": "glsl",
    ".frag": "glsl",
    ".vert": "glsl",
    ".comp": "glsl",
    ".geom": "glsl",
    ".tesc": "glsl",
    ".tese": "glsl",
}

# Supported file extensions for code chunking — derived from EXT_TO_LANGUAGE.
SUPPORTED_EXTENSIONS: set[str] = set(EXT_TO_LANGUAGE.keys())


# Common large/build/tooling directories to skip during traversal
DEFAULT_IGNORED_DIRS: set[str] = {
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
    "logs",
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
NODE_TYPE_MAP: dict[str, str] = {
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


# ---------------------------------------------------------------------------
# Per-language grammar spec table (P4 architecture deepening)
# ---------------------------------------------------------------------------
# Single source of truth for the two pieces of "config wearing a class
# costume" that were duplicated across 9 near-identical leaf chunkers:
#
#   _load_language()           — which grammar module to import
#   _get_splittable_node_types() — which node types to chunk
#
# Adding a new language now requires only one entry here (plus the LANGUAGE_MAP
# factory lambda in tree_sitter.py).
#
# Two special-case hooks are available for the minority of languages that
# need non-trivial grammar loading:
#   grammar_loader   — fully custom callable returning a tree_sitter.Language
#                      (used by TypeScriptChunker for use_tsx branching)
#   load_warning_filter — suppress a specific warning during Language() init
#                         (used by GLSLChunker)
# ---------------------------------------------------------------------------


@dataclass
class LanguageSpec:
    """Specification for a single tree-sitter language binding.

    Attributes:
        grammar_module: dotted module name that provides the grammar, e.g.
            ``"tree_sitter_rust"``.  The module must expose a zero-arg
            ``language()`` callable that returns the C binding pointer.
        splittable_node_types: Set of tree-sitter node type strings whose
            top-level occurrences should each become a separate chunk.
        grammar_loader: Optional override callable that accepts no arguments
            and returns a ``tree_sitter.Language`` object.  Provide this for
            languages that require special loading logic (e.g. TypeScript's
            dual ``language_typescript()``/``language_tsx()`` entry points).
            When set, ``grammar_module`` is still used for ``AVAILABLE_LANGUAGES``
            population but the per-instance ``_load_language`` calls this instead.
        load_warning_filter: Optional ``(action, message_pattern)`` tuple passed
            to ``warnings.filterwarnings`` during ``Language()`` construction.
            Used by GLSL to silence a deprecation warning from the C extension.
        install_hint: Human-readable ``pip install`` hint embedded in the
            ValueError raised when the grammar package is missing.
    """

    grammar_module: str
    splittable_node_types: set[str] = field(default_factory=set)
    grammar_loader: Callable[[], object] | None = None
    load_warning_filter: tuple[WarningAction, str] | None = None
    install_hint: str = ""

    def load_grammar(self) -> object:
        """Import the grammar module and return a ``tree_sitter.Language``.

        Returns:
            A ``tree_sitter.Language`` object.

        Raises:
            ValueError: If the grammar package is not installed.
        """
        from tree_sitter import Language  # local import — avoid top-level dep

        if self.grammar_loader is not None:
            return self.grammar_loader()

        try:
            mod = importlib.import_module(self.grammar_module)
        except ImportError as err:
            hint = (
                self.install_hint
                or f"pip install {self.grammar_module.replace('_', '-')}"
            )
            raise ValueError(
                f"{self.grammar_module} not installed. Install with: {hint}"
            ) from err

        if self.load_warning_filter is not None:
            action, pattern = self.load_warning_filter
            with warnings.catch_warnings():
                warnings.filterwarnings(action, message=pattern)
                return Language(mod.language())

        return Language(mod.language())


def _ts_loader() -> object:
    """Load tree-sitter-typescript (typescript grammar, not tsx)."""
    import tree_sitter_typescript as tstypescript  # noqa: PLC0415
    from tree_sitter import Language

    return Language(tstypescript.language_typescript())


def _tsx_loader() -> object:
    """Load tree-sitter-typescript (tsx grammar)."""
    import tree_sitter_typescript as tstypescript  # noqa: PLC0415
    from tree_sitter import Language

    return Language(tstypescript.language_tsx())


# Map language_name (as used in LanguageChunker.language_name) → LanguageSpec.
# This must stay in sync with EXT_TO_LANGUAGE — every value in EXT_TO_LANGUAGE
# should have a corresponding entry here (except tsx which shares the package).
LANGUAGE_SPECS: dict[str, LanguageSpec] = {
    "python": LanguageSpec(
        grammar_module="tree_sitter_python",
        splittable_node_types={
            "function_definition",
            "class_definition",
            "decorated_definition",
        },
        install_hint="pip install tree-sitter-python",
    ),
    "javascript": LanguageSpec(
        grammar_module="tree_sitter_javascript",
        splittable_node_types={
            "function_declaration",
            "function",
            "arrow_function",
            "class_declaration",
            "method_definition",
            "generator_function",
            "generator_function_declaration",
        },
        install_hint="pip install tree-sitter-javascript",
    ),
    "typescript": LanguageSpec(
        grammar_module="tree_sitter_typescript",
        splittable_node_types={
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
        },
        grammar_loader=_ts_loader,
        install_hint="pip install tree-sitter-typescript",
    ),
    "tsx": LanguageSpec(
        grammar_module="tree_sitter_typescript",
        splittable_node_types={
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
        },
        grammar_loader=_tsx_loader,
        install_hint="pip install tree-sitter-typescript",
    ),
    "go": LanguageSpec(
        grammar_module="tree_sitter_go",
        splittable_node_types={
            "function_declaration",
            "method_declaration",
            "type_declaration",
            "interface_declaration",
            "struct_declaration",
        },
        install_hint="pip install tree-sitter-go",
    ),
    "rust": LanguageSpec(
        grammar_module="tree_sitter_rust",
        splittable_node_types={
            "function_item",
            "impl_item",
            "struct_item",
            "enum_item",
            "trait_item",
            "mod_item",
            "macro_definition",
        },
        install_hint="pip install tree-sitter-rust",
    ),
    "c": LanguageSpec(
        grammar_module="tree_sitter_c",
        splittable_node_types={
            "function_definition",
            "struct_specifier",
            "union_specifier",
            "enum_specifier",
            "type_definition",
        },
        install_hint="pip install tree-sitter-c",
    ),
    "cpp": LanguageSpec(
        grammar_module="tree_sitter_cpp",
        splittable_node_types={
            "function_definition",
            "class_specifier",
            "struct_specifier",
            "union_specifier",
            "enum_specifier",
            "namespace_definition",
            "template_declaration",
            "concept_definition",
        },
        install_hint="pip install tree-sitter-cpp",
    ),
    "csharp": LanguageSpec(
        grammar_module="tree_sitter_c_sharp",
        splittable_node_types={
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
        },
        install_hint="pip install tree-sitter-c-sharp",
    ),
    "glsl": LanguageSpec(
        grammar_module="tree_sitter_glsl",
        splittable_node_types={
            "function_definition",
            "struct_declaration",
            "variable_declaration",
            "preprocessor_define",
            "preprocessor_function_def",
            "preprocessor_include",
            "preprocessor_ifdef",
            "preprocessor_ifndef",
            "layout_qualifier_statement",
            "uniform_block",
            "interface_block",
            "block_statement",
            "compound_statement",
            "subroutine_definition",
            "precision_statement",
        },
        load_warning_filter=("ignore", "int argument support is deprecated"),
        install_hint="pip install tree-sitter-glsl",
    ),
}
