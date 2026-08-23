"""Unit tests for GLSL's 5 Phase 3 relationship types.

Unlike Python, GLSL has no standalone `chunking/relationships/relationship_extractors/`
classes — `GLSLChunker.extract_metadata` (chunking/languages/glsl.py) walks the parse
tree once and appends plain relationship dicts to `metadata["relationships"]` inline
(see `_add_relationship`), which `materialize_relationship_edges`
(chunking/relationships/edge_specs.py) then converts into `RelationshipEdge` objects
with no re-parse. So these tests operate at the `MultiLanguageChunker.chunk_file()`
level — the same seam GLSL relationships actually flow through in production —
rather than instantiating an extractor directly.

Tests:
- IMPORTS       (#include "x.glslinc")
- DEFINES_CONSTANT (const decl and object-like #define; function-like #define excluded)
- DEFINES_FIELD  (struct field declarations)
- USES_TYPE      (struct-typed function parameter, struct-typed struct field)
- INSTANTIATES   (struct constructor call, disambiguated from an ordinary call)

The fixture below was validated empirically against the real chunker output before
these assertions were written (per this GLSL-parity effort's verification discipline)
so every expected line number/metadata value below reflects actual chunker behavior,
not an assumption about it.
"""

from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from chunking.relationships.relationship_types import RelationshipType


# A single small fixture exercising all 5 relationship types plus two negative
# cases (a function-like macro that must NOT produce DEFINES_CONSTANT, and an
# ordinary call that must NOT get reclassified as INSTANTIATES).
_FIXTURE_SOURCE = """\
// Fixture exercising all 5 GLSL Phase 3 relationship types.

#include "common.glslinc"

#define PI 3.14159265
#define SQUARE(x) ((x) * (x))

// Maximum number of lights this shader supports.
const int MAX_LIGHTS = 4;

struct Material {
    vec3 albedo;
    float roughness;
};

struct Light {
    vec3 direction;
    float intensity;
};

struct Scene {
    Material mat;
    Light light;
};

vec3 shade(Material mat, vec3 lightDir) {
    return mat.albedo * lightDir;
}

void main() {
    Material mat = Material(vec3(1.0), 0.5);
    vec3 color = shade(mat, vec3(0.0));
}
"""


@pytest.fixture
def glsl_chunks(tmp_path: Path):
    """Chunk `_FIXTURE_SOURCE` through the real MultiLanguageChunker -> GLSLChunker path."""
    file_path = tmp_path / "relationships.glsl"
    file_path.write_text(_FIXTURE_SOURCE, encoding="utf-8")

    chunker = MultiLanguageChunker(root_path=str(tmp_path))
    chunks = chunker.chunk_file(str(file_path))
    return {c.name: c for c in chunks}


def _rels(chunk, rel_type: RelationshipType):
    return [r for r in (chunk.relationships or []) if r.relationship_type == rel_type]


# ===== IMPORTS =====


def test_include_produces_imports_edge(glsl_chunks):
    """#include "common.glslinc" -> one IMPORTS edge on the include chunk itself."""
    include_chunk = glsl_chunks["common.glslinc"]
    edges = _rels(include_chunk, RelationshipType.IMPORTS)

    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "common.glslinc"
    assert edge.line_number == 3
    assert edge.metadata == {"is_system_include": False}
    assert edge.confidence == 1.0
    assert edge.source_id == include_chunk.chunk_id


# ===== DEFINES_CONSTANT =====


def test_object_like_macro_produces_defines_constant(glsl_chunks):
    """`#define PI 3.14159265` -> one DEFINES_CONSTANT edge, macro=True."""
    pi_chunk = glsl_chunks["PI"]
    edges = _rels(pi_chunk, RelationshipType.DEFINES_CONSTANT)

    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "PI"
    assert edge.line_number == 5
    assert edge.metadata == {"definition": True, "macro": True}


def test_function_like_macro_produces_no_defines_constant(glsl_chunks):
    """`#define SQUARE(x) ...` is a macro function, not a value -> no edge."""
    square_chunk = glsl_chunks["SQUARE"]
    assert not square_chunk.relationships


