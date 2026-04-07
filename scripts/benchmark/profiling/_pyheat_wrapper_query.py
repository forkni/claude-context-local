"""pyheat wrapper: runs profile_first_query without --snoop for heatmap generation.

WARNING: Do NOT add --snoop here. pyheat uses sys.settrace for profiling,
         and snoop also uses sys.settrace — they conflict.

Usage:
    .venv/Scripts/pyheat scripts/benchmark/profiling/_pyheat_wrapper_query.py -o heatmap_query.png
"""

import sys
from pathlib import Path


# Pre-configure argv before profile_first_query parses it
sys.argv = ["profile_first_query.py"]

# Ensure project root is on the path
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from profile_first_query import main  # noqa: E402


main()
