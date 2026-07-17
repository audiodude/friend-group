"""Tests for configurable activity tuning (config.get_activity_config) and the
dampener parameters on schedule.should_respond."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.config import get_activity_config, DEFAULT_ACTIVITY
from src.schedule import should_respond


class TestGetActivityConfig:
    def test_defaults_when_no_activity_section(self):
        with patch.object(config, "load_config", return_value={"model": "x"}):
            cfg = get_activity_config()
        assert cfg == DEFAULT_ACTIVITY
        # returns a copy, not the module-level default
        assert cfg is not DEFAULT_ACTIVITY

    def test_partial_override_merges_over_defaults(self):
        raw = {"activity": {"initiation": {"silence_threshold_minutes": 30}}}
        with patch.object(config, "load_config", return_value=raw):
            cfg = get_activity_config()
        assert cfg["initiation"]["silence_threshold_minutes"] == 30      # overridden
        assert cfg["initiation"]["dampener"] == DEFAULT_ACTIVITY["initiation"]["dampener"]  # default kept
        assert cfg["reply"] == DEFAULT_ACTIVITY["reply"]                  # untouched section = defaults

    def test_unknown_keys_ignored(self):
        raw = {"activity": {"initiation": {"bogus_key": 999}}}
        with patch.object(config, "load_config", return_value=raw):
            cfg = get_activity_config()
        assert "bogus_key" not in cfg["initiation"]


class TestShouldRespondDampeners:
    CONFIG = {"chattiness": 1.0, "bot_reply_chance": 1.0,
              "timezone": "America/New_York",
              "schedule": {"wake_up": "00:00", "sleep_at": "23:59",
                           "work_start": "09:00", "work_end": "09:00", "days_off": []}}

    def test_human_dampener_zero_never_responds(self):
        # With a 0 human dampener, non-mention human messages never pass the gate.
        assert should_respond(self.CONFIG, is_bot_message=False, mentioned=False,
                              human_dampener=0.0) is False

    def test_bot_dampener_zero_never_responds_to_bots(self):
        assert should_respond(self.CONFIG, is_bot_message=True,
                              bot_dampener=0.0) is False

    def test_defaults_present(self):
        # Signature still callable without the new kwargs (backward compatible).
        import inspect
        sig = inspect.signature(should_respond)
        assert sig.parameters["human_dampener"].default == 0.9
        assert sig.parameters["bot_dampener"].default == 0.9
