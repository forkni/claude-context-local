"""Unit tests for utils/dspy_mcp.py and the async ClaudeCodeLM.aforward.

Tests cover (all offline — no real subprocess, no MCP server, no subscription):

- ClaudeCodeLM.aforward delegates to forward and returns a ModelResponse.
- _switch_project calls the switch_project MCP tool and raises on error.
- _with_timeout wraps a dspy.Tool's func with asyncio.wait_for.
- code_search_session wraps all session lifecycle; surfaces connection errors.
- run_code_search_agent wires MCP tools and invokes the ReAct agent.
- Missing-tool guard raises RuntimeError with a helpful message.
"""

import asyncio
import json
import subprocess
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import mcp.types as mcp_types
import pytest

from utils.dspy_claude_code import ClaudeCodeLM
from utils.dspy_mcp import (
    _with_timeout,
    run_code_search_agent,
)


# A minimal fake LM for tests that need a ClaudeCodeLM instance without a
# real claude binary.
class _FakeLM(ClaudeCodeLM):
    def __init__(self):
        super().__init__(model="claude-sonnet-4-6")

    def forward(self, prompt=None, messages=None, **kwargs):
        from litellm import ModelResponse

        resp = ModelResponse(
            choices=[
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
            model=self.model,
        )
        resp._hidden_params = {"response_cost": 0.0}
        return resp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PARIS_RESULT = json.dumps({"result": "Paris"})
_SWITCH_OK = json.dumps({"success": True, "project": "/my/project", "indexed": True})


def _make_proc(stdout: str, returncode: int = 0) -> MagicMock:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.stdout = stdout
    proc.stderr = ""
    proc.returncode = returncode
    return proc


def _make_mcp_tool(name: str, description: str = "A tool.") -> mcp_types.Tool:
    """Build a minimal mcp.types.Tool for testing."""
    return mcp_types.Tool(
        name=name,
        description=description,
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."}
            },
            "required": [],
        },
    )


def _make_call_result(text: str) -> mcp_types.CallToolResult:
    """Build a successful CallToolResult with a single TextContent."""
    return mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text=text)],
        isError=False,
    )


def _make_session_mock(
    tool_name: str = "search_code",
    project_path: str = "/my/project",
) -> AsyncMock:
    """Build an async-mock ClientSession that handles switch_project + one tool."""
    session = AsyncMock()
    session.initialize = AsyncMock(return_value=None)

    list_result = MagicMock()
    list_result.tools = [_make_mcp_tool(tool_name)]
    session.list_tools = AsyncMock(return_value=list_result)

    def _call_side_effect(tool, args=None):
        if tool == "switch_project":
            return _make_call_result(
                json.dumps({"success": True, "project": project_path, "indexed": True})
            )
        return _make_call_result(
            '{"chunks": [{"content": "FaissVectorIndex at embeddings/faiss_index.py"}]}'
        )

    session.call_tool = AsyncMock(side_effect=_call_side_effect)
    return session


def _patch_agent_acall(answer: str):
    """Return a mock dspy.ReAct.acall that immediately resolves."""
    import dspy

    result = MagicMock(spec=dspy.Prediction)
    result.answer = answer
    result.trajectory = {"thought_0": "search it", "observation_0": "found it"}
    return AsyncMock(return_value=result)


def _make_http_mock():
    """Return a patch-ready streamablehttp_client mock yielding a 3-tuple."""
    mock = MagicMock()
    mock.return_value.__aenter__ = AsyncMock(
        return_value=(AsyncMock(), AsyncMock(), AsyncMock())
    )
    mock.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock


def _make_session_cls_mock(session_mock: AsyncMock) -> MagicMock:
    """Return a patch-ready ClientSession class mock wrapping session_mock."""
    cls = MagicMock()
    cls.return_value.__aenter__ = AsyncMock(return_value=session_mock)
    cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return cls


# ---------------------------------------------------------------------------
# ClaudeCodeLM.aforward (unchanged from original tests)
# ---------------------------------------------------------------------------


