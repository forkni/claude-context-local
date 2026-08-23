"""C-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from ._c_family import neutralize_preprocessor_conditionals, unwrap_declarator_name
from .base import LanguageChunker


class CChunker(LanguageChunker):
    """C-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("c", language)

    def preprocess_source_for_parse(self, source_bytes: bytes) -> bytes:
        """Blank preprocessor conditional directives before parsing.

        See `neutralize_preprocessor_conditionals` (_c_family.py) for the
        rewrite, why it preserves byte offsets, and the measured impact. A
        no-op substitution on source with no `#if`/`#ifdef`/.../`#endif`.

        Args:
            source_bytes: UTF-8-encoded original source.

        Returns:
            Source bytes with preprocessor conditionals blanked.
        """
        return neutralize_preprocessor_conditionals(source_bytes)

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract C-specific metadata."""
        metadata = {"node_type": node.type}

        # Extract function name. Unwraps pointer_declarator (pointer-returning
        # functions, e.g. `int* getPtr()`) instead of the pre-v0.24 direct-
        # child scan, which only matched a bare `function_declarator` child
        # and silently returned name=None for every pointer-returning
        # function -- see chunking/languages/_c_family.py.
        if node.type == "function_definition":
            name = unwrap_declarator_name(
                node.child_by_field_name("declarator"),
                lambda n: self.get_node_text(n, source),
            )
            if name is not None:
                metadata["name"] = name

        # Extract struct/union/enum name
        elif node.type in ["struct_specifier", "union_specifier", "enum_specifier"]:
            for child in node.children:
                if child.type in ["type_identifier", "identifier"]:
                    metadata["name"] = self.get_node_text(child, source)
                    break

        # Extract typedef name
        elif node.type == "type_definition":
            # Look for the last identifier which is the new type name. The
            # new type name is a `type_identifier` node (e.g.
            # `typedef struct {...} Color;` -> Color), not a plain
            # `identifier` -- the bare-`identifier` check alone always
            # missed it, silently leaving every anonymous-struct/enum
            # typedef nameless. Mirrors the struct/union/enum branch above,
            # which already checks both kinds. Found via the C++ chunking
            # parity plan's live gate verification for calculator.c.
            identifiers = []
            for child in node.children:
                if child.type in ("identifier", "type_identifier"):
                    identifiers.append(self.get_node_text(child, source))
            if identifiers:
                metadata["name"] = identifiers[-1]
            else:
                # Direct-child scan finds nothing for a nested-declarator
                # typedef, e.g. `typedef void (*Callback)(int);` -- the name
                # is `type_identifier` inside a
                # function_declarator/parenthesized_declarator/
                # pointer_declarator chain, not a direct child. Falls back to
                # the shared unwrap, widening the terminal set to
                # `type_identifier` since that's the typedef's name terminal
                # (not its type, as `type_identifier` reads elsewhere).
                name = unwrap_declarator_name(
                    node.child_by_field_name("declarator"),
                    lambda n: self.get_node_text(n, source),
                    extra_terminals=frozenset({"type_identifier"}),
                )
                if name is not None:
                    metadata["name"] = name

        return metadata
