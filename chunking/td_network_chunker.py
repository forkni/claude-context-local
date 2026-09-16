"""Chunk TouchDesigner ``.tdgraph.json`` network snapshots (ADR-0062, Part C).

``TDNetworkChunker`` is a pseudo-language chunker: unlike ``TreeSitterChunker`` it
builds :class:`~chunking.python_ast_chunker.CodeChunk` objects directly from a JSON
network snapshot (operators, wiring, docking, the ``td`` class hierarchy) instead of
parsing source text with a grammar. Modeled on
``chunking/file_summarizer.py``'s ``_build_file_summary`` -- the only other CodeChunk
producer in the codebase that hand-builds chunks (and a hand-built chunk_id) rather
than converting ``TreeSitterChunk`` output.

Only reached when ``chunking.language_registry.td_network_indexing_enabled()`` is
True (checked by the caller, ``MultiLanguageChunker.chunk_file``) -- this module has
no gate of its own.

Schema: derived directly from ``TD_Glossary_tox``'s
``Extensions/OperatorGlossary/dat_NetworkGraphExt.py`` exporter, not invented. See
``docs/adr/0062-td-network-indexing.md``, ``docs/adr/0072-td-edge-type-vocabulary-is-
declared-and-drift-tested.md``, and
``tests/fixtures/td_network/Test_network.tdgraph.json`` for the authoritative shape:
``schema_version`` (int), ``target``, ``nodes`` (``stub: true`` for out-of-subtree
placeholders), ``edges`` (13 types -- see ``TD_GRAPH_EDGE_TYPES`` below),
``classes`` (``{mro, signature}`` per class actually instantiated by a node -- *not*
every class in ``mro``), ``scripts``, ``tag_groups``, ``node_line_spans``,
``edge_types``, ``stats``.

Anyone comparing ``edge_types``/``stats`` against what this chunker actually
emits must account for the divergence: ``shared_tag`` is emitted in *both*
directions (see ``RelationshipType.SHARES_TAG`` below -- halve it to compare),
``script_ref`` edges with a null ``dst`` are dropped rather than emitted, an
extra ``scripted_by`` edge is synthesized per synced script file, and
``inherits``/``instance_of`` edges are synthesized from ``classes``/``nodes``
and have no entry in ``edge_types`` at all. The network chunk's own operator/
relationship counts are therefore reported as the *exporter's* numbers, not
recomputed -- see ``_build_network_chunk``.

Emits three chunk_type kinds, all ``language="td_network"``, ids built exclusively
via ``search/chunk_id.py::build()`` (never hand-rolled) and always carrying a real
line span **into the ``.tdgraph.json`` file itself** (see ``_json_element_spans``):
an operator's span is the line range of its node object, a class's span is the
line range of its ``classes`` entry, and the network chunk spans the whole file.
The exporter's ``node_line_spans`` key is deliberately *ignored* -- it holds the
script line count of each Python DAT (``{"start_line": 1, "end_line": N}``), not a
position in the snapshot, so it cannot drive ``Read``-able spans.

- ``operator``  -- one per real (non-stub) node *other than the network root*,
  named by its path relative to the network target (``"glsl1"``, ``"comp1/box1"``).
  The exporter emits the target COMP itself as a depth-0 node; it is folded into
  the ``network`` chunk instead of getting an operator chunk (whose name would
  otherwise be empty -- ``build()`` drops a falsy name, yielding an unparseable id).
- ``class``     -- one per entry in the snapshot's ``classes`` table, named by class
  name.
- ``network``   -- one per file, a synthetic summary of the whole snapshot (same
  role as ``file_summarizer``'s ``module`` chunk); also the edge endpoint for every
  edge that touches the network root (contains/dock/shared_tag/...).

Relationship edges are built as ``RelationshipEdge`` objects directly (not through
``chunking.relationships.edge_specs.materialize_relationship_edges`` -- there is no
AST for a JSON snapshot to run through). An edge whose target isn't itself chunked
here (a stub node, or a class outside the local ``classes`` table, e.g. an
abstract base like ``TOP``/``OP`` that no node instantiates directly) still gets a
chunk_id-shaped ``target_name``; ``graph_storage`` creates a phantom node for it on
first edge, exactly as it does for an edge to an unindexed Python symbol.
"""

from __future__ import annotations

import bisect
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from chunking.python_ast_chunker import CodeChunk
from chunking.relationships.relationship_types import RelationshipEdge, RelationshipType
from search.chunk_id import ChunkId
from search.chunk_id import build as build_chunk_id
from utils.path_utils import normalize_path


logger = logging.getLogger(__name__)

# Every edge this chunker emits comes straight off a live TD network snapshot --
# there is no fuzzy resolution step, so there is nothing to grade: an edge either
# reflects a fact the exporter wrote down, or (script_ref with a null dst) it is
# dropped and counted instead of emitted. confidence=1.0 is the honest value for
# every edge that IS emitted. The tradeoff is lossy: a 1.0 JSON-lookup edge is now
# indistinguishable from any other 1.0 edge in this codebase (e.g. a type-inferred
# one) -- provenance lives in metadata["resolver_source"] below instead.
_RESOLVER_SOURCE = "td_live"

