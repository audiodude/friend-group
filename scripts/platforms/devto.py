"""dev.to — articles and profile."""

import hashlib
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "dev.to"
DESCRIPTION = "dev.to profile (e.g. https://dev.to/username)"

API = "https://dev.to/api"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc != "dev.to":
        return False
    path = parsed.path.strip("/")
    return bool(path) and "/" not in path


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    username = parsed.path.strip("/")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"devto:{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached dev.to data for {username}")
        return cache_file.read_text()

    print(f"  Fetching dev.to @{username}...")
    parts = [f"dev.to: {username}"]

    # User profile
    try:
        req = urllib.request.Request(
            f"{API}/users/by_username?url={username}",
            headers={"User-Agent": "friend-group/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            user = json.loads(resp.read().decode())
        if user.get("name"):
            parts.append(f"Name: {user['name']}")
        if user.get("summary"):
            parts.append(f"Bio: {user['summary']}")
        if user.get("location"):
            parts.append(f"Location: {user['location']}")
    except Exception:
        pass

    # Articles
    try:
        req = urllib.request.Request(
            f"{API}/articles?username={username}&per_page=30",
            headers={"User-Agent": "friend-group/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            articles = json.loads(resp.read().decode())

        if articles:
            parts.append(f"\n--- Articles ({len(articles)}) ---")
            for a in articles:
                tags = ", ".join(a.get("tag_list", []))
                parts.append(f"  {a['title']} [{tags}]")
                if a.get("description"):
                    parts.append(f"    {a['description'][:200]}")
    except Exception:
        pass

    print(f"  Got profile + articles")
    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
