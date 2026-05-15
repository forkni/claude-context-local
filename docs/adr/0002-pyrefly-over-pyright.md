# Use Pyrefly as the type checker; do not adopt Pyright or Mypy

Status: accepted
Date: 2026-05-15

`docs/styleguides/PYTHON_STYLE_GUIDE.md §1.2, §5, §12` require type hints for all public
functions, but no tool enforced this: `pyproject.toml` had no `[tool.pyright|mypy|pyrefly|ty]`
block and the pre-commit hook only ran `ruff`. Spot-check (2026-05-15): `mcp_server/server.py`
100%, `embeddings/embedder.py` 88%, `search/searcher.py` 50%, `chunking/multi_language_chunker.py`
50%, `graph/community_detector.py` 50% — overall ~70% return-annotated. We adopt Pyrefly 1.0 as
the enforcing checker.

Three concrete payoffs for this codebase:

1. **Search-index integrity.** `search/faiss_index.py`, `search/indexer.py`, `search/mmap_vectors.py`,
   `embeddings/embedder.py` shuttle numpy arrays through FAISS (native, stubless) with implicit
   dtype/shape contracts. `np.float32`/`np.float64` drift or a FAISS signature change surfaces only
   at index-build or query time without a checker; Pyrefly catches it at edit time.

2. **MCP tool signature drift.** `mcp_server/server.py` wires 19 tools through
   `mcp_server/tool_registry.py` to handlers in `mcp_server/tools/*.py`. Handler signatures, tool
   registration schemas, and `mcp.types` must agree — drift breaks tool calls at the protocol layer
   for external clients. A checker against `mcp.server.lowlevel` + `mcp.types` flags mismatches
   at edit time.

3. **Style-guide enforcement.** §11 already prescribed Pyrefly (pre-1.0), but without config the
   prescription was aspirational. `[tool.pyrefly]` in `pyproject.toml` makes it enforced.

## Considered Options

- **Pyrefly 1.0 — chosen.** Stable 1.0.0 released May 2026. Default type checker at PyTorch (this
  codebase imports torch in `search/neural_reranker.py`), JAX, and Instagram (20M LOC). 10×–50×
  faster than Pyright; significantly better torch/transformers handling than Mypy. `permissive-ignores`
  respects existing `# type: ignore` comments (20 sites in this repo). `replace-imports-with-any`
  suppresses noise from stubless native deps (faiss, tree_sitter_*, rank_bm25, onnxruntime) at
  the config layer rather than per-file.
- **Pyright** — not chosen. More conformant (~99% typing-spec vs Pyrefly's ~88–90%), but slower,
  with weaker handling of torch tensor subclasses and diffusers/transformers patterns. No
  exotic generics or variance in this codebase — the conformance gap is not load-bearing.
- **Mypy** — not chosen. Slow, weak on torch, requires per-package stubs. Not prescribed by §11.
- **Ty (Astral)** — not chosen. Still beta as of 2026-05-15; no stable 1.0 release.

## Consequences

- `pyproject.toml` gains `[tool.pyrefly]` with `replace-imports-with-any` for all stubless deps.
- `pyrefly>=1.0` added to `[project.optional-dependencies].dev`.
- `.githooks/pre-commit` gains a non-blocking `pyrefly check` block (mirrors existing ruff pattern).
- 165 existing type errors suppressed with `# pyrefly: ignore[...]` via `pyrefly suppress` — future
  code requires annotations or an explicit per-line suppress at the offending site.
- `docs/styleguides/PYTHON_STYLE_GUIDE.md §11` updated to match 1.0 config format.
- ~10% typing-spec coverage lost vs Pyright — acceptable; no exotic generics in this codebase.
- `docs/styleguides/PYTHON_STYLE_GUIDE.md §11` must be kept current with Pyrefly version bumps.

## Re-evaluation triggers

Revisit this decision when any of the following hold:

1. Pyright ships a torch-optimized mode competitive with Pyrefly on this dep tree.
2. The backlog of `# pyrefly: ignore[...]` comments grows faster than it shrinks (signal that
   `replace-imports-with-any` heuristics need tightening rather than suppression at call sites).
3. Ty reaches stable 1.0 with comparable throughput and torch handling.
