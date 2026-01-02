"""Notify running MCP server of config/state changes.

This module provides HTTP-based notifications to the running MCP server
for UI operations that need to sync state in real-time.

Usage:
    python notify_server.py reload_config
    python notify_server.py switch_project <path>
"""

import sys

try:
    import requests
except ImportError:
    print("[ERROR] requests package not found. Install with: pip install requests")
    sys.exit(1)


def notify_config_reload(port: int = 8765) -> bool:
    """Tell running MCP server to reload config from search_config.json.

    Args:
        port: MCP server HTTP port (default: 8765 for SSE mode)

    Returns:
        True if server reloaded config successfully, False otherwise
    """
    try:
        response = requests.post(f"http://localhost:{port}/reload_config", timeout=5)
        if response.status_code == 200:
            result = response.json()
            print("[OK] Server config reloaded successfully")
            if "config" in result:
                cfg = result["config"]
                print(f"    Search mode: {cfg.get('search_mode')}")
                print(
                    f"    BM25/Dense weights: {cfg.get('bm25_weight')}/{cfg.get('dense_weight')}"
                )
                print(f"    Entity tracking: {cfg.get('entity_tracking')}")
                print(f"    Reranker: {cfg.get('reranker_enabled')}")
            return True
        else:
            print(
                f"[ERROR] Server returned status {response.status_code}: {response.text}"
            )
            return False
    except requests.exceptions.ConnectionError:
        print("[INFO] MCP server not running (SSE mode)")
        print("[INFO] Config changes will apply on next server start")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to notify server: {e}")
        return False


def notify_project_switch(project_path: str, port: int = 8765) -> bool:
    """Tell running MCP server to switch project.

    Args:
        project_path: Absolute path to project directory
        port: MCP server HTTP port (default: 8765 for SSE mode)

    Returns:
        True if server switched project successfully, False otherwise
    """
    try:
        response = requests.post(
            f"http://localhost:{port}/switch_project",
            json={"project_path": project_path},
            timeout=5,
        )
        if response.status_code == 200:
            result = response.json()
            print("[OK] Server switched project successfully")
            print(f"    Project: {result.get('project')}")
            print(f"    Indexed: {result.get('indexed')}")
            return True
        else:
            print(
                f"[ERROR] Server returned status {response.status_code}: {response.text}"
            )
            return False
    except requests.exceptions.ConnectionError:
        print("[INFO] MCP server not running (SSE mode)")
        print("[INFO] Project switch will apply on next server start")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to notify server: {e}")
        return False


def main() -> int:
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: notify_server.py <command> [args]")
        print()
        print("Commands:")
        print("  reload_config             Reload search_config.json in running server")
        print("  switch_project <path>     Switch active project in running server")
        print()
        print("Note: Only works with SSE mode (default port 8765)")
        return 1

    command = sys.argv[1]

    if command == "reload_config":
        success = notify_config_reload()
        return 0 if success else 1

    elif command == "switch_project":
        if len(sys.argv) < 3:
            print("[ERROR] switch_project requires project path argument")
            print("Usage: notify_server.py switch_project <path>")
            return 1

        project_path = sys.argv[2]
        success = notify_project_switch(project_path)
        return 0 if success else 1

    else:
        print(f"[ERROR] Unknown command: {command}")
        print("Valid commands: reload_config, switch_project")
        return 1


if __name__ == "__main__":
    sys.exit(main())
