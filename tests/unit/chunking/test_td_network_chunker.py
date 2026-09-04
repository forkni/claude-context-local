"""Tests for TDNetworkChunker (ADR-0062, Part C, C5).

Exercises the chunker directly against the hand-built fixture
``tests/fixtures/td_network/Test_network.tdgraph.json`` -- see the ADR and
``docs/adr/0062-td-network-indexing.md`` for the schema this fixture stands in for
(shape cross-checked against a real Part B export, ``D:\\dev\\SDTD_040``,
2026-09-04). The fixture covers every one of the 11 edge types once, plus the
``dock``/``replicator`` direction-inversion cases documented in
``_build_relationship_edges``, and -- like every real export -- carries the
target COMP itself as a depth-0 node (the "root"), which must never become an
operator chunk.
"""

from pathlib import Path

import pytest

from chunking.python_ast_chunker import CodeChunk
from chunking.relationships.relationship_types import RelationshipType
from chunking.td_network_chunker import TDNetworkChunker
from search.chunk_id import ChunkId, dedup_key, is_chunk_id


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "td_network"
FIXTURE_PATH = FIXTURE_DIR / "Test_network.tdgraph.json"


def _chunk_fixture() -> list[CodeChunk]:
    chunker = TDNetworkChunker(root_path=str(FIXTURE_DIR))
    return chunker.chunk_file(str(FIXTURE_PATH), "Test_network.tdgraph.json")


def _by_name(chunks: list[CodeChunk], name: str) -> CodeChunk:
    return next(c for c in chunks if c.name == name)


def _rel(chunk: CodeChunk, rtype: RelationshipType, target_suffix: str):
    """First relationship of `rtype` on `chunk` whose target_name ends with
    `target_suffix` (chunk_id components), or None."""
    for r in chunk.relationships or []:
        if r.relationship_type == rtype and r.target_name.endswith(target_suffix):
            return r
    return None


def _fixture_lines() -> list[str]:
    return FIXTURE_PATH.read_text(encoding="utf-8").splitlines()


def _node_json_span(node_id: str) -> tuple[int, int]:
    """1-based inclusive line range of the node object with `node_id` in the
    fixture, derived from the file text itself (exporter writes indent=2 with
    ``id`` as the first key, so the object opens on the line before ``"id"`` and
    closes at the next 4-space-indented ``}``)."""
    lines = _fixture_lines()
    id_line = next(
        i for i, ln in enumerate(lines) if ln.strip() == f'"id": "{node_id}",'
    )
    start = id_line  # 0-based index of the "{" line == 1-based line of "id" - 1
    end = next(i for i in range(id_line, len(lines)) if lines[i].rstrip(",") == "    }")
    return start, end + 1


def _class_json_span(cname: str) -> tuple[int, int]:
    """1-based inclusive line range of the ``classes[cname]`` entry."""
    lines = _fixture_lines()
    start = next(
        i for i, ln in enumerate(lines) if ln.strip().startswith(f'"{cname}": {{')
    )
    if lines[start].rstrip(",").endswith("}"):
        return start + 1, start + 1
    end = next(i for i in range(start, len(lines)) if lines[i].rstrip(",") == "    }")
    return start + 1, end + 1


class TestChunkFileErrors:
    def test_missing_file_returns_empty_list(self):
        chunker = TDNetworkChunker(root_path=str(FIXTURE_DIR))
        assert (
            chunker.chunk_file(str(FIXTURE_DIR / "does_not_exist.tdgraph.json")) == []
        )

    def test_malformed_json_returns_empty_list(self, tmp_path):
        bad = tmp_path / "bad.tdgraph.json"
        bad.write_text("{not valid json", encoding="utf-8")
        chunker = TDNetworkChunker(root_path=str(tmp_path))
        assert chunker.chunk_file(str(bad)) == []

    def test_relative_path_computed_from_root_path_when_omitted(self):
        chunker = TDNetworkChunker(root_path=str(FIXTURE_DIR))
        chunks = chunker.chunk_file(str(FIXTURE_PATH))
        assert chunks
        assert chunks[0].relative_path == "Test_network.tdgraph.json"


