# TD network edges carry only honest provenance

Status: accepted
Date: 2026-09-15

## Context

`chunking/td_network_chunker.py` ingests `.tdgraph.json` exports produced by `TD_Glossary_tox`.
The producer's per-edge schema is exactly 13 keys (`type, src, dst, par, via, shortcut, tag,
carries, dst_index, target, kind, line, col`) — no `confidence`, no `resolver_source`. Yet every
edge this chunker emits arrived downstream carrying `confidence=0.98`, a number the producer never
wrote. Two further places in the same file reported the producer's own facts as if the consumer had
computed them, or reported the wrong ones. One root cause underlies all three: **the consumer
invented or mis-reported facts the producer never asserted.**

1. **Invented confidence.** `_RESOLVED_CONFIDENCE = 0.98` was justified by a comment describing a
   two-tier resolver that does not exist in this chunker — there is no fuzzy resolution step, so
   there is no second (0.5) tier; that half of the comment was dead prose. The number itself was
   also borrowed from a real, distinct convention: 0.98 is `ResolverConfidence.LSP`, the confidence
   tier for a type-inferred call edge elsewhere in the codebase. Stamping it on a JSON-lookup edge
   made the two indistinguishable to anything reading `confidence`. Confirmed live via the
   `code-search` MCP server: `find_connections` on a real TD operator chunk returned
   `"confidence": 0.98` on `contained_by`/`references`/`scripted_by` edges. The fabrication also
   bought nothing: `graph_storage.edge_confidence()` only honours `confidence` when it is a
   **string** tag present in `AST_CONFIDENCE_BY_TAG`; a bare float falls through to `None`, which
   `_edge_confidence` maps to `1.0`. TD edges already **traversed** at 1.0 and only **displayed**
   0.98.
2. **Borrowed count.** The network chunk's summary line rendered `stats.node_count` /
   `stats.edge_count` — the exporter's own tallies — as `"N operators, M relationships"`, with no
   indication the numbers were the producer's, not this chunker's. They diverge by a wide margin:
   for the test fixture, the exporter's `stats.edge_count` is 40, while the chunker actually emits
   **70** `RelationshipEdge` objects, from five independent causes — `shared_tag` is emitted in
   both directions (+9, ADR-0062 C5), `script_ref` edges with a null `dst` are dropped (−3),
   an extra `scripted_by` edge is synthesized per synced script file (+2), and `inherits`/
   `instance_of` edges are synthesized from the `classes`/`nodes` tables with no entry in
   `edge_types` at all (+8, +14). No single consumer-computed total could be attributed correctly
   without recomputing all five divergences, and that computation would silently rot as the chunker
   evolves.

   **Correction (2026-09-15, against this repo's bundled fixture only — do not generalize from
   it):** the "−3" line above attributes part of the divergence to `script_ref` null-`dst` drop
   specifically. That is a fixture artifact, not the general mechanism, and the producer side
   disproved reading it as general: across all four of `TD_Glossary_tox`'s live networks,
   `par_ref` carries **zero** null-`dst` edges yet still collapses down to a smaller consumer
   count. The actual general mechanism, verified against those live networks and written up in
   `docs/architecture/network-graph.md`'s "Contract" section (producer repo): `par_ref`,
   `script_ref`, and `shortcut_ref` all merge onto one consumer relationship, `references_op`,
   keyed `(src, dst, relationship)` — parallel edges between the same pair collapse across **all
   three** producer types, after null-`dst` edges are dropped first. Null-`dst` drop is one step
   in that pipeline, not a standalone per-type cause; no single reference type "drops" on its own.
   The producer doc also confirms `inherits`/`instance_of` synthesis as the largest inflating term
   in general (matching this ADR's own +8/+14), and that the divergence ratio is network-specific
   (1.38x–1.80x measured), not the fixture's fixed 70/40.
3. **Misdirected warning.** A `script_ref` edge with a null `dst` is contract-conformant — it means
   the exporter itself could not resolve a DAT's callback to a project file, and the count was
   already surfaced on the network chunk's own body — yet it logged at `logger.warning`. Meanwhile
   a non-null `dst` that names no node anywhere in the snapshot is the more interesting case: nothing
   detected it, and `chunk_id_for()` never raises — it silently synthesizes a phantom node for it,
   indistinguishable from the legitimate case of a real out-of-scope reference (a stub node, or an
   external class). The warning fired on the benign, already-expected case and stayed silent on the
   one that is actually contract drift.

## Decision

**Delete the invented confidence; keep the honest provenance.** `_RESOLVED_CONFIDENCE` is removed.
Both of its use sites (the `scripted_by`/`via: file` edge, and the shared `add()` closure every
other TD `RelationshipEdge` routes through) now pass `confidence=1.0` explicitly — not by omitting
the kwarg and relying on `RelationshipEdge`'s own default, since an explicit `1.0` documents the
decision at the call site instead of hiding it behind a dataclass default.
`_RESOLVER_SOURCE = "td_live"` and every one of its ten metadata stamps are unchanged: naming where
an edge came from is honest; grading it on a resolver-confidence scale that does not apply to it is
not. The module comment above the constant is rewritten to say so: these edges are read straight
off a live snapshot with no resolution step, so there is nothing to be uncertain about; the
tradeoff is that a 1.0 JSON-lookup edge is now lossy in the sense that it is indistinguishable from
any other 1.0 edge in the graph — provenance lives in `metadata["resolver_source"]` instead. The
value is deliberately **not** routed through `resolver_confidence` metadata: that key is the only
thing `edge_confidence()` honours as a float, and it drives `get_edge_data`'s tie-break sort
(`_primary_key`, which defaults absent `resolver_confidence` to `0.0`) — stamping it there would
change traversal and ranking outcomes, not just what is displayed, which is the opposite of this
ADR's intent.

**Attribute the network chunk's counts to whoever computed them.** `shared_tag`'s symmetric
double-emission is correct per ADR-0062 C5 and is untouched. The summary line now reads
`"{reported_nodes} operators, {reported_edges} relationships reported by exporter"`, where both
values are read from `stats` with *producer-sourced* fallbacks (`len(graph.get("nodes"))`, the raw
`edge_types` histogram sum) rather than consumer-built ones — so the label stays true even when
`stats` is absent from an export. `node_count`'s existing role feeding `complexity_score` is left
byte-identical; only the rendered text and its source variable changed. A module-docstring sentence
now states the rule for anyone comparing `edge_types`/`stats` against emitted edges: halve
`shared_tag`, and account for the other four divergences.

**Make the log level match which case is actionable.** The null-`dst` `script_ref` warning is
demoted to `logger.debug` — it is expected, already counted, and already visible on the network
chunk. In its place, a new check runs immediately after the existing (and unrelated) null-`dst`
guard for other edge types: every non-null `dst`, for **every** edge type, is checked against the
full set of node ids declared in the snapshot's own `nodes` array (which includes stub nodes and
the network root — both legitimate, so neither false-positives). A `dst` absent from that set now
logs a `warning` before `chunk_id_for()` synthesizes a phantom node for it, naming the edge type,
the missing id, and the source. This is a deliberate broadening beyond a `script_ref`-only check:
every edge type in this file funnels its `dst` through the same `chunk_id_for()` call, so the same
silent-phantom-node risk exists uniformly, and a single guard at the loop level is both the simpler
implementation and the more complete one. The existing "any type other than `script_ref` with a
null `dst`" warning (added by the immediately-preceding commit as ADR-0072 drift detection) is left
at `warning` — it is contract drift of exactly the same kind this file already warns about
elsewhere, and no real export has ever produced it.

**Report-only, in these Consequences, not fixed:** the codebase-wide `confidence`-vs-
`resolver_confidence` naming split that made the invented value inert in the first place —
`chunking/relationships/relationship_extractors/instantiation_extractor.py:127` sets
`confidence=0.8` for a heuristic instantiation match, `implements_extractor.py:171` sets `1.0`, and
`base_extractor.py:236` passes a caller-supplied value through unchanged. None of these three is
touched: fixing the pattern codebase-wide is a larger, separable change, and every one of them is
already inert in exactly the same way `_RESOLVED_CONFIDENCE` was — a bare float in `confidence` is
never read by `edge_confidence()` unless it happens to match a string tag in
`AST_CONFIDENCE_BY_TAG`, which none of these do.

## Consequences

- Persisted graphs built before this change keep `confidence: 0.98` on stored TD edges. There is
  no migration; a stale index and a freshly built one will disagree on this field until the stale
  one is reindexed.
- Any external consumer reading the displayed `confidence` value on a TD edge sees a silent
  0.98 → 1.0 change the next time the project is reindexed.
- `graph/graph_storage.py`'s on-disk load path already defaults a missing `confidence` to `1.0`
  (`EDGE_ATTR_CONFIDENCE` default), so the storage layer already agreed with the new value before
  this change — this ADR brings the emission side into agreement with a default that was already
  in place.
- TD edges were never gated by the 0.98 value: they survive traversal only via
  `TraversalPolicy.admits`'s permissive unknown-confidence default (ADR-0050). Nothing about
  traversal or ranking changes here, since `resolver_confidence` (the only float
  `edge_confidence()` reads) was never stamped on a TD edge either before or after this change.
- `RelationshipEdge.is_high_confidence` has no production consumers (only its own docstring and
  one direct unit test), so the 0.98 → 1.0 change is inert there.
- The `CHANGELOG.md` `[Unreleased]` entry that documented the `scripted_by` edge's shape as
  `confidence 0.98, resolver_source: td_live` is corrected in the same section it appears in, since
  `[Unreleased]` describes what will ship, not a historical record.
- The three report-only extractor sites above remain a known, separate cleanup: fixing the
  `confidence`/`resolver_confidence` naming pattern across the codebase is out of scope for this
  change and is left as a candidate for a future, dedicated pass.

## Verification

- `uv run pytest tests/` green, including new coverage: the network chunk's summary line is
  asserted to attribute its counts to the exporter and to diverge from the chunker's own emitted
  edge count (`test_network_chunk_reports_exporter_counts_not_its_own`); the demoted warning is
  asserted absent at `WARNING` and present at `DEBUG`
  (`test_unresolved_script_ref_logs_at_debug_not_warning`); the new phantom-`dst` detection is
  proven to fire on a mutated fixture and stay silent on stub/root targets in the unmodified one
  (`test_unresolvable_non_null_dst_warns_before_phantom_synthesis`,
  `test_stub_and_root_dst_do_not_trigger_unresolvable_warning`); a follow-up fix
  (2026-09-15) de-dups that warning to once per unique `(etype, dst)` pair instead of once per
  edge, since a fan-in target (many edges naming the same missing dst) would otherwise flood the
  log with identical lines — pinned by
  `test_unresolvable_dst_warns_once_per_unique_target_not_per_edge`, and the network chunk's
  summary line now also reports the unique phantom-target count; and the six pre-existing
  assertions of `confidence == 0.98` on TD `scripted_by` edges (`test_td_network_chunker.py`,
  `test_graph_storage.py`, `test_graph_integration.py`) are updated to `1.0`.
- `grep -rn "0\.98"` across the tree shows no remaining TD-path hit — every surviving 0.98 is the
  legitimate LSP resolver tier (`graph/graph_storage.py`, the LSP/call-edge-resolver test suite,
  `docs/ADVANCED_FEATURES_GUIDE.md`, `CHANGELOG.md`'s LSP-rollout entries).
- The TD golden gates (`test_golden_set_guard.py`, `test_td_golden_schema.py`) re-run green: no
  chunk id, kind, or count changed.
- All five blocking CI gates clean: `pytest`, `ruff check`, `ruff format --check`, `pyrefly check`,
  `pre-commit run --all-files`.
- End-to-end via the `code-search` MCP server: `switch_project` onto the fixture project,
  `find_connections` on a TD operator chunk, and confirm the returned edges show
  `confidence: 1.0` with `resolver_source: td_live` intact. Note: this requires a running server
  built from this change's modules — a long-lived server process holding pre-change modules will
  not reflect it without a restart.
