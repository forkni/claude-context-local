"""GLSL-specific chunker using tree-sitter."""

import re
from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


# tree-sitter-glsl hard-errors on the anonymous layout-qualifier "execution
# mode" form — `layout(local_size_x=16) in;` (compute), `layout(triangles)
# in;` / `layout(triangle_strip, max_vertices=3) out;` (geometry) — and the
# resulting ERROR node swallows every function defined after it in the
# translation unit (verified on a geometry shader: emit_verts and tail both
# vanished, leaving only main). See GLSLChunker.preprocess_source_for_parse.
_ANON_LAYOUT_QUALIFIER_RE = re.compile(rb"layout[ \t]*\([^)]*\)[ \t]*(?:in|out)[ \t]*;")


def _neutralize_anon_layout_qualifiers(source_bytes: bytes) -> bytes:
    """Rewrite anonymous layout-qualifier statements into equal-length block comments.

    Each match is rewritten by dropping its first two and last two bytes and
    wrapping what remains in `/* ... */` — total byte length is unchanged
    (2 dropped + 2 dropped == `/*` + `*/` added) and no newline is added or
    removed, so tree-sitter node byte offsets computed against the rewritten
    bytes stay valid when later applied against the original source text.
    The block-comment form (not `//`) is deliberate: it closes at the end of
    the match, so it cannot swallow code that follows on the same line
    (e.g. `layout(...) out; void tail(){}`).

    Args:
        source_bytes: UTF-8-encoded original source.

    Returns:
        Source bytes with anonymous layout qualifiers commented out.
    """
    return _ANON_LAYOUT_QUALIFIER_RE.sub(
        lambda m: b"/*" + m.group(0)[2:-2] + b"*/", source_bytes
    )


# Bare storage/precision/interpolation qualifier keywords that appear as
# anonymous children of a `declaration` node (tree-sitter-glsl is a fork of
# tree-sitter-c, so these surface as literal-keyword node types, not a
# dedicated "qualifier" wrapper — verified via grammar dump). `const` is the
# one exception: the C grammar wraps it in a `type_qualifier` node instead,
# handled separately in _extract_declaration_metadata.
_STORAGE_QUALIFIER_TYPES = frozenset(
    {
        "uniform",
        "in",
        "out",
        "inout",
        "buffer",
        "shared",
        "varying",
        "attribute",
        "flat",
        "smooth",
        "noperspective",
        "centroid",
        "sample",
        "patch",
        "invariant",
        "precise",
        "coherent",
        "volatile",
        "restrict",
        "readonly",
        "writeonly",
        "highp",
        "mediump",
        "lowp",
    }
)

# Node types that always add exactly one decision point to cyclomatic
# complexity. Mirrors chunking/languages/python.py's _SIMPLE_DECISION_TYPES;
# GLSL's C-style grammar represents "else if" as a nested if_statement
# inside an else_clause (not a flat elif_clause like Python's), so the flat
# stack walk in _count_decision_points visits and counts it directly — no
# special-casing needed.
_SIMPLE_DECISION_TYPES = frozenset(
    {
        "if_statement",
        "for_statement",
        "while_statement",
        "switch_statement",
        "case_statement",
        "conditional_expression",
    }
)
# binary_expression only counts as a decision point when its operator is a
# short-circuiting logical operator (GLSL's equivalent of a boolean_operator).
_LOGICAL_OPERATORS = frozenset({"&&", "||"})

# GLSL built-in variables — presence indicates shader-stage I/O usage.
_BUILTIN_VAR_NAMES = frozenset(
    {
        "gl_Position",
        "gl_FragColor",
        "gl_FragCoord",
        "gl_FragDepth",
        "gl_Normal",
        "gl_Vertex",
        "gl_PointSize",
        "gl_PointCoord",
        "gl_VertexID",
        "gl_InstanceID",
        "gl_PrimitiveID",
        "gl_GlobalInvocationID",
        "gl_LocalInvocationID",
        "gl_LocalInvocationIndex",
        "gl_WorkGroupID",
        "gl_NumWorkGroups",
        "gl_TessCoord",
        "gl_ModelViewMatrix",
        "gl_ProjectionMatrix",
        "gl_ModelViewProjectionMatrix",
        "gl_NormalMatrix",
    }
)

# Texture sampling function calls.
_TEXTURE_OP_NAMES = frozenset(
    {
        "texture",
        "texture2D",
        "texture3D",
        "textureCube",
        "textureLod",
        "textureProj",
        "textureGrad",
        "textureGather",
        "textureSize",
        "texelFetch",
        "texelFetchOffset",
        "textureOffset",
    }
)
# Sampler/image type-name prefixes — declaring one of these types is itself
# a texture-operation signal, even with no accompanying texture*() call.
_SAMPLER_TYPE_PREFIXES = (
    "sampler",
    "isampler",
    "usampler",
    "image",
    "iimage",
    "uimage",
)

