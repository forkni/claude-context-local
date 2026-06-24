# DSPy with Claude Code Subscription

DSPy is integrated via a custom `ClaudeCodeLM` backend that routes all
completions through the `claude` CLI instead of the Anthropic HTTP API.
This means DSPy jobs are billed to your **Claude Code Max plan** — no
`ANTHROPIC_API_KEY`, no API credits required.

## Why not just set `ANTHROPIC_API_KEY`?

Setting `ANTHROPIC_API_KEY` globally **disables subscription auth** in
Claude Code itself.  The API key outranks the Max OAuth token in Claude Code's
auth precedence, so every request — including the IDE session — would be
charged to your API account.  Keep that variable unset.

## Quick start

```python
import dspy
from utils.dspy_claude_code import configure_dspy

configure_dspy()                      # routes DSPy through the subscription
pred = dspy.Predict("question -> answer")
print(pred(question="capital of France").answer)
```

`configure_dspy()` calls `dspy.configure(lm=...)` globally, so subsequent
`dspy.Predict` / `dspy.ChainOfThought` / optimizer calls all use the same LM.

## Headless / unattended runs

The `claude` CLI authenticates via the active Claude Code login.  For
unattended jobs (CI, long optimizer runs) that outlive the interactive
session, mint a long-lived token first:

```bash
claude setup-token
```

Store the printed token in your `.env` file (copy `env.example → .env`):

```
CLAUDE_CODE_OAUTH_TOKEN=<token>
```

`configure_dspy()` loads `.env` automatically via `python-dotenv`.

## Model override

```python
configure_dspy(model="claude-opus-4-8")   # use a specific model
# or via env:
# DSPY_LM_MODEL=claude-opus-4-8
```

## Direct use without `configure_dspy`

```python
from utils.dspy_claude_code import ClaudeCodeLM
import dspy

lm = ClaudeCodeLM(model="claude-sonnet-4-6", max_tokens=2048, timeout=60)
dspy.configure(lm=lm)
```

## Optimizer concurrency

Each DSPy `forward()` call spawns one `claude -p` subprocess (~1–3 s cold
start).  Cap parallel workers when running optimizers:

```python
import dspy

teleprompter = dspy.BootstrapFewShot(max_bootstrapped_demos=4)
# For MIPRO / BootstrapFewShotWithRandomSearch that expose num_threads:
compiled = teleprompter.compile(
    student, trainset=trainset, num_threads=5   # ≤ 10 recommended
)
```

Exceeding ~10 concurrent subprocesses risks hitting Claude Code session limits.

## Long-running jobs

For optimizer runs that take many minutes, set the watchdog env var so
Claude Code auto-restarts stalled sessions:

```bash
CLAUDE_CODE_RETRY_WATCHDOG=1 python my_optimizer.py
```

## SDK alternative

The subprocess approach (used here) is equivalent in throughput to the
`claude-agent-sdk` package (the SDK also spawns a subprocess per call).
To switch to the SDK path, install `claude-agent-sdk` and subclass
`ClaudeCodeLM`, replacing `_call_claude` with an SDK invocation.  The
subscription guard (stripping `ANTHROPIC_API_KEY`) applies either way.

## Agent over MCP tools (ReAct + code-search)

`utils/dspy_mcp.py` wires a `dspy.ReAct` agent to the project's `code-search`
MCP server over **StreamableHTTP**.  Each ReAct step is one `claude -p` call;
the agent issues `search_code` / `find_connections` calls against the
**already-running, warm** server, producing a grounded answer from the actual
codebase index — no second subprocess, no cold model load.

### Prerequisites

1. **The code-search HTTP server must be running on port 8765.**  Start it
   with `start_mcp_http.bat` if needed, then verify:
   ```bash
   curl http://localhost:8765/mcp   # should return MCP protocol response
   ```
   Or in Claude Code: `/mcp` → `code-search:list_projects`.
2. The target project must already be indexed (see `index_directory` tool).
3. No `ANTHROPIC_API_KEY` set — see above.
4. Active Claude Code login (`claude whoami`).

### Quick start

```python
import asyncio
from utils.dspy_mcp import run_code_search_agent

result = asyncio.run(
    run_code_search_agent(
        "Where is the FAISS vector index class defined?",
        project_path="D:/claude-context-local",   # must already be indexed
    )
)
print(result.answer)
```

`run_code_search_agent` connects to the warm HTTP server, calls
`switch_project` to activate the correct index (switch & leave — the server
stays on the requested project after the call returns), then runs the ReAct
loop.

### Shared session seam (`code_search_session`)

For multi-query workloads (e.g. the evaluation runner), open **one** session
shared across all queries to avoid repeated connection setup:

```python
import asyncio
import dspy
from utils.dspy_mcp import code_search_session
from utils.dspy_claude_code import ClaudeCodeLM

async def batch_query(questions):
    lm = ClaudeCodeLM()
    async with code_search_session(project_path="D:/claude-context-local") as (_, tools):
        agent = dspy.ReAct("question -> answer", tools=tools)
        results = []
        for q in questions:
            with dspy.context(lm=lm):
                results.append(await agent.acall(question=q))
    return results
```

All calls in a batch must stay on **one event loop** that owns the session.
Do not pass the session or tools to another thread or a separate event loop.

