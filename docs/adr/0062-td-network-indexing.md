# Index `.tdgraph.json` TouchDesigner network snapshots (Part C)

Status: accepted
Date: 2026-09-03

## Context

A companion project, `TD_Glossary_tox`, will export a TouchDesigner network as
`Graph/<slug>.tdgraph.json` — a JSON snapshot of operators, their parameters, wiring, docking,
and the `td` class hierarchy (`OP`/`COMP`/`TOP`/.../`glslTOP`). That exporter (Part B of the
source plan) is blocked on a live TD session and has not landed. This ADR covers the consumer
side only: teaching this server to index `.tdgraph.json` as a pseudo-language, so `search_code`,
`find_connections`, and `find_path` work over TD operators the same way they work over Python
symbols.

The source plan's Part C was verified against this codebase on 2026-09-03 (see
`C:\Users\Inter\.claude\plans\study-this-plan-verify-pure-blum.md`, retained as the working
design doc). Verification found 12 claims wrong or incomplete against the live code — most
importantly: the proposed operator chunk_id format (no line span) fails `search/chunk_id.py`'s
own parser; the phantom-node bug the design depends on (`graph_storage.add_node` not clearing
`is_target_name` on promotion) changes PageRank eligibility on the *existing Python index* and
so cannot share a benchmark gate with the TD work; and `USES_TYPE` resolution for operator→class
edges goes through an unreliable k=4 semantic search rather than the deterministic `INSTANTIATES`
path. These are folded into the Decision below.

No real `.tdgraph.json` export exists yet (Part B needs a live TD session to *run*), but
`TD_Glossary_tox`'s `Scripts/dat_NetworkGraphExt.py` already contains Part B's serializer, stdlib-only
down to `_write_graph_json`, and was read directly to derive C4's fixture instead of inventing a
schema. Two corrections against the source plan's assumptions: the version key is `schema_version`
(a plain int, `1` — not `FORMAT_VERSION = "1.1"`), and a node's `signature` is a compact
`"OPType(par=val, ...)"` string (`_node_signature`), not a structured object — there is no
`signature.attribs.point`; the per-*class* `signature` (in the top-level `classes` table, gated by
`Includesignature`, default on) is a *list* of `{name, style, default}` dicts instead, one per custom
par, distinct from the per-node string. C4's fixture matches the real serializer's field names,
key order (`_NODE_KEY_ORDER`/`_EDGE_KEY_ORDER`/`_ROOT_KEY_ORDER`), and all 11 edge shapes exactly.

**Mid-implementation addition (user directive, 2026-09-03):** guard the entire feature behind a
`search_config.json` parameter, default off. Nothing about `.tdgraph.json` recognition should be
live on a deployed server that hasn't opted in — this project's own self-index has no
`.tdgraph.json` files, so the default-off case is also what the C8 benchmark gate measures.

## Decision

**Config gate**: `ChunkingConfig.enable_td_network_indexing: bool`, default `False`
(`search/config.py`). Consumed through one helper,
`chunking/language_registry.py::td_network_indexing_enabled()`, which lazily imports
`search.config.get_chunking_config()` (mirrors `_max_file_size_bytes`'s existing lazy-import
pattern in `multi_language_chunker.py`) and returns `False` when the flag is off *or* when no
config is available (e.g. isolated unit tests) — the safe default in both cases. Every other gate
point below calls this one helper; there is exactly one place that decides whether the feature is
active.

Gate gets applied at the extension-recognition boundary, not scattered through the chunker:
`chunking/tree_sitter.py::get_supported_extensions()` only unions in the `.tdgraph.json`
pseudo-language extension when the helper returns `True`; `MultiLanguageChunker.is_supported()`
independently checks the same helper before consulting `SUPPORTED_EXTENSIONS`. Both feed from
`chunking/language_registry.py`, which still registers `.tdgraph.json → td_network` in
`EXT_TO_LANGUAGE` unconditionally (a static declarative mapping is harmless on its own); the gate
lives at the two consumption points that actually decide whether a file gets chunked or
hash-tracked as that language, matching how `incremental_indexer.py:120` build its
`supported_extensions` set from `get_supported_extensions()` and how that same set feeds the
Merkle hashing scheme. With the flag off, a `.tdgraph.json` file behaves exactly as it does today
on `main`: an unrecognized extension, stat-hashed, never chunked.

**Corrected design** (supersedes the source plan's Part C where they conflict; full detail in the
plan doc above):

