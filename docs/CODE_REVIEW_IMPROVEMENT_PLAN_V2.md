# Code Review & Ranked Improvement Plan — v2

**Date:** 2026-06-12
**Scope:** Follow-up full-codebase review building on `CODE_REVIEW_IMPROVEMENT_PLAN.md`
(2026-06-11, findings #1–#42). Two goals: (A) trace the implementation of the v1 plan
through the commit history and verify the fixes actually landed; (B) a fresh
correctness/performance review with emphasis on the embedding path (`embeddings/`)
and the async MCP pipeline (`mcp_server/`), with every load-bearing claim re-verified
against official PyTorch 2.8 / ONNX Runtime / Optimum / transformers / asyncio / NVML /
FAISS documentation or version-pinned sources (citations inline and at the end).

Numbering continues from the v1 plan: new findings are **#43–#62** so cross-references
stay unambiguous.

Severity legend (unchanged): **P0** = data loss / wrong results · **P1** = high-impact
bug, hang, or event-loop stall · **P2** = meaningful performance or robustness win ·
**P3** = polish, comment accuracy, low-risk hardening.

---

## Part A — Implementation trace of the v1 plan (2026-06-11 → v0.16.0)

Commit-level map of every v1 finding, verified against the working tree on this branch:

| v1 item | Commit(s) | Verified in tree |
|---|---|---|
| #1 embed-failure data loss, #2 atomic searcher swap | `0b7b94c` | ✅ (`search_factory.py:157-222` commits keys only on success) |
| #6 timeout deadlock, #8 import CWD, #12 ancestor-dir ignore, #32 print→log, #42 comments | `f4c3891` | ✅ |
| #9 provider_options dict, #11 offline-env leak, #20 logger try/finally, #33 norm invariant, #35 lifecycle lock, #37 basicConfig, #38 zip strict | `fb8372c` (+ `6780a94` test fixes) | ✅ (`onnx_loader.py:349`, `embedder.py:1271-1418`, etc.) |
| #10 clear_index handle order, #36 output_format pop, #42 SSE comment | `535f5cd` | ✅ (`index_handlers.py:550`, `server.py:259-271`) |
| #19 reconstruct_n, #29 add() copy, #41 version tuples | `e356095` | ✅ (`faiss_index.py:347`) |
| #23 visited-before-filter, #40 path normalize + float cast | `07965a0` | ✅ |
| #3 MultiDiGraph migration | `ae13947` + `d1b98da` | ✅ (with #3-follow-up keying call edges on `"calls"`) |
| #21 merkle symlink cycles, #27 atomic JSON writes | `6b2aa45`, `4a0981e` | ✅ |
| #7 singleton/state locking | `7067978` | ✅ (`_pool_lock` + documented lock ordering, `model_pool_manager.py:23-29`; double-checked locking in `search_factory.py`) |
| #5 async offload + reindex lock | `4ffa9cc` | ⚠️ **PARTIAL — see #43** |
| #4 per-thread parser/extractor isolation | `7d8efc5` | ✅ |
| Deferred: #13–#18, #22, #24–#26, #28 | — | still open; re-ranked in Part C |

**Net assessment:** Batch 1, 2A and 2B landed faithfully — every spot-check matched the
plan's described fix. The one materially incomplete item is **#5** (event-loop offload):
the headline sites were fixed (the three search handlers, `_handle_chunk_id_lookup`,
auto-reindex offload + per-project `asyncio.Lock`), but six blocking sites listed in the
v1 #5 table were *not* offloaded and one new blocking path has since become live by
default. These are rolled up into **#43** below as the top-priority item of this plan.

---

## Part B — New findings (this review)

### P1 — Event-loop and correctness

#### 43. Residual #5: six call sites still block the asyncio event loop

The MCP Python SDK dispatches **every incoming request as its own task on one event
loop** (`Server.run()` → `tg.start_soon(self._handle_message, …)`, verified at tag
v1.27.0), so a single synchronous handler stalls pings, cancellation, and all
concurrent tool calls ([asyncio docs: running blocking code][asyncio-dev],
[python-sdk v1.27.0 `server.py`][mcp-sdk]). The remaining sites:

| # | Call site | Blocking work |
|---|---|---|
| a | `search_orchestrator.py:682` — `SearchPlanner().plan(arguments)` runs inline in `run()` | `IntentClassifier.classify()` with `semantic_enabled` calls `embedder.embed_query(query)` — a **GPU forward pass per search request** (`intent_classifier.py:477`). This is **live by default**: `search_config.json:65` ships `"semantic_enabled": true`. The first request additionally embeds every anchor query sequentially (`intent_classifier.py:424-435`). `plan()` also does `_route_query_to_model` filesystem `.exists()` probes. |
| b | `search_orchestrator.py:700` — `get_searcher(model_key=…)` in the SIMILARITY redirect | Can construct a full `HybridSearcher` (model load + FAISS/BM25 load) inline. The *same call* 35 lines earlier in `_execute` (line 364) is wrapped in `asyncio.to_thread` with a comment explaining exactly why — this site was simply missed. |
| c | `index_handlers.py:946-948` — `get_embedder()` and `get_searcher(...)` inline in `handle_index_directory` | Multi-second model load / index load on first use, *before* the `to_thread` block that runs the indexing itself. |
| d | `index_handlers.py:534-609` — `handle_clear_index` | `close_project_resources()` (which includes `time.sleep(0.3)` at `resource_manager.py:157`) plus `shutil.rmtree`/`unlink` inline. |
| e | `status_handlers.py:330` — `handle_cleanup_resources` | `_cleanup_previous_resources()` inline: `gc.collect()` + `torch.cuda.synchronize()` + `empty_cache()` can take hundreds of ms. |
| f | `server.py:519` — HTTP `/cleanup` endpoint | Same `_cleanup_previous_resources()` inline on the uvicorn loop. |

**Fix:** mechanical `asyncio.to_thread` wraps for (b)–(f). For (a), either offload the
whole `plan()` call, or (cleaner) keep `plan()` synchronous but make the semantic-scoring
branch fetch its `embed_query` via `to_thread` — note `plan()` is documented as
"synchronous and side-effect-free", so offloading the single classify call preserves that
design. Combine with **#59** (batch the anchor embeds). **Effort:** Small. **P1.**

#### 44. Stale `_metadata_cache` (including negative entries) survives `clear_index` / re-index

`BaseSearcher._metadata_cache` (`base_searcher.py:36`) caches `SearchResult` objects *and
negative lookups* (`hybrid_searcher.py:531` stores `None` for missing chunk_ids).
`HybridSearcher.clear_index()` (`hybrid_searcher.py:1297-1335`) meticulously rebuilds
every component reference (BM25, dense, reranker metadata store, multi-hop, graph) but
never clears this cache; `remove_file_chunks()` doesn't either. After clear → re-index,
`get_by_chunk_id()` can return chunks that no longer exist, or a cached `None` for a
chunk_id that now exists (e.g. a re-added file with identical line ranges — common after
`force_reindex`). Eviction is FIFO on overflow only, so entries persist indefinitely on
small/medium indexes.

**Fix:** `self._metadata_cache.clear()` in `clear_index()` and on `remove_file_chunks()`
for affected chunk_ids (or simply clear wholesale — it's a warm cache, not a source of
truth). **Effort:** Trivial. **P1** (wrong results), found by sub-agent review and
verified line-by-line.

#### 45. `_count_chunks_in_file` returns the project-wide file count

`searcher.py:204-210`: returns `stats.get("files_indexed", 0)` — the number of *files in
the index* — as "total chunks in this file". Every `IntelligentSearcher` result's
`context_info["file_context"]["total_chunks_in_file"]` carries the same wrong number, and
each result pays a `get_stats()` call for it. The comment even admits the shortcut
("simplified implementation"). **Fix:** count via the metadata store
(`relative_path` equality) once per distinct file in the result set, or drop the field.
**Effort:** Small. **P1-correctness / P2-perf** (semantic-only mode; hybrid default path
unaffected).

#### 46. ONNX tokenization is unbounded — batch sizing assumes ≤1024 tokens, tokenizer allows 8192

`onnx_wrapper.py:116-121` tokenizes with `truncation=True` and **no `max_length`**.
Per the transformers padding/truncation docs, that truncates at "the maximum length
accepted by the model" — `tokenizer.model_max_length`, which for BGE-M3 is **8192**
([transformers pad/truncation][hf-trunc], [BAAI/bge-m3 tokenizer config][bge-m3]).
Meanwhile the entire VRAM model in `embedder.py` is calibrated to
`t_eff = 1024` (`embedder.py:175`) and `create_embedding_content` caps content at 6000
*chars* — which for code regularly tokenizes to 1500–3000 tokens. `padding=True` then
pads the **whole batch** to the longest member. One long chunk therefore inflates every
item's activation cost ~2–8× past what `calculate_optimal_batch_size` budgeted — and
without Flash-Attention the ORT path materializes T×T attention, so cost grows
quadratically. This is very likely the root mechanism behind the empirical
`MODEL_ACTIVATION_COST_OVERRIDES_ONNX` floors (`embedder.py:56-65`).

**Fix:** pass an explicit `max_length` aligned with the memory model (e.g.
`min(model_max, 2048)` — configurable per model in the registry), and feed the *actual*
tokenized max length of each batch into the safety logging. **Effort:** Small.
**P1** (latent OOM despite all the careful batch-size machinery).

#### 47. Graph storage path-normalization gaps (Windows)

`graph_storage.py:273` `upgrade_call_edge()` indexes `self.graph.edges[caller_id,
callee_id, "calls"]` with **raw** ids while every read API normalizes
(`normalize_path`) — a backslash chunk_id raises `KeyError` during resolver upgrades.
`__contains__` (`graph_storage.py:936`) has the same inconsistency. **Fix:** normalize in
both; longer-term, normalize in *all* write methods (`add_node`, `add_call_edge`) so
reads don't have to compensate. **Effort:** Trivial. **P1 on Windows, P3 elsewhere.**
(Found by sub-agent review; verified by reading the quoted code.)

#### 48. Evaluation: line-0 truthiness filtering + off-by-one span

`evaluation/chunk_mapping.py:56-59` and `evaluation/metrics.py:454-455` use
`if path and start and end` after `or 0` defaults — any chunk whose metadata lacks line
numbers is *silently* dropped from eval mappings. `chunk_mapping.py:92` computes
`size = end - start` for documented *inclusive* ranges (off by one; consistent within the
file today, so innermost-chunk selection still works, but it's a trap). **Fix:** explicit
`is not None` checks + `size = end - start + 1`. **Effort:** Trivial. **P2** (eval-only).

#### 49. Merkle: unreadable files are hashed by *path*

`merkle/merkle_dag.py:163-165`: on `OSError` the node hash becomes a digest of the path
string. The hash no longer represents content; when the file becomes readable its hash
flips → spurious "modified" events; two snapshots can also agree the file is "unchanged"
while its content changed during the unreadable window. **Fix:** mark the node with an
explicit `unreadable` sentinel that always compares unequal (forcing a re-hash attempt
next run), and log at WARNING. **Effort:** Trivial. **P2.**

---

### P2 — Embedding-path performance

#### 50. (v1 #14, promoted) Per-chunk file re-reads inside the embedding loop — biggest indexing CPU win

`create_embedding_content` is called once per chunk (`embedder.py:1309-1317`, `:1074`),
and each call re-opens the source file in `_extract_import_context`
(`embedder.py:790-826`) and re-reads the **entire file** in `_get_class_signature`
(`embedder.py:828-884`, plus an `re.search` over full content). A 50-chunk file is read
~100 times; total work is O(chunks × file-size) of redundant I/O + regex *interleaved
with GPU batches*, so the GPU sits idle while Python re-reads files. **Fix:** an
LRU/`dict` cache keyed by `(file_path, mtime)` holding `(import_context,
{class_name: signature})` — computed once per file; or precompute in the chunker where
the parsed tree is already available. Also a natural place to fix the latent quirk where
import scanning can pick up `import`-looking lines inside module docstrings.
**Effort:** Small-Medium. **P2 (large).**

#### 51. (v1 #24, expanded) ONNX `encode()` — no length bucketing, `batch_size` ignored

`onnx_wrapper.py:98-105` admits `batch_size` is "ignored — all processed at once".
Two consequences: (a) any caller that passes a large list directly (e.g.
`embed_queries_batch`, or future callers trusting the SentenceTransformer-compatible
signature) bypasses *all* of the OOM-protection machinery; (b) every batch pays
worst-case padding. SentenceTransformer itself sorts by length before batching and
restores order after — verified in v5.2.2 source (`length_sorted_idx = np.argsort(...)`)
([sentence-transformers v5.2.2][st-encode]) — so the PyTorch backend already gets this
for free and the ONNX backend silently lost it. **Fix:** tokenize once, sort indices by
token length, loop in `batch_size` sub-batches, concatenate, restore order. Combines
with the `max_length` cap from #46. **Effort:** Small-Medium. **P2.**

#### 52. Ego-graph scoring: O(neighbors × N) list copy + linear scan + per-vector reconstruct

`hybrid_searcher.py:862-871`, *inside the per-neighbor loop*:
`chunk_ids_list = list(self.dense_index.chunk_ids)` (full copy of all N ids), then
`.index(chunk_id)` (O(N) scan), then `_faiss_index.reconstruct(idx)` (one C++ crossing
per neighbor). For a 100k-chunk index with 50 ego neighbors that's 50 full list copies +
50 linear scans per search. **Fix:** build `{chunk_id: idx}` once per call (or reuse the
position already stored in the metadata DB by `CodeIndexManager.add_embeddings`), and
batch with `reconstruct_batch` — the API FAISS provides precisely "to avoid the loop"
([FAISS wiki: special operations][faiss-wiki]). **Effort:** Small. **P2.**

#### 53. NVML handle churn — init/shutdown per measurement

`model_loader.py:45-75` runs `nvmlInit()` → query → `nvmlShutdown()` on every call (≥3×
per ONNX model load, plus any VRAM probes). NVML init/shutdown is reference-counted and
thread-safe, but init "loads/initializes the library" and NVIDIA's guidance is to
initialize once per process ([NVML init/cleanup docs][nvml]). Also note the `pynvml`
PyPI package is deprecated in favor of `nvidia-ml-py` (same import name) — worth
aligning the dependency. **Fix:** module-level lazy init with `atexit` shutdown; keep
the device handle cached. **Effort:** Trivial. **P2 (small) + dependency hygiene.**

#### 54. ONNX activation measurement runs *after* the arena has already grown — floors are compensating

Order in `_load_onnx` (`model_loader.py:404-428`): (1) warmup `encode(["warmup"],
batch_size=1)` grows the ORT BFC arena; (2) pynvml before/after delta for *model* VRAM;
(3) `_measure_activation_per_item` with batch=4 measures another pynvml delta — but with
`arena_extend_strategy=kSameAsRequested` much of the batch-4 activation fits in arena
space the warmup already reserved, so the measured delta systematically **underestimates**
per-item cost (the plan's own comments record warmup reporting 0.053 GB/item vs 0.28
real for BGE-M3). That underestimate is exactly what `MODEL_ACTIVATION_COST_OVERRIDES_ONNX`
hard-codes around. **Fix:** measure the *first* inference (batch=4, representative
512-token texts) as the activation probe instead of warming up at batch=1 first — i.e.
swap the order so warmup *is* the measurement; long-term, prefer deriving cost from the
tokenized-length-aware formula (#46) over device-delta probing. Keep the floors until
the new measurement is validated on an 8 GB GPU. **Effort:** Small (order swap) /
Medium (validation). **P2.**

#### 55. (v1 #26, promoted) `EmbeddingResult.metadata` duplicates full chunk content

`embedder.py:1057-1062` stores both `content` (full text) and `content_preview` for every
chunk — doubling peak RAM during indexing and bloating the SQLite metadata store; the
preview is derivable. **Fix:** store full content only (preview computed at read time),
or store preview only if full content is never read downstream (verify `bm25`/reranker
readers first). **Effort:** Small. **P2.**

#### 56. `_check_vram_status` is a no-op on the ONNX backend

`embedder.py:750-757` reads `torch.cuda.memory_allocated()`, which stays ≈0 when ORT owns
the allocations (the code itself documents this elsewhere: `_get_model_vram_gb`,
`onnx_wrapper.cleanup`). So the 85 %/95 % warn/abort thresholds in the `embed_chunks`
loop can never fire for ONNX models — the backend most prone to arena OOM. **Fix:** when
`self._is_onnx`, use the NVML used/total ratio (cheap once #53 caches the handle).
**Effort:** Small. **P2.**

#### 57. Redundant warmup encode in `embed_chunks`

`embedder.py:1136-1141` runs `self.model.encode(["warmup"])` to force model load, but
`ModelLoader.load()` already performed warmup + activation measurement on both backends
(`model_loader.py:651`, `:409`). Accessing `self.model` alone triggers the load; the
extra forward pass is wasted (and misleads readers into thinking it's load-bearing).
**Fix:** replace with `_ = self.model`. **Effort:** Trivial. **P3.**

#### 58. ONNX wrapper micro-issues (perf + clarity)

- `onnx_wrapper.py:136`: `if target_device == "cuda"` — exact match; a configured
  `"cuda:0"` leaves inputs on CPU. Optimum still runs (IOBinding copies them), but the
  H2D copy happens per call instead of binding device pointers; optimum enables
  IOBinding by default on the CUDA EP precisely to avoid this
  ([optimum GPU guide][optimum-gpu]). Use `target_device.startswith("cuda")` and
  `.to(target_device)`.
- Optional: allocate tokenized batches in pinned memory and transfer with
  `non_blocking=True` — official PyTorch guidance for faster H2D
  ([CUDA notes: pinned memory][pt-pinned]); modest win, measure first.
- `onnx_wrapper.py:140`: `torch.no_grad()` around the ORT call has no effect on ORT
  execution (ORT runs outside autograd; optimum wraps outputs in fresh tensors). Harmless
  — keep or drop with a one-line comment so readers don't infer it's load-bearing.
  (Reasoned from optimum source; no official doc statement exists.)

**Effort:** Trivial each. **P3.**

---

### P2/P3 — MCP pipeline hygiene

#### 59. Anchor embeddings: N sequential `embed_query` calls → one batch

`intent_classifier.py:424-435` embeds each anchor query in a Python loop;
`CodeEmbedder.embed_queries_batch` (`embedder.py:1500`) already exists and does one
forward pass with cache integration. First-search latency win; pairs with #43a.
**Effort:** Trivial. **P2 (first request only).**

#### 60. `handle_call_tool` serializes large results on the loop

`server.py:281-290` `json.dumps` of potentially large result dicts runs inline (and
again inside `format_response`). Only matters for big subgraph responses; offload when
`len(results)` is large, or leave with a comment. **Effort:** Trivial. **P3.**

#### 61. (v1 #25) Config `stat()` per call — keep, but document

`search/config.py:894-899` stats the config file on every `load_config()` to support
hot-reload; called on every tool call. A `st_mtime` check is ~1 µs — acceptable; document
the tradeoff at the call site rather than "fixing" it. **Effort:** Trivial. **P3.**

#### 62. Error responses echo full `arguments`

`server.py:310` includes the raw arguments dict in the error payload — fine today, but
`index_directory`/`search_code` arguments can be large and the echo doubles log noise
(`exc_info` already captures context). Trim to keys or first 200 chars. **Effort:**
Trivial. **P3.**

---

## Part C — Ranked execution plan

**Batch 3 — correctness + event-loop (small effort, do first)**
1. **#43** — offload the six residual blocking sites (a–f). *(P1)*
2. **#44** — clear `_metadata_cache` on `clear_index`/`remove_file_chunks`. *(P1)*
3. **#46** — explicit `max_length` in ONNX tokenization, registry-configurable. *(P1)*
4. **#45** — fix `_count_chunks_in_file`. *(P1/P2)*
5. **#47** — normalize ids in `upgrade_call_edge` / `__contains__`. *(P1-Windows)*
6. **#48, #49** — eval truthiness/off-by-one; merkle unreadable-file sentinel. *(P2)*

**Batch 4 — embedding-path throughput (the perf payoff)**
7. **#50** — per-file context cache in `create_embedding_content` (largest win). *(P2)*
8. **#51** — ONNX length-sorted sub-batching honoring `batch_size`. *(P2)*
9. **#54** — reorder ONNX warmup/measurement; aim to retire the hardcoded floors. *(P2)*
10. **#52** — ego-graph `{chunk_id→idx}` map + `reconstruct_batch`. *(P2)*
11. **#53** — NVML init-once + `nvidia-ml-py` dependency rename. *(P2)*
12. **#56** — NVML-based VRAM check on the ONNX path. *(P2)*
13. **#55** — de-duplicate metadata content. *(P2)*
14. **#59** — batch anchor embedding. *(P2, first-request)*

**Batch 5 — polish + remaining v1 deferred**
15. **#57, #58, #60, #61, #62** — micro/clarity items. *(P3)*
16. v1 deferred, re-ranked: **#17** (O(files×chunks) verification scan) and **#18**
    (rglob-per-extension) next — they sit on the indexing hot path; then **#15/#16/#28**
    (chunking/community), **#22** (edge-weights no-op — decide: implement weighted
    traversal budget or delete the config surface), **#13** (non-Python chunk names —
    schedule with language-support work).

**Validation gates per batch:** existing pytest suite + a force-reindex run on a
memory-constrained GPU before touching #46/#54 floors; an event-loop-stall probe
(`asyncio` task that logs if `loop.time()` jumps > 250 ms) while exercising
search/index/cleanup tools for #43.

---

## Part D — Claims reviewed and rejected (false positives)

Recorded so they aren't re-reported by future reviews:

- **`indexer.py:156` "wrong shape axis"** — rejected. `EmbeddingResult.embedding` is
  1-D `(embedding_dim,)` by contract (`embedder.py:1124-1126` docstring); `shape[0]` is
  the dimension, not a batch axis.
- **`indexer.py:198-206` "start_id captured before add()"** — rejected. Capturing
  `ntotal` *before* appending is the correct base for positions of the vectors about to
  be added; writes are serialized by the state/pool locks (v1 #7).
- **"Rename to `PYTORCH_ALLOC_CONF`"** — rejected *for this repo*: torch is pinned
  `>=2.8,<2.9` and 2.8 reads only `PYTORCH_CUDA_ALLOC_CONF`; the rename + deprecation
  landed in 2.9 ([pytorch 2.9 release notes][pt-29]). Revisit when the pin moves.
- **`expandable_segments` on Windows** — the existing comment (`embedder.py:202`) is
  *correct*: gated on `PYTORCH_C10_DRIVER_API_SUPPORTED`, which CMake defines only
  `if(NOT WIN32)` in v2.8.0 — no action.
- **`gpu_mem_limit` semantics** (v1 #31) — re-confirmed against the ORT CUDA EP docs:
  arena-only. Optional follow-up, not a bug: the run option
  `memory.enable_memory_arena_shrinkage` is the documented way to return arena memory
  between runs if idle-VRAM footprint ever matters ([ORT run-options keys][ort-shrink]).
- **`torch.cuda.set_per_process_memory_fraction` coverage** — re-confirmed: caching
  allocator only; ORT/FAISS unaffected — the code's existing comments
  (`embedder.py:315-318`) already state this accurately.

---

## Part E — Documentation verified against

- PyTorch 2.8 — [CUDA semantics / allocator env vars][pt-cuda] ·
  [v2.8.0 `CUDAAllocatorConfig.h`](https://github.com/pytorch/pytorch/blob/v2.8.0/c10/cuda/CUDAAllocatorConfig.h) ·
  [v2.8.0 `c10/cuda/CMakeLists.txt`](https://github.com/pytorch/pytorch/blob/v2.8.0/c10/cuda/CMakeLists.txt) ·
  [`set_per_process_memory_fraction`](https://docs.pytorch.org/docs/2.8/generated/torch.cuda.set_per_process_memory_fraction.html) ·
  [`mem_get_info`](https://docs.pytorch.org/docs/2.8/generated/torch.cuda.mem_get_info.html) ·
  [pinned-memory guidance][pt-pinned] · [PyTorch 2.9 rename notes][pt-29]
- ONNX Runtime — [CUDA Execution Provider options][ort-cuda] ·
  [run-options config keys (arena shrinkage)][ort-shrink] ·
  [pybind `log_severity_level` docstring](https://github.com/microsoft/onnxruntime/blob/main/onnxruntime/python/onnxruntime_pybind_state.cc)
- HuggingFace Optimum — [GPU usage guide (IOBinding default on CUDA)][optimum-gpu] ·
  [`check_io_binding` source](https://github.com/huggingface/optimum-onnx/blob/main/optimum/onnxruntime/utils.py)
- transformers — [padding & truncation (v4.57)][hf-trunc] · [BAAI/bge-m3 (`model_max_length: 8192`)][bge-m3]
- sentence-transformers — [v5.2.2 `encode()` length sorting][st-encode]
- Python — [asyncio: running blocking code][asyncio-dev] ·
  [`asyncio.to_thread`](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread) ·
  [asyncio sync primitives (loop binding, not thread-safe)](https://docs.python.org/3/library/asyncio-sync.html)
- NVML — [initialization & cleanup (refcounted, thread-safe)][nvml] ·
  [`nvidia-ml-py` (official; `pynvml` deprecated)](https://pypi.org/project/nvidia-ml-py/)
- FAISS — [special operations (`reconstruct_n`, `reconstruct_batch`)][faiss-wiki] ·
  [MetricType & distances (IP + L2-normalize = cosine)](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances)
- MCP Python SDK — [v1.27.0 `Server.run()` task-per-request dispatch][mcp-sdk]

[asyncio-dev]: https://docs.python.org/3/library/asyncio-dev.html#running-blocking-code
[mcp-sdk]: https://github.com/modelcontextprotocol/python-sdk/blob/v1.27.0/src/mcp/server/lowlevel/server.py
[hf-trunc]: https://huggingface.co/docs/transformers/v4.57.0/en/pad_truncation
[bge-m3]: https://huggingface.co/BAAI/bge-m3
[st-encode]: https://github.com/huggingface/sentence-transformers/blob/v5.2.2/sentence_transformers/SentenceTransformer.py
[faiss-wiki]: https://github.com/facebookresearch/faiss/wiki/Special-operations-on-indexes
[nvml]: https://docs.nvidia.com/deploy/nvml-api/group__nvmlInitializationAndCleanup.html
[optimum-gpu]: https://huggingface.co/docs/optimum/onnxruntime/usage_guides/gpu
[pt-pinned]: https://docs.pytorch.org/docs/2.8/notes/cuda.html#use-pinned-memory-buffers
[pt-cuda]: https://docs.pytorch.org/docs/2.8/notes/cuda.html
[pt-29]: https://pytorch.org/blog/pytorch-2-9/
[ort-cuda]: https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html
[ort-shrink]: https://github.com/microsoft/onnxruntime/blob/main/include/onnxruntime/core/session/onnxruntime_run_options_config_keys.h