class TestChunkCounts:
    def test_produces_operator_class_and_network_chunks(self):
        chunks = _chunk_fixture()
        by_type: dict[str, int] = {}
        for c in chunks:
            by_type[c.chunk_type] = by_type.get(c.chunk_type, 0) + 1
        # 15 nodes = 1 root (folded into the network chunk) + 13 real operators
        # + 1 stub; 8 classes table entries; 1 network summary.
        assert by_type == {"operator": 13, "class": 8, "network": 1}

    def test_network_root_gets_no_operator_chunk(self):
        """The exporter emits the target COMP as a depth-0 node. Before the fix it
        produced ``<file>:0-0:operator`` -- an id with no name segment."""
        chunks = _chunk_fixture()
        operators = [c for c in chunks if c.chunk_type == "operator"]
        assert all(c.name not in ("", "Test_network") for c in operators)
        assert all(":operator:" in c.chunk_id for c in operators)
        assert all(ChunkId.parse(c.chunk_id).name for c in operators)

    def test_network_chunk_carries_root_operator_identity(self):
        chunks = _chunk_fixture()
        network = next(c for c in chunks if c.chunk_type == "network")
        assert "root operator: containerCOMP (COMP)" in network.content
        assert "class containerCOMP < PanelCOMP < COMP < OP" in network.content
        assert "params: w=1280, h=720" in network.content

    def test_stub_node_gets_no_operator_chunk(self):
        chunks = _chunk_fixture()
        names = {c.name for c in chunks if c.chunk_type == "operator"}
        assert "external/mix1" not in names
        assert "mix1" not in names

    def test_all_chunks_are_td_network_language(self):
        chunks = _chunk_fixture()
        assert all(c.language == "td_network" for c in chunks)


class TestChunkIdContract:
    def test_every_chunk_id_is_well_formed_and_unique(self):
        chunks = _chunk_fixture()
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))
        for cid in ids:
            assert is_chunk_id(cid)
            parsed = ChunkId.parse(cid)
            assert parsed is not None
            # build() silently drops a falsy name -- every TD chunk must have one.
            assert parsed.name, cid

    def test_dedup_keys_are_unique(self):
        chunks = _chunk_fixture()
        keys = [dedup_key(c.chunk_id) for c in chunks]
        assert len(keys) == len(set(keys))

    def test_operator_chunk_id_carries_op_path_and_kind(self):
        chunks = _chunk_fixture()
        glsl1 = _by_name(chunks, "glsl1")
        parsed = ChunkId.parse(glsl1.chunk_id)
        assert parsed.kind == "operator"
        assert parsed.name == "glsl1"

    def test_nested_operator_uses_path_relative_to_target(self):
        chunks = _chunk_fixture()
        box1 = _by_name(chunks, "comp1/box1")
        parsed = ChunkId.parse(box1.chunk_id)
        assert parsed.name == "comp1/box1"

    @pytest.mark.parametrize("name", ["glsl1", "comp1/box1", "info1", "rep1/item1"])
    def test_operator_span_is_the_node_object_position_in_the_file(self, name):
        """Spans point into the .tdgraph.json itself so a Read of the span shows
        exactly that node's JSON. Expected values are derived from the fixture
        text, never hard-coded."""
        chunks = _chunk_fixture()
        chunk = _by_name(chunks, name)
        expected = _node_json_span(f"/project1/Test_network/{name}")
        assert (chunk.start_line, chunk.end_line) == expected
        assert chunk.start_line >= 1 and chunk.end_line > chunk.start_line
        parsed = ChunkId.parse(chunk.chunk_id)
        assert (parsed.line_start, parsed.line_end) == expected

    def test_exporter_node_line_spans_are_ignored(self):
        """The exporter's ``node_line_spans`` is the *script line count* of each
        Python DAT ({start_line: 1, end_line: N}), not a position in the snapshot.
        The fixture gives info1 {1, 12}; the chunk must not carry that."""
        chunks = _chunk_fixture()
        info1 = _by_name(chunks, "info1")
        assert (info1.start_line, info1.end_line) != (1, 12)
        assert (info1.start_line, info1.end_line) == _node_json_span(
            "/project1/Test_network/info1"
        )

    def test_no_chunk_has_a_zero_span(self):
        chunks = _chunk_fixture()
        assert all((c.start_line, c.end_line) != (0, 0) for c in chunks)

    @pytest.mark.parametrize("cname", ["glslTOP", "constantCHOP", "boxSOP"])
    def test_class_span_is_the_classes_entry_position(self, cname):
        chunks = _chunk_fixture()
        cls = next(c for c in chunks if c.chunk_type == "class" and c.name == cname)
        assert (cls.start_line, cls.end_line) == _class_json_span(cname)

    def test_network_span_covers_the_whole_file(self):
        chunks = _chunk_fixture()
        network = next(c for c in chunks if c.chunk_type == "network")
        assert (network.start_line, network.end_line) == (1, len(_fixture_lines()))

    def test_spans_are_formatting_independent(self, tmp_path):
        """A minified export still yields well-formed, non-zero spans (every
        element collapses onto line 1)."""
        import json

        minified = tmp_path / "Mini.tdgraph.json"
        minified.write_text(
            json.dumps(json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))),
            encoding="utf-8",
        )
        chunks = TDNetworkChunker(root_path=str(tmp_path)).chunk_file(str(minified))
        assert len(chunks) == 22
        assert all((c.start_line, c.end_line) == (1, 1) for c in chunks)
        assert all(is_chunk_id(c.chunk_id) for c in chunks)


