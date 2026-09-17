"""File-backed Procedural Graph store (ADR-0074).

A *Procedural Graph* (arXiv 2609.09153) is a directed multigraph whose nodes
are actions from a closed, producer-owned vocabulary and whose edges
("transitions") carry three free-text attributes -- ``condition``,
``guidance``, ``pitfalls`` (jointly "Phi"). ``TD_Glossary_tox`` is the
producer that builds these graphs; this module is the consumer-side store:
given an agent's last action, *locate* the graph at that node, *extract* an
h-hop out-neighbourhood, and *serialize* it to plain text for the calling
agent to reason over. No LLM call happens here.

Canonical state is the document, not the derived NetworkX graph
------------------------------------------------------------------
``ProceduralGraph`` holds an ordered node-id list and an edge-dict list, and
derives a private ``nx.MultiDiGraph`` (keyed by relation) purely for
traversal. This is deliberate: ``nx.MultiDiGraph.add_edge(u, v, key=r, ...)``
*overwrites* an existing ``(u, v, r)`` triple instead of rejecting it or
adding a parallel edge, and ``add_edge`` silently creates any endpoint that
does not already exist. Validating duplicate node ids, duplicate
``(src, relation, dst)`` triples, and dangling endpoints *after* building the
NetworkX graph would make all three structurally undetectable -- the
NetworkX object would already have silently absorbed the corruption. So
validation runs on the raw document/lists first (:func:`_validate_document`),
and only a value known to be duplicate-free and endpoint-complete is ever
handed to :func:`_build_graph`. This also gives node insertion order and
byte-stable round-tripping for free, and lets :meth:`ProceduralGraph.apply_edit`
copy two small lists instead of deep-copying a NetworkX object.

Byte-stability
---------------
``ProceduralGraphStore.save`` is canonicalising and idempotent:
``save(load(save(x)))`` equals ``save(x)`` byte for byte. It does **not**
follow that ``save(load(y)) == y`` for an arbitrary hand-authored ``y`` --
``json.dumps`` defaults to ``ensure_ascii=True``, so any non-ASCII character
in a ``guidance``/``pitfalls`` string round-trips through a ``\\uXXXX``
escape. Seed documents intended to stay byte-identical after import must be
pure ASCII.
"""

import json
import re
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx

from utils.atomic_io import write_json_atomic


PG_RELATIONS: tuple[str, ...] = (
    "LEADS_TO",
    "TRIGGERS",
    "PROVIDES_INPUT_FOR",
    "CONVERGES_TO",
)
"""The producer's closed vocabulary of transition relations."""

PG_EDGE_FIELDS: tuple[str, ...] = ("condition", "guidance", "pitfalls")
"""The three free-text attributes ("Phi") every transition carries."""

PG_EDGE_KEYS: frozenset[str] = frozenset({"src", "dst", "relation", *PG_EDGE_FIELDS})
"""The exact key set of one edge record, document- or edit-side."""

PG_SCHEMA_VERSION = 1

NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
"""A procedural-graph name doubles as a file stem; this also blocks path
traversal (no ``.``, ``/``, or ``\\`` can appear)."""

NODE_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

_DOC_KEYS: frozenset[str] = frozenset(
    {"schema_version", "name", "notes", "nodes", "edges"}
)
_EDIT_KEYS: frozenset[str] = frozenset(
    {"add_nodes", "delete_nodes", "add_edges", "delete_edges"}
)
_DELETE_EDGE_KEYS: frozenset[str] = frozenset({"src", "dst", "relation"})
_EMPTY_APPLIED: dict[str, int] = {
    "add_nodes": 0,
    "delete_nodes": 0,
    "add_edges": 0,
    "delete_edges": 0,
}


class ProceduralGraphError(ValueError):
    """A procedural-graph document or edit failed validation.

    Carries every violation found (``.errors``), not just the first --
    :func:`_validate_document` and :func:`_validate_structure` both collect
    all errors before raising. Subclasses ``ValueError`` so callers can catch
    "bad name" and "bad document" failures with one except clause.
    """

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors: list[str] = list(errors)
        super().__init__("; ".join(self.errors) or "invalid procedural graph")


