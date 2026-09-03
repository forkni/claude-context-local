# Call-Graph Resolver Tuning Reference

> **Version**: v0.23.0 | **Updated**: 2026-08-07
>
> Covers both **pyan3 2.6.0** and **LibCST** APIs as used by the layered
> call-graph resolver pipeline.  Includes accuracy-limitation matrices,
> known wrong-edge classes, and tuning recipes.

---

## Table of Contents

1. [Pipeline Overview](#1-pipeline-overview)
2. [pyan3 2.6.0 API Reference](#2-pyan3-260-api-reference)
3. [LibCST API Reference](#3-libcst-api-reference)
4. [Confidence Tier Matrix](#4-confidence-tier-matrix)
5. [Known Wrong-Edge Classes](#5-known-wrong-edge-classes)
6. [Tuning Recipes](#6-tuning-recipes)
7. [Out-of-Scope Items](#7-out-of-scope-items)

---

## 1. Pipeline Overview

`run_resolvers()` in `chunking/relationships/call_edge_resolver.py` runs four
resolver tiers in ascending confidence order and merges them by
**confidence-precedence** (higher confidence wins on the same `(caller, callee)`
key). **AST edges are not one of these tiers** — they ride a separate
`extract_calls()` / `add_call_edge` rail written during chunking, before
`run_resolvers()` ever runs (see `call_edge_resolver.py`'s module docstring
for the authoritative "two namespaces" explanation):

| Tier | Module | Confidence | Always on? | Notes |
|------|--------|-----------|------------|-------|
| AST (in-house) | `chunking/relationships/call_graph_extractor.py` | tag: `"exact"` / `"ambiguous"` / `"recovered"` (qualitative, **not** numeric) | ✅ | Same-file + import-resolved calls, single pass; not a `CallEdgeResolver`, not part of the keep-max merge |
| pyan wildcard fan-out | `external_call_graph.py` | **0.6** | ✅ (but tagged by `_TrackedVisitor`) | `expand_unknowns` residue, demoted |
| pyan direct | `external_call_graph.py` | 0.75 | via `resolvers` config | Cross-module, graph-inferred |
| LibCST FQN | `libcst_call_graph.py` | 0.90 | via `resolvers` config | Import-aware, per-file |
| LSP / basedpyright | `lsp_call_graph.py` | 0.98 | `lsp_enabled=True` (default) | Most precise; requires `pip install -e ".[lsp]"`, no-ops otherwise |

**Two distinct confidence namespaces** (do not conflate): the AST rail's
`CallEdge.confidence` (a float, always `1.0`, set at extraction time and not
graph-consumed the way resolver confidence is) is unrelated to the qualitative
`"exact"`/`"ambiguous"`/`"recovered"` string tag assigned during graph
injection based on resolution certainty (unique match vs. multiple same-named
candidates) — and both are unrelated to `resolver_confidence`, the numeric
score written by the resolver pipeline below.

Config is read from `CallGraphConfig` (see `search/config.py`).

---

## 2. pyan3 2.6.0 API Reference

### 2.1 Lineage and Python Version

This is the **Technologicat/pyan** revival fork (PyPI `pyan3`), **not** the
older `davidfraser/pyan`.  Python ≥ 3.10 required.  The postprocessing
pipeline is substantially different from the older fork.

### 2.2 `process()` Signature (public API)

```python
pyan.create_callgraph(
    filenames: list[str],          # absolute paths
    root: str | None = None,       # project root for relative module names
    no_defines: bool = False,      # omit "defines" edges
    draw_defines: bool = False,    # include defines edges in graph
    draw_uses: bool = True,        # include uses edges (call edges)
    colored: bool = False,
    grouped: bool = False,
    annotated: bool = False,
    nested_groups: bool = False,
    filename: str | None = None,   # output dot/svg file
    format: str = "dot",           # "dot", "svg", "png", "html"
    logger: logging.Logger | None = None,
) -> pyan.CallGraphVisitor
```

We use the internal `_CallGraphVisitor` / `_TrackedVisitor` directly (via
`uses_edges`) rather than `create_callgraph`, so the output format arguments
do not apply.

### 2.3 `_CallGraphVisitor` Constructor (internal)

```python
_CallGraphVisitor(
    filenames: list[str],
    root: str | None = None,
    logger: logging.Logger | None = None,
    *,
    no_defines: bool = False,
    draw_uses: bool = True,
)
```

**Key invariant**: All postprocessing passes run **unconditionally in
`__init__`**:

```
__init__
  → _analyze()              # AST walk, fills uses_edges
  → contract_nonexistents() # collapses undefined → wildcard nodes
  → expand_unknowns()       # fans out wildcard calls to all matching names
  → collapse_inner()        # collapses nested-scope nodes into parents
  → cull_subsumed()         # drops module-level edges a finer edge already conveys
```

(pyan3 ≥ 2.8 order; 2.6 ran `cull_inherited()` before `collapse_inner()` instead.)
**Only `cull_subsumed` can be disabled via a constructor argument
(`cull_subsumed_edges=False`); the rest always run.**  The
correct precision lever is **read-time filtering** of `uses_edges` (described
in §2.5).

### 2.4 `_TrackedVisitor` — Wildcard-Edge Demotion

`_TrackedVisitor` (in `external_call_graph.py`) is our subclass of
`_CallGraphVisitor`.  It overrides `expand_unknowns()` to snapshot which edges
were created by the fan-out pass, storing them in `.expanded_edges: set[tuple]`.

At injection time, edges whose `(caller, callee)` pair is in `.expanded_edges`
receive `confidence=0.60` instead of the base `0.75`.  This allows
`min_confidence=0.65` to filter them out while keeping direct pyan edges.

### 2.5 `Flavor` Table

`pyan.Flavor` is an `enum.Enum`; each node has `flavor.name`:

| `Flavor.name` | Meaning | Keep as callee? |
|---------------|---------|----------------|
| `FUNCTION` | Defined function | ✅ |
| `METHOD` | Instance/class method | ✅ |
| `STATICMETHOD` | `@staticmethod` | ✅ |
| `CLASSMETHOD` | `@classmethod` | ✅ |
| `COROUTINE` | `async def` | ✅ |
| `CLASS` | Class object (callable) | ✅ (we add CLASS) |
| `NAME` | Unresolved name | ❌ phantom edge |
| `ATTRIBUTE` | Attribute access | ❌ phantom edge |
| `UNKNOWN` | Unknown origin | ❌ phantom edge |
| `UNSPECIFIED` | Default / unset | ❌ phantom edge |
| `IMPORTEDITEM` | Imported symbol | ❌ phantom edge |
| `MODULE` | Module object | ❌ phantom edge |

Our filter is `_CALLEE_FLAVORS = _CALLABLE_FLAVORS | {"CLASS"}` applied at
`external_call_graph.py`.  The six phantom-edge flavors are excluded.

### 2.6 Node Attributes Used for Filtering

```python
node.flavor          # Flavor enum instance
node.namespace       # str | None  (None = wildcard node from contract_nonexistents)
node.defined         # bool (False = external/undefined target, e.g. stdlib stubs)
node.filename        # str | None  (absolute path to defining file)
node.ast_node        # ast.AST | None
node.get_name()      # → str (short name, not FQN)
```

**Guard order** (applied in `external_call_graph.py` before chunk-ID lookup):

1. `_CALLEE_FLAVORS` check on caller (skip if caller is phantom-type)
2. `getattr(caller_node, "namespace", "") is None` → skip (wildcard residue)
3. `not getattr(caller_node, "defined", True)` → skip (undefined caller)
4. Same `namespace is None` check on callee
5. Existing `defined=False` check on callee
6. `flavor.name in _CALLEE_FLAVORS` check on callee

### 2.7 `filter()` Mutation Warning

`_CallGraphVisitor.filter(predicate)` mutates `uses_edges` in place.  We do
**not** call it; we iterate `uses_edges.items()` and apply guards manually so
we can count skipped edges for observability logging.

### 2.8 `ast.parse` Pre-Validation (Mandatory)

pyan has no internal `SyntaxError` guard.  A single unparseable `.py` file
(e.g. TouchDesigner YAML-in-`.py` config) aborts the entire constructor.
Pre-validate every file with `ast.parse()` before passing to
`_TrackedVisitor`.  This is already implemented in `_gather_py_files()`.

### 2.9 Wrong-Edge Classes (pyan-specific)

| Source | Why it happens | Our mitigation |
|--------|---------------|----------------|
| **Wildcard fan-out** | `expand_unknowns` fans out all unresolved calls to every same-named function | `_TrackedVisitor` tags them `confidence=0.6`; filterable via `min_confidence` |
| **Same-name collision** | Two functions named `process()` in different modules — pyan may merge them | Not fully mitigated; use LibCST tier to override |
| **`namespace=None` phantom** | `contract_nonexistents` leaves wildcard nodes with `namespace=None` | Caller/callee `namespace is None` guards in `inject_call_edges` |
| **`defined=False` external** | stdlib stubs and third-party symbols pyan can't locate | `defined=False` callee guard; excluded entirely |
| **Duck-type calls** | `obj.method()` where `obj` type unknown — pyan guesses based on name | Same-name collision fallout; demoted to 0.6 or overridden by LibCST at 0.90 |

---

## 3. LibCST API Reference

### 3.1 `FullRepoManager` Signature

```python
FullRepoManager(
    repo_root_dir: str | Path,       # project root — must be str, not Path object
    paths: list[str],                # list of ABSOLUTE file paths in the repo
    providers: set[type[BaseMetadataProvider]],
    timeout: int = 5,                # seconds; only affects TypeInferenceProvider
    use_pyproject_toml: bool = False, # ← see §3.3
)
```

After construction, call `manager.resolve_cache()` to front-load the entire
batch cache in one pass (recommended; reduces per-file overhead in large
projects):

```python
manager = FullRepoManager(
    repo_root_str,
    abs_keys,
    {FullyQualifiedNameProvider},
    use_pyproject_toml=use_pyproject_toml,
)
manager.resolve_cache()  # front-load batch cache
```

### 3.2 Provider Comparison

| Provider | FQN Source | Resolution Quality | Import-site only? |
|----------|-----------|-------------------|------------------|
| `QualifiedNameProvider` | Scope analysis | Module-relative names | No (resolves `from x import y` targets) |
| **`FullyQualifiedNameProvider`** | Repo root + imports | Absolute dotted names | Yes (re-exports not chased) |
| `ScopeProvider` | Scope graph | No FQNs (scope metadata only) | — |
| `PositionProvider` | AST | Line/column offsets | — |
| `TypeInferenceProvider` | pyre + watchman | Type-aware, most precise | ❌ Windows-incompatible (see §3.6) |

We use **`FullyQualifiedNameProvider`** only. `PositionProvider` was dropped
(profiling measured it as ~10% marginal cost on top of FQN resolution — its
own whole-tree `visit_batched` pass per file, just to populate the edge's
call-site `line`). Every libcst-sourced edge now reports `line=0`, which the
injection seam treats as "unknown" and omits from the output payload rather
than an error (see `search/index_write_stage.py` / `subgraph_extractor.py`).

`FullyQualifiedNameProvider` produces **import-site names** — the name that
`import x.y.z` would resolve to.  It does **not** chase re-exports
(`__init__.py` re-exporting a symbol under a shorter name).  This is a
fundamental limitation, not a bug.

### 3.3 `use_pyproject_toml` Semantics

| Project layout | Correct value | Effect |
|----------------|--------------|--------|
| **Flat** (`mypkg/mod.py`) | `False` (default) | FQNs relative to repo root: `mypkg.mod` |
| **Src-layout** (`src/mypkg/mod.py`) | `True` | FQNs from nearest `pyproject.toml`: `mypkg.mod` (not `src.mypkg.mod`) |

For this repository (flat layout): `use_pyproject_toml=False` is correct.
Set `use_pyproject_toml=True` in `CallGraphConfig` for src-layout projects.
The setting is exposed as a config field and forwarded to `LibCSTResolver.__init__`.

### 3.4 `MetadataWrapper` Safety Rule

```python
MetadataWrapper(module, unsafe_skip_copy=True, cache=resolved_cache)
```

`unsafe_skip_copy=True` skips a deep-copy of the CST.  It is **safe and
correct** on fresh `cst.parse_module()` output because the parsed module is
not shared between wrappers and will not be mutated before the wrapper's
visitor finishes.  On pre-existing or mutated CSTs, set `unsafe_skip_copy=False`.

### 3.5 FQN for Nested Definitions

`FullyQualifiedNameProvider` produces:

```
module.outer.<locals>.inner   # for defs nested inside another function
module.Klass.method           # for methods
```

The `<locals>` segment is present and non-empty for closures.  We filter it:
in `_CallVisitor`, any callee whose FQN contains `<locals>` is skipped
(cannot map to a chunk without type info).  The already-implemented
`_resolve_self_call` synthesizes `ClassName.method` from `self.method()` and
`cls.method()` calls.

### 3.6 `TypeInferenceProvider` — Rejected for Windows

`TypeInferenceProvider` requires a running **pyre** type-checker with
**watchman** file-watching.  Neither is practical on Windows.  Do **not** add
it to the provider set; `FullyQualifiedNameProvider` is the highest-quality
provider available without a daemon.

### 3.7 Structural Limitations (LibCST tier)

| Limitation | Effect | Mitigated by |
|------------|--------|--------------|
| FQN = import-site name | Re-exports have wrong FQN | Accept — document, no fix |
| No receiver type resolution | `obj.method()` → bare FQN only | LSP tier (0.98) |
| `<locals>` defs excluded | Closures not mapped | Filtered pre-lookup |
| Multi-assign unpacking | `a, b = fn()` → single FQN | Accept |

---

## 4. Confidence Tier Matrix

Interpreting the tier table: "Accuracy" means fraction of injected edges that
are real call relationships.  "Recall" means fraction of true call
relationships captured.

| Tier | Confidence | Accuracy | Recall | Primary gap |
|------|-----------|----------|--------|-------------|
| AST (in-house) | qualitative tag, not numeric — see §1 | Not measured on this scale (baseline rail, not a `run_resolvers()` tier) | Same-file + import-resolved cross-file | Dynamic dispatch, re-exports, shadowed names (§5.3) |
| pyan wildcard fan-out | **0.6** | ≈ 40% | High | Many phantom edges; demoted |
| pyan direct | 0.75 | ≈ 75% | High | Same-name collisions; duck typing |
| LibCST FQN | 0.90 | ≈ 92% | Medium–high | Re-exports; type-polymorphic calls |
| LSP / basedpyright | 0.98 | ≈ 98% | High | Multi-file type inference, slow |

**Merge behavior**: when two tiers report the same `(caller, callee)` pair,
the higher-confidence entry wins (overrides the lower one).

---

## 5. Known Wrong-Edge Classes

### 5.1 pyan

See §2.9.

### 5.2 LibCST

| Source | Description |
|--------|-------------|
| **Re-export mismatch** | `from pkg import A` where `A` is re-exported — FQN may point to the re-export file, not the implementation |
| **Method on unknown receiver** | `obj.method()` where `obj` type unknown → FQN is `module.method` (wrong) or not resolved |
| **First-class function** | `fn = some_func; fn()` → FQN of `fn` is not resolved |
| **`super()` calls** | Resolved to parent-class method only when parent is in same file |

### 5.3 AST

| Source | Description |
|--------|-------------|
| **Shadowed names** | Local variable shadows imported name — may produce wrong cross-file edge |
| **Conditional imports** | `if TYPE_CHECKING:` block imports generate edges even for runtime-absent paths |

---

## 6. Tuning Recipes

### 6.1 `min_confidence` — Injection Floor

Set in `search_config.json` under `call_graph`:

```json
"call_graph": {
  "resolvers": ["pyan", "libcst"],
  "min_confidence": 0.65
}
```

| Goal | `min_confidence` | Effect |
|------|-----------------|--------|
| Keep all edges | `0.0` | No filtering |
| Drop pyan wildcard fan-out (default) | `0.65` | Drops 0.60-tagged edges; keeps direct pyan (0.75) |
| Drop all pyan edges | `0.80` | Keeps LibCST (0.90) and LSP (0.98) only |
| LSP-only (highest precision) | `0.95` | Requires `lsp_enabled: true` |

**Observability**: this floor filters on `resolver_confidence` (the resolver
pipeline's numeric precedence value — not the qualitative `confidence` tag
`exact`/`recovered`/`ambiguous` written by the AST chunking pass). Logged at
INFO when it drops at least one edge, DEBUG otherwise:

```
[CALL_EDGES] resolver_confidence floor=0.65: dropped 142/210 edge(s) below threshold (ladder: pyan-wildcard 0.60 / pyan 0.75 / libcst 0.90 / lsp 0.98)
```

### 6.2 `use_pyproject_toml` — Src-Layout Projects

```json
"call_graph": {
  "use_pyproject_toml": true
}
```

Enable only for src-layout projects (`src/mypkg/`).  For flat-layout (this
repo, `mypkg/`), leave at `false` (default).  Incorrect `use_pyproject_toml`
causes systematic wrong FQNs from LibCST — every cross-package call would map
to a non-existent chunk ID.

### 6.3 Disabling Resolvers

```json
"call_graph": {
  "resolvers": ["pyan"]
}
```

`resolvers` controls which optional resolvers load.  AST is always-on.
Valid values: `"pyan"`, `"libcst"`, `"lsp"`.  Remove a resolver by removing
its name from the list.

**`resolvers` is `benchmark_locked`** (`search/index_probe.py`'s
`FORBIDDEN_AUTO_TUNE_KEYS`) as of the 2026-09-03 call-graph verification
session: `RESOLVER_TIER_CALIBRATION_20260902.md` §11/§12 execution-witnessed
scoring considered dropping pyan (post-gate `prec_lb_cov` 0.2510) and decided
it stays (0.6032 after the CLASS call-position gate, `recall_marginal`
flat). This is an auto-tune interdiction, not a human-editing freeze — the
value above remains a legitimate manual choice for a project that wants a
faster/lower-precision index; only `search/index_probe.py`'s automated
probe is barred from rewriting it.

### 6.4 LSP Tier

```json
"call_graph": {
  "lsp_enabled": true,
  "lsp_timeout_seconds": 30.0,
  "lsp_total_timeout_seconds": 180.0
}
```

basedpyright must be installed (`pip install basedpyright`) and the LSP server
must be startable.  On Windows, `lsp_call_graph.py` falls back to the venv
`basedpyright` binary if the system-level one is absent.

`lsp_timeout_seconds` bounds each individual JSON-RPC request; increase it for
large codebases where a single `callHierarchy/outgoingCalls` type-check pass
takes longer than 30s. `lsp_total_timeout_seconds` is the separate aggregate
budget for the *whole* LSP resolver pass across all files — if exceeded, the
basedpyright subprocess is force-killed and whatever edges were collected so
far are kept (safe, since LSP only upgrades confidence on edges pyan/libcst
already found).

**Requires v0.14.0+** — earlier builds silently resolved 0 edges due to three
protocol bugs (probe at column 0 instead of the symbol-name position, missing
JSON-RPC ID correlation, and `file:///f%3A/...` percent-encoded drive-colon
handling on Windows).

**Diagnostics.** Every LSP session emits one INFO line:

```text
[LSP] probes=N null_prepares=N items=N outgoing_calls=N dropped_uri=N dropped_no_chunk=N
```

| Counter | Meaning |
|---------|---------|
| `probes` | Chunks for which `prepareCallHierarchy` was attempted |
| `null_prepares` | Chunks skipped (module / split-block continuations with no def/class header) |
| `items` | Chunks where `prepareCallHierarchy` returned at least one item |
| `outgoing_calls` | Total callee references returned by `callHierarchy/outgoingCalls` |
| `dropped_uri` | Callees whose URI could not be mapped to a local path |
| `dropped_no_chunk` | Callees resolved to a local path but with no enclosing chunk (`.venv/`, unindexed files) |

Health signals:

- `dropped_uri ≈ outgoing_calls` — URI-to-path conversion is failing; check Python version and basedpyright version.
- Large `dropped_no_chunk` is **normal** — most callees land in `.venv/` site-packages which are not indexed.
- Zero resolved edges with `items > 0` and `dropped_uri = 0` — basedpyright stderr tail is logged at WARNING.

### 6.5 pyan Budget

```json
"call_graph": {
  "pyan_total_timeout_seconds": 600.0,
  "pyan_seconds_per_file": 2.5,
  "pyan_total_timeout_cap_seconds": 3600.0
}
```

Mirrors the LSP budget trio in §6.4, same derivation shape:
`budget = min(cap, max(floor, seconds_per_file * n_files))`, computed in
`PyanResolver.resolve()` from the scoped file count.

Unlike LSP's partial results, **a pyan pass that hits its deadline is
abandoned entirely** — `resolve()` returns `[]` and logs:

```text
[PYAN] budget 600.0s exceeded after 842/1483 files — abandoning pyan tier (libcst/lsp edges unaffected)
```

This is deliberate: without a completed `postprocess()`, `uses_edges` still
holds unresolved imports and wildcard placeholders left over from
`expand_unknowns`, so a partial pass is not comparable to a complete one the
way partial LSP results are (LSP only ever *upgrades confidence* on edges
the earlier tiers already produced). Increase `pyan_seconds_per_file` if a
large project legitimately needs more than the default ~2.5s/file; the
default floor (600s) already covers most projects, and the cap (3600s) is a
runaway guard, not a throttle — raising it only matters for projects larger
than the cap would otherwise allow.

The deadline is checked cooperatively at each file boundary
(`_prescan_one`, `process_one`) and at the top of the two whole-project
stages (`resolve_base_classes`, `postprocess`) — not via a hard kill, since
force-terminating the child process mid-analysis could leave pyan's internal
scope state inconsistent. `expand_unknowns` and its postprocess siblings
have no interior polling point, so the budget can overshoot by up to one
postprocess step.

**Progress observability.** Both pyan and LibCST run in a child process and
previously produced no log output there at all — the parent's `Logger`
cannot cross the process boundary, so every `[PYAN]`/`[LIBCST]` line was
silently dropped. All three resolvers (pyan, LibCST, LSP) now emit
throttled heartbeat lines (at most one per ~15s) to stderr for every
long-running phase:

```text
[PYAN] pass 1: 302/1483 files (20%), 24s elapsed, ~1m35s remaining
[PYAN] resolve_base_classes: 3.2s elapsed
[PYAN] postprocess: expand_unknowns took 41.7s
[LIBCST] resolve_cache: 1.1s elapsed
[LIBCST] 890/1483 files (60%), 52s elapsed, ~35s remaining
[LSP] 12000/18892 chunks (63%), 94s elapsed, ~55s remaining
```

pyan reports five distinct phases, matching `process()`'s structure
(§2.2): `prescan`, `pass 1`, `pass 2` (all per-file), plus the two
whole-project stages `resolve_base_classes` and `postprocess` (five named
sub-steps). No gap in that sequence should exceed the ~15s heartbeat
interval on a healthy run.

### 6.6 Recommended Defaults by Use Case

| Use case | Settings |
|----------|---------|
| **Fastest indexing (lowest precision)** | `resolvers: ["pyan"]`, `lsp_enabled: false`, `min_confidence: 0.0` |
| **Balanced (default)** | `resolvers: ["pyan", "libcst"]`, `lsp_enabled: true`, `min_confidence: 0.65` |
| **Highest precision (slower)** | `resolvers: ["pyan", "libcst"]`, `lsp_enabled: true`, `min_confidence: 0.80` (drops all pyan; §6.1) |
| **Src-layout project** | Add `use_pyproject_toml: true` to any of the above |

`lsp_enabled` defaults to `true` — it only takes effect (and only costs the extra indexing time)
when the `[lsp]` extra is installed (`pip install -e ".[lsp]"`); otherwise the resolver's
`available()` probe fails and it silently no-ops, so the "Balanced (default)" row above behaves
identically to the pre-LSP pipeline on a machine that never installed the extra.

Every `resolvers` value in this table is still a valid **manual** choice — see §6.3's
`benchmark_locked` note: the lock only blocks `search/index_probe.py`'s automated probe from
rewriting `resolvers`, not a human deliberately picking one of these presets.

### 6.7 `inject_on_incremental` — Resolver Edges on Incremental Passes (ADR-0044)

```json
"call_graph": {
  "inject_on_incremental": false
}
```

Incremental passes prune and re-add graph nodes for changed files, which restores only the
always-on AST edges — resolver-injected pyan/LibCST/LSP edges for touched files are lost until
the next full pass. `true` re-runs the injection pipeline on every incremental pass: ADR-0044
measured +1.58 s on a 4-file fixture, and `evaluation/INJECT_ON_INCREMENTAL_COST_20260903.md`
re-measured on this 233-file repo at +36-38 s per pass (~10-19x the opt-out baseline), flat in K
because the resolver pass rescans the whole indexed set regardless of how many files changed —
the default keeps incremental passes cheap. Gated in `IndexWriteStage.inject_call_edges_if_enabled`
(ADR-0052). **`benchmark_locked`** (`[latency]`) as of 2026-09-03 — ADR-0044's reopening condition
(a changed-file-scoped injection variant landing) is unmet, so the auto-tuner will not flip this;
a human may still set it manually.

### 6.8 Traversal Gates — `TraversalPolicy`

The gates that decide which *stored* edges ego-graph and multi-hop expansion may walk live on
`GraphEnhancedConfig`, not `CallGraphConfig`, and travel through the graph layer as one frozen
`TraversalPolicy` object (`graph/traversal_policy.py`; seam
`CodeGraphStorage.get_neighbors_ranked(chunk_id, policy)`):

| Key | Default | Effect |
|-----|---------|--------|
| `graph_enhanced.min_traversal_confidence` | `0.0` | Skip edges whose resolver confidence is below the floor (A2 arm; structurally inert at depth 1 with floor ≤ 0.65) |
| `graph_enhanced.traversal_confidence_weighting_enabled` | `false` | Weight BFS priority by edge confidence (A2 arm, measured neutral) |
| `graph_enhanced.drop_ambiguous_traversal_edges` | `false` | Drop `tag:ambiguous` call edges during traversal — the traversal-time counterpart of `find_connections(hide_ambiguous=True)`, which only filters display. Replay-screened 2026-09-02 (`evaluation/AMBIGUOUS_EDGE_REPLAY_20260902.md`), benchmark-locked, off pending a live A/B |

`TraversalPolicy.ego(...)` and `.graph_hop(...)` derive these from config at the two production
call sites; `policy.gates_edges` short-circuits the per-edge lookups when no gate is armed, so
the defaults cost nothing.

---

## 7. Out-of-Scope Items

These were evaluated and deliberately excluded from the implementation:

| Item | Reason |
|------|--------|
| `TypeInferenceProvider` / pyre tier | Requires pyre + watchman; Windows-incompatible |
| Fan-out cap per caller | Deferred until evidence of need; add to `_TrackedVisitor` if required |
| `pyan.Flavor.is_method_call` | `is_method` flag in `ResolvedEdge` is caller-flavor-based, not receiver-based — note in future refactor |
| LSP per-request timeout thread leak | Pre-existing concern, separate tracking item |
