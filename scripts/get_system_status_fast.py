"""
Fast system status retriever for batch scripts.
ZERO dependencies on project modules to ensure <100ms startup time.
Reads JSON config files directly.
"""

import json
import os
from pathlib import Path


# --- Constants (mirrored from config.py) ---
MODEL_REGISTRY = {
    "google/embeddinggemma-300m": {
        "dim": 768,
        "vram": "~1.2GB",
        "short": "embeddinggemma-300m",
    },
    "BAAI/bge-m3": {"dim": 1024, "vram": "1-1.5GB", "short": "bge-m3"},
    "Qwen/Qwen3-Embedding-0.6B": {"dim": 1024, "vram": "2.3GB", "short": "qwen3-0.6b"},
    "Qwen/Qwen3-Embedding-4B": {"dim": 2560, "vram": "~10GB", "short": "qwen3-4b"},
    "nomic-ai/CodeRankEmbed": {
        "dim": 768,
        "vram": "0.5-0.6GB",
        "short": "coderankembed",
    },
    "Alibaba-NLP/gte-modernbert-base": {
        "dim": 768,
        "vram": "0.28GB",
        "short": "gte-modernbert",
    },
    "jinaai/jina-embeddings-v5-text-small-retrieval": {
        "dim": 1024,
        "vram": "1.2-1.5GB",
        "short": "jina-v5-small",
    },
}

DEFAULT_STORAGE_DIR = Path.home() / ".claude_code_search"

# This script lives at <repo-root>/scripts/get_system_status_fast.py; anchor the
# primary candidates to the repo root so resolution doesn't depend on process cwd
# (see project_search_config_guard memory note for the incident this fixes).
_REPO_ROOT = Path(__file__).resolve().parent.parent


def get_config_path():
    """Find search_config.json (falls back to the committed .example template)."""
    candidates = [
        _REPO_ROOT / "search_config.json",
        _REPO_ROOT / ".search_config.json",
        DEFAULT_STORAGE_DIR / "search_config.json",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # No real config anywhere -- fall back to the committed shared-default template
    # (read-only; never written to) so status reflects the real shared default
    # instead of a bare hardcoded fallback.
    example = _REPO_ROOT / "search_config.json.example"
    if example.exists():
        return example
    return candidates[0]  # Default fallback (path only; file may not exist)


def get_selection_path():
    """Find project_selection.json"""
    # Check env var
    storage = os.environ.get("CODE_SEARCH_STORAGE")
    if storage:
        return Path(storage) / "project_selection.json"
    return DEFAULT_STORAGE_DIR / "project_selection.json"


def main():
    try:
        # 1. Load Search Config
        config_path = get_config_path()
        cfg = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    cfg = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Warning: Config parse error: {e.msg}")
            except PermissionError:
                print("Warning: Config file locked, using defaults")
            except OSError as e:
                print(f"Warning: Cannot read config: {e}")

        # Parse Config Values
        embedding = cfg.get("embedding", {})
        reranker = cfg.get("reranker", {})
        performance = cfg.get("performance", {})
        output = cfg.get("output", {})

        # -- Model Status --
        model_name = embedding.get("model_name", "BAAI/bge-m3")
        spec = MODEL_REGISTRY.get(
            model_name, {"dim": "?", "vram": "?", "short": model_name}
        )
        short_name = spec.get("short", model_name.split("/")[-1])
        print(f"Model: {short_name} ({spec['dim']}d, {spec['vram']})")
        print("Tip: Press M for Quick Model Switch")

        # -- Reranker Status --
        reranker_enabled = reranker.get("enabled", True)
        if reranker_enabled:
            r_name = reranker.get(
                "model_name", "Alibaba-NLP/gte-reranker-modernbert-base"
            )
            print(f"       Reranker: {r_name.split('/')[-1]} (enabled)")
        else:
            print("       Reranker: Disabled")

        print()

        # -- RAM Fallback --
        ram_fallback = performance.get("allow_ram_fallback", False)
        # Handle legacy key allow_shared_memory if allow_ram_fallback missing
        if (
            "allow_ram_fallback" not in performance
            and "allow_shared_memory" in performance
        ):
            ram_fallback = performance["allow_shared_memory"]

        print(f"RAM Fallback: {'On' if ram_fallback else 'Off'}")

        # -- Semantic Intent --
        intent = cfg.get("intent", {})
        semantic = intent.get("semantic_enabled", False)
        print(f"Semantic Intent: {'On' if semantic else 'Off'}")

        # -- Output Format --
        out_fmt = output.get("format", "compact")
        print(f"Output Format: {out_fmt}")

        # 2. Load Project Selection
        sel_path = get_selection_path()
        project_info = "None (use option 5 to select)"

        if sel_path.exists():
            try:
                with open(sel_path, encoding="utf-8") as f:
                    sel_data = json.load(f)
                    path_str = sel_data.get("last_project_path", "")
                    if path_str:
                        p_path = Path(path_str)
                        if p_path.exists():
                            name = p_path.name
                            # Truncate for display
                            display_path = path_str
                            if len(path_str) > 50:
                                display_path = "..." + path_str[-47:]

                            print(f"Current Project: {name}")
                            print(f"                 ({display_path})")
                        else:
                            print(f"Current Project: {p_path.name} (Not Found)")
                    else:
                        print(f"Current Project: {project_info}")
            except Exception:
                print(f"Current Project: {project_info}")
        else:
            print(f"Current Project: {project_info}")

    except Exception as e:
        print(f"Status Error: {e}")


if __name__ == "__main__":
    main()
