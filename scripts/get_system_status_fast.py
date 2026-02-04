"""
Fast system status retriever for batch scripts.
ZERO dependencies on project modules to ensure <100ms startup time.
Reads JSON config files directly.
"""

import json
import os
import sys
from pathlib import Path

# --- Constants (mirrored from config.py) ---
MODEL_REGISTRY = {
    "google/embeddinggemma-300m": {"dim": 768, "vram": "4-8GB", "short": "embeddinggemma-300m"},
    "BAAI/bge-m3": {"dim": 1024, "vram": "1-1.5GB", "short": "bge-m3"},
    "BAAI/bge-code-v1": {"dim": 1536, "vram": "4GB", "short": "bge-code-v1"},
    "Qwen/Qwen3-Embedding-0.6B": {"dim": 1024, "vram": "2.3GB", "short": "qwen3-0.6b"},
    "Qwen/Qwen3-Embedding-4B": {"dim": 2560, "vram": "7.5-8GB", "short": "qwen3-4b"},
    "nomic-ai/CodeRankEmbed": {"dim": 768, "vram": "0.5-0.6GB", "short": "coderankembed"},
    "Alibaba-NLP/gte-modernbert-base": {"dim": 768, "vram": "0.28GB", "short": "gte-modernbert"},
}

DEFAULT_STORAGE_DIR = Path.home() / ".claude_code_search"

def get_config_path():
    """Find search_config.json"""
    candidates = [
        "search_config.json",
        ".search_config.json",
        DEFAULT_STORAGE_DIR / "search_config.json"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0] # Default fallback

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
                with open(config_path, "r") as f:
                    cfg = json.load(f)
            except:
                pass

        # Parse Config Values
        embedding = cfg.get("embedding", {})
        routing = cfg.get("routing", {})
        reranker = cfg.get("reranker", {})
        performance = cfg.get("performance", {})
        output = cfg.get("output", {})

        # -- Model Status --
        model_name = embedding.get("model_name", "google/embeddinggemma-300m")
        multi_enabled = routing.get("multi_model_enabled", True) # Default True in code
        pool = routing.get("multi_model_pool", None) or "full"

        if multi_enabled:
            if pool == "lightweight-speed":
                print("Model: [MULTI] BGE-M3 + gte-modernbert (1.65GB total)")
            else:
                print("Model: [MULTI] BGE-Code-v1 + Qwen3 (6.3GB total)")
            print(f"       Active routing - {pool} pool")
        else:
            # Single model lookup
            spec = MODEL_REGISTRY.get(model_name, {"dim": "?", "vram": "?", "short": model_name})
            short_name = spec.get("short", model_name.split("/")[-1])
            print(f"Model: [SINGLE] {short_name} ({spec['dim']}d, {spec['vram']})")
            print("Tip: Press M for Quick Model Switch")

        # -- Reranker Status --
        reranker_enabled = reranker.get("enabled", True)
        if reranker_enabled:
            r_name = reranker.get("model_name", "BAAI/bge-reranker-v2-m3")
            print(f"       Reranker: {r_name.split('/')[-1]} (enabled)")
        else:
            print("       Reranker: Disabled")

        print()

        # -- RAM Fallback --
        ram_fallback = performance.get("allow_ram_fallback", False)
        # Handle legacy key allow_shared_memory if allow_ram_fallback missing
        if "allow_ram_fallback" not in performance and "allow_shared_memory" in performance:
            ram_fallback = performance["allow_shared_memory"]
            
        print(f"RAM Fallback: {'On' if ram_fallback else 'Off'}")

        # -- Output Format --
        out_fmt = output.get("format", "compact")
        print(f"Output Format: {out_fmt}")

        # 2. Load Project Selection
        sel_path = get_selection_path()
        project_info = "None (use option 5 to select)"
        
        if sel_path.exists():
            try:
                with open(sel_path, "r", encoding="utf-8") as f:
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
            except:
                print(f"Current Project: {project_info}")
        else:
            print(f"Current Project: {project_info}")

    except Exception as e:
        print(f"Status Error: {e}")

if __name__ == "__main__":
    main()
