#!/usr/bin/env python3
"""
Manual MCP Server Configuration Script

This script directly edits the .claude.json file to configure the code-search MCP server.
This is more reliable than using the Claude CLI, which has known argument parsing issues.

Usage:
    python scripts/manual_configure.py [--global] [--project]

Options:
    --global    Configure for all projects (default, modifies ~/.claude.json)
    --project   Configure for current project only (modifies ./.claude.json)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class ClaudeConfigManager:
    """Manages Claude Code MCP server configuration."""

    def __init__(self, project_dir: Optional[Path] = None):
        """Initialize configuration manager."""
        self.project_dir = project_dir or Path.cwd()
        self.config_path: Optional[Path] = None

    def get_config_path(self, global_scope: bool = True) -> Path:
        """Get the path to the Claude configuration file."""
        if global_scope:
            # Global config in user's home directory
            home = Path.home()
            return home / ".claude.json"
        else:
            # Project-specific config
            return self.project_dir / ".claude.json"

    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load existing Claude configuration."""
        if not config_path.exists():
            print(f"[INFO] Config file not found: {config_path}")
            print("[INFO] Creating new configuration file...")
            return {}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"[OK] Loaded existing configuration from {config_path}")
            return config
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse config file: {e}")
            print("[WARNING] Creating backup and starting fresh...")
            backup_path = config_path.with_suffix('.json.backup')
            if config_path.exists():
                config_path.rename(backup_path)
                print(f"[OK] Backup created: {backup_path}")
            return {}
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            return {}

    def save_config(self, config: Dict[str, Any], config_path: Path) -> bool:
        """Save Claude configuration to file."""
        try:
            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write with proper formatting
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print(f"[OK] Configuration saved to {config_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")
            return False

    def create_mcp_server_config(
        self, command: str, args: list = None, env: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Create MCP server configuration structure."""
        config = {
            "type": "stdio",
            "command": command
        }

        if args:
            config["args"] = args

        if env:
            config["env"] = env

        return config

    def add_mcp_server(
        self,
        name: str,
        command: str,
        args: list = None,
        env: Dict[str, str] = None,
        global_scope: bool = True,
        force: bool = False
    ) -> bool:
        """Add or update MCP server configuration."""
        config_path = self.get_config_path(global_scope)
        self.config_path = config_path

        print(f"\n=== Claude Code MCP Manual Configuration ===")
        print(f"Server Name: {name}")
        print(f"Command: {command}")
        if args:
            print(f"Arguments: {' '.join(args)}")
        if env:
            print("Environment Variables:")
            for key, value in env.items():
                # Show truncated path for readability
                display_value = value if len(value) < 60 else f"{value[:57]}..."
                print(f"  {key}: {display_value}")
        print(f"Config File: {config_path}")
        print(f"Scope: {'Global (all projects)' if global_scope else 'Project-specific'}")
        print()

        # Load existing config
        config = self.load_config(config_path)

        # Ensure mcpServers exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Check if server already exists
        if name in config["mcpServers"] and not force:
            print(f"[WARNING] MCP server '{name}' already exists")
            print("Current configuration:")
            current = config["mcpServers"][name]
            print(f"  Command: {current.get('command', 'N/A')}")
            if current.get('args'):
                print(f"  Args: {' '.join(current['args'])}")
            if current.get('env'):
                print(f"  Environment variables: {len(current['env'])} set")
            print()

            response = input("Update configuration? (y/N): ").strip().lower()
            if response != 'y':
                print("[INFO] Configuration unchanged")
                return False

        # Create server config
        server_config = self.create_mcp_server_config(command, args, env)

        # Add/update server
        config["mcpServers"][name] = server_config

        # Save config
        if self.save_config(config, config_path):
            print("\n[SUCCESS] MCP server configuration added!")
            print()
            print("Next steps:")
            print("  1. Restart Claude Code")
            print(f"  2. Verify with: /mcp")
            print(f"  3. Test with: /search_code \"test query\"")
            print()
            return True
        else:
            return False

    def validate_config(self, config_path: Optional[Path] = None) -> bool:
        """Validate the configuration file."""
        if config_path is None:
            config_path = self.config_path

        if not config_path or not config_path.exists():
            print(f"[ERROR] Config file not found: {config_path}")
            return False

        config = self.load_config(config_path)

        if "mcpServers" not in config:
            print("[WARNING] No mcpServers section found")
            return False

        if "code-search" not in config["mcpServers"]:
            print("[WARNING] code-search server not configured")
            return False

        server = config["mcpServers"]["code-search"]

        print("\n=== Configuration Validation ===")
        validation_passed = True

        # Check required fields
        if not server.get("command"):
            print("[ERROR] Missing 'command' field")
            validation_passed = False
        else:
            print(f"[OK] Command: {server['command']}")

        if not server.get("env"):
            print("[WARNING] Missing 'env' field - environment variables not set")
        else:
            env = server["env"]
            if "PYTHONPATH" in env:
                print(f"[OK] PYTHONPATH: {env['PYTHONPATH']}")
            else:
                print("[WARNING] PYTHONPATH not set")

            if "PYTHONUNBUFFERED" in env:
                print(f"[OK] PYTHONUNBUFFERED: {env['PYTHONUNBUFFERED']}")
            else:
                print("[WARNING] PYTHONUNBUFFERED not set")

        if validation_passed:
            print("\n[OK] Configuration is valid!")
        else:
            print("\n[ERROR] Configuration has errors")

        return validation_passed


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manually configure Claude Code MCP server"
    )
    parser.add_argument(
        "--global",
        dest="global_scope",
        action="store_true",
        default=True,
        help="Configure globally for all projects (default)"
    )
    parser.add_argument(
        "--project",
        dest="project_scope",
        action="store_true",
        help="Configure for current project only"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update without confirmation"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing configuration"
    )

    args = parser.parse_args()

    # Determine scope
    global_scope = not args.project_scope

    # Get project directory
    script_dir = Path(__file__).parent.parent
    project_dir = script_dir.resolve()

    print("\n=================================================")
    print("Claude Code MCP Manual Configuration Tool")
    print("=================================================\n")
    print(f"Project Directory: {project_dir}")

    # Initialize manager
    manager = ClaudeConfigManager(project_dir)

    # Validate only mode
    if args.validate_only:
        config_path = manager.get_config_path(global_scope)
        manager.validate_config(config_path)
        return

    # Determine paths
    wrapper_script = project_dir / "scripts" / "batch" / "mcp_server_wrapper.bat"
    python_path = project_dir / ".venv" / "Scripts" / "python.exe"

    # Validate paths exist
    if not wrapper_script.exists():
        print(f"[ERROR] Wrapper script not found: {wrapper_script}")
        sys.exit(1)

    if not python_path.exists():
        print(f"[WARNING] Python executable not found: {python_path}")
        print("[INFO] Proceeding with wrapper script method...")

    # Setup configuration
    command = str(wrapper_script)
    args_list = []
    env_vars = {
        "PYTHONPATH": str(project_dir),
        "PYTHONUNBUFFERED": "1"
    }

    # Add server
    success = manager.add_mcp_server(
        name="code-search",
        command=command,
        args=args_list,
        env=env_vars,
        global_scope=global_scope,
        force=args.force
    )

    if success:
        # Validate after configuration
        manager.validate_config()
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
