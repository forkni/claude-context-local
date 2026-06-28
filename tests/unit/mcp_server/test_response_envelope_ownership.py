"""P3 completeness gate: all MCP envelope literals owned by responses.py.

If this test fails you have either:
- Added a stray ``{"error": …}`` or ``{"success": …}`` dict literal in a
  ``mcp_server/tools/`` handler outside ``responses.py``, OR
- Called ``responses.error()`` / ``responses.ok()`` correctly but this test has
  a false positive (update the allowlist below).

The canonical owner is ``mcp_server.tools.responses``.  All handler-layer
error/success envelopes must be built through its helpers.
"""

from __future__ import annotations

import ast
import glob
from pathlib import Path


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _is_error_dict_literal(node: ast.expr) -> bool:
    """Return True if *node* is a dict literal whose first key is ``"error"``."""
    if not isinstance(node, ast.Dict):
        return False
    if not node.keys:
        return False
    first_key = node.keys[0]
    return isinstance(first_key, ast.Constant) and first_key.value == "error"


def _is_success_dict_literal(node: ast.expr) -> bool:
    """Return True if *node* is a dict literal that contains a ``"success"`` key."""
    if not isinstance(node, ast.Dict):
        return False
    return any(isinstance(k, ast.Constant) and k.value == "success" for k in node.keys)


def _collect_stray_envelope_literals(src_file: str) -> list[str]:
    """Return a list of ``"file:line"`` strings for any stray envelope literals."""
    try:
        tree = ast.parse(Path(src_file).read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return []

    stray: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.expr) and (
            _is_error_dict_literal(node) or _is_success_dict_literal(node)
        ):
            stray.append(f"{src_file}:{node.lineno}")
    return stray


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------


class TestResponseEnvelopeOwnership:
    """P3 completeness gate: no inline error/success envelope literals in handlers.

    Scans every ``mcp_server/tools/*.py`` file except ``responses.py`` itself
    and asserts that no dict literal with an ``"error"`` first key or a
    ``"success"`` key is constructed inline.

    The gate runs in the project root so that glob paths are relative (same
    convention as ``TestSearchResultOwnership`` and ``TestNormalizePathOwnership``).
    """

    def test_no_stray_error_or_success_literals_in_tools(self) -> None:
        """All {"error":…} / {"success":…} dicts in mcp_server/tools/ must use responses.*."""
        tools_files = glob.glob("mcp_server/tools/*.py", recursive=False)

        # Exclude the owner itself and __init__ (empty)
        excluded = {"mcp_server/tools/responses.py", "mcp_server/tools/__init__.py"}
        # Normalise separators so the check is platform-independent
        excluded_norm = {p.replace("\\", "/") for p in excluded}

        stray: list[str] = []
        for fpath in tools_files:
            norm = fpath.replace("\\", "/")
            if norm in excluded_norm:
                continue
            stray.extend(_collect_stray_envelope_literals(fpath))

        assert not stray, (
            "Stray error/success dict literals found in mcp_server/tools/ — "
            "route through mcp_server.tools.responses.error() / .ok() instead:\n"
            + "\n".join(f"  {s}" for s in stray)
        )

    def test_responses_helpers_return_correct_shapes(self) -> None:
        """Unit-test each responses.* helper for exact output."""
        from mcp_server.tools import responses

        # ok() — drops None and "", keeps everything else (including [], {}, 0, False)
        assert responses.ok(success=True, project="/p", count=0) == {
            "success": True,
            "project": "/p",
            "count": 0,
        }
        # None and "" are dropped; [] and {} are kept (may be meaningful)
        assert responses.ok(success=True, extra=None, empty="", lst=[], dct={}) == {
            "success": True,
            "lst": [],
            "dct": {},
        }
        # ok() keeps False and 0
        assert responses.ok(success=True, indexed=False) == {
            "success": True,
            "indexed": False,
        }

        # error() — basic + context fields
        assert responses.error("oops") == {"error": "oops"}
        assert responses.error("oops", chunk_id="a.py:1-5:fn:f") == {
            "error": "oops",
            "chunk_id": "a.py:1-5:fn:f",
        }
        assert responses.error("oops", tool="search_code", arguments_keys=["q"]) == {
            "error": "oops",
            "tool": "search_code",
            "arguments_keys": ["q"],
        }

        # client_disconnected()
        assert responses.client_disconnected() == {
            "error": "Client disconnected",
            "status": "cancelled",
        }

        # no_indexed_project()
        result = responses.no_indexed_project()
        assert result["error"] == "No indexed project found"
        assert result["current_project"] is None
        assert "message" in result
        assert "system_message" in result

    def test_dimension_mismatch_delegates_to_exception(self) -> None:
        """dimension_mismatch() round-trips through DimensionMismatchError.to_response()."""
        from mcp_server.tools import responses
        from search.exceptions import DimensionMismatchError

        exc = DimensionMismatchError(
            "dim 512 != 1024",
            embedder_dim=512,
            index_dim=1024,
            embedder_model="small-model",
            index_model="large-model",
        )

        result = responses.dimension_mismatch(exc)
        assert result["error"] == "Dimension mismatch"
        assert result["message"] == "dim 512 != 1024"
        assert result["embedder_dimension"] == 512
        assert result["index_dimension"] == 1024
        assert "recovery_suggestion" in result
        assert "small-model" in result["recovery_suggestion"]

        # Must equal exc.to_response() directly
        assert result == exc.to_response()
