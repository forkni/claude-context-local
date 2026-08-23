"""C++-specific chunker using tree-sitter."""

import re
from typing import Any

from tree_sitter import Language

from ._c_family import (
    blank_preserving_layout,
    declarator_is_function_shaped,
    neutralize_preprocessor_conditionals,
    unwrap_declarator_name,
)
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
    # Parse-error neutralization
    # ------------------------------------------------------------------

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
        # template_declaration wrapping a free function, header-only
        # prototype, or alias -- should_chunk_node returns False for one
        # wrapping a class/struct/union, so that case never produces a chunk
        # here; the container itself gets its own chunk and name directly
        # instead. `class_specifier`/`struct_specifier`/`union_specifier`
        # were in this tuple until PR #57 review flagged them as dead code:
        # a template_declaration reaching this point can never wrap one of
        # those three types, so branches for them were unreachable).
        # `declaration` covers a templated header-only prototype
        # (`template<typename T> void proto(T v);`), `alias_declaration`
        # covers a templated alias (`template<class T> using Ptr = T*;`) --
        # both previously fell through this scan unmatched and chunked
        # nameless despite `extract_metadata` already having working
        # handlers for both node types.
        if node.type == "template_declaration":
            metadata["is_template"] = True
            for child in node.children:
                if child.type in (
                    "function_definition",
                    "declaration",
                    "alias_declaration",
                ):
                    child_metadata = self.extract_metadata(child, source)
                    if "name" in child_metadata:
                        metadata["name"] = child_metadata["name"]
                    break

        return metadata


# -----------------------------------------------------------------------------
# CUDA (.cu / .cuh) -- routed to the cpp grammar, no new tree-sitter dependency
# -----------------------------------------------------------------------------

#: CUDA execution-space/memory-space specifiers. Neither is standard C++, so
#: tree-sitter-cpp doesn't recognize them as declaration specifiers -- e.g.
#: `__global__ void kernel(float* out) { ... }` desyncs the parser the same
#: way an unrecognized export macro does (see `_c_family.py`'s A1 docstring).
#: Blanking them before parsing is the same trade already made for
#: preprocessor conditionals: the token itself carries no chunk-name or
#: metadata information tree-sitter needs, and the original text survives in
#: chunk content (sliced from the un-rewritten source, per
#: `LanguageChunker.preprocess_source_for_parse`'s contract).
_CUDA_ATTRS = re.compile(
    rb"\b(?:__global__|__device__|__host__|__forceinline__"
    rb"|__restrict__|__constant__|__shared__|__managed__)\b"
)

#: CUDA kernel-launch triple-chevron syntax, e.g. `kernel<<<grid, block>>>(args);`.
#: Not valid C++ token syntax at all -- tree-sitter-cpp has no grammar rule
#: for `<<<`/`>>>` as a unit (each `<`/`>` lexes as a comparison/shift
#: operator instead), so an unblanked launch expression reliably desyncs the
#: parser. `[^>]*` can span multiple lines for a multi-argument launch config
#: split across lines, so this match is fed through the same
#: `blank_preserving_layout` byte-for-byte blanker the preprocessor-
#: conditional blanker uses -- a naive `b" " * len(match)` would silently
#: corrupt newline positions for every line after a wrapped launch config.
_LAUNCH_CFG = re.compile(rb"<<<[^>]*>>>")


class CudaChunker(CppChunker):
    """CUDA (.cu/.cuh) chunker -- the cpp grammar plus CUDA-specific blanking.

    No new tree-sitter grammar: `.cu`/`.cuh` route to the existing
    `tree_sitter_cpp` parser (`chunking/language_registry.py`'s
    `EXT_TO_LANGUAGE`), which parses ordinary CUDA C++ cleanly. Only two CUDA
    extensions to plain C++ syntax break it -- execution-space attributes and
    the `<<<...>>>` launch configuration -- both handled here.

    Deliberately keeps `language_name == "cpp"` (inherited, unchanged) rather
    than registering a `"cuda"` language: see
    `docs/adr/0054-route-cuda-extensions-to-cpp-grammar.md` for the full
    rationale (no `LANGUAGE_SPECS` entry needed, `EXPECTED_LANGUAGES` in
    `tests/unit/chunking/test_language_spec_ownership.py` stays untouched).

    Measured: CUDA source parsed as plain cpp (no CUDA-specific blanking) has
    62 ERROR lines (3.0%); with both `_CUDA_ATTRS` and `_LAUNCH_CFG` blanked
    ahead of the inherited preprocessor-conditional neutralization, 0 ERROR
    lines (0.0%).

    Accepted limitation, distinct from the preprocessor-conditional case in
    `_c_family.py`: a blanked execution-space attribute (`__global__`,
    `__device__`, `__constant__`, ...) sits *before* the declaration node it
    modifies, not nested inside a larger enclosing chunk, so tree-sitter's
    node span for that declaration starts after the blanked bytes -- the
    attribute keyword itself is not part of any emitted chunk's `content`.
    The declaration's real name, body, and line numbers are unaffected; only
    the leading annotation keyword's literal text is invisible in the index.
    This mirrors `GLSLChunker`'s own qualifier-neutralization precedent
    (`glsl.py`'s `_neutralize_anon_layout_qualifiers`, which comments out
    rather than preserves the original qualifier arguments) and is within
    the workstream's scope: the success criteria are ERROR-line elimination
    and correct definition names/line numbers, not attribute-token recall.
    """

    def preprocess_source_for_parse(self, source_bytes: bytes) -> bytes:
        """Blank CUDA-specific syntax, then preprocessor conditionals.

        Order matters only in that both rewrites are independently length-
        and newline-position-preserving, so composing them in either order
        produces the same result -- `super()` first keeps the CUDA-specific
        rules scoped to bytes that have already had `#if`/`#ifdef`/...
        directive lines blanked, avoiding any chance of a CUDA regex
        matching text that lives inside a blanked directive line.

        Args:
            source_bytes: UTF-8-encoded original source.

        Returns:
            Source bytes with CUDA attributes, launch configs, and
            preprocessor conditionals all blanked. Identical in total length
            and newline positions to `source_bytes`.
        """
        rewritten = super().preprocess_source_for_parse(source_bytes)
        rewritten = _CUDA_ATTRS.sub(blank_preserving_layout, rewritten)
        rewritten = _LAUNCH_CFG.sub(blank_preserving_layout, rewritten)
        return rewritten
