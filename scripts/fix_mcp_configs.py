#!/usr/bin/env python3
"""Fix MCP configurations across all projects on this machine.

This script:
1. Scans all projects for .mcp.json and .mcp-ticketer/config.json
2. Ensures consistent GitHub tokens across all configs
3. Adds mcp-ticketer MCP server to projects that have ticketer configs
4. Updates kuzu-memory configs with correct project paths
5. Ensures mcp-vector-search points to correct project

Usage:
    python scripts/fix_mcp_configs.py --dry-run   # Preview changes
    python scripts/fix_mcp_configs.py             # Apply changes
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


# Configuration constants
PROJECTS_DIR = Path("/Users/masa/Projects")
CLIENTS_DIR = Path("/Users/masa/Clients")

# The canonical GitHub token to use everywhere
CANONICAL_GITHUB_TOKEN = "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"

# Projects that should have mcp-ticketer configured
TICKETER_PROJECTS = {
    "claude-mpm": {"adapter": "github", "owner": "bobmatnyc", "repo": "claude-mpm"},
    "mcp-ticketer": {
        "adapter": "linear",
        "team_key": "1M",
        "default_epic": "eac28953c267",
    },
    "kuzu-memory": {"adapter": "github", "owner": "bobmatnyc", "repo": "kuzu-memory"},
    "mcp-vector-search": {
        "adapter": "github",
        "owner": "bobmatnyc",
        "repo": "mcp-vector-search",
    },
}


def load_json(path: Path) -> dict[str, Any] | None:
    """Load JSON file, return None if not found or invalid."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_json(path: Path, data: dict[str, Any], dry_run: bool = False) -> bool:
    """Save JSON file with pretty formatting."""
    if dry_run:
        print(f"  [DRY-RUN] Would write to {path}")
        return True

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"  [SAVED] {path}")
        return True
    except Exception as e:
        print(f"  [ERROR] Could not save {path}: {e}")
        return False


def fix_parent_mcp_json(dry_run: bool = False) -> None:
    """Fix the parent /Users/masa/Projects/.mcp.json with canonical settings."""
    print("\n=== Fixing Parent .mcp.json ===")

    mcp_json_path = PROJECTS_DIR / ".mcp.json"

    config = {
        "mcpServers": {
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": CANONICAL_GITHUB_TOKEN},
            },
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    str(PROJECTS_DIR),
                ],
            },
        }
    }

    existing = load_json(mcp_json_path)
    if existing != config:
        print(f"  Updating {mcp_json_path}")
        save_json(mcp_json_path, config, dry_run)
    else:
        print(f"  {mcp_json_path} is already correct")


def create_standard_mcp_json(project_path: Path, project_name: str) -> dict[str, Any]:
    """Create a standard .mcp.json for a project."""
    config: dict[str, Any] = {"mcpServers": {}}

    # All projects get kuzu-memory with project-specific paths
    config["mcpServers"]["kuzu-memory"] = {
        "type": "stdio",
        "command": "kuzu-memory",
        "args": ["mcp"],
        "env": {
            "KUZU_MEMORY_PROJECT_ROOT": str(project_path),
            "KUZU_MEMORY_DB": str(project_path / "kuzu-memories"),
        },
    }

    # All projects get mcp-vector-search (points to current project)
    config["mcpServers"]["mcp-vector-search"] = {
        "type": "stdio",
        "command": "uv",
        "args": ["run", "mcp-vector-search", "mcp"],
        "env": {"MCP_ENABLE_FILE_WATCHING": "true"},
    }

    # Projects with ticketer config get mcp-ticketer
    ticketer_config_path = project_path / ".mcp-ticketer" / "config.json"
    if ticketer_config_path.exists() or project_name in TICKETER_PROJECTS:
        config["mcpServers"]["mcp-ticketer"] = {
            "type": "stdio",
            "command": "mcp-ticketer",
            "args": ["mcp", "--path", str(project_path)],
            "env": {},
        }

    return config