# Common GLSL math built-ins.
_MATH_OP_NAMES = frozenset(
    {
        "dot",
        "cross",
        "normalize",
        "length",
        "distance",
        "reflect",
        "refract",
        "mix",
        "clamp",
        "smoothstep",
        "step",
        "pow",
        "sqrt",
        "inversesqrt",
        "abs",
        "sign",
        "floor",
        "ceil",
        "fract",
        "mod",
        "min",
        "max",
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "exp",
        "log",
        "exp2",
        "log2",
    }
)

_IDENTIFIER_NODE_TYPES = frozenset(
    {"identifier", "type_identifier", "field_identifier"}
)

# ---------------------------------------------------------------------------
# Call-graph noise filtering (Phase 2b)
#
# `call_expression` has the same [identifier, argument_list] shape for user
# calls, GLSL builtins, and type constructors alike (tree-sitter-c's
# context-free grammar cannot distinguish them without a symbol table), so
# filtering can only be name-based. Measured on a real shader: 17
# call_expression targets, of which exactly one was user-defined — the other
# 16 were builtins/type-constructors/TD-prefixed globals. Struct constructors
# (e.g. `Material(...)`) are handled separately: `_extract_call_metadata`
# reclassifies them as INSTANTIATES relationship edges (via
# `_collect_struct_names`) instead of leaving them in metadata["calls"].
# ---------------------------------------------------------------------------

# Built-in functions beyond _MATH_OP_NAMES / _TEXTURE_OP_NAMES: bit-cast /
# pack-unpack, vector-relational, matrix, derivative, image/atomic,
# synchronization, and geometry-shader emit functions.
_OTHER_BUILTIN_FUNCTION_NAMES = frozenset(
    {
        "radians",
        "degrees",
        "modf",
        "trunc",
        "round",
        "roundEven",
        "isnan",
        "isinf",
        "floatBitsToInt",
        "floatBitsToUint",
        "intBitsToFloat",
        "uintBitsToFloat",
        "packHalf2x16",
        "unpackHalf2x16",
        "packUnorm2x16",
        "unpackUnorm2x16",
        "packSnorm2x16",
        "unpackSnorm2x16",
        "packUnorm4x8",
        "unpackUnorm4x8",
        "packSnorm4x8",
        "unpackSnorm4x8",
        "packDouble2x32",
        "unpackDouble2x32",
        "lessThan",
        "lessThanEqual",
        "greaterThan",
        "greaterThanEqual",
        "equal",
        "notEqual",
        "any",
        "all",
        "not",
        "matrixCompMult",
        "outerProduct",
        "transpose",
        "determinant",
        "inverse",
        "dFdx",
        "dFdy",
        "dFdxCoarse",
        "dFdyCoarse",
        "dFdxFine",
        "dFdyFine",
        "fwidth",
        "fwidthCoarse",
        "fwidthFine",
        "textureQueryLod",
        "textureQueryLevels",
        "textureSamples",
        "imageLoad",
        "imageStore",
        "imageSize",
        "imageSamples",
        "imageAtomicAdd",
        "imageAtomicMin",
        "imageAtomicMax",
        "imageAtomicAnd",
        "imageAtomicOr",
        "imageAtomicXor",
        "imageAtomicExchange",
        "imageAtomicCompSwap",
        "atomicAdd",
        "atomicMin",
        "atomicMax",
        "atomicAnd",
        "atomicOr",
        "atomicXor",
        "atomicExchange",
        "atomicCompSwap",
        "barrier",
        "memoryBarrier",
        "memoryBarrierBuffer",
        "memoryBarrierImage",
        "memoryBarrierShared",
        "groupMemoryBarrier",
        "EmitVertex",
        "EndPrimitive",
        "EmitStreamVertex",
        "EndStreamPrimitive",
        "noise1",
        "noise2",
        "noise3",
        "noise4",
        "ftransform",
    }
)

_GLSL_BUILTIN_FUNCTION_NAMES = (
    _MATH_OP_NAMES | _TEXTURE_OP_NAMES | _OTHER_BUILTIN_FUNCTION_NAMES
)

# Built-in vector/matrix constructors: (b|i|u|d)?vec[234], d?mat[234](x[234])?
_TYPE_CONSTRUCTOR_RE = re.compile(r"^(?:[biud]?vec[234]|d?mat[234](?:x[234])?)$")
# Scalar type names, valid as function-style casts: float(x), int(x), ...
_SCALAR_CAST_NAMES = frozenset({"float", "int", "uint", "bool", "double"})


