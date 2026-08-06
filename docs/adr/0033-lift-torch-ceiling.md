# Lift the torch `<2.9.0` ceiling, bump the ML stack

Status: accepted
Date: 2026-08-06

## Context

`pyproject.toml` pinned `torch>=2.8.0,<2.9.0` since commit `b68cfff8` (2026-01-06) with the stated
rationale: *"2.9.x breaks ModernBERT `torch.compile`"* (`docs/PYTORCH_COMPATIBILITY.md:98-100`,
pre-edit). That rationale was verified false on both legs before this round touched anything:

- The **GTE-ModernBERT embedder** the ceiling protected was deleted from `MODEL_REGISTRY` in
  commit `24f6b8c` (2026-07-31).
- The pinned `transformers>=5.3.0,<6` floor **removed ModernBERT's `reference_compile` path
  entirely** — `grep torch.compile` over the installed `transformers/models/modernbert/*.py`
  returns nothing; only a `output.pop("reference_compile", None)` serialization leftover
  survives. So even the still-registered `gte-reranker-modernbert-base` *reranker*
  (`RERANKER_MODELS["lightweight"]`, distinct from the deleted embedder) cannot reach the
  inductor path that motivated the ceiling.
- The project never calls `torch.compile` itself — the single `_dynamo` hit is a log suppressor
  (`mcp_server/server.py:207`). Nine benchmark logs under `scripts/logs/` showed TorchDynamo
  tracing zero frames.

Meanwhile torch carried 8 tracked CVEs at 2.8.0+cu128 (invisible to `pip-audit`'s default PyPI
service — it silently `skip_reason`s local-version wheels like `2.8.0+cu128`; only visible via
`pip-audit -s osv`, the fallback `tools/summarize_audit.py` runs automatically since the
2026-08-06 dep-audit fix). `2.10.0` closes 6 of 8, including both CVSS 8.8 vulnerabilities in the
set (`CVE-2026-24747`, a `weights_only` unpickler bypass, and `CVE-2025-3001`, a `torch.lstm_cell`
memory-corruption bug — an earlier version of this project's own audit trail mischaracterized
`CVE-2025-3001` as a *second* `weights_only` bypass; it is not, though the 6-of-8 closure count
and the fix version were correct throughout).

The torch pin is a **single-package move**: reverse-dependency check confirmed only
`claude-context-local` itself constrained `torch<2.9.0`; `sentence-transformers` only requires
`torch>=1.11.0`. No `triton`/`xformers`/`tensorrt` were installed, so there was no coordinated
CUDA-ecosystem upgrade to sequence — though `torch`'s own transitive deps (`triton`,
`nvidia-nccl-cu12`, plus two newly-added `cuda-bindings`/`cuda-pathfinder`/`nvidia-nvshmem-cu12`
packages) did move as part of the `uv lock` re-pin.

Alongside the torch ceiling, the retrieval libraries (`transformers`, `sentence-transformers`,
`faiss-cpu`, `huggingface-hub`, `hf-xet`) were also several minor versions behind — deferred in
the same-day dep audit specifically because moving them would invalidate the pinned deterministic
benchmark canons without a fresh A/B (`pyproject.toml` "Last audit" tracking comment, previous
entry).

## Decision

Two-stage upgrade, each independently gated on a fresh 63q intent-on benchmark arm against a
same-day pre-side baseline (substrate-drift rule: never diff a post-upgrade run against a stored
canon from a different substrate — `evaluation/RECALL_CAMPAIGN_CLOSEOUT_20260802.md:72`).

### Stage 1 — retrieval libraries

```
transformers          5.13.0 -> 5.14.1
sentence-transformers  5.6.1 -> 5.7.0
faiss-cpu             1.14.3 -> 1.15.0
huggingface-hub        1.22.0 -> 1.26.1
hf-xet                 1.5.1 -> 1.6.0
tokenizers              0.22.2 (unchanged — transformers 5.14.1 kept the same ceiling)
```

