# Code Review & Ranked Improvement Plan

**Date:** 2026-06-11
**Scope:** Full-codebase correctness/performance review with emphasis on the
embedding path (`embeddings/`, `search/faiss_index.py`, `search/incremental_indexer.py`)
and the async MCP pipeline (`mcp_server/`), plus chunking/merkle/graph subsystems.
**Method:** Line-by-line review of the embedding and MCP layers; deep review of
chunking/merkle/graph; claims verified against official PyTorch, ONNX Runtime,
HuggingFace Optimum, FAISS, and Python asyncio documentation/sources (citations inline).
High-severity findings were independently re-verified against the source.

Severity legend: **P0** = data loss / wrong results · **P1** = high-impact bug, hang, or
event-loop stall · **P2** = meaningful performance or robustness win · **P3** = polish,
comment accuracy, low-risk hardening.

---

## P0 — Critical correctness

### 1. Silent, permanent index data loss when embedding fails mid-incremental-index
**Where:** `search/incremental_indexer.py:1181-1206` (`_add_new_chunks`) and
`incremental_index` (`:317`, `:322`, `:368`).

The incremental flow is *remove old chunks → embed new chunks → save snapshot*.
`_add_new_chunks` wraps `self.embedder.embed_chunks(...)` in
`except Exception: logger.warning(...)` and returns `0`. Execution then continues: the
old chunks for modified files were **already removed** (`_remove_old_chunks`, line 317),
and the Merkle snapshot is **saved anyway** (line 368), recording those files as up to
date. Any embedding failure (CUDA OOM that survives batch-halving, ORT failure, model
load error) permanently drops the modified files from the index with only a warning log;
they are not re-indexed until their content changes again.

**Fix:** Let the exception propagate (the caller's `except` already routes to
`_attempt_recovery`), or track per-file success and exclude failed files from the
snapshot DAG before `save_snapshot`. Add a regression test that fails embedding and
asserts the snapshot is not advanced. **Effort:** Small.

### 2. Stale searcher served for the wrong project/model after a failed switch
**Where:** `mcp_server/search_factory.py:134-181` (`get_searcher`).

The function mutates `state.current_project` and `state.current_model_key` *before*
constructing the new searcher. If construction raises (e.g. `DimensionMismatchError` at
line 164), `state.searcher` still holds the **previous project/model's searcher**, but
the cache keys now match the *new* values. The next call finds all keys equal and
`state.searcher is not None` → silently returns the old searcher for the wrong
project/model; searches run against the wrong index with no error.

**Fix:** Build into a local variable; commit keys + searcher together only on success;
on failure set `state.searcher = None`. **Effort:** Small.

### 3. Call-graph silently drops all but one relationship type per node pair
**Where:** `graph/graph_storage.py:149` (`nx.DiGraph`), `:242-250` (`add_call_edge`),
`:323-330` (`add_relationship_edge`). *(verified)*

`nx.DiGraph` permits one edge per `(u, v)`; `add_edge` on an existing pair **overwrites**
the attribute dict. A chunk that both `calls` and `instantiates` `Foo`
(`x = Foo(); x.bar()` — ubiquitous), or `imports` and `uses_type` the same symbol, keeps
only the last extractor's `type`. All downstream consumers (`get_relationships`,
`find_connections`, edge-weight profiles, subgraph extraction) operate on this lossy
graph. **Fix:** migrate to `nx.MultiDiGraph` keyed by relationship type (update
`node_link_data` round-trip and all `edges[...]`/`get_edge_data` accesses), or encode the
type into the edge key. **Effort:** Medium.

### 4. Parallel chunking shares non-thread-safe parser/extractor state
**Where:** `chunking/multi_language_chunker.py:693-698` (`_chunk_files_parallel`),
`chunking/languages/base.py:159` (one shared `Parser` per language),
`chunking/relationships/call_graph_extractor.py:160-200` (instance state
`self._imports`/`self._current_class`/...), `base_extractor.py:81-88` (shared
`self.edges`), `tree_sitter.py` `get_chunker` lazy check-then-set. *(verified)*

Worker threads share a single tree-sitter `Parser` per language — py-tree-sitter ≥0.25
releases the GIL during `parse`, so concurrent `parse()` on one `TSParser` is undefined
behavior (crashes/corrupt trees). The Python call-graph extractor and all relationship
extractors mutate per-call instance state, so concurrent files cross-contaminate: calls
attributed to the wrong class context, edges built from another file's imports.

