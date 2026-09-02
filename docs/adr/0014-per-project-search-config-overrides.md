# Per-project search config overrides via search_overrides.json

Status: accepted
Date: 2026-07-29

Each indexed project may carry a `search_overrides.json` in its storage
directory (sibling of `project_info.json`). Its `overrides` section is
deep-merged over the global `search_config.json` when that project is
active, with precedence **env > per-project overrides > global file >
dataclass defaults**. The file is written by an auto-tuning probe during
full reindex (see Consequences) but is equally valid hand-edited.

## Context

The search config was a single global file: `search/config_paths.py`
resolves repo-root `search_config.json` (fallback:
`~/.claude_code_search/search_config.json`), and `handle_switch_project`
only changed the storage directory. One config governed every indexed
project, so any hardware- or corpus-specific tuning (chunking worker
count, reranker enable, GLSL prefix filtering) either leaked into
the global file — wrong for every other project — or was lost.

At the same time, accumulated benchmark experience on this repo
(ADR-0011 through ADR-0013, the 77/96-query golden sets) produced a body
of "safe to derive from hardware and corpus shape" knobs *and* a body of
"never touch without a golden dataset" knobs. A tuning mechanism needed a
place to write per-project values without contaminating the global
baseline.

Alternatives considered:

- **Per-project full config files** (a complete `search_config.json`
  copy per project): rejected — full copies go stale the moment the
  global baseline moves, and diffing "what was tuned here" becomes
  archaeology. A sparse overlay keeps the delta explicit.
- **Auto-editing the global file in place**: rejected — destroys the
  hardware-neutral baseline semantics of `search_config.json.example`
  (which `load_config()` reads as the live fallback for fresh installs)
  and makes multi-project switching order-dependent.
- **A DI-style config service**: rejected per
  [ADR-0005](0005-no-di-container-module-singleton-state.md) — the
  active-project seam is a module-level singleton
  (`set_active_project_storage_dir()` /
  `get_active_project_storage_dir()` in `search/config.py`), informed by
  the MCP handlers without a reverse import.

## Decision

### File and schema

`<project_storage_dir>/search_overrides.json`:

```json
{
  "probe_version": "1",
  "generated_at": "<iso8601 UTC>",
  "overrides": {"performance": {"max_chunking_workers": 12}},
  "reasons": {"performance.max_chunking_workers": "cpu_count=24, files=233 -> 12"},
  "observations": [{"key": "chunking.community_resolution", "note": "..."}]
}
```

`reasons` keys match the dotted `overrides` keys 1:1 (unit-enforced);
`observations` are report-only notes that never duplicate an override
key. Only the `overrides` section affects behaviour.

### Merge point and precedence

The merge lives in `search/config.py:load_config`, inserted between the
global-file load and the env-var merge, reusing `_deep_merge` verbatim.
Env stays on top as the explicit human-in-the-loop escape. The override
file's mtime is folded into the hot-reload check
(`max(global_mtime, override_mtime)`), so hand-edits apply without a
server restart. A malformed override file warns and is skipped,
mirroring the malformed-global-config recovery.

### Escape hatches

Two, checked in order: the `CLAUDE_DISABLE_PROJECT_OVERRIDES` env var
(truthy values: `true/1/yes/on/enabled`) and
`PerformanceConfig.enable_project_overrides` (default `True`). Both gate
the read-side merge *and* the probe's writes — disabling produces no
file at all, not a file that is silently ignored.

### Index-affecting vs search-time-only keys

Index-affecting keys (all of `chunking.*`, `search_mode.bm25_tokenizer`,
the `embedding.*` context/cache flags, `performance.
enable_entity_tracking`, `call_graph.*`) may only be probed/applied
before chunking starts (probe pass 1); search-time-only keys (reranker,
multi_hop, ego_graph, fusion, etc.) are safe any time. One documented
nuance: `performance.max_chunking_workers` /
`enable_parallel_chunking` are bound to indexer instance attributes at
construction, so a pass-1 override of those takes effect on the *next*
reindex — acceptable because hardware is stable between runs.

### Status surfacing

`get_search_config_status` reports `project_overrides_active`, `_path`,
`_probe_version`, `_generated_at`, and the dotted `_keys`, so "why is
this project behaving differently" is answerable from the MCP surface.

## Consequences

- Per-project tuning no longer contaminates the global config; the
  global file and its `.example` stay a validated, hardware-neutral
  baseline.
- **Auto-tuning probe** (`search/index_probe.py`, `PROBE_VERSION = "1"`):
  a full reindex runs a two-pass probe — pass 1 (pre-chunking) measures
  VRAM/CPU/corpus shape and *auto-applies* safe hardware/structural
  knobs (batch sizes, worker count, reranker enable, GLSL
  prefix filter), rewriting the file wholesale with fresh provenance;
  pass 2 (post-build) appends *report-only observations* from
  `stats.json` (community resolution, split share, ego density).
  Retrieval-quality knobs are never auto-applied — no golden dataset
  exists on arbitrary projects — and a static unit test pins the
  forbidden set. See `search/index_probe.py`'s `FORBIDDEN_AUTO_TUNE_KEYS`
  frozenset for the current, live membership — this list has grown since
  and previously named `enable_community_merge`, deleted by ADR-0020; do
  not hand-copy it here again (see ADR-0042 for why). Probe failures are
  isolated: they warn and never break indexing.
  Incremental reindexes never re-probe; the existing file keeps
  applying untouched.
- A full reindex overwrites hand-edits to the `overrides` section
  (documented limitation — the wholesale rewrite is what keeps
  provenance honest). Durable manual tuning belongs in the global file
  or env vars, which outrank the probe.
- The active-project seam means CLI/test paths that never call the
  setter simply skip both the merge and the probe — consistent, since
  neither side would apply without the other.
- Open item: the local config's `parent_retrieval.enabled: true` is an
  undocumented deviation from the example's `false`; it predates this
  ADR and remains unresolved here.