1. **C0 — phantom-node fix, standalone.** `graph_storage.add_node` pops
   `NODE_ATTR_IS_TARGET_NAME`/`NODE_ATTR_IS_CALL_TARGET` when a real chunk is promoted over a
   placeholder node. Landed and benchmarked in its own commit, before any TD-specific code, because
   `graph_queries.py`'s phantom filter feeds PageRank/degree centrality (ADR-0055) — this changes
   which nodes are centrality-eligible on the *existing* Python self-index, independent of TD.
2. **C1 — relationship vocabulary.** 8 new `RelationshipType` members (`WIRES_TO`, `DOCKED_TO`,
   `CONTAINS`, `REFERENCES_OP`, `BINDS_TO`, `EXPORTS_TO`, `SCRIPTED_BY`, `SHARES_TAG`), mapped in
   `get_relationship_field_mapping`, `REVERSE_RELATIONS`, `DEFAULT_EDGE_WEIGHTS`,
   `EDGE_EMISSION_SPECS`, and the `find_connections` tool schema — all enumeration sites the
   source plan missed are listed in the plan doc's "Additional gaps" section.
3. **C2 — semantic types.** `operator`, `network` added to both `SEMANTIC_TYPES`
   (`search/graph_integration.py`) and the separate `DEFAULT_SEMANTIC_TYPES`
   (`evaluation/chunk_mapping.py`) — two independent lists, not one.
4. **C3 — extension plumbing**, gated as above. `extension_key()`/`is_td_network_file()` in
   `language_registry.py` are the single source of truth for compound-suffix detection, used
   everywhere a caller currently reads `Path(path).suffix`.
5. **C4/C5 — fixture + `TDNetworkChunker`.** Operator/network/class chunks built with
   `search/chunk_id.py::build()` (never hand-rolled), always carrying a line span — the source
   plan's spanless `<file>:operator:<name>` format fails `is_chunk_id`/`ChunkId.parse`/
   `dedup_key`. Operator→class edges use `INSTANTIATES` (deterministic `get_by_chunk_id`
   resolution), not `USES_TYPE` (unreliable k=4 semantic search on short class names like `TOP`).
   `RelationshipEdge.metadata` (`relationship_types.py:228`) is a real per-edge dict and carries
   `td_edge_type`/`resolver_source`/etc. exactly as the plan describes. `CodeChunk`
   (`chunking/python_ast_chunker.py`) has **no** generic per-chunk `metadata` dict, unlike
   `RelationshipEdge` — the plan's `metadata["op_path"]`/`metadata["shortcuts"]`/`metadata["mro"]`/
   `metadata["signature"]` references at the *chunk* level do not map onto any existing field, and
   adding one to a dataclass shared by every chunker in the system for one pseudo-language's benefit
   fails the "existing functionality first / minimal complexity" project rule and risks a storage
   schema change nobody asked for. Decision: fold `op_path` (redundant with the operator chunk_id's
   own name segment, already retrievable via `ChunkId.parse`/`extract_name`), `mro`, `signature`, and
   `shortcuts` into the operator chunk's NL `content` text instead, exactly where the plan's own
   "Operator chunk NL content" spec already puts them — this makes them BM25/semantic-searchable,
   which nothing would do for a write-only metadata dict with no reader anyway.
