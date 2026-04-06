"""Hacker News — comments and submissions via Algolia API."""

import hashlib
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Hacker News"
DESCRIPTION = "HN profile (e.g. https://news.ycombinator.com/user?id=username)"

API = "https://hn.algolia.com/api/v1"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    return "ycombinator.com" in parsed.netloc and "user" in parsed.path


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    # /user?id=username
    from urllib.parse import parse_qs
    qs = parse_qs(parsed.query)
    username = qs.get("id", [""])[0]
    if not username:
        return ""

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"hn:{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached HN data for {username}")
        return cache_file.read_text()

    print(f"  Fetching HN @{username}...")
    parts = [f"Hacker News: {username}"]

    # Get user info
    try:
        req = urllib.request.Request(
            f"https://hacker-news.firebaseio.com/v0/user/{username}.json",
            headers={"User-Agent": "friend-group/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            user = json.loads(resp.read().decode())
        if user.get("about"):
            import re
            about = re.sub(r'<[^>]+>', '', user["about"])
            parts.append(f"About: {about}")
        parts.append(f"Karma: {user.get('karma', 0)}")
    except Exception:
        pass

    # Get recent comments via Algolia
    try:
        search_url = f"{API}/search?tags=comment,author_{username}&hitsPerPage=100"
        req = urllib.request.Request(search_url, headers={"User-Agent": "friend-group/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        comments = []
        for hit in data.get("hits", []):
            text = hit.get("comment_text", "").strip()
            if text:
                import re
                text = re.sub(r'<[^>]+>', '', text)[:300]
                comments.append(text)
        if comments:
            parts.append(f"\n--- Recent comments ({len(comments)}) ---")
            parts.extend(comments[:50])
    except Exception:
        pass

    # Get submissions
    try:
        search_url = f"{API}/search?tags=story,author_{username}&hitsPerPage=50"
        req = urllib.request.Request(search_url, headers={"User-Agent": "friend-group/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        stories = [h.get("title", "") for h in data.get("hits", []) if h.get("title")]
        if stories:
            parts.append(f"\n--- Submissions ({len(stories)}) ---")
            parts.extend(f"  {s}" for s in stories)
    except Exception:
        pass

    print(f"  Got profile + comments + submissions")
    result = "\n\n".join(parts)[:30000]
    cache_file.write_text(result)
    return result