class TestEdgeTypeMapping:
    """One assertion per .tdgraph.json edge type, cross-checked against the
    fixture's literal edge list (see the module docstring)."""

    def test_wire_edge_maps_to_wires_to_with_metadata(self):
        chunks = _chunk_fixture()
        grid1 = _by_name(chunks, "comp1/grid1")
        edge = _rel(grid1, RelationshipType.WIRES_TO, ":operator:comp1/box1")
        assert edge is not None
        assert edge.metadata["td_edge_type"] == "wire"
        assert edge.metadata["dst_index"] == 0
        assert edge.metadata["carries"] == "gridSOP()"

    def test_comp_wire_edge_maps_to_wires_to(self):
        chunks = _chunk_fixture()
        ctrl1 = _by_name(chunks, "ctrl1")
        edge = _rel(ctrl1, RelationshipType.WIRES_TO, ":operator:comp1")
        assert edge is not None
        assert edge.metadata["td_edge_type"] == "comp_wire"

    def test_dock_edge_direction_is_reversed_relative_to_json(self):
        """fixture: {type: dock, src: glsl1, dst: info1} but info1.rel.docked_to
        == glsl1 -- the RelationshipEdge must read "info1 docked_to glsl1", i.e.
        source=chunk(dst), target=chunk(src). See _build_relationship_edges."""
        chunks = _chunk_fixture()
        info1 = _by_name(chunks, "info1")
        glsl1 = _by_name(chunks, "glsl1")

        docked = _rel(info1, RelationshipType.DOCKED_TO, ":operator:glsl1")
        assert docked is not None

        # And glsl1 (the host) must NOT carry an outbound DOCKED_TO to info1 --
        # that direction belongs to info1 only.
        assert _rel(glsl1, RelationshipType.DOCKED_TO, ":operator:info1") is None

    def test_dock_host_lists_docked_child_in_content(self):
        chunks = _chunk_fixture()
        glsl1 = _by_name(chunks, "glsl1")
        assert "hosts docked: info1" in glsl1.content

    def test_docked_operator_lists_host_in_content(self):
        chunks = _chunk_fixture()
        info1 = _by_name(chunks, "info1")
        assert "docked to: glsl1" in info1.content

    def test_contains_edge_from_network_root_attaches_to_network_chunk(self):
        chunks = _chunk_fixture()
        network = next(c for c in chunks if c.chunk_type == "network")
        edge = _rel(network, RelationshipType.CONTAINS, ":operator:glsl1")
        assert edge is not None

    def test_dock_edge_hosted_by_network_root_targets_network_chunk(self):
        """fixture: {type: dock, src: <root>, dst: ctrl1}. The root has no
        operator chunk, so ctrl1 must read "docked_to <network chunk>", not a
        phantom ``:0-0:operator`` id with an empty name."""
        chunks = _chunk_fixture()
        network = next(c for c in chunks if c.chunk_type == "network")
        ctrl1 = _by_name(chunks, "ctrl1")
        edge = _rel(ctrl1, RelationshipType.DOCKED_TO, ":network:Test_network")
        assert edge is not None
        assert edge.target_name == network.chunk_id
        assert "docked to: Test_network" in ctrl1.content

    def test_shared_tag_edge_from_network_root_uses_network_chunk_both_ways(self):
        chunks = _chunk_fixture()
        network = next(c for c in chunks if c.chunk_type == "network")
        comp1 = _by_name(chunks, "comp1")
        out = _rel(network, RelationshipType.SHARES_TAG, ":operator:comp1")
        back = _rel(comp1, RelationshipType.SHARES_TAG, ":network:Test_network")
        assert out is not None and out.metadata["tag"] == "ui"
        assert back is not None and back.target_name == network.chunk_id

    def test_no_edge_endpoint_is_a_nameless_operator_id(self):
        chunks = _chunk_fixture()
        for c in chunks:
            for r in c.relationships or []:
                assert not r.target_name.endswith(":operator"), r.target_name
                assert not r.source_id.endswith(":operator"), r.source_id

    def test_contains_edge_nested_attaches_to_parent_operator_chunk(self):
        chunks = _chunk_fixture()
        comp1 = _by_name(chunks, "comp1")
        edge = _rel(comp1, RelationshipType.CONTAINS, ":operator:comp1/box1")
        assert edge is not None

    def test_par_ref_edge_maps_to_references_op(self):
        chunks = _chunk_fixture()
        glsl1 = _by_name(chunks, "glsl1")
        edge = _rel(glsl1, RelationshipType.REFERENCES_OP, ":operator:glslpixel1")
        assert edge is not None
        assert edge.metadata["td_edge_type"] == "par_ref"
        assert edge.metadata["par"] == "pixeldat"

    def test_bind_edge_maps_to_binds_to(self):
        chunks = _chunk_fixture()
        slave1 = _by_name(chunks, "slave1")
        edge = _rel(slave1, RelationshipType.BINDS_TO, ":operator:master1")
        assert edge is not None
        assert edge.metadata["par"] == "value1"

    def test_export_edge_maps_to_exports_to_with_phantom_target(self):
        chunks = _chunk_fixture()
        exportsrc1 = _by_name(chunks, "exportsrc1")
        edge = _rel(exportsrc1, RelationshipType.EXPORTS_TO, "project1/external/mix1")
        assert edge is not None
        assert edge.metadata["par"] == "value1"

    def test_script_ref_resolved_edge_maps_to_references_op(self):
        chunks = _chunk_fixture()
        info1 = _by_name(chunks, "info1")
        edge = _rel(info1, RelationshipType.REFERENCES_OP, ":operator:noise1")
        assert edge is not None
        assert edge.metadata["td_edge_type"] == "script_ref"
        assert edge.metadata["via"] == "op('../noise1')"

    def test_script_ref_unresolved_edges_are_dropped_and_counted(self):
        chunks = _chunk_fixture()
        network = next(c for c in chunks if c.chunk_type == "network")
        # 3 of the fixture's 4 info1 script_ref rows have dst: null.
        assert "3 unresolved script reference(s)" in network.content

    def test_shortcut_ref_edges_map_to_references_op(self):
        chunks = _chunk_fixture()
        info1 = _by_name(chunks, "info1")
        ctrl_edge = _rel(info1, RelationshipType.REFERENCES_OP, ":operator:ctrl1")
        glsl_edge = _rel(info1, RelationshipType.REFERENCES_OP, ":operator:glsl1")
        assert ctrl_edge is not None and ctrl_edge.metadata["shortcut"] == "Ctrl"
        assert glsl_edge is not None and glsl_edge.metadata["shortcut"] == "GLSL1"

    def test_replicator_edge_maps_to_instantiates(self):
        chunks = _chunk_fixture()
        rep1 = _by_name(chunks, "rep1")
        edge = _rel(rep1, RelationshipType.INSTANTIATES, ":operator:rep1/item1")
        assert edge is not None
        assert edge.metadata["td_edge_type"] == "replicator"

    def test_shared_tag_edge_emitted_in_both_directions(self):
        chunks = _chunk_fixture()
        master1 = _by_name(chunks, "master1")
        slave1 = _by_name(chunks, "slave1")
        exportsrc1 = _by_name(chunks, "exportsrc1")

        # exportsrc1 <-> master1 and exportsrc1 <-> slave1 both share "audio".
        assert (
            _rel(master1, RelationshipType.SHARES_TAG, ":operator:exportsrc1")
            is not None
        )
        assert (
            _rel(exportsrc1, RelationshipType.SHARES_TAG, ":operator:master1")
            is not None
        )
        assert (
            _rel(slave1, RelationshipType.SHARES_TAG, ":operator:exportsrc1")
            is not None
        )
        assert (
            _rel(exportsrc1, RelationshipType.SHARES_TAG, ":operator:slave1")
            is not None
        )


