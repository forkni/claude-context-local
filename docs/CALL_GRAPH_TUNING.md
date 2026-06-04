# Call-Graph Resolver Tuning Reference

> **Version**: v0.14.0 | **Updated**: 2026-06-03
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
key):

| Tier | Module | Confidence | Always on? | Notes |
|------|--------|-----------|------------|-------|
| AST (definition) | `ast_call_graph.py` | 0.5 | ✅ | Same-file calls only |
| AST (cross-file) | `ast_call_graph.py` | 0.7 | ✅ | FQN-based cross-file |
| pyan wildcard fan-out | `external_call_graph.py` | **0.6** | ✅ (but tagged by `_TrackedVisitor`) | `expand_unknowns` residue, demoted |
| pyan direct | `external_call_graph.py` | 0.75 | via `resolvers` config | Cross-module, graph-inferred |
| LibCST FQN | `libcst_call_graph.py` | 0.90 | via `resolvers` config | Import-aware, per-file |
| LSP / basedpyright | `lsp_call_graph.py` | 0.98 | `lsp_enabled=True` | Most precise; opt-in |

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
  → cull_inherited()        # removes edges redundant due to inheritance
  → collapse_inner()        # collapses nested-scope nodes into parents
```

**None of these passes can be disabled via constructor arguments.**  The
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
| **`namespace=None` phantom** | `contract_nonexistents` leaves wildcard nodes with `namespace=None` | Caller/callee `namespace is None` guards in `_inject_call_edges` |
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
    {FullyQualifiedNameProvider, PositionProvider},
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

We use **`FullyQualifiedNameProvider` + `PositionProvider`** only.

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
| AST in-file | 0.5 | ≈ 90% | Low — same-file only | Cross-module calls missed |
| AST cross-file | 0.7 | ≈ 85% | Medium | Dynamic dispatch, re-exports |
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
  "min_confidence": 0.0
}
```

| Goal | `min_confidence` | Effect |
|------|-----------------|--------|
| Keep all edges (default) | `0.0` | No filtering |
| Drop pyan wildcard fan-out | `0.65` | Drops 0.60-tagged edges; keeps direct pyan (0.75) |
| Drop all pyan edges | `0.80` | Keeps LibCST (0.90) and LSP (0.98) only |
| LSP-only (highest precision) | `0.95` | Requires `lsp_enabled: true` |

**Observability**: dropped edges are logged at INFO level:

```
[CALL_EDGES] min_confidence=0.65 dropped 142 edge(s) (confidence below threshold)
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

### 6.4 LSP Tier

```json
"call_graph": {
  "lsp_enabled": true,
  "lsp_timeout_seconds": 30.0
}
```

basedpyright must be installed (`pip install basedpyright`) and the LSP server
must be startable.  On Windows, `lsp_call_graph.py` falls back to the venv
`basedpyright` binary if the system-level one is absent.

### 6.5 Recommended Defaults by Use Case

| Use case | Settings |
|----------|---------|
| **Fast indexing, any precision** | `resolvers: ["pyan"]`, `min_confidence: 0.0` |
| **Balanced (default)** | `resolvers: ["pyan", "libcst"]`, `min_confidence: 0.0` |
| **High precision** | `resolvers: ["pyan", "libcst"]`, `min_confidence: 0.65` |
| **Highest precision (slow)** | `resolvers: ["pyan", "libcst"]`, `lsp_enabled: true`, `min_confidence: 0.80` |
| **Src-layout project** | Add `use_pyproject_toml: true` to any of the above |

---

## 7. Out-of-Scope Items

These were evaluated and deliberately excluded from the implementation:

| Item | Reason |
|------|--------|
| `TypeInferenceProvider` / pyre tier | Requires pyre + watchman; Windows-incompatible |
| Fan-out cap per caller | Deferred until evidence of need; add to `_TrackedVisitor` if required |
| `pyan.Flavor.is_method_call` | `is_method` flag in `ResolvedEdge` is caller-flavor-based, not receiver-based — note in future refactor |
| LSP per-request timeout thread leak | Pre-existing concern, separate tracking item |
| `character: 0` LSP probe position | Pre-existing; affects accuracy but not scope of this work |
