"""Mastodon / Pleroma / Akkoma / any Mastodon-API-compatible instance."""

import hashlib
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Mastodon"
DESCRIPTION = "Mastodon profile (e.g. https://mastodon.social/@user)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not (path.startswith("@") and "/" not in path):
        return False
    # Verify it's actually a Mastodon-compatible instance
    try:
        check = f"https://{parsed.netloc}/api/v1/instance"
        req = urllib.request.Request(check, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    instance = parsed.netloc
    username = parsed.path.strip("/").lstrip("@")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"mastodon:{instance}/{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached posts for @{username}@{instance}")
        return cache_file.read_text()

    print(f"  Fetching @{username}@{instance}...")

    lookup_url = f"https://{instance}/api/v1/accounts/lookup?acct={username}"
    try:
        with urllib.request.urlopen(lookup_url, timeout=10) as resp:
            account = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Lookup failed: {e}")
        return ""

    account_id = account["id"]
    bio = re.sub(r'<[^>]+>', '', account.get("note", ""))

    parts = [f"Mastodon: @{username}@{instance}"]
    if account.get("display_name"):
        parts.append(f"Name: {account['display_name']}")
    if bio:
        parts.append(f"Bio: {bio}")

    posts = []
    max_id = None
    for _ in range(3):  # max 3 pages of 40
        api_url = (
            f"https://{instance}/api/v1/accounts/{account_id}/statuses"
            f"?limit=40&exclude_reblogs=true"
        )
        if max_id:
            api_url += f"&max_id={max_id}"
        try:
            with urllib.request.urlopen(api_url, timeout=10) as resp:
                statuses = json.loads(resp.read().decode())
        except Exception:
            break
        if not statuses:
            break
        for s in statuses:
            text = re.sub(r'<[^>]+>', '', s.get("content", "")).strip()
            if text:
                posts.append(text)
            max_id = s["id"]

    print(f"  Got {len(posts)} posts")
    parts.append(f"\n--- Posts ({len(posts)}) ---")
    parts.extend(posts)

    result = "\n\n".join(parts)[:30000]
    cache_file.write_text(result)
    return result
