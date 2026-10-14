# VRAM budget has one home: `VramBudget` in `embeddings/vram_budget.py`

Status: accepted
Date: 2026-10-13

## Context

The per-process PyTorch VRAM cap and the GPU batch sizer grew inside `embeddings/embedder.py`
as five module functions (`set_vram_limit`, `compute_effective_vram_cap`, `_own_cached_vram_gb`,
`calculate_optimal_batch_size`, `VramCapReading`) with six call sites. The embedder applied the
cap in `__init__` and again in `embed_chunks`, and each of the three rerankers copy-pasted the same
nine-line "re-apply the cap from config" block behind a lazy import. Every caller read
`performance.vram_limit_fraction`, `dynamic_batch_min` and `dynamic_batch_max` for itself, and
`embed_chunks` re-derived the batch sizer's memory fraction (`0.8125` of the cap, clamped to
`[0.05, 0.95]`) inline. A fourth place, `search/vram_manager.py`, held a `VRAMTierManager` class
with no production caller, next to the `VRAM_TIERS` table that `search/index_probe.py` actually
reads. The table's 6/10/18 GB bands were re-encoded as literals in three functions, and the batch
sizer's copy used `<=` where the table is half-open.

Two kinds of caller (embedder, rerankers) already sat on this behaviour, so the seam was real; it
just had no interface, and a change to the cap policy touched all four files.

## Decision

- `embeddings/vram_budget.py` is the only module that reads the three `performance.*` VRAM fields
  (`search/config.py` liveness `reader=` metadata points there). It exposes one object,
  `VramBudget` (`cap_fraction`, `batch_min`, `batch_max`), built once with `from_config(performance)`
  or `default()` when no config can be read, and used only through `apply_cap(min_room_gb)`,
  `batch_size(...)` and the non-fatal `reapply_cap(logger)`. The batch sizer's share of the cap is a
  class constant. The module functions remain as the implementation behind it.
- `search/vram_manager.py` is the tier table only: `VRAMTier` rows carry the per-tier numbers
  (recommended model, reranker, `embed_batch_size`, `dynamic_batch_max`, `sizer_max_batch`,
  `sizer_min_batch`) and `tier_for(vram_gb)` is the one band lookup. `VRAMTierManager` is deleted.
  A new per-tier number is a new column on the row, never a new literal at a call site.
- RAM fallback stays resolved inside `set_vram_limit` at apply time, not captured in `VramBudget`:
  the indexing override is per run ([ADR-0011](0011-listwise-reranker-doc-cap.md)) and must be read
  when the cap is applied, not when the budget was built.
- The rerankers import `VramBudget` lazily inside the loading method. A module-level import would
  close the cycle `search/__init__` -> `reranking_engine` -> `neural_reranker` -> `embeddings.vram_budget`
  -> `search.config`.

## Consequences

- Paths quoted by older records moved without a behaviour change:
  [ADR-0007](0007-onnx-token-contract-and-activation-floors.md)'s
  `embeddings/embedder.py::calculate_optimal_batch_size` and
  [ADR-0011](0011-listwise-reranker-doc-cap.md)'s `set_vram_limit()` now live in
  `embeddings/vram_budget.py`.
- Golden set: Q116 and H034 retarget `calculate_optimal_batch_size` to its new file; H039 drops the
  deleted class and keeps `VRAMTier` as its grade-3 gold (recorded in the dataset's `_meta.changelog`).
  The retrieval path itself is untouched, so no SSCG re-baseline was run.
- Band edge: a GPU reporting exactly 6.0 or 10.0 GB now takes the larger tier's sizer clamp
  (half-open bands, matching the table). Measured cards report fractions, so no real device moves.
- Tests patch `embeddings.vram_budget.set_vram_limit`, not the embedder, and `VramBudget` is tested
  through its interface in `tests/unit/embeddings/test_vram_budget.py`.
