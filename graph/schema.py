"""Single owner of the code-graph NetworkX encoding.

Defines the attribute key names used on nodes and edges of the
``CodeGraphStorage`` MultiDiGraph, plus the canonical forward→reverse
relationship-type mapping.

Design rules
------------
* Pure literals only — **no imports** — so any layer (``graph/``,
  ``search/``, ``mcp_server/``) may import this module without creating
  a circular dependency.
* All attribute-key constants are plain strings whose values match the
  literal strings currently written into the graph at index time.  Changing
  a constant here changes the *name* of the attribute — only do that if you
  also update every reader and re-index.

Reverse-relation names
----------------------
``REVERSE_RELATIONS`` maps every forward ``RelationshipType`` value to the
human-readable label used for incoming edges in query results.  The mapping
must stay complete — the test in ``tests/unit/graph/test_schema.py`` asserts
that every enum value is present, so adding a new ``RelationshipType`` will
fail CI until a corresponding entry is added here.
"""

# ---------------------------------------------------------------------------
# Node attribute keys
# ---------------------------------------------------------------------------

NODE_ATTR_NAME: str = "name"  # symbol name (e.g. "MyClass", "my_func")
NODE_ATTR_TYPE: str = "type"  # chunk kind ("function", "class", "symbol_name", …)
NODE_ATTR_FILE: str = "file"  # file path (may be absolute; prefer chunk_id prefix)
NODE_ATTR_LANGUAGE: str = "language"  # language tag (e.g. "python")
NODE_ATTR_IS_TARGET_NAME: str = "is_target_name"  # True on placeholder symbol nodes
NODE_ATTR_IS_CALL_TARGET: str = "is_call_target"  # True on unresolved call-target nodes

# Special value of NODE_ATTR_TYPE for placeholder nodes (unresolved call/symbol targets).
# Used by community_detector and callee queries to filter real chunk nodes from phantoms.
NODE_TYPE_SYMBOL_NAME: str = "symbol_name"

# ---------------------------------------------------------------------------
# Edge attribute keys
# ---------------------------------------------------------------------------

EDGE_ATTR_TYPE: str = "type"  # relationship kind ("calls", "inherits", …)
EDGE_ATTR_LINE: str = "line"  # call-site / definition line number (int)
EDGE_ATTR_CONFIDENCE: str = (
    "confidence"  # resolver confidence ("exact"/"ambiguous"/float)
)
EDGE_ATTR_IS_METHOD: str = "is_method"  # True when the call is a method call
EDGE_ATTR_IS_RESOLVED: str = (
    "is_resolved"  # True when target was resolved to a chunk_id
)
EDGE_ATTR_WEIGHT: str = (
    "weight"  # edge weight used in community-detection collapsed graph
)

# ---------------------------------------------------------------------------
# Forward → reverse relationship-name mapping
# ---------------------------------------------------------------------------

#: Maps each forward ``RelationshipType`` value to its reverse label.
#: Used to name incoming edges in ``get_neighbors``/``find_connections`` results.
#: Keep in sync with ``RelationshipType`` in
#: ``chunking/relationships/relationship_types.py``.
REVERSE_RELATIONS: dict[str, str] = {
    "calls": "called_by",
    "inherits": "inherited_by",
    "uses_type": "used_as_type_by",
    "imports": "imported_by",
    "decorates": "decorated_by",
    "raises": "raised_by",
    "catches": "caught_by",
    "instantiates": "instantiated_by",
    "implements": "implemented_by",
    "overrides": "overridden_by",
    "assigns_to": "assigned_by",
    "reads_from": "read_by",
    "defines_constant": "constant_defined_by",
    "defines_enum_member": "enum_member_defined_by",
    "defines_class_attr": "class_attr_defined_by",
    "defines_field": "field_defined_by",
    "uses_constant": "constant_used_by",
    "uses_default": "default_used_by",
    "uses_global": "global_used_by",
    "asserts_type": "type_asserted_by",
    "uses_context_manager": "context_manager_used_by",
}


def get_reverse_relation(rel_type: str) -> str:
    """Return the incoming-edge label for a forward relationship type.

    Args:
        rel_type: Forward relationship type string (e.g. ``"calls"``).

    Returns:
        The reverse label (e.g. ``"called_by"``), or ``f"{rel_type}_by"``
        as a fallback for types not yet in ``REVERSE_RELATIONS``.
    """
    return REVERSE_RELATIONS.get(rel_type, f"{rel_type}_by")