def _is_builtin_type_constructor(name: str) -> bool:
    """True for built-in vector/matrix/scalar/sampler/image type constructors."""
    return (
        bool(_TYPE_CONSTRUCTOR_RE.match(name))
        or name in _SCALAR_CAST_NAMES
        or name.startswith(_SAMPLER_TYPE_PREFIXES)
    )


def _is_td_builtin(name: str) -> bool:
    """TouchDesigner reserves the `TD` prefix for its shader-include namespace.

    A rule instead of an enumerable list — covers every current and future
    TD* builtin (TDPanelSize, TDOutputSwizzle, ...) without maintaining one.
    """
    return name.startswith("TD") and len(name) > 2 and name[2].isupper()


def _is_call_noise(name: str, filter_td_prefix: bool) -> bool:
    """True if `name` is a builtin/type-constructor/TD call, not a user function."""
    if name in _GLSL_BUILTIN_FUNCTION_NAMES or _is_builtin_type_constructor(name):
        return True
    return filter_td_prefix and _is_td_builtin(name)


def _add_relationship(
    metadata: dict[str, Any],
    rel_type: str,
    target_name: str,
    line_number: int,
    **extra: Any,
) -> None:
    """Append a plain-dict relationship edge to metadata["relationships"].

    Mirrors the metadata["calls"] convention (Phase 2b): this emits plain
    data only, converted into `RelationshipEdge` objects downstream by
    `MultiLanguageChunker._extract_glsl_phase3_relationships` — keeps
    `chunking/relationships/` out of this language chunker.

    Args:
        metadata: Metadata dict being populated; must already have a
            "relationships" list key (set at the top of extract_metadata).
        rel_type: RelationshipType enum value string, e.g. "imports".
        target_name: Name of the related symbol.
        line_number: 1-indexed source line the relationship was found on.
        **extra: Extra key/value pairs folded into the edge's metadata dict.
    """
    metadata["relationships"].append(
        {
            "relationship_type": rel_type,
            "target_name": target_name,
            "line_number": line_number,
            "metadata": extra,
        }
    )


