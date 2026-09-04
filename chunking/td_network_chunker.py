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
via ``search/chunk_id.py::build()`` (never hand-rolled) and always carrying a line
span -- ``0-0`` for anything without a natural one, mirroring
``file_summarizer.py``'s module-chunk convention:

- ``operator``  -- one per real (non-stub) node, named by its path relative to the
  network target (``"glsl1"``, ``"comp1/box1"``).
- ``class``     -- one per entry in the snapshot's ``classes`` table, named by class
  name.
- ``network``   -- one per file, a synthetic summary of the whole snapshot (same
  role as ``file_summarizer``'s ``module`` chunk).

Relationship edges are built as ``RelationshipEdge`` objects directly (not through
``chunking.relationships.edge_specs.materialize_relationship_edges`` -- there is no
AST for a JSON snapshot to run through). An edge whose target isn't itself chunked
here (a stub node, or a class outside the local ``classes`` table, e.g. an
abstract base like ``TOP``/``OP`` that no node instantiates directly) still gets a
chunk_id-shaped ``target_name``; ``graph_storage`` creates a phantom node for it on
first edge, exactly as it does for an edge to an unindexed Python symbol.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from chunking.python_ast_chunker import CodeChunk
from chunking.relationships.relationship_types import RelationshipEdge, RelationshipType
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
                graph: dict[str, Any] = json.load(fh)
        except OSError as e:
            logger.warning("Could not read %s: %s", file_path, e)
            return []
        except json.JSONDecodeError as e:
            logger.warning("Malformed .tdgraph.json %s: %s", file_path, e)
            return []

        if relative_path is None:
            relative_path = self._compute_relative_path(file_path)

        return self._build_chunks(graph, file_path, relative_path)

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
        stays a stable, human-readable chunk_id component either way.
        """
        if node_id == target:
            return ""
        prefix = target.rstrip("/") + "/"
        if node_id.startswith(prefix):
            return node_id[len(prefix) :]
        return node_id.lstrip("/")

    # ------------------------------------------------------------------
    # Chunk assembly
    # ------------------------------------------------------------------

    def _build_chunks(
        self, graph: dict[str, Any], file_path: str, relative_path: str
    ) -> list[CodeChunk]:
        target = graph.get("target", "")
        nodes = graph.get("nodes") or []
        edges = graph.get("edges") or []
        classes = graph.get("classes") or {}
        node_line_spans = graph.get("node_line_spans") or {}

        real_nodes = [n for n in nodes if not n.get("stub")]

        # ---- Pass 1: assign chunk ids (needed before any edge can be built) ----
        op_chunk_id: dict[str, str] = {}
        op_span: dict[str, tuple[int, int]] = {}
        for n in real_nodes:
            node_id = n["id"]
            op_path = self._relative_op_path(node_id, target)
            span = node_line_spans.get(node_id)
            start, end = (span["start_line"], span["end_line"]) if span else (0, 0)
            op_span[node_id] = (start, end)
            op_chunk_id[node_id] = build_chunk_id(
                relative_path, start, end, "operator", op_path
            )

        network_name = Path(target).name or (target or Path(relative_path).stem)
        network_chunk_id = build_chunk_id(relative_path, 0, 0, "network", network_name)

        class_chunk_id = {
            cname: build_chunk_id(relative_path, 0, 0, "class", cname)
            for cname in classes
        }

        def chunk_id_for(node_id: str) -> str:
            """Chunk_id for any node id, real or not.

            Gives a stable RelationshipEdge target_name even for nodes this file
            never builds an operator chunk for (a stub, or a reference that lives
            outside the walked subtree) -- graph_storage creates a phantom node
            for it on first edge, matching correction #8 in ADR-0062.
            """
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
                    relationships_by_source.get(class_chunk_id[cname]),
                )
            )

        chunks.append(
            self._build_network_chunk(
                graph,
                network_name,
                network_chunk_id,
                real_nodes,
                file_path,
                relative_path,
                folder_structure,
                unresolved_script_refs,
                relationships_by_source.get(network_chunk_id),
            )
        )

        return chunks

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
                # network root itself is never chunked as an "operator"); nested
                # ones attach to the parent operator chunk.
                source_id = network_chunk_id if src == target else chunk_id_for(src)
                add(
                    source_id,
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
            start_line=0,
            end_line=0,
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
            start_line=0,
            end_line=0,
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
