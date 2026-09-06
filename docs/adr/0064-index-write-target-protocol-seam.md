# Name the `IndexWriteStage` write-target seam with an `IndexWriteTarget` protocol

Status: accepted
Date: 2026-09-06

## Context

[ADR-0030](0030-deepen-config-searcher-seam.md) surfaced C1 (split the index-write half out of
`HybridSearcher`) alongside C3/C4 but explicitly deferred it as "not part of this round." A
`/improve-codebase-architecture` pass re-surfaced the same seam independently, verified against the
live 2026-09-06 canon substrate (235 files / 2,956 chunks), and this ADR closes the deferral —
narrower in scope than ADR-0030's original framing.

`IndexWriteStage.__init__` (`search/index_write_stage.py`) annotated its constructor parameter as
`indexer: Indexer`, where `Indexer` was imported as `from .indexer import CodeIndexManager as
Indexer` — but the runtime object passed in is a `HybridSearcher` whenever
`config.search_mode.enable_hybrid` is true (`mcp_server/tools/index_handlers.py:981`). The type was
a lie, stated correctly only in prose (`index_handlers.py:138`'s docstring: "indexer: HybridSearcher
or CodeIndexManager"; `incremental_indexer.py:458` says the same). Because the interface was never
named, `IndexWriteStage.inject_call_edges` and `.retarget_td_script_edges` reached through a
**private** attribute twice — `getattr(self._indexer, "_graph", None)` — then a message chain
`_indexer → dense_index → metadata_store` for the metadata store. Nine `hasattr`/`getattr`
capability probes elsewhere stood in for the same missing declaration.

Two adapters already exist and already satisfy a shared shape — `CodeIndexManager` (the plain
on-disk index) and `HybridSearcher` (which forwards each member to its own wrapped
`CodeIndexManager`/`IndexSynchronizer`) — so this is a real seam, not a hypothetical one. The
deletion test confirms it: `HybridSearcher`'s six one-line forwards (`save_indices`,
`validate_index_sync`, `resync_bm25_from_dense`, `resync_if_desynced`, `load_indices`, plus
`clear_index`/`remove_files`) exist only to satisfy this duck type; deleting them reintroduces the
complexity at both consumers.

### Narrowed scope

The original architecture-review candidate also proposed unifying the full-index and incremental
passes' call sequences via Replace Conditional with Polymorphism — the full pass calls
`IndexWriteStage.run()` as a whole (`incremental_indexer.py:814`), while the incremental pass never
calls `run()`, hand-sequencing five of the stage's methods across two of its own methods instead.
That unification is **not** part of this change. The two passes' sequencing has already documented,
intentional behavioural differences (call-edge injection is full-only per `config.py:1769-1770`'s
own comment, gated by the separate `call_graph.inject_on_incremental` opt-in) that a polymorphism
unification would need to either preserve as an explicit branch or resolve as its own reviewed
change — not bundled into a seam-naming refactor. This ADR is seam-fix-and-dedup only.

## Decision

Declare a `@runtime_checkable` `Protocol` in `search/index_write_stage.py`, directly modeled on
`search/resource_refresh.py`'s `ResourceRefresher` (ADR-0053) — same shape, same "two adapters
satisfy this structurally, no subclassing, no cross-import" framing:

```python
@runtime_checkable
class IndexWriteTarget(Protocol):
    storage_dir: Path

    @property
    def graph_integration(self) -> GraphIntegration | None: ...

    @property
    def metadata_store(self) -> MetadataStore: ...

    def add_embeddings(self, embedding_results: list[EmbeddingResult]) -> None: ...
    def save_indices(self) -> None: ...
    def resync_if_desynced(self, log_prefix: str = ...) -> tuple[bool, int]: ...
```

`graph_integration` and `metadata_store` are **required** members — not optional/duck-typed via
`getattr` — because both adapters always construct them at `__init__` time. `metadata_store` is
never `None` on either adapter (`CodeIndexManager` constructs it unconditionally; `HybridSearcher`
forwards to its always-constructed `self.dense_index.metadata_store`). `graph_integration` is typed
`GraphIntegration | None` because `HybridSearcher._graph` can genuinely be `None` on the exception/
fallback paths where graph storage failed to load — unlike `CodeIndexManager._graph`, always
constructed. Required means "the member must exist," not "the value must be non-`None`" — the same
pattern `HybridSearcher.graph_storage` already used.

