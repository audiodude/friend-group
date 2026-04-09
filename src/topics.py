"""Track recently discussed topics to prevent repetition."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from .config import DATA_DIR

logger = logging.getLogger(__name__)

TOPICS_PATH = DATA_DIR / "RECENT_TOPICS.md"
TOPIC_TTL_HOURS = 24


def record_topic(sender: str, topic: str):
    """Append a topic to the rolling log."""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
    line = f"{timestamp} {sender}: {topic}\n"
    with open(TOPICS_PATH, "a") as f:
        f.write(line)
    logger.debug(f"Recorded topic: {sender} — {topic}")


def get_recent_topics() -> str:
    """Return recent topics as a string for prompt injection. Prunes stale entries."""
    if not TOPICS_PATH.exists():
        return ""

    lines = TOPICS_PATH.read_text().strip().split("\n")
    lines = [l for l in lines if l.strip()]

    if not lines:
        return ""

    cutoff = datetime.now() - timedelta(hours=TOPIC_TTL_HOURS)
    fresh = []
    for line in lines:
        try:
            ts_str = line.split(" ", 1)[0]
            ts = datetime.fromisoformat(ts_str)
            if ts > cutoff:
                fresh.append(line)
        except (ValueError, IndexError):
            continue

    # Rewrite file with only fresh entries
    if len(fresh) != len(lines):
        TOPICS_PATH.write_text("\n".join(fresh) + "\n" if fresh else "")

    if not fresh:
        return ""

    return "\n".join(fresh)
