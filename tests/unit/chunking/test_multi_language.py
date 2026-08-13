"""Basic tests for multi-language chunking."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from search.config import ChunkingConfig


class TestMultiLanguageChunker:
    """Test multi-language chunking functionality."""

    @pytest.fixture
    def chunker(self):
        """Create a chunker instance."""
        return MultiLanguageChunker()

    @pytest.fixture
    def test_data_dir(self):
        """Get test data directory."""
        return Path(__file__).parent.parent.parent / "test_data" / "multi_language"

    def test_supported_extensions(self, chunker):
        """Test that all required extensions are supported."""
        assert chunker.is_supported("test.py")
        assert chunker.is_supported("test.js")
        assert chunker.is_supported("test.ts")
        assert chunker.is_supported("test.tsx")
        assert chunker.is_supported("test.go")
        assert chunker.is_supported("test.c")
        assert chunker.is_supported("test.cpp")
        assert chunker.is_supported("test.cc")
        assert chunker.is_supported("test.cxx")
        assert chunker.is_supported("test.c++")
        assert chunker.is_supported("test.h")
        assert chunker.is_supported("test.hpp")
        assert chunker.is_supported("test.hh")
        assert chunker.is_supported("test.hxx")
        assert chunker.is_supported("test.inl")
        assert chunker.is_supported("test.ipp")
        assert chunker.is_supported("test.tpp")
        assert chunker.is_supported("test.cs")
        assert chunker.is_supported("test.rs")
        assert chunker.is_supported("test.glsl")
        assert chunker.is_supported("test.frag")
        assert chunker.is_supported("test.vert")
        assert chunker.is_supported("test.comp")
        assert chunker.is_supported("test.geom")
        assert chunker.is_supported("test.tesc")
        assert chunker.is_supported("test.tese")
        assert not chunker.is_supported("test.txt")

    def test_chunk_python_file(self, chunker, test_data_dir):
        """Test chunking Python file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "example.py"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find the class and functions
            chunk_types = {chunk.chunk_type for chunk in chunks}
            assert "function" in chunk_types or "method" in chunk_types
            assert "class" in chunk_types

    def test_chunk_javascript_file(self, chunker, test_data_dir):
        """Test chunking JavaScript file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "example.js"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find functions and class
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            assert "calculateSum" in chunk_names
            assert "Calculator" in chunk_names

    def test_chunk_typescript_file(self, chunker, test_data_dir):
        """Test chunking TypeScript file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "example.ts"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find interface, class, and functions
            chunk_types = {chunk.chunk_type for chunk in chunks}
            assert any(t in chunk_types for t in ["class", "interface", "function"])

    def test_chunk_tsx_file(self, chunker, test_data_dir):
        """Test chunking TSX file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "Component.tsx"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find TypeScript React components
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            assert any(name in chunk_names for name in ["TypedCounter", "UserList"])

    def test_chunk_go_file(self, chunker, test_data_dir):
        """Test chunking Go file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "calculator.go"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find functions, methods, types, and interfaces
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            chunk_types = {chunk.chunk_type for chunk in chunks}

            assert any(
                name in chunk_names
                for name in ["Calculator", "CalculateSum", "NewCalculator"]
            )
            assert len(chunk_names) > 0
            # `or len(chunks) > 0` was already proven true by the assertion
            # at the top of this test, making the whole expression an
            # unconditional pass regardless of what chunk_types actually
            # contains — dropped so this checks what it claims to check.
            assert any(
                t in chunk_types for t in ["function", "method", "type", "interface"]
            ), f"Expected a Go-relevant chunk type, got {chunk_types}"

    def test_chunk_c_file(self, chunker, test_data_dir):
        """Test chunking C file."""
        file_path = test_data_dir / "calculator.c"
        chunks = chunker.chunk_file(str(file_path))

        # tree-sitter-c is a hard dependency (pyproject.toml), not optional --
        # the parser is always available, so this must produce real chunks.
        assert len(chunks) > 0, "C parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert any(
            name in chunk_names
            for name in ["calculate_sum", "get_result", "apply_operation"]
        )

    def test_chunk_c_typedef_name(self, chunker, test_data_dir):
        """Test that anonymous-struct/enum typedefs get a name.

        Regression guard: `type_definition`'s name lives on a
        `type_identifier` child (e.g. `typedef struct {...} Calculator;`),
        not a plain `identifier` -- c.py's extract_metadata only checked
        `identifier`, so every anonymous-struct/enum typedef silently
        chunked with name=None. Found via the C++ chunking parity plan's
        live gate verification, unrelated to that plan's declarator-unwrap
        fix (which only covers `function_definition`).
        """
        file_path = test_data_dir / "calculator.c"
        chunks = chunker.chunk_file(str(file_path))

        typedef_names = {
            chunk.name for chunk in chunks if chunk.chunk_type == "type_definition"
        }
        assert typedef_names == {"Calculator", "Operation"}

    def test_chunk_cpp_file(self, chunker, test_data_dir):
        """Test chunking C++ file."""
        file_path = test_data_dir / "Calculator.cpp"
        chunks = chunker.chunk_file(str(file_path))

        # tree-sitter-cpp is a hard dependency (pyproject.toml), not optional --
        # the parser is always available, so this must produce real chunks.
        assert len(chunks) > 0, "C++ parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert any(name in chunk_names for name in ["Point", "main"])

    def test_chunk_cpp_header_file(self, chunker, tmp_path):
        """Test chunking a .h header file end-to-end.

        Regression guard: `.h` was added to SUPPORTED_EXTENSIONS /
        EXT_TO_LANGUAGE (Phase 1) but `TreeSitterChunker.LANGUAGE_MAP` --
        a separate suffix -> chunker-factory dict in tree_sitter.py -- was
        not updated alongside it, so `get_chunker(".h")` silently returned
        None and headers produced zero chunks despite is_supported()
        reporting True. is_supported() alone would not catch this; only an
        actual chunk_file() call does.
        """
        header = tmp_path / "widget.h"
        header.write_text(
            "class Widget {\npublic:\n    void draw();\n};\n", encoding="utf-8"
        )
        chunks = chunker.chunk_file(str(header))

        assert len(chunks) > 0, "Header parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "Widget" in chunk_names
        assert "draw" in chunk_names

    def test_chunk_cpp_anonymous_namespace_and_enum(self, chunker, tmp_path):
        """Anonymous namespace/enum have no `name`/`namespace_identifier`/
        `type_identifier` child at all -- exercises extract_metadata's
        field-lookup-returns-None fallback branch for both node types (a
        *named* namespace/enum resolves via `child_by_field_name("name")`
        directly and never reaches the fallback scan).

        Also documents a Copilot PR #57 review comment that flagged this as
        a bug (`child_by_field_name("name")` returning a MISSING
        error-recovery placeholder, forcing `metadata["name"] = ""`).
        Verified false against live tree-sitter-cpp output: an anonymous
        namespace/enum has no name child at all -- `child_by_field_name`
        returns plain `None`, not a MISSING node -- so `metadata["name"]` is
        never set and `chunk.name` stays `None`, never `""`.
        """
        source = tmp_path / "anon.cpp"
        source.write_text(
            "namespace { void helper() {} }\nenum { X, Y };\n", encoding="utf-8"
        )
        chunks = chunker.chunk_file(str(source))

        assert len(chunks) > 0, "C++ parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "helper" in chunk_names

        anon_namespace = next((c for c in chunks if c.chunk_type == "namespace"), None)
        assert anon_namespace is not None, "Anonymous namespace should still chunk"
        assert anon_namespace.name is None, (
            "Anonymous namespace should have name=None, never name=''"
        )

    def test_chunk_cpp_reference_returning_declaration(self, chunker, tmp_path):
        """Header-only reference-returning method declaration (`int& getRef();`).

        `reference_declarator` has no `declarator` field in tree-sitter-cpp's
        grammar, so `declarator_is_function_shaped`'s None-field fallback (the
        gate `should_chunk_node` uses to narrow `field_declaration` down to
        function-shaped ones) is only reachable from a node like this one --
        `T& operator=`-style function_definitions go through the base
        splittable-node path instead and never call it.
        """
        source = tmp_path / "ref_getter.h"
        source.write_text(
            "class Shape {\npublic:\n    int& getRef();\n};\n", encoding="utf-8"
        )
        chunks = chunker.chunk_file(str(source))

        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "getRef" in chunk_names

    def test_chunk_cpp_anonymous_typedef_struct_union_enum(self, chunker, tmp_path):
        """Anonymous struct/union/enum typedefs get a name on the cpp path (P0).

        Regression guard: `type_definition` is in c's `splittable_node_types`
        but not cpp's (chunking/language_registry.py), so
        `typedef struct {...} Vec3;` only chunks its anonymous inner
        `struct_specifier` under the cpp grammar -- the alias name lives one
        level up, as a direct child of the parent `type_definition`, not a
        child of the specifier itself. Before the fix all three chunked with
        name=None despite this exact idiom being the most common C-header
        declaration shape (the path this PR's `.h` routing feature targets).
        A *named* `typedef struct Point {...} Point_t;` is unaffected --
        covered separately by not regressing test_chunk_cpp_header_file.
        """
        source = tmp_path / "shapes.h"
        source.write_text(
            "typedef struct { int x; int y; int z; } Vec3;\n"
            "typedef union { int i; float f; } Word;\n"
            "typedef enum { RED, GREEN, BLUE } Color;\n",
            encoding="utf-8",
        )
        chunks = chunker.chunk_file(str(source))

        assert len(chunks) > 0, "C++ parser produced no chunks"
        nameless = [c for c in chunks if c.name is None]
        assert not nameless, f"Expected zero nameless chunks, got {nameless}"
        chunk_names = {chunk.name for chunk in chunks}
        assert {"Vec3", "Word", "Color"} <= chunk_names

    def test_chunk_cpp_member_function_pointer(self, chunker, tmp_path):
        """C-style function-pointer struct/class member gets a name (P1).

        Regression guard: `void (*cb)(int,int);`'s declarator chain is
        `function_declarator -> parenthesized_declarator ->
        pointer_declarator -> field_identifier "cb"`.
        `parenthesized_declarator` was missing from `_WRAPPER_DECLARATOR_TYPES`,
        so `unwrap_declarator_name` stopped dead there and returned None, even
        though `declarator_is_function_shaped` correctly chunked the member
        (it short-circuits True on the outer `function_declarator` before ever
        reaching the parenthesized wrapper). Members chunk as chunk_type
        "method" (parent_type="class" promotion), not "function".
        """
        source = tmp_path / "table.h"
        source.write_text(
            "struct Table {\n    void (*cb)(int, int);\n};\n", encoding="utf-8"
        )
        chunks = chunker.chunk_file(str(source))

        cb_chunk = next((c for c in chunks if c.name == "cb"), None)
        assert cb_chunk is not None, (
            f"Expected a chunk named 'cb', got names {[c.name for c in chunks]}"
        )
        assert cb_chunk.chunk_type == "method"

    def test_chunk_cpp_global_function_pointer(self, chunker, tmp_path):
        """Global (non-member) function-pointer declaration gets a name (P1).

        Same `parenthesized_declarator` gap as the member case, but on a
        `declaration` node (not `field_declaration`) at global/namespace
        scope -- exercises the same unwrap chain from a different splittable
        node type.
        """
        source = tmp_path / "handler.h"
        source.write_text("void (*g_handler)(int);\n", encoding="utf-8")
        chunks = chunker.chunk_file(str(source))

        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "g_handler" in chunk_names

    def test_chunk_cpp_function_returning_function_pointer(self, chunker, tmp_path):
        """A real function *definition* returning a function pointer gets a
        name (P1) -- `void (*getHandler(int))(int) {...}` has the same
        `parenthesized_declarator`-wrapped name deep in its declarator chain,
        but as an actual `function_definition` rather than a bare
        declaration.
        """
        source = tmp_path / "factory.cpp"
        source.write_text(
            "void (*getHandler(int x))(int) { return nullptr; }\n", encoding="utf-8"
        )
        chunks = chunker.chunk_file(str(source))

        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "getHandler" in chunk_names

    def test_chunk_c_function_pointer_typedef(self, chunker, tmp_path):
        """`typedef void (*Callback)(int);` gets a name on the c path (P1).

        Regression guard: the direct-child scan in c.py's `type_definition`
        branch finds no `identifier`/`type_identifier` direct child for this
        shape (the name is nested inside the declarator chain), so it falls
        back to `unwrap_declarator_name` with `extra_terminals={"type_identifier"}`.
        A bare fallback without widening the terminal set still returns None,
        since the chain terminates at `type_identifier`, which
        `_TERMINAL_DECLARATOR_TYPES` does not include by default.
        """
        source = tmp_path / "callback.c"
        source.write_text("typedef void (*Callback)(int);\n", encoding="utf-8")
        chunks = chunker.chunk_file(str(source))

        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "Callback" in chunk_names

    def test_chunk_cpp_struct_member_parent_chunk_id(self, chunker, tmp_path):
        """Struct members get `parent_chunk_id` pointing at the struct (P2).

        Regression guard: `_convert_tree_chunks`'s `class_chunk_map`
        registration gate only covered `("class", "namespace")`, but
        `struct_specifier` became a container in this PR (C++ header parity)
        -- so struct members now chunk separately, each with
        `parent_chunk_id=None`, unlike an equivalent `class`'s methods.
        """
        source = tmp_path / "plain.h"
        source.write_text("struct Plain {\n    void go();\n};\n", encoding="utf-8")
        chunks = chunker.chunk_file(str(source))

        struct_chunk = next((c for c in chunks if c.name == "Plain"), None)
        go_chunk = next((c for c in chunks if c.name == "go"), None)
        assert struct_chunk is not None, "Struct chunk should exist"
        assert go_chunk is not None, "Method chunk should exist"
        assert go_chunk.parent_chunk_id == struct_chunk.chunk_id, (
            "Struct member should have parent_chunk_id pointing at the struct"
        )

    def test_chunk_cpp_nested_same_named_namespace_parent_linkage(
        self, chunker, tmp_path
    ):
        """Same-named nested namespaces resolve parent_chunk_id by innermost
        enclosing span, not by traversal-order last-write-wins (PR #57 review).

        Regression guard: `_convert_tree_chunks`'s `class_chunk_map` used to be
        a flat `(relative_path, name) -> chunk_id` dict. For a reopened
        namespace (`namespace A { namespace A { void f(); } void g(); }`),
        registering the inner `A` overwrote the outer `A`'s entry, so `g` --
        whose real parent is the *outer* `A` -- resolved to the *inner* `A`'s
        chunk_id once the inner namespace had been visited. `f`'s lookup
        happened to still be correct (it's inside the inner namespace, which
        was the most-recently-registered entry at that point), masking the
        bug for the common case.
        """
        source = tmp_path / "nested_ns.cpp"
        source.write_text(
            "namespace A {\n"
            "    namespace A {\n"
            "        void f() { }\n"
            "    }\n"
            "    void g() { }\n"
            "}\n",
            encoding="utf-8",
        )
        chunks = chunker.chunk_file(str(source))

        outer_ns = next(
            (c for c in chunks if c.chunk_type == "namespace" and c.start_line == 1),
            None,
        )
        inner_ns = next(
            (c for c in chunks if c.chunk_type == "namespace" and c.start_line == 2),
            None,
        )
        f_chunk = next((c for c in chunks if c.name == "f"), None)
        g_chunk = next((c for c in chunks if c.name == "g"), None)
        assert outer_ns is not None and inner_ns is not None
        assert f_chunk is not None and g_chunk is not None

        assert f_chunk.parent_chunk_id == inner_ns.chunk_id, (
            "f is a direct child of the inner (reopened) namespace"
        )
        assert g_chunk.parent_chunk_id == outer_ns.chunk_id, (
            "g is a direct child of the outer namespace, not the inner one "
            "it happens to share a name with"
        )

    def test_chunk_cpp_templated_prototype_and_alias_naming(self, chunker, tmp_path):
        """Templated header-only prototypes and aliases get a name.

        Regression guard: `extract_metadata`'s `template_declaration` child
        scan looked for `function_definition | class_specifier |
        struct_specifier | union_specifier` -- but `should_chunk_node`
        already returns False for a template_declaration wrapping a
        class/struct/union, so those three branches were unreachable dead
        code, and the scan never matched `declaration` (a templated
        prototype, e.g. `template<typename T> void proto(T v);`) or
        `alias_declaration` (a templated alias, e.g.
        `template<class T> using Ptr = T*;`) -- both chunked with
        name=None despite `extract_metadata` already having working
        handlers for both node types via its `declaration`/`alias_declaration`
        branches.
        """
        source = tmp_path / "templates.hpp"
        source.write_text(
            "template<typename T> void proto(T v);\n"
            "template<class T> using Ptr = T*;\n"
            "template<typename T> T add(T a, T b) { return a + b; }\n",
            encoding="utf-8",
        )
        chunks = chunker.chunk_file(str(source))

        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "proto" in chunk_names
        assert "Ptr" in chunk_names
        assert "add" in chunk_names

    def test_chunk_pure_c_header_under_cpp_grammar(self, chunker, tmp_path):
        """Pure-C-only constructs parse cleanly under the cpp grammar in a
        `.h` file, with no ERROR/MISSING recovery nodes.

        Both PR #57 reviews flagged that routing all header extensions to
        the C++ grammar (chunking/tree_sitter.py) means pure-C headers using
        C-only syntax get parsed by tree_sitter_cpp instead of tree_sitter_c.
        Verified empirically (not just asserted) against `_Generic`, a
        flexible array member, a `restrict`-qualified VLA parameter, and a
        C99 designated initializer -- tree-sitter-cpp parses all of them
        without error, and every declaration still gets a name.
        """
        source = tmp_path / "legacy.h"
        source.write_text(
            "#define MAX(a,b) _Generic((a), int: imax, default: dmax)(a,b)\n"
            "int imax(int a, int b);\n"
            "struct Buf { int n; char data[]; };\n"
            "void copy(int n, int m, double a[restrict n][m]);\n"
            "static const struct Cfg cfg = { .width = 4, .height = 8 };\n",
            encoding="utf-8",
        )
        chunks = chunker.chunk_file(str(source))

        assert len(chunks) > 0, "Pure-C header produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert {"imax", "Buf", "copy", "Cfg"} <= chunk_names

    def test_cpp_function_node_types(self):
        """Only `function_definition` counts as a function for the adaptive-
        sizing profiler -- containers and the header-only declaration types
        added alongside them must not skew its size-percentile baseline.
        """
        from chunking.languages.cpp import CppChunker

        assert CppChunker().function_node_types == frozenset({"function_definition"})

    def test_chunk_csharp_file(self, chunker, test_data_dir):
        """Test chunking C# file."""
        file_path = test_data_dir / "Calculator.cs"
        chunks = chunker.chunk_file(str(file_path))

        # tree-sitter-c-sharp is a hard dependency (pyproject.toml), not optional --
        # the parser is always available, so this must produce real chunks.
        assert len(chunks) > 0, "C# parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert any(name in chunk_names for name in ["Math"])

    def test_chunk_glsl_file(self, chunker, test_data_dir):
        """Test chunking GLSL file."""
        file_path = test_data_dir / "example.glsl"
        chunks = chunker.chunk_file(str(file_path))

        # tree-sitter-glsl is a hard dependency (pyproject.toml), not optional --
        # the parser is always available, so this must produce real chunks.
        assert len(chunks) > 0, "GLSL parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        chunk_types = {chunk.chunk_type for chunk in chunks}

        assert any(name in chunk_names for name in ["Wave", "computeWave", "main"])
        assert any(t in chunk_types for t in ["struct", "function"])

    def test_chunk_rust_file(self, chunker, test_data_dir):
        """Test chunking Rust file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "calculator.rs"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find functions, structs, traits, enums, impls, macros
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            chunk_types = {chunk.chunk_type for chunk in chunks}

            assert any(
                name in chunk_names
                for name in [
                    "Calculator",
                    "calculate_sum",
                    "MathOperations",
                    "Operation",
                    "Point",
                ]
            )
            assert any(
                t in chunk_types
                for t in ["function", "struct", "trait", "enum", "impl", "macro"]
            )
