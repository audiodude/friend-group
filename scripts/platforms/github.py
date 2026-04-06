"""GitHub profile — repos, bio, languages."""

import hashlib
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "GitHub"
DESCRIPTION = "GitHub profile (e.g. https://github.com/username)"

API = "https://api.github.com"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc != "github.com":
        return False
    path = parsed.path.strip("/")
    # Must be just a username, not a repo (no second slash)
    return bool(path) and "/" not in path


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    username = parsed.path.strip("/")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"github:{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached GitHub data for {username}")
        return cache_file.read_text()

    print(f"  Fetching GitHub @{username}...")
    headers = {"User-Agent": "friend-group/1.0"}

    # Profile
    try:
        req = urllib.request.Request(f"{API}/users/{username}", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            user = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Failed: {e}")
        return ""

    parts = [f"GitHub: {username}"]
    if user.get("name"):
        parts.append(f"Name: {user['name']}")
    if user.get("bio"):
        parts.append(f"Bio: {user['bio']}")
    if user.get("location"):
        parts.append(f"Location: {user['location']}")
    if user.get("blog"):
        parts.append(f"Website: {user['blog']}")
    parts.append(f"Public repos: {user.get('public_repos', 0)}")

    # Repos (sorted by stars)
    try:
        req = urllib.request.Request(
            f"{API}/users/{username}/repos?sort=stars&per_page=30&type=owner",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            repos = json.loads(resp.read().decode())
    except Exception:
        repos = []

    if repos:
        parts.append("\n--- Top repositories ---")
        for r in repos[:20]:
            lang = r.get("language") or "?"
            stars = r.get("stargazers_count", 0)
            desc = r.get("description") or ""
            parts.append(f"  {r['name']} ({lang}, {stars}★): {desc}")

    # README (profile repo)
    try:
        req = urllib.request.Request(
            f"{API}/repos/{username}/{username}/readme",
            headers={**headers, "Accept": "application/vnd.github.v3.raw"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            readme = resp.read().decode("utf-8", errors="replace")[:3000]
        parts.append(f"\n--- Profile README ---\n{readme}")
    except Exception:
        pass

    print(f"  Got profile + {len(repos)} repos")
    result = "\n\n".join(parts)[:30000]
    cache_file.write_text(result)
    return result
