"""Unit tests for the low-level MCP tool specs (mcp_server/tool_specs.py)."""

import dataclasses

import pytest

from mcp_server.config_schema import (
    CONFIG_BACKED,
    HAND_TYPED,
    NO_DEFAULT,
    OUTPUT_FORMAT_PROPERTY,
)
from mcp_server.tool_specs import (
    ADVANCED_TOOLS,
    TOOL_SPECS,
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


TOOL_SPECS_BY_NAME = {s.name: s for s in TOOL_SPECS}


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
        assert len(tools) == len(TOOL_SPECS) - len(ADVANCED_TOOLS)

    def test_env_var_enables_advanced_tools(self, monkeypatch):
        monkeypatch.setenv("MCP_EXPOSE_ADVANCED_TOOLS", "1")

        tools = build_tool_list()

        names = {tool.name for tool in tools}
        assert ADVANCED_TOOLS.issubset(names)
        assert len(tools) == len(TOOL_SPECS)

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

        assert len(tools) == len(TOOL_SPECS)
        for tool in tools:
            assert tool.name in TOOL_SPECS_BY_NAME
            spec = TOOL_SPECS_BY_NAME[tool.name]
            assert tool.description == spec.description
            assert tool.input_schema == spec.input_schema


class TestEgoGraphEnabledSchema:
    """ego_graph_enabled must describe a genuine two-way gate: the stale text
    ("one-way switch, not a gate") predates build_effective_config's tri-state
    fix and would actively mislead a caller if it survived the fix.
    """

    def _schema(self):
        return TOOL_SPECS_BY_NAME["search_code"].input_schema["properties"][
            "ego_graph_enabled"
        ]

    def test_description_no_longer_claims_one_way_switch(self):
        description = self._schema()["description"]
        assert "one-way switch" not in description
        assert "not a gate" not in description

    def test_description_documents_omission_as_the_defer_to_server_default_path(self):
        description = self._schema()["description"]
        assert "omit" in description.lower()
        assert "get_search_config_status" in description

    def test_no_forced_schema_default(self):
        """A JSON-schema 'default' here would misrepresent the field as binary;
        omission must be distinguishable from an explicit False.
        """
        assert "default" not in self._schema()


class TestIndexDirectoryFilterSchema:
    """include_dirs, exclude_dirs, and include_exclusive all share the same
    "omit to reuse the stored project value" semantics (index_handlers.py's
    tri-state resolution against project_info.json) — none of the three may
    publish a JSON-schema "default", or a conformant client materializing
    schema defaults would send an explicit value on every call, indistinguishable
    from the omitted case and forcing a filters-changed full reindex. This is
    the regression guard for include_exclusive's former "default": False.

    project_name is dead (no handler ever reads it) and must not be advertised.
    """

    def _properties(self):
        return TOOL_SPECS_BY_NAME["index_directory"].input_schema["properties"]

    @pytest.mark.parametrize(
        "arg_key", ["include_dirs", "exclude_dirs", "include_exclusive"]
    )
    def test_no_forced_schema_default(self, arg_key):
        assert "default" not in self._properties()[arg_key]

    def test_project_name_not_advertised(self):
        assert "project_name" not in self._properties()


class TestIncludeSignaturesSchema:
    """include_signatures must default off and document its non-Python bound
    (degrades to a raw-line excerpt, not a per-language signature guarantee).
    """

    def _schema(self):
        return TOOL_SPECS_BY_NAME["search_code"].input_schema["properties"][
            "include_signatures"
        ]

    def test_default_false(self):
        assert self._schema()["default"] is False

    def test_description_documents_non_python_bound(self):
        description = self._schema()["description"].lower()
        assert "non-python" in description


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

    Widened (C4) from a 4-tool parity check into a whole-registry hygiene
    ratchet: every property across all 18 tools that carries minimum/maximum/
    enum/default must be accounted for in mcp_server/config_schema.py, either
    as CONFIG_BACKED (derived from spec(), never carries a default) or
    HAND_TYPED (documented rationale for why no config field backs it). The
    original 4-tool parametrized check stays alongside it — it verifies a
    different seam (config_handlers.py's apply-path field maps agree with the
    schema), which the registry-wide ratchet does not cover.
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
        properties = TOOL_SPECS_BY_NAME[tool_name].input_schema["properties"]
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

    @staticmethod
    def _iter_spec_properties():
        for spec in TOOL_SPECS:
            for arg_key, prop in spec.input_schema["properties"].items():
                yield spec.name, arg_key, prop

    @staticmethod
    def _classification_key(tool_name, arg_key):
        """The CONFIG_BACKED/HAND_TYPED key that classifies this property, or
        None if neither a direct "<tool>.<arg>" nor a "*.<arg>" wildcard entry
        exists.
        """
        direct = f"{tool_name}.{arg_key}"
        if direct in CONFIG_BACKED or direct in HAND_TYPED:
            return direct
        wildcard = f"*.{arg_key}"
        if wildcard in CONFIG_BACKED:
            return wildcard
        return None

    def test_every_bound_carrying_property_is_classified(self):
        bound_keys = ("minimum", "maximum", "enum", "default")
        unclassified = [
            f"{tool_name}.{arg_key}"
            for tool_name, arg_key, prop in self._iter_spec_properties()
            if any(k in prop for k in bound_keys)
            and self._classification_key(tool_name, arg_key) is None
        ]
        assert not unclassified, (
            "Propert(y/ies) carrying minimum/maximum/enum/default but missing "
            "from both CONFIG_BACKED and HAND_TYPED in "
            "mcp_server/config_schema.py:\n  " + "\n  ".join(unclassified)
        )

    def test_config_backed_properties_spread_the_derived_fragment(self):
        """A property classified CONFIG_BACKED must actually spread that
        fragment (type/minimum/maximum/enum) rather than hand-retyping the
        same values — otherwise a future spec() change silently stops
        reaching the schema. Equality also proves no stray 'default' leaked
        in, since CONFIG_BACKED itself never carries one.
        """
        mismatches = []
        for tool_name, arg_key, prop in self._iter_spec_properties():
            key = self._classification_key(tool_name, arg_key)
            if key is None or key not in CONFIG_BACKED:
                continue
            actual = {k: v for k, v in prop.items() if k != "description"}
            if actual != CONFIG_BACKED[key]:
                mismatches.append(
                    f"{tool_name}.{arg_key}: schema has {actual}, "
                    f"CONFIG_BACKED[{key!r}] is {CONFIG_BACKED[key]}"
                )
        assert not mismatches, "\n  ".join(mismatches)

    def test_output_format_properties_match_shared_definition(self):
        mismatches = [
            spec.name
            for spec in TOOL_SPECS
            if spec.input_schema["properties"].get("output_format")
            != OUTPUT_FORMAT_PROPERTY
        ]
        assert not mismatches, (
            "Tool(s) whose output_format property diverges from "
            "OUTPUT_FORMAT_PROPERTY: " + ", ".join(mismatches)
        )


class TestHandTypedSchemaSeam:
    """D2 made HAND_TYPED[key].schema and arg()'s fallback the same read of the
    same object, so a schema default and a handler fallback can no longer
    independently drift — the exact seam include_exclusive fell through, where
    the old tool_registry.py's "default": False and index_handlers.py's
    no-fallback tri-state resolution silently disagreed (docs/adr/0046). These
    ratchets make that regression structurally impossible, not just caught by
    review.
    """

    @staticmethod
    def _governed_properties():
        """Yield (key, prop) for every ToolSpec property whose "<tool>.<arg>"
        key has a direct HAND_TYPED entry. HAND_TYPED carries no "*.<arg>"
        wildcard entries, so a direct match is the only membership test
        needed.
        """
        for spec in TOOL_SPECS:
            for arg_key, prop in spec.input_schema["properties"].items():
                key = f"{spec.name}.{arg_key}"
                if key in HAND_TYPED:
                    yield key, prop

    def test_schema_default_matches_the_seam(self):
        """A published 'default' must be the exact same value AND type as
        HAND_TYPED[key].schema's — plain != would let 0 pass for False, or
        "auto" pass for a hypothetical non-enum 0/"" mismatch.
        """
        mismatches = []
        for key, prop in self._governed_properties():
            record = HAND_TYPED[key]
            if record.default is NO_DEFAULT:
                continue
            expected = record.schema.get("default")
            actual = prop.get("default")
            if (actual, type(actual)) != (expected, type(expected)):
                mismatches.append(
                    f"{key}: schema has {actual!r} ({type(actual).__name__}), "
                    f"HAND_TYPED[{key!r}].schema has {expected!r} "
                    f"({type(expected).__name__})"
                )
        assert not mismatches, "\n  ".join(mismatches)

    def test_every_published_default_comes_from_hand_typed(self):
        """No '"default"' may appear on a property whose classification key is
        either missing from HAND_TYPED entirely, or maps to a
        HAND_TYPED(default=NO_DEFAULT) entry — that combination is exactly the
        include_exclusive regression: a schema default published for a
        parameter whose own rationale says it must stay tri-state (e.g. omit
        to reuse the value stored in project_info.json).
        """
        unbacked = []
        for spec in TOOL_SPECS:
            for arg_key, prop in spec.input_schema["properties"].items():
                if "default" not in prop:
                    continue
                key = f"{spec.name}.{arg_key}"
                record = HAND_TYPED.get(key)
                if record is None or record.default is NO_DEFAULT:
                    rationale = record.rationale if record else "no HAND_TYPED entry"
                    unbacked.append(f"{key} ({rationale})")
        assert not unbacked, (
            "Propert(y/ies) publishing a schema default with no backing "
            "HAND_TYPED default:\n  " + "\n  ".join(unbacked)
        )

    def test_hand_typed_defaults_are_json_scalars(self):
        """.schema's emitted 'default' value — not .default itself, which may
        legitimately hold an Enum member (see SearchMode) — must be a plain
        JSON scalar so it is safe to spread straight into a wire schema.
        """
        json_scalars = (str, int, float, bool, type(None))
        offenders = []
        for key, record in HAND_TYPED.items():
            if record.default is NO_DEFAULT:
                continue
            value = record.schema.get("default")
            if not isinstance(value, json_scalars):
                offenders.append(f"{key}: .schema default is {type(value).__name__}")
        assert not offenders, "\n  ".join(offenders)

    def test_no_inline_default_literal_in_tool_specs_source(self):
        """AST ban, supplementary to the runtime seam above: after D2,
        mcp_server/tool_specs.py must never contain a literal '"default": ...'
        dict entry in a TOOL_SPECS row's input_schema — every default now
        reaches the schema exclusively via a HAND_TYPED[key].schema or
        CONFIG_BACKED[key] spread. Detection-after-the-fact (comparing values
        at runtime, as the tests above do) is precisely the mechanism that
        already failed once on include_exclusive; this bans the pattern at
        the source-code level so a reviewer doesn't have to re-derive that
        reasoning from scratch.
        """
        import ast
        import inspect

        import mcp_server.tool_specs as tool_specs_module

        source = inspect.getsource(tool_specs_module)
        tree = ast.parse(source)

        offending_lines = [
            key.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Dict)
            for key in node.keys
            if isinstance(key, ast.Constant) and key.value == "default"
        ]

        assert not offending_lines, (
            "Literal '\"default\": ...' dict entries found at line(s) "
            f"{offending_lines} in tool_specs.py — defaults must be "
            "spread from HAND_TYPED[key].schema / CONFIG_BACKED[key], never "
            "restated inline (docs/adr/0046)"
        )
