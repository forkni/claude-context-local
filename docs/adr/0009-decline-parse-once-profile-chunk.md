# Decline parse-once tree reuse between the profile and chunk passes

Status: accepted
Date: 2026-07-20

We evaluated reusing tree-sitter trees parsed during the profile pass
(`chunking/repo_profiler.py`) in the subsequent chunk pass
(`search/parallel_chunker.py`), instead of each pass independently
tree-sitter-parsing every file. We decided not to build this ("Candidate B",
the deferred follow-up to the `ParsedSource` seam introduced in the same
change — see `CONTEXT.md`'s `ParsedSource` entry).

## Context

`IncrementalIndexer._full_index` runs two passes when `sizing_mode ==
"adaptive"` (this project's setting, `search_config.json`): pass 1 profiles
the whole repo serially on the main thread to compute a global `RepoProfile`
(P75/P90 function size, max cyclomatic complexity) before any file can be
chunked; pass 2 chunks every file in parallel across a `ThreadPoolExecutor`.
Both passes independently call `TreeSitterChunker.parse_file()` on every
file — a real double-parse, not hypothetical.

Two hard constraints stand in the way of literally carrying pass-1's trees
into pass 2:

- **Global-ordering barrier.** The adaptive threshold needs the whole-repo
  profile before any file is chunked, so passes can't interleave per file —
  reusing a tree means holding *all* trees in memory between passes, an
  unbounded memory profile that doesn't exist today.
- **Thread affinity.** `ParsedSource.tree` is only valid on the thread that
  produced it (tree-sitter `Tree`/`Node` objects aren't thread-safe; the
  parser cache is `threading.local`). Pass 1 produces trees on the main
  thread; pass 2 would need to consume them from worker threads —  a direct
  invariant violation, not a peculiarity of this codebase.

Given those costs, the question was whether the payoff was even worth
resolving them for, so we measured before designing anything
(`scripts/benchmark/measure_parse_once.py`, driving the real
`profile_repository` / `ParallelChunker.chunk_files` / `TreeSitterChunker.
parse_file` code paths, no reimplementation).

## Decision

Do not implement parse-once, and do not parallelize the profile pass either.
Leave the double-parse as-is.

## Reasons

**t_profile stays under 1 second regardless of repo size or complexity.**
Measured on two repos:

| Repo | Supported files | t_profile | t_chunk | ceiling = t_profile/(t_profile+t_chunk) |
|---|---|---|---|---|
| claude-context-local (this repo) | 193 | 0.44s | 3.42s | 11.4% |
| SDTD_032_dev (larger, more complex) | 353 | 1.00s | 8.95s | 10.0% |

SDTD_032_dev has ~1.8x the files, ~2.7x the functions, and ~2x the max
cyclomatic complexity of this repo, yet the ceiling ratio *held steady*
(10.0% vs 11.4%) rather than growing — the profile pass scales in lockstep
with chunking, not faster. There is no evidence it becomes a bottleneck at
any realistic repo size.

**The ceiling ratio overstates the real-world impact.** 10-11% is a
percentage of the profile+chunk *subtotal*, not of full-index wall time.
On this repo's own 94s full reindex log, embedding (~35s) and call-graph
resolvers (pyan/libcst/LSP, ~43s combined) dominate — ~80s of 94s. Even
fully eliminating the profile pass saves under 1% of total index time.

**Parallelizing just the profile pass isn't worth it either.** The
decision rule considered this as a cheaper alternative if the *serial*
profile wall time were itself a large absolute chunk. It isn't — under 1
second on both tested repos — so there's nothing meaningful to parallelize
away.

## Considered Options

- **Full parse-once (sharded two-phase worker model, hold all trees)** —
  rejected; unbounded memory cost and a thread-affinity rewrite for <1%
  total-time savings.
- **Parallelize only the profile pass** (keep the double-parse, just make
  pass 1 concurrent) — rejected; the serial pass is already under 1 second,
  nothing to reclaim.
- **Drop it, keep both passes as-is** — accepted.

## Consequences

`chunking/repo_profiler.py` and `search/parallel_chunker.py` are unchanged.
`scripts/benchmark/measure_parse_once.py` remains in the repo as a reusable,
non-invasive harness (drives real code paths, makes no production changes)
in case a future repo profile or config change makes this worth
re-measuring — re-run it rather than re-deriving these numbers from scratch.
