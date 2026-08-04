"""Unit tests for the low-level MCP tool registry (mcp_server/tool_registry.py)."""

import dataclasses

import pytest

from mcp_server.tool_registry import (
    ADVANCED_TOOLS,
    TOOL_REGISTRY,
    _advanced_tools_enabled,
    build_tool_list,
)
from mcp_server.tools.config_handlers import (
    _CHUNKING_FIELDS,
    _PERFORMANCE_SEARCH_FIELDS,
    _RERANKER_FIELDS,
    _SEARCH_MODE_FIELDS,
)
from search.config import (
    ChunkingConfig,
    PerformanceConfig,
    RerankerConfig,
    SearchModeConfig,
)


@pytest.fixture(autouse=True)
def _clear_expose_advanced_env(monkeypatch):
    """Ensure no ambient MCP_EXPOSE_ADVANCED_TOOLS leaks between tests."""
    monkeypatch.delenv("MCP_EXPOSE_ADVANCED_TOOLS", raising=False)


class TestAdvancedToolsEnabled:
    def test_unset_defaults_to_false(self):
        assert _advanced_tools_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "True", "TRUE", "yes", "YES"])
    def test_truthy_values_enable(self, monkeypatch, value):
        monkeypatch.setenv("MCP_EXPOSE_ADVANCED_TOOLS", value)
        assert _advanced_tools_enabled() is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "", "garbage"])
    def test_other_values_stay_disabled(self, monkeypatch, value):
        monkeypatch.setenv("MCP_EXPOSE_ADVANCED_TOOLS", value)
        assert _advanced_tools_enabled() is False


class TestBuildToolList:
    def test_default_excludes_advanced_tools(self, monkeypatch):
        monkeypatch.delenv("MCP_EXPOSE_ADVANCED_TOOLS", raising=False)

        tools = build_tool_list()

        names = {tool.name for tool in tools}
        assert names.isdisjoint(ADVANCED_TOOLS)
        assert len(tools) == len(TOOL_REGISTRY) - len(ADVANCED_TOOLS)

    def test_env_var_enables_advanced_tools(self, monkeypatch):
        monkeypatch.setenv("MCP_EXPOSE_ADVANCED_TOOLS", "1")

        tools = build_tool_list()

        names = {tool.name for tool in tools}
        assert ADVANCED_TOOLS.issubset(names)
        assert len(tools) == len(TOOL_REGISTRY)

    def test_explicit_true_overrides_unset_env_var(self, monkeypatch):
        monkeypatch.delenv("MCP_EXPOSE_ADVANCED_TOOLS", raising=False)

        tools = build_tool_list(include_advanced=True)

        names = {tool.name for tool in tools}
        assert ADVANCED_TOOLS.issubset(names)

    def test_explicit_false_overrides_enabled_env_var(self, monkeypatch):
        monkeypatch.setenv("MCP_EXPOSE_ADVANCED_TOOLS", "1")

        tools = build_tool_list(include_advanced=False)

        names = {tool.name for tool in tools}
        assert names.isdisjoint(ADVANCED_TOOLS)

    def test_each_tool_has_name_description_and_schema(self):
        tools = build_tool_list(include_advanced=True)

        assert len(tools) == len(TOOL_REGISTRY)
        for tool in tools:
            assert tool.name in TOOL_REGISTRY
            assert tool.description == TOOL_REGISTRY[tool.name]["description"]
            assert tool.input_schema == TOOL_REGISTRY[tool.name]["input_schema"]


def _field_metadata(section_cls, field_name):
    for f in dataclasses.fields(section_cls):
        if f.name == field_name:
            return f.metadata
    raise KeyError(f"{section_cls.__name__} has no field {field_name!r}")


class TestConfigToolSchemaMatchesFieldSpec:
    """A configure_* tool's hand-typed input_schema min/max/enum is a second,
    independent representation of the same bound already declared on the
    field's ``spec(range=...)``/``spec(choices=...)`` metadata (ADR-0022).
    Nothing enforced agreement between the two until this test.
    """

    @pytest.mark.parametrize(
        "tool_name,section_cls,field_map",
        [
            ("configure_chunking", ChunkingConfig, _CHUNKING_FIELDS),
            ("configure_reranking", RerankerConfig, _RERANKER_FIELDS),
            ("configure_search_mode", SearchModeConfig, _SEARCH_MODE_FIELDS),
            ("configure_search_mode", PerformanceConfig, _PERFORMANCE_SEARCH_FIELDS),
        ],
    )
    def test_numeric_and_choice_bounds_match(self, tool_name, section_cls, field_map):
        properties = TOOL_REGISTRY[tool_name]["input_schema"]["properties"]
        for arg_key, attr in field_map:
            schema_prop = properties[arg_key]
            metadata = _field_metadata(section_cls, attr)

            # Bidirectional: a schema bound with no spec range (or vice versa)
            # is itself a divergence, not just a mismatched pair of bounds.
            schema_bound = (schema_prop.get("minimum"), schema_prop.get("maximum"))
            expected_bound = metadata.get("range", (None, None))
            assert schema_bound == expected_bound, (
                f"{tool_name}.{arg_key} schema bound {schema_bound} diverges from "
                f"{section_cls.__name__}.{attr}'s spec(range={metadata.get('range')})"
            )

            schema_enum = schema_prop.get("enum")
            expected_enum = list(metadata["choices"]) if "choices" in metadata else None
            assert schema_enum == expected_enum, (
                f"{tool_name}.{arg_key} schema enum {schema_enum} diverges from "
                f"{section_cls.__name__}.{attr}'s spec(choices={metadata.get('choices')})"
            )
