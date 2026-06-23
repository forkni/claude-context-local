"""Unit tests for utils/dspy_claude_code.py.

Tests cover:
- forward() returns a ModelResponse with correct choices and model.
- choices[0].message.content matches the mocked CLI output.
- subprocess env passed to run() has no ANTHROPIC_API_KEY.
- n>1 spawns multiple subprocess calls and returns multiple choices.
- End-to-end dspy.Predict call works with the mocked LM.
- _call_claude raises RuntimeError when the binary is missing.
- _call_claude raises RuntimeError on non-zero subprocess exit.
- _call_claude raises RuntimeError on malformed JSON output.
- configure_dspy sets dspy's global LM and returns the ClaudeCodeLM.
"""

import json
import subprocess
from unittest.mock import MagicMock, patch

import dspy
import pytest

from utils.dspy_claude_code import ClaudeCodeLM, configure_dspy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(stdout: str, returncode: int = 0, stderr: str = "") -> MagicMock:
    """Build a mock CompletedProcess for subprocess.run."""
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = returncode
    return proc


_PARIS_STDOUT = json.dumps({"result": "Paris"})


# ---------------------------------------------------------------------------
# ClaudeCodeLM.forward
# ---------------------------------------------------------------------------


class TestClaudeCodeLMForward:
    """Tests for ClaudeCodeLM.forward()."""

    def test_returns_model_response_with_correct_content(self):
        """forward() wraps the CLI result in a ModelResponse."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", return_value=_make_proc(_PARIS_STDOUT)),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            resp = lm.forward(
                messages=[{"role": "user", "content": "capital of France?"}]
            )

        assert resp.choices[0].message.content == "Paris"
        assert resp.model == "claude-sonnet-4-6"

    def test_model_set_on_response(self):
        """Response carries the model name passed at construction time."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", return_value=_make_proc(_PARIS_STDOUT)),
        ):
            lm = ClaudeCodeLM(model="claude-opus-4-8")
            resp = lm.forward(messages=[{"role": "user", "content": "hi"}])

        assert resp.model == "claude-opus-4-8"

    def test_n_produces_multiple_choices(self):
        """n=3 spawns 3 subprocess calls and returns 3 choices."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", return_value=_make_proc(_PARIS_STDOUT)) as mock_run,
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            resp = lm.forward(messages=[{"role": "user", "content": "q"}], n=3)

        assert len(resp.choices) == 3
        assert mock_run.call_count == 3
        for choice in resp.choices:
            assert choice.message.content == "Paris"

    def test_system_message_extracted(self):
        """System role messages are forwarded as --system-prompt, not user text."""
        captured_cmd: list[list[str]] = []

        def capture_run(cmd, **kwargs):
            captured_cmd.append(cmd)
            return _make_proc(_PARIS_STDOUT)

        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", side_effect=capture_run),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            lm.forward(
                messages=[
                    {"role": "system", "content": "You are a geography expert."},
                    {"role": "user", "content": "capital of France?"},
                ]
            )

        cmd = captured_cmd[0]
        assert "--system-prompt" in cmd
        sys_idx = cmd.index("--system-prompt")
        assert "geography expert" in cmd[sys_idx + 1]

    def test_hidden_params_response_cost_zero(self):
        """_hidden_params carries response_cost=0.0 (no API billing)."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", return_value=_make_proc(_PARIS_STDOUT)),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            resp = lm.forward(messages=[{"role": "user", "content": "hi"}])

        assert resp._hidden_params.get("response_cost") == 0.0

    def test_dspy_internal_kwargs_stripped(self):
        """cache and rollout_id are stripped before dispatch; no TypeError."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", return_value=_make_proc(_PARIS_STDOUT)),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            # Should not raise even though these kwargs are DSPy-internal
            resp = lm.forward(
                messages=[{"role": "user", "content": "hi"}],
                cache=True,
                rollout_id="abc123",
            )

        assert resp.choices[0].message.content == "Paris"


# ---------------------------------------------------------------------------
# Subscription guard — ANTHROPIC_API_KEY must be absent from env
# ---------------------------------------------------------------------------


class TestSubscriptionGuard:
    """Subprocess env must not contain API credentials."""

    def test_anthropic_api_key_absent_from_env(self, monkeypatch):
        """Even if set in os.environ, ANTHROPIC_API_KEY is stripped."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret")

        captured_env: dict = {}

        def capture_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return _make_proc(_PARIS_STDOUT)

        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", side_effect=capture_run),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            lm.forward(messages=[{"role": "user", "content": "hi"}])

        assert "ANTHROPIC_API_KEY" not in captured_env

    def test_anthropic_auth_token_absent_from_env(self, monkeypatch):
        """ANTHROPIC_AUTH_TOKEN is also stripped."""
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "secret-token")

        captured_env: dict = {}

        def capture_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return _make_proc(_PARIS_STDOUT)

        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", side_effect=capture_run),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            lm.forward(messages=[{"role": "user", "content": "hi"}])

        assert "ANTHROPIC_AUTH_TOKEN" not in captured_env


