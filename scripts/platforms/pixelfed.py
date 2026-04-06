"""Pixelfed / Lemmy / any ActivityPub instance (Mastodon-compatible API)."""

import hashlib
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

NAME = "Pixelfed/Lemmy"
DESCRIPTION = "ActivityPub profile (e.g. https://pixelfed.social/@user, https://lemmy.world/u/user)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # Pixelfed: /@username or /username
    # Lemmy: /u/username
    if not path:
        return False

    # Skip known platforms handled by other plugins
    known = ["github.com", "bsky.app", "dev.to", "last.fm", "letterboxd.com",
             "goodreads.com", "steamcommunity.com", "bandcamp.com",
             "tumblr.com", "discogs.com", "news.ycombinator.com"]
    if any(k in parsed.netloc for k in known):
        return False

    # Check if it's a Mastodon-compatible API (but not already handled by mastodon.py)
    # mastodon.py handles /@user on mastodon instances; this catches pixelfed/lemmy/others
    if path.startswith("@") and "/" not in path:
        return False  # let mastodon.py handle it

    # Lemmy: /u/username
    if path.startswith("u/") and "/" not in path[2:]:
        try:
            check = f"https://{parsed.netloc}/api/v3/site"
            req = urllib.request.Request(check, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    # Pixelfed: /username (no @)
    if "/" not in path and not path.startswith("u/"):
        try:
            check = f"https://{parsed.netloc}/api/v1/instance"
            req = urllib.request.Request(check, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                # Pixelfed often has "pixelfed" in the version string
                return "pixelfed" in data.get("version", "").lower()
        except Exception:
            return False

    return False


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    instance = parsed.netloc
    path = parsed.path.strip("/")

    # Determine username
    if path.startswith("u/"):
        username = path[2:]
        platform = "Lemmy"
    else:
        username = path.lstrip("@")
        platform = "Pixelfed"

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"activitypub:{instance}/{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached {platform} data for {username}@{instance}")
        return cache_file.read_text()

    print(f"  Fetching {platform} @{username}@{instance}...")
    parts = [f"{platform}: @{username}@{instance}"]

    if platform == "Lemmy":
        # Lemmy API
        try:
            api_url = f"https://{instance}/api/v3/user?username={username}&limit=50"
            req = urllib.request.Request(api_url, headers={"User-Agent": "friend-group/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            person = data.get("person_view", {}).get("person", {})
            if person.get("bio"):
                parts.append(f"Bio: {person['bio']}")

            posts = data.get("posts", [])
            if posts:
                parts.append(f"\n--- Posts ({len(posts)}) ---")
                for p in posts:
                    post = p.get("post", {})
                    parts.append(f"  {post.get('name', '?')}")

            comments = data.get("comments", [])
            if comments:
                parts.append(f"\n--- Comments ({len(comments)}) ---")
                for c in comments[:30]:
                    text = c.get("comment", {}).get("content", "")[:200]
                    if text:
                        parts.append(f"  {text}")
        except Exception as e:
            print(f"  Lemmy fetch failed: {e}")
    else:
        # Mastodon-compatible API (Pixelfed)
        try:
            lookup_url = f"https://{instance}/api/v1/accounts/lookup?acct={username}"
            with urllib.request.urlopen(lookup_url, timeout=10) as resp:
                account = json.loads(resp.read().decode())

            if account.get("display_name"):
                parts.append(f"Name: {account['display_name']}")
            bio = re.sub(r'<[^>]+>', '', account.get("note", ""))
            if bio:
                parts.append(f"Bio: {bio}")

            account_id = account["id"]
            api_url = f"https://{instance}/api/v1/accounts/{account_id}/statuses?limit=40"
            with urllib.request.urlopen(api_url, timeout=10) as resp:
                statuses = json.loads(resp.read().decode())

            posts_text = []
            for s in statuses:
                text = re.sub(r'<[^>]+>', '', s.get("content", "")).strip()
                if text:
                    posts_text.append(text)
            if posts_text:
                parts.append(f"\n--- Posts ({len(posts_text)}) ---")
                parts.extend(posts_text)
        except Exception as e:
            print(f"  Pixelfed fetch failed: {e}")

    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