torch confirmed absent from `pip install --dry-run`'s "Would install" before dropping
`--dry-run`, verifying this stage does not touch torch.

### Stage 2 — torch

```
torch  2.8.0+cu128 -> 2.10.0+cu128
```

Installed via `pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cu128`
(never a bare `torch` — the explicit index keeps the `+cu128` local version). Verified
`torch.__version__ == "2.10.0+cu128"`, `torch.cuda.is_available() is True`,
`torch.version.cuda == "12.8"`.

### New ceiling: `<2.11.0`

Not floor-only, because `[tool.uv.sources]` pins `torch` to the explicit `pytorch-cu128` index,
which tops out at `2.11.0` (PyPI itself publishes newer releases; the CUDA-12.8 wheel index does
not). `<2.11.0` reflects that hard platform-availability limit, not a known regression — unlike
the old `<2.9.0` ceiling, there is no known reason to avoid `2.11.0`+ once the index publishes it.

### Per-side capture sequence (applied identically before both gates)

1. `cleanup_resources` (MCP tool — releases the `metadata.db` lock; no second server launched).
2. **Delete `chunk_embeddings.bin`** from the project's storage dir before reindexing. The cache
   provenance string is `f"v1|device={device}|dtype={dtype}|backend=pytorch"`
   (`embeddings/model_loader.py:227-240`) — **no library version** — so a `--mode force` reindex
   after a library upgrade would otherwise silently reuse pre-upgrade vectors and report a
   spurious null result.
3. `tools/batch_index.py --path . --mode force`.
4. `scripts/benchmark/audit_golden_dataset.py` — confirmed CLEAN (both datasets, both stages).
5. Capture with `CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0` exported (post-ADR-0021: 0 flips,
   0.0000 spread — one round per side suffices).

## Measurement

Gate metric is the 63q intent-on arm (`--set intent.enabled=true` — the harness pins
`intent.enabled=False` per query by default at `run_sscg_benchmark.py:738-739`, re-asserted
unless the arm's own override is present; this is the only way to measure what actually ships,
per ADR-0026/B1b).

| Capture | Substrate | MRR | Recall@5 | Recall@10 | pool_hit_rate |
|---|---|---|---|---|---|
| `canon_k0_63q_arm` (pre-upgrade) | 205 files / 2331 chunks | 0.858 | 0.678 | 0.801 | 0.905 |
| `canon_k1_63q_arm` (post Stage 1) | 205 files / 2331 chunks | 0.858 | 0.678 | 0.801 | 0.905 |
| `canon_k2_63q_arm` (post Stage 2) | 205 files / 2331 chunks | 0.860 | 0.683 | 0.788 | 0.905 |

### Adoption gate (methodology rule 7: accept unless the paired 95% CI on MRR excludes zero on
the losing side)

**Stage 1** (`canon_k0` → `canon_k1`, n=63 shared queries):

| Metric | mean Δ | 95% CI | n_moved |
|---|---|---|---|
| MRR | +0.0000 | [+0.0000, +0.0000] | 0 |
| recall@5 | +0.0000 | [+0.0000, +0.0000] | 0 |
| recall@10 | +0.0000 | [+0.0000, +0.0000] | 0 |
| ndcg@5 | +0.0002 | [−0.0002, +0.0007] | 1 |
| hit | +0.0000 | [+0.0000, +0.0000] | 0 |

Byte-identical retrieval outcome (0 queries moved on every ranking metric) — the retrieval
libraries' internal changes did not touch this project's usage surface. **Gate passes trivially.**

**Stage 2** (`canon_k1` → `canon_k2`, n=63 shared queries):