class TestClassHierarchy:
    def test_class_inherits_from_second_mro_entry(self):
        chunks = _chunk_fixture()
        glsl_top = next(
            c for c in chunks if c.chunk_type == "class" and c.name == "glslTOP"
        )
        edge = _rel(glsl_top, RelationshipType.INHERITS, ":class:TOP")
        assert edge is not None

    def test_inherits_target_is_phantom_safe_for_abstract_base(self):
        """TOP is never a concrete class_name on any node, so no real class
        chunk exists for it -- the edge's target_name must still be a
        well-formed chunk_id (graph_storage creates a phantom node for it)."""
        chunks = _chunk_fixture()
        real_class_names = {c.name for c in chunks if c.chunk_type == "class"}
        assert "TOP" not in real_class_names

        glsl_top = next(
            c for c in chunks if c.chunk_type == "class" and c.name == "glslTOP"
        )
        edge = _rel(glsl_top, RelationshipType.INHERITS, ":class:TOP")
        assert is_chunk_id(edge.target_name)

    def test_network_root_instantiates_its_class_from_the_network_chunk(self):
        chunks = _chunk_fixture()
        network = next(c for c in chunks if c.chunk_type == "network")
        edge = _rel(network, RelationshipType.INSTANTIATES, ":class:containerCOMP")
        assert edge is not None

    def test_class_instances_never_list_the_root_as_empty_name(self):
        chunks = _chunk_fixture()
        container = next(
            c for c in chunks if c.chunk_type == "class" and c.name == "containerCOMP"
        )
        assert "instances: comp1" in container.content

    def test_operator_instantiates_its_class(self):
        chunks = _chunk_fixture()
        glsl1 = _by_name(chunks, "glsl1")
        edge = _rel(glsl1, RelationshipType.INSTANTIATES, ":class:glslTOP")
        assert edge is not None
        assert edge.metadata["td_edge_type"] == "instance_of"


