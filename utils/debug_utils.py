"""Debug and profiling utilities for the MCP server.

Provides safe snoop wrappers that degrade to no-ops when snoop is not installed,
ensuring zero overhead in production.

Usage::

    from utils.debug_utils import snoop_decorator, create_snoop_config

    # As a decorator (no-op if snoop not installed)
    @snoop_decorator(depth=2, watch=("self.model_name",))
    def my_method(self): ...

    # For monkey-patching in profiling scripts
    cfg = create_snoop_config(out="debug.log")
    if cfg:
        MyClass.initialize = cfg.snoop(depth=1)(MyClass.initialize)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar


logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


def snoop_decorator(
    fn: Callable | None = None,
    *,
    depth: int = 1,
    watch: tuple[str, ...] = (),
    enabled: bool = True,
) -> Callable:
    """Return a @snoop decorator, or a transparent no-op if snoop is unavailable.

    Designed so ``@snoop_decorator`` can be left on functions in development
    branches without breaking production (no snoop installed = zero overhead).

    Args:
        fn: When used as ``@snoop_decorator`` (no args), receives the function
            directly. When used as ``@snoop_decorator(depth=2)``, is None.
        depth: Levels of called functions to trace.
        watch: Extra expressions to evaluate and display (e.g.
            ``("self.model_name", "len(self._cache)")``).
        enabled: Pass ``False`` to get a no-op decorator regardless of
            whether snoop is installed.

    Returns:
        Decorator or decorated function.

    Example::

        @snoop_decorator(depth=2, watch=("self.model_name",))
        def load(self):
            ...
    """

    def _noop(f: Callable) -> Callable:
        return f

    try:
        import snoop as _snoop
    except ImportError:
        logger.debug("snoop not installed; snoop_decorator() is a no-op")
        decorator: Callable = _noop
    else:
        if not enabled:
            decorator = _noop
        elif watch:
            decorator = _snoop(depth=depth, watch=watch)
        else:
            decorator = _snoop(depth=depth)

    if fn is not None:
        # Called as @snoop_decorator with no arguments
        return decorator(fn)
    return decorator


def create_snoop_config(
    out: str | None = None,
    *,
    enabled: bool = True,
) -> object | None:
    """Create a snoop.Config with timestamp column output.

    Note: call-depth tracing is configured per-decorator via ``cfg.snoop(depth=N)``,
    not at Config creation time.

    Args:
        out: Output destination — file path string, or None for stderr.
        enabled: Set to False to get a no-op config object.

    Returns:
        ``snoop.Config`` instance, or ``None`` if snoop is not installed.

    Example::

        cfg = create_snoop_config(out="debug.log")
        if cfg:
            ModelLoader.load = cfg.snoop(depth=1)(ModelLoader.load)
    """
    try:
        import snoop as _snoop

        kwargs: dict[str, object] = {
            "columns": "time",
            "enabled": enabled,
        }
        if out is not None:
            kwargs["out"] = out
        return _snoop.Config(**kwargs)
    except ImportError:
        logger.debug("snoop not installed; create_snoop_config() is a no-op")
        return None
