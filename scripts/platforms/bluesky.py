"""Bluesky (AT Protocol)."""

import hashlib
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Bluesky"
DESCRIPTION = "Bluesky profile (e.g. https://bsky.app/profile/user.bsky.social)"

API = "https://public.api.bsky.app"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc == "bsky.app" and "/profile/" in parsed.path


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    # /profile/handle.bsky.social
    handle = parsed.path.split("/profile/")[-1].strip("/")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"bluesky:{handle}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached Bluesky posts for {handle}")
        return cache_file.read_text()

    print(f"  Fetching Bluesky @{handle}...")

    # Get profile
    try:
        profile_url = f"{API}/xrpc/app.bsky.actor.getProfile?actor={handle}"
        with urllib.request.urlopen(profile_url, timeout=10) as resp:
            profile = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Profile fetch failed: {e}")
        return ""

    parts = [f"Bluesky: @{handle}"]
    if profile.get("displayName"):
        parts.append(f"Name: {profile['displayName']}")
    if profile.get("description"):
        parts.append(f"Bio: {profile['description']}")

    # Get posts
    posts = []
    cursor = None
    for _ in range(3):
        feed_url = f"{API}/xrpc/app.bsky.feed.getAuthorFeed?actor={handle}&limit=50"
        if cursor:
            feed_url += f"&cursor={cursor}"
        try:
            with urllib.request.urlopen(feed_url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except Exception:
            break
        for item in data.get("feed", []):
            post = item.get("post", {}).get("record", {})
            text = post.get("text", "").strip()
            if text:
                posts.append(text)
        cursor = data.get("cursor")
        if not cursor:
            break

    print(f"  Got {len(posts)} posts")
    parts.append(f"\n--- Posts ({len(posts)}) ---")
    parts.extend(posts)

    result = "\n\n".join(parts)[:30000]
    cache_file.write_text(result)
    return result
