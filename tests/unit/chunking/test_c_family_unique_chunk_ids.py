"""Regression tests for duplicate chunk ids (ADR-0087 addendum).

A chunk id is `path:start-end:type[:name]`, so two unnamed `module_preamble`
chunks on one line collide, and a full reindex fails its position check.
Preamble descent produced them: a prototype naming `enum PyUnicode_Kind`
held a bodyless `enum_specifier` chunk, so it was descended to declarator
level and the runs on either side of that chunk shared a line
(CPython `unicodeobject.h:780`). Two fixes, each sufficient for that file:
bodyless specifiers are no longer chunks, and no two preamble chunks may
share a line in any language.
"""

from collections import Counter

import pytest

from chunking.languages.c import CChunker
from chunking.languages.cpp import CppChunker
from chunking.tree_sitter import TreeSitterChunker


# `PyAPI_FUNC(int)` is blanked by the bare-macro repair; the prototype then
# parses as a root ERROR holding a function_declarator.
_PROTOTYPE_NAMING_AN_ENUM = """/* Don't call this function directly, use the macro
   instead. */
PyAPI_FUNC(int)
_PyUnicodeWriter_PrepareKindInternal(_PyUnicodeWriter *writer,
                                     enum PyUnicode_Kind kind);
"""

_SPECIFIER_TYPES = {
    "struct_specifier",
    "enum_specifier",
    "union_specifier",
    "class_specifier",
}


def _keys(chunks):
    return [
        (c.start_line, c.end_line, c.node_type, c.metadata.get("name")) for c in chunks
    ]


def _duplicates(chunks):
    return [key for key, n in Counter(_keys(chunks)).items() if n > 1]


def _preambles(chunks):
    return [c for c in chunks if c.node_type == "module_preamble"]


class TestPrototypeNamingAnEnumType:
    @pytest.mark.parametrize(
        "source",
        [
            _PROTOTYPE_NAMING_AN_ENUM,
            'extern "C" {\n' + _PROTOTYPE_NAMING_AN_ENUM + "}\n",
        ],
        ids=["root", "extern_c"],
    )
    def test_no_duplicate_chunk_keys(self, source):
        assert _duplicates(CppChunker().chunk_code(source)) == []

    def test_prototype_lands_in_one_preamble_with_its_comment(self):
        (preamble,) = _preambles(CppChunker().chunk_code(_PROTOTYPE_NAMING_AN_ENUM))
        assert "Don't call this function directly" in preamble.content
        assert "_PyUnicodeWriter_PrepareKindInternal(_PyUnicodeWriter *writer," in (
            preamble.content
        )
        assert "enum PyUnicode_Kind kind);" in preamble.content


class TestBodylessSpecifiersAreNotChunks:
    """A forward declaration or a type reference defines nothing."""

    @pytest.mark.parametrize(
        ("chunker", "source"),
        [
            (CChunker, "struct S;\n"),
            (CChunker, "int g(struct S *p);\n"),
            (CChunker, "void h(enum K k);\n"),
            (CppChunker, "class Foo;\n"),
            (CppChunker, "enum class K : int;\n"),
            (CppChunker, "union U;\n"),
        ],
        ids=[
            "c_struct_decl",
            "c_struct_param",
            "c_enum_param",
            "cpp_class_decl",
            "cpp_opaque_enum",
            "cpp_union_decl",
        ],
    )
    def test_no_specifier_chunk(self, chunker, source):
        kinds = {c.node_type for c in chunker().chunk_code(source)}
        assert kinds.isdisjoint(_SPECIFIER_TYPES), kinds

    @pytest.mark.parametrize(
        ("chunker", "source", "kind", "name"),
        [
            (CChunker, "struct S {\n    int a;\n};\n", "struct_specifier", "S"),
            (CChunker, "enum K {\n    A,\n    B,\n};\n", "enum_specifier", "K"),
            (
                CppChunker,
                "class Foo : public Bar {\npublic:\n    int f() const { return 1; }\n};\n",
                "class_specifier",
                "Foo",
            ),
        ],
        ids=["c_struct", "c_enum", "cpp_class"],
    )
    def test_specifiers_with_a_body_still_chunk(self, chunker, source, kind, name):
        assert (kind, name) in {
            (c.node_type, c.metadata.get("name")) for c in chunker().chunk_code(source)
        }


class TestPreamblesNeverShareALine:
    """Two runs on one line around a chunk collide in every language."""

    @pytest.mark.parametrize(
        ("filename", "source"),
        [
            ("x.c", "int a = 1; int f(void) { return 0; } int b = 2;\n"),
            ("x.js", "const a = 1; function f() { return 1; } const b = 2;\n"),
            ("x.ts", "const a = 1; function f(): number { return 1; } const b = 2;\n"),
        ],
        ids=["c", "js", "ts"],
    )
    def test_runs_on_one_line_merge_into_one_preamble(self, filename, source):
        chunks = TreeSitterChunker().chunk_file(filename, content=source)
        (preamble,) = _preambles(chunks)
        assert "a = 1" in preamble.content and "b = 2" in preamble.content
        assert _duplicates(chunks) == []


class TestSameIdChunksFold:
    """Same-name overloads on one line share an id, so they fold into one chunk.

    opencv `matx.hpp` declares `Matx_AddOp() {} Matx_AddOp(const Matx_AddOp&)
    {}` on one line inside `class CV_EXPORTS Matx_AddOp`; once the class head
    parsed, both constructors chunked as `function_definition:Matx_AddOp`.
    """

    @pytest.mark.parametrize(
        ("filename", "source", "line", "first", "second"),
        [
            (
                "x.hpp",
                "class A {\npublic:\n    A() {} A(const A&) {}\n};\n",
                3,
                "A() {}",
                "A(const A&) {}",
            ),
            (
                "X.cs",
                "class A {\n    void F() {} void F(int x) {}\n}\n",
                2,
                "void F() {}",
                "void F(int x) {}",
            ),
        ],
        ids=["cpp_constructors", "csharp_methods"],
    )
    def test_overloads_on_one_line_fold(self, filename, source, line, first, second):
        chunks = TreeSitterChunker().chunk_file(filename, content=source)
        keys = [
            (*key, c.parent_class) for key, c in zip(_keys(chunks), chunks, strict=True)
        ]
        assert [k for k, n in Counter(keys).items() if n > 1] == []
        (folded,) = [c for c in chunks if c.start_line == line and first in c.content]
        assert folded.content.startswith(first)
        assert folded.content.endswith(second)

    def test_overloads_on_separate_lines_stay_apart(self):
        source = "class A {\npublic:\n    A() {}\n    A(const A&) {}\n};\n"
        chunks = TreeSitterChunker().chunk_file("x.hpp", content=source)
        lines = [c.start_line for c in chunks if c.metadata.get("name") == "A"]
        assert lines == [1, 3, 4]