@dataclass(frozen=True, slots=True)
class Transition:
    """One out-edge emitted by :meth:`ProceduralGraph.extract`.

    ``hop`` is the BFS depth of ``src`` (not ``dst``) -- an edge leaving a
    node first reached at depth ``d`` is emitted at hop ``d + 1``, even when
    it closes a cycle back to a shallower node. ``hop is None`` marks a
    whole-graph dump (``extract(start=None, ...)``).
    """

    hop: int | None
    src: str
    relation: str
    dst: str
    condition: str
    guidance: str
    pitfalls: str


@dataclass(frozen=True, slots=True)
class EditReport:
    """Outcome of :meth:`ProceduralGraph.apply_edit`.

    ``applied`` always carries all four verb keys
    (``add_nodes``/``delete_nodes``/``add_edges``/``delete_edges``), even when
    the edit was rejected before any item was processed. ``graph`` is
    non-``None`` if and only if ``valid`` is ``True`` -- the caller decides
    whether and where to save it.
    """

    valid: bool
    errors: tuple[str, ...]
    applied: dict[str, int]
    graph: "ProceduralGraph | None"


def _plural(n: int, word: str) -> str:
    return word if n == 1 else f"{word}s"


def _fmt_field(value: str) -> str:
    return value if value else "-"


def _build_graph(nodes: list[str], edges: list[dict[str, str]]) -> nx.MultiDiGraph:
    """Build the traversal graph from already-validated, duplicate-free lists.

    Nodes are added first, in order, so a later ``add_edge`` never has to
    auto-create an endpoint (which would silently corrupt node order).
    """
    g: nx.MultiDiGraph = nx.MultiDiGraph()
    g.add_nodes_from(nodes)
    for e in edges:
        g.add_edge(
            e["src"], e["dst"], key=e["relation"], **{f: e[f] for f in PG_EDGE_FIELDS}
        )
    return g


# --- document-level validation (runs before any graph exists) --------------