6. **C6 — cross-file `SCRIPTED_BY` — researched, not buildable, deferred.** The plan's spec
   (`SCRIPTED_BY` from a DAT operator chunk to `f"{normalize_path(rel)}:0-0:module:{stem}"`, plus a
   "GLSL path via the `pixeldat` par_ref") assumes the exporter records an external companion source
   file for a scripted operator. It does not. Read directly against the real Part B serializer
   (`TD_Glossary_tox/Scripts/dat_NetworkGraphExt.py`, 2026-09-04):
   - `_node_script_info` (L983–996) captures a scripted DAT as `{language, bytes}`, where `bytes` is
     `len(td_op.text.encode(...))` — the *inline* script text's byte length, not a path.
   - `_build_script_ref_edges` (L1227–1305) resolves every `script_ref` edge's `dst` to either
     another operator's node path or `None` (unresolved) — never a filesystem path.
   - `_compute_scripts_block` (L1413–1428) is keyed by the DAT's own node path and lists refs *made
     by* that DAT's script to other operators, not a link to an external `.py` file.
   - No `pixeldat` par, file-sync field, or any other companion-file mechanism exists anywhere in the
     file (grepped for `pixeldat`, `glsl`, `[Ff]ile[Ss]ync`, `External`, `companion` — the one hit is
     an unrelated docstring word, "docked companion ops").

   A TD script (Python DAT text, or a docked GLSL pixel DAT's text) lives entirely inline in the
   `.tdgraph.json` node record; there is no `rel` for `SCRIPTED_BY`'s target format to normalize. The
   `RelationshipType.SCRIPTED_BY` enum member (C1) stays defined — declaring vocabulary ahead of a
   producer is harmless and matches how other unused-by-default types already work — but
   `TDNetworkChunker` emits no edges of this type, because the real schema gives it nothing to point
   at. Reopening condition: only if Part B ever adds a real external-file field (e.g. a TD "Sync to
   File" DAT integration) would this become buildable; until then it is not a config gap or a bug,
   it is a feature with no data source.
7. **C7 — MCP schema + docs** updated for the two new chunk types.

Not built: `docs/CALL_GRAPH_TUNING.md` changes (it holds only a resolver table — nothing there
describes chunk types or relationship types), any `document_composer.compose` branch (it switches on
policy flags, never `chunk_type`; a JSON file already composes to `""` harmlessly), and C6's
cross-file `SCRIPTED_BY` edge emission (see above — no data source in the real exporter).

## Consequences

- With the flag at its default (`False`), this ADR's changes are inert on every existing indexed
  project, including this repo's own self-index — `.tdgraph.json` stays an unrecognized
  extension. The C8 benchmark gate (63q/133q canon, zero movers) measures exactly this default
  state.
- Opting in on a project containing real `.tdgraph.json` files is the only way to observe any
  behavior change from C1–C7; C0 (phantom-node fix) is the only part of this ADR that affects
  already-indexed Python projects regardless of the flag, which is why it ships and is measured
  separately.
- A project that wants TD indexing sets `"chunking": {"enable_td_network_indexing": true}` in its
  `search_config.json` and does a non-incremental reindex (new extension ⇒ new files, not a
  format change to existing ones — no `INDEX_VERSION` bump per the ADR-0037 precedent).
- Part B (the exporter) and Part D (trust/verification oracle, `td_golden.json`) remain out of
  scope; the fixture in C4 is this ADR's stand-in contract for Part B's output shape and must be
  re-validated against the first real export.

## Verification

**C0 (phantom-node fix), measured 2026-09-04.** Gate run per the plan: `graph_phantom_preflight.py`
plus a 63q `run_sscg_benchmark.py` A/B, both on identical substrate (this repo's self-index,
234 files / 2851 chunks) — the fix code toggled on/off, everything else held fixed, to isolate
C0's effect from the unrelated TD-work substrate growth (219→234 files across this same session).

- `graph_phantom_preflight.py`, fix-on vs fix-off: **byte-identical** — 6658 total nodes / 4056
  phantom / 0 orphan-degree-0 both runs, identical top-20 PageRank list (same 10 phantom builtin
  names, same 5 real chunks, same values to 6 decimal places), top-20 phantom fraction 75.00% both,
  max-PageRank node phantom=True both, 14/2602 (0.54%) real chunks clearing the 0.02 centrality
  threshold both. Zero nodes changed phantom classification.
- 63q `run_sscg_benchmark.py`, fix-on (`c0_after_63q.json`) vs fix-off (`c0_off_matched_63q.json`):
  MRR 0.8380 vs 0.8406 (Δ −0.0026), recall@10 0.7659 vs 0.7664 (Δ −0.0005), recall@20 0.8372 vs
  0.8446 (Δ −0.0074), ndcg@10 0.7355 vs 0.7367 (Δ −0.0012). All deltas are within the established
  ±0.02 MRR run-to-run noise band for independent index rebuilds on this project (recorded
  precedent: `project_benchmark_noise_and_pool_hit` memory, "SSCG ±0.02 run noise") — not a real
  signal, consistent with the phantom-preflight result showing zero classification change.
- **Verdict: the fix is correct (regression test
  `test_add_node_clears_phantom_flags_on_promotion` passes, and the bug it closes is real per
  corrections #7/#8 in the source plan) but empirically inert on this codebase's self-index** — the
  phantom→real promotion scenario it guards against does not occur in this project's current call
  graph, so PageRank/degree centrality eligibility (ADR-0055) is unaffected here. Accepted anyway,
  per the plan ("accept or revert on its own merits"): it is a genuine correctness fix for a
  demonstrated bug (`nx.Graph.add_node()` attribute-merge semantics permanently mis-flagging a
  promoted node), and a project with a call graph that does exercise the promotion path (e.g. one
  with more forward-reference edges landing before their target chunk) would see real movement.
  Landed standalone, ahead of the TD-specific commits, per the plan's sequencing.
- C1–C7 zero-mover gate (TD-specific changes, self-index has no `.tdgraph.json`) is tracked
  separately — see C8 below.
