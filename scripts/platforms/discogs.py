"""Discogs — music collection."""

import hashlib
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Discogs"
DESCRIPTION = "Discogs profile (e.g. https://www.discogs.com/user/username)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    return "discogs.com" in parsed.netloc and "/user/" in parsed.path


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    username = parsed.path.split("/user/")[-1].strip("/")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"discogs:{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached Discogs data for {username}")
        return cache_file.read_text()

    print(f"  Fetching Discogs @{username}...")
    parts = [f"Discogs: {username}"]
    headers = {"User-Agent": "friend-group/1.0"}

    # Fetch collection (first 100 items)
    try:
        api_url = (
            f"https://api.discogs.com/users/{username}/collection/folders/0/releases"
            f"?per_page=100&sort=added&sort_order=desc"
        )
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        releases = data.get("releases", [])
        if releases:
            parts.append(f"\n--- Collection ({data.get('pagination', {}).get('items', len(releases))} total, showing {len(releases)}) ---")
            for r in releases:
                info = r.get("basic_information", {})
                artist = ", ".join(a.get("name", "?") for a in info.get("artists", []))
                title = info.get("title", "?")
                year = info.get("year", "")
                genres = ", ".join(info.get("genres", []))
                parts.append(f"  {artist} — {title} ({year}) [{genres}]")
    except Exception as e:
        print(f"  Collection fetch failed: {e}")
        # Fallback to wantlist
        pass

    # Wantlist
    try:
        api_url = f"https://api.discogs.com/users/{username}/wants?per_page=50"
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        wants = data.get("wants", [])
        if wants:
            parts.append(f"\n--- Wantlist ({len(wants)}) ---")
            for w in wants:
                info = w.get("basic_information", {})
                artist = ", ".join(a.get("name", "?") for a in info.get("artists", []))
                title = info.get("title", "?")
                parts.append(f"  {artist} — {title}")
    except Exception:
        pass

    print(f"  Got collection + wantlist")
    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
