"""Token-usage logging: cost math and the emitted log line."""

import logging
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import usage
from src.usage import estimate_cost, log_usage


def test_cost_uncached_input():
    # 1M input tokens on Sonnet 5 (intro $2) = $2.00
    assert estimate_cost("claude-sonnet-5", 1_000_000, 0, 0, 0) == 2.00


def test_cost_output():
    # 1M output tokens on Sonnet 5 (intro $10) = $10.00
    assert estimate_cost("claude-sonnet-5", 0, 0, 0, 1_000_000) == 10.00


def test_cache_read_is_a_tenth():
    full = estimate_cost("claude-sonnet-5", 1_000_000, 0, 0, 0)
    cached = estimate_cost("claude-sonnet-5", 0, 1_000_000, 0, 0)
    assert abs(cached - full * 0.1) < 1e-9


def test_cache_write_is_1_25x():
    full = estimate_cost("claude-sonnet-5", 1_000_000, 0, 0, 0)
    written = estimate_cost("claude-sonnet-5", 0, 0, 1_000_000, 0)
    assert abs(written - full * 1.25) < 1e-9


def test_unknown_model_is_free_not_a_crash():
    assert estimate_cost("some-future-model", 1_000_000, 0, 0, 0) == 0.0


def test_log_line_format(caplog):
    u = SimpleNamespace(input_tokens=11479, cache_read_input_tokens=6346,
                        cache_creation_input_tokens=0, output_tokens=180)
    with caplog.at_level(logging.INFO, logger="src.usage"):
        log_usage("decide:jordan", "claude-sonnet-5", u)
    line = caplog.records[-1].getMessage()
    assert "[usage]" in line
    assert "decide:jordan" in line
    assert "cache_read=6346" in line
    assert "in=11479" in line
    assert "$" in line


def test_log_handles_missing_usage_fields(caplog):
    # A usage object without cache fields must not crash.
    u = SimpleNamespace(input_tokens=100, output_tokens=20)
    with caplog.at_level(logging.INFO, logger="src.usage"):
        log_usage("nag_detect", "claude-haiku-4-5", u)
    assert "cache_read=0" in caplog.records[-1].getMessage()
