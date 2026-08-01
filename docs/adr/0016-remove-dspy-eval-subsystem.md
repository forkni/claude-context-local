# Remove the DSPy eval subsystem

Status: accepted
Date: 2026-08-01

## Context

`evaluation/dspy_agent_eval.py` and its supporting modules (`dspy_gepa_optimize.py`,
`utils/dspy_mcp.py`, `utils/dspy_claude_code.py`, the `run_dspy_eval.py` /
`run_dspy_gepa.py` CLI entry points, `scripts/dspy_mcp_demo.py`) implement a DSPy
ReAct-agent harness that drives the code-search MCP tools over a live HTTP server and
measures tool-selection/trajectory-recall accuracy, plus a GEPA (Genetic-Pareto)
prompt optimizer that evolves the harness's own signature instructions against the
golden dataset. Both are gated behind the `[eval]` optional-dependency extra
(`dspy>=3.2.1`) and were never imported by `mcp_server/` or `search/` — `find_connections`
confirms `run_code_search_agent`'s only caller is `scripts/dspy_mcp_demo.py:main`, and
`utils/dspy_mcp.py` is the *only* consumer anywhere in the repo of the `mcp` package's
**client** API (`ClientSession`, `streamablehttp_client`); every other `mcp` usage is
server-side in `mcp_server/`.

The subsystem produced real, useful measurements (Recall@7=0.9046, MRR=0.8519 on the
77-query golden set, 4-tool harness) that are already recorded in
`.claude/skills/mcp-search-tool/SKILL.md` and `references/performance.md` as historical
citations — the harness itself is no longer needed to keep those numbers meaningful.
Maintaining it costs: a second, heavier eval path alongside `evaluation/metrics.py` +
`scripts/benchmark/run_mcp_pipeline_eval.py` (which cover the same MRR/Recall/NDCG
ground without a DSPy/Claude-Code-subscription dependency); a `dspy` entry in the
pyrefly `replace-imports-with-any` stub-ignore list; and — the immediate trigger for
this ADR — the last non-`mcp_server` consumer of the `mcp` client API, which would
otherwise need its own review during the MCP SDK v1→v2 migration (`ADR-0017`).

## Decision

Delete the DSPy eval subsystem outright: 13 files, 4,849 lines
(`evaluation/dspy_agent_eval.py`, `evaluation/dspy_gepa_optimize.py`,
`utils/dspy_claude_code.py`, `utils/dspy_mcp.py`, `scripts/benchmark/run_dspy_eval.py`,
`scripts/benchmark/run_dspy_gepa.py`, `scripts/dspy_mcp_demo.py`,
`tests/integration/test_dspy_eval_e2e.py`, `tests/unit/evaluation/test_dspy_agent_eval.py`,
`tests/unit/evaluation/test_dspy_gepa_optimize.py`, `tests/unit/utils/test_dspy_claude_code.py`,
`tests/unit/utils/test_dspy_mcp.py`, `docs/DSPY_SETUP.md`), plus the now-entirely-dead
`env.example` (its only content was DSPy/`CLAUDE_CODE_OAUTH_TOKEN` setup instructions).
Drop the `[project.optional-dependencies] eval` extra and the `dspy`/`gepa` pyrefly
stub-ignore entries from `pyproject.toml`.

## Reasons

**Zero production consumers.** `mcp_server/` and `search/` never import anything under
`evaluation/dspy_*` or `utils/dspy_*`. The subsystem is reachable only via its own CLI
entry points, which require a live HTTP server and an active Claude Code subscription
login (the integration test skips itself when either is absent).

**Redundant with the existing benchmark harness.** `scripts/benchmark/run_mcp_pipeline_eval.py`

+ `evaluation/metrics.py` already measure MRR/Recall/NDCG against the same golden
dataset without a DSPy or live-agent dependency, and are what CI-adjacent benchmarking
actually uses.

**Measurements are preserved, not lost.** The one number this subsystem uniquely
produced — full 4-tool agent performance, as opposed to searcher-only — is retained as
a dated, explicitly-historical citation in `SKILL.md` and `performance.md`, annotated
to point here.

**Simplifies the SDK v2 migration.** With this subsystem gone, `utils/dspy_mcp.py`'s
`ClientSession`/`streamablehttp_client` usage — the repo's only non-server consumer of
the `mcp` package — goes with it, so `ADR-0017`'s SDK v2 port touches exactly one file
(`mcp_server/server.py`) instead of two independent call sites with different API
surfaces (server handlers vs. client session).

## Considered Options

+ **Keep behind the `[eval]` extra, migrate to SDK v2 alongside `mcp_server/`** —
  rejected: doubles the v2 migration's surface area for a harness with no production
  consumer and a superseding benchmark path already in place.
+ **Archive under `_archive/`** — rejected: the repo has no precedent for a code
  graveyard, and the historical citations in `SKILL.md`/`performance.md` already serve
  the "don't lose the numbers" goal without carrying dead code.
+ **Delete outright** — accepted.

## Consequences

+ `uv sync --all-extras` no longer pulls `dspy>=3.2.1` and its transitive tree.
+ `evaluation/commit_mined_candidates.json` had 6 commit-mined candidate queries
  (H016, H017, I002, I047, I048, I049) pruned — their `intended` chunk IDs pointed at
  now-deleted DSPy symbols and could never be promoted to `golden_dataset_expanded.json`.
+ `.github/workflows/branch-protection.yml`'s `ALLOWED_DOCS` allowlist and the
  `[eval]`-extra explanatory comment in its pyrefly step, and `.gitignore`'s
  `docs/DSPY_SETUP.md` doc-tracking exception, are removed along with the deleted doc.
+ `scripts/benchmark/run_mcp_pipeline_eval.py`'s printed baseline comment drops its
  "0.8519 DSPy-agent" comparison figure (the file has no `dspy` import — cosmetic only).
+ Test count drops by the DSPy-specific unit/integration tests removed; no golden-set
  guard coverage is affected (`test_golden_set_guard.py` never referenced these files).
