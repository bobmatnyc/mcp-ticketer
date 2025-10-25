#!/usr/bin/env python3
"""
Test GitHub token permissions
"""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables
env_path = Path(".env.local")
if env_path.exists():
    load_dotenv(env_path)

token = os.getenv("GITHUB_TOKEN")
if not token:
    print("GITHUB_TOKEN not found!")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json",
}

# Test different endpoints
tests = [
    ("User info", "https://api.github.com/user"),
    ("Rate limit", "https://api.github.com/rate_limit"),
    ("Repo access", "https://api.github.com/repos/bobmatnyc/mcp-ticketer"),
    ("Issues access", "https://api.github.com/repos/bobmatnyc/mcp-ticketer/issues"),
]

print(f"Testing GitHub token: {token[:10]}...")
print()

with httpx.Client(headers=headers) as client:
    for name, url in tests:
        try:
            response = client.get(url)
            if response.status_code == 200:
                print(f"✓ {name}: Success")
                if name == "User info":
                    data = response.json()
                    print(f"  Authenticated as: {data.get('login', 'Unknown')}")
                elif name == "Rate limit":
                    data = response.json()
                    rate = data.get("rate", {})
                    print(
                        f"  API calls remaining: {rate.get('remaining', 0)}/{rate.get('limit', 0)}"
                    )
            else:
                print(f"✗ {name}: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print(f"✗ {name}: {e}")

print()
print("Token scopes needed for full functionality:")
print("  - repo (full control of private repositories)")
print("  - public_repo (access to public repositories)")
print("If tests failed, regenerate token with proper scopes at:")
print("  https://github.com/settings/tokens")
