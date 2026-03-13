"""pyheat wrapper: runs profile_init without --snoop for heatmap generation.

WARNING: Do NOT add --snoop here. pyheat uses sys.settrace for profiling,
         and snoop also uses sys.settrace — they conflict.

Usage:
    .venv/Scripts/pyheat scripts/benchmark/profiling/_pyheat_wrapper_init.py -o heatmap_init.png
"""

import sys
from pathlib import Path


# Pre-configure argv before profile_init parses it
sys.argv = ["profile_init.py"]

# Ensure project root is on the path
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from profile_init import main  # noqa: E402


main()
