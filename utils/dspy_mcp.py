"""DSPy ReAct agent that queries the code-search MCP server over HTTP.

Connects to the **already-running** ``mcp_server.server`` via StreamableHTTP
(no subprocess spawn), wraps its tools via ``dspy.Tool.from_mcp_tool``, and
drives a ``dspy.ReAct`` reasoning loop billed to the Claude Code Max
subscription (no ``ANTHROPIC_API_KEY``).

The :func:`code_search_session` async context manager is the shared seam: it
opens one session to the warm server and yields ``(session, dspy_tools)`` for
any number of agent calls — used by both the single-query demo and the
multi-query evaluation runner.

Usage::

    import asyncio
    from utils.dspy_mcp import run_code_search_agent

    result = asyncio.run(
        run_code_search_agent(
            "Where is the FAISS vector index class defined?",
            project_path="D:/claude-context-local",
        )
    )
    print(result.answer)

Prerequisites:
    - The code-search HTTP server is **already running** on port 8765.
      Start it with ``start_mcp_http.bat`` if needed.
    - The target project must already be indexed.
    - No ``ANTHROPIC_API_KEY`` in env (would override subscription OAuth).
    - Active Claude Code login (``claude whoami``).

See ``docs/DSPY_SETUP.md`` for setup, latency expectations, and optimizer
guidance.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import dspy
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from utils.dspy_claude_code import ClaudeCodeLM


logger = logging.getLogger(__name__)

# Project root is the directory containing utils/
_PROJECT_ROOT = str(Path(__file__).parent.parent)

# Default URL for the already-running code-search HTTP server.
# The server.py arg-parse default port is 8000, but the standard launcher
# (start_mcp_http.bat) starts it on 8765.  The URL must include /mcp.
# Override via CODE_SEARCH_MCP_URL env var.
_DEFAULT_SERVER_URL = os.getenv("CODE_SEARCH_MCP_URL", "http://localhost:8765/mcp")


async def _switch_project(session: ClientSession, project_path: str) -> None:
    """Switch the MCP server's active project to ``project_path``.

    Calls the ``switch_project`` MCP tool (required arg: ``project_path`` as
    an absolute path; handler validates existence and indexing state).  The
    server is left on the requested project — **switch & leave**.

    Args:
        session: An initialized :class:`mcp.ClientSession`.
        project_path: Absolute path to the already-indexed project directory.

    Raises:
        RuntimeError: If the server returns an error (e.g. path not indexed).
    """
    result = await session.call_tool("switch_project", {"project_path": project_path})
    # MCP content[0] can be TextContent | ImageContent | AudioContent | EmbeddedResource;
    # only TextContent carries .text — use getattr to satisfy the type checker.
    text = getattr(result.content[0], "text", "{}") if result.content else "{}"
    payload = json.loads(text)
    if "error" in payload:
        raise RuntimeError(
            f"switch_project failed for {project_path!r}: {payload['error']}"
        )
    logger.info(
        "Switched to project: %s (indexed=%s)",
        payload.get("project", project_path),
        payload.get("indexed"),
    )


def _with_timeout(tool: Any, timeout_s: float) -> Any:
    """Wrap a dspy.Tool's async func to enforce a per-call timeout.

    On timeout or unexpected exception the wrapped func returns an observation
    string instead of raising, so a slow tool degrades gracefully to an
    observation in the ReAct loop rather than crashing the agent.

    The warmup call in :func:`code_search_session` ensures bge-m3 is resident
    before timed concurrent calls; ``timeout_s=120.0`` is a defense-in-depth
    backstop for any genuine first cold load.

    Args:
        tool: A ``dspy.Tool`` instance.  **Mutated in place**: ``tool.func`` is
            replaced with the timeout wrapper.
        timeout_s: Maximum seconds to wait for a single tool call.

    Returns:
        The same ``tool`` object with its ``func`` replaced.
    """
    original_func = tool.func
    tool_name = tool.name

    async def _timed_func(**kwargs: Any) -> Any:
        try:
            return await asyncio.wait_for(
                original_func(**kwargs),
                timeout=timeout_s,
            )
        except TimeoutError:
            msg = f"Execution error in {tool_name}: timeout after {timeout_s:.0f}s"
            logger.warning("Tool %r timed out after %.0fs", tool_name, timeout_s)
            return msg
        except Exception as exc:  # noqa: BLE001
            msg = f"Execution error in {tool_name}: {exc}"
            logger.warning("Tool %r raised %r", tool_name, exc)
            return msg

    tool.func = _timed_func
    return tool


def _with_no_reindex(tool: Any) -> Any:
    """Wrap a search_code tool to always inject ``auto_reindex=False``.

    Eval and GEPA harnesses read a frozen index and must never trigger an
    age-based reindex.  Without this, any ``search_code`` call against an index
    older than ``max_age_minutes`` (default 5) causes a full embedder teardown
    (``state.clear_embedders`` + ``reset_pool_manager`` + ``embedder.cleanup``),
    forcing a cold bge-m3 reload under the HF per-blob filelock.  Under GEPA's
    concurrent rollouts each abandoned call re-triggers the teardown, producing
    the "5+ distinct FileLock objects on one blob" stall.

    For non-search_code tools this wrapper is a no-op pass-through.

    Args:
        tool: A ``dspy.Tool`` instance.  **Mutated in place**: ``tool.func`` is
            replaced with the no-reindex wrapper.

    Returns:
        The same ``tool`` object with its ``func`` replaced.
    """
    original_func = tool.func
    tool_name = tool.name

    async def _no_reindex_func(**kwargs: Any) -> Any:
        if tool_name == "search_code":
            kwargs["auto_reindex"] = False
        return await original_func(**kwargs)

    tool.func = _no_reindex_func
    return tool


@asynccontextmanager
async def code_search_session(
    *,
    project_path: str,
    server_url: str = _DEFAULT_SERVER_URL,
    tool_names: tuple[str, ...] = ("search_code", "find_connections"),
    tool_timeout_s: float = 120.0,
):
    """Async context manager: open a session to the warm code-search HTTP server.

    Connects to the already-running server, switches the active project
    (switch & leave), issues a single warmup ``search_code`` call to ensure
    bge-m3 is resident before concurrent timed calls, and yields
    ``(session, dspy_tools)`` — a live :class:`mcp.ClientSession` and a list
    of ``dspy.Tool`` wrappers with per-call timeouts and ``auto_reindex=False``
    applied.

    This is the shared seam that both the single-query demo and the
    multi-query evaluation runner plug into.  Keep all agent calls inside
    **one** event loop that owns this session — do not pass the session or tools
    to another thread or a separate event loop.

    Usage::

        async with code_search_session(project_path="/my/project") as (_, tools):
            agent = dspy.ReAct("question -> answer", tools=tools)
            with dspy.context(lm=lm):
                result = await agent.acall(question="…")

    Args:
        project_path: Absolute path to the already-indexed project directory.
        server_url: Full URL of the MCP HTTP endpoint (must include ``/mcp``).
            Default: ``http://localhost:8765/mcp`` (or ``CODE_SEARCH_MCP_URL``).
        tool_names: MCP tool names to expose.  Keep to read-only search tools.
        tool_timeout_s: Per-call timeout for each tool invocation (seconds).

    Yields:
        ``(session, dspy_tools)`` tuple.

    Raises:
        RuntimeError: If the server is unreachable, the project path cannot be
            switched, or requested tool names are not exposed by the server.
    """
    try:
        async with streamablehttp_client(server_url) as (read, write, _):  # noqa: SIM117
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.debug("MCP HTTP session initialized at %s", server_url)

                await _switch_project(session, project_path)

                tools_response = await session.list_tools()
                all_tools = {t.name: t for t in tools_response.tools}

                missing = [n for n in tool_names if n not in all_tools]
                if missing:
                    raise RuntimeError(
                        f"MCP server does not expose requested tool(s): {missing}. "
                        f"Available: {sorted(all_tools)}"
                    )

                dspy_tools = [
                    _with_no_reindex(
                        _with_timeout(
                            dspy.Tool.from_mcp_tool(session, all_tools[name]),
                            tool_timeout_s,
                        )
                    )
                    for name in tool_names
                ]
                logger.info(
                    "Wrapped %d MCP tools for DSPy: %s",
                    len(dspy_tools),
                    [t.name for t in dspy_tools],
                )

                # Warm bge-m3 once, single-threaded, before concurrent timed
                # rollouts.  A genuine post-restart cold load of the 2.27 GB
                # model can take 60–120 s; warming here ensures all subsequent
                # calls hit the resident fast-path.
                logger.info(
                    "Warming up embedding model (single-threaded, up to 180 s)…"
                )
                try:
                    await asyncio.wait_for(
                        session.call_tool(
                            "search_code",
                            {"query": "warmup", "k": 1, "auto_reindex": False},
                        ),
                        timeout=180.0,
                    )
                    logger.info("Embedding model warm.")
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Warmup call failed or timed out: %r — continuing anyway", exc
                    )

                yield session, dspy_tools

    except (ConnectionError, OSError) as exc:
        raise RuntimeError(
            f"Cannot reach code-search HTTP server at {server_url}. "
            f"Start it (start_mcp_http.bat) — this bridge connects to the "
            f"existing server, it does not spawn one."
        ) from exc


async def run_code_search_agent(
    question: str,
    *,
    project_path: str,
    server_url: str = _DEFAULT_SERVER_URL,
    tool_names: tuple[str, ...] = ("search_code", "find_connections"),
    tool_timeout_s: float = 120.0,
    max_iters: int = 6,
    model: str | None = None,
    **lm_kwargs: Any,
) -> dspy.Prediction:
    """Run a DSPy ReAct agent that uses the code-search MCP tools.

    Connects to the **already-running** code-search HTTP server (does not
    spawn a new process), switches the active project (switch & leave),
    converts the requested MCP tools to ``dspy.Tool`` wrappers with per-call
    timeouts, and drives a ``dspy.ReAct`` loop.

    Each ReAct step costs one ``claude -p`` invocation (~3–10 s) plus one MCP
    tool round-trip to the warm server (no cold model load on repeat calls).

    Args:
        question: Natural-language question for the agent to answer.
        project_path: Absolute path to the indexed project directory.
        server_url: Full URL of the MCP HTTP endpoint including ``/mcp``.
            Defaults to ``http://localhost:8765/mcp`` (or ``CODE_SEARCH_MCP_URL``
            env var).
        tool_names: Which MCP tools to expose to the agent.  Defaults to the
            read-only search pair.  Do **not** include mutating tools.
        tool_timeout_s: Per-tool call timeout in seconds.
        max_iters: Maximum ReAct iterations.  Keep ≤ 6–8 to bound cost.
        model: Claude model ID.  Falls back to ``DSPY_LM_MODEL`` env var then
            ``"claude-sonnet-4-6"``.
        **lm_kwargs: Extra kwargs forwarded to
            :class:`~utils.dspy_claude_code.ClaudeCodeLM`.

    Returns:
        A ``dspy.Prediction`` with at least an ``answer`` field plus a
        ``trajectory`` dict showing the chain-of-thought and tool calls.

    Raises:
        RuntimeError: If the HTTP server is unreachable or the project is not
            indexed.  Start the server with ``start_mcp_http.bat`` first.
    """
    async with code_search_session(
        project_path=project_path,
        server_url=server_url,
        tool_names=tool_names,
        tool_timeout_s=tool_timeout_s,
    ) as (_, dspy_tools):
        lm = ClaudeCodeLM(model=model, **lm_kwargs)
        logger.info("DSPy LM: model=%s", lm.model)

        agent = dspy.ReAct(
            "question -> answer",  # pyrefly: ignore[bad-argument-type]  # DSPy stub too strict; string signature is valid at runtime
            tools=dspy_tools,
            max_iters=max_iters,
        )

        # dspy.context() is async-task-safe (uses contextvars under the hood),
        # unlike dspy.configure() which writes to a global non-task-local store.
        logger.info("Running ReAct agent (max_iters=%d): %r", max_iters, question)
        with dspy.context(lm=lm):
            result = await agent.acall(question=question)
        logger.info("Agent finished. answer=%r", getattr(result, "answer", None))
        return result