class TestAforward:
    """aforward wraps the sync subprocess call via asyncio.to_thread."""

    def test_aforward_returns_model_response(self):
        """aforward returns the same ModelResponse as forward."""
        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", return_value=_make_proc(_PARIS_RESULT)),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            resp = asyncio.run(
                lm.aforward(messages=[{"role": "user", "content": "hi"}])
            )

        assert resp.choices[0].message.content == "Paris"
        assert resp.model == "claude-sonnet-4-6"

    def test_aforward_strips_api_key_from_env(self, monkeypatch):
        """Even in the async path, ANTHROPIC_API_KEY is stripped."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret")

        captured_env: dict[str, Any] = {}

        def capture_run(cmd, **kwargs):
            captured_env.update(kwargs.get("env", {}))
            return _make_proc(_PARIS_RESULT)

        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", side_effect=capture_run),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            asyncio.run(lm.aforward(messages=[{"role": "user", "content": "hi"}]))

        assert "ANTHROPIC_API_KEY" not in captured_env

    def test_aforward_disables_cli_tools(self):
        """--tools '' appears in the subprocess command."""
        captured_cmds: list[list[str]] = []

        def capture_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return _make_proc(_PARIS_RESULT)

        with (
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("subprocess.run", side_effect=capture_run),
        ):
            lm = ClaudeCodeLM(model="claude-sonnet-4-6")
            asyncio.run(lm.aforward(messages=[{"role": "user", "content": "hi"}]))

        cmd = captured_cmds[0]
        assert "--tools" in cmd
        tools_idx = cmd.index("--tools")
        assert cmd[tools_idx + 1] == ""


# ---------------------------------------------------------------------------
# _with_timeout
# ---------------------------------------------------------------------------


class TestWithTimeout:
    """_with_timeout wraps a tool's func with asyncio.wait_for."""

    @pytest.mark.asyncio
    async def test_timeout_returns_observation_string(self):
        """A tool that hangs past timeout_s returns an observation, not a raise."""

        async def _slow(**kwargs):
            await asyncio.sleep(999)
            return "never"

        tool = MagicMock()
        tool.name = "slow_tool"
        tool.func = _slow

        wrapped = _with_timeout(tool, timeout_s=0.05)
        result = await wrapped.func()

        assert "slow_tool" in result
        assert "timeout" in result.lower()

    @pytest.mark.asyncio
    async def test_normal_result_passes_through(self):
        """A fast tool's return value is not modified."""

        async def _fast(**kwargs):
            return "search results"

        tool = MagicMock()
        tool.name = "fast_tool"
        tool.func = _fast

        wrapped = _with_timeout(tool, timeout_s=5.0)
        result = await wrapped.func()

        assert result == "search results"

    @pytest.mark.asyncio
    async def test_exception_returns_observation_string(self):
        """An exception inside the tool becomes an observation string."""

        async def _broken(**kwargs):
            raise ValueError("index not found")

        tool = MagicMock()
        tool.name = "broken_tool"
        tool.func = _broken

        wrapped = _with_timeout(tool, timeout_s=5.0)
        result = await wrapped.func()

        assert "broken_tool" in result
        assert "index not found" in result

    def test_mutates_tool_func_in_place(self):
        """_with_timeout mutates tool.func and returns the same tool object."""

        async def _f(**kw):
            return "x"

        tool = MagicMock()
        tool.name = "t"
        original_func = _f
        tool.func = original_func

        returned = _with_timeout(tool, timeout_s=1.0)
        assert returned is tool
        assert tool.func is not original_func


# ---------------------------------------------------------------------------
# run_code_search_agent (HTTP transport)
# ---------------------------------------------------------------------------


