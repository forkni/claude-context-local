# Unify RelationshipAnalyzer's three result-row projections

Status: accepted
Date: 2026-09-06

## Context

A `/improve-codebase-architecture` pass surfaced six candidates (C1-C6) from a hot-spot scan of
this repo. C1 landed as [ADR-0064](0064-index-write-target-protocol-seam.md). This ADR is the
review's C2 — **a different candidate from [ADR-0030](0030-deepen-config-searcher-seam.md)'s own
C2** (unify the retrieval funnel widths), which is unrelated and untouched here. Disambiguating by
name only: this document's "C2" is result-row projection unification, nothing else.

`search/relationship_analyzer.py` held three near-clone adapters that turn a search result into a
display dict — `_result_to_dict`, `_extract_result_info`, `_extract_symbol_info`. All three
repeated the same `hasattr(result, "metadata")` vs. `getattr(result, "file_path", getattr(result,
"relative_path", ""))` bifurcation, the same `lines` f-string, and the same `kind` extraction, but
silently disagreed on three axes: whether `file` was passed through `normalize_path` (backslash to
forward slash — a real, Windows-only divergence, since chunk metadata carries an absolute OS path
via `chunking/multi_language_chunker.py`), whether a `score` key was present, and whether a `name`
key was present.

Tracing every call site showed the divergence was a **wire-output inconsistency, not a filtering
bug**: `matches_directory_filter` is fed only by `_result_to_dict` output (the adapter that already
normalized), and it self-normalizes its own input regardless (`search/filters.py`). The two
divergent siblings feed response payload fields directly and never reach filtering. So unifying
`normalize_path` behavior could only ever change the `file` string inside `find_connections`
payload entries — never retrieval, ranking, or result-set membership.

`search/relationship_analyzer.py:method:RelationshipAnalyzer._result_to_dict` is a grade-2 golden
chunk (referenced in both `evaluation/golden_dataset.json` and `golden_dataset_expanded.json`,
including Q65: "what code calls normalize_path in utils" — graded specifically *because*
`_result_to_dict` calls `normalize_path`). Golden chunk IDs carry no line range
(`file:kind:QualifiedName`), so line shifts from refactoring are harmless; only a rename, move, or
deletion would break the gold reference. `_extract_result_info` and `_extract_symbol_info` have
zero golden references in either dataset.

## Decision

**Two separate commits, two hats** — a pure structural refactor first, a reviewed behavior change
second, so the wire-visible half stays independently revertible.

**Commit 1** (`1ee386a`, behavior-preserving): extracted a shared `_project_result(result,
chunk_id, *, include_score, name=None)` static method holding the common `hasattr`/`getattr`
bifurcation, `lines` f-string, and `kind` extraction. `_extract_result_info` and
`_extract_symbol_info` became one-line delegations. `_result_to_dict` kept its dict-passthrough
branch (`isinstance(result, dict)`) in place and first — it mutates the input dict and returns it,
and that aliasing had to be preserved — then delegates its two object branches to the helper.
`_project_result` never calls `normalize_path` itself; each adapter applies it (or doesn't) as its
own post-step, preserving every divergence exactly. `_result_to_dict` kept its name and stayed a
method to protect its golden chunk_id. The literal `normalize_path` call inside `_find_similar`
(a fourth, inlined sibling) was deliberately left untouched — folding it into the shared helper
would have diluted the same golden-chunk call-graph signal Q65 depends on.

Gate 0 (`4869671`, committed *before* any production edit): a syrupy `JSONSnapshotExtension`
snapshot suite (`tests/unit/search/test_result_projection_snapshot.py`, following this repo's own
`tests/unit/mcp_server/test_search_results_snapshot.py` precedent) plus plain `unittest.TestCase`
branch/axis assertions (`tests/unit/search/test_relationship_analyzer.py`), covering dict input,
object-with-metadata, object-without-metadata, missing `file`, and falsy `file` for all three
adapters — pinning the pre-refactor divergence so Commit 1's refactor is provably byte-identical.
One correction made while building this: the `snapshot` pytest fixture is not injected into
`unittest.TestCase` methods, so the snapshot-shaped assertions had to live in their own plain
pytest module, not alongside the existing `TestCase`-based suite.

**Commit 2** (`bb665ac`, the reviewed behavior change): added the `normalize_path` post-step to
`_extract_result_info` and `_extract_symbol_info`, guarded on a truthy `file` value only
(`normalize_path(file_value) if file_value else <unchanged>`) — deliberately *not* copying
`_result_to_dict`'s falsy-to-`""` coercion, so the only wire delta is `\` → `/` inside `file`
strings; a `None`/falsy `file` value still passes through both siblings exactly as before. This
keeps the change scoped to path-separator normalization alone, per the plan's own wire-diff gate.

## Consequences

- `_result_to_dict`, `_extract_result_info`, and `_extract_symbol_info` now agree on `file`
  normalization; they still intentionally differ on `score` (only `_result_to_dict`) and `name`
  (only `_extract_symbol_info`) — those axes were never in scope.
- Gate 0's snapshots and characterization tests updated in lockstep with Commit 2: one snapshot
  file changed (`_extract_result_info`/`_extract_symbol_info`'s `file` value gained the forward
  slash), the other two snapshots (dict passthrough, falsy/missing `file`) were unchanged —
  confirming no delta beyond the intended one. Four `test_relationship_analyzer.py` tests renamed
  and re-pinned from "does not normalize" to "normalizes" expectations.
- Verification used live MCP `find_connections` wire-diff checks (not a benchmark canon re-pin, per
  the plan's own risk analysis) both before Commit 1 and after Commit 2: confirmed `_result_to_dict`
  keeps `normalize_path` as a direct callee throughout, and confirmed `_extract_result_info`/
  `_extract_symbol_info` gained `normalize_path` as a direct callee only after Commit 2 — matching
  the intended structural change exactly.
- Full unit suite green at every step (4,652 passed, 2 skipped, unchanged from baseline); lint,
  format, and pyrefly clean on both commits.
- No benchmark re-run, no canon re-pin: this is a wire-output-only change confined to
  `find_connections` payload `file` strings, never reaching filtering, retrieval, ranking, or
  result-set membership (see Context).

## Out of scope

- The inlined `normalize_path` call inside `_find_similar` — left untouched to protect the Q65
  golden-chunk call-graph signal (see Decision).
- The `_project_result` helper's placement: kept as a private method on `RelationshipAnalyzer`, not
  promoted to a shared module. It has exactly one consumer; `search/subgraph_extractor.py`'s
  `_node_dict`/`_edge_dict` and `search/searcher.py`'s `_create_search_result` are related
  projections but were not swept into this change — promoting the helper now would be speculative
  generality with a single call site.
- `_result_to_dict`'s dict-passthrough branch has no falsy guard before `normalize_path` (a
  `dict` with `file=None` raises `AttributeError`) — a latent bug, pinned as-is by Gate 0, not
  fixed here. The object branches' existing `if file_path else ""` guard was not backported to it.
- `mcp_server/tools/result_view.py`'s `_format_search_results` — already pinned by its own snapshot
  suite, already internally consistent, untouched.
- `_NEVER_DROP_FILTERED_KEYS` (`relationship_analyzer.py:1031`, 2 keys) and the differently-named
  `NEVER_DROP_EMPTY_KEYS` (`mcp_server/output_formatter.py:31-32`, 4 keys) are two divergent
  constants, not one triplicated definition; `search/types.py:338` carries only a prose comment,
  no constant — not folded in.
