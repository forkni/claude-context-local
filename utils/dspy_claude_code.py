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
        max_tokens: Token cap forwarded to ``--max-tokens``.
        timeout: Per-call subprocess timeout in seconds.
        **kwargs: Forwarded to ``dspy.BaseLM.__init__``.
    """

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int = 4096,
        timeout: int = 120,
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
        max_tokens: int = kwargs.pop("max_tokens", self.max_tokens)
        # temperature is accepted but not forwarded (CLI doesn't expose it via
        # non-API path); pop to avoid unexpected forwarding in the future.
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
            texts.append(self._call_claude(user_text, system_text, max_tokens))

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_claude(
        self,
        user: str,
        system: str | None,
        max_tokens: int,
    ) -> str:
        """Invoke ``claude -p`` and return the result text.

        Args:
            user: User-turn content.
            system: System prompt content, or ``None``.
            max_tokens: Token ceiling for the response.

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

        cmd: list[str] = [
            binary,
            "-p",
            user,
            "--model",
            self.model,
            "--output-format",
            "json",
            "--no-session-persistence",
            "--max-turns",
            "1",
        ]
        if system:
            cmd += ["--system-prompt", system]
        if max_tokens:
            cmd += ["--max-tokens", str(max_tokens)]

        # Strip API credentials so the CLI always uses subscription OAuth.
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
        }

        logger.debug("ClaudeCodeLM: running %s", cmd[0])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            env=env,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"claude CLI exited with code {result.returncode}: {result.stderr}"
            )

        try:
            return json.loads(result.stdout)["result"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise RuntimeError(
                f"Unexpected claude CLI output: {result.stdout!r}"
            ) from exc


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