**Fix:** per-thread (`threading.local`) or per-task chunker+extractor instances; or keep
parallel *parsing* but serialize relationship extraction. **Effort:** Medium.

---

## P1 — High impact

### 5. Async MCP pipeline: heavy synchronous work runs on the event loop
Per the [Python asyncio docs](https://docs.python.org/3/library/asyncio-dev.html#running-blocking-code),
blocking calls inside a coroutine stall the whole loop — MCP pings time out, cancellation
can't be processed, and in HTTP/stateless mode all concurrent requests freeze. The two
biggest cases are already offloaded (`handle_index_directory`, the orchestrator's final
`searcher.search`), but equally heavy paths still run inline:

| Call site | Blocking work |
|---|---|
| `mcp_server/tools/search_orchestrator.py:326` | `_check_auto_reindex` — can run a **full reindex including GPU embedding**, synchronously. Worst offender: a routine `search_code` on a stale index can block the loop for minutes. |
| `mcp_server/tools/search_handlers.py:765, 824, 931` | `find_similar_to_chunk`, `analyze_impact`, `find_path` — FAISS + multi-hop graph traversal inline (only Tier-3 of `_resolve_symbol_to_chunk_id` uses `to_thread`). |
| `mcp_server/tools/index_handlers.py:788, 934` | `_cleanup_previous_resources()` (gc + `torch.cuda.empty_cache()`) and `get_embedder()` (multi-second model load on first use) inline before the `to_thread` block. |
| `mcp_server/resource_manager.py:157` | `time.sleep(0.3)` in `close_project_resources`, reached from async `handle_delete_project`. |
| `mcp_server/tools/status_handlers.py:320`, `server.py:519` | `_cleanup_previous_resources()` inline in async handlers/endpoints. |
| `mcp_server/tools/index_handlers.py:534-609` | `handle_clear_index` does `shutil.rmtree`/`unlink` inline. |
| `mcp_server/tools/search_orchestrator.py:168, 667` | `IntentClassifier.classify` with `semantic_enabled` (model forward pass) and `_handle_chunk_id_lookup` inline. |

**Fix:** wrap each in `asyncio.to_thread(...)`; add a per-project `asyncio.Lock` around
auto-reindex so two concurrent searches can't start overlapping reindexes.
**Effort:** Medium (mechanical, but coordinate with item 7).

### 6. File-read "timeout" deadlocks instead of timing out
**Where:** `chunking/tree_sitter.py:159-166` (`_read_file_with_timeout`). *(verified)*

`with ThreadPoolExecutor(...)` + `future.result(timeout=...)`: when the timeout fires,
the `with` exit calls `shutdown(wait=True)`, which blocks until the hung `read_file()`
thread finishes — i.e. forever for a genuinely locked file. The timeout protection is
illusory; indexing hangs in exactly the case this code was written to survive. It also
spawns a fresh thread pool per file read.

**Fix:** create the executor without a context manager; on timeout call
`executor.shutdown(wait=False, cancel_futures=True)` (leaks one blocked thread, doesn't
hang); reuse a module-level executor. **Effort:** Small.

### 7. Shared mutable state has no synchronization (concurrent tool calls race)
**Where:** `mcp_server/state.py` (entire `ApplicationState`),
`mcp_server/model_pool_manager.py:211-234` (`_load_pool_embedder` check-then-act),
`search_factory.py` lazy init.

In HTTP mode the server is stateless and concurrent `call_tool` requests are expected;
handlers also hop between the loop and `to_thread` workers. No lock guards: (a) lazy
embedder load — two requests can construct the same `CodeEmbedder` concurrently, doubling
VRAM and leaking the loser (overwritten without `cleanup()`); (b) `get_searcher`
check-then-construct — duplicate FAISS/BM25 loads; (c) `clear_embedders()` /
`_cleanup_previous_resources()` tearing down a searcher under an in-flight request (the
embedder's own `_lifecycle_lock` prevents crashes mid-encode, but not searcher teardown).

**Fix:** a `threading.Lock` (usable from loop and worker threads) guarding embedder-pool
mutation and searcher construction/teardown, double-checked inside. Document that
`ApplicationState` writes require it. **Effort:** Medium (deadlock-care around the
embedder's RLock).

### 8. Import resolution silently broken when CWD ≠ project root
**Where:** `chunking/multi_language_chunker.py:398-400` (`file_path` set to
`chunk.relative_path`) → `chunking/relationships/resolvers/import_resolver.py:117`
(`open(file_path)` against process CWD). *(verified)*

For an MCP server started anywhere other than the project root (the normal case), every
full-file import read fails with `OSError`, is logged only at DEBUG, and an **empty
import map is cached per file**. Aliased-import and class-method call resolution silently
degrade to bare names — quietly weakening the entire call graph.

**Fix:** pass `chunk.file_path` (absolute) in the metadata, or join with the project root
inside `read_file_imports`. **Effort:** Small.

### 9. ONNX `provider_options` passed as a *list* breaks on the minimum-pinned Optimum
**Where:** `embeddings/onnx_loader.py:340-345`. *(doc-verified)*

In optimum **1.25.0** (`pyproject.toml` allows `optimum>=1.25.0`),
`ORTModel.from_pretrained` declares `provider_options: Optional[Dict[str, Any]]` and
wraps it itself (`providers_options = [provider_options] + [{}...]`,
[optimum v1.25.0 `modeling_ort.py:390-400`](https://github.com/huggingface/optimum/blob/v1.25.0/optimum/onnxruntime/modeling_ort.py)).
Passing the current `[{...}]` yields a nested `[[{...}]]` → session creation fails →
`load()` catches `RuntimeError` and **silently falls back to PyTorch**, losing both the
ONNX speedup and the ORT VRAM cap. Newer `optimum-onnx` accepts `Sequence[dict] | dict`
([source](https://github.com/huggingface/optimum-onnx/blob/main/optimum/onnxruntime/modeling.py)),
so a plain **dict works on both**.

**Fix:** pass a dict. **Effort:** Trivial.

### 10. `handle_clear_index` deletes index/DB files while handles are still open
**Where:** `mcp_server/tools/index_handlers.py:534-597`.

It deletes `chunks_metadata.db`, `code.index`, and the BM25 dir **before** resetting
search components — and never closes the metadata SQLite connections.
`handle_delete_project` does the correct order (`close_project_resources` → delete). On
Windows the open handles make `unlink()` raise `PermissionError`, leaving a partially
deleted index. **Fix:** close/cleanup first, mirroring `handle_delete_project`; run
deletion in `to_thread`. **Effort:** Small.

### 11. `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` leak across model loads
**Where:** `embeddings/model_loader.py:598-599`, cleared only in the failure fallback
(`:689-690`).

Process-wide env vars set after any successful cached load put the whole process in
offline mode. Later loading a *different, uncached* model (model switch, cross-pool,
routing) fails Step 2's `model_info()`/download with a misleading "Model not found on
HuggingFace Hub". The constructor already passes `local_files_only=True` for the
validated-cache case, which scopes offline behavior correctly — the env mutation is
redundant *and* harmful. **Fix:** drop it (or save/restore around the single load call).
**Effort:** Small.

### 12. Ancestor-directory names can disable indexing entirely
**Where:** `chunking/multi_language_chunker.py:626`, same pattern in
`merkle/merkle_dag.py` `build_node`/`should_ignore`. *(verified)*

`any(part in DEFAULT_IGNORED_DIRS for part in file_path.parts)` inspects **absolute**
path components, including those above the project root. A repo under any ancestor
directory named `build`, `dist`, `env`, `bin`, `out`, `target`, `logs`, `public`,
`coverage`, … indexes **zero files**; a project folder itself named e.g. `build`
produces an empty Merkle DAG (root ignored). **Fix:** test only components of
`path.relative_to(project_root)`, and never ignore the root node. **Effort:** Small.

### 13. JS/TS/Go methods are chunked with `name=None`
**Where:** `chunking/languages/javascript.py:44-48`, `typescript.py:52-56`,
`go.py:42-46`.

JS/TS `method_definition` names are `property_identifier` nodes; Go `method_declaration`
names are `field_identifier` nodes; the extraction loops only match
`identifier`/`type_identifier`. Every class method in JS/TS and every Go method loses its
name — breaking qualified names, chunk-ids, and symbol search for those languages. Also
`go.py` lists `struct_declaration`/`interface_declaration`, which don't exist in the Go
grammar (they live under `type_declaration → type_spec`), and `type_declaration` names
are never extracted. **Fix:** add the missing node types to the name-extraction loops;
correct the Go splittable-node list. **Effort:** Small.

---

## P2 — Performance & robustness (embedding/indexing path first)

### 14. Per-chunk file re-reads inside the embedding loop
**Where:** `embeddings/embedder.py:786-822` (`_extract_import_context`),
`:824-880` (`_get_class_signature`), called from `create_embedding_content` for **every
chunk** (`embed_chunks` → `:1299-1306`).

For each chunk the source file is re-opened and re-scanned for imports; for each *method*
chunk the **entire file** is read again and regex-searched for the parent-class header. A
file with 40 chunks ⇒ ~40 redundant opens+reads, serialized on the thread feeding the
GPU (and each open can trigger a Defender scan on Windows). Also a config
`ServiceLocator` lookup per chunk (`:899-906`) that should be hoisted.

**Fix:** cache per `(file_path, mtime)` — one pass computing the import header and a
`{class_name: signature}` map per file — or compute both at chunking time where the
content is already in memory and store them on `CodeChunk`.
**Expected win:** large on full indexes; the I/O-bound share of the embed loop ≈ vanishes.

### 15. Re-parse of chunk content ~13–16× per Python chunk
**Where:** `chunking/multi_language_chunker.py:379-479` + `relationship_extractors/*`.

Per chunk: `smart_dedent` twice (each with 1–2 validation `ast.parse` calls), one
`ast.parse` in the call extractor, and one **per relationship extractor** (11–14
extractors). **Fix:** parse the dedented content once; pass the tree to all extractors.
This is the single biggest CPU win in the chunking stage.

### 16. O(M×N) community remerge over the entire index
**Where:** `chunking/languages/base.py:507-556` + `search/community_stage.py:104`.

`_from_treesitter_chunks` linearly scans the full `original_chunks` list (twice) for each
merged chunk — quadratic in repo size; billions of comparisons at ~50k chunks on every
full index. **Fix:** pre-bucket `original_chunks` by `file_path` once.

### 17. O(files × chunks) verification scan + per-file INFO logging in full index
**Where:** `search/incremental_indexer.py:822-826` and `:778-779`.

`any(c.file_path == str(Path(project_path) / f) for c in all_chunks)` per file is
quadratic with a `Path` construction per comparison; just above it every supported file
is logged at INFO through the rich console. **Fix:** one `{c.file_path for c in
all_chunks}` set + membership; demote logs to DEBUG.

### 18. One full recursive tree walk per extension (twice over)
**Where:** `chunking/multi_language_chunker.py:622-628` (19 walks; `rglob` still
descends into `node_modules`/`.git` before per-file filtering) and
`mcp_server/tools/index_handlers.py:803-806`
(`list(rglob(f"*{ext}"))[:10]` materializes the full walk ~30× just to sample ≤50 files).

**Fix:** single `os.walk` with directory pruning + suffix dispatch; `itertools.islice`
for the sampling.

### 19. mmap export reconstructs vectors one-by-one in Python
**Where:** `search/faiss_index.py:345-347` (`save()`). *(doc-verified)*

`np.array([self._index.reconstruct(i) for i in range(ntotal)])` crosses Python↔C++ per
vector; FAISS provides `reconstruct_n(0, ntotal)` exactly for this
([FAISS wiki](https://github.com/facebookresearch/faiss/wiki/Special-operations-on-indexes)) —
for `IndexFlatIP` it is essentially one memcpy. Runs on every `save()` above 10k vectors,
i.e. on every incremental index of a large project. **Fix:** one-line change.

### 20. Embedding-batch logger level leaked on exception
**Where:** `embeddings/embedder.py:1260-1261` and `:1403`.

`embed_chunks` sets the module logger to WARNING for the progress bar and restores after
the loop — not in a `finally`. `VRAMExhaustedError` (`:1289`) or an OOM re-raise
(`:1371`) leaves `embeddings.embedder` at WARNING for the rest of the process, hiding all
subsequent VRAM/diagnostic INFO logs. The level also lives on a module logger shared by
all instances (concurrent calls race the save/restore). **Fix:** `try/finally`; prefer a
scoped `logging.Filter` over mutating shared state.

### 21. Merkle traversal robustness (symlinks, swallowed subtree errors, reindex loop)
**Where:** `merkle/merkle_dag.py:196-230`, `merkle/change_detector.py:160-166`.

(a) Symlinked directories are followed with no cycle/escape protection — a symlink loop
recurses to `OSError` (silently swallowed), a symlink to a large external tree gets
indexed. (b) A *transient* `PermissionError/OSError` in `iterdir()` silently drops the
whole subtree from the new DAG → the change detector reports every file in it as
`removed` → their chunks are **deleted from the index**, unlogged. (c) The snapshot-dir
ignore pattern is added as a multi-segment relative path
(`.claude_code_search/merkle`) which `should_ignore` can never match (it compares
`path.name` only) — if the snapshot dir is inside the project this causes a perpetual
self-triggering reindex loop.

**Fix:** `is_dir(follow_symlinks=False)` semantics; log + reuse the prior snapshot's
subtree on traversal error instead of treating files as deleted; match ignore patterns
against relative-path prefixes.

### 22. `edge_weights` / intent edge-weight profiles have zero effect on results
**Where:** `graph/graph_storage.py:385-465` (weighted BFS), `:62-105`
(`INTENT_EDGE_WEIGHT_PROFILES`), wired up in `search_orchestrator.py:481-494`.

The "weighted BFS" changes only *expansion order*; with no node/visit budget the returned
neighbor set is provably identical to the unweighted branch. The whole intent
edge-profile machinery is dead weight plus heap overhead, and the docstring is
misleading. **Fix:** add a budget (top-k by accumulated priority) so weights actually
shape results, or delete the parameter and profiles.

### 23. Graph traversal `visited`-before-filter drops legitimate results
**Where:** `graph/graph_queries.py:574-606, 623-653`.

Neighbors are marked visited *before* the `relation_types` filter applies; first
encounter via a non-matching edge permanently suppresses a later matching edge, making
`find_connections` results dependent on iteration order. **Fix:** mark visited only on
report (or evaluate all edges before marking).

### 24. ONNX `encode()` batching/padding improvements
**Where:** `embeddings/onnx_wrapper.py:98-121`.

`batch_size` is intentionally ignored (CodeEmbedder pre-batches — safe today). Cheap
wins: sort-by-token-length within an indexing run (uniform batches cut padded FLOPs —
ORT has no FlashAttention and materializes T×T attention); pass `pad_to_multiple_of=8`
for tensor cores; pass an explicit `max_length` so the bound doesn't silently depend on
`create_embedding_content`'s 6000-char cap (BGE-M3's tokenizer otherwise allows 8192
tokens).

### 25. Hot-path config access stats the config file on every call
**Where:** `search/config.py:1128-1130` (`get_search_config` → mtime check).

A single `search_code` request triggers a dozen-plus `stat()` calls (planner,
orchestrator, embedder, hybrid searcher, formatters), more inside indexing loops.
**Fix:** TTL-cache the mtime check (1–2 s) — preserves hot reload, removes per-call
syscalls. (This also makes the `/reload_config` HTTP endpoint effectively redundant —
today it builds a *new* `SearchConfigManager` whose only real effect is the same
mtime-triggered reload the singleton performs anyway; worth a clarifying comment.)

### 26. Memory: `EmbeddingResult.metadata` duplicates full chunk content
**Where:** `embeddings/embedder.py:1053-1058` (`content` **and** `content_preview`).

During a full index every chunk's complete text is held twice in the results list until
the write stage drains it (plus once on the `CodeChunk`) — hundreds of MB transient RSS
at 50k chunks. **Fix:** store `content` only; derive the preview at write/format time
(audit `content_preview` consumers first).

### 27. Non-atomic JSON persistence (snapshots, graph)
**Where:** `merkle/snapshot_manager.py:179-196`, `graph/graph_storage.py:722, 771-776`.

No tmp-file + `os.replace`; a crash mid-write corrupts the snapshot (silent full reindex)
or the graph (silently reset to empty — all edges gone until the next full index).
`save_snapshot` also mutates the caller's `metadata` dict. **Fix:** atomic write helper
used by both.

### 28. Community-merged chunks lose their call-graph contribution
**Where:** `chunking/languages/base.py:471-505, 250-296, 576-579`.

The `_to_treesitter_chunks` docstring claims calls/relationships are preserved through
the merge pass, but `_create_merged_chunk` copies only a few metadata fields and
`_from_treesitter_chunks` hard-sets `calls=[]`, `relationships=[]` for merged chunks.
Either union member edges into the merged chunk or fix the comment and accept the loss
explicitly.

### 29. `FaissVectorIndex.add()` mutates the caller's embedding array in place
**Where:** `search/faiss_index.py:394` vs `:441` (search copies, add doesn't).

`faiss.normalize_L2` is in-place; callers reusing the array afterwards silently see
normalized data. Latent (embeddings are already unit-norm today) but a classic aliasing
trap — copy like `search()` does, or document the contract loudly.

---

## P3 — Hardening, comments, docs

30. **CUDA allocator config comment overstates the constraint** — `embeddings/embedder.py:188-217`:
    `PYTORCH_CUDA_ALLOC_CONF` is read when the caching allocator initializes (first CUDA
    allocation), not at `import torch`
    ([PyTorch CUDA semantics](https://docs.pytorch.org/docs/2.11/notes/cuda.html)). Current
    placement works but silently becomes a no-op if anything allocates on CUDA before
    `embeddings.embedder` is imported. Set it in the server entrypoint and fix the comment.
31. **`gpu_mem_limit` is not a total-VRAM cap** — `embeddings/onnx_loader.py:304-309`: per
    [ORT CUDA EP docs](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)
    it limits only the EP's BFC arena; cuDNN workspaces and the CUDA context live outside.
    The conservative batch-size use is fine — adjust comments so readers don't rely on it
    as a hard ceiling.
32. **`print()` on stdout in an MCP stdio server** — `merkle/snapshot_manager.py:217-221`:
    stdout is the JSON-RPC channel; a version-mismatch warning can corrupt the protocol
    stream. Use `logger.warning`. (Likewise audit any other `print()` in server-reachable
    paths.)
33. **Normalization invariant split across layers** — ONNX wrapper always L2-normalizes
    (`onnx_wrapper.py:156`); the PyTorch path depends on the model's `Normalize` module;
    `FaissVectorIndex` re-normalizes on add and query (`faiss_index.py:394,443`), which makes
    FAISS scores correct on both backends. Document the invariant in one place; consumers of
    raw `embed_query()` output must not assume unit norm on the PyTorch path.
34. **Merkle hash details** — `merkle/merkle_dag.py:140-149`: unreadable file hashes to a
    constant of its *path* (content changes while locked are never detected; a mid-read error
    silently yields a partial-content hash, no log). The `:201-203` comment "detects
    renames/moves via mtime+size" is wrong — renames are detected by path-set diff.
    `from_dict` (`:286-313`) doesn't restore `supported_extensions`, so a hashing-scheme
    change flags every non-code file "modified" once; serialize the scheme in the snapshot.
35. **`embed_chunk` (singular) skips the lifecycle lock** — `embeddings/embedder.py:1068-1099`
    encodes without `_lifecycle_lock` while `embed_chunks`/`embed_query` take it; a cleanup
    racing a lone `embed_chunk` can null the model mid-call.
36. **`handle_call_tool` pops `output_format` after dispatch** — `mcp_server/server.py:267-271`:
    handlers receive the key (all currently ignore it); pop before dispatch.
37. **`logging.basicConfig(level=INFO)` inside `CodeEmbedder.__init__`** —
    `embeddings/embedder.py:624`: library code mutating root logging fights the server's
    dual-handler setup; delete.
38. **`zip(..., strict=False)` in embedding result assembly** — `embedder.py:1383-1385`,
    `incremental_indexer.py:1186-1188`: counts are equal by contract; `strict=True` turns a
    silent truncation into a loud failure.
39. **`cleanup_old_snapshots` is a guaranteed no-op** — `merkle/snapshot_manager.py:391-418`:
    snapshot stems are unique per project/model/dim, so every "group" has one file; remove or
    redesign.
40. **`find_call_chain` doesn't normalize paths; `compute_centrality("degree")` returns raw
    ints** — `graph/graph_queries.py:56-96, 479-480`: Windows-separator chunk_ids fail only
    in this query; degree centrality contradicts its docstring.
41. **`utils/version_check.py:33-45`** — `parse_version_tuple("2.8")` → `(2, 8)` compares
    `< (2, 8, 0)` → false "too old"; splitting on `"a"`/`"b"` mangles versions containing
    those letters outside pre-release context.
42. **Stale comments** — references to the removed AST chunker
    (`multi_language_chunker.py:106-107`, `languages/python.py:3-5`,
    `languages/__init__.py:7,16`); `repo_profiler.py:148` says `statistics.quantiles` is
    "inclusive" (default is `method='exclusive'`); `resource_manager.py` docstrings still say
    "SSE modes" (transport is StreamableHTTP); `QueryEmbeddingCache.get` disabled-path
    increments `_misses` outside the lock (`query_cache.py:113-115`); Python docstring
    extraction misses prefix-quoted (`r"""`) docstrings (`languages/python.py:182-201`).

---

## Checked and found sound (no action)

- **Tree-sitter offsets:** all chunkers slice `bytes` with `start_byte`/`end_byte` and
  decode afterwards (`chunking/languages/base.py:236, 735-737, 885-887`) — non-ASCII safe.
- **FAISS metric:** `IndexFlatIP` + L2-normalize on add and query = cosine similarity,
  correct on both backends.
- **OOM recovery loop** (`embedder.py:1322-1371`): batch-halving with progress-total
  recalculation and non-advancing retry index is correct; covers torch
  (`OutOfMemoryError` subclasses `RuntimeError`), legacy string-match, and ORT BFCArena
  messages.
- **`compute_effective_vram_cap`** math and its shared use by the PyTorch cap and ORT
  `gpu_mem_limit` is coherent; `set_per_process_memory_fraction` governs only the PyTorch
  allocator as documented.
- **`handle_index_directory`** correctly offloads indexing via `asyncio.to_thread`;
  the `error_handler` decorator correctly re-raises `CancelledError` and isolates
  context-enrichment failures.
- **Optimum 2.x `token_type_ids`/`position_ids` synthesis note** in
  `onnx_wrapper.py:123-133` matches optimum-onnx behavior.
- **Louvain phantom-collapse** (`community_detector.py`) correctly excludes self-loops
  and caps clique creation; `evaluation/` interval merge/intersection logic verified
  correct.

---

## Suggested execution order

| Phase | Items | Theme | Est. effort |
|---|---|---|---|
| 1 | 1, 2, 9, 10, 11 | Stop silent data loss, wrong-index serving, silent ONNX fallback, env leak | ~1–2 days |
| 2 | 5, 6, 7 | Async pipeline: `to_thread` everywhere heavy, reindex lock, state locking, read-timeout fix | ~2–3 days |
| 3 | 3, 4, 8, 12, 13 | Graph/chunking correctness: MultiDiGraph, thread-safe parallel chunking, import paths, ignore-dir scoping, JS/TS/Go names | ~3–4 days |
| 4 | 14–19 | Embedding/indexing hot-path perf (file-read caching + single-parse are the headline wins) | ~2 days |
| 5 | 20–29 | Robustness + second-order perf (merkle traversal, atomic writes, edge-weight budget, memory) | ~2–3 days |
| 6 | 30–42 | Comments, invariants, hardening | ~1 day |

Phases are independently shippable. Phases 1–2 should land first: they change the same
files the later perf items touch, and they eliminate the failure modes (silent data loss,
stale searcher) that would otherwise mask regressions while benchmarking the perf work.

---

## Documentation verified against

- Python asyncio — [Running blocking code](https://docs.python.org/3/library/asyncio-dev.html#running-blocking-code)
- PyTorch — [CUDA semantics / caching allocator env config](https://docs.pytorch.org/docs/2.11/notes/cuda.html)
- ONNX Runtime — [CUDA Execution Provider options (`gpu_mem_limit`, `arena_extend_strategy`)](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)
- HuggingFace Optimum — [`ORTModel` reference](https://huggingface.co/docs/optimum-onnx/en/onnxruntime/package_reference/modeling_ort),
  [optimum v1.25.0 `modeling_ort.py`](https://github.com/huggingface/optimum/blob/v1.25.0/optimum/onnxruntime/modeling_ort.py),
  [optimum-onnx `modeling.py` (provider_options: `Sequence[dict] | dict`)](https://github.com/huggingface/optimum-onnx/blob/main/optimum/onnxruntime/modeling.py)
- FAISS — [Special operations on indexes (`reconstruct_n`)](https://github.com/facebookresearch/faiss/wiki/Special-operations-on-indexes)
- tree-sitter — byte-offset API semantics confirmed against `chunking/languages/base.py` usage (slices `bytes`, decodes after)