class TestChunkContent:
    def test_operator_content_mentions_family_and_op_type(self):
        chunks = _chunk_fixture()
        glsl1 = _by_name(chunks, "glsl1")
        assert "glslTOP" in glsl1.content
        assert "TOP" in glsl1.content

    def test_operator_tags_do_not_hardcode_stale_plan_literals(self):
        """ADR-0062 deviation: no `bypassed`/flags field exists in the real
        schema, so tags are [family.lower(), op_type, *user_tags] -- not the
        stale plan literal ["comp", "bypassed"] baked into every operator."""
        chunks = _chunk_fixture()
        noise1 = _by_name(chunks, "noise1")
        assert "bypassed" not in noise1.tags
        assert "top" in noise1.tags
        assert "source" in noise1.tags

    def test_network_chunk_lists_top_level_operators(self):
        chunks = _chunk_fixture()
        network = next(c for c in chunks if c.chunk_type == "network")
        assert "glsl1" in network.content
        assert "comp1/box1" not in network.content  # nested, not top-level


class TestConfigGate:
    def test_disabled_by_default_via_multi_language_chunker(self, monkeypatch):
        import search.config as sc
        from chunking.multi_language_chunker import MultiLanguageChunker

        # Pin the *dataclass default*, not the developer's live search_config.json
        # (which may already have the gate flipped on).
        monkeypatch.setattr(sc, "get_chunking_config", lambda: sc.ChunkingConfig())

        mc = MultiLanguageChunker(root_path=str(FIXTURE_DIR))
        assert mc.is_supported(str(FIXTURE_PATH)) is False
        assert mc.chunk_file(str(FIXTURE_PATH)) == []

    def test_enabled_dispatches_to_td_network_chunker(self, monkeypatch):
        import search.config as sc
        from chunking.multi_language_chunker import MultiLanguageChunker

        cfg = sc.ChunkingConfig(enable_td_network_indexing=True)
        monkeypatch.setattr(sc, "get_chunking_config", lambda: cfg)

        mc = MultiLanguageChunker(root_path=str(FIXTURE_DIR))
        assert mc.is_supported(str(FIXTURE_PATH)) is True
        chunks = mc.chunk_file(str(FIXTURE_PATH))
        assert len(chunks) == 22
        assert {c.language for c in chunks} == {"td_network"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
