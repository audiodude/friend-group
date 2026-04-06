#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "anthropic>=0.40.0",
#     "pyyaml>=6.0",
# ]
# ///
"""Add a new friend to an existing friend group.

Run from the project directory:
    uv run scripts/make_new_friend.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (
    get_client, get_paths, resolve_project_dir,
    load_or_create_profile, run_selection_loop,
    generate_souls_for_selected, create_friend_dir,
    get_existing_friend_names, collect_bot_token,
)


def main():
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║   Friend Group — New Friend          ║")
    print("  ╚══════════════════════════════════════╝")

    root = resolve_project_dir()
    paths = get_paths(root)

    if not (root / "src" / "main.py").exists():
        print("  Error: Not in a friend-group project directory.")
        print("  Run initialize.py first, or cd into the project.")
        sys.exit(1)

    client = get_client(paths["env"])
    if not client:
        print("  Error: No Anthropic API key found in .env")
        sys.exit(1)

    profile = load_or_create_profile(client, paths)
    if not profile:
        print("  Error: No PROFILE.md found. Run initialize.py first.")
        sys.exit(1)

    existing = get_existing_friend_names(paths["friends"])
    if existing:
        print(f"\n  Current friends: {', '.join(existing)}")

    selected = run_selection_loop(
        client, profile,
        existing_friends=existing,
    )

    if selected is None:
        print("  Cancelled.")
        return

    print(f"\n  Selected {len(selected)} new friends:")
    for c in selected:
        print(f"    {c['name']} — {c['vibe']}")

    souls = generate_souls_for_selected(
        client, selected, profile, paths["friends"],
    )

    print()
    for c in selected:
        slug = create_friend_dir(paths["friends"], c["name"],
                                  souls[c["name"]], c)
        print(f"  Created friends/{slug}/")

    # Collect tokens
    print()
    for c in selected:
        token = collect_bot_token(paths["env"], c["name"])
        if token is None:
            slug = c["name"].lower().replace(" ", "_")
            print(f"\n  Skipped token for {c['name']}.")
            print(f"  Set TELEGRAM_BOT_TOKEN_{slug.upper()} in .env later.")

    print()
    print("  Don't forget to:")
    print("    - /setprivacy > Disable for new bots")
    print("    - Add new bots to the Telegram group")
    print("    - Redeploy or restart the app")
    print()


if __name__ == "__main__":
    main()
