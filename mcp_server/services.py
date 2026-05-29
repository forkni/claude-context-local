"""State and config accessors — thin re-exports for backward compatibility.

ServiceLocator was removed (see docs/adr/0005-no-di-container-module-singleton-state.md):
it was a closed loop that always resolved to the module-level ApplicationState singleton
with no production consumers of swappability. Direct accessors are the canonical form.
"""

from __future__ import annotations

from mcp_server.state import get_state as get_state  # noqa: F401
from search.config import get_search_config as get_config  # noqa: F401
