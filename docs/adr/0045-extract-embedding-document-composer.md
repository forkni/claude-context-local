# Extract the embedding-document composer from `CodeEmbedder`

Status: accepted
Date: 2026-08-19

## Context

`CodeEmbedder` (`embeddings/embedder.py`, ~1,928 lines; the class itself spans `:490-1928`, 35
methods) owns GPU model lifecycle, batching, OOM backoff, and a query cache — and, contiguously at
`:748-1048`, 298 lines that decide **what text represents a chunk**: whether to prepend a
structural header, how many lines of import context to pull in, how much of the parent class's
signature to include, and how to assemble all of that plus the chunk's own content into the string
actually handed to `model.encode()`.

That cluster is AST-verified model-free — zero references to `self.model`, `device`, torch, or any
tokenizer — and internally closed. `_read_source_cached`'s only direct callers are
`_extract_import_context` and `_get_class_signature` (LSP-resolved, confidence 0.98); those two
exit only into `create_embedding_content`; and that function's only callees outside the cluster are
the two helpers plus `get_search_config`. Its entire external interface is a logger plus three
plain instance dicts. `embed_chunks` already hoists the composition call **above** the model-load
block with the comment "`create_embedding_content` needs no model", so a 100% chunk-cache hit
returns without ever loading a model — a property that was load-bearing but guaranteed only by
convention, not by any module boundary.

The template for the extraction is `search/rerank_window_policy.py`, not `_build_rerank_document`:
a frozen-dataclass policy object in its own module, with a `from_config`-style classmethod, whose
fields' `search/config.py` `reader=` strings point at the module that *governs the behaviour*
rather than the module that *fetches the config*. `doc_representation_mode` follows the same split
— `reader="search/neural_reranker.py"`, fetched in `reranking_engine.py`. That convention settles
where the `get_search_config()` call stays: in `embedder.py`, not the new module, so all 20 existing
`embeddings.embedder.get_search_config` patch sites (including every test in
`test_structural_header.py`) keep working untouched.

## Decision

New module `embeddings/document_composer.py`:

- `EmbeddingDocumentPolicy` — a frozen dataclass with the five fields that govern composition
  (`enable_import_context`, `enable_class_context`, `max_import_lines`,
  `max_class_signature_lines`, `enable_structural_header`), field names byte-identical to
  `EmbeddingConfig`'s so `from_config` is a plain attribute copy. See `CONTEXT.md`'s "Document
  policy" glossary entry.
- `EmbeddingDocumentComposer` — `compose(chunk, policy, max_chars=6000) -> str` (the seam),
  `clear_caches()`, and the three moved-verbatim helpers (`_read_source_cached`,
  `_extract_import_context`, `_get_class_signature`). A class rather than free functions: the three
  mtime-keyed caches collapse O(chunks × filesize) file I/O to O(files) within a pass, and that
  state needs an owner. `CodeEmbedder.__new__` now constructs one composer instance, so every
  `__new__`-only construction path (test mocks, unpickling) gets a working composer for free — the
  same hook already existed for exactly this purpose.

Landed as two commits, two hats:

**Commit 1 — pure refactor, byte-identical output** (`e3256e3`). Move the three helpers verbatim;
split `create_embedding_content` into a fetch-half that stays in `CodeEmbedder` and a compose-half
that moves. `EmbeddingDocumentPolicy`'s int defaults were, deliberately, verbatim copies of the
existing fallback literals (`10`/`5`) — reconciling them with the real config defaults was left to
commit 2 so the refactor commit changed no behaviour at all. Repointed the five affected
`search/config.py` `reader=` strings at `document_composer.py`. Moved 8 tests into a new
`tests/unit/embeddings/test_document_composer.py` that **never imports `CodeEmbedder`** — that
import-absence is the model-freeness proof.

Gate B1 byte-identity digest over `chunking/ graph/ merkle/ utils/ mcp_server/`, before and after:
`files=101 chunks=844 bytes=1518374 sha256=b249be70f69eb0c7e778381b9e277f1321c2388d7d885d88dc33cd1f7c8b4bb3`
— identical both sides.

**Commit 2 — behaviour: derive the degraded-path caps from `EmbeddingConfig`** (`f0fefc8`). The
fallback used only when `get_search_config()` raises had fallen out of sync with the real config
defaults: `max_import_lines=10` / `max_class_signature_lines=5` in the fallback, versus
`EmbeddingConfig`'s actual `25` / `20`. `get_search_config()` does file I/O and JSON parsing and is
called once per chunk inside `embed_chunks`'s comprehension, so a corrupt or transiently unreadable
`search_config.json` mid-index silently composed a *shorter* document for the affected chunks —
which is also their persistent chunk-embedding cache key (`embeddings/chunk_cache.py`). All five
`EmbeddingDocumentPolicy` fields now default to `EmbeddingConfig`'s own class attributes directly
(a plain `@dataclass`, no `__post_init__`, so the class attribute already is the defaulted int/bool
— no instantiation needed) rather than duplicating literals, closing the whole drift class instead
of just today's instance of it.

