"""DSPy LM backend that routes completions through the Claude Code subscription.

Drives the ``claude`` CLI in headless one-shot mode so DSPy jobs are billed
to the user's Claude Code Max plan — no ``ANTHROPIC_API_KEY`` required.

Usage::

    import dspy
    from utils.dspy_claude_code import configure_dspy

    configure_dspy()
    pred = dspy.Predict("question -> answer")
    print(pred(question="capital of France").answer)

See ``docs/DSPY_SETUP.md`` for caveats, token limits, and optimizer guidance.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from typing import Any

import dspy
from litellm import ModelResponse


logger = logging.getLogger(__name__)


class ClaudeCodeLM(dspy.BaseLM):
    """DSPy ``BaseLM`` subclass that dispatches to the ``claude`` CLI.

    Each ``forward()`` call spawns ``claude -p …`` as a subprocess and returns
    a ``litellm.ModelResponse`` so DSPy's pipeline machinery works unchanged.
    The subprocess environment strips ``ANTHROPIC_API_KEY`` /
    ``ANTHROPIC_AUTH_TOKEN`` to guarantee subscription billing, never API
    billing.

    Args:
        model: Claude model identifier, e.g. ``"claude-sonnet-4-6"``.
            Falls back to the ``DSPY_LM_MODEL`` env var, then
            ``"claude-sonnet-4-6"``.
        max_tokens: Token cap stored for forward-compatibility (not forwarded to the CLI).
        timeout: Per-call subprocess timeout in seconds (default 300 — the DSPy
            ReAct system prompt is long and the first call may take 60–120 s).
        **kwargs: Forwarded to ``dspy.BaseLM.__init__``.
    """

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int = 4096,
        timeout: int = 300,
        **kwargs: Any,
    ) -> None:
        resolved_model = model or os.getenv("DSPY_LM_MODEL", "claude-sonnet-4-6")
        super().__init__(model=resolved_model, **kwargs)
        self.max_tokens = max_tokens
        self.timeout = timeout

    # ------------------------------------------------------------------
    # DSPy protocol
    # ------------------------------------------------------------------

    def forward(
        self,
        prompt: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Run one DSPy completion via the ``claude`` CLI.

        Args:
            prompt: Raw prompt string (rarely used by DSPy internals).
            messages: OpenAI-style message list (DSPy always supplies this).
            **kwargs: DSPy-internal kwargs such as ``cache``, ``rollout_id``,
                ``n``, ``temperature``, ``max_tokens``.

        Returns:
            A ``litellm.ModelResponse`` whose ``choices`` carry the assistant
            reply text(s).
        """
        # Strip DSPy-internal kwargs that the CLI doesn't understand.
        kwargs.pop("cache", None)
        kwargs.pop("rollout_id", None)

        n: int = kwargs.pop("n", 1)
        # Pop DSPy kwargs the CLI doesn't understand (keep in sync with
        # DSPy's internal call sites to avoid unexpected forwarding).
        kwargs.pop("max_tokens", None)
        kwargs.pop("temperature", None)

        # Build user and system content from the message list.
        user_parts: list[str] = []
        system_parts: list[str] = []

        if messages:
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "system":
                    system_parts.append(content)
                else:
                    user_parts.append(content)
        elif prompt:
            user_parts.append(prompt)

        user_text = "\n".join(user_parts)
        system_text = "\n".join(system_parts) if system_parts else None

        texts: list[str] = []
        for _ in range(n):
            texts.append(self._call_claude(user_text, system_text))

        choices = [
            {
                "index": i,
                "message": {"role": "assistant", "content": t},
                "finish_reason": "stop",
            }
            for i, t in enumerate(texts)
        ]

        resp = ModelResponse(
            choices=choices,
            model=self.model,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
        resp._hidden_params = {"response_cost": 0.0}
        return resp

    async def aforward(
        self,
        prompt: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Async path: run the blocking ``claude`` subprocess off the event loop.

        Required by ``dspy.ReAct.aforward`` (and any async DSPy module that
        calls ``acall``). Delegates to the sync :meth:`forward` via
        :func:`asyncio.to_thread` so the running asyncio event loop — which
        owns the MCP ``ClientSession`` — is never blocked.

        Args:
            prompt: Raw prompt string.
            messages: OpenAI-style message list.
            **kwargs: Forwarded to :meth:`forward`.

        Returns:
            Same ``litellm.ModelResponse`` as :meth:`forward`.
        """
        return await asyncio.to_thread(
            self.forward, prompt=prompt, messages=messages, **kwargs
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(stdout: str) -> str:
        """Pull the final assistant text out of ``claude -p --output-format json``.

        The CLI's JSON shape varies by version; the final answer always lives
        in the ``result`` field of the ``type=="result"`` event:

        * CLI ≤ 2.0 (documented shape): single JSON object
          ``{"type": "result", "result": "<text>", ...}``
        * CLI 2.1.x (empirical): top-level JSON **array** of event objects
          ``[{"type": "system", ...}, {"type": "assistant", ...},
             {"type": "result", "subtype": "success", "result": "<text>", ...}]``

        A defensive fallback extracts text from the last ``assistant`` content
        block when no ``result`` entry is found, guarding against future format
        drift.

        Args:
            stdout: Raw stdout from the ``claude -p`` subprocess.

        Returns:
            The assistant reply string.

        Raises:
            json.JSONDecodeError: If ``stdout`` is not valid JSON.
            KeyError: If neither a ``result`` entry nor assistant text is found.
            TypeError: If the JSON root type is neither ``dict`` nor ``list``.
        """
        data = json.loads(stdout)  # propagate JSONDecodeError to caller

        if isinstance(data, dict):
            # Documented single-object shape: {"type":"result","result":"...",...}
            if "result" in data:
                return data["result"]
            raise KeyError("result")

        if isinstance(data, list):
            # CLI 2.1.x: array of typed event objects.
            # Primary: find the type=="result" entry (walk in reverse — it's last).
            for event in reversed(data):
                if (
                    isinstance(event, dict)
                    and event.get("type") == "result"
                    and "result" in event
                ):
                    return event["result"]
            # Fallback: assemble text from the last assistant content blocks.
            for event in reversed(data):
                if isinstance(event, dict) and event.get("type") == "assistant":
                    blocks = event.get("message", {}).get("content", [])
                    text = "".join(
                        b.get("text", "")
                        for b in blocks
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                    if text:
                        return text
            raise KeyError("result")

        raise TypeError(f"unexpected claude CLI JSON type: {type(data).__name__}")

    def _call_claude(
        self,
        user: str,
        system: str | None,
    ) -> str:
        """Invoke ``claude -p`` and return the result text.

        Args:
            user: User-turn content.
            system: System prompt content, or ``None``.

        Returns:
            The assistant reply string.

        Raises:
            RuntimeError: If the ``claude`` binary cannot be found or the
                subprocess exits with a non-zero status.
        """
        binary = shutil.which("claude") or os.getenv("CLAUDE_CLI_PATH")
        if not binary:
            raise RuntimeError(
                "claude CLI not found. Install it (https://claude.ai/code) or "
                "set the CLAUDE_CLI_PATH environment variable to its path."
            )

        # Pass the user text via stdin (-p with no argument) rather than as a
        # command-line argument.  The ReAct trajectory grows with each tool call
        # and can exceed Windows' 32767-char CreateProcess limit or contain
        # characters that trip the CLI's argument parser.  Stdin bypasses both.
        cmd: list[str] = [
            binary,
            "-p",  # no inline argument; prompt is read from stdin
            "--model",
            self.model,
            "--output-format",
            "json",
            "--no-session-persistence",
            "--max-turns",
            "1",
            # Disable the CLI's own agentic tools so it behaves as a pure
            # text completer.  DSPy drives the tool-use loop itself; we don't
            # want the CLI's built-in Bash/Edit/etc. tools competing with it.
            "--tools",
            "",
            # Suppress globally-registered MCP servers (e.g. code-search).
            # Without this flag the subprocess auto-connects to every MCP
            # server in ~/.claude.json and is handed all their tools; it then
            # spends its one turn on a self-initiated tool call instead of
            # returning DSPy's expected text output → error_max_turns on every
            # rollout.  With --strict-mcp-config and no --mcp-config provided,
            # the effective MCP set is empty and the subprocess is a pure LM.
            "--strict-mcp-config",
        ]
        if system:
            cmd += ["--system-prompt", system]
        # Note: the claude CLI does not expose --max-tokens for the -p mode;
        # the max_tokens parameter is stored for forward-compatibility but not
        # forwarded to the subprocess.

        # Strip API credentials so the CLI always uses subscription OAuth.
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
        }

        logger.debug("ClaudeCodeLM: running %s (stdin=%d chars)", cmd[0], len(user))
        result = subprocess.run(
            cmd,
            input=user,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout,
            env=env,
        )

        # Parse stdout first regardless of exit code.  When --tools "" is used
        # the CLI can exit 1 while still producing valid JSON output in stdout;
        # treat that as success.  Only raise when both conditions hold (non-zero
        # AND unparseable / empty stdout).
        try:
            return self._extract_text(result.stdout)
        except (json.JSONDecodeError, KeyError, TypeError) as parse_exc:
            if result.returncode != 0:
                raise RuntimeError(
                    f"claude CLI exited with code {result.returncode}: "
                    f"{result.stderr or result.stdout!r}"
                ) from parse_exc
            raise RuntimeError(
                f"Unexpected claude CLI output: {result.stdout!r}"
            ) from parse_exc


def configure_dspy(model: str | None = None, **kwargs: Any) -> ClaudeCodeLM:
    """Build a :class:`ClaudeCodeLM`, configure DSPy globally, and return it.

    Loads an optional ``.env`` file (searched from the current working
    directory upward) so ``CLAUDE_CODE_OAUTH_TOKEN`` and ``DSPY_LM_MODEL``
    can be supplied without polluting the shell environment.

    Args:
        model: Model override; falls back to ``DSPY_LM_MODEL`` then
            ``"claude-sonnet-4-6"``.
        **kwargs: Forwarded to :class:`ClaudeCodeLM`.

    Returns:
        The configured :class:`ClaudeCodeLM` instance (also set as the DSPy
        default LM via ``dspy.configure``).

    Example::

        lm = configure_dspy()
        print(lm.model)        # "claude-sonnet-4-6" (or DSPY_LM_MODEL)
    """
    try:
        from dotenv import find_dotenv, load_dotenv

        load_dotenv(find_dotenv(usecwd=True))
        logger.debug(
            "ClaudeCodeLM: loaded .env from %s", find_dotenv(usecwd=True) or "(none)"
        )
    except ImportError:
        logger.debug("ClaudeCodeLM: python-dotenv not installed, skipping .env load")

    lm = ClaudeCodeLM(model=model, **kwargs)
    dspy.configure(lm=lm)
    logger.info("DSPy configured with ClaudeCodeLM (model=%s)", lm.model)
    return lm