### Runnable demo

```bash
.venv/Scripts/python.exe scripts/dspy_mcp_demo.py
# custom question:
.venv/Scripts/python.exe scripts/dspy_mcp_demo.py "How does hybrid search work?"
```

### Latency

- Warm server (model already loaded): **no cold-start delay**.
- Each `claude -p` ReAct step: **3–10 s**.
- A typical 3-step query: **~15–40 s** total.
- First call after server startup still incurs model load (~8–15 s);
  the 45 s per-tool timeout accommodates this.

### Design notes

- Tools are exposed with `--tools ""` so the CLI's own Bash/Edit/etc. tools
  are disabled; DSPy drives the tool-use loop entirely via its text-based
  ReAct adapter.
- Only read-only tools (`search_code`, `find_connections`) are exposed by
  default; index-mutating or config tools are never passed to the agent.
- Each tool call is wrapped in `asyncio.wait_for(timeout=45s)` so a stalled
  tool returns an observation string instead of hanging the entire agent run.
- The async path (`ReAct.aforward`) is required because the MCP
  `ClientSession.call_tool` is a coroutine.  `ClaudeCodeLM.aforward` runs
  the blocking `claude -p` subprocess via `asyncio.to_thread`, keeping the
  event loop free.
- `dspy.context(lm=lm)` is used (not `dspy.configure`) — it uses Python
  contextvars so it is async-task-safe: multiple concurrent tasks can each
  hold their own LM reference without interference.

## GEPA prompt optimisation

`dspy.GEPA` (Genetic-Pareto reflective prompt evolution) can automatically improve
the `CodeNavQA` signature instructions to close the agent-judgment recall gap.

### When to use it

The standard eval harness (`run_dspy_eval.py`) measures a *tool ceiling* — how
many expected chunks the tools surfaced — versus what the agent actually returned.
When the gap (ceiling − agent recall) is > 0.1 it is worth running GEPA to
discover a better instruction.

### Prerequisites

Same as the agent eval (server running, project indexed, no `ANTHROPIC_API_KEY`).
Additionally:

- Set `CLAUDE_CODE_OAUTH_TOKEN` for unattended auth (GEPA runs are long — minutes
  to ~1 h for `auto="light"`).
- Set `CLAUDE_CODE_RETRY_WATCHDOG=1` to auto-retry on `claude` CLI transient errors.

### Quick start

```powershell
# Light budget (~6 candidate evaluations, good first run):
.venv/Scripts/python.exe scripts/benchmark/run_dspy_gepa.py `
    --project-path D:/claude-context-local

# Medium budget (12 candidates):
.venv/Scripts/python.exe scripts/benchmark/run_dspy_gepa.py `
    --project-path D:/claude-context-local --budget medium
```

### Key parameters

| Flag | Default | Notes |
|---|---|---|
| `--budget` | `light` | `light`=6 / `medium`=12 / `heavy`=18 candidates |
| `--reflection-model` | `claude-opus-4-8` | Stronger model for instruction proposals |
| `--model` | `claude-sonnet-4-6` | Rollout model (agent invocations) |
| `--num-threads` | `4` | Keep ≤ 4; MCP I/O is serialised on the single session |

### Billing

Both rollout and reflection LMs use `ClaudeCodeLM` (subscription billing).
No `ANTHROPIC_API_KEY` required or desired.

### Async→sync bridge

`dspy.GEPA.compile()` is synchronous and thread-parallel; the MCP `ClientSession`
is bound to one asyncio event loop.  `evaluation/dspy_gepa_optimize.gepa_tool_bridge`
solves this by running the event loop on a daemon thread, entering the session there,
and exposing sync wrappers that marshal calls via `asyncio.run_coroutine_threadsafe`.
A `threading.Lock` serialises tool I/O; LM calls still run in parallel.

### Artifacts

Written to gitignored `results/gepa/`:

- `optimized_codenavqa_<ts>.json` — the saved `dspy.load()`-able program.
- `gepa_stats_<ts>.json` — seed score, best score, evolved instruction text.
- `latest_summary.json` — same summary, always at a stable path.

### After the run

1. Read the printed "Discovered instruction".
2. If `best_score > seed_score`: manually port the text into `CodeNavQA` in
   `evaluation/dspy_agent_eval.py` (docstring + `relevant_chunk_ids` desc).
3. Re-run `run_dspy_eval.py` to confirm the lift.
4. Commit: `feat: adopt GEPA-discovered CodeNavQA instruction (Recall@7 X→Y)`.

### In-sample caveat

The golden dataset has only 13 queries.  GEPA uses `trainset = valset = all 13`
(in-sample prompt discovery).  The discovered instruction is plausibly better but
overfits the dataset.  True generalisation requires a larger dataset (deferred work).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `RuntimeError: claude CLI not found` | Install Claude Code or set `CLAUDE_CLI_PATH=/path/to/claude` |
| Responses are slow | Normal — each call is a subprocess.  Use small `n` values. |
| `RuntimeError: claude CLI exited with code 1` | Check `~/.claude/` login state: run `claude --version` |
| DSPy cache hits route to the API | `ClaudeCodeLM` uses `BaseLM` which bypasses the disk cache — should not happen |
