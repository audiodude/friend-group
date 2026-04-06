"""Last.fm — music listening history (no API key needed for public profiles)."""

import hashlib
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Last.fm"
DESCRIPTION = "Last.fm profile (e.g. https://www.last.fm/user/username)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    return "last.fm" in parsed.netloc and "/user/" in parsed.path


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    # /user/username
    username = parsed.path.split("/user/")[-1].strip("/")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"lastfm:{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached Last.fm data for {username}")
        return cache_file.read_text()

    print(f"  Fetching Last.fm {username}...")
    parts = [f"Last.fm: {username}"]

    def _scrape(path: str) -> str:
        try:
            req = urllib.request.Request(
                f"https://www.last.fm/user/{username}{path}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return ""

    # Top artists (all time)
    html = _scrape("/library/artists?date_preset=ALL")
    artists = re.findall(r'class="link-block-target"[^>]*>([^<]+)</a>', html)
    # Filter out non-artist noise
    artists = [a.strip() for a in artists if a.strip() and len(a.strip()) > 1][:30]
    if artists:
        parts.append(f"\n--- Top artists (all time, {len(artists)}) ---")
        parts.extend(f"  {a}" for a in artists)

    # Recent tracks
    html = _scrape("/library")
    tracks = re.findall(
        r'class="chartlist-name"[^>]*>.*?<a[^>]*>([^<]+)</a>',
        html, re.DOTALL,
    )
    tracks = [t.strip() for t in tracks if t.strip()][:20]
    if tracks:
        parts.append(f"\n--- Recent tracks ---")
        parts.extend(f"  {t}" for t in tracks)

    print(f"  Got {len(artists)} top artists, {len(tracks)} recent tracks")
    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
