# Resolve call targets only inside the caller's language group

Status: accepted
Date: 2026-11-24

`GraphIntegration._two_pass_build` resolved every call against one project-wide
`name_to_chunk_ids` map, so a bare name matched chunks of any language. On the
multi-language `hyprzero` index (Rust workspace + Python/TypeScript SDK and QA
scripts) this produced 370,870 python->rust, 44,870 python->typescript and 2,459
rust->python ambiguous `calls` edges, plus 845 python->rust edges tagged exact
(`pathlib.Path(...)` resolved uniquely to a Rust `struct Path`). A stratified
sample of 80 python->rust edges was 0/80 correct
(`evaluation/LANGUAGE_FENCE_A1_SAMPLE_20261124.md`); all 347 cross-language
edges in `twozero-dev` (python->javascript/glsl) were also name collisions. The
languages talk through SDK contracts (sockets, JSON, `osascript`), not direct
calls; hyprzero has no pyo3/ctypes binding to its own Rust code.

Pass 1 now builds one map per language group (python; rust; c+cpp;
javascript+typescript+tsx; glsl; any other language alone), and pass 2 gives each
caller only its group's map. Every lookup site therefore sees the fence: Rust
qualified-first lookup, the common-member blocklists' "unless the project defines
it" checks, unique and same-file resolution, and the ambiguous fan-out. The fence
is always on, with no config field. Real FFI pairs go on
`_CROSS_GROUP_CALL_ALLOWLIST` (a code constant, empty), and only with measured
evidence.

## Considered options

- **A `call_graph` config switch, default on.** Rejected: every sampled
  cross-language edge was wrong, so the switch would only invite turning a defect
  back on, and a new field needs a config spec row and the liveness ratchet
  (ADR-0022).
- **Filter candidates after lookup.** Rejected: it leaves the blocklist and
  qualified-first checks reading the global map (a Rust `Type::m` could still hit a
  C++ `Type::m`, and a Python `get` stays unblocked because Rust defines one).

## Consequences

- TouchDesigner is not affected: `td_network` was already never a call target
  (`PSEUDO_LANGUAGES`), and its links to Python are `scripted_by` relationship
  edges, which do not use this map. Non-call edges had 0 cross-language rows of
  83,930 in hyprzero.
- The Python-only self-index (the benchmark canon substrate) has 0 cross-group
  call edges, so the canon cannot move; no re-pin is owed (ADR-0070 precedent).
- No version marker detects the change: an already-indexed multi-language project
  keeps its old edges until a non-incremental reindex.
- A real cross-language contract (SDK command name -> Rust handler) is still not
  represented; that needs a separate edge kind, not a call edge.
