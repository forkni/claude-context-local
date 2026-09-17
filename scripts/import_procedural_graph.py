"""Import a producer-authored Procedural Graph seed into the local store.

Standalone operator entry point for ADR-0074: the only supported way to load
a seed document (produced by ``TD_Glossary_tox``) into
``<storage_dir>/procedural_graphs/``. Deliberately does **not** import
``mcp_server.storage_manager.get_storage_dir`` -- that import pulls in
PyTorch and measured 10.4s on this machine, which is unacceptable for a
one-shot CLI script. Instead this script re-implements the same
``CODE_SEARCH_STORAGE`` / ``~/.claude_code_search`` lookup standalone
(matching ``scripts/list_projects_parseable.py``), overridable with
``--storage-dir``.

Usage:
    .venv/Scripts/python.exe scripts/import_procedural_graph.py \
        tests/fixtures/pg/network_layout_seed.json
    .venv/Scripts/python.exe scripts/import_procedural_graph.py \
        tests/fixtures/pg/network_layout_seed.json --name network_layout__cand3 --force
"""

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from graph.procedural_graph import (  # noqa: E402
    ProceduralGraphError,
    ProceduralGraphStore,
)


def _default_storage_dir() -> Path:
    """Replicates ``mcp_server.storage_manager.get_storage_dir()`` without
    importing it (see module docstring for why).
    """
    storage_path = os.getenv(
        "CODE_SEARCH_STORAGE", str(Path.home() / ".claude_code_search")
    )
    return Path(storage_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "seed", type=Path, help="Path to a Procedural Graph seed JSON document"
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Stored name (default: the seed's own 'name' field)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing graph of the same name",
    )
    parser.add_argument(
        "--storage-dir",
        type=Path,
        default=None,
        help="Base storage dir (default: $CODE_SEARCH_STORAGE or ~/.claude_code_search)",
    )
    args = parser.parse_args()

    base_dir = (
        args.storage_dir if args.storage_dir is not None else _default_storage_dir()
    )
    store = ProceduralGraphStore(base_dir / "procedural_graphs")

    try:
        stored_name = store.import_seed(args.seed, name=args.name, force=args.force)
    except ProceduralGraphError as exc:
        print(f"invalid procedural graph seed: {args.seed}", file=sys.stderr)
        for error in exc.errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    graph = store.load(stored_name)
    dest = store.path_for(stored_name)
    edge_count = len(graph.extract(None, 1))
    print(f"imported {stored_name!r} -> {dest}")
    print(f"{len(graph.node_ids)} nodes, {edge_count} edges")


if __name__ == "__main__":
    main()
