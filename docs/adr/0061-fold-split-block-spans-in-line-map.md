# Fold split_block fragments into one line-map span keyed to the first fragment

Status: accepted
Date: 2026-09-03

## Context

`evaluation/chunk_mapping.build_line_to_chunk_map` is the only line-number → chunk-id
lookup the resolver pipeline has. The LSP resolver (`chunking/relationships/lsp_call_graph.py`)
maps every `CallHierarchyOutgoingCall.to.range.start` through it, and the pyan resolver
(`chunking/relationships/external_call_graph.py`) maps `(filename, lineno)` the same way.
Its default `semantic_types` was `{function, method, class, decorated_definition}`.

`split_block` chunks were not in that set. They are the fragments the chunker produces for a
function or method whose body exceeds the size cap (`_split_large_node` in
`chunking/languages/base.py`); the self-index carries 288 of them across 97 logical symbols.
Two properties of a fragment matter here:

- A fragment's `start_line` is its first *body* statement, so the `def` line, any decorators
  and a multi-line signature sit in a gap no fragment covers.
- Each fragment is a real store chunk and a real graph node (`search/graph_integration.py`
  includes `split_block` in `SEMANTIC_TYPES`). There is no `method:` node for a split symbol;
  `dedup_key` (`search/chunk_id.py`) collapses `split_block` → `method` only as a *key*,
  for search deduplication and evaluation.

Because no fragment was in the map, `find_enclosing_chunk` on any line of a split method fell
through to the smallest chunk that did contain it: the enclosing `class:` chunk. Every callee
that lives in a long method was therefore recorded as a call to its class.
`evaluation/RESOLVER_PRECISION_LABELS_20260902.md` ("Systemic finding") measured this on the
stored graph: `class:` targets whose recorded line is inside the class body, i.e. really a
member, numbered 63 for lsp, 18 for pyan and 18 for libcst. Both lsp and pyan report the
callee by its `def` keyword line, so simply adding the fragments' own spans would not fix
it either: the `def` line is outside every fragment.

## Decision

1. `split_block` joins `DEFAULT_SEMANTIC_TYPES` in `evaluation/chunk_mapping.py`.
2. Fragments never appear individually. All fragments of one symbol (grouped by file and
   `normalize_chunk_id`) fold into **one span** that runs from the symbol's definition line to
   the end of its last fragment.
3. The definition line is recovered by gap-filling, not by parsing: the span starts at the
   tightest of (previous chunk in the file, any type) `end + 1` and (strictly enclosing
   container) `start + 1 + decorator_count`, capped at the first fragment's start, default
   line 1. Only whitespace, comments, decorators and the signature can sit between the
   previous sibling's last line and the first body statement, so the gap belongs to the method.
   The container bound keeps the `class` statement (and a decorated class's decorator lines)
   resolving to the class.
4. The folded span's chunk id is the **raw id of the lowest-start fragment** when
   `normalize=False`, and the shared `method:` key when `normalize=True`. **No synthetic
   `method:` node is added to the graph.**
5. Passing an explicit `semantic_types` without `split_block` reproduces the old behaviour.

## Reasons

- **Graph nodes must be real store chunks.** `find_connections`, centrality and every graph
  consumer hydrate node ids from the metadata store; a synthetic `method:` id would be a
  phantom there. `GraphIntegration._extract_split_block_calls` already elects the *first*
  fragment of a logical method to carry its outgoing AST call edges (`_seen_split_methods`),
  so keying incoming resolver edges to the same fragment gives one node owning both
  directions without a new node kind. `dedup_key` already unifies the fragments everywhere
  a symbol-level identity is needed (search dedupe, golden matching, tracer scoring).
- **Gap-fill beats content parsing.** `content_preview` is truncated to 200 characters, so
  counting signature lines from stored content is unreliable (31/97 groups lose the split
  marker). Gap-fill needs only line numbers, which every chunk has. Validated on the live
  self-index: 97/97 `def` lines land inside their folded span and 0 `class` statements are
  swallowed.
- **Scope is the resolver line map only.** The tracer's own map (`evaluation/tracer/build.py`)
  already included `split_block` with `normalize=True`; folding changes nothing it asserted.

## Consequences

- The LSP resolver now also sees split methods as *callers* (their `def` line is inside a
  mapped span), so its edge count rises as well as its precision. `_find_def_position` scans
  only 10 lines from a span's start; 3 of 97 self-index groups have a gap of 10+ lines
  (long decorators/signatures) and are still skipped as callers. Status quo, tracked as a
  follow-up.
- Injected `calls` edges now land on `split_block` nodes instead of `class` nodes. Scorers
  normalise ids before comparison, so their `method:` form is what the tracer sees.
- Calibration numbers are re-measured on the same substrate with the old and new map
  (`tmp/ab_split_callee.py`, results in `evaluation/RESOLVER_TIER_CALIBRATION_20260902.md`).
- Unit coverage: `tests/unit/evaluation/test_chunk_mapping.py::TestSplitBlockFolding`.
