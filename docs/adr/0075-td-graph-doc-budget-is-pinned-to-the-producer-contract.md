# TD graph doc budget is pinned to the producer contract

Status: accepted
Date: 2026-09-19

## Context

`claude-context-local`'s `chunking.max_file_size_bytes` (`search/config.py`, `ChunkingConfig`) is
the whole-artifact admission gate `chunking/multi_language_chunker.py`'s `chunk_file()` checks
(`:335-347`) *before* `.tdgraph.json` dispatch (`:349`, ADR-0062, Part C): any TD-network export
over this cap never reaches `TDNetworkChunker` and is dropped with a `logger.info` line, invisible
at default log level.

The producer, `TD_Glossary_tox`, declares its own matching admission gate,
`Extensions/OperatorGlossary/tdgraph_contract.py`'s `CHUNKER_MAX_DOC_BYTES`, sized from measured
per-node/per-edge cost on a full-fidelity POPX-scale export (TD_Glossary_tox ADR 0014,
`0014-graph-budget-is-24mib-lossless-first-with-measured-size.md` — a distinct document from this
repo's own ADR-0014, `search_overrides.json` per-project overrides, which shares the number "0014"
only by coincidence of the two repos' independent ADR sequences). That module's docstring states
this repo is expected to keep a matching copy and drift-test it. Before this ADR, no such copy or
test existed here — the consumer's stale 5 MB default and the producer's raised 24 MiB
(25,165,824 B) budget drifted silently, and a real 18,491,105 B lossless POPX export
(`F:/STUDIO_ELSEWHERE/Graph/POPX_1_4_0.tdgraph.json`, 16,649,428 B on an earlier, degraded rung of
the same export) was silently dropped in production on 2026-09-19, before the two sides were
reconciled.

Neither repository imports the other — they are separate git repositories with no packaging
relationship — so this cannot be an import-based assertion; it can only be a literal-vs-literal
pin, checked by a dedicated test on each side. Precedent: ADR-0072 recorded exactly this pattern
for the TD edge-type vocabulary (`tdgraph_contract.py`'s `GRAPH_EDGE_TYPES` vs
`td_network_chunker.py`'s `TD_GRAPH_EDGE_TYPES`).

## Decision

**Raise `ChunkingConfig.max_file_size_bytes`'s default from 5 MB to 24 MiB (25,165,824), matching
`tdgraph_contract.CHUNKER_MAX_DOC_BYTES` exactly.** This is the *global* default, not a
per-project `search_overrides.json` override — every project pays the same cap unless it opts into
a narrower one. The field's declared validation range, `(1024, 104_857_600)` (1 KiB - 100 MiB,
`search/config.py`), is unchanged; 24 MiB sits at 24% of it, well inside the existing ceiling, so
no range widening was needed.

**Pin the number with a literal-vs-literal drift test**,
`tests/unit/chunking/test_td_graph_doc_budget.py`: asserts `ChunkingConfig().max_file_size_bytes
== 25_165_824`; asserts the live, machine-local `search_config.json` (gitignored, the file
`get_chunking_config()` actually serves at runtime, skipped on a fresh checkout where it doesn't
exist) and the checked-in `search_config.json.example` both carry the same number; asserts the
number still falls inside the declared validation range; and two behavioural tests prove a
POPX-sized export actually clears the gate under the new default and would have been dropped
under the old one (monkeypatching `os.path.getsize` rather than growing the checked-in fixture,
which stays small and fast).

**The adaptive-sizing profiler follows this field only at import time, by design.**
`chunking/repo_profiler.py`'s `MAX_FILE_SIZE_BYTES` is seeded once from a bare `ChunkingConfig()`
default (deliberately not `get_chunking_config()`, to keep the constant monkeypatchable in tests)
— a runtime `configure_chunking` change, or a live `search_config.json` reload, does not move the
profiler's already-frozen copy. This ADR does not change that mechanism; it only moves the seed
value the freeze captures at the next process start.

## Consequences

- A future producer-side budget change (a successor to TD_Glossary_tox ADR 0014, if any) that
  lands without a matching change to `_TD_GLOSSARY_TOX_CHUNKER_MAX_DOC_BYTES` in this repo's drift
  test fails CI here instead of silently re-dropping oversized exports — the same failure mode
  that caused the 2026-09-19 incident.
- The listwise reranker's VRAM profile is bounded by `top_k_candidates` x `listwise_doc_max_chars`
  and is independent of index size in that specific sense, but a larger admitted graph changes the
  candidate pool's *composition*, which is a separate, measured concern; see
  `evaluation/RERANKER_TD_TOKEN_DENSITY_20260919.md`.
- `repo_profiler.MAX_FILE_SIZE_BYTES` moves to 24 MiB on the next process start after this change
  ships; nothing calls `configure_chunking` and expects the profiler to follow it mid-process, so
  this is not a behavioural break, only a documentation point (see
  `tests/unit/chunking/test_repo_profiler.py::test_max_file_size_bytes_derives_from_chunking_config`).

## Verification

- `./scripts/test/run_tests.sh tests/unit/chunking/test_td_graph_doc_budget.py -v` -- 6/6 passing,
  including the two new behavioural gate tests.
- `./scripts/git/check_lint.sh --modified-only` -- ruff check, ruff format, markdownlint clean.
- Simulated CI for the gitignored-file guard: `search_config.json` temporarily renamed away, the
  suite re-run (1 skip, rest pass), then restored.
