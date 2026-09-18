# Procedural graphs are stored in seed format outside CodeGraphStorage

Status: accepted
Date: 2026-09-16

## Context

A *Procedural Graph* (PG, arXiv 2609.09153) is a directed multigraph whose nodes are actions drawn
from a closed vocabulary and whose edges ("transitions") carry three free-text attributes, Φ:
`condition`, `guidance`, `pitfalls`. Given an agent's last action, the graph is *located* at that
node, an h-hop out-neighbourhood is *extracted*, and the Φ text of that neighbourhood is appended to
the agent's next prompt as guidance.

`claude-context-local` (CCL) is the **consumer** of such graphs. `TD_Glossary_tox` (its own
ADR-0011) is the **producer**: it authors and version-controls the graphs as tracked JSON documents
and hands CCL a snapshot to serve. CCL does not know the producer's action vocabulary, does not
validate node ids against it, and makes no LLM call of its own — the tool returns Φ text verbatim
and the calling agent reasons over it.

The cross-repo contract is a single JSON document shape:

| Field | Shape | Notes |
|---|---|---|
| `schema_version` | `1` | literal, checked exactly |
| `name` | string, `^[A-Za-z0-9_-]{1,64}$` | also the stored file's stem |
| `notes` | string, optional | free text, survives edits |
| `nodes` | `[{"id": str}]` | id matches `^[A-Za-z][A-Za-z0-9_]*$`, unique |
| `edges` | `[{"src","dst","relation","condition","guidance","pitfalls"}]` | all seven keys required, no others |

Relations are a closed set of four: `LEADS_TO`, `TRIGGERS`, `PROVIDES_INPUT_FOR`, `CONVERGES_TO`.
The bundled `tests/fixtures/pg/network_layout_seed.json` seed is the canonical dump of the
producer's own `tools/pg_seed_network_layout.json`: 12 nodes and 24 transitions. The middle of the
graph is one strongly connected component with several cycles, such as `Verify_Layout` back to
`Set_Position` via `TRIGGERS` and `Update_Annotation` back to `Identify_Group` via `LEADS_TO` —
procedural graphs are cyclic by design, not a defect to validate away.

Nothing in CCL today can hold this shape. `CodeGraphStorage` (`graph/graph_storage.py`) is
enum-typed (`RelationshipType`), auto-creates placeholder endpoints for edges naming an unknown
node, and its on-disk file name is exactly the glob `clear_index`/`delete_project` purge — none of
which fits a hand-authored, free-text-edge document that must survive index maintenance untouched.

## Decision

**A new, independent store, not an extension of `CodeGraphStorage`.**