def _validate_doc_header(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    unknown = set(doc) - _DOC_KEYS
    if unknown:
        errors.append(f"document: unknown top-level key(s) {sorted(unknown)}")
    if doc.get("schema_version") != PG_SCHEMA_VERSION:
        errors.append(
            f"document: schema_version must be {PG_SCHEMA_VERSION}, "
            f"got {doc.get('schema_version')!r}"
        )
    name = doc.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.match(name):
        errors.append(f"document: name {name!r} does not match {NAME_PATTERN.pattern}")
    if "notes" in doc and not isinstance(doc["notes"], str):
        errors.append(
            f"document: notes must be a string, got {type(doc['notes']).__name__}"
        )
    return errors


def _validate_doc_nodes(raw: object) -> tuple[list[str], list[str]]:
    """Returns (declared ids, in doc order, errors)."""
    if not isinstance(raw, list):
        return [], ["document: nodes must be a list"]
    errors: list[str] = []
    ids: list[str] = []
    seen: set[str] = set()
    for i, rec in enumerate(raw):
        if not isinstance(rec, dict) or set(rec) != {"id"}:
            errors.append(
                f"document: nodes[{i}] must be an object with exactly key 'id'"
            )
            continue
        node_id = rec["id"]
        if not isinstance(node_id, str) or not NODE_ID_PATTERN.match(node_id):
            errors.append(
                f"document: nodes[{i}].id {node_id!r} does not match "
                f"{NODE_ID_PATTERN.pattern}"
            )
            continue
        if node_id in seen:
            errors.append(f"document: duplicate node id {node_id!r}")
            continue
        seen.add(node_id)
        ids.append(node_id)
    return ids, errors


def _validate_edge_record(rec: object, idx: int, declared: set[str]) -> list[str]:
    if not isinstance(rec, dict) or set(rec) != PG_EDGE_KEYS:
        return [
            f"document: edges[{idx}] must be an object with keys {sorted(PG_EDGE_KEYS)}"
        ]
    errors: list[str] = []
    for field in PG_EDGE_FIELDS:
        if not isinstance(rec[field], str):
            errors.append(f"document: edges[{idx}].{field} must be a string")
    relation = rec["relation"]
    if relation not in PG_RELATIONS:
        errors.append(
            f"document: edges[{idx}].relation {relation!r} is not one of {PG_RELATIONS}"
        )
    src, dst = rec["src"], rec["dst"]
    if src not in declared:
        errors.append(f"document: edges[{idx}].src {src!r} is not a declared node")
    if dst not in declared:
        errors.append(f"document: edges[{idx}].dst {dst!r} is not a declared node")
    if src == dst:
        errors.append(f"document: edges[{idx}] is a self-loop ({src!r})")
    return errors


def _validate_doc_edges(raw: object, declared: set[str]) -> list[str]:
    if not isinstance(raw, list):
        return ["document: edges must be a list"]
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for i, rec in enumerate(raw):
        rec_errors = _validate_edge_record(rec, i, declared)
        errors.extend(rec_errors)
        if rec_errors or not isinstance(rec, dict):
            continue
        key = (rec["src"], rec["relation"], rec["dst"])
        if key in seen:
            errors.append(
                f"document: duplicate edge (src={key[0]!r}, relation={key[1]!r}, "
                f"dst={key[2]!r})"
            )
            continue
        seen.add(key)
    return errors


def _validate_document(doc: object) -> list[str]:
    """All shape/type errors in a raw loaded document, collected -- never the first only."""
    if not isinstance(doc, dict):
        return ["document must be an object"]
    errors = list(_validate_doc_header(doc))
    node_ids, node_errors = _validate_doc_nodes(doc.get("nodes"))
    errors.extend(node_errors)
    errors.extend(_validate_doc_edges(doc.get("edges"), set(node_ids)))
    return errors


# --- graph-level validation (runs on lists already free of doc-level errors)


def _validate_structure(nodes: list[str], edges: list[dict[str, str]]) -> list[str]:
    """Entry/terminal/reachability rules. Assumes *nodes*/*edges* are already
    duplicate-free and endpoint-complete (guaranteed by the caller).
    """
    g = _build_graph(nodes, edges)
    errors: list[str] = []

    sources = sorted(n for n in g if g.in_degree(n) == 0)
    if len(sources) != 1:
        errors.append(
            f"graph must have exactly one entry node (in-degree 0); found {sources}"
        )

    terminals = {n for n in g if g.out_degree(n) == 0}
    if not terminals:
        errors.append("graph has no terminal node (every node has an out-edge)")
        return errors

    seen: set[str] = set(terminals)
    queue: deque[str] = deque(terminals)
    while queue:
        node = queue.popleft()
        for pred in g.predecessors(node):
            if pred not in seen:
                seen.add(pred)
                queue.append(pred)
    unreachable = sorted(n for n in g if n not in seen)
    if unreachable:
        errors.append(f"node(s) with no path to a terminal: {unreachable}")
    return errors


# --- edit application --------------------------------------------------------


def _edit_delete_edges(
    edges: list[dict[str, str]], items: object, applied: dict[str, int]
) -> list[str]:
    if not isinstance(items, list):
        return ["delete_edges must be a list"]
    errors: list[str] = []
    for item in items:
        if not isinstance(item, dict) or set(item) != _DELETE_EDGE_KEYS:
            errors.append(f"delete_edges: invalid edge reference {item!r}")
            continue
        src, dst, relation = item["src"], item["dst"], item["relation"]
        idx = next(
            (
                i
                for i, e in enumerate(edges)
                if e["src"] == src and e["dst"] == dst and e["relation"] == relation
            ),
            None,
        )
        if idx is None:
            errors.append(f"delete_edges: no such edge {src} -{relation}-> {dst}")
            continue
        del edges[idx]
        applied["delete_edges"] += 1
    return errors


def _edit_delete_nodes(
    nodes: list[str],
    edges: list[dict[str, str]],
    items: object,
    applied: dict[str, int],
) -> list[str]:
    if not isinstance(items, list):
        return ["delete_nodes must be a list"]
    errors: list[str] = []
    for item in items:
        if not isinstance(item, str):
            errors.append(f"delete_nodes: invalid node id {item!r}")
            continue
        if item not in nodes:
            errors.append(f"delete_nodes: no such node {item!r}")
            continue
        nodes.remove(item)
        edges[:] = [e for e in edges if e["src"] != item and e["dst"] != item]
        applied["delete_nodes"] += 1
    return errors


def _edit_add_nodes(
    nodes: list[str], items: object, applied: dict[str, int]
) -> list[str]:
    if not isinstance(items, list):
        return ["add_nodes must be a list"]
    errors: list[str] = []
    for item in items:
        if (
            not isinstance(item, dict)
            or set(item) != {"id"}
            or not isinstance(item.get("id"), str)
        ):
            errors.append(f"add_nodes: invalid node {item!r}")
            continue
        node_id = item["id"]
        if not NODE_ID_PATTERN.match(node_id):
            errors.append(f"add_nodes: invalid node id {node_id!r}")
            continue
        if node_id in nodes:
            errors.append(f"add_nodes: node already present {node_id!r}")
            continue
        nodes.append(node_id)
        applied["add_nodes"] += 1
    return errors


def _edit_add_edges(
    nodes: list[str],
    edges: list[dict[str, str]],
    items: object,
    applied: dict[str, int],
) -> list[str]:
    if not isinstance(items, list):
        return ["add_edges must be a list"]
    errors: list[str] = []
    for item in items:
        if not isinstance(item, dict) or set(item) != PG_EDGE_KEYS:
            errors.append(f"add_edges: invalid edge {item!r}")
            continue
        src, dst, relation = item["src"], item["dst"], item["relation"]
        if not all(isinstance(item[f], str) for f in PG_EDGE_FIELDS):
            errors.append(
                f"add_edges: non-string field(s) in edge {src}-{relation}->{dst}"
            )
            continue
        if relation not in PG_RELATIONS:
            errors.append(f"add_edges: unknown relation {relation!r}")
            continue
        if src not in nodes or dst not in nodes:
            errors.append(
                f"add_edges: unknown endpoint in edge {src}-{relation}->{dst}"
            )
            continue
        if src == dst:
            errors.append(f"add_edges: self-loop not allowed ({src})")
            continue
        if any(
            e["src"] == src and e["dst"] == dst and e["relation"] == relation
            for e in edges
        ):
            errors.append(f"add_edges: duplicate edge {src} -{relation}-> {dst}")
            continue
        edges.append({k: item[k] for k in ("src", "dst", "relation", *PG_EDGE_FIELDS)})
        applied["add_edges"] += 1
    return errors


def _validate_edit_shape(edit: object) -> list[str]:
    if not isinstance(edit, dict):
        return ["edit must be an object"]
    unknown = set(edit) - _EDIT_KEYS
    if unknown:
        return [f"edit: unknown key(s) {sorted(unknown)}"]
    return []


class ProceduralGraph:
    """A validated procedural graph: an ordered node-id list, an edge-dict
    list, optional free-text ``notes``, and a derived NetworkX multigraph
    used for traversal only (see module docstring).

    Construct only via :meth:`from_document` -- ``__init__`` takes
    already-validated lists and performs no validation of its own, so an
    unvalidated graph can never reach :meth:`extract`/:meth:`serialize`.
    """

    def __init__(
        self, nodes: list[str], edges: list[dict[str, str]], notes: str | None
    ) -> None:
        """Internal. Use :meth:`from_document` to construct a validated instance."""
        self._nodes: list[str] = list(nodes)
        self._edges: list[dict[str, str]] = [dict(e) for e in edges]
        self._notes: str | None = notes
        self._graph: nx.MultiDiGraph = _build_graph(self._nodes, self._edges)

    @classmethod
    def from_document(cls, doc: object) -> "ProceduralGraph":
        """Validate *doc* (document rules, then graph-structure rules) and build.

        Raises :class:`ProceduralGraphError` carrying every violation found.
        """
        errors = _validate_document(doc)
        if errors:
            raise ProceduralGraphError(errors)
        assert isinstance(doc, dict)
        nodes = [n["id"] for n in doc["nodes"]]
        edges = [
            {k: e[k] for k in ("src", "dst", "relation", *PG_EDGE_FIELDS)}
            for e in doc["edges"]
        ]
        notes = doc.get("notes")
        structure_errors = _validate_structure(nodes, edges)
        if structure_errors:
            raise ProceduralGraphError(structure_errors)
        return cls(nodes, edges, notes)

    def to_document(self, name: str) -> dict[str, Any]:
        """Canonical document: nodes in insertion order, edges sorted
        ``(src, relation, dst)``. Always writes ``name`` as given -- the
        caller (the store) passes the current file stem, so a file renamed
        on disk self-heals on its next save.
        """
        doc: dict[str, Any] = {"schema_version": PG_SCHEMA_VERSION, "name": name}
        if self._notes is not None:
            doc["notes"] = self._notes
        doc["nodes"] = [{"id": n} for n in self._nodes]
        doc["edges"] = [
            {k: e[k] for k in ("src", "dst", "relation", *PG_EDGE_FIELDS)}
            for e in sorted(
                self._edges, key=lambda e: (e["src"], e["relation"], e["dst"])
            )
        ]
        return doc

    @property
    def node_ids(self) -> list[str]:
        """Node ids in insertion order (the order :meth:`to_document` writes)."""
        return list(self._nodes)

    @property
    def notes(self) -> str | None:
        """Optional free-text note; preserved across save/load and edits."""
        return self._notes

    def locate(self, last_action: str | None) -> str | None:
        """Exact node-id match, else ``None``. No fuzzy, prefix, or
        case-folded matching -- a miss is a signal the producer measures
        offline.
        """
        if last_action is None:
            return None
        return last_action if last_action in self._graph else None

    def _all_transitions(self) -> list[Transition]:
        transitions = [
            Transition(
                hop=None,
                src=u,
                relation=r,
                dst=v,
                **{f: data[f] for f in PG_EDGE_FIELDS},
            )
            for u, v, r, data in self._graph.edges(keys=True, data=True)
        ]
        transitions.sort(key=lambda t: (t.src, t.relation, t.dst))
        return transitions

    def _bfs_transitions(self, start: str, hops: int) -> list[Transition]:
        depth: dict[str, int] = {start: 0}
        queue: deque[str] = deque([start])
        transitions: list[Transition] = []
        while queue:
            node = queue.popleft()
            d = depth[node]
            if d >= hops:
                continue
            for _, v, r, data in self._graph.out_edges(node, keys=True, data=True):
                transitions.append(
                    Transition(
                        hop=d + 1,
                        src=node,
                        relation=r,
                        dst=v,
                        **{f: data[f] for f in PG_EDGE_FIELDS},
                    )
                )
                if v not in depth:
                    depth[v] = d + 1
                    queue.append(v)
        transitions.sort(key=lambda t: (t.hop, t.src, t.relation, t.dst))
        return transitions

    def extract(self, start: str | None, hops: int) -> list[Transition]:
        """BFS over out-edges from *start* for *hops* levels.

        Hop 1 is every edge leaving *start*; hop *k* is every edge leaving a
        node first reached at hop *k-1* -- an edge's hop is the depth of its
        *source*, so a cycle-closing edge back into an already-visited node
        is still emitted once, at the depth of the node that closes the
        cycle. ``start=None`` returns every edge in the graph with
        ``hop=None``, sorted ``(src, relation, dst)``.

        Raises ``ValueError`` if ``hops < 1`` or *start* names no node --
        never silently falls back to the whole graph, which would make a
        typo look like a successful answer.
        """
        if hops < 1:
            raise ValueError(f"hops must be >= 1, got {hops}")
        if start is None:
            return self._all_transitions()
        if start not in self._graph:
            raise ValueError(f"unknown start node: {start!r}")
        return self._bfs_transitions(start, hops)

    def serialize(
        self,
        name: str,
        last_action: str | None,
        located: str | None,
        hops: int,
        transitions: Sequence[Transition],
    ) -> str:
        """Render the fixed plain-text block: a header line, then one line
        per transition. No trailing newline.
        """
        count = len(transitions)
        if located is not None:
            header = (
                f'Procedural graph "{name}": {hops} {_plural(hops, "hop")} '
                f"from {located}, {count} {_plural(count, 'transition')}."
            )
        elif last_action is not None:
            header = (
                f'Procedural graph "{name}": "{last_action}" is not a '
                f"procedure node; full graph, {count} {_plural(count, 'transition')}."
            )
        else:
            header = f'Procedural graph "{name}": full graph, {count} {_plural(count, "transition")}.'

        lines = [header]
        for t in transitions:
            prefix = f"[hop {t.hop}] " if t.hop is not None else ""
            fields = " | ".join(
                f"{f}: {_fmt_field(getattr(t, f))}" for f in PG_EDGE_FIELDS
            )
            lines.append(f"{prefix}{t.src} -{t.relation}-> {t.dst} | {fields}")
        return "\n".join(lines)

    def apply_edit(self, edit: object) -> EditReport:
        """Apply *edit* to a copy of this graph's lists and re-validate.

        Never mutates ``self``. Order: delete edges, then delete nodes
        (dropping their incident edges), then add nodes, then add edges.
        Every phase runs in full -- a failing item is skipped, not the rest
        of the edit -- but the final structural validation is skipped
        entirely if any phase produced an error, since a half-applied graph
        would otherwise bury the real error under cascading ones (missing
        entry node, no terminal, ...).

        Deleting an absent node/edge, or adding an already-present one, is
        an error, not a no-op: a stale edit against a changed graph must
        fail loudly, and duplicate-edge silence is exactly what NetworkX
        would otherwise do (see module docstring).
        """
        shape_errors = _validate_edit_shape(edit)
        if shape_errors:
            return EditReport(
                valid=False,
                errors=tuple(shape_errors),
                applied=dict(_EMPTY_APPLIED),
                graph=None,
            )
        assert isinstance(edit, dict)

        nodes = list(self._nodes)
        edges = [dict(e) for e in self._edges]
        applied = dict(_EMPTY_APPLIED)

        phase_errors: list[str] = []
        phase_errors += _edit_delete_edges(edges, edit.get("delete_edges", []), applied)
        phase_errors += _edit_delete_nodes(
            nodes, edges, edit.get("delete_nodes", []), applied
        )
        phase_errors += _edit_add_nodes(nodes, edit.get("add_nodes", []), applied)
        phase_errors += _edit_add_edges(
            nodes, edges, edit.get("add_edges", []), applied
        )

        if phase_errors:
            return EditReport(
                valid=False, errors=tuple(phase_errors), applied=applied, graph=None
            )

        structure_errors = _validate_structure(nodes, edges)
        if structure_errors:
            return EditReport(
                valid=False, errors=tuple(structure_errors), applied=applied, graph=None
            )

        return EditReport(
            valid=True,
            errors=(),
            applied=applied,
            graph=ProceduralGraph(nodes, edges, self._notes),
        )


class ProceduralGraphStore:
    """A directory of ``<name>.json`` procedural graphs."""

    def __init__(self, storage_dir: Path) -> None:
        """Bind to *storage_dir*; the directory is created lazily on first save."""
        self._storage_dir = Path(storage_dir)

    def list_names(self) -> list[str]:
        """Sorted stems of ``*.json`` files; ``[]`` if the directory does not exist."""
        if not self._storage_dir.exists():
            return []
        return sorted(p.stem for p in self._storage_dir.glob("*.json"))

    def path_for(self, name: str) -> Path:
        """``<storage_dir>/<name>.json``. Raises ``ValueError`` if *name*
        fails :data:`NAME_PATTERN` -- checked before any filesystem access.
        """
        if not NAME_PATTERN.match(name):
            raise ValueError(f"invalid procedural graph name: {name!r}")
        return self._storage_dir / f"{name}.json"

    def load(self, name: str) -> ProceduralGraph:
        """Read, validate, and build.

        Raises ``ValueError`` for a bad *name*, ``FileNotFoundError`` for a
        missing file, ``json.JSONDecodeError`` (a ``ValueError`` subclass)
        for malformed JSON, or :class:`ProceduralGraphError` for a
        well-formed but invalid document.
        """
        path = self.path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"no such procedural graph: {name!r}")
        doc = json.loads(path.read_text(encoding="utf-8"))
        return ProceduralGraph.from_document(doc)

    def save(self, name: str, graph: ProceduralGraph) -> Path:
        """Atomically write ``graph.to_document(name)``."""
        path = self.path_for(name)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, graph.to_document(name))
        return path

    def import_seed(
        self, path: Path, name: str | None = None, *, force: bool = False
    ) -> str:
        """Validate an external seed document and store it under *name*
        (defaulting to the document's own ``"name"`` field).

        Raises :class:`ProceduralGraphError` for an invalid seed (nothing is
        written), ``ValueError`` for an invalid *name* override, and
        ``FileExistsError`` if *name* already exists and ``force`` is
        ``False``.
        """
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        graph = ProceduralGraph.from_document(doc)
        assert isinstance(doc, dict)
        stored_name = name if name is not None else doc["name"]
        if not NAME_PATTERN.match(stored_name):
            raise ValueError(f"invalid procedural graph name: {stored_name!r}")
        dest = self.path_for(stored_name)
        if dest.exists() and not force:
            raise FileExistsError(
                f"procedural graph already exists: {stored_name!r} (use force=True to overwrite)"
            )
        self.save(stored_name, graph)
        return stored_name