class GLSLChunker(LanguageChunker):
    """GLSL-specific chunker using tree-sitter."""

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("glsl", language)

    # ------------------------------------------------------------------
    # Adaptive-sizing profiler support
    # ------------------------------------------------------------------

    @property
    def function_node_types(self) -> frozenset[str]:
        """Only `function_definition` counts as a function for profiling.

        GLSL's `splittable_node_types` (the chunk-granularity set) is much
        wider than "functions" -- it also includes top-level `declaration`
        (every uniform/in/out/const), `struct_specifier`, and every
        `preproc_*` directive, all of which are real, useful *chunks* but
        not functions. The base class's default `function_node_types`
        (splittable minus class-level types) only excludes
        `struct_specifier`, so without this override the adaptive-sizing
        profiler measured every uniform declaration and #define as if it
        were a function -- skewing the P25/P50/P75 baseline it computes
        function-size percentiles from.
        """
        return frozenset({"function_definition"})

    # ------------------------------------------------------------------
    # Parse-error neutralization
    # ------------------------------------------------------------------

    def preprocess_source_for_parse(self, source_bytes: bytes) -> bytes:
        """Neutralize the anonymous layout-qualifier form before parsing.

        See `_neutralize_anon_layout_qualifiers` for the rewrite and why it
        preserves byte offsets. Only affects compute/geometry/tessellation
        shaders that use the anonymous `layout(...) in;`/`layout(...) out;`
        form — a no-op substitution on any source that doesn't contain it.

        Args:
            source_bytes: UTF-8-encoded original source.

        Returns:
            Source bytes with anonymous layout qualifiers commented out.
        """
        return _neutralize_anon_layout_qualifiers(source_bytes)

    # ------------------------------------------------------------------
    # Chunk-granularity gate
    # ------------------------------------------------------------------

    # Bare, uncommented `declaration` chunks whose byte span is under this
    # stay folded into module_preamble instead of becoming their own chunk.
    # Tunable — see should_chunk_node. Record the before/after chunk count
    # this produces against the Phase 1 snapshot in the commit message.
    _SMALL_DECLARATION_BYTES = 200

    def should_chunk_node(self, node: Any) -> bool:
        """Gate `declaration` nodes to avoid a one-chunk-per-uniform explosion.

        Adding `declaration` to splittable_node_types (1a) makes every
        one-line `uniform mat4 uModel;` its own chunk, and nothing ever
        merges small siblings back together for GLSL (`chunk_parsed` never
        calls `_greedy_merge_small_chunks`). Every other splittable node
        type (function_definition, struct_specifier, preproc_*, ...) keeps
        the base behavior unchanged; only `declaration` is gated here:

        1. an interface/UBO block (has a field_declaration_list child) —
           always a meaningful standalone unit, chunk it;
        2. carries an attached leading or trailing comment — the comment
           is exactly the semantic payload that makes a standalone chunk
           beat the blob, chunk it (same sibling walk `should_chunk_node`
           shares with docstring extraction below);
        3. otherwise, only chunk if the byte span is at or above
           _SMALL_DECLARATION_BYTES.

        A bare, uncommented, small declaration (the common case) is left
        unchunked here — it falls through to `_collect_module_preamble_chunks`
        alongside its neighbours instead of becoming a near-empty,
        unnamed-adjacent chunk.

        Args:
            node: Tree-sitter node.

        Returns:
            True if node should become its own chunk.
        """
        if node.type != "declaration":
            return super().should_chunk_node(node)
        if any(child.type == "field_declaration_list" for child in node.children):
            return True
        if self._has_attached_comment_sibling(node):
            return True
        return (node.end_byte - node.start_byte) >= self._SMALL_DECLARATION_BYTES

    # ------------------------------------------------------------------
    # Complexity
    # ------------------------------------------------------------------

    def get_node_complexity(self, node: Any) -> int:
        """Get cyclomatic complexity for a GLSL function node.

        Overrides the base class default (returns 1). GLSL has no
        recursion, exceptions, or comprehensions, so the branch surface is
        narrower than Python's — see _SIMPLE_DECISION_TYPES.

        Args:
            node: Tree-sitter node (function_definition)

        Returns:
            Cyclomatic complexity (minimum 1)
        """
        if node.type == "function_definition":
            return self._calculate_complexity(node)
        return 1

    def _calculate_complexity(self, node: Any) -> int:
        """Calculate cyclomatic complexity for a GLSL function.

        Args:
            node: function_definition node

        Returns:
            Cyclomatic complexity score (minimum 1)
        """
        complexity = 1
        body_node = self._find_body_node(node)
        if body_node is None:
            return complexity
        complexity += self._count_decision_points(body_node)
        return complexity

    def _find_body_node(self, node: Any) -> Any | None:
        """Find the compound_statement body of a function_definition.

        Override of LanguageChunker._find_body_node: GLSL function bodies
        are `compound_statement`, not Python's `block`, and (unlike Python's
        decorated_definition) a GLSL function_definition is never wrapped —
        no recursion into an inner definition is needed. Doubles as the
        body-lookup used by both complexity scoring (above) and large-node
        splitting (_split_large_node, base.py).
        """
        for child in node.children:
            if child.type == "compound_statement":
                return child
        return None

    def _count_decision_points(self, node: Any) -> int:
        """Count decision points in a subtree, iteratively (explicit stack).

        Mirrors PythonChunker._count_decision_points: counting is
        order-independent, so an iterative walk is exactly equivalent to a
        recursive one without the per-node call overhead.

        Args:
            node: Tree-sitter node to analyze

        Returns:
            Number of decision points found
        """
        count = 0
        stack = [node]
        while stack:
            current = stack.pop()
            node_type = current.type
            if node_type in _SIMPLE_DECISION_TYPES:
                count += 1
            elif node_type == "binary_expression":
                operator = current.child_by_field_name("operator")
                if operator is not None and operator.type in _LOGICAL_OPERATORS:
                    count += 1
            stack.extend(current.children)
        return count

    # ------------------------------------------------------------------
    # Large-node splitting
    # ------------------------------------------------------------------

    def _get_block_boundary_types(self) -> set[str]:
        """GLSL statement types that are valid split points for oversized functions.

        Mirrors PythonChunker._get_block_boundary_types for GLSL's narrower
        statement surface (no try/with/match). Overriding this from the
        base class's empty-set default is what enables splitting at all —
        _split_large_node (base.py) bails immediately when it's empty.

        Returns:
            Set of GLSL tree-sitter node type names.
        """
        return {
            "declaration",
            "expression_statement",
            "if_statement",
            "for_statement",
            "while_statement",
            "return_statement",
        }

    def _extract_signature(self, node: Any, source_bytes: bytes) -> str:
        """Extract a GLSL function's signature (return type + declarator).

        The base implementation accumulates lines until one ends in `:` —
        a Python-only convention no GLSL line ever satisfies, so it falls
        through and returns the entire function body as the "signature".
        Instead, take everything from the node's start up to (but not
        including) its compound_statement body — the return type, any
        qualifiers, and the function_declarator (name + parameter_list) —
        stopping right before the opening `{`.

        Args:
            node: function_definition node.
            source_bytes: Source code bytes.

        Returns:
            Signature string, e.g. "vec3 shade(Material m, vec3 lightDir)".
        """
        body = self._find_body_node(node)
        if body is None:
            return self.get_node_text(node, source_bytes)
        return (
            source_bytes[node.start_byte : body.start_byte]
            .decode("utf-8", errors="ignore")
            .rstrip()
        )

    def _split_block_marker(self) -> str:
        """GLSL comment syntax for the split-chunk marker (`//`, not `#`)."""
        return "    // ... (split block)"

    # ------------------------------------------------------------------
    # Metadata extraction
    # ------------------------------------------------------------------

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract GLSL-specific metadata."""
        metadata: dict[str, Any] = {"node_type": node.type, "relationships": []}

        if node.type == "function_definition":
            self._extract_function_metadata(node, source, metadata)
            self._extract_call_metadata(node, source, metadata)
            self._extract_parameter_type_relationships(node, source, metadata)
        elif node.type in ("struct_specifier", "union_specifier", "enum_specifier"):
            self._extract_struct_metadata(node, source, metadata)
        elif node.type == "type_definition":
            self._extract_typedef_metadata(node, source, metadata)
        elif node.type == "declaration":
            self._extract_declaration_metadata(node, source, metadata)
        elif node.type in ("preproc_def", "preproc_function_def"):
            self._extract_macro_metadata(node, source, metadata)
        elif node.type == "preproc_include":
            self._extract_include_metadata(node, source, metadata)
        elif node.type == "preproc_call":
            self._extract_version_metadata(node, source, metadata)
        # preproc_ifdef / preproc_if / preproc_extension: no dedicated name
        # extraction — falls through with node_type only.

        self._tag_glsl_features(node, source, metadata)

        # Comments are root-level siblings in this grammar, not a leading
        # string-literal statement inside the node (Python's docstring
        # shape) — fold any attached leading/trailing comment into the same
        # CodeChunk.docstring channel Python uses. See
        # LanguageChunker._extract_sibling_comment_docstring.
        docstring = self._extract_sibling_comment_docstring(node, source)
        if docstring:
            metadata["docstring"] = docstring

        return metadata

    def _extract_function_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        for child in node.children:
            if child.type == "function_declarator":
                for declarator_child in child.children:
                    if (
                        declarator_child.type == "identifier"
                        and not declarator_child.is_missing
                    ):
                        metadata["name"] = self.get_node_text(declarator_child, source)
                        break
                break
            elif child.type == "identifier" and not child.is_missing:
                metadata["name"] = self.get_node_text(child, source)
                break

    def _extract_call_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Walk `call_expression` nodes and record (callee_name, line_number) pairs.

        Emits plain data, not `CallEdge` objects — that conversion (and the
        `caller_id` it needs) happens in
        `MultiLanguageChunker._extract_call_relationships`, which is what
        keeps `chunking/relationships/` out of this language chunker.

        Always sets `metadata["calls"]` (empty list when the function makes
        no user calls) so "no calls" and "language does not report calls"
        stay distinguishable downstream.

        GLSL has no recursion, no method calls, and no first-class functions,
        so a plain name walk is sufficient — every call resolves statically
        within the translation unit. Builtins, type constructors, and (by
        default) TouchDesigner's TD-prefixed globals are filtered out here;
        see `_is_call_noise`. Struct-constructor calls (e.g. `Material(...)`)
        are reclassified as INSTANTIATES relationship edges instead of
        appearing in metadata["calls"] — see `_collect_struct_names`.

        Args:
            node: function_definition node.
            source: Full source bytes.
            metadata: Metadata dict to populate in place.
        """
        filter_td_prefix = self._filter_td_prefix()
        struct_names = self._collect_struct_names(node, source)
        calls: list[tuple[str, int]] = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current.type == "call_expression":
                func_node = current.child_by_field_name("function")
                if (
                    func_node is not None
                    and func_node.type == "identifier"
                    and not func_node.is_missing
                ):
                    name = self.get_node_text(func_node, source)
                    line = func_node.start_point[0] + 1
                    if name in struct_names:
                        _add_relationship(
                            metadata, "instantiates", name, line, struct_name=name
                        )
                    elif not _is_call_noise(name, filter_td_prefix):
                        calls.append((name, line))
            stack.extend(current.children)
        # Stack-based traversal visits children in reverse order; sort by
        # source line so metadata["calls"] reads in document order.
        calls.sort(key=lambda c: c[1])
        metadata["calls"] = calls

    def _collect_struct_names(self, node: Any, source: bytes) -> set[str]:
        """Collect every struct/union type name declared anywhere in this file.

        Used to reclassify `Material(...)`-shaped call_expression targets as
        INSTANTIATES rather than ordinary CALLS — a call_expression's
        [identifier, argument_list] shape is identical for both, so the only
        way to tell them apart is a name lookup against every struct
        declared in the translation unit, not just the current chunk's
        subtree.

        `extract_metadata` only ever sees the current chunk's node, so this
        walks up to the tree root via `.parent` first, then walks the whole
        tree once collecting the `type_identifier` of every
        struct_specifier/union_specifier node.

        Args:
            node: Any node from the parse tree (e.g. the function_definition
                being processed) — used only to reach the tree root.
            source: Full source bytes.

        Returns:
            Set of struct/union type names declared anywhere in the file.
        """
        root = node
        while root.parent is not None:
            root = root.parent

        names: set[str] = set()
        stack = [root]
        while stack:
            current = stack.pop()
            if current.type in ("struct_specifier", "union_specifier"):
                for child in current.children:
                    if child.type == "type_identifier" and not child.is_missing:
                        names.add(self.get_node_text(child, source))
                        break
            stack.extend(current.children)
        return names

    def _extract_parameter_type_relationships(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Emit USES_TYPE edges for struct-typed function parameters.

        Walks `function_definition` -> `function_declarator` ->
        `parameter_list` -> `parameter_declaration` children. A
        `type_identifier` type is only USES_TYPE-worthy when its name is a
        struct/union declared somewhere in this file (per
        `_collect_struct_names`) — verified via grammar dump that GLSL's
        built-in vector/matrix/sampler types (`vec3`, `mat4`, `sampler2D`,
        ...) *also* surface as `type_identifier`, not `primitive_type`
        (only true C scalars like `float`/`int` do), so node-type alone
        cannot distinguish a struct parameter from a builtin one. Mirrors
        type_extractor.py's USES_TYPE convention for Python.

        Args:
            node: function_definition node.
            source: Full source bytes.
            metadata: Metadata dict to populate in place.
        """
        declarator = next(
            (c for c in node.children if c.type == "function_declarator"), None
        )
        if declarator is None:
            return
        param_list = next(
            (c for c in declarator.children if c.type == "parameter_list"), None
        )
        if param_list is None:
            return
        struct_names = self._collect_struct_names(node, source)
        for param in param_list.children:
            if param.type != "parameter_declaration":
                continue
            type_node = next(
                (c for c in param.children if c.type == "type_identifier"), None
            )
            if type_node is None or type_node.is_missing:
                continue
            type_name = self.get_node_text(type_node, source)
            if type_name not in struct_names:
                continue
            param_name_node = next(
                (
                    c
                    for c in param.children
                    if c.type in ("identifier", "array_declarator")
                ),
                None,
            )
            param_name = self._unwrap_declarator_name(param_name_node, source)
            _add_relationship(
                metadata,
                "uses_type",
                type_name,
                type_node.start_point[0] + 1,
                annotation_location="parameter",
                parameter_name=param_name,
            )

    def _filter_td_prefix(self) -> bool:
        """Whether to filter TouchDesigner's TD-prefixed builtins from calls.

        Reads `ChunkingConfig.glsl_filter_td_prefix` (default True). Falls
        back to True (filter on) when no search config is available yet —
        e.g. standalone chunker use outside the MCP server.
        """
        config = self._get_chunking_config()
        return True if config is None else config.glsl_filter_td_prefix

    def _extract_struct_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        struct_name = None
        for child in node.children:
            if child.type in ("type_identifier", "identifier") and not child.is_missing:
                struct_name = self.get_node_text(child, source)
                metadata["name"] = struct_name
                break

        field_list = next(
            (c for c in node.children if c.type == "field_declaration_list"), None
        )
        if field_list is not None:
            fields = self._extract_field_names(field_list, source)
            if fields:
                metadata["fields"] = fields
            if struct_name:
                self._extract_field_relationships(
                    field_list, source, struct_name, metadata
                )

    def _extract_field_relationships(
        self,
        field_list_node: Any,
        source: bytes,
        struct_name: str,
        metadata: dict[str, Any],
    ) -> None:
        """Emit DEFINES_FIELD (and field-type USES_TYPE) edges for a struct.

        Mirrors dataclass_field_extractor.py's DEFINES_FIELD convention
        (target_name = f"{struct_name}.{field_name}"). Also emits a
        USES_TYPE edge when a field's declared type is itself a struct
        declared somewhere in this file (per `_collect_struct_names`) — a
        bare `type_identifier` check is not enough, since GLSL's built-in
        vector/matrix/sampler types (`vec3`, `mat4`, ...) also surface as
        `type_identifier`, not `primitive_type`; see
        `_extract_parameter_type_relationships` for the same rule.

        Args:
            field_list_node: field_declaration_list node.
            source: Full source bytes.
            struct_name: Enclosing struct/union's name.
            metadata: Metadata dict to populate in place.
        """
        struct_names = self._collect_struct_names(field_list_node, source)
        for child in field_list_node.children:
            if child.type != "field_declaration":
                continue
            line = child.start_point[0] + 1
            field_name = None
            for field_child in child.children:
                if (
                    field_child.type == "field_identifier"
                    and not field_child.is_missing
                ):
                    field_name = self.get_node_text(field_child, source)
                elif field_child.type == "array_declarator":
                    field_name = self._unwrap_declarator_name(field_child, source)
            if field_name is None:
                continue
            _add_relationship(
                metadata,
                "defines_field",
                f"{struct_name}.{field_name}",
                line,
                struct_name=struct_name,
                field_name=field_name,
            )
            type_node = next(
                (c for c in child.children if c.type == "type_identifier"), None
            )
            if type_node is not None and not type_node.is_missing:
                type_name = self.get_node_text(type_node, source)
                if type_name in struct_names:
                    _add_relationship(
                        metadata,
                        "uses_type",
                        type_name,
                        type_node.start_point[0] + 1,
                        annotation_location="field",
                        field_name=field_name,
                    )

    def _extract_typedef_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        # GLSL has no typedef, but the grammar (a tree-sitter-c fork) still
        # defines type_definition — handle it defensively, same shape as C.
        names = []
        for child in node.children:
            if child.type in ("identifier", "array_declarator"):
                name = self._unwrap_declarator_name(child, source)
                if name:
                    names.append(name)
        if names:
            metadata["name"] = names[-1]

    def _extract_declaration_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Extract metadata for a `declaration` node.

        `declaration` covers three distinct shapes in GLSL (verified via
        grammar dump): a plain/layout-qualified variable declaration
        (`uniform mat4 uModel;`), an initialized declaration (`const vec3
        COLORS[3] = ...;`, name nested in an init_declarator), and an
        interface/UBO block (`layout(std140) uniform Cam {...} cam;`,
        distinguished by a field_declaration_list child). A single
        declaration can also carry multiple comma-separated declarators
        (`float a, b = 1.0, c;`).
        """
        storage_qualifiers = []
        layout_qualifiers = []
        field_list_node = None
        pre_field_names = []
        pre_field_lines = []
        post_field_names = []
        seen_field_list = False

        for child in node.children:
            if child.type in _STORAGE_QUALIFIER_TYPES:
                storage_qualifiers.append(child.type)
            elif child.type == "type_qualifier":
                storage_qualifiers.append(self.get_node_text(child, source))
            elif child.type == "layout_specification":
                layout_qualifiers.extend(self._extract_layout_qualifiers(child, source))
            elif child.type == "field_declaration_list":
                field_list_node = child
                seen_field_list = True
            elif child.type in ("identifier", "array_declarator", "init_declarator"):
                name = self._unwrap_declarator_name(child, source)
                if name:
                    if seen_field_list:
                        post_field_names.append(name)
                    else:
                        pre_field_names.append(name)
                        pre_field_lines.append(child.start_point[0] + 1)

        if storage_qualifiers:
            metadata["storage_qualifiers"] = storage_qualifiers
        if layout_qualifiers:
            metadata["layout_qualifiers"] = layout_qualifiers

        if field_list_node is not None:
            # Interface/UBO block: block type name comes before the field
            # list, optional instance name comes after (an anonymous
            # instance — no trailing name — promotes members to global
            # scope; valid, common GLSL).
            block_name = pre_field_names[-1] if pre_field_names else None
            instance_name = post_field_names[0] if post_field_names else None
            if block_name:
                metadata["block_name"] = block_name
            if instance_name:
                metadata["instance_name"] = instance_name
            metadata["name"] = instance_name or block_name
            fields = self._extract_field_names(field_list_node, source)
            if fields:
                metadata["fields"] = fields
            if block_name:
                self._extract_field_relationships(
                    field_list_node, source, block_name, metadata
                )
            return

        if pre_field_names:
            if len(pre_field_names) > 1:
                metadata["name"] = ", ".join(pre_field_names)
                metadata["variable_names"] = pre_field_names
            else:
                metadata["name"] = pre_field_names[0]
            if "const" in storage_qualifiers:
                for name, line in zip(pre_field_names, pre_field_lines, strict=True):
                    _add_relationship(
                        metadata, "defines_constant", name, line, definition=True
                    )

    def _extract_macro_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Extract a #define's name, and a DEFINES_CONSTANT edge for object-like macros.

        Only `preproc_def` (`#define PI 3.14`) is treated as a constant —
        `preproc_function_def` (`#define SQ(x) ...`) is a macro function,
        not a value, and gets no DEFINES_CONSTANT edge.
        """
        for child in node.children:
            if child.type == "identifier" and not child.is_missing:
                name = self.get_node_text(child, source)
                metadata["name"] = name
                if node.type == "preproc_def":
                    _add_relationship(
                        metadata,
                        "defines_constant",
                        name,
                        child.start_point[0] + 1,
                        definition=True,
                        macro=True,
                    )
                break

    def _extract_include_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        line = node.start_point[0] + 1
        for child in node.children:
            if child.type == "string_literal":
                for sub in child.children:
                    if sub.type == "string_content":
                        path = self.get_node_text(sub, source)
                        metadata["name"] = path
                        metadata["include_path"] = path
                        _add_relationship(
                            metadata, "imports", path, line, is_system_include=False
                        )
                        return
            elif child.type == "system_lib_string":
                path = self.get_node_text(child, source).strip("<>")
                metadata["name"] = path
                metadata["include_path"] = path
                metadata["is_system_include"] = True
                _add_relationship(
                    metadata, "imports", path, line, is_system_include=True
                )
                return

    def _extract_version_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        directive = None
        arg = None
        for child in node.children:
            if child.type == "preproc_directive":
                directive = self.get_node_text(child, source).lstrip("#")
            elif child.type == "preproc_arg":
                arg = self.get_node_text(child, source).strip()
        if directive:
            metadata["name"] = f"{directive} {arg}".strip() if arg else directive

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _extract_layout_qualifiers(
        self, layout_spec_node: Any, source: bytes
    ) -> list[str]:
        """Extract layout qualifier strings from a layout_specification node.

        e.g. `layout(binding = 0, std140)` -> ["binding = 0", "std140"].
        """
        qualifiers = []
        for child in layout_spec_node.children:
            if child.type != "layout_qualifiers":
                continue
            for qualifier in child.children:
                if qualifier.type == "qualifier":
                    qualifiers.append(self.get_node_text(qualifier, source))
        return qualifiers

    def _extract_field_names(self, field_list_node: Any, source: bytes) -> list[str]:
        """Extract field names from a field_declaration_list.

        Shared by struct/interface-block metadata above; Phase 3's
        DEFINES_FIELD relationship extractor (_extract_field_relationships)
        reuses this directly.
        """
        fields = []
        for child in field_list_node.children:
            if child.type != "field_declaration":
                continue
            for field_child in child.children:
                if (
                    field_child.type == "field_identifier"
                    and not field_child.is_missing
                ):
                    fields.append(self.get_node_text(field_child, source))
                elif field_child.type == "array_declarator":
                    name = self._unwrap_declarator_name(field_child, source)
                    if name:
                        fields.append(name)
        return fields

    def _unwrap_declarator_name(self, node: Any | None, source: bytes) -> str | None:
        """Recursively unwrap a declarator to its identifier name.

        Handles bare `identifier`/`field_identifier` declarators directly,
        and unwraps `array_declarator` (`taps[4]`, `COLORS[3]`) and
        `init_declarator` (`b = 1.0`) via their `declarator` field until
        reaching the underlying name. Returns None for MISSING identifiers
        — the zero-width error-recovery placeholder produced by, e.g., the
        `precision highp float;` form.
        """
        while node is not None and node.type in ("array_declarator", "init_declarator"):
            node = node.child_by_field_name("declarator")
        if (
            node is not None
            and node.type in ("identifier", "field_identifier")
            and not node.is_missing
        ):
            return self.get_node_text(node, source)
        return None

    def _tag_glsl_features(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Flag builtin-variable, texture, and math-operation usage.

        Matches against extracted identifier/type tokens rather than a
        lowercase substring scan of the whole node's raw text — the
        previous implementation flagged `has_math_ops` on any identifier
        merely *containing* "dot" or "mix" (e.g. a variable named
        `dotProduct` or `mixture`).
        """
        names = self._collect_identifier_names(node, source)
        if names & _BUILTIN_VAR_NAMES:
            metadata["has_builtin_vars"] = True
        if names & _TEXTURE_OP_NAMES or any(
            name.startswith(_SAMPLER_TYPE_PREFIXES) for name in names
        ):
            metadata["has_texture_ops"] = True
        if names & _MATH_OP_NAMES:
            metadata["has_math_ops"] = True

    def _collect_identifier_names(self, node: Any, source: bytes) -> set[str]:
        """Collect the text of every identifier/type_identifier/field_identifier
        in node's subtree, for exact-match feature tagging in _tag_glsl_features.
        """
        names = set()
        stack = [node]
        while stack:
            current = stack.pop()
            if current.type in _IDENTIFIER_NODE_TYPES and not current.is_missing:
                names.add(self.get_node_text(current, source))
            stack.extend(current.children)
        return names
