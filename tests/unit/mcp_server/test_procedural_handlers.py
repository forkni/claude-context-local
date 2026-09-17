"""Unit tests for mcp_server.tools.procedural_handlers (ADR-0074)."""

from pathlib import Path

import pytest

from graph.procedural_graph import ProceduralGraphStore
from mcp_server.tool_specs import ADVANCED_TOOLS, build_tool_list
from mcp_server.tools.procedural_handlers import (
    handle_edit_procedural_graph,
    handle_get_procedural_guidance,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = REPO_ROOT / "tests" / "fixtures" / "pg" / "network_layout_seed.json"


def _seed_store(base_dir: Path) -> str:
    """Import the checked-in seed fixture under ``base_dir/procedural_graphs``
    and return its stored name.
    """
    store = ProceduralGraphStore(base_dir / "procedural_graphs")
    return store.import_seed(SEED_PATH)


@pytest.fixture
def base_dir(tmp_path, monkeypatch):
    """Isolate each test's procedural-graph storage under its own tmp_path,
    patching the binding site in procedural_handlers (not the origin module)
    -- that is what the handler actually calls.
    """
    monkeypatch.setattr(
        "mcp_server.tools.procedural_handlers.get_storage_dir", lambda: tmp_path
    )
    return tmp_path


class TestGetProceduralGuidance:
    async def test_hops_zero_clamps_to_one(self, base_dir):
        name = _seed_store(base_dir)
        result = await handle_get_procedural_guidance(
            {"graph": name, "last_action": "Create_Op", "hops": 0}
        )
        assert result["hops"] == 1

    async def test_hops_99_clamps_to_four(self, base_dir):
        name = _seed_store(base_dir)
        result = await handle_get_procedural_guidance(
            {"graph": name, "last_action": "Create_Op", "hops": 99}
        )
        assert result["hops"] == 4

    async def test_omitted_hops_defaults_to_two(self, base_dir):
        name = _seed_store(base_dir)
        result = await handle_get_procedural_guidance(
            {"graph": name, "last_action": "Create_Op"}
        )
        assert result["hops"] == 2

    async def test_miss_returns_located_false_and_full_graph(self, base_dir):
        name = _seed_store(base_dir)
        result = await handle_get_procedural_guidance(
            {"graph": name, "last_action": "Not_A_Node", "hops": 1}
        )
        assert result["located"] is False
        assert result["edge_count"] == 17

    async def test_hit_returns_located_true(self, base_dir):
        name = _seed_store(base_dir)
        result = await handle_get_procedural_guidance(
            {"graph": name, "last_action": "Create_Op", "hops": 1}
        )
        assert result["located"] is True
        assert result["edge_count"] == 2
        assert "condition:" in result["guidance"]
        assert "guidance:" in result["guidance"]
        assert "pitfalls:" in result["guidance"]

    async def test_bad_graph_name_rejected_without_creating_directory(self, base_dir):
        result = await handle_get_procedural_guidance(
            {"graph": "../escape", "last_action": "Create_Op"}
        )
        assert "error" in result
        assert not (base_dir / "procedural_graphs").exists()

    async def test_unknown_graph_name_returns_available(self, base_dir):
        name = _seed_store(base_dir)
        result = await handle_get_procedural_guidance(
            {"graph": "no_such_graph", "last_action": "Create_Op"}
        )
        assert "error" in result
        assert result["available"] == [name]


class TestEditProceduralGraph:
    async def test_dry_run_defaults_true_and_never_writes(self, base_dir):
        name = _seed_store(base_dir)
        path = ProceduralGraphStore(base_dir / "procedural_graphs").path_for(name)
        before = path.read_bytes()

        result = await handle_edit_procedural_graph(
            {
                "graph": name,
                "edit": {
                    "add_nodes": [{"id": "NewNode"}],
                    "add_edges": [
                        {
                            "src": "End",
                            "dst": "NewNode",
                            "relation": "LEADS_TO",
                            "condition": "always",
                            "guidance": "",
                            "pitfalls": "",
                        }
                    ],
                },
            }
        )

        assert result["dry_run"] is True
        assert result["valid"] is True
        assert result["committed"] is False
        assert path.read_bytes() == before

    async def test_invalid_edit_with_dry_run_false_still_never_writes(self, base_dir):
        name = _seed_store(base_dir)
        path = ProceduralGraphStore(base_dir / "procedural_graphs").path_for(name)
        before = path.read_bytes()

        result = await handle_edit_procedural_graph(
            {
                "graph": name,
                "edit": {"delete_nodes": ["Does_Not_Exist"]},
                "dry_run": False,
            }
        )

        assert result["valid"] is False
        assert result["committed"] is False
        assert result["errors"]
        assert path.read_bytes() == before

    async def test_committed_edit_is_reflected_by_next_guidance_call(self, base_dir):
        name = _seed_store(base_dir)

        edit_result = await handle_edit_procedural_graph(
            {
                "graph": name,
                "edit": {"delete_nodes": ["Reposition_Docked"]},
                "dry_run": False,
            }
        )
        assert edit_result["valid"] is True
        assert edit_result["committed"] is True
        assert edit_result["node_count"] == 11

        guidance_result = await handle_get_procedural_guidance(
            {"graph": name, "last_action": "Create_Op", "hops": 4}
        )
        assert guidance_result["node_count"] == 11

    async def test_unknown_graph_name_returns_available(self, base_dir):
        name = _seed_store(base_dir)
        result = await handle_edit_procedural_graph(
            {"graph": "no_such_graph", "edit": {}}
        )
        assert "error" in result
        assert result["available"] == [name]


class TestAdvancedToolGating:
    def test_both_tools_are_advanced(self):
        assert "get_procedural_guidance" in ADVANCED_TOOLS
        assert "edit_procedural_graph" in ADVANCED_TOOLS

    def test_absent_by_default(self):
        names = {t.name for t in build_tool_list(include_advanced=False)}
        assert "get_procedural_guidance" not in names
        assert "edit_procedural_graph" not in names

    def test_present_with_include_advanced(self):
        names = {t.name for t in build_tool_list(include_advanced=True)}
        assert "get_procedural_guidance" in names
        assert "edit_procedural_graph" in names
