# TD edge-type vocabulary is declared and drift-tested

Status: accepted
Date: 2026-09-15

## Context

`claude-context-local` ingests `.tdgraph.json` exports written by `TD_Glossary_tox`'s Export
Graph JSON pulse (`Extensions/OperatorGlossary/dat_NetworkGraphExt.py` in that repo — moved there
from `Scripts/` in 2026-09; ADR-0062's Context section still names the old path) into a searchable
code/graph index via `chunking/td_network_chunker.py` (ADR-0062, Part C). The producer's edge
vocabulary is declared authoritatively in
`Extensions/OperatorGlossary/tdgraph_contract.py`'s `GRAPH_EDGE_TYPES` — **13 types**, not the 11
ADR-0062's Context section describes (that count undercounted both `clone` and `scripted_by`; see
the forward-pointer added there). This consumer handled 12 of the 13 and silently dropped `clone`
at `logger.debug`, and held **no copy of the vocabulary at all** — nothing in this repo could
detect producer/consumer drift in either direction.

That gap was not accidental on the producer's side. `tdgraph_contract.py`'s own docstring states
the tuple lives there specifically because "this vocabulary is what the consumer's unhandled /
declared-but-unhandled / observed-but-undeclared drift detection diffs against." The producer went
further and shipped its own half of the check —
`TD_Glossary_tox/tests/test_tdgraph_edge_types_contract.py` — which guards three copies of the
vocabulary (the exporter's `EDGE_TYPES` registry, the contract tuple, and the JSON-schema `type`
enum) against each other, in both directions and as an exact order match, and its docstring states
plainly that "the claude-context-local `td_network_chunker`'s ... drift detection diffs against
exactly this vocabulary." It did not, until this ADR.

Three further staleness findings surfaced while tracing the gap:

