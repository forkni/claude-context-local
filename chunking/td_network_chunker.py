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

Schema: derived directly from ``TD_Glossary_tox``'s ``Scripts/dat_NetworkGraphExt.py``
(the real, not-yet-run, Part B exporter), not invented. See
``docs/adr/0062-td-network-indexing.md`` and
``tests/fixtures/td_network/Test_network.tdgraph.json`` for the authoritative shape:
``schema_version`` (int), ``target``, ``nodes`` (``stub: true`` for out-of-subtree
placeholders), ``edges`` (11 types), ``classes`` (``{mro, signature}`` per class
actually instantiated by a node -- *not* every class in ``mro``), ``scripts``,
``tag_groups``, ``node_line_spans``, ``edge_types``, ``stats``.

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


logger = logging.getLogger(__name__)

# Every edge this chunker emits comes straight off a live TD network snapshot --
# there is no fuzzy resolution step, so only two confidence tiers exist: an edge
# whose endpoint resolved to a real node (0.98, matching the LSP-resolver tier
# convention elsewhere in the codebase) or one that didn't (0.5). See
# search/call_edge_injection.py for the established resolver_source/confidence
# convention this mirrors.
_RESOLVED_CONFIDENCE = 0.98
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
}


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

        relationships_by_source, unresolved_script_refs = (
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
            parsed = ChunkId.parse(c.chunk_id)
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

    def _build_relationship_edges(
        self,
        graph: dict[str, Any],
        edges: list[dict],
        classes: dict[str, Any],
        chunk_id_for,
        class_chunk_for,
        network_chunk_id: str,
        target: str,
    ) -> tuple[dict[str, list[RelationshipEdge]], int]:
        """Build every RelationshipEdge, grouped by source chunk_id.

        Returns (relationships_by_source, unresolved_script_ref_count). The count
        is surfaced on the network chunk's content per ADR-0062 ("dst: null edges
        are dropped and counted on the network chunk").
        """
        scripts = graph.get("scripts") or {}
        scripts_index = {
            (dat_path, ref.get("kind"), ref.get("line"), ref.get("col")): ref
            for dat_path, refs in scripts.items()
            for ref in refs
        }

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
                    confidence=_RESOLVED_CONFIDENCE,
                    metadata=meta,
                )
            )

        unresolved_script_refs = 0

        for e in edges:
            etype = e.get("type")
            src, dst = e.get("src"), e.get("dst")

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
                logger.debug("Unrecognized .tdgraph.json edge type %r, skipped", etype)

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

        return by_source, unresolved_script_refs

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
        relationships: list[RelationshipEdge] | None,
    ) -> CodeChunk:
        target = graph.get("target", "")
        stats = graph.get("stats") or {}
        edge_types = graph.get("edge_types") or []
        tag_groups = graph.get("tag_groups") or {}

        node_count = stats.get("node_count", len(real_nodes))
        edge_count = stats.get("edge_count", sum(t.get("count", 0) for t in edge_types))
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
        lines.append(f"{node_count} operators, {edge_count} relationships")
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
