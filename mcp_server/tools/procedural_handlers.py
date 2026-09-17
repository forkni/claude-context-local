"""Procedural Graph guidance and edit tool handlers (ADR-0074).

The only place ``graph.procedural_graph`` meets ``mcp_server``. Two
handlers over a file-backed ``ProceduralGraphStore``
(``<storage_dir>/procedural_graphs/``): one read-only lookup
(``handle_get_procedural_guidance``) and one typed, validated edit
(``handle_edit_procedural_graph``). No LLM call happens here -- guidance
text is returned verbatim for the calling agent to reason over.
"""

import logging
from typing import Any

from graph.procedural_graph import NAME_PATTERN, ProceduralGraph, ProceduralGraphStore
from mcp_server.config_schema import arg
from mcp_server.storage_manager import get_storage_dir
from mcp_server.tools import responses
from mcp_server.tools.decorators import error_handler, with_mutation_lock


logger = logging.getLogger(__name__)


def _store() -> ProceduralGraphStore:
    return ProceduralGraphStore(get_storage_dir() / "procedural_graphs")


def _load_or_error(
    store: ProceduralGraphStore, name: str
) -> tuple[ProceduralGraph | None, dict[str, Any] | None]:
    """Resolve *name* to a validated graph, or an error envelope.

    A malformed *name* is rejected via :data:`NAME_PATTERN` before any
    filesystem access; a well-formed but unknown *name* reports the store's
    current names so the caller can self-correct.
    """
    if not NAME_PATTERN.match(name):
        return None, responses.error("invalid procedural graph name", name=name)
    try:
        return store.load(name), None
    except FileNotFoundError:
        return None, responses.error(
            "no such procedural graph", name=name, available=store.list_names()
        )


@error_handler("Procedural guidance")
async def handle_get_procedural_guidance(arguments: dict[str, Any]) -> dict:
    """Locate a procedural graph at ``last_action`` and extract nearby guidance.

    A miss (``last_action`` names no node) is not an error: it returns the
    full graph with ``located: false`` so the caller can still see every
    transition, and the miss itself is a signal the producer measures
    offline -- see ``ProceduralGraph.locate``'s "no fuzzy matching" note.
    """
    name = arguments.get("graph", "")
    last_action = arguments.get("last_action")
    store = _store()
    graph, error = _load_or_error(store, name)
    if error is not None:
        return error
    assert graph is not None

    hops = min(max(arg(arguments, "get_procedural_guidance.hops"), 1), 4)
    located_id = graph.locate(last_action)
    transitions = graph.extract(located_id, hops)
    guidance = graph.serialize(name, last_action, located_id, hops, transitions)

    return responses.ok(
        graph=name,
        last_action=last_action,
        located=located_id is not None,
        hops=hops,
        node_count=len(graph.node_ids),
        edge_count=len(transitions),
        guidance=guidance,
    )


@error_handler("Procedural graph edit")
@with_mutation_lock
async def handle_edit_procedural_graph(arguments: dict[str, Any]) -> dict:
    """Apply a typed edit to a procedural graph, saving only when it is
    both valid and not a dry run.

    An invalid edit is never saved regardless of ``dry_run`` -- ``dry_run``
    only gates whether a *valid* edit is committed to disk.
    """
    name = arguments.get("graph", "")
    edit = arguments.get("edit", {})
    dry_run = arg(arguments, "edit_procedural_graph.dry_run")
    store = _store()
    graph, error = _load_or_error(store, name)
    if error is not None:
        return error
    assert graph is not None

    report = graph.apply_edit(edit)
    committed = False
    if report.valid and not dry_run:
        assert report.graph is not None
        store.save(name, report.graph)
        committed = True

    result_graph = report.graph if report.graph is not None else graph
    return responses.ok(
        graph=name,
        dry_run=dry_run,
        valid=report.valid,
        errors=list(report.errors),
        applied=report.applied,
        node_count=len(result_graph.node_ids),
        edge_count=len(result_graph.extract(None, 1)),
        committed=committed,
    )
