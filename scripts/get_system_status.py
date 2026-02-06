import sys
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp_server.project_persistence import get_selection_for_display
    from search.config import MODEL_REGISTRY, get_search_config
except ImportError:
    # Fallback if dependencies aren't ready yet
    print("Runtime: Python | Status: Modules not ready")
    sys.exit(0)


def main():
    try:
        # Load Config
        cfg = get_search_config()

        # --- Model Status ---
        model = cfg.embedding.model_name
        specs = MODEL_REGISTRY.get(model, {})
        model_short = model.split("/")[-1]
        dim = specs.get("dimension", 768)
        vram = specs.get("vram_gb", "?")
        multi_enabled = cfg.routing.multi_model_enabled
        pool = cfg.routing.multi_model_pool or "full"

        if multi_enabled:
            if pool == "lightweight-speed":
                print("Model: [MULTI] BGE-M3 + gte-modernbert (1.65GB total)")
            else:
                print("Model: [MULTI] BGE-Code-v1 + Qwen3 (6.3GB total)")
            print(f"       Active routing - {pool} pool")
        else:
            print(f"Model: [SINGLE] {model_short} ({dim}d, {vram})")
            print("Tip: Press M for Quick Model Switch")

        # --- Reranker Status ---
        if cfg.reranker.enabled:
            reranker_model = cfg.reranker.model_name.split("/")[-1]
            print(f"       Reranker: {reranker_model} (enabled)")
        else:
            print("       Reranker: Disabled")

        print()  # Separator

        # --- RAM Fallback ---
        ram_fallback = "On" if cfg.performance.allow_ram_fallback else "Off"
        print(f"RAM Fallback: {ram_fallback}")

        # --- Output Format ---
        print(f"Output Format: {cfg.output.format}")

        # --- Current Project ---
        info = get_selection_for_display()
        if not info["exists"]:
            print("Current Project: None (use option 5 to select)")
        else:
            name = info["name"]
            path = info["path"]
            # Truncate path if > 50 chars
            if len(path) > 50:
                path = "..." + path[-47:]
            print(f"Current Project: {name}")
            print(f"                 ({path})")

    except Exception as e:
        print(f"Error getting system status: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
