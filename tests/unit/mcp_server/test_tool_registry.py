"""Unit tests for the low-level MCP tool registry (mcp_server/tool_registry.py)."""

import pytest

from mcp_server.tool_registry import (
    ADVANCED_TOOLS,
    TOOL_REGISTRY,
    _advanced_tools_enabled,
    build_tool_list,
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
