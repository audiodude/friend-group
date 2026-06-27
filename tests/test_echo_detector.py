"""Tests for the message filters in src/echo_detector.py.

Focus: is_name_only — a message whose entire content is just a participant's
name ("Travis.", "casey", "Robin!") is a robotic chatbot tell and must be
dropped. Regression for the 2026-06-26 incident where two bots independently
replied with nothing but "Travis."
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.echo_detector import is_name_only, is_echo


NAMES = {"jordan", "quinn", "robin", "Travis"}


class TestIsNameOnly:
    def test_bare_name_with_period_is_dropped(self):
        # The exact incident: a complete message of just "Travis."
        assert is_name_only("Travis.", NAMES) is True

    def test_bare_name_no_punctuation(self):
        assert is_name_only("casey", {"casey"}) is True

    def test_bare_name_with_bang(self):
        assert is_name_only("Robin!", NAMES) is True

    def test_case_insensitive(self):
        assert is_name_only("travis", NAMES) is True
        assert is_name_only("QUINN.", NAMES) is True

    def test_surrounding_punctuation_and_space(self):
        assert is_name_only("...Travis...", NAMES) is True
        assert is_name_only("  Travis. ", NAMES) is True

    def test_name_plus_content_is_kept(self):
        assert is_name_only("Travis you good?", NAMES) is False
        assert is_name_only("no Travis stop", NAMES) is False

    def test_non_name_message_is_kept(self):
        assert is_name_only("lol", NAMES) is False
        assert is_name_only("yes?", NAMES) is False
        assert is_name_only("I'm partying", NAMES) is False

    def test_empty_inputs(self):
        assert is_name_only("", NAMES) is False
        assert is_name_only("Travis.", set()) is False
        assert is_name_only("...", NAMES) is False

    def test_two_names_not_treated_as_single(self):
        # Not a single addressee — leave it alone.
        assert is_name_only("casey robin", NAMES) is False


class TestIsEchoStillWorks:
    def test_short_message_allowed(self):
        assert is_echo("lol same", ["lol same here everyone"]) is False

    def test_obvious_echo_flagged(self):
        recent = ["sounds like she really gets it honestly"]
        assert is_echo("yeah sounds like she really gets it", recent) is True