- `graph/procedural_graph.py` — a new module, NetworkX-backed internally but never importing
  `mcp_server` (ADR-0051's `graph/` ↔ `mcp_server` boundary). Not re-exported from
  `graph/__init__.py`: keeping it off the code-graph API surface is the point. `ProceduralGraph`'s
  canonical state is an ordered node-id list plus an edge-dict list — not the derived
  `nx.MultiDiGraph` — because `MultiDiGraph.add_edge(u, v, key=relation)` silently overwrites an
  existing `(u, v, relation)` triple and silently creates missing endpoints, which would make
  duplicate-transition and dangling-endpoint validation undetectable once the graph existed in nx.
  Validation runs on the raw document before nx ever sees it.
- `ProceduralGraphStore(storage_dir)` persists one JSON file per graph under
  `<storage_dir>/procedural_graphs/`, a directory `clear_index`/`delete_project` never touch (their
  purge globs are file-scoped to the per-model directory, not recursive).
- Own file format, `schema_version: 1`, own validation — no `RelationshipType` extension (a string
  relation cannot pass through `RelationshipEdge`, which reads `.value` off an enum) and no import
  tool (`scripts/import_procedural_graph.py` is an operator entry point, not an MCP tool).
- Two `advanced=True` MCP tools in `mcp_server/tools/procedural_handlers.py` —
  `get_procedural_guidance` (locate → extract → serialize, read-only) and
  `edit_procedural_graph` (typed, validated edit, `dry_run` gated) — are the entire consumer-facing
  surface. Neither makes a network or LLM call; guidance text is returned exactly as the producer
  wrote it.
- The store is a **derived serving copy**, not a source of truth. The versioned record of every
  graph lives in `TD_Glossary_tox` as a tracked JSON file; promoting a new revision into CCL is a
  re-import with `force=True`. The store therefore needs no history, checkpoints, or version
  tracking beyond `write_json_atomic`'s single-file atomic write — round-tripping a graph through
  `save`/`load` is canonicalising and idempotent, but is not a claim that hand-authored input is
  preserved byte-for-byte (JSON key order and `ensure_ascii` escaping normalize it).
- `edit_procedural_graph(dry_run=false)` is intended for **candidate-named** graphs only (e.g.
  `network_layout__cand3`, saved alongside the live `network_layout`) — that separation is
  orchestration policy the calling agent is expected to follow, not something the tool enforces.
- `last_action` is **self-declared** by the calling agent from the producer's closed vocabulary; CCL
  never validates it against that vocabulary. A miss — `last_action` names no node in the graph — is
  not an error: `get_procedural_guidance` returns `located: false` plus the *entire* graph, so the
  agent still receives every transition, and the miss rate itself is a signal the producer measures
  offline. There is deliberately no fuzzy or partial matching: a near-miss silently returning the
  wrong node's guidance is worse than an honest miss.
- The **entry-node rule is structural, not nominal**: `validate()` requires exactly one node with
  zero in-degree, whatever its id happens to be, rather than requiring a node literally named
  `Start`. CCL does not know the producer's naming convention, and checking for a literal id would
  be exactly the kind of vocabulary assumption this ADR otherwise avoids. One consequence: deleting
  the seed's `Start` node is not an entry-rule violation by itself (it leaves `Read_Layout` as the
  sole remaining source) — it can still fail for the ordinary reason that `Start`'s incident edges
  disappear with it.
- **Reachability is checked in both directions from the entry, not just into the terminals.**
  `validate()` requires every node to have both a path *to* some terminal (backward BFS from all
  terminals) and a path *from* the sole entry (forward BFS from it, run only once the entry is
  unambiguous) — a cyclic island that drains into its own terminal passes the first check and the
  entry-count check alike, since its nodes still have in-degree ≥ 1 from the cycle, so only the
  forward check catches it. Multiple terminals stay allowed — a procedure may legitimately end
  several ways; this ADR never required exactly one, and the seed's single `End` is pinned by a
  fixture test, not by the validator. This rule runs on every `load()`, not just on edit, because
  both go through `from_document`; a previously-stored graph that violates it becomes unloadable
  (`ProceduralGraphError`, naming the unreachable nodes) rather than silently served. The intended
  recovery path is the same one this ADR already specifies for any invalid document: a re-import
  with `force=True` from the corrected producer-side source, not `edit_procedural_graph` (which
  can't load a graph it can't validate).
- Guidance text is returned **verbatim and is never fetched or expanded** — if Φ text contains a
  reference to something else, resolving it is the calling agent's job, not CCL's.
- This is **pull, not push**: there is no hook, no automatic prompt injection, no background
  process. A host model calls `get_procedural_guidance` when it chooses to.

## Consequences

- Procedural graphs are invisible to `find_path`, `find_connections`, and every other code-graph
  tool. This is intended — they are not code-graph nodes and mixing the two APIs would blur what
  each one means.
- They are never purged by `clear_index` or `delete_project`: both globs
  (`*_call_graph.json`, `*_communities.json`, `index_handlers.py:364-365`) are file-only,
  non-recursive, and scoped under the per-embedding-model directory; `procedural_graphs/` sits
  outside that scope entirely and under a different filename shape by construction.
