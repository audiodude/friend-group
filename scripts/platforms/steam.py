"""Steam — game library (public profiles only)."""

import hashlib
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Steam"
DESCRIPTION = "Steam profile (e.g. https://steamcommunity.com/id/username)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    return "steamcommunity.com" in parsed.netloc and (
        "/id/" in parsed.path or "/profiles/" in parsed.path
    )


def fetch(url: str, cache_dir: Path) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"steam:{url}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached Steam data")
        return cache_file.read_text()

    print(f"  Fetching Steam profile...")
    parts = [f"Steam: {url}"]

    # Scrape the profile page
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Failed: {e}")
        return ""

    # Username
    name_match = re.search(r'class="actual_persona_name">(.+?)</span>', html)
    if name_match:
        parts.append(f"Name: {name_match.group(1).strip()}")

    # Summary
    summary_match = re.search(
        r'class="profile_summary"[^>]*>(.+?)</div>', html, re.DOTALL
    )
    if summary_match:
        summary = re.sub(r'<[^>]+>', '', summary_match.group(1)).strip()
        if summary:
            parts.append(f"Summary: {summary}")

    # Scrape games page
    games_url = url.rstrip("/") + "/games/?tab=all"
    try:
        req = urllib.request.Request(games_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            games_html = resp.read().decode("utf-8", errors="replace")

        # Extract from the JavaScript rgGames array
        games_match = re.search(r'var rgGames = (\[.+?\]);', games_html, re.DOTALL)
        if games_match:
            import json
            games = json.loads(games_match.group(1))
            # Sort by hours played
            games.sort(key=lambda g: g.get("hours_forever", "0").replace(",", ""),
                       reverse=True)
            parts.append(f"\n--- Games ({len(games)} total, sorted by playtime) ---")
            for g in games[:40]:
                name = g.get("name", "?")
                hours = g.get("hours_forever", "0")
                parts.append(f"  {name}: {hours}h")
    except Exception:
        # Fallback: scrape game names from profile
        game_names = re.findall(r'class="game_name"[^>]*>(.+?)</a>', html)
        if game_names:
            parts.append(f"\n--- Games ({len(game_names)}) ---")
            parts.extend(f"  {g.strip()}" for g in game_names[:40])

    print(f"  Got Steam profile + games")
    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
