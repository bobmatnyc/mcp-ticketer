#!/usr/bin/env python3
"""Check and release submodules with changes."""

import subprocess
import sys
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).parent.parent
SUBMODULES = {"py-mcp-installer": "src/services/py_mcp_installer"}


def has_changes(submodule_path: Path) -> bool:
    """Check if submodule has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=submodule_path,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def get_submodule_version(submodule_path: Path) -> str:
    """Get current version of submodule."""
    result = subprocess.run(
        ["python", "scripts/manage_version.py"],
        cwd=submodule_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def release_submodule(
    name: str, path: Path, bump_type: Literal["major", "minor", "patch"]
) -> str | None:
    """Release submodule if it has changes."""
    if not has_changes(path):
        print(f"ℹ️  {name}: No changes, skipping release")
        return None

    print(f"📦 {name}: Changes detected, releasing...")

    # Run release script
    result = subprocess.run(
        ["./scripts/release.sh", bump_type],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )

    # Get new version
    new_version = get_submodule_version(path)
    print(f"✅ {name}: Released v{new_version}")

    return new_version


def main():
    bump_type = sys.argv[1] if len(sys.argv) > 1 else "patch"

    print("🔍 Checking submodules for changes...")

    released = {}
    for name, rel_path in SUBMODULES.items():
        path = REPO_ROOT / rel_path
        if not path.exists():
            print(f"⚠️  {name}: Path not found, skipping")
            continue

        version = release_submodule(name, path, bump_type)
        if version:
            released[name] = version

    if released:
        print(f"\n✅ Released {len(released)} submodule(s):")
        for name, version in released.items():
            print(f"   - {name}: v{version}")

        # Update parent's submodule pointer
        print("\n📌 Updating parent submodule pointers...")
        subprocess.run(
            ["git", "add"] + [SUBMODULES[n] for n in released.keys()], check=True
        )
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "chore: update submodule versions\n\n"
                + "\n".join(f"- {n}: v{v}" for n, v in released.items()),
            ],
            check=True,
        )
        print("✅ Parent repo updated")
    else:
        print("\nℹ️  No submodules needed releasing")


if __name__ == "__main__":
    main()