# Edge types whose RelationshipEdge is a straightforward literal src->dst mapping
# (source_id=chunk(src), target_name=chunk(dst)) to one RelationshipType, with a
# fixed set of metadata keys pulled off the edge dict. "dock" is deliberately
# excluded -- its RelationshipEdge direction is the *reverse* of the edge's own
# src/dst (see _add_edges_for_graph below) -- and "contains"/"script_ref"/
# "shared_tag"/"replicator" are excluded because they need extra per-edge logic
# (network-vs-nested source, dst-null dropping, dual-direction emission).
_SIMPLE_EDGE_MAP: dict[str, tuple[RelationshipType, tuple[str, ...]]] = {
    "par_ref": (RelationshipType.REFERENCES_OP, ("par",)),
    "bind": (RelationshipType.BINDS_TO, ("par",)),
    "export": (RelationshipType.EXPORTS_TO, ("par",)),
    "shortcut_ref": (RelationshipType.REFERENCES_OP, ("shortcut",)),
    # host op -> the DAT that scripts it (par="callbacks"|"op"|..., via="callbacks"|"execute")
    "scripted_by": (RelationshipType.SCRIPTED_BY, ("par", "via")),
    # clone COMP -> its Clone Master (ADR-0072). No extra metadata keys: the
    # producer's clone edge shape is exactly {"type": "clone", "src", "dst"}
    # (dat_NetworkGraphExt._emit_clone_edge) -- no "par" field like the other
    # simple types. The master may be a stub node (out-of-scope utility op,
    # e.g. the built-in annotateCOMP's master); chunk_id_for already resolves
    # that to a phantom node, same as any other unindexed target.
    "clone": (RelationshipType.CLONES, ()),
}

# Edge types handled by an explicit ``if``/``elif`` branch in
# _build_relationship_edges below rather than through _SIMPLE_EDGE_MAP --
# "contains" (network-vs-nested source), "wire"/"comp_wire" (dst_index/carries
# metadata), "dock" (reversed direction), "script_ref" (dst-null dropping),
# "replicator", and "shared_tag" (dual-direction emission). Kept as a literal
# constant next to the dispatch it describes so TD_GRAPH_EDGE_TYPE_SET's
# handled-set test (tests/unit/chunking/test_td_network_edge_vocabulary.py)
# doesn't need a second, independently-maintained copy of this list living in
# the test file -- if a branch is added or removed here, this constant must
# move with it, in the same diff.
_EXPLICIT_BRANCH_EDGE_TYPES: frozenset[str] = frozenset(
    {"contains", "wire", "comp_wire", "dock", "script_ref", "replicator", "shared_tag"}
)

# The full producer edge-type vocabulary, in the same canonical order as
# TD_Glossary_tox's ``Extensions/OperatorGlossary/tdgraph_contract.py``
# ``GRAPH_EDGE_TYPES`` (which drives every ``edge_types[]`` histogram a real
# export writes -- see that module's docstring and
# ``tests/test_tdgraph_edge_types_contract.py`` in that repo). The two
# vocabularies must change in lockstep: adding a 14th producer edge type
# without adding it here is exactly the drift this constant exists to catch
# (ADR-0072). Order is asserted, not just membership -- see
# test_td_network_edge_vocabulary.py.
TD_GRAPH_EDGE_TYPES: tuple[str, ...] = (
    "contains",
    "wire",
    "comp_wire",
    "dock",
    "scripted_by",
    "par_ref",
    "bind",
    "export",
    "clone",
    "script_ref",
    "shortcut_ref",
    "replicator",
    "shared_tag",
)
TD_GRAPH_EDGE_TYPE_SET: frozenset[str] = frozenset(TD_GRAPH_EDGE_TYPES)

# The ``schema_version`` this chunker was written against, mirroring
# TD_Glossary_tox's ``tdgraph_contract.GRAPH_SCHEMA_VERSION``. That module's
# docstring defines the contract: additive fields never bump it; a removal,
# rename, or type change does. Checked (not enforced) at ingestion time --
# see chunk_file() -- so an export from a newer/older producer schema is
# ingested with a loud warning instead of silently, rather than rejected.
TD_GRAPH_SCHEMA_VERSION = 1


def _resolve_script_file(
    script_file: str, file_path: str, relative_path: str
) -> str | None:
    """Map a node's ``script.file`` to a root-relative ``.py`` path, or None.

    The exporter copies TD's ``par.file`` verbatim, which the sync tool
    (``dat_DatSyncExt._convert_to_relative_path``) writes as a *project*-relative
    forward-slash path such as ``Scripts/X__td.py``. The snapshot itself usually
    sits one level down (``Graph/X.tdgraph.json``), so two candidates are tried
    against the index root (``file_path`` minus ``relative_path``): the path
    re-rooted next to the snapshot's parent folder, then the path as written.
    The first that exists on disk wins; when neither does the as-written form
    is returned anyway so the edge still lands on a (phantom) module node.

    Anything that escapes the root -- an absolute path, a drive prefix, or a
    ``..`` segment -- is rejected with a DEBUG log and no edge is emitted.
    """
    cleaned = normalize_path(str(script_file)).strip()
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    if not cleaned:
        return None
    parts = cleaned.split("/")
    if (
        Path(cleaned).is_absolute()
        or cleaned.startswith("/")
        or (len(parts[0]) == 2 and parts[0][1] == ":")
        or ".." in parts
    ):
        logger.debug(
            "td_network: ignoring script.file %r (absolute or escapes the "
            "index root) in %s",
            script_file,
            relative_path,
        )
        return None

    rel_norm = normalize_path(relative_path)
    file_norm = normalize_path(str(file_path))
    if file_norm.endswith(rel_norm):
        root = Path(file_norm[: len(file_norm) - len(rel_norm)] or ".")
    else:
        root = Path(file_norm).parent

    rerooted = Path(rel_norm).parent.parent / cleaned
    candidates = [normalize_path(str(rerooted)), cleaned]
    for cand in candidates:
        while cand.startswith("./"):
            cand = cand[2:]
        if (root / cand).exists():
            return cand
    return cleaned