def fix_project_mcp_json(project_path: Path, dry_run: bool = False) -> None:
    """Fix .mcp.json for a specific project."""
    project_name = project_path.name
    mcp_json_path = project_path / ".mcp.json"

    existing = load_json(mcp_json_path)
    standard = create_standard_mcp_json(project_path, project_name)

    if existing is None:
        print(f"  Creating {mcp_json_path}")
        save_json(mcp_json_path, standard, dry_run)
    elif existing != standard:
        # Merge: keep existing servers, update standard ones
        merged = {"mcpServers": {}}

        # Start with existing servers
        if existing.get("mcpServers"):
            merged["mcpServers"] = existing["mcpServers"].copy()

        # Update/add standard servers
        for server_name, server_config in standard["mcpServers"].items():
            merged["mcpServers"][server_name] = server_config

        print(f"  Updating {mcp_json_path}")
        save_json(mcp_json_path, merged, dry_run)
    else:
        print(f"  {mcp_json_path} is already correct")


def fix_ticketer_config(project_path: Path, dry_run: bool = False) -> None:
    """Fix .mcp-ticketer/config.json for a project."""
    project_name = project_path.name
    config_path = project_path / ".mcp-ticketer" / "config.json"

    existing = load_json(config_path)
    if existing is None:
        # Check if this project should have a ticketer config
        if project_name in TICKETER_PROJECTS:
            print(f"  Creating ticketer config for {project_name}")
            settings = TICKETER_PROJECTS[project_name]

            if settings["adapter"] == "github":
                config = {
                    "default_adapter": "github",
                    "adapters": {
                        "github": {
                            "adapter": "github",
                            "enabled": True,
                            "token": CANONICAL_GITHUB_TOKEN,
                            "owner": settings["owner"],
                            "repo": settings["repo"],
                            "project_id": f"{settings['owner']}/{settings['repo']}",
                            "additional_config": {},
                        }
                    },
                    "default_user": "bobmatnyc",
                }
            elif settings["adapter"] == "linear":
                config = {
                    "default_adapter": "linear",
                    "adapters": {
                        "linear": {
                            "adapter": "linear",
                            "enabled": True,
                            "team_key": settings["team_key"],
                            "additional_config": {},
                        }
                    },
                    "default_epic": settings.get("default_epic"),
                }
            else:
                return

            save_json(config_path, config, dry_run)
        return

    # Update existing config with canonical token
    modified = False

    if "adapters" in existing:
        for adapter_name, adapter_config in existing["adapters"].items():
            if adapter_name == "github" and isinstance(adapter_config, dict):
                if (
                    adapter_config.get("token")
                    and adapter_config["token"] != CANONICAL_GITHUB_TOKEN
                ):
                    print(f"  Updating GitHub token in {config_path}")
                    adapter_config["token"] = CANONICAL_GITHUB_TOKEN
                    modified = True

    if modified:
        save_json(config_path, existing, dry_run)
    else:
        print(f"  {config_path} is OK (or doesn't have GitHub adapter)")


def scan_and_fix_projects(base_dir: Path, dry_run: bool = False) -> None:
    """Scan and fix all projects in a directory."""
    if not base_dir.exists():
        print(f"  Directory not found: {base_dir}")
        return

    for project_path in sorted(base_dir.iterdir()):
        if not project_path.is_dir():
            continue
        if project_path.name.startswith("."):
            continue

        # Check if this looks like a project (has some code files or configs)
        has_indicators = any(
            [
                (project_path / ".git").exists(),
                (project_path / "pyproject.toml").exists(),
                (project_path / "package.json").exists(),
                (project_path / ".mcp.json").exists(),
                (project_path / ".mcp-ticketer").exists(),
            ]
        )

        if not has_indicators:
            continue

        print(f"\n--- {project_path.name} ---")
        fix_project_mcp_json(project_path, dry_run)
        fix_ticketer_config(project_path, dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix MCP configurations across projects"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("MCP Configuration Fixer")
    print("=" * 60)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    # Fix parent .mcp.json
    fix_parent_mcp_json(args.dry_run)

    # Fix projects
    print("\n=== Scanning Projects ===")
    scan_and_fix_projects(PROJECTS_DIR, args.dry_run)

    # Fix client projects
    print("\n=== Scanning Client Projects ===")
    if CLIENTS_DIR.exists():
        for client_dir in sorted(CLIENTS_DIR.iterdir()):
            if client_dir.is_dir() and not client_dir.name.startswith("."):
                projects_dir = client_dir / "projects"
                if projects_dir.exists():
                    print(f"\n  Client: {client_dir.name}")
                    scan_and_fix_projects(projects_dir, args.dry_run)

    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE - Run without --dry-run to apply changes")
    else:
        print("CONFIGURATION FIX COMPLETE")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
