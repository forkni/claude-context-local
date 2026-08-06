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

### Stage 3 — torch 2.11.0+cu128 (CVE-2026-4538 correction)

This project's own final-verification step (a fresh `/deps-audit` run intended only to record the
after-state) caught a factual error in the Stage 2 CVE ledger before it was committed. The ledger
above and the corresponding text in `pyproject.toml`/`docs/PYTORCH_COMPATIBILITY.md` claimed
`CVE-2026-4538` had "no upstream fix at any version." That claim was **wrong**, and the reason it
went unnoticed is itself worth recording:

**Root cause**: `pip-audit`'s default OSV lookup silently drops findings for packages with a local
version suffix. `torch==2.10.0+cu128` (and `2.11.0+cu128`) never matches OSV's affected-versions
list, which only enumerates plain versions like `"2.10.0"` — no `skip_reason`, the CVE entry is
simply absent from the report, indistinguishable from "not affected." This is the same class of
silent gap as the `pip-audit` PyPI-service `skip_reason` issue this project's dep-audit tooling
already works around for the whole-package case (see the "Context" section above) — but this time
it was a per-CVE version-matching gap inside the OSV fallback path itself, not caught by the
existing workaround.

**Ground truth**, obtained by querying the OSV API directly rather than trusting `pip-audit`'s
report:

```
curl https://api.osv.dev/v1/vulns/PYSEC-2026-139
```

The response's `ranges` field is `[{type: "ECOSYSTEM", events: [{introduced: "0"}, {last_affected:
"2.10.0"}]}]`, its explicit `versions` list enumerates every affected release up to and including
`"2.10.0"` but not `"2.11.0"`, and its `references` include a `type: "FIX"` entry pointing to the
merged PR `pytorch/pytorch#176791`. Together this is definitive: torch **2.10.0 was still
vulnerable**; **2.11.0 is the version that actually closes it**.

**New standing rule** (recorded in `docs/PYTORCH_COMPATIBILITY.md`): always verify torch CVE claims
against the raw OSV API, not just `pip-audit`'s report, whenever the installed wheel carries a
local version suffix (`+cu128`, `+cu124`, etc.).

Surfaced to the user as a scope question (stay at 2.10.0 with corrected-but-still-open-CVE docs,
vs. bump one more version to close it for real) — user selected the bump.

```
torch  2.10.0+cu128 -> 2.11.0+cu128
```

Installed the same way as Stage 2 (`pip install torch==2.11.0 --index-url
https://download.pytorch.org/whl/cu128`, never a bare `torch`). Verified
`torch.__version__ == "2.11.0+cu128"`, `torch.cuda.is_available() is True`,
`torch.version.cuda == "12.8"`.

**New ceiling: `<2.12.0`** — `2.11.0` is still the `pytorch-cu128` index's current maximum, so the
ceiling shifts by exactly one minor version, same platform-availability rationale as before.

**Side effect discovered**: torch `2.11.0` declares `setuptools<82`, which downgraded the venv's
installed `setuptools` from `83.0.0` (this project's runtime security floor for
`CVE-2026-59890`) to `78.1.0` on install. Investigated and judged an acceptable, build-time-only
tradeoff:

- Grepped the entire codebase for `import setuptools|import pkg_resources|from setuptools|from
  pkg_resources` — zero matches. No runtime code path touches setuptools.
- `[build-system].requires >=83.0.0` in `pyproject.toml` still governs actual package builds via
  PEP 517 isolated build environments, unaffected by the venv's installed version.
- `pip check` stays clean — build-system requirements aren't runtime dependency declarations.
- Confirmed by inspecting the wheel METADATA directly: torch 2.10.0 has no setuptools ceiling at
  all (`Requires-Dist: setuptools; python_version >= "3.12"`, unconditional on version); the
  `<82` constraint is new to 2.11.0.

