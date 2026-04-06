"""Letterboxd — movie taste via RSS."""

import hashlib
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Letterboxd"
DESCRIPTION = "Letterboxd profile (e.g. https://letterboxd.com/username)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc != "letterboxd.com":
        return False
    path = parsed.path.strip("/")
    return bool(path) and "/" not in path


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    username = parsed.path.strip("/")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"letterboxd:{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached Letterboxd data for {username}")
        return cache_file.read_text()

    print(f"  Fetching Letterboxd @{username}...")

    rss_url = f"https://letterboxd.com/{username}/rss/"
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Failed: {e}")
        return ""

    parts = [f"Letterboxd: {username}"]

    # Parse RSS items (rough regex, no XML lib needed)
    titles = re.findall(r"<title><!\[CDATA\[(.+?)\]\]></title>", xml)
    descriptions = re.findall(r"<description><!\[CDATA\[(.+?)\]\]></description>", xml, re.DOTALL)

    entries = []
    for i, title in enumerate(titles[1:], start=1):  # skip channel title
        desc = ""
        if i < len(descriptions):
            desc = re.sub(r'<[^>]+>', '', descriptions[i]).strip()[:200]
        entries.append(f"  {title}: {desc}" if desc else f"  {title}")

    print(f"  Got {len(entries)} entries")
    parts.append(f"\n--- Recent activity ({len(entries)}) ---")
    parts.extend(entries)

    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
