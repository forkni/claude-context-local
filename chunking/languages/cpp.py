"""C++-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from ._c_family import declarator_is_function_shaped, unwrap_declarator_name
from .base import LanguageChunker


def _anonymous_typedef_name(node: Any) -> Any | None:
    """Recover a name for an anonymous class/struct/union/enum specifier.

    `type_definition` is not in cpp's `splittable_node_types` (unlike C's),
    so `typedef struct { ... } Vec3;` only chunks its anonymous inner
    specifier -- the alias name `Vec3` is a direct child of the *parent*
    `type_definition`, not of `node` itself. Returns None if `node`'s parent
    isn't a `type_definition` (i.e. this specifier isn't part of a typedef
    at all) or has no name child.
    """
    parent = node.parent
    if parent is None or parent.type != "type_definition":
        return None
    for child in reversed(parent.children):
        if child.type in ("type_identifier", "identifier"):
            return child
    return None


class CppChunker(LanguageChunker):
    """C++-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("cpp", language)

    # ------------------------------------------------------------------
    # Container seam (v0.24 header parity)
    # ------------------------------------------------------------------

    #: Beyond the base default (class_definition/class_declaration, which
    #: C++ never produces), C++ needs its own container types so traversal
    #: continues into a chunked container's children to pick up members as
    #: separate chunks. Before this override, `namespace_definition` and
    #: `class_specifier`/`struct_specifier`/`union_specifier` were chunked
    #: as one opaque blob each -- e.g. a whole namespace with 18 function
    #: definitions inside produced a single unnamed chunk.
    _CONTAINER_NODE_TYPES: frozenset[str] = frozenset(
        {
            "class_specifier",
            "struct_specifier",
            "union_specifier",
            "namespace_definition",
        }
    )

    # ------------------------------------------------------------------
    # Adaptive-sizing profiler support
    # ------------------------------------------------------------------

    @property
    def function_node_types(self) -> frozenset[str]:
        """Only `function_definition` counts as a function for profiling.

        The base class's default derivation (splittable minus
        `_CLASS_LEVEL_NODE_TYPES`) would still include `union_specifier`,
        `namespace_definition`, `template_declaration`, `concept_definition`,
        and the newly-added `field_declaration`/`declaration`/
        `alias_declaration` -- none of which are functions, and mixing them
        into the size-percentile baseline the adaptive splitter uses would
        skew it. Mirrors `GLSLChunker.function_node_types`.
        """
        return frozenset({"function_definition"})

    # ------------------------------------------------------------------
    # Chunk-granularity gate
    # ------------------------------------------------------------------

    def should_chunk_node(self, node: Any) -> bool:
        """Narrow header-only declarations; unwrap templated classes.

        Two special cases beyond the base default (`node.type in
        splittable_node_types`):

        1. `field_declaration` / `declaration` -- these were added to
           `splittable_node_types` to catch header-only method declarations
           (`int m();`, `virtual void pure() = 0;`) and constructor/
           destructor declarations (`Foo();`, `~Foo();`). Both node types
           are also how *data members* parse (`int x;` is a
           `field_declaration` too), so only chunk the ones whose
           declarator ultimately wraps a `function_declarator` --
           `declarator_is_function_shaped` walks the same pointer/reference
           unwrap chain `unwrap_declarator_name` uses for the name itself.
           `declaration` also naturally covers free-standing function
           prototypes at namespace/global scope (`void foo(int);` in a
           header) -- intentional, not just an incidental side effect: it
           makes header prototype indexing work the same way member
           declarations do.
        2. `template_declaration` wrapping a class/struct/union -- return
           False so traversal falls through to the wrapped container
           directly. The container then gets its own name and its members
           split out individually, instead of one flat, larger blob under
           `template_declaration` (the template parameter list prefix is
           dropped from the resulting chunk -- an accepted trade-off).
           A `template_declaration` wrapping a free function is unaffected
           and still chunks as one unit (unchanged from before).

        Args:
            node: Tree-sitter node.

        Returns:
            True if node should become its own chunk.
        """
        if node.type in ("field_declaration", "declaration"):
            return declarator_is_function_shaped(node.child_by_field_name("declarator"))
        if node.type == "template_declaration" and any(
            child.type in ("class_specifier", "struct_specifier", "union_specifier")
            for child in node.children
        ):
            return False
        return super().should_chunk_node(node)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract C++-specific metadata."""
        metadata: dict[str, Any] = {"node_type": node.type}

        if node.type in ("function_definition", "field_declaration", "declaration"):
            name = unwrap_declarator_name(
                node.child_by_field_name("declarator"),
                lambda n: self.get_node_text(n, source),
            )
            if name is not None:
                metadata["name"] = name

        elif node.type in ("class_specifier", "struct_specifier", "union_specifier"):
            for child in node.children:
                if child.type in ("type_identifier", "identifier"):
                    metadata["name"] = self.get_node_text(child, source)
                    break
            if "name" not in metadata:
                # Anonymous specifier, e.g. `typedef struct { ... } Vec3;` --
                # unlike C (where `type_definition` is itself splittable and
                # picks up its own trailing type_identifier), C++'s
                # splittable_node_types has no `type_definition` entry, so
                # only this anonymous inner specifier chunks. Its name lives
                # one level up, as a direct child of the parent
                # `type_definition`. A *named* `typedef struct Point {...}
                # Point_t;` never reaches here -- the scan above already
                # found `Point`.
                name = _anonymous_typedef_name(node)
                if name is not None:
                    metadata["name"] = self.get_node_text(name, source)

        elif node.type == "namespace_definition":
            # `namespace math {}`'s name child is `namespace_identifier` --
            # neither `identifier` nor `type_identifier` (both of those are
            # only ever a MISSING placeholder here) -- so this required its
            # own scan rather than sharing the class/struct/union branch.
            name_node = node.child_by_field_name("name")
            if name_node is None:
                name_node = next(
                    (c for c in node.children if c.type == "namespace_identifier"),
                    None,
                )
            if name_node is not None:
                metadata["name"] = self.get_node_text(name_node, source)

        elif node.type == "enum_specifier":
            # Covers both plain enums and `enum class` -- the grammar uses
            # the same node type for both, distinguished by an optional
            # "class"/"struct" keyword child that doesn't affect the name.
            name_node = node.child_by_field_name("name")
            if name_node is None:
                name_node = next(
                    (c for c in node.children if c.type == "type_identifier"), None
                )
            if name_node is None:
                # Anonymous `typedef enum { ... } Color;` -- same rationale
                # as the class/struct/union branch above.
                name_node = _anonymous_typedef_name(node)
            if name_node is not None:
                metadata["name"] = self.get_node_text(name_node, source)

        elif node.type == "alias_declaration":
            # `using X = Y;`
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                metadata["name"] = self.get_node_text(name_node, source)

        # Check for template parameters (only reached for a
        # template_declaration wrapping a free function -- should_chunk_node
        # returns False for one wrapping a class/struct/union, so that case
        # never produces a chunk here).
        if node.type == "template_declaration":
            metadata["is_template"] = True
            for child in node.children:
                if child.type in (
                    "function_definition",
                    "class_specifier",
                    "struct_specifier",
                    "union_specifier",
                ):
                    child_metadata = self.extract_metadata(child, source)
                    if "name" in child_metadata:
                        metadata["name"] = child_metadata["name"]
                    break

        return metadata
