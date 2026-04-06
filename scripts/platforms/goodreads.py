"""Goodreads — reading taste via RSS feed."""

import hashlib
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Goodreads"
DESCRIPTION = "Goodreads profile (e.g. https://www.goodreads.com/user/show/12345-username)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    return "goodreads.com" in parsed.netloc and "/user/" in parsed.path


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    # /user/show/12345-username
    path = parsed.path.strip("/")
    user_id = ""
    for part in path.split("/"):
        if part and part[0].isdigit():
            user_id = part.split("-")[0]
            break

    if not user_id:
        print("  Could not extract Goodreads user ID from URL")
        return ""

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"goodreads:{user_id}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached Goodreads data")
        return cache_file.read_text()

    print(f"  Fetching Goodreads user {user_id}...")
    parts = [f"Goodreads user: {user_id}"]

    # Try RSS feed for recent reviews
    rss_url = f"https://www.goodreads.com/review/list_rss/{user_id}?shelf=read"
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  RSS fetch failed: {e}")
        # Fall back to scraping the profile page
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)[:10000]
            result = f"Goodreads profile (scraped):\n{text}"
            cache_file.write_text(result)
            return result
        except Exception:
            return ""

    titles = re.findall(r"<title><!\[CDATA\[(.+?)\]\]></title>", xml)
    # Extract author names
    authors = re.findall(r"<author_name>(.+?)</author_name>", xml)
    ratings = re.findall(r"<user_rating>(\d+)</user_rating>", xml)

    books = []
    for i, title in enumerate(titles[1:]):  # skip channel title
        author = authors[i] if i < len(authors) else "?"
        rating = f" ({ratings[i]}★)" if i < len(ratings) and ratings[i] != "0" else ""
        books.append(f"  {title} by {author}{rating}")

    if books:
        parts.append(f"\n--- Books read ({len(books)}) ---")
        parts.extend(books)

    print(f"  Got {len(books)} books")
    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