class TestRunCodeSearchAgent:
    """run_code_search_agent wires the MCP HTTP session, tools, and ReAct loop."""

    @pytest.mark.asyncio
    async def test_returns_prediction_with_answer(self):
        """Happy path: agent wraps the tool and returns an answer."""
        session_mock = _make_session_mock("search_code")

        with (
            patch("utils.dspy_mcp.ClaudeCodeLM", return_value=_FakeLM()),
            patch("utils.dspy_mcp.streamablehttp_client", new=_make_http_mock()),
            patch(
                "utils.dspy_mcp.ClientSession", new=_make_session_cls_mock(session_mock)
            ),
            patch("dspy.ReAct") as mock_react_cls,
        ):
            mock_agent = MagicMock()
            mock_agent.acall = _patch_agent_acall(
                "FaissVectorIndex in embeddings/faiss_index.py"
            )
            mock_react_cls.return_value = mock_agent

            result = await run_code_search_agent(
                "Where is FAISS index?",
                project_path="/my/project",
                tool_names=("search_code",),
            )

        assert "FaissVectorIndex" in result.answer

    @pytest.mark.asyncio
    async def test_switch_project_called_with_project_path(self):
        """The bridge calls switch_project with the given project_path."""
        session_mock = _make_session_mock("search_code", "/my/project")

        with (
            patch("utils.dspy_mcp.ClaudeCodeLM", return_value=_FakeLM()),
            patch("utils.dspy_mcp.streamablehttp_client", new=_make_http_mock()),
            patch(
                "utils.dspy_mcp.ClientSession", new=_make_session_cls_mock(session_mock)
            ),
            patch("dspy.ReAct") as mock_react_cls,
        ):
            mock_agent = MagicMock()
            mock_agent.acall = _patch_agent_acall("done")
            mock_react_cls.return_value = mock_agent

            await run_code_search_agent(
                "question",
                project_path="/my/project",
                tool_names=("search_code",),
            )

        session_mock.call_tool.assert_any_call(
            "switch_project", {"project_path": "/my/project"}
        )

    @pytest.mark.asyncio
    async def test_connection_error_raises_runtime_error(self):
        """A down server surfaces a clear RuntimeError, not a raw ConnectionError."""
        broken_http = MagicMock()
        broken_http.return_value.__aenter__ = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )
        broken_http.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("utils.dspy_mcp.streamablehttp_client", new=broken_http),
            pytest.raises(RuntimeError, match="Cannot reach code-search HTTP server"),
        ):
            await run_code_search_agent("question", project_path="/proj")

    @pytest.mark.asyncio
    async def test_missing_tool_raises_runtime_error(self):
        """Requesting a tool the server doesn't expose raises RuntimeError."""
        session_mock = _make_session_mock("search_code")  # only search_code exposed

        with (
            patch("utils.dspy_mcp.streamablehttp_client", new=_make_http_mock()),
            patch(
                "utils.dspy_mcp.ClientSession", new=_make_session_cls_mock(session_mock)
            ),
            pytest.raises(RuntimeError, match="does not expose requested tool"),
        ):
            await run_code_search_agent(
                "question",
                project_path="/proj",
                tool_names=("nonexistent_tool",),
            )

    @pytest.mark.asyncio
    async def test_tools_filtered_to_requested_names(self):
        """Only the requested tool names are converted, even if server has more."""
        session_mock = AsyncMock()
        session_mock.initialize = AsyncMock(return_value=None)
        list_result = MagicMock()
        list_result.tools = [
            _make_mcp_tool("search_code"),
            _make_mcp_tool("find_connections"),
            _make_mcp_tool("index_directory"),  # mutating — should NOT be exposed
        ]
        session_mock.list_tools = AsyncMock(return_value=list_result)
        session_mock.call_tool = AsyncMock(
            side_effect=lambda tool, args=None: _make_call_result(
                _SWITCH_OK if tool == "switch_project" else '{"chunks": []}'
            )
        )

        captured_tool_names: list[str] = []

        def capture_react(signature, tools, max_iters=20):
            captured_tool_names.extend(t.name for t in tools)
            agent = MagicMock()
            agent.acall = _patch_agent_acall("done")
            return agent

        with (
            patch("utils.dspy_mcp.ClaudeCodeLM", return_value=_FakeLM()),
            patch("utils.dspy_mcp.streamablehttp_client", new=_make_http_mock()),
            patch(
                "utils.dspy_mcp.ClientSession", new=_make_session_cls_mock(session_mock)
            ),
            patch("dspy.ReAct", side_effect=capture_react),
        ):
            await run_code_search_agent(
                "question",
                project_path="/proj",
                tool_names=("search_code", "find_connections"),
            )

        assert "index_directory" not in captured_tool_names
        assert "search_code" in captured_tool_names
        assert "find_connections" in captured_tool_names