- The committed fixture (`tests/fixtures/td_network/Test_network.tdgraph.json`) carried an
  `edge_types` summary of 11 entries while its own `edges` array used 12 distinct types
  (`scripted_by` was present in `edges` but missing from the summary) — a hand-edit slip, not a
  producer bug: the producer's `_compute_edge_types_block` seeds `dict.fromkeys(EDGE_TYPE_ORDER,
  0)` first and always writes all 13 entries, zeros included, confirmed against three real
  exports on disk. The fixture is now rebuilt to that faithful 13-entry shape.
- `mcp_server/tool_specs.py`'s `find_connections` `relationship_types` filter is prose inside a
  `description` string, not a JSON-Schema enum (the actual schema is an unconstrained
  `{"type": "array", "items": {"type": "string"}}`) — and that prose list had already drifted on
  its own, missing `assigns_to`/`reads_from` entirely, independent of this pass.
- The ingestion path had three small silent-data-loss gaps found while auditing it end to end: a
  null `dst` on any edge type other than `script_ref` would propagate an `AttributeError` that a
  broad `except Exception` upstream turns into a silently-dropped file's worth of chunks; the
  producer's `schema_version` was never checked against what this chunker was written against; and
  `script.file_matches_dat` (the Sync Manifest's disk/DAT-match flag) and a non-zero
  `unresolved_script_refs` count were both read/computed but never surfaced anywhere outside a
  chunk's own body text.

## Decision

**Add `RelationshipType.CLONES`.** Producer semantics: `clone` is *clone COMP → its Clone Master*,
emitted only while `enablecloning` is on (the producer downgrades to `par_ref` otherwise). Source
is the clone, target is the master. Not folded into `INSTANTIATES` — that member already carries
both `replicator` edges and the synthesized `instance_of` edges, and a third, semantically
different relation would make all three indistinguishable to any `relationship_types=[...]`
filter. Mirrored across every site `SHARES_TAG` (the last TD type added, ADR-0062) touches: the
enum member and vocabulary docstring, the priority-6 group, `get_relationship_field_mapping()`
(`"clones": ("clones", "cloned_by")`), `graph/schema.py`'s `REVERSE_RELATIONS`
(`"clones": "cloned_by"`), `graph/graph_storage.py`'s `DEFAULT_EDGE_WEIGHTS` (`0.8` — the same
tier as `docked_to`/`scripted_by`, above the 0.7 parameter-reference tier, since a clone master is
the operator's definition), a `_SIMPLE_EDGE_MAP` row in `td_network_chunker.py`, every closed-list
test that enumerated the prior 29-member vocabulary, and the doc-only prose lists in
`tool_specs.py` (also fixing the pre-existing `assigns_to`/`reads_from` gap there),
`result_view.py`, `MCP_TOOLS_REFERENCE.md`, and `search_config.json.example`. `clone`'s `dst` is
never null in a real export (`_emit_clone_edge` always sources it via `_stub_target()`); an
out-of-scope master arrives as a stub node, which `chunk_id_for` already resolves to a phantom
node the same way every other unindexed target does — no new null-handling branch was needed for
this type specifically (see the general null-`dst` guard below, added for other types).

**Declare the vocabulary and drift-test it — the consumer's half of the contract the producer was
waiting on.** `chunking/td_network_chunker.py` gains `TD_GRAPH_EDGE_TYPES: tuple[str, ...]`, all 13
types in the producer's own canonical order (a tuple, not just a `frozenset`, because the
producer's `GRAPH_EDGE_TYPES` asserts exact order — that order drives every real
`edge_types[]` histogram — and mirroring it is what makes the fixture-faithfulness test below
meaningful), plus a derived `TD_GRAPH_EDGE_TYPE_SET` for membership checks. A frozenset constant,
`_EXPLICIT_BRANCH_EDGE_TYPES`, lives immediately next to the `if`/`elif` dispatch chain it
describes, with a comment requiring it move in the same diff as any branch change — this is what
lets the new test compute the "handled set" (`_EXPLICIT_BRANCH_EDGE_TYPES | _SIMPLE_EDGE_MAP.keys()`)
from source instead of hand-maintaining a fourth, independently-drifting copy of the list.
`tests/unit/chunking/test_td_network_edge_vocabulary.py` asserts: the handled set equals
`TD_GRAPH_EDGE_TYPE_SET` (the actual drift guard — add or remove a type on either side without
updating the other and this fails); every edge type in the fixture is a declared type; and the
fixture's `edge_types` histogram is the full 13 entries in canonical order with true counts,
mirroring the producer's own `test_schema_edge_type_enum_matches_contract_order`. The
previously-DEBUG fallback for an unrecognized edge type is now `logger.warning` — a silent DEBUG
drop is exactly what let `clone` sit unhandled for a full release; the warning catches drift in
the field, the test catches it in CI.

**Fixture rebuilt to be a faithful stand-in.** `edge_types` now lists all 13 types in canonical
order with real counts including zeros for none-observed types (there are none in this fixture,
but the shape now matches what a real export always writes rather than a filtered subset). Two
`clone` edges were added: one from an in-scope operator to another already-present real node (so
`find_connections(relationship_types=["clones"])` returns a genuine chunk→chunk edge, not just a
phantom), and one to a new stub node (`/project1/external/annotate1`), exercising the built-in
`annotateCOMP` utility-node case the producer's own docs describe (its Clone Master is
`op.TDAnnotate.op('annotate', includeUtility=True)`, outside any walked project). The stub adds no
chunk (`real_nodes` filters `stub`), so chunk-count-derived goldens are unaffected.

**Ingestion audit — fixed what was cheap, reported the rest.** Fixed: (1) a null-`dst` guard at the
top of the edge loop skips-and-warns for any type other than `script_ref` that carries a null
`dst`, rather than letting `chunk_id_for(None)` raise into a silently-swallowed whole-file chunk
loss; (2) a `schema_version` mismatch against a new `TD_GRAPH_SCHEMA_VERSION = 1` constant now logs
a warning instead of being ignored (checked, not enforced — an export from a different schema
version is still ingested); (3) `script.file_matches_dat` is now read into the `scripted_by` edge's
metadata alongside the already-consumed `synced` flag; (4) a non-zero `unresolved_script_refs`
count now logs a warning at ingestion time, in addition to its existing prose mention inside the
network chunk's body. Everything else found during the audit (`par_modes`, `state`, `layout`,
`perf`, `generated_at`, `content_hash` unread; the invented `resolver_source`/`confidence`
constants; `carries` retained only for `wire`/`comp_wire`; `shared_tag`'s double-counting relative
to the producer's per-edge histogram; only `mro[1]` driving `INHERITS`) is reported, not fixed —
none is a silent-data-loss bug on the scale of the four above, and each is a larger, separable
change.

**Out of scope, noted for the record.** `TD_Glossary_tox/docs/Procedural_Graphs_Prerequisites.md`
§4 says ADR-0062 "grafted TouchDesigner on as a pseudo-language with 8 relation types" — adding
`CLONES` makes that 9, and the line is now stale. That file belongs to `TD_Glossary_tox`; it is
not edited here.

## Consequences

- The producer/consumer contract this ADR closes is now enforced in both directions: the producer
  already asserted its own vocabulary against its own exporter and schema; this repo now asserts
  its handled set against the same vocabulary. A future producer change to `GRAPH_EDGE_TYPES`
  without a matching change here fails this repo's CI instead of silently under- or
  over-interpreting an export.
- `clones` is reachable exactly like every other TD relationship type — via
  `relationship_types=[...]` on `find_connections`, weighted traversal
  (`graph_storage.get_neighbors_ranked`), and a named `REVERSE_RELATIONS` output field.
  `graph/traversal_policy.py`'s `DEFAULT_RELATION_TYPES` (`("calls", "called_by")`) is untouched —
  no TD type has ever been in it, and `TraversalPolicy` is generic over a caller-supplied list.
- The rebuilt fixture is a closer stand-in for a real export than before this ADR (full 13-entry
  histogram, zeros included) but is still hand-built, not machine-generated; it should be
  re-validated against the next real export the same way ADR-0062's C4 fixture was originally
  derived.
- The three report-only ingestion-audit findings that are cheap wins for a future pass:
  `unresolved_script_refs` and `schema_version` are now visible in logs but neither is enforced or
  gated; a project ingesting a genuinely incompatible schema version still proceeds, just loudly.

## Verification

- `uv run pytest tests/` green, including the new
  `tests/unit/chunking/test_td_network_edge_vocabulary.py` and every closed-list test updated for
  the vocabulary's 29→30 member count (`test_relationship_types.py`, `test_schema.py`,
  `test_graph_enrichment.py`, `test_graph_storage_weighted.py`, `test_extractor_registry.py`), plus
  the unmodified TD golden gates (`test_golden_set_guard.py`, `test_td_golden_schema.py`) confirming
  the fixture rebuild caused no chunk-id churn (golden ids are span-less; the new stub node adds no
  chunk).
- The drift test proven red/green in both directions: a fake type temporarily added to
  `TD_GRAPH_EDGE_TYPES` fails `test_handled_edge_types_match_declared_vocabulary`; temporarily
  removing `"clone"` from `_SIMPLE_EDGE_MAP` fails the same test from the other side.
- `find_connections(relationship_types=["clones"])`, driven through the `code-search` MCP server
  against the fixture project with `chunking.enable_td_network_indexing=true`, returns the
  in-scope clone→master edge as a real chunk→chunk result; the stub-master clone edge resolves to
  a phantom node without a dangling target or an error.
- All five blocking CI gates clean: `pytest`, `ruff check`, `ruff format --check`, `pyrefly check`,
  `pre-commit run --all-files` (including `typos`, live for this pass since it touches this ADR and
  `CHANGELOG.md`).
