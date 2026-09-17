"""Unit tests for graph.procedural_graph (ADR-0074).

Covers the file-backed ProceduralGraph/ProceduralGraphStore: document
validation (report every error, never just the first), the document- vs
NetworkX-canonical-state split, locate/extract/serialize, apply_edit, and
the bundled network_layout seed fixture (tests/fixtures/pg/).
"""

import json
from pathlib import Path

import pytest

from graph.procedural_graph import (
    NAME_PATTERN,
    NODE_ID_PATTERN,
    PG_EDGE_FIELDS,
    PG_RELATIONS,
    PG_SCHEMA_VERSION,
    ProceduralGraph,
    ProceduralGraphError,
    ProceduralGraphStore,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = REPO_ROOT / "tests" / "fixtures" / "pg" / "network_layout_seed.json"

CONTRACT_NODE_ORDER = [
    "Start",
    "Read_Layout",
    "Identify_Group",
    "Compute_Positions",
    "Create_Op",
    "Set_Position",
    "Connect_Ops",
    "Query_Docked",
    "Reposition_Docked",
    "Update_Annotation",
    "Verify_Layout",
    "End",
]


def _edge(src, dst, relation="LEADS_TO", condition="c", guidance="g", pitfalls="p"):
    return {
        "src": src,
        "dst": dst,
        "relation": relation,
        "condition": condition,
        "guidance": guidance,
        "pitfalls": pitfalls,
    }


def _toy_doc(**overrides):
    """A minimal valid document: A -LEADS_TO-> B -LEADS_TO-> C.

    A is the sole entry (in-degree 0); C is the sole terminal (out-degree 0).
    """
    doc = {
        "schema_version": PG_SCHEMA_VERSION,
        "name": "toy",
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "edges": [
            _edge("A", "B", condition="c1", guidance="g1", pitfalls="p1"),
            _edge("B", "C", condition="c2", guidance="g2", pitfalls=""),
        ],
    }
    doc.update(overrides)
    return doc


def _toy_graph():
    return ProceduralGraph.from_document(_toy_doc())


def _seed_doc():
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def _seed_graph():
    return ProceduralGraph.from_document(_seed_doc())


def _errors_of(doc):
    with pytest.raises(ProceduralGraphError) as exc_info:
        ProceduralGraph.from_document(doc)
    return list(exc_info.value.errors)


# --- contract ----------------------------------------------------------------


def test_pg_relations_pinned():
    assert PG_RELATIONS == (
        "LEADS_TO",
        "TRIGGERS",
        "PROVIDES_INPUT_FOR",
        "CONVERGES_TO",
    )


def test_pg_edge_fields_pinned():
    assert PG_EDGE_FIELDS == ("condition", "guidance", "pitfalls")


@pytest.mark.parametrize("name", ["", "a.b", "a/b", "a\\b", "x" * 65])
def test_name_pattern_rejects_dot_slash_and_empty(name):
    assert not NAME_PATTERN.match(name)


def test_name_pattern_accepts_hyphen_and_underscore():
    assert NAME_PATTERN.match("network_layout-v2")


@pytest.mark.parametrize("node_id", ["1abc", "-abc", "a-b", ""])
def test_node_id_pattern_rejects_leading_digit_and_hyphen(node_id):
    assert not NODE_ID_PATTERN.match(node_id)


# --- document rejection --------------------------------------------------


def test_document_must_be_a_dict():
    errors = _errors_of(["not", "a", "dict"])
    assert errors == ["document must be an object"]


def test_document_rejects_wrong_schema_version():
    errors = _errors_of(_toy_doc(schema_version=2))
    assert any("schema_version" in e for e in errors)


def test_document_rejects_missing_name():
    doc = _toy_doc()
    del doc["name"]
    errors = _errors_of(doc)
    assert any("name" in e for e in errors)


def test_document_rejects_invalid_name_pattern():
    errors = _errors_of(_toy_doc(name="not/a/name"))
    assert any("name" in e for e in errors)


def test_document_rejects_unknown_top_level_key():
    errors = _errors_of(_toy_doc(unexpected="oops"))
    assert any("unknown top-level key" in e for e in errors)


def test_document_rejects_non_string_notes():
    errors = _errors_of(_toy_doc(notes=123))
    assert any("notes must be a string" in e for e in errors)


def test_document_rejects_nodes_not_a_list():
    errors = _errors_of(_toy_doc(nodes="oops"))
    assert any("nodes must be a list" in e for e in errors)


def test_document_rejects_edges_not_a_list():
    errors = _errors_of(_toy_doc(edges="oops"))
    assert any("edges must be a list" in e for e in errors)


def test_document_rejects_node_not_a_dict():
    errors = _errors_of(_toy_doc(nodes=[{"id": "A"}, "not-a-dict", {"id": "C"}]))
    assert any("nodes[1]" in e for e in errors)


def test_document_rejects_node_with_extra_key():
    errors = _errors_of(
        _toy_doc(nodes=[{"id": "A", "extra": 1}, {"id": "B"}, {"id": "C"}])
    )
    assert any("nodes[0]" in e for e in errors)


def test_document_rejects_duplicate_node_id():
    errors = _errors_of(
        {**_toy_doc(), "nodes": [{"id": "A"}, {"id": "A"}], "edges": []}
    )
    assert errors == ["document: duplicate node id 'A'"]


def test_document_rejects_dangling_edge_endpoint():
    doc = _toy_doc(
        nodes=[{"id": "A"}, {"id": "B"}], edges=[_edge("A", "B"), _edge("B", "C")]
    )
    errors = _errors_of(doc)
    assert any("dst 'C' is not a declared node" in e for e in errors)


def test_document_rejects_duplicate_edge_triple():
    doc = _toy_doc(
        nodes=[{"id": "A"}, {"id": "B"}],
        edges=[_edge("A", "B"), _edge("A", "B", guidance="different text")],
    )
    errors = _errors_of(doc)
    assert any("duplicate edge" in e for e in errors)


def test_document_rejects_edge_missing_key():
    edge = _edge("A", "B")
    del edge["pitfalls"]
    errors = _errors_of(_toy_doc(edges=[edge]))
    assert any("edges[0]" in e and "keys" in e for e in errors)


def test_document_rejects_edge_extra_key():
    edge = {**_edge("A", "B"), "extra": "oops"}
    errors = _errors_of(_toy_doc(edges=[edge]))
    assert any("edges[0]" in e and "keys" in e for e in errors)


def test_document_rejects_non_string_edge_field():
    errors = _errors_of(_toy_doc(edges=[_edge("A", "B", condition=123)]))
    assert any("edges[0].condition must be a string" in e for e in errors)


def test_document_rejects_unknown_relation():
    errors = _errors_of(_toy_doc(edges=[_edge("A", "B", relation="FOO")]))
    assert any("relation 'FOO' is not one of" in e for e in errors)


def test_document_rejects_self_loop():
    errors = _errors_of(_toy_doc(edges=[_edge("A", "A")]))
    assert any("self-loop" in e for e in errors)


def test_document_reports_every_error_not_just_first():
    doc = _toy_doc(
        schema_version=99,
        name="bad name!",
        nodes=[{"id": "A"}, {"id": "A"}],
        edges=[],
    )
    errors = _errors_of(doc)
    assert len(errors) >= 3


def test_document_errors_are_deterministic_order():
    doc = _toy_doc(schema_version=99, name="bad name!", edges=[_edge("A", "Z")])
    assert _errors_of(doc) == _errors_of(doc)


# --- fixture drift ---------------------------------------------------------


def test_seed_fixture_loads_and_validates():
    graph = _seed_graph()
    assert isinstance(graph, ProceduralGraph)


def test_seed_fixture_has_12_nodes():
    assert len(_seed_graph().node_ids) == 12


def test_seed_fixture_has_17_edges():
    assert len(_seed_graph().extract(None, 1)) == 17


def test_seed_fixture_end_is_only_terminal():
    graph = _seed_graph()
    all_edges = graph.extract(None, 1)
    sources_with_out_edges = {t.src for t in all_edges}
    terminals = [n for n in graph.node_ids if n not in sources_with_out_edges]
    assert terminals == ["End"]


def test_seed_fixture_start_is_only_entry():
    graph = _seed_graph()
    all_edges = graph.extract(None, 1)
    destinations = {t.dst for t in all_edges}
    entries = [n for n in graph.node_ids if n not in destinations]
    assert entries == ["Start"]


def test_seed_fixture_node_ids_match_contract_set():
    assert set(_seed_graph().node_ids) == set(CONTRACT_NODE_ORDER)


def test_seed_fixture_node_order_matches_contract():
    assert _seed_graph().node_ids == CONTRACT_NODE_ORDER


# --- round-trip -------------------------------------------------------------


def test_import_seed_then_load_preserves_all_phi_text(tmp_path):
    store = ProceduralGraphStore(tmp_path / "procedural_graphs")
    name = store.import_seed(SEED_PATH)
    loaded = store.load(name)
    original = _seed_graph()
    original_by_key = {(t.src, t.relation, t.dst): t for t in original.extract(None, 1)}
    for t in loaded.extract(None, 1):
        orig = original_by_key[(t.src, t.relation, t.dst)]
        assert (t.condition, t.guidance, t.pitfalls) == (
            orig.condition,
            orig.guidance,
            orig.pitfalls,
        )


def test_save_twice_is_byte_identical(tmp_path):
    store = ProceduralGraphStore(tmp_path / "procedural_graphs")
    graph = _seed_graph()
    path = store.save("network_layout", graph)
    first = path.read_bytes()
    store.save("network_layout", store.load("network_layout"))
    assert path.read_bytes() == first


def test_checked_in_seed_is_already_canonical():
    doc = _seed_doc()
    graph = ProceduralGraph.from_document(doc)
    canonical = json.dumps(graph.to_document("network_layout"), indent=2)
    on_disk = SEED_PATH.read_text(encoding="utf-8").rstrip("\n")
    assert on_disk == canonical


def test_checked_in_seed_is_pure_ascii():
    assert SEED_PATH.read_text(encoding="utf-8").isascii()


def test_save_rewrites_name_to_file_stem(tmp_path):
    store = ProceduralGraphStore(tmp_path / "procedural_graphs")
    store.save("network_layout", _seed_graph())
    renamed = (tmp_path / "procedural_graphs" / "network_layout.json").with_name(
        "renamed.json"
    )
    (tmp_path / "procedural_graphs" / "network_layout.json").rename(renamed)
    reloaded = store.load("renamed")
    store.save("renamed", reloaded)
    doc = json.loads(renamed.read_text(encoding="utf-8"))
    assert doc["name"] == "renamed"


def test_notes_survive_save_and_load(tmp_path):
    doc = _toy_doc(notes="hand-off note")
    graph = ProceduralGraph.from_document(doc)
    store = ProceduralGraphStore(tmp_path / "procedural_graphs")
    store.save("toy", graph)
    assert store.load("toy").notes == "hand-off note"


def test_notes_survive_apply_edit():
    graph = ProceduralGraph.from_document(_toy_doc(notes="keep me"))
    report = graph.apply_edit({})
    assert report.valid
    assert report.graph is not None
    assert report.graph.notes == "keep me"


def test_import_seed_without_force_raises_on_existing_name(tmp_path):
    store = ProceduralGraphStore(tmp_path / "procedural_graphs")
    store.import_seed(SEED_PATH)
    with pytest.raises(FileExistsError):
        store.import_seed(SEED_PATH)


def test_import_seed_with_force_overwrites(tmp_path):
    store = ProceduralGraphStore(tmp_path / "procedural_graphs")
    store.import_seed(SEED_PATH)
    store.import_seed(SEED_PATH, force=True)
    assert store.list_names() == ["network_layout"]


def test_invalid_seed_writes_nothing(tmp_path):
    storage_dir = tmp_path / "procedural_graphs"
    bad_seed = tmp_path / "bad_seed.json"
    bad_seed.write_text(json.dumps(_toy_doc(schema_version=99)), encoding="utf-8")
    store = ProceduralGraphStore(storage_dir)
    with pytest.raises(ProceduralGraphError):
        store.import_seed(bad_seed)
    assert not storage_dir.exists()


# --- locate -------------------------------------------------------------


def test_locate_hit_returns_id():
    assert _seed_graph().locate("Create_Op") == "Create_Op"


def test_locate_miss_returns_none():
    assert _seed_graph().locate("Not_A_Node") is None


def test_locate_is_case_sensitive_no_fuzzy_matching():
    assert _seed_graph().locate("create_op") is None


def test_locate_none_last_action_returns_none():
    assert _seed_graph().locate(None) is None


# --- extract --------------------------------------------------------------


def test_extract_hops_1_returns_2():
    assert len(_seed_graph().extract("Create_Op", 1)) == 2


def test_extract_hops_2_returns_5():
    assert len(_seed_graph().extract("Create_Op", 2)) == 5


def test_extract_hops_4_returns_11():
    assert len(_seed_graph().extract("Create_Op", 4)) == 11


def test_extract_saturates_at_11_for_large_hops():
    assert len(_seed_graph().extract("Create_Op", 99)) == 11


def test_extract_miss_returns_all_17_with_hop_none():
    # extract() itself only raises on an unknown start; the "miss -> full
    # graph" behavior lives in the handler layer. Exercise it directly here
    # via start=None, which is what a locate() miss maps to.
    transitions = _seed_graph().extract(None, 1)
    assert len(transitions) == 17
    assert all(t.hop is None for t in transitions)


def test_extract_no_edge_repeats_despite_cycle():
    transitions = _seed_graph().extract("Create_Op", 10)
    keys = [(t.src, t.relation, t.dst) for t in transitions]
    assert len(keys) == len(set(keys))


def test_extract_hop4_edge_is_cycle_closing_verify_layout_to_set_position():
    transitions = _seed_graph().extract("Create_Op", 4)
    hop4 = [t for t in transitions if t.hop == 4]
    assert [(t.src, t.relation, t.dst) for t in hop4] == [
        ("Verify_Layout", "LEADS_TO", "Set_Position")
    ]


def test_extract_hops_zero_raises():
    with pytest.raises(ValueError, match="hops"):
        _seed_graph().extract("Create_Op", 0)


def test_extract_unknown_start_raises():
    with pytest.raises(ValueError, match="unknown start"):
        _seed_graph().extract("Not_A_Node", 1)


def test_extract_start_none_returns_whole_graph_sorted():
    transitions = _seed_graph().extract(None, 1)
    keys = [(t.src, t.relation, t.dst) for t in transitions]
    assert keys == sorted(keys)


# --- serializer -------------------------------------------------------------


def test_serialize_hit_golden_string():
    graph = _seed_graph()
    transitions = graph.extract("Create_Op", 1)
    text = graph.serialize("network_layout", "Create_Op", "Create_Op", 1, transitions)
    lines = text.split("\n")
    assert lines[0] == (
        'Procedural graph "network_layout": 1 hop from Create_Op, 2 transitions.'
    )
    assert len(lines) == 3
    for line in lines[1:]:
        assert line.startswith("[hop 1] Create_Op -")
        assert "condition:" in line
        assert "guidance:" in line
        assert "pitfalls:" in line


def test_serialize_miss_golden_header():
    graph = _seed_graph()
    transitions = graph.extract(None, 1)
    text = graph.serialize("network_layout", "Foo", None, 2, transitions)
    header = text.split("\n", 1)[0]
    assert header == (
        'Procedural graph "network_layout": "Foo" is not a procedure node; '
        "full graph, 17 transitions."
    )
    assert not text.split("\n")[1].startswith("[hop")


def test_serialize_last_action_none_header():
    graph = _seed_graph()
    transitions = graph.extract(None, 1)
    text = graph.serialize("network_layout", None, None, 2, transitions)
    header = text.split("\n", 1)[0]
    assert header == 'Procedural graph "network_layout": full graph, 17 transitions.'


def test_serialize_singular_hop_and_transition():
    graph = _seed_graph()
    transitions = graph.extract("Update_Annotation", 1)[:1]
    text = graph.serialize(
        "network_layout", "Update_Annotation", "Update_Annotation", 1, transitions
    )
    header = text.split("\n", 1)[0]
    assert "1 hop " in header
    assert "1 transition." in header
    assert "hops" not in header
    assert "transitions." not in header.replace("1 transition.", "")


def test_serialize_no_trailing_newline():
    graph = _seed_graph()
    text = graph.serialize(
        "network_layout", "Create_Op", "Create_Op", 1, graph.extract("Create_Op", 1)
    )
    assert not text.endswith("\n")


def test_serialize_empty_field_renders_dash():
    graph = _toy_graph()
    transitions = graph.extract("B", 1)
    text = graph.serialize("toy", "B", "B", 1, transitions)
    assert "pitfalls: -" in text


# --- apply_edit: accept -----------------------------------------------------


def test_apply_edit_empty_edit_is_noop_and_valid():
    graph = _toy_graph()
    report = graph.apply_edit({})
    assert report.valid
    assert report.errors == ()
    assert report.applied == {
        "add_nodes": 0,
        "delete_nodes": 0,
        "add_edges": 0,
        "delete_edges": 0,
    }
    assert report.graph is not None
    assert report.graph.node_ids == graph.node_ids


def test_apply_edit_does_not_mutate_original():
    graph = _toy_graph()
    before = graph.node_ids
    graph.apply_edit({"delete_nodes": ["C"]})
    assert graph.node_ids == before


def test_apply_edit_phi_change_via_delete_and_add():
    graph = _toy_graph()
    edit = {
        "delete_edges": [{"src": "A", "dst": "B", "relation": "LEADS_TO"}],
        "add_edges": [_edge("A", "B", guidance="revised guidance")],
    }
    report = graph.apply_edit(edit)
    assert report.valid
    assert report.applied["delete_edges"] == 1
    assert report.applied["add_edges"] == 1
    new_edge = next(t for t in report.graph.extract(None, 1) if t.src == "A")
    assert new_edge.guidance == "revised guidance"


def test_apply_edit_delete_node_drops_incident_edges():
    graph = _seed_graph()
    before = {(t.src, t.relation, t.dst) for t in graph.extract(None, 1)}
    report = graph.apply_edit({"delete_nodes": ["Reposition_Docked"]})
    assert report.valid
    assert report.applied["delete_nodes"] == 1
    after = {(t.src, t.relation, t.dst) for t in report.graph.extract(None, 1)}
    assert "Reposition_Docked" not in report.graph.node_ids
    assert before - after == {
        ("Set_Position", "PROVIDES_INPUT_FOR", "Reposition_Docked"),
        ("Reposition_Docked", "CONVERGES_TO", "Verify_Layout"),
    }


def test_apply_edit_readded_node_moves_to_end():
    graph = _toy_graph()
    edit = {
        "delete_nodes": ["B"],
        "add_nodes": [{"id": "B"}],
        "add_edges": [_edge("A", "B"), _edge("B", "C")],
    }
    report = graph.apply_edit(edit)
    assert report.valid
    assert report.graph.node_ids == ["A", "C", "B"]


def test_apply_edit_applied_always_has_all_four_keys():
    graph = _toy_graph()
    report = graph.apply_edit({"delete_nodes": ["does-not-exist"]})
    assert set(report.applied) == {
        "add_nodes",
        "delete_nodes",
        "add_edges",
        "delete_edges",
    }


def test_apply_edit_graph_is_none_iff_invalid():
    graph = _toy_graph()
    valid_report = graph.apply_edit({})
    invalid_report = graph.apply_edit({"delete_nodes": ["does-not-exist"]})
    assert valid_report.graph is not None
    assert invalid_report.graph is None


# --- apply_edit: reject -----------------------------------------------------


def test_apply_edit_rejects_dangling_endpoint():
    graph = _toy_graph()
    report = graph.apply_edit({"add_edges": [_edge("A", "NoSuchNode")]})
    assert not report.valid
    assert any("unknown endpoint" in e for e in report.errors)


def test_apply_edit_rejects_endpoint_deleted_earlier_in_same_edit():
    graph = _toy_graph()
    edit = {"delete_nodes": ["C"], "add_edges": [_edge("B", "C")]}
    report = graph.apply_edit(edit)
    assert not report.valid
    assert any("unknown endpoint" in e for e in report.errors)


def test_apply_edit_rejects_illegal_relation():
    graph = _toy_graph()
    report = graph.apply_edit({"add_edges": [_edge("A", "C", relation="BOGUS")]})
    assert not report.valid
    assert any("unknown relation" in e for e in report.errors)


def test_apply_edit_rejects_missing_phi_key():
    graph = _toy_graph()
    edge = _edge("A", "C")
    del edge["pitfalls"]
    report = graph.apply_edit({"add_edges": [edge]})
    assert not report.valid
    assert any("invalid edge" in e for e in report.errors)


def test_apply_edit_rejects_extra_edge_key():
    graph = _toy_graph()
    edge = {**_edge("A", "C"), "extra": "oops"}
    report = graph.apply_edit({"add_edges": [edge]})
    assert not report.valid
    assert any("invalid edge" in e for e in report.errors)


def test_apply_edit_rejects_non_string_phi_value():
    graph = _toy_graph()
    report = graph.apply_edit({"add_edges": [_edge("A", "C", condition=123)]})
    assert not report.valid
    assert any("non-string field" in e for e in report.errors)


def test_apply_edit_rejects_self_loop():
    graph = _toy_graph()
    report = graph.apply_edit({"add_edges": [_edge("A", "A")]})
    assert not report.valid
    assert any("self-loop" in e for e in report.errors)


def test_apply_edit_rejects_duplicate_edge_triple():
    graph = _toy_graph()
    report = graph.apply_edit({"add_edges": [_edge("A", "B", guidance="second copy")]})
    assert not report.valid
    assert any("duplicate edge" in e for e in report.errors)


def test_apply_edit_rejects_already_present_node():
    graph = _toy_graph()
    report = graph.apply_edit({"add_nodes": [{"id": "A"}]})
    assert not report.valid
    assert any("already present" in e for e in report.errors)


def test_apply_edit_rejects_node_with_no_path_to_terminal():
    graph = _toy_graph()
    edit = {
        "add_nodes": [{"id": "D"}, {"id": "E"}],
        "add_edges": [
            _edge("D", "E", relation="LEADS_TO"),
            _edge("E", "D", relation="TRIGGERS"),
        ],
    }
    report = graph.apply_edit(edit)
    assert not report.valid
    assert any("no path to a terminal" in e for e in report.errors)


def test_apply_edit_rejects_delete_that_leaves_two_entry_nodes():
    graph = _seed_graph()
    edit = {
        "delete_edges": [{"src": "Start", "dst": "Read_Layout", "relation": "LEADS_TO"}]
    }
    report = graph.apply_edit(edit)
    assert not report.valid
    assert any("exactly one entry node" in e for e in report.errors)


def test_apply_edit_rejects_add_that_creates_second_entry_node():
    graph = _seed_graph()
    report = graph.apply_edit({"add_nodes": [{"id": "New_Entry"}]})
    assert not report.valid
    assert any("exactly one entry node" in e for e in report.errors)


def test_apply_edit_rejects_delete_absent_edge():
    graph = _toy_graph()
    report = graph.apply_edit(
        {"delete_edges": [{"src": "A", "dst": "C", "relation": "LEADS_TO"}]}
    )
    assert not report.valid
    assert any("no such edge" in e for e in report.errors)


def test_apply_edit_rejects_delete_absent_node():
    graph = _toy_graph()
    report = graph.apply_edit({"delete_nodes": ["NoSuchNode"]})
    assert not report.valid
    assert any("no such node" in e for e in report.errors)


def test_apply_edit_rejects_bad_node_id():
    graph = _toy_graph()
    report = graph.apply_edit({"add_nodes": [{"id": "1bad"}]})
    assert not report.valid
    assert any("invalid node id" in e for e in report.errors)


def test_apply_edit_rejects_non_dict_edit():
    graph = _toy_graph()
    report = graph.apply_edit(["not", "a", "dict"])
    assert not report.valid
    assert report.errors == ("edit must be an object",)


def test_apply_edit_rejects_non_list_phase_value():
    graph = _toy_graph()
    report = graph.apply_edit({"add_nodes": "oops"})
    assert not report.valid
    assert any("add_nodes must be a list" in e for e in report.errors)


def test_apply_edit_rejects_unknown_edit_key():
    graph = _toy_graph()
    report = graph.apply_edit({"modify": [{"id": "A"}]})
    assert not report.valid
    assert any("unknown key" in e and "modify" in e for e in report.errors)


def test_apply_edit_reports_all_errors_not_just_first():
    graph = _toy_graph()
    edit = {
        "delete_edges": [{"src": "Nope", "dst": "Nope2", "relation": "LEADS_TO"}],
        "add_edges": [_edge("A", "C", relation="BOGUS")],
    }
    report = graph.apply_edit(edit)
    assert not report.valid
    assert len(report.errors) == 2


def test_apply_edit_phase_failure_suppresses_structural_pass():
    graph = _toy_graph()
    edit = {
        "delete_edges": [
            {"src": "A", "dst": "B", "relation": "LEADS_TO"},
            {"src": "Nope", "dst": "Nope2", "relation": "LEADS_TO"},
        ]
    }
    report = graph.apply_edit(edit)
    assert not report.valid
    assert report.applied["delete_edges"] == 1
    assert len(report.errors) == 1
    assert "no such edge" in report.errors[0]
    assert not any("entry" in e or "terminal" in e for e in report.errors)


# --- storage path -----------------------------------------------------------


def test_store_writes_name_json(tmp_path):
    store = ProceduralGraphStore(tmp_path / "procedural_graphs")
    path = store.save("network_layout", _seed_graph())
    assert path == tmp_path / "procedural_graphs" / "network_layout.json"
    assert path.exists()


def test_store_purge_globs_do_not_match(tmp_path):
    storage_dir = tmp_path / "procedural_graphs"
    store = ProceduralGraphStore(storage_dir)
    store.save("network_layout", _seed_graph())
    for pattern in ("*_call_graph.json", "*_communities.json"):
        assert list(storage_dir.glob(pattern)) == []


@pytest.mark.parametrize("bad_name", ["../escape", "a/b", "", "x" * 65])
def test_store_path_for_rejects_path_traversal_before_touching_disk(tmp_path, bad_name):
    store = ProceduralGraphStore(tmp_path / "procedural_graphs")
    with pytest.raises(ValueError, match="invalid procedural graph name"):
        store.path_for(bad_name)
    assert not (tmp_path / "procedural_graphs").exists()
