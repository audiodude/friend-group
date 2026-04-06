"""Bandcamp — music collection/releases via scrape."""

import hashlib
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Bandcamp"
DESCRIPTION = "Bandcamp profile (e.g. https://username.bandcamp.com)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.endswith(".bandcamp.com")


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    username = parsed.netloc.replace(".bandcamp.com", "")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"bandcamp:{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached Bandcamp data for {username}")
        return cache_file.read_text()

    print(f"  Fetching Bandcamp {username}...")

    parts = [f"Bandcamp: {username}"]

    # Scrape main page for releases
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Failed: {e}")
        return ""

    # Extract album/track titles
    titles = re.findall(r'<p class="title">\s*(.+?)\s*</p>', html)
    if titles:
        parts.append("\n--- Releases ---")
        for t in titles[:30]:
            parts.append(f"  {t.strip()}")

    # Try collection page
    try:
        coll_url = f"https://bandcamp.com/{username}"
        req = urllib.request.Request(coll_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            coll_html = resp.read().decode("utf-8", errors="replace")
        coll_items = re.findall(
            r'class="collection-item-title">(.+?)</div>', coll_html
        )
        if coll_items:
            parts.append(f"\n--- Collection ({len(coll_items)} items) ---")
            for item in coll_items[:50]:
                parts.append(f"  {item.strip()}")
    except Exception:
        pass

    print(f"  Got {len(titles)} releases")
    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