Both adapters gain a public `graph_integration` property (`CodeIndexManager` in `search/indexer.py`,
`HybridSearcher` in `search/hybrid_searcher.py`) forwarding to their existing `self._graph`, so
callers reach it without touching a private attribute. `IndexWriteStage.__init__`'s parameter
changed from `indexer: Indexer` to `indexer: IndexWriteTarget`; the lying `Indexer` alias import was
deleted. `inject_call_edges` and `retarget_td_script_edges` now read `self._indexer.graph_integration`
and `self._indexer.metadata_store` directly — zero `getattr(self._indexer, ...)` probes remain in
`index_write_stage.py`.

Separately, `IncrementalIndexer`'s full-index and incremental-add paths had already drifted apart on
two pre-write steps that should have been identical: supported-file filtering (`_is_supported_file`
existed but the incremental path re-implemented it inline) and the unmatched-include-pattern warning
loop (byte-identical except for the log prefix). Both are now shared: `_get_supported_files` (already
existed, now actually called from both sites) and a new `_warn_unmatched_patterns(path_filter,
log_prefix)` static helper.

## Consequences

- `getattr(self._indexer, "_graph", None)` in `index_write_stage.py`: **2 → 0**.
- The `Indexer` type alias (`from .indexer import CodeIndexManager as Indexer`): deleted. The
  constructor parameter's annotation now matches what is actually passed at every call site.
- `CodeIndexManager` and `HybridSearcher` each gain one new public property
  (`graph_integration`); `HybridSearcher` also gains `metadata_store` (a one-line forward to
  `self.dense_index.metadata_store`, matching its existing `graph_storage` property's shape).
- Test doubles across `tests/unit/search/test_index_write_stage.py` that wired `indexer._graph =
  ...` / `indexer.dense_index.metadata_store = ...` were rewired to
  `indexer.graph_integration = ...` / `indexer.metadata_store = ...`, matching the new Protocol
  surface. `Mock()` auto-vivifies arbitrary attributes silently, so a stale fixture would not have
  raised `AttributeError` — `test_gate_on_without_graph_is_zero` uses `Mock(spec=["graph_integration"])`
  to make the interface constraint explicit rather than relying on production code reading the
  right name by chance.
- `_add_new_chunks`'s inline supported-file filter and unmatched-pattern warning loop: deleted,
  replaced by calls to `_get_supported_files`/`_warn_unmatched_patterns`, shared with `_full_index`.
  Verified pure (no behaviour change): `is_supported(file_path)` only calls `extension_key`
  (suffix-based), confirmed by reading `chunking/multi_language_chunker.py:299` and
  `chunking/tree_sitter.py:618` — the switch from raw-path to project-joined-path calling
  convention makes no observable difference.
- Full unit suite: 4,636 passed, 2 skipped (zero regressions). Six directly-affected files
  (`test_index_write_stage.py`, `test_incremental_indexer.py`, `test_index_sync.py`,
  `test_index_sync_ownership.py`, `test_layering_ownership.py`, `test_indexer_clear_index.py`):
  164/164 passed. `tests/fast_integration/`: 102/102 passed. Lint (`check_lint.sh
  --modified-only`) and pyrefly both clean.
- Both index passes exercised end-to-end against this repo with `CLAUDE_AUTO_REINDEX=0`: a full
  force reindex (235 files / 2,966 chunks — the +10 over the 2026-09-06 canon's 2,956 is this
  change's own new code: the `IndexWriteTarget` protocol, two new properties, and
  `_warn_unmatched_patterns`) and a subsequent incremental pass (0 changes detected, correct no-op).
- No benchmark re-run, no canon re-pin. This is a behaviour-preserving refactor — no retrieval path,
  scoring, or ranking logic touched.

## Out of scope

- **Replace Conditional with Polymorphism unifying the full and incremental passes' call
  sequences into one shared sequence** — the original architecture-review candidate's fuller scope.
  Deferred because the two passes have pre-existing, intentional behavioural differences (call-edge
  injection full-only, no third snapshot save on the incremental path, a missing try/except on the
  incremental hand-roll) that a unification would have to resolve as its own reviewed, benchmarked
  change — not bundled into a pure seam-naming refactor. Two hats: this ADR adds no behaviour.
- **The missing try/except around the incremental path's embed→add-to-index sequence**, **the
  incremental path's third snapshot save bypassing `finalize`**, and **making call-edge injection
  available to the incremental pass unconditionally rather than via the `inject_on_incremental` opt-
  in** — all named as documented drift in the originating architecture review, all genuine
  behaviour changes, none touched here. Candidates for future ADRs, each needing its own gate.
- **`C2`'s result-row projection unification** (`mcp_server/tools/result_view.py`,
  `search/relationship_analyzer.py`) — the architecture review's natural follow-on candidate;
  landed as [ADR-0065](0065-relationship-analyzer-result-projection-unification.md).
