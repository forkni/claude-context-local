"""Patch server.py to add first-search messaging."""

import re
from pathlib import Path


def patch_first_search_messaging():
    """Add user-friendly first-search messaging to get_embedder function."""
    server_path = Path(__file__).parent.parent / "mcp_server" / "server.py"

    with open(server_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to find the lazy load section
    old_pattern = (
        r"        # Lazy load model if not already loaded\n"
        r"        if model_key not in _embedders or _embedders\[model_key\] is None:\n"
        r"            model_name = MODEL_POOL_CONFIG\[model_key\]\n"
        r'            logger\.info\(f"Lazy loading \{model_key\} \(\{model_name\}\)\.\.\."\)\n'
        r"            try:\n"
        r"                embedder = CodeEmbedder\(model_name=model_name, cache_dir=str\(cache_dir\)\)\n"
        r"                _embedders\[model_key\] = embedder\n"
        r"                state\.set_embedder\(model_key, embedder\)  # Sync to state\n"
        r'                logger\.info\(f"✓ \{model_key\} loaded successfully"\)'
    )

    new_text = """        # Lazy load model if not already loaded
        if model_key not in _embedders or _embedders[model_key] is None:
            model_name = MODEL_POOL_CONFIG[model_key]
            # Check if this is the first model being loaded (cold start)
            is_first_load = not any(_embedders.values())
            if is_first_load:
                logger.info(
                    f"[FIRST USE] Loading embedding model {model_key} ({model_name})... "
                    f"This is a one-time initialization (~5-10s). Subsequent searches will be fast."
                )
            else:
                logger.info(f"Lazy loading {model_key} ({model_name})...")
            try:
                embedder = CodeEmbedder(model_name=model_name, cache_dir=str(cache_dir))
                _embedders[model_key] = embedder
                state.set_embedder(model_key, embedder)  # Sync to state
                if is_first_load:
                    logger.info(f"✓ {model_key} loaded successfully. Ready for fast searches!")
                else:
                    logger.info(f"✓ {model_key} loaded successfully")"""

    # Replace
    content_new = re.sub(old_pattern, new_text, content, count=1)

    if content_new != content:
        with open(server_path, "w", encoding="utf-8") as f:
            f.write(content_new)
        print("[OK] Successfully added first-search messaging")
        return True
    else:
        print("[ERROR] Pattern not found - file may have changed")
        return False


if __name__ == "__main__":
    patch_first_search_messaging()