def test_const_declaration_produces_defines_constant(glsl_chunks):
    """`const int MAX_LIGHTS = 4;` -> one DEFINES_CONSTANT edge, no macro flag."""
    max_lights_chunk = glsl_chunks["MAX_LIGHTS"]
    edges = _rels(max_lights_chunk, RelationshipType.DEFINES_CONSTANT)

    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "MAX_LIGHTS"
    assert edge.line_number == 9
    assert edge.metadata == {"definition": True}


# ===== DEFINES_FIELD =====


def test_struct_fields_produce_defines_field_edges(glsl_chunks):
    """Each `struct Material { ... }` field -> a `Material.<field>` DEFINES_FIELD edge."""
    material_chunk = glsl_chunks["Material"]
    edges = _rels(material_chunk, RelationshipType.DEFINES_FIELD)

    targets = {(e.target_name, e.line_number) for e in edges}
    assert targets == {
        ("Material.albedo", 12),
        ("Material.roughness", 13),
    }
    for edge in edges:
        assert edge.metadata["struct_name"] == "Material"


def test_struct_field_of_struct_type_produces_both_edges(glsl_chunks):
    """`Scene.mat` is both a DEFINES_FIELD edge and (since its type, Material, is
    itself a known struct) a USES_TYPE edge -- unlike a plain vec3/float field."""
    scene_chunk = glsl_chunks["Scene"]

    field_edges = {
        e.target_name: e for e in _rels(scene_chunk, RelationshipType.DEFINES_FIELD)
    }
    assert set(field_edges) == {"Scene.mat", "Scene.light"}
    assert field_edges["Scene.mat"].line_number == 22
    assert field_edges["Scene.light"].line_number == 23


# ===== USES_TYPE =====


def test_struct_typed_field_produces_uses_type_edge(glsl_chunks):
    """Scene's `Material mat;` / `Light light;` fields each produce a field-level
    USES_TYPE edge naming the struct type, since vec3/float fields (Material's own
    fields) do not -- only struct-typed fields do."""
    scene_chunk = glsl_chunks["Scene"]
    edges = {e.target_name: e for e in _rels(scene_chunk, RelationshipType.USES_TYPE)}

    assert set(edges) == {"Material", "Light"}
    assert edges["Material"].line_number == 22
    assert edges["Material"].metadata == {
        "annotation_location": "field",
        "field_name": "mat",
    }
    assert edges["Light"].line_number == 23
    assert edges["Light"].metadata == {
        "annotation_location": "field",
        "field_name": "light",
    }

    # Material's own vec3/float fields are builtin types, not structs -- no
    # USES_TYPE edges on Material itself.
    material_chunk = glsl_chunks["Material"]
    assert not _rels(material_chunk, RelationshipType.USES_TYPE)


def test_struct_typed_parameter_produces_uses_type_edge(glsl_chunks):
    """`vec3 shade(Material mat, vec3 lightDir)` -> one USES_TYPE edge for the
    struct-typed `Material` parameter; the builtin-typed `vec3` parameter does not
    produce one."""
    shade_chunk = glsl_chunks["shade"]
    edges = _rels(shade_chunk, RelationshipType.USES_TYPE)

    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "Material"
    assert edge.line_number == 26
    assert edge.metadata == {
        "annotation_location": "parameter",
        "parameter_name": "mat",
    }


# ===== INSTANTIATES =====


def test_struct_constructor_call_produces_instantiates_edge(glsl_chunks):
    """`Material(vec3(1.0), 0.5)` -> one INSTANTIATES edge; the sibling `shade(...)`
    call in the same function is an ordinary call, not a relationship edge."""
    main_chunk = glsl_chunks["main"]
    edges = _rels(main_chunk, RelationshipType.INSTANTIATES)

    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "Material"
    assert edge.line_number == 31
    assert edge.metadata == {"struct_name": "Material"}

    # `shade` is a real user function, not a struct -- it must show up in `calls`,
    # never reclassified as INSTANTIATES.
    assert any(callee.callee_name == "shade" for callee in main_chunk.calls)
    assert not any(e.target_name == "shade" for e in main_chunk.relationships or [])