**Stage 3 gate** — same per-side capture sequence as Stages 1/2, against the current (Stage 2)
substrate as the pre-side. One complication actually occurred here: the user manually triggered a
reindex via the running MCP server's UI mid-investigation, and that reindex silently reused the
stale `chunk_embeddings.bin` left over from before the torch 2.11.0 install (cache provenance has
no library version — exactly the trap step 2 of the capture sequence exists to avoid). Caught via
`chunk_embeddings.bin`'s mtime predating `code.index`/`metadata.db`'s in the storage directory;
fixed by `cleanup_resources` → deleting the stale cache file → a genuine cold force-reindex
(57.44s, same 205 files/2331 chunks) before capturing anything.

| Capture | Substrate | MRR | Recall@5 | Recall@10 | pool_hit_rate |
|---|---|---|---|---|---|
| `canon_l0_63q_arm` (pre-upgrade, = `canon_k1` substrate) | 205 files / 2331 chunks | 0.8603 | 0.6795 | 0.7957 | 0.9048 |
| `canon_l1_63q_arm` (post Stage 3) | 205 files / 2331 chunks | 0.8603 | 0.6795 | 0.7957 | 0.9048 |

`--compare` reported **0 queries moved on every ranking metric**, all five paired 95% CIs exactly
`[+0.0000, +0.0000]` — byte-identical retrieval outcome to torch 2.10.0. **Gate passes trivially.**
The `--deterministic-gpu` strict-mode re-validation (`canon_l1_detgpu`) again completed with zero
`RuntimeError`s.

`canon_l1` becomes the final adopted canon, superseding `canon_k1`/`canon_k2` (which were captured
against the now-corrected-but-superseded torch 2.10.0 install). Because the two substrates are
retrieval-identical, none of the published benchmark figures in `docs/BENCHMARKS.md` or `CLAUDE.md`
change — only the canon name citation does.

## Consequences

- `pyproject.toml`: `torch>=2.11.0,<2.12.0` (Stage 3 correction, superseding Stage 2's
  `>=2.10.0,<2.11.0`), `transformers>=5.14.1,<6`, `sentence-transformers>=5.7.0`,
  `faiss-cpu>=1.15.0`, `huggingface-hub>=1.26.1`.
- `uv.lock` re-pinned via `uv lock --upgrade-package torch --upgrade-package setuptools` (never
  `uv sync`) — `uv lock --check` passes. Resolved `setuptools` (`81.0.0`) and three
  CUDA-ecosystem packages (`cuda-toolkit`, `nvidia-cudnn-cu12`, `nvidia-nccl-cu12`) diverge from
  what `pip freeze` shows actually installed (`setuptools 78.1.0`, no separate `nvidia-*`
  packages) — investigated and judged a benign, Windows-specific resolution-graph artifact:
  Windows torch wheels bundle the CUDA runtime directly rather than via separate `nvidia-*` pip
  packages the way Linux wheels do, and `uv lock --check` only verifies internal resolution
  consistency, not `pip freeze` parity. `pip check` stays clean.
- Editable-install metadata refreshed (`pip install -e . --no-deps`) so `pip check` reads the new
  pins rather than stale dist-info from the previous install — without this, `pip check` reports
  a phantom stale-ceiling conflict even though the installed torch and the `pyproject.toml` pin
  agree.
- `docs/PYTORCH_COMPATIBILITY.md` rewritten twice this campaign: first for the Stage 2 ceiling
  change and corrected `CVE-2025-3001` characterization, then again for Stage 3's `<2.12.0`
  ceiling, the corrected `CVE-2026-4538` status, the pip-audit-OSV-lookup-gap standing rule, and
  the `setuptools<82` side effect. `docs/INSTALLATION_GUIDE.md` and `README.md` version strings
  updated to match both times.
- Torch CVE ledger: 8 tracked → **1 remaining** (`CVE-2025-3000`, fixed in `2.13.0` which the
  pinned `cu128` index does not publish — reopening condition is "re-check each cycle whether the
  index has started publishing `>=2.13.0`"). `CVE-2026-4538` is closed as of `2.11.0`, correcting
  the Stage 2 ledger above which wrongly counted it as unfixable.
- `canon_l1`'s intent-on arm (byte-identical to `canon_k1`/`canon_k2`) is the final adopted
  reference point, captured as the full four-view set (63q/133q control+arm, F-via-similar) per
  the campaign's final-canon step — supersedes `canon_k1`/`canon_k2` citations throughout.

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
