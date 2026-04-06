"""Tumblr — posts via RSS."""

import hashlib
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Tumblr"
DESCRIPTION = "Tumblr blog (e.g. https://username.tumblr.com)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.endswith(".tumblr.com")


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    username = parsed.netloc.replace(".tumblr.com", "")

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"tumblr:{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached Tumblr data for {username}")
        return cache_file.read_text()

    print(f"  Fetching Tumblr @{username}...")
    parts = [f"Tumblr: {username}"]

    rss_url = f"https://{username}.tumblr.com/rss"
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  RSS failed: {e}")
        return ""

    # Extract titles and descriptions
    titles = re.findall(r"<title><!\[CDATA\[(.+?)\]\]></title>", xml)
    descriptions = re.findall(
        r"<description><!\[CDATA\[(.+?)\]\]></description>", xml, re.DOTALL
    )

    posts = []
    for i in range(min(len(titles) - 1, len(descriptions) - 1)):
        title = titles[i + 1].strip()  # skip channel title
        desc = re.sub(r'<[^>]+>', '', descriptions[i + 1]).strip()[:300]
        if title:
            posts.append(f"  {title}: {desc}" if desc else f"  {title}")
        elif desc:
            posts.append(f"  {desc}")

    if posts:
        parts.append(f"\n--- Recent posts ({len(posts)}) ---")
        parts.extend(posts)

    print(f"  Got {len(posts)} posts")
    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
