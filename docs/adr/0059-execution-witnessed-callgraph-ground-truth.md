# Execution-witnessed call-graph ground truth for resolver-tier calibration

Status: accepted
Date: 2026-09-02

## Context

The call graph's edges carry a `resolver_source` (`ast`, `pyan`, `libcst`, `lsp`) and a
`resolver_confidence` (0.5/0.7, 0.75, 0.90, 0.98) that downstream code treats as trust:
`call_graph.min_confidence` gates injection, `run_resolvers()` lets a higher tier overwrite a
lower one, `find_connections` sorts on it, and the graph-enhanced traversal reads it as an edge
weight. None of those confidence values had ever been measured. They are the numbers the
resolvers declare for themselves. The 2026-09-01 ego-membership probe
(`evaluation/EGO_MEMBERSHIP_PROBE_20260901.md`) found 84.6%/86.6% of traversed call edges carry
no resolver tag at all, and every retrieval lever built on top of edge confidence since Track A
has either been byte-identical or rejected. Before spending more on confidence-weighted retrieval,
the tiers need an instrument that says what each one actually gets right.

Hand-labeling every edge is not viable (28k edges on the self-index). TraceEval (arXiv
2605.11006) shows the workable alternative: run the code, record which function really called
which, and treat the witnessed edges as positive labels. Positives only. An edge the trace never
saw is unlabeled, not false, because tests exercise a fraction of the call sites.

Environment facts that shaped the design: the venv Python is 3.11 (`sys.monitoring` is 3.12+);
`tests/` is not indexed, so test functions have no chunk ids; split chunks start at the first body
statement and decorated definitions are chunked from the decorator line, so a function's `def`
line is not a reliable probe for its chunk; `run_resolvers()` overwrites lower tiers, so the
persisted provenance is each tier's marginal contribution, not its standalone output.

## Decision

Add an evaluation-only tracer package, `evaluation/tracer/`, and one CLI,
`scripts/benchmark/traced_callgraph.py`. Nothing in `search/`, `graph/`, `chunking/`, or
`mcp_server/` imports it, and no resolver default changes.

- **Collector** (`collector.py`): `sys.setprofile` plus `threading.setprofile`, `call` events
  only, caller found by walking `frame.f_back` past non-project frames. The walk yields
  `external_depth` (frames between callee and its nearest project caller) so direct and indirect
  edges are separable later. Frames are classified once per code object as project, test, or
  external. Endpoints are raw `(rel_path, def_line, body_line, qualname)` tuples; the collector
  never imports the index.
- **Pytest plugin** (`pytest_callgraph.py`): loaded only via `-p evaluation.tracer.pytest_callgraph`
  plus `--callgraph-trace`. Refuses xdist, unseeded pytest-randomly, and an unset
  `PYTHONHASHSEED`. Installs at collection end, uninstalls before the conftest's session-finish
  subprocess. Normal test runs never load it; `test_plugin_inactive.py` asserts no profiler is
  installed.
- **Build** (`build.py`): intersects three raw runs on endpoint keys (TraceEval's determinism
  check), maps endpoints to chunk ids with the existing `evaluation/chunk_mapping.py` helpers
  trying `body_line` first and `def_line` second, drops self-loops after mapping, and writes
  `evaluation/traced_callgraph.json` with `schema_ok`, `density_ok` (at least two cross-function
  edges), and `deterministic` verdicts.
- **Scoring** (`scoring.py`): per tier, recall against the witnessed direct edges (marginal and
  cumulative down the ladder), a precision lower bound over all stored edges and over the
  caller-executed subset, an instantiation equivalence (`C.__init__` matches `class:C`), a
  lenient `ast_name_only` column for phantom targets that never enters recall, a six-class miss
  taxonomy, a strided per-tier precision sample for hand labeling, and positive-only traced
  goldens in the `run_caller_recall.py` schema with `_meta.semantics =
  "positive-only; missing != absent"`. Every metric definition is embedded in the JSON report.

Results and their interpretation live in `evaluation/RESOLVER_TIER_CALIBRATION_20260902.md`.
Raw runs under `evaluation/traced_runs/` are gitignored; the built graph, report, sample, and
traced goldens are committed only on request.

## Consequences

- The four tiers now have measured recall and a measured precision floor on the self-project.
  The declared confidence ladder can be checked against them before any ω table is published.
- Labels are positive-only. `precision` and `extra` columns from `run_caller_recall.py` are
  meaningless against the traced goldens; gate on recall only. The precision sample exists so a
  human can turn the lower bound into an estimate (`prec_est` formula in the report).
- Coverage follows the unit suite. Code no test executes is unwitnessed and shows up as
  `unwitnessable`, never as a miss. Pre-existing threads, dataclass-generated `__init__`
  (`co_filename "<string>"`), and C-extension calls are blind spots and are listed as such.
- Stored provenance is marginal. A tier's recall here is what it adds over the tiers above it, so
  a low `pyan` number does not mean pyan alone would score low.
- Tracing roughly doubles suite wall time; the plugin is opt-in and never part of CI.
- Upgrade path: on Python 3.12+ the collector can move to `sys.monitoring` with the same payload
  schema; nothing downstream of `collector.to_payload()` changes.
- Follow-ups explicitly out of scope: the pyan retention decision (ADR-0034 stands until the
  calibration is read), a C/C++ tracer, and any change to `min_confidence` or the resolver order.
