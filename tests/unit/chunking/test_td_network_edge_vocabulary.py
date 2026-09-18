"""Drift detection for the ``.tdgraph.json`` edge-type vocabulary (ADR-0072).

TD_Glossary_tox's ``Extensions/OperatorGlossary/tdgraph_contract.py`` declares the
producer's edge vocabulary (``GRAPH_EDGE_TYPES``, 13 types, canonical order) and ships
its own drift guard (``tests/test_tdgraph_edge_types_contract.py``) asserting three
copies of that vocabulary -- the exporter's ``EDGE_TYPES`` registry, the contract
tuple, and the JSON-schema ``type`` enum -- agree with each other, in both directions
and in exact order. That producer test's docstring states plainly that this consumer's
drift detection is supposed to diff against exactly that vocabulary. Before ADR-0072
it did not: this repo held no copy of the vocabulary at all, and silently dropped the
producer's ``clone`` edge type for a full release (see ``RelationshipType.CLONES``).

This module is the consumer's half of that two-sided contract: it pins
``TD_GRAPH_EDGE_TYPES`` (declared in ``chunking/td_network_chunker.py``) against the
handled set derived from source, and against the committed fixture, so an edge type
added on either side without a matching change on this one fails CI instead of
silently dropping data or accessible only by direct chunk-metadata reading.
"""

import json
from pathlib import Path

from chunking.td_network_chunker import (
    _EXPLICIT_BRANCH_EDGE_TYPES,
    _SIMPLE_EDGE_MAP,
    TD_GRAPH_EDGE_TYPE_SET,
    TD_GRAPH_EDGE_TYPES,
)


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "td_network"
FIXTURE_PATH = FIXTURE_DIR / "Test_network.tdgraph.json"


def _handled_edge_types() -> frozenset[str]:
    """The edge types this chunker actually dispatches on, derived from source.

    Union of the explicit ``if``/``elif`` branch literals (kept as a frozenset
    constant next to the dispatch itself, specifically so this test does not need
    a fourth, independently-maintained copy of the list) and ``_SIMPLE_EDGE_MAP``'s
    keys (the table-driven branch).
    """
    return _EXPLICIT_BRANCH_EDGE_TYPES | frozenset(_SIMPLE_EDGE_MAP)


def test_td_graph_edge_types_has_no_duplicates():
    """Order-sensitive tuple, so a duplicate would silently under-count."""
    assert len(TD_GRAPH_EDGE_TYPES) == len(set(TD_GRAPH_EDGE_TYPES))


def test_td_graph_edge_type_set_matches_the_tuple():
    assert frozenset(TD_GRAPH_EDGE_TYPES) == TD_GRAPH_EDGE_TYPE_SET


def test_handled_edge_types_match_declared_vocabulary():
    """The chunker's dispatch handles exactly the declared 13 producer types.

    This is the actual drift guard: add a 14th type to ``TD_GRAPH_EDGE_TYPES``
    without teaching the chunker to handle it (or vice versa) and this fails.
    """
    handled = _handled_edge_types()
    assert handled == TD_GRAPH_EDGE_TYPE_SET, (
        f"Handled edge types {sorted(handled)} != declared vocabulary "
        f"{sorted(TD_GRAPH_EDGE_TYPE_SET)}. If a producer edge type was added or "
        "removed, update both chunking/td_network_chunker.py's dispatch and "
        "TD_GRAPH_EDGE_TYPES (and the mirrored TD_Glossary_tox contract)."
    )


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_edges_use_only_declared_types():
    graph = _load_fixture()
    edge_types_in_use = {e["type"] for e in graph["edges"]}
    unknown = edge_types_in_use - TD_GRAPH_EDGE_TYPE_SET
    assert not unknown, (
        f"Fixture edges use undeclared type(s) {sorted(unknown)} -- add them to "
        "TD_GRAPH_EDGE_TYPES if they are real producer types, or fix the fixture."
    )


def test_fixture_edge_types_histogram_is_the_full_faithful_shape():
    """The fixture's ``edge_types`` summary must be all 13 types, in canonical
    order, with true counts (including zeros) -- exactly what a real export's
    ``_compute_edge_types_block`` always writes (``dict.fromkeys(EDGE_TYPE_ORDER,
    0)`` seeded first, never a filtered subset). This is what keeps the fixture
    itself honest, not just the code that reads it.
    """
    graph = _load_fixture()
    histogram_types = [entry["type"] for entry in graph["edge_types"]]
    assert tuple(histogram_types) == TD_GRAPH_EDGE_TYPES, (
        "Fixture edge_types histogram order/membership drifted from "
        "TD_GRAPH_EDGE_TYPES -- a real export always writes all 13 entries, "
        "in this order, zeros included."
    )

    from collections import Counter

    actual_counts = Counter(e["type"] for e in graph["edges"])
    declared_counts = {entry["type"]: entry["count"] for entry in graph["edge_types"]}
    for etype in TD_GRAPH_EDGE_TYPES:
        assert declared_counts[etype] == actual_counts.get(etype, 0), (
            f"edge_types histogram count for {etype!r} ({declared_counts[etype]}) "
            f"!= actual edges array count ({actual_counts.get(etype, 0)})"
        )


def test_fixture_has_a_clone_edge_to_an_in_scope_master():
    """A16.3 verification precondition: at least one ``clone`` edge whose ``dst``
    resolves to a real (non-stub) node, so ``find_connections`` on it returns an
    actual chunk->chunk edge and not just a phantom.
    """
    graph = _load_fixture()
    stub_ids = {n["id"] for n in graph["nodes"] if n.get("stub")}
    clone_edges = [e for e in graph["edges"] if e["type"] == "clone"]
    assert clone_edges, "fixture has no clone edge at all"
    assert any(e["dst"] not in stub_ids for e in clone_edges), (
        "no clone edge points at an in-scope (non-stub) master"
    )


def test_fixture_has_a_clone_edge_to_a_stub_master():
    """The built-in annotateCOMP utility-node case (network-graph.md:307-308 in
    TD_Glossary_tox): a clone's master frequently lives outside the walked
    project and arrives as a stub node, not a null dst.
    """
    graph = _load_fixture()
    stub_ids = {n["id"] for n in graph["nodes"] if n.get("stub")}
    clone_edges = [e for e in graph["edges"] if e["type"] == "clone"]
    assert any(e["dst"] in stub_ids for e in clone_edges), (
        "no clone edge points at a stub (out-of-scope) master"
    )


def test_no_clone_edge_has_a_null_dst():
    """clone's dst is never null in a real export (_emit_clone_edge always
    sources it from _stub_target()); unlike script_ref, there is no legitimate
    null-dst case for this type.
    """
    graph = _load_fixture()
    for e in graph["edges"]:
        if e["type"] == "clone":
            assert e["dst"] is not None