class TDNetworkChunker:
    """Builds operator/class/network CodeChunks from one ``.tdgraph.json`` file."""

    def __init__(self, root_path: str | None = None) -> None:
        self.root_path = root_path

    def chunk_file(
        self, file_path: str, relative_path: str | None = None
    ) -> list[CodeChunk]:
        """Chunk one ``.tdgraph.json`` file. Returns ``[]`` on any read/parse failure.

        Args:
            file_path: Path to the snapshot file (absolute or as given by the caller;
                stored verbatim on every produced ``CodeChunk.file_path``).
            relative_path: Path relative to the project root, used to build chunk_ids.
                Computed from ``self.root_path`` when omitted (matches
                ``MultiLanguageChunker``'s own relative_path convention).
        """
        try:
            with open(file_path, encoding="utf-8") as fh:
                text = fh.read()
            graph: dict[str, Any] = json.loads(text)
        except OSError as e:
            logger.warning("Could not read %s: %s", file_path, e)
            return []
        except json.JSONDecodeError as e:
            logger.warning("Malformed .tdgraph.json %s: %s", file_path, e)
            return []
        if not isinstance(graph, dict):
            logger.warning(
                "Malformed .tdgraph.json %s: top level is not an object", file_path
            )
            return []

        if relative_path is None:
            relative_path = self._compute_relative_path(file_path)

        schema_version = graph.get("schema_version")
        if schema_version != TD_GRAPH_SCHEMA_VERSION:
            logger.warning(
                "%s declares schema_version=%r, this chunker was written "
                "against %r -- ingesting anyway, but the shape may have "
                "changed (see TD_Glossary_tox's tdgraph_contract.py)",
                file_path,
                schema_version,
                TD_GRAPH_SCHEMA_VERSION,
            )

        node_spans, class_spans = _json_element_spans(text)
        total_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        return self._build_chunks(
            graph, file_path, relative_path, node_spans, class_spans, total_lines
        )

    def _compute_relative_path(self, file_path: str) -> str:
        path = Path(file_path)
        if self.root_path:
            try:
                return str(path.relative_to(self.root_path))
            except ValueError:
                pass
        return str(path)

    # ------------------------------------------------------------------
    # Op-path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _relative_op_path(node_id: str, target: str) -> str:
        """Op path used as the chunk name, relative to the target network.

        Nodes under the target subtree get a path relative to it (``"glsl1"``,
        ``"comp1/box1"``); nodes outside it -- an export/bind target that lives
        elsewhere in the project, or a ``stub`` node the exporter couldn't fully
        resolve -- keep their absolute path minus the leading slash, so the name
        stays a stable, human-readable chunk_id component either way. The target
        itself maps to its own leaf name (``"Test_network"``), never ``""`` -- it is
        only used for display here (the root never gets an operator chunk; see
        ``_build_chunks``).
        """
        if node_id == target:
            return Path(target).name or target
        prefix = target.rstrip("/") + "/"
        if node_id.startswith(prefix):
            return node_id[len(prefix) :]
        return node_id.lstrip("/")

    # ------------------------------------------------------------------
    # Chunk assembly
    # ------------------------------------------------------------------

    def _build_chunks(
        self,
        graph: dict[str, Any],
        file_path: str,
        relative_path: str,
        node_spans: dict[str, tuple[int, int]] | None = None,
        class_spans: dict[str, tuple[int, int]] | None = None,
        total_lines: int = 0,
    ) -> list[CodeChunk]:
        target = graph.get("target", "")
        nodes = graph.get("nodes") or []
        edges = graph.get("edges") or []
        classes = graph.get("classes") or {}
        node_spans = node_spans or {}
        class_spans = class_spans or {}
        # NOTE: graph["node_line_spans"] is intentionally unused -- see module docstring.

        # The exporter emits the target COMP itself as a depth-0 real node. It is
        # the network, not an operator *in* the network: skip it here and route
        # every edge touching it to the network chunk (chunk_id_for below).
        root_node = next((n for n in nodes if n.get("id") == target), None)
        real_nodes = [n for n in nodes if not n.get("stub") and n.get("id") != target]

        # ---- Pass 1: assign chunk ids (needed before any edge can be built) ----
        op_chunk_id: dict[str, str] = {}
        op_span: dict[str, tuple[int, int]] = {}
        for n in real_nodes:
            node_id = n["id"]
            op_path = self._relative_op_path(node_id, target)
            start, end = node_spans.get(node_id, (0, 0))
            op_span[node_id] = (start, end)
            op_chunk_id[node_id] = build_chunk_id(
                relative_path, start, end, "operator", op_path
            )

        network_name = Path(target).name or (target or Path(relative_path).stem)
        network_span = (1, total_lines) if total_lines > 0 else (0, 0)
        network_chunk_id = build_chunk_id(
            relative_path, network_span[0], network_span[1], "network", network_name
        )

        class_chunk_id = {
            cname: build_chunk_id(
                relative_path, *class_spans.get(cname, (0, 0)), "class", cname
            )
            for cname in classes
        }

        def chunk_id_for(node_id: str) -> str:
            """Chunk_id for any node id, real or not.

            The network root resolves to the network chunk (it has no operator
            chunk of its own). Otherwise gives a stable RelationshipEdge
            target_name even for nodes this file never builds an operator chunk
            for (a stub, or a reference that lives outside the walked subtree) --
            graph_storage creates a phantom node for it on first edge, matching
            correction #8 in ADR-0062.
            """
            if node_id == target:
                return network_chunk_id
            if node_id in op_chunk_id:
                return op_chunk_id[node_id]
            return build_chunk_id(
                relative_path, 0, 0, "operator", self._relative_op_path(node_id, target)
            )

        def class_chunk_for(cname: str) -> str:
            if cname in class_chunk_id:
                return class_chunk_id[cname]
            # Abstract base with no node directly instantiating it (e.g. "TOP",
            # "OP") -- phantom target, same rationale as chunk_id_for above.
            return build_chunk_id(relative_path, 0, 0, "class", cname)

        # ---- Pass 2: bucket edges per source node for content-building ----
        out_edges: dict[str, list[dict]] = defaultdict(list)
        in_edges: dict[str, list[dict]] = defaultdict(list)
        for e in edges:
            out_edges[e.get("src", "")].append(e)
            if e.get("dst"):
                in_edges[e["dst"]].append(e)

        relationships_by_source, unresolved_script_refs, phantom_dst_count = (
            self._build_relationship_edges(
                graph,
                edges,
                classes,
                chunk_id_for,
                class_chunk_for,
                network_chunk_id,
                target,
            )
        )
        if unresolved_script_refs:
            # Surfaced as prose on the network chunk's own body too (see
            # _build_network_chunk below). A script_ref with a null dst is
            # contract-conformant, not a defect -- it means the exporter
            # itself couldn't resolve a DAT's callback to a project file
            # (op_call target outside the snapshot, or an unmatched
            # shortcut). DEBUG, not WARNING: nothing here is actionable, and
            # the count is already visible on the network chunk.
            logger.debug(
                "%s: %d unresolved script reference(s) in network %r",
                file_path,
                unresolved_script_refs,
                target,
            )
        self._add_script_file_edges(
            real_nodes, op_chunk_id, file_path, relative_path, relationships_by_source
        )

        # ---- Pass 3: build CodeChunks --------------------------------------
        folder_structure = list(Path(relative_path).parent.parts)
        if folder_structure == ["."]:
            folder_structure = []

        chunks: list[CodeChunk] = []
        for n in real_nodes:
            node_id = n["id"]
            start, end = op_span[node_id]
            chunks.append(
                self._build_operator_chunk(
                    n,
                    target,
                    file_path,
                    relative_path,
                    folder_structure,
                    op_chunk_id[node_id],
                    start,
                    end,
                    out_edges.get(node_id, []),
                    in_edges.get(node_id, []),
                    relationships_by_source.get(op_chunk_id[node_id]),
                )
            )

        for cname, cdata in classes.items():
            instances = sorted(
                self._relative_op_path(n["id"], target)
                for n in real_nodes
                if n.get("class_name") == cname
            )
            chunks.append(
                self._build_class_chunk(
                    cname,
                    cdata,
                    instances,
                    file_path,
                    relative_path,
                    folder_structure,
                    class_chunk_id[cname],
                    class_spans.get(cname, (0, 0)),
                    relationships_by_source.get(class_chunk_id[cname]),
                )
            )

        chunks.append(
            self._build_network_chunk(
                graph,
                network_name,
                network_chunk_id,
                network_span,
                root_node,
                real_nodes,
                file_path,
                relative_path,
                folder_structure,
                unresolved_script_refs,
                phantom_dst_count,
                relationships_by_source.get(network_chunk_id),
            )
        )

        return self._drop_nameless(chunks, file_path)

    @staticmethod
    def _drop_nameless(chunks: list[CodeChunk], file_path: str) -> list[CodeChunk]:
        """Guard: never emit a chunk whose id lost its ``:name`` segment.

        ``build()`` silently omits the suffix for a falsy name, which produced an
        unparseable ``<file>:0-0:operator`` id for the network root before the
        root was routed to the network chunk. Any recurrence is a chunker bug --
        log it loudly and drop the chunk rather than poison the index.
        """
        kept: list[CodeChunk] = []
        for c in chunks:
            parsed = ChunkId.parse(c.chunk_id) if c.chunk_id is not None else None
            if parsed is None or not parsed.name:
                logger.error(
                    "TDNetworkChunker produced a nameless chunk_id %r in %s "
                    "(chunk_type=%s, name=%r); dropped",
                    c.chunk_id,
                    file_path,
                    c.chunk_type,
                    c.name,
                )
                continue
            kept.append(c)
        return kept

    # ------------------------------------------------------------------
    # Relationship-edge construction
    # ------------------------------------------------------------------

    @staticmethod
    def _add_script_file_edges(
        real_nodes: list[dict[str, Any]],
        op_chunk_id: dict[str, str],
        file_path: str,
        relative_path: str,
        by_source: dict[str, list[RelationshipEdge]],
    ) -> int:
        """Join each scripted DAT to its synced ``.py`` (ADR-0062 C6).

        For every real node carrying ``script.file`` emit a ``SCRIPTED_BY`` edge
        from the *operator chunk* to the module-summary chunk id of that file
        (``<rel>.py:0-0:module:<stem>``, the id ``file_summarizer`` builds).
        Module chunks never become graph nodes, so ``GraphIntegration``
        retargets the edge to the file's first indexed chunk at build time
        (``metadata["retargeted"]``); when the file is not in the batch the id
        stays a phantom node, exactly like any other unindexed target.

        The DAT is the source because it is the node that owns the ``file``
        parameter -- the ``.py`` on disk knows nothing about which DAT loads it.
        Returns the number of edges emitted.
        """
        emitted = 0
        for n in real_nodes:
            script = n.get("script") or {}
            script_file = script.get("file")
            if not script_file:
                continue
            rel_py = _resolve_script_file(script_file, file_path, relative_path)
            if rel_py is None:
                continue
            source_id = op_chunk_id[n["id"]]
            target_id = build_chunk_id(rel_py, 0, 0, "module", Path(rel_py).stem)
            meta = {
                "td_edge_type": "scripted_by",
                "via": "file",
                "file": rel_py,
                "synced": bool(script.get("synced")),
                "resolver_source": _RESOLVER_SOURCE,
            }
            # Sync Manifest join (schema optional -- omitted by older exports):
            # "this .py's content on disk still matches the DAT's contents",
            # independent of "synced" (which means "the sync tool has run").
            if "file_matches_dat" in script:
                meta["file_matches_dat"] = bool(script["file_matches_dat"])
            by_source[source_id].append(
                RelationshipEdge(
                    source_id=source_id,
                    target_name=target_id,
                    relationship_type=RelationshipType.SCRIPTED_BY,
                    line_number=0,
                    confidence=1.0,
                    metadata=meta,
                )
            )
            emitted += 1
        return emitted

    def _build_relationship_edges(
        self,
        graph: dict[str, Any],
        edges: list[dict],
        classes: dict[str, Any],
        chunk_id_for,
        class_chunk_for,
        network_chunk_id: str,
        target: str,
    ) -> tuple[dict[str, list[RelationshipEdge]], int, int]:
        """Build every RelationshipEdge, grouped by source chunk_id.

        Returns (relationships_by_source, unresolved_script_ref_count,
        phantom_dst_count). Both counts are surfaced on the network chunk's
        content per ADR-0062 ("dst: null edges are dropped and counted on the
        network chunk") and ADR-0073 (phantom-target dst warned once per
        unique (etype, dst) pair, not once per edge -- a fan-in target hit by
        many edges would otherwise flood the log with one identical warning
        per edge).
        """
        scripts = graph.get("scripts") or {}
        scripts_index = {
            (dat_path, ref.get("kind"), ref.get("line"), ref.get("col")): ref
            for dat_path, refs in scripts.items()
            for ref in refs
        }
        # Every non-null dst is resolved via chunk_id_for, which never raises --
        # an id absent from the snapshot's own node list silently becomes a
        # phantom node (same machinery used for a legitimate out-of-scope
        # target, e.g. a clone edge to a stub master). That's indistinguishable
        # from contract drift unless checked here. Includes stubs and the
        # network root (both are real entries in "nodes") so neither
        # false-positives.
        known_node_ids = {n["id"] for n in graph.get("nodes") or [] if n.get("id")}

        by_source: dict[str, list[RelationshipEdge]] = defaultdict(list)

        def add(
            source_id: str,
            target_id: str,
            rtype: RelationshipType,
            line: int,
            meta: dict,
        ) -> None:
            by_source[source_id].append(
                RelationshipEdge(
                    source_id=source_id,
                    target_name=target_id,
                    relationship_type=rtype,
                    line_number=line or 0,
                    confidence=1.0,
                    metadata=meta,
                )
            )

        unresolved_script_refs = 0
        # De-dup key is (etype, dst), not (src, etype, dst): the point is to
        # warn once per distinct phantom target, not once per edge reaching
        # it -- a single mistyped/renamed dst can be the target of many
        # edges (e.g. every op in a group referencing a deleted shortcut),
        # and one warning per edge would drown the log without adding
        # information the reader doesn't already have after the first.
        phantom_dst_seen: set[tuple[str, str]] = set()

        for e in edges:
            etype = e.get("type")
            src, dst = e.get("src"), e.get("dst")

            # A null dst is only meaningful for "script_ref" (an unresolved
            # op_call target -- handled explicitly below, dropped and counted
            # into unresolved_script_refs). No real export has ever emitted a
            # null dst on any other type (verified against all TD_Glossary_tox
            # exports and the schema's other edge shapes), but the schema does
            # not forbid it, and chunk_id_for(None) -> _relative_op_path(None,
            # target) raises AttributeError, which multi_language_chunker's
            # blanket except then turns into a silent whole-file chunk loss.
            # Guard here instead of trusting that invariant to hold forever.
            if dst is None and etype != "script_ref":
                logger.warning(
                    "td_network: edge type %r has a null dst (only script_ref "
                    "is expected to) in network %r; skipping edge src=%r",
                    etype,
                    target,
                    src,
                )
                continue

            # A non-null dst that names no node in this snapshot is the
            # exporter asserting a relationship to something that isn't
            # there. Left unchecked, chunk_id_for() synthesizes a phantom
            # node for it -- silently, and indistinguishably from the
            # legitimate out-of-scope case (a stub node, which *is* in
            # known_node_ids). Warn instead of dropping: the edge is still
            # built (the phantom node keeps the relationship traversable),
            # but the drift is now visible.
            if dst is not None and dst not in known_node_ids:
                phantom_key = (str(etype), str(dst))
                if phantom_key not in phantom_dst_seen:
                    phantom_dst_seen.add(phantom_key)
                    logger.warning(
                        "td_network: edge type %r has dst %r that is not a "
                        "node in network %r; a phantom node will be "
                        "synthesized for it (src=%r, first occurrence)",
                        etype,
                        dst,
                        target,
                        src,
                    )

            if etype == "contains":
                # Root-sourced contains edges attach to the network chunk (the
                # network root is never chunked as an "operator" -- chunk_id_for
                # maps it to network_chunk_id); nested ones attach to the parent
                # operator chunk.
                add(
                    chunk_id_for(src),
                    chunk_id_for(dst),
                    RelationshipType.CONTAINS,
                    0,
                    {"td_edge_type": "contains", "resolver_source": _RESOLVER_SOURCE},
                )

            elif etype in ("wire", "comp_wire"):
                meta = {"td_edge_type": etype, "resolver_source": _RESOLVER_SOURCE}
                if "dst_index" in e:
                    meta["dst_index"] = e["dst_index"]
                if "carries" in e:
                    meta["carries"] = e["carries"]
                add(
                    chunk_id_for(src),
                    chunk_id_for(dst),
                    RelationshipType.WIRES_TO,
                    0,
                    meta,
                )

            elif etype == "dock":
                # The edge is {src: host, dst: docked-child} -- dst.rel.docked_to
                # == src (verified against TD_Glossary_tox's _apply_relationships).
                # DOCKED_TO reads "source docked_to target", so the RelationshipEdge
                # direction is the *reverse* of the edge's own src/dst: the child
                # is the source, the host is the target.
                add(
                    chunk_id_for(dst),
                    chunk_id_for(src),
                    RelationshipType.DOCKED_TO,
                    0,
                    {"td_edge_type": "dock", "resolver_source": _RESOLVER_SOURCE},
                )

            elif etype == "script_ref":
                if dst is None:
                    # Unresolved (op_call target outside the snapshot, or a
                    # shortcut the queued-resolution pass never matched) --
                    # dropped per ADR-0062, counted on the network chunk instead.
                    unresolved_script_refs += 1
                    continue
                ref = scripts_index.get(
                    (src, e.get("kind"), e.get("line"), e.get("col"))
                )
                meta = {
                    "td_edge_type": "script_ref",
                    "resolver_source": _RESOLVER_SOURCE,
                    "resolved": True,
                    "kind": e.get("kind"),
                    "target_op_path": e.get("target"),
                }
                if ref is not None:
                    if ref.get("via"):
                        meta["via"] = ref["via"]
                    if ref.get("symbol"):
                        meta["symbol"] = ref["symbol"]
                add(
                    chunk_id_for(src),
                    chunk_id_for(dst),
                    RelationshipType.REFERENCES_OP,
                    e.get("line", 0),
                    meta,
                )

            elif etype == "replicator":
                add(
                    chunk_id_for(src),
                    chunk_id_for(dst),
                    RelationshipType.INSTANTIATES,
                    0,
                    {"td_edge_type": "replicator", "resolver_source": _RESOLVER_SOURCE},
                )

            elif etype == "shared_tag":
                meta = {
                    "td_edge_type": "shared_tag",
                    "resolver_source": _RESOLVER_SOURCE,
                    "tag": e.get("tag"),
                }
                # Symmetric relationship -- emit both directions (ADR-0062 C5 spec).
                add(
                    chunk_id_for(src),
                    chunk_id_for(dst),
                    RelationshipType.SHARES_TAG,
                    0,
                    dict(meta),
                )
                add(
                    chunk_id_for(dst),
                    chunk_id_for(src),
                    RelationshipType.SHARES_TAG,
                    0,
                    dict(meta),
                )

            elif etype in _SIMPLE_EDGE_MAP:
                rtype, meta_keys = _SIMPLE_EDGE_MAP[etype]
                meta = {"td_edge_type": etype, "resolver_source": _RESOLVER_SOURCE}
                for key in meta_keys:
                    if e.get(key) is not None:
                        meta[key] = e[key]
                add(chunk_id_for(src), chunk_id_for(dst), rtype, 0, meta)

            else:
                # A silently-dropped edge type at DEBUG is what let "clone" sit
                # unhandled for a full release (ADR-0072) -- WARNING catches it
                # in the field; the vocabulary-drift test
                # (test_td_network_edge_vocabulary.py) catches it in CI.
                logger.warning(
                    "Unrecognized .tdgraph.json edge type %r, skipped", etype
                )

        # Class hierarchy: each class inherits from the first entry after itself
        # in its own mro (mro[0] is always the class itself).
        for cname, cdata in classes.items():
            mro = cdata.get("mro") or []
            if len(mro) > 1:
                add(
                    class_chunk_for(cname),
                    class_chunk_for(mro[1]),
                    RelationshipType.INHERITS,
                    0,
                    {"td_edge_type": "inherits", "resolver_source": _RESOLVER_SOURCE},
                )

        # Operator -> class: deterministic get_by_chunk_id resolution (INSTANTIATES),
        # not USES_TYPE (correction #9, ADR-0062 -- USES_TYPE resolves via an
        # unreliable k=4 semantic search on short class names like "TOP").
        for n in graph.get("nodes") or []:
            if n.get("stub"):
                continue
            cname = n.get("class_name")
            if cname:
                add(
                    chunk_id_for(n["id"]),
                    class_chunk_for(cname),
                    RelationshipType.INSTANTIATES,
                    0,
                    {
                        "td_edge_type": "instance_of",
                        "resolver_source": _RESOLVER_SOURCE,
                    },
                )

        return by_source, unresolved_script_refs, len(phantom_dst_seen)

    # ------------------------------------------------------------------
    # Individual chunk builders
    # ------------------------------------------------------------------

    def _build_operator_chunk(
        self,
        node: dict[str, Any],
        target: str,
        file_path: str,
        relative_path: str,
        folder_structure: list[str],
        chunk_id: str,
        start_line: int,
        end_line: int,
        node_out_edges: list[dict],
        node_in_edges: list[dict],
        relationships: list[RelationshipEdge] | None,
    ) -> CodeChunk:
        node_id = node["id"]
        op_path = self._relative_op_path(node_id, target)
        family = node.get("family", "")
        op_type = node.get("op_type") or node.get("class_name", "")
        mro = node.get("mro") or []
        signature = node.get("signature")
        params = node.get("params") or {}
        user_tags = node.get("tags") or []
        shortcuts = node.get("shortcuts") or []
        rel = node.get("rel") or {}

        lines = [f"{node.get('name', op_path)} — {op_type} ({family}) in {target}"]
        if len(mro) > 1:
            lines.append("class " + " < ".join(mro))
        if signature:
            lines.append(f"signature: {signature}")

        wires_in = [e for e in node_in_edges if e.get("type") in ("wire", "comp_wire")]
        wires_out = [
            e for e in node_out_edges if e.get("type") in ("wire", "comp_wire")
        ]
        if wires_in:
            names = ", ".join(
                self._relative_op_path(e["src"], target) for e in wires_in
            )
            lines.append(f"inputs: {names}")
        if wires_out:
            names = ", ".join(
                self._relative_op_path(e["dst"], target) for e in wires_out
            )
            lines.append(f"outputs: {names}")

        if rel.get("docked_to"):
            lines.append(
                f"docked to: {self._relative_op_path(rel['docked_to'], target)}"
            )
        # dock edges are {src: host, dst: docked-child} (see _build_relationship_edges),
        # so a node's docked children are the dock edges where it is the *source*.
        docked_children = [e for e in node_out_edges if e.get("type") == "dock"]
        if docked_children:
            names = ", ".join(
                self._relative_op_path(e["dst"], target) for e in docked_children
            )
            lines.append(f"hosts docked: {names}")

        if params:
            param_str = ", ".join(f"{k}={v!r}" for k, v in params.items())
            lines.append(f"params: {param_str}")

        ref_edges = [
            e
            for e in node_out_edges
            if e.get("type")
            in ("par_ref", "bind", "export", "script_ref", "shortcut_ref")
        ]
        if ref_edges:
            refs = []
            for e in ref_edges:
                dst = e.get("dst")
                refs.append(
                    self._relative_op_path(dst, target)
                    if dst
                    else (e.get("target") or "?")
                )
            lines.append(f"references: {', '.join(refs)}")

        # Reverse references: this node is the *target* of another node's
        # parameter/bind/export/script/shortcut reference. Without this line an
        # operator that is only ever pointed at (a pixel-shader DAT, a bind
        # master) has no text linking it to its users (ADR-0062 D2 finding).
        referenced_by = [
            e
            for e in node_in_edges
            if e.get("type")
            in ("par_ref", "bind", "export", "script_ref", "shortcut_ref")
        ]
        if referenced_by:
            names = sorted(
                {self._relative_op_path(e["src"], target) for e in referenced_by}
            )
            lines.append(f"referenced by: {', '.join(names)}")

        # scripted_by edges are {src: scripted host, dst: DAT holding its code}.
        scripted_by = [e for e in node_out_edges if e.get("type") == "scripted_by"]
        if scripted_by:
            parts = []
            for e in scripted_by:
                name = self._relative_op_path(e["dst"], target)
                via = e.get("via") or e.get("par")
                parts.append(f"{name} ({via})" if via else name)
            lines.append(f"scripted by: {', '.join(parts)}")
        scripts_for = [e for e in node_in_edges if e.get("type") == "scripted_by"]
        if scripts_for:
            parts = []
            for e in scripts_for:
                name = self._relative_op_path(e["src"], target)
                via = e.get("via") or e.get("par")
                parts.append(f"{name} ({via})" if via else name)
            lines.append(f"scripts: {', '.join(parts)}")

        if shortcuts:
            sc = ", ".join(f"{s.get('kind')}:{s.get('name')}" for s in shortcuts)
            lines.append(f"shortcuts: {sc}")

        if rel.get("replicator"):
            lines.append(
                f"replicated by: {self._relative_op_path(rel['replicator'], target)}"
            )

        if user_tags:
            lines.append(f"tags: {', '.join(user_tags)}")

        content = "\n".join(lines)

        tags: list[str] = []
        if family:
            tags.append(family.lower())
        if op_type and op_type not in tags:
            tags.append(op_type)
        for t in user_tags:
            if t not in tags:
                tags.append(t)

        return CodeChunk(
            content=content,
            chunk_type="operator",
            start_line=start_line,
            end_line=end_line,
            file_path=file_path,
            relative_path=relative_path,
            folder_structure=folder_structure,
            name=op_path or node.get("name"),
            complexity_score=len(params),
            tags=tags,
            relationships=relationships or None,
            language="td_network",
            chunk_id=chunk_id,
        )

    def _build_class_chunk(
        self,
        cname: str,
        cdata: dict[str, Any],
        instances: list[str],
        file_path: str,
        relative_path: str,
        folder_structure: list[str],
        chunk_id: str,
        span: tuple[int, int],
        relationships: list[RelationshipEdge] | None,
    ) -> CodeChunk:
        mro = cdata.get("mro") or []
        signature = cdata.get("signature") or []

        lines = [f"{cname} — TouchDesigner operator class"]
        if len(mro) > 1:
            lines.append("class " + " < ".join(mro))
        if signature:
            pars = ", ".join(
                f"{p.get('name')}: {p.get('style')} = {p.get('default')!r}"
                for p in signature
            )
            lines.append(f"custom parameters: {pars}")
        if instances:
            lines.append(f"instances: {', '.join(instances)}")

        content = "\n".join(lines)

        return CodeChunk(
            content=content,
            chunk_type="class",
            start_line=span[0],
            end_line=span[1],
            file_path=file_path,
            relative_path=relative_path,
            folder_structure=folder_structure,
            name=cname,
            complexity_score=len(signature),
            tags=["class", "td_class"],
            relationships=relationships or None,
            language="td_network",
            chunk_id=chunk_id,
        )

    def _build_network_chunk(
        self,
        graph: dict[str, Any],
        network_name: str,
        chunk_id: str,
        span: tuple[int, int],
        root_node: dict[str, Any] | None,
        real_nodes: list[dict],
        file_path: str,
        relative_path: str,
        folder_structure: list[str],
        unresolved_script_refs: int,
        phantom_dst_count: int,
        relationships: list[RelationshipEdge] | None,
    ) -> CodeChunk:
        target = graph.get("target", "")
        stats = graph.get("stats") or {}
        edge_types = graph.get("edge_types") or []
        tag_groups = graph.get("tag_groups") or {}

        node_count = stats.get("node_count", len(real_nodes))
        # reported_* are the exporter's own tallies (stubs included, shared_tag
        # counted once) -- never the same number as what this chunker actually
        # builds/emits. See the module docstring for the divergences. Fallbacks
        # are producer-sourced too (graph["nodes"], not real_nodes) so the label
        # stays true even when the exporter omits "stats".
        reported_nodes = stats.get("node_count", len(graph.get("nodes") or []))
        reported_edges = stats.get(
            "edge_count", sum(t.get("count", 0) for t in edge_types)
        )
        family_counts = stats.get("family_counts") or {}

        lines = [f"{network_name} — TouchDesigner network at {target}"]
        # The root COMP's own identity lives here, not on an operator chunk.
        if root_node:
            root_type = root_node.get("op_type") or root_node.get("class_name")
            if root_type:
                lines.append(
                    f"root operator: {root_type} ({root_node.get('family', '')})"
                )
            root_mro = root_node.get("mro") or []
            if len(root_mro) > 1:
                lines.append("class " + " < ".join(root_mro))
            root_params = root_node.get("params") or {}
            if root_params:
                param_str = ", ".join(f"{k}={v!r}" for k, v in root_params.items())
                lines.append(f"params: {param_str}")
        lines.append(
            f"{reported_nodes} operators, {reported_edges} relationships "
            "reported by exporter"
        )
        if family_counts:
            fam_str = ", ".join(f"{k}:{v}" for k, v in sorted(family_counts.items()))
            lines.append(f"operator families: {fam_str}")

        top_level = sorted(
            self._relative_op_path(n["id"], target)
            for n in real_nodes
            if n.get("parent") == target
        )
        if top_level:
            lines.append(f"top-level operators: {', '.join(top_level)}")

        if tag_groups:
            tg_str = ", ".join(
                f"{tag}({len(members)})" for tag, members in sorted(tag_groups.items())
            )
            lines.append(f"tag groups: {tg_str}")

        if unresolved_script_refs:
            lines.append(f"{unresolved_script_refs} unresolved script reference(s)")

        if phantom_dst_count:
            lines.append(
                f"{phantom_dst_count} unique unresolved edge target(s) "
                "synthesized as phantom node(s)"
            )

        content = "\n".join(lines)

        return CodeChunk(
            content=content,
            chunk_type="network",
            start_line=span[0],
            end_line=span[1],
            file_path=file_path,
            relative_path=relative_path,
            folder_structure=folder_structure,
            name=network_name,
            complexity_score=node_count,
            tags=["network"],
            relationships=relationships or None,
            language="td_network",
            chunk_id=chunk_id,
        )


