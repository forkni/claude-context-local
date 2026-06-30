"""Envelope constructors for MCP tool responses.

All handler-layer error/success shapes are owned here — every ``{"error": …}`` and
``{"success": …}`` dict in ``mcp_server/tools/`` must be built through one of these
helpers so that the envelope contract lives in exactly one place.

Invariants
----------
- Key names are frozen (snapshot tests + MCP client contracts depend on them).
- ``ok()`` drops only fields that are ``None``, ``""`` (empty string), ``[]`` (empty
  list), or ``{}`` (empty dict).  It keeps ``False``, ``0``, and non-empty values.
- ``error()`` never drops context fields — clients may rely on them.
- ``mcp_server.output_formatter`` owns token-reduction *formatting*; this module is
  not merged into it and does not call it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from search.exceptions import DimensionMismatchError


def ok(**fields: Any) -> dict[str, Any]:
    """Build a success envelope, omitting fields that are ``None`` or ``""``.

    Drops fields whose value is ``None`` or ``""`` (empty string) — useful for
    optional fields passed as ``None`` to indicate absence.  Keeps ``False``,
    ``0``, ``[]``, ``{}`` and any other value, so that fields which are
    legitimately empty (e.g. ``deleted_directories=[]``) are preserved.

    Example::

        responses.ok(success=True, project="/path", files_added=5)
        # → {"success": True, "project": "/path", "files_added": 5}

        responses.ok(success=True, optional=None)
        # → {"success": True}   (None dropped)
    """
    return {k: v for k, v in fields.items() if v is not None and v != ""}


def error(error_message: str, **context: Any) -> dict[str, Any]:
    """Build an error envelope.

    Args:
        error_message: Human-readable error message (value of the ``"error"``
            key).  Named ``error_message`` (not ``message``) so that callers can
            pass a separate ``message=`` context field without a kwarg collision::

                responses.error("Not found", message="More detail here")
                # → {"error": "Not found", "message": "More detail here"}

        **context: Optional extra fields (e.g. ``tool=``, ``chunk_id=``,
            ``hint=``, ``message=``, ``is_current_project=``).

    Returns:
        ``{"error": error_message, **context}``
    """
    result: dict[str, Any] = {"error": error_message}
    result.update(context)
    return result


def client_disconnected() -> dict[str, Any]:
    """Error envelope for anyio broken/closed resource (client disconnected)."""
    return {"error": "Client disconnected", "status": "cancelled"}


def no_indexed_project() -> dict[str, Any]:
    """Error envelope emitted when no project is currently indexed.

    Preserves the exact 4-key shape required by MCP clients.
    """
    return {
        "error": "No indexed project found",
        "message": "Use index_directory to index a project first.",
        "current_project": None,
        "system_message": (
            "No project indexed. Use index_directory to index a project first."
        ),
    }


def dimension_mismatch(e: DimensionMismatchError) -> dict[str, Any]:
    """Error envelope for a :class:`~search.exceptions.DimensionMismatchError`.

    Delegates to ``e.to_response()`` so the exact key names live on the
    exception class itself.
    """
    return e.to_response()
