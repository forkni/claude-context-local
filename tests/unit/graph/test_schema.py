"""Unit tests for graph.schema — single owner of the code-graph encoding.

The most important test here is the *completeness gate*: every value of the
``RelationshipType`` enum must have an entry in ``REVERSE_RELATIONS``.  This
replaces the compile-time coupling that existed when the 21-entry dict lived
inside ``_get_reverse_relation_type``; now adding a 22nd ``RelationshipType``
without adding a corresponding reverse-name entry will fail CI here.
"""

import pytest

from graph.schema import (
    EDGE_ATTR_CONFIDENCE,
    EDGE_ATTR_IS_METHOD,
    EDGE_ATTR_IS_RESOLVED,
    EDGE_ATTR_LINE,
    EDGE_ATTR_TYPE,
    EDGE_ATTR_WEIGHT,
    NODE_ATTR_FILE,
    NODE_ATTR_IS_CALL_TARGET,
    NODE_ATTR_IS_TARGET_NAME,
    NODE_ATTR_LANGUAGE,
    NODE_ATTR_NAME,
    NODE_ATTR_TYPE,
    NODE_TYPE_SYMBOL_NAME,
    REVERSE_RELATIONS,
    get_reverse_relation,
)


# ---------------------------------------------------------------------------
# Constants have the expected string values (guards against typos)
# ---------------------------------------------------------------------------


class TestConstantValues:
    def test_node_attr_name(self):
        assert NODE_ATTR_NAME == "name"

    def test_node_attr_type(self):
        assert NODE_ATTR_TYPE == "type"

    def test_node_attr_file(self):
        assert NODE_ATTR_FILE == "file"

    def test_node_attr_language(self):
        assert NODE_ATTR_LANGUAGE == "language"

    def test_node_attr_is_target_name(self):
        assert NODE_ATTR_IS_TARGET_NAME == "is_target_name"

    def test_node_attr_is_call_target(self):
        assert NODE_ATTR_IS_CALL_TARGET == "is_call_target"

    def test_node_type_symbol_name(self):
        assert NODE_TYPE_SYMBOL_NAME == "symbol_name"

    def test_edge_attr_type(self):
        assert EDGE_ATTR_TYPE == "type"

    def test_edge_attr_line(self):
        assert EDGE_ATTR_LINE == "line"

    def test_edge_attr_confidence(self):
        assert EDGE_ATTR_CONFIDENCE == "confidence"

    def test_edge_attr_is_method(self):
        assert EDGE_ATTR_IS_METHOD == "is_method"

    def test_edge_attr_is_resolved(self):
        assert EDGE_ATTR_IS_RESOLVED == "is_resolved"

    def test_edge_attr_weight(self):
        assert EDGE_ATTR_WEIGHT == "weight"


# ---------------------------------------------------------------------------
# Completeness gate: every RelationshipType enum value must be in REVERSE_RELATIONS
# ---------------------------------------------------------------------------


class TestReverseRelationsCompleteness:
    """Add a new RelationshipType → this test fails → you must add to REVERSE_RELATIONS."""

    def test_all_relationship_types_covered(self):
        from chunking.relationships.relationship_types import RelationshipType

        enum_values = {rt.value for rt in RelationshipType}
        missing = enum_values - set(REVERSE_RELATIONS.keys())
        assert not missing, (
            f"REVERSE_RELATIONS in graph/schema.py is missing entries for: {missing!r}. "
            "Add the corresponding reverse-name strings to graph.schema.REVERSE_RELATIONS."
        )

    def test_reverse_relations_has_21_entries(self):
        """Snapshot: if this number changes, update the docstring in schema.py too."""
        assert len(REVERSE_RELATIONS) == 21


# ---------------------------------------------------------------------------
# get_reverse_relation: mapped and fallback cases
# ---------------------------------------------------------------------------


class TestGetReverseRelation:
    def test_calls_returns_called_by(self):
        assert get_reverse_relation("calls") == "called_by"

    def test_inherits_returns_inherited_by(self):
        assert get_reverse_relation("inherits") == "inherited_by"

    def test_uses_type_returns_used_as_type_by(self):
        assert get_reverse_relation("uses_type") == "used_as_type_by"

    def test_imports_returns_imported_by(self):
        assert get_reverse_relation("imports") == "imported_by"

    def test_defines_constant_returns_constant_defined_by(self):
        # Irregular form — not the default _by suffix
        assert get_reverse_relation("defines_constant") == "constant_defined_by"

    def test_unknown_type_fallback(self):
        assert get_reverse_relation("unknown_future_type") == "unknown_future_type_by"

    def test_empty_string_fallback(self):
        assert get_reverse_relation("") == "_by"

    @pytest.mark.parametrize("rel_type,expected", list(REVERSE_RELATIONS.items()))
    def test_all_known_types_round_trip(self, rel_type: str, expected: str):
        assert get_reverse_relation(rel_type) == expected