| Metric | mean Δ | 95% CI | n_moved |
|---|---|---|---|
| MRR | +0.0026 | [−0.0025, +0.0078] | 1 |
| recall@5 | +0.0053 | [−0.0265, +0.0371] | 8 |
| recall@10 | −0.0132 | [−0.0394, +0.0130] | 8 |
| ndcg@5 | +0.0024 | [−0.0163, +0.0210] | 13 |
| hit | +0.0000 | [+0.0000, +0.0000] | 0 |

All five CIs include zero — **gate passes.** The small per-query movement (9 distinct queries
shifted, e.g. Q12 +0.167 MRR, Q56/Q74/Q76/Q87 small negative shifts) is consistent with normal
kernel-level floating-point reordering across a two-minor-version torch bump, not a systematic
regression.

### Determinism re-validation

`--deterministic-gpu` strict mode (`utils/determinism.py` — raises `RuntimeError` on any op
lacking a deterministic implementation) completed the full 63q arm capture with **zero
`RuntimeError`s**, confirming torch 2.10.0 introduces no non-deterministic kernel into this
project's retrieval/rerank funnel.

## Consequences

- `pyproject.toml`: `torch>=2.10.0,<2.11.0`, `transformers>=5.14.1,<6`,
  `sentence-transformers>=5.7.0`, `faiss-cpu>=1.15.0`, `huggingface-hub>=1.26.1`.
- `uv.lock` re-pinned via `uv lock --upgrade-package` (one flag per moved package, never
  `uv sync` which could re-resolve and drop the `+cu128` local version) — resolved versions
  verified byte-identical to `pip freeze` for all six packages. `uv lock --check` passes.
- Editable-install metadata refreshed (`pip install -e . --no-deps`) so `pip check` reads the new
  pins rather than stale dist-info from the previous install — without this, `pip check` reports
  a phantom `torch<2.9.0` conflict even though the installed torch and the `pyproject.toml` pin
  agree.
- `docs/PYTORCH_COMPATIBILITY.md` rewritten: new ceiling, corrected `CVE-2025-3001`
  characterization, new acceptable-versions table, new troubleshooting commands.
  `docs/INSTALLATION_GUIDE.md` and `README.md` version strings updated to match.
- Torch CVE ledger: 8 tracked → 2 remaining (`CVE-2026-4538`, no fix at any version;
  `CVE-2025-3000`, fixed in `2.13.0` which the pinned `cu128` index does not publish — reopening
  condition is now "re-check each cycle whether the index has started publishing `>=2.13.0`",
  replacing the old inductor-regression reopening condition).
- `canon_k2`'s intent-on arm becomes the new reference point pending the full four-view re-pin
  (63q/133q control+arm, F-via-similar) captured separately as `canon_k1` per the campaign's
  final-canon step.

## Verification

`./scripts/test/run_tests.sh tests/unit/ -q` green at both stages (5687 passed, 1 skipped,
identical count — the library upgrades did not add or remove any test-collectible surface).
`pip check` clean at both stages (Stage 2's transient `torch<2.9.0` conflict was the expected,
documented editable-metadata staleness, resolved by the `pip install -e . --no-deps` refresh
above). `audit_golden_dataset.py` CLEAN on both datasets after every reindex. CUDA verified intact
throughout (`torch.cuda.is_available()` True, device RTX 4090).

## Out of scope

- **torch 2.13.0** — closes the 8th CVE (`CVE-2025-3000`) but the pinned `cu128` index does not
  publish it; using the plain-PyPI build would drop the `+cu128` local version and break the CUDA
  toolchain pin. Reopening condition recorded in `pyproject.toml`.
- **tree-sitter 0.26.0** — touches the chunker; changing chunk boundaries/kinds risks golden-ID
  breakage and possibly an `INDEX_VERSION` bump. Its own campaign.
- The 4-package `opentelemetry-*` sibling-pin cluster, `fsspec`, `mpmath`, `pydantic_core` —
  unrelated to the ML stack; `mpmath` is blocked by `sympy<1.4` regardless.