Ratchet test: `EmbeddingDocumentPolicy() == EmbeddingDocumentPolicy.from_config(SearchConfig())`
(`tests/unit/embeddings/test_document_composer.py::TestPolicyDefaultsMatchConfig`) — it would have
failed on the pre-fix code (`10 != 25`, `5 != 20`) and fails again the day anyone edits
`EmbeddingConfig`'s defaults without updating this file, because there is nothing left in this file
to update.

Also fixed `create_embedding_content`'s docstring (`embeddings/embedder.py`), which restated two
wrong "default:" values and omitted `enable_structural_header` entirely. Per ADR-0042/0043, it now
points at `EmbeddingConfig` rather than restating numbers that can drift from it again.

Gate B1 re-verified on a restricted corpus — `chunking/ graph/ merkle/ utils/`, excluding
`mcp_server/` this round because Workstream D's parallel agent was concurrently, actively editing
files inside it, making that directory unsafe as a "frozen" comparison corpus:
`files=72 chunks=607 bytes=1092496 sha256=e448d179af99622213b9516303bf489822059df38e4305f0d223596132c34dcd`
— identical before and after, confirming the fix is scoped to only the fallback path and did not
leak into the config-available path (which was, and remains, unaffected — it always read live
`EmbeddingConfig` values via `from_config`).

## Consequences

- `embeddings/document_composer.py` is a new, standalone, model-free module — testable without
  constructing a `CodeEmbedder` or loading any model, and independently reusable if a second caller
  ever needs "what text represents this chunk" without the rest of `CodeEmbedder`'s machinery.
- `CodeEmbedder.create_embedding_content` is now a ~7-line delegator: fetch config, build a policy
  (or fall back to the policy's own defaults on failure), delegate to
  `self._document_composer.compose(...)`. The three `getattr(self, "_class_file_cache", None)`
  defensive guards that existed to handle `__new__`-only construction paths were deleted; the
  composer is unconditionally present after `__new__`.
- A corrupted or transiently unreadable `search_config.json` mid-index now composes the *same*
  document (modulo the config values that were actually meant to differ) as the healthy-config
  path would for the caps that matter, instead of silently truncating import/class context further
  than intended for a subset of chunks.
- **Deferred, not fixed here:** `CodeEmbedder.cleanup()` (`:1850-1903`) does not clear the three
  composer caches, and `mcp_server/model_pool_manager.py` holds one `CodeEmbedder` for the process
  lifetime — so they grow unbounded for the life of the process. Pre-existing before this
  extraction; the extraction gives the problem a name and a home (`clear_caches()`) but does not
  wire it into `cleanup()`. Likewise the per-chunk `get_search_config()` call was deliberately kept
  as-is — hoisting it out of the per-chunk loop would stop live config edits from taking effect
  mid-run, a separate behaviour change outside this extraction's scope.
- `CONTEXT.md` gains **Embedding document** and **Document policy** glossary entries — the repo had
  no noun for either concept before this extraction gave them a module to be named after.

## Verification

- `tests/unit/embeddings/test_document_composer.py` — 19 tests (8 moved from
  `test_embedder.py::TestContextExtraction`, plus the commit-2 ratchet test), none importing
  `CodeEmbedder`.
- `tests/unit/embeddings/test_embedder.py` and `test_structural_header.py` — all pre-existing
  `embeddings.embedder.get_search_config` patch sites and cache-clearing call sites
  (`embedder._document_composer.clear_caches()`, replacing the old two-attribute clear) pass
  unchanged.
- `tests/unit/mcp_server/test_profile_full_index_layer3_patch.py` (new) —
  `test_profiler_layer3_patch_point_intercepts_composition`, guarding against
  `profile_full_index.py`'s class-attribute monkeypatch silently rebinding a dead attribute after
  the move.
- Full `tests/unit/` and `tests/fast_integration/` + `tests/integration/` green at both commits;
  `pyrefly check` clean.
- Gate B1 byte-identity digests (above) confirm zero output drift at commit 1 and a fix scoped
  exactly to the fallback path at commit 2 — the composed string is the persistent chunk-embedding
  cache key, so any unintended drift here would have invalidated every cached vector in every
  indexed project.
