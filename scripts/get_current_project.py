#!/usr/bin/env python3
"""Get current project selection for batch script display.

Outputs a single line with project info for use in start_mcp_server.cmd.
Exit codes: 0 = project selected, 1 = no selection
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.project_persistence import get_selection_for_display


def main():
    """Output current project info for batch script consumption."""
    info = get_selection_for_display()

    if not info["exists"]:
        print("Current Project: None (use option 5 to select)")
        return 1

    # Format: name + path (truncated if too long)
    name = info["name"]
    path = info["path"]

    # Truncate path if > 50 chars
    if len(path) > 50:
        path = "..." + path[-47:]

    print(f"Current Project: {name}")
    print(f"                 ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