# ---------------------------------------------------------------------------
# Error paths in _call_claude
# ---------------------------------------------------------------------------


class TestCallClaudeErrors:
    """Error handling in _call_claude."""

    def test_raises_when_binary_missing(self):
        """RuntimeError with helpful message when no claude binary found."""
        with (
            patch("shutil.which", return_value=None),
            patch("os.getenv", return_value=None),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            with pytest.raises(RuntimeError, match="claude CLI not found"):
                lm._call_claude("hello", None, 4096)

    def test_raises_on_nonzero_exit(self):
        """RuntimeError is raised when the subprocess exits with non-zero."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch(
                "subprocess.run",
                return_value=_make_proc("", returncode=1, stderr="auth error"),
            ),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            with pytest.raises(RuntimeError, match="exited with code 1"):
                lm._call_claude("hello", None, 4096)

    def test_raises_on_malformed_json(self):
        """RuntimeError when CLI returns non-JSON output."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", return_value=_make_proc("not json")),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            with pytest.raises(RuntimeError, match="Unexpected claude CLI output"):
                lm._call_claude("hello", None, 4096)

    def test_raises_when_result_key_missing(self):
        """RuntimeError when JSON is valid but 'result' key is absent."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch(
                "subprocess.run",
                return_value=_make_proc(json.dumps({"type": "result"})),
            ),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            with pytest.raises(RuntimeError, match="Unexpected claude CLI output"):
                lm._call_claude("hello", None, 4096)


# ---------------------------------------------------------------------------
# End-to-end: dspy.Predict with mocked LM
# ---------------------------------------------------------------------------


class TestDspyPredictIntegration:
    """dspy.Predict round-trip using the mocked ClaudeCodeLM."""

    def test_predict_question_answer(self):
        """dspy.Predict('question -> answer') works with mocked forward.

        DSPy's JSONAdapter expects the LM to return structured output such as
        ``{"answer": "Paris"}``.  The subprocess mock returns that JSON string
        as the ``result`` field so the adapter can parse it correctly.
        """
        # DSPy's JSONAdapter will parse this into result.answer = "Paris".
        answer_stdout = json.dumps({"result": json.dumps({"answer": "Paris"})})

        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", return_value=_make_proc(answer_stdout)),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            dspy.configure(lm=lm)
            pred = dspy.Predict("question -> answer")
            result = pred(question="What is the capital of France?")

        assert "paris" in result.answer.lower()


# ---------------------------------------------------------------------------
# configure_dspy
# ---------------------------------------------------------------------------


class TestConfigureDspy:
    """configure_dspy wires up the global DSPy LM."""

    def test_returns_claude_code_lm(self):
        """configure_dspy returns a ClaudeCodeLM instance."""
        with patch("dotenv.load_dotenv"):
            lm = configure_dspy(model="claude-sonnet-4-6")
        assert isinstance(lm, ClaudeCodeLM)

    def test_sets_dspy_global_lm(self):
        """After configure_dspy, dspy.settings.lm is the returned LM."""
        with patch("dotenv.load_dotenv"):
            lm = configure_dspy(model="claude-sonnet-4-6")
        assert dspy.settings.lm is lm

    def test_model_default_from_env(self, monkeypatch):
        """DSPY_LM_MODEL env var sets the model when no explicit model given."""
        monkeypatch.setenv("DSPY_LM_MODEL", "claude-opus-4-8")
        with patch("dotenv.load_dotenv"):
            lm = configure_dspy()
        assert lm.model == "claude-opus-4-8"

    def test_model_default_fallback(self, monkeypatch):
        """Falls back to claude-sonnet-4-6 when DSPY_LM_MODEL is unset."""
        monkeypatch.delenv("DSPY_LM_MODEL", raising=False)
        with patch("dotenv.load_dotenv"):
            lm = configure_dspy()
        assert lm.model == "claude-sonnet-4-6"
