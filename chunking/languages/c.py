"""C-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from ._c_family import (
    _CFamilyChunker,
    extract_call_sites,
    extract_include_metadata,
    unwrap_declarator_name,
)


class CChunker(_CFamilyChunker):
    """C-specific chunker using tree-sitter.

    Inherits `_CFamilyChunker`'s `preprocess_source_for_parse` composition
    (_c_family.py) unchanged: preprocessor-conditional neutralization, then
    macro-wrapped-declaration repair. Measured over 69 real `.c` files
    (154,346 lines) from a TouchDesigner installation tree: ERROR lines
    6,055 (3.92%) -> 5,733 (3.71%), with definitions gained (17,240 ->
    17,254) and zero files regressed (7 improved / 0 regressed) -- smaller
    than the C++-extension case (fewer macro-wrapped-prototype headers
    reach the `c` grammar at all, since most C-compatible headers route to
    `cpp` -- see `chunking/language_registry.py`'s `EXT_TO_LANGUAGE`), but
    real and zero-regression by the same construction.
    """

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("c", language)

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract C-specific metadata."""
        metadata: dict[str, Any] = {"node_type": node.type, "relationships": []}

        def get_text(n: Any) -> str:
            return self.get_node_text(n, source)

        # Extract function name. Unwraps pointer_declarator (pointer-returning
        # functions, e.g. `int* getPtr()`) instead of the pre-v0.24 direct-
        # child scan, which only matched a bare `function_declarator` child
        # and silently returned name=None for every pointer-returning
        # function -- see chunking/languages/_c_family.py.
        if node.type == "function_definition":
            name = unwrap_declarator_name(
                node.child_by_field_name("declarator"), get_text
            )
            if name is not None:
                metadata["name"] = name
            metadata["calls"] = extract_call_sites(node, get_text)

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

        elif node.type == "preproc_include":
            extract_include_metadata(node, get_text, metadata)

        return metadata