# ----------------------------------------------------------------------
# JSON position scanning
# ----------------------------------------------------------------------


def _json_element_spans(
    text: str,
) -> tuple[dict[str, tuple[int, int]], dict[str, tuple[int, int]]]:
    """Locate every top-level ``nodes[]`` element and ``classes{}`` entry in *text*.

    Returns ``(node_spans_by_id, class_spans_by_name)``, each value a 1-based
    inclusive ``(start_line, end_line)`` range in the serialized file -- the span
    ``Read`` needs to show exactly that node/class JSON. Works on any formatting
    (``indent=2`` as the exporter writes it, or minified, where every element
    collapses onto the same line).

    Walks only the *top-level* object with ``json.JSONDecoder.raw_decode`` so a
    nested ``"nodes"``/``"classes"`` key (say, inside a node's ``params``) can never
    be mistaken for the real tables. Any structural surprise (non-object root,
    non-list ``nodes``, malformed tail) degrades to whatever was collected so far
    -- the caller already validated the document with ``json.loads``, so this
    only guards against the walker's own assumptions.
    """
    node_spans: dict[str, tuple[int, int]] = {}
    class_spans: dict[str, tuple[int, int]] = {}

    newline_offsets = [i for i, ch in enumerate(text) if ch == "\n"]

    def line_of(pos: int) -> int:
        return bisect.bisect_right(newline_offsets, pos) + 1

    def skip_ws(i: int) -> int:
        n = len(text)
        while i < n and text[i] in " \t\r\n":
            i += 1
        return i

    decoder = json.JSONDecoder()

    def walk_object(i: int, on_entry) -> int:
        """Walk ``{ "k": v, ... }`` starting at the ``{`` at *i*; return the index
        just past the closing ``}``. ``on_entry(key, key_pos, value_pos, value,
        value_end)`` is invoked per pair."""
        i = skip_ws(i)
        if i >= len(text) or text[i] != "{":
            raise ValueError("expected object")
        i = skip_ws(i + 1)
        while i < len(text) and text[i] != "}":
            key_pos = i
            key, i = decoder.raw_decode(text, i)
            i = skip_ws(i)
            if i >= len(text) or text[i] != ":":
                raise ValueError("expected ':'")
            value_pos = skip_ws(i + 1)
            value, i = decoder.raw_decode(text, value_pos)
            on_entry(key, key_pos, value_pos, value, i)
            i = skip_ws(i)
            if i < len(text) and text[i] == ",":
                i = skip_ws(i + 1)
        return i + 1

    def walk_array(i: int, on_element) -> int:
        """Walk ``[ v, ... ]`` starting at the ``[`` at *i*; return the index just
        past the closing ``]``. ``on_element(value, value_pos, value_end)``."""
        i = skip_ws(i)
        if i >= len(text) or text[i] != "[":
            raise ValueError("expected array")
        i = skip_ws(i + 1)
        while i < len(text) and text[i] != "]":
            value_pos = i
            value, i = decoder.raw_decode(text, i)
            on_element(value, value_pos, i)
            i = skip_ws(i)
            if i < len(text) and text[i] == ",":
                i = skip_ws(i + 1)
        return i + 1

    def on_node(value: Any, start: int, end: int) -> None:
        if isinstance(value, dict) and isinstance(value.get("id"), str):
            node_spans[value["id"]] = (line_of(start), line_of(end - 1))

    def on_class(key: str, key_pos: int, _vpos: int, _value: Any, end: int) -> None:
        class_spans[key] = (line_of(key_pos), line_of(end - 1))

    def on_top(key: str, _kpos: int, value_pos: int, value: Any, _end: int) -> None:
        if key == "nodes" and isinstance(value, list):
            walk_array(value_pos, on_node)
        elif key == "classes" and isinstance(value, dict):
            walk_object(value_pos, on_class)

    try:
        walk_object(0, on_top)
    except (ValueError, json.JSONDecodeError) as e:  # pragma: no cover - defensive
        logger.debug("tdgraph position scan stopped early: %s", e)

    return node_spans, class_spans