- The rejected `CodeGraphStorage` wrap would have cost three specific things, not just genericity:
  the `<project_id>_call_graph.json` name pattern (`graph_storage.py:207`) *is* the purge glob a PG
  file would need to dodge by convention rather than by design; `RelationshipEdge`
  (`graph_storage.py:446`) carries a `RelationshipType` enum whose `.value` is read at
  `add_relationship_edge` (`:503`, `:505`), so a producer-defined string relation cannot pass
  through it without widening that enum for a domain `CodeGraphStorage` doesn't otherwise model;
  and placeholder-node auto-creation on an unknown endpoint (`:485-496`) is the opposite of what PG
  validation needs — a dangling endpoint must be a hard error, not a silently synthesized node. The
  AST mutator ratchet in `tests/unit/graph/test_graph_storage_version.py` would also have to widen
  to admit a fourth relationship family it was never scoped to cover.
- Three of the document's nine validation rules — duplicate node id, dangling edge endpoint,
  duplicate `(src, relation, dst)` transition — are only checkable *before* the document becomes an
  nx graph, because nx's own `add_node`/`add_edge` are idempotent/overwriting rather than
  error-raising for exactly those cases. This is why `ProceduralGraph` treats the ordered
  node/edge lists as canonical and the `nx.MultiDiGraph` as a derived traversal structure, not the
  reverse.
- `mcp_server/tools/__init__.py`'s `__all__` groups handlers by module with a running count in a
  comment ("Status handlers (6)", …); the two new handlers are added as "Procedural handlers (2)"
  for consistency, alongside a full documentation sync of the tool count (18 → 20, 10 core + 10
  advanced) across the README, MCP tools reference, installation docs, and the `mcp-search-tool`
  skill's `allowed-tools` frontmatter (functional there — without the two names listed, the skill
  cannot invoke them).

## Verification

- `tests/unit/graph/test_procedural_graph.py` — contract constants; document rejection (one test per
  error string, driven through `from_document`/`load` so the three nx-unenforceable rules are
  actually exercised); the bundled seed's node/edge counts and structural shape; round-trip and
  byte-stability behavior of `save`/`load`/`import_seed`; `locate`/`extract` hop semantics including
  the cycle-closing edge and the reachable-transition count at each hop depth; the serializer's
  golden hit/miss/no-`last_action` strings; `apply_edit`'s accept and reject cases, including the
  entry-rule and duplicate-transition cases nx would otherwise hide; storage-path and
  `NAME_PATTERN` traversal-safety checks.
- `tests/unit/mcp_server/test_procedural_handlers.py` — `hops` clamping (0→1, 99→4, omitted→2);
  `dry_run` defaults and never-write behavior, including for an invalid edit with `dry_run=false`;
  bad/unknown graph name handling; a committed edit reflected by the next
  `get_procedural_guidance` call; both tools' `ADVANCED_TOOLS` gating.
- `tests/unit/mcp_server/test_tool_handlers.py::test_all_handlers_have_error_handling` extended to
  cover `procedural_handlers`.
- All five blocking CI gates clean: `pytest`, `ruff check`, `ruff format --check`, `pyrefly check`,
  `pre-commit run --all-files`.
- `scripts/import_procedural_graph.py tests/fixtures/pg/network_layout_seed.json` writes
  `<storage_dir>/procedural_graphs/network_layout.json` in well under a second (it does not import
  `mcp_server.storage_manager`, avoiding a measured 10.4s PyTorch import cost); a second run without
  `--force` exits 1.
- `MCP_EXPOSE_ADVANCED_TOOLS=1` → `build_tool_list()` returns 20 tools; unset → 10.
- Manual smoke test: `get_procedural_guidance("network_layout", "Create_Op", hops=2)` returns 8
  transitions, each line carrying `condition:`, `guidance:`, and `pitfalls:`; a dry-run
  `edit_procedural_graph` reports `valid` with `committed=false` and leaves the file byte-identical.
