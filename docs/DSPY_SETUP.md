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

## Troubleshooting

| Symptom | Fix |
|---|---|
| `RuntimeError: claude CLI not found` | Install Claude Code or set `CLAUDE_CLI_PATH=/path/to/claude` |
| Responses are slow | Normal — each call is a subprocess.  Use small `n` values. |
| `RuntimeError: claude CLI exited with code 1` | Check `~/.claude/` login state: run `claude --version` |
| DSPy cache hits route to the API | `ClaudeCodeLM` uses `BaseLM` which bypasses the disk cache — should not happen |
