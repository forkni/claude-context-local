"""List indexed projects in selection format for batch scripts.

STANDALONE VERSION - No ML imports to avoid PyTorch crash.
Uses only Python stdlib.

Output format: index|project_name|project_path|models_list
Example: 1|myproject|F:/Projects/MyProject|bge-m3 (1024d), Qwen3-0.6B (1024d)
"""

import os
import sys
from pathlib import Path
import json


def get_storage_dir():
    """Get storage directory without importing from mcp_server.

    Replicates logic from mcp_server.server.get_storage_dir().
    """
    storage_path = os.getenv('CODE_SEARCH_STORAGE',
                             str(Path.home() / '.claude_code_search'))
    return Path(storage_path)


def main():
    try:
        storage = get_storage_dir()
    except Exception:
        # Storage dir doesn't exist - silent exit
        return

    projects_dir = storage / 'projects'

    if not projects_dir.exists():
        # Silent exit for batch script handling
        return

    projects_by_path = {}

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        info_file = project_dir / 'project_info.json'
        if not info_file.exists():
            continue

        try:
            with open(info_file, encoding='utf-8') as f:
                info = json.load(f)
        except Exception:
            # Skip malformed project_info.json
            continue

        path = info.get('project_path')
        if not path:
            continue

        if path not in projects_by_path:
            projects_by_path[path] = {
                'name': info.get('project_name', 'Unknown'),
                'path': path,
                'hash': info.get('project_hash', ''),
                'models': []
            }

        # Get model short name and dimension
        model_full = info.get('embedding_model', 'unknown')
        model_short = model_full.split('/')[-1]
        dimension = info.get('model_dimension', 0)

        projects_by_path[path]['models'].append(f"{model_short} ({dimension}d)")

    # Output format: index|name|path|models
    for i, (path, info) in enumerate(projects_by_path.items(), 1):
        models_str = ', '.join(info['models'])
        print(f"{i}|{info['name']}|{info['path']}|{models_str}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Silent exit for batch script error handling
        sys.exit(0)
