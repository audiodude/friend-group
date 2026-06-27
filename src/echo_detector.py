"""Detect when a proposed message echoes phrasing from recent chat.

Multiple bots independently reading the same chat context often converge on
the same "obvious" phrasing ("sounds like she gets it" / "december gap").
This module flags those cases so the bot loop can drop them.
"""

import re


MIN_WORDS = 5
NGRAM_N = 3
THRESHOLD = 0.5
RECENT_MESSAGES_TO_CHECK = 15


def _normalize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s']", " ", text)
    return text.split()


def _ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    if len(words) < n:
        return set()
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


# Punctuation/whitespace stripped from the edges when checking for a bare name.
_NAME_EDGE_CHARS = ".,!?;:…\"'`~*()[]{}-—– \t\n\r"


def is_name_only(proposed: str, names) -> bool:
    """Return True if the entire message is nothing but a participant's name.

    A message whose whole content is an addressee's name ("Travis.", "casey",
    "Robin!") is a robotic chatbot tell — real people say something when they
    address someone. Such messages get dropped so the bot stays silent rather
    than shipping a bare name. Only exact single-name matches are flagged;
    "Travis you good?" and "no Travis stop" are left alone.
    """
    if not proposed or not names:
        return False
    cleaned = proposed.strip(_NAME_EDGE_CHARS).lower()
    if not cleaned:
        return False
    return cleaned in {n.strip(_NAME_EDGE_CHARS).lower() for n in names
                       if n and n.strip(_NAME_EDGE_CHARS)}


def is_echo(proposed: str, recent_messages: list[str]) -> bool:
    """Return True if `proposed` substantially overlaps any single recent message.

    Short messages ("lol", "nice", "same") are always allowed — real people
    reuse short reactions freely.
    """
    proposed_words = _normalize(proposed)
    if len(proposed_words) < MIN_WORDS:
        return False

    proposed_grams = _ngrams(proposed_words, NGRAM_N)
    if not proposed_grams:
        return False

    for msg in recent_messages:
        msg_words = _normalize(msg)
        msg_grams = _ngrams(msg_words, NGRAM_N)
        if not msg_grams:
            continue
        overlap = len(proposed_grams & msg_grams) / len(proposed_grams)
        if overlap >= THRESHOLD:
            return True

    return False
