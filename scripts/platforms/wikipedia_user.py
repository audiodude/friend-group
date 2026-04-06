"""Wikipedia user page."""

import hashlib
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, unquote

NAME = "Wikipedia"
DESCRIPTION = "Wikipedia user page (e.g. https://en.wikipedia.org/wiki/User:Username)"


def detect(url: str) -> bool:
    parsed = urlparse(url)
    return "wikipedia.org" in parsed.netloc and "User:" in parsed.path


def fetch(url: str, cache_dir: Path) -> str:
    parsed = urlparse(url)
    # /wiki/User:Username
    path = unquote(parsed.path)
    username = path.split("User:")[-1].strip("/")
    lang = parsed.netloc.split(".")[0]  # en, de, etc.

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"wikipedia:{lang}:{username}".encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.txt"
    if cache_file.exists():
        print(f"  Using cached Wikipedia data for {username}")
        return cache_file.read_text()

    print(f"  Fetching Wikipedia User:{username}...")
    parts = [f"Wikipedia user: {username} ({lang}.wikipedia.org)"]

    # Get user page content via API
    api_url = (
        f"https://{lang}.wikipedia.org/w/api.php"
        f"?action=query&titles=User:{username}&prop=revisions"
        f"&rvprop=content&rvslots=main&format=json"
    )
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "friend-group/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                print("  User page doesn't exist")
                break
            revisions = page.get("revisions", [])
            if revisions:
                content = revisions[0].get("slots", {}).get("main", {}).get("*", "")
                if content:
                    # Strip wiki markup roughly
                    import re
                    content = re.sub(r'\{\{[^}]+\}\}', '', content)
                    content = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', content)
                    content = re.sub(r"'{2,}", '', content)
                    parts.append(f"\n--- User page ---\n{content[:5000]}")
    except Exception as e:
        print(f"  Failed: {e}")

    # Get user contributions summary
    try:
        contrib_url = (
            f"https://{lang}.wikipedia.org/w/api.php"
            f"?action=query&list=usercontribs&ucuser={username}"
            f"&uclimit=50&ucprop=title|comment&format=json"
        )
        req = urllib.request.Request(contrib_url, headers={"User-Agent": "friend-group/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        contribs = data.get("query", {}).get("usercontribs", [])
        if contribs:
            # Get unique articles edited
            articles = list(dict.fromkeys(c["title"] for c in contribs))
            parts.append(f"\n--- Recent edits ({len(articles)} articles) ---")
            parts.extend(f"  {a}" for a in articles)
    except Exception:
        pass

    print(f"  Got user page + contributions")
    result = "\n\n".join(parts)[:15000]
    cache_file.write_text(result)
    return result
