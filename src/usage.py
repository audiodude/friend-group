"""One log line per LLM call: token breakdown (incl. cache hits) + rough cost.

Grep the container logs for `[usage]` to see live spend, e.g.:
    docker logs sudomake-friends | grep '\\[usage\\]'
"""

import logging

logger = logging.getLogger(__name__)

# Approximate USD per 1M tokens as (input, output). Cache reads bill ~0.1x input,
# cache writes ~1.25x. UPDATE when pricing changes — notably Sonnet 5's intro
# pricing ($2/$10) ends 2026-08-31, reverting to $3/$15.
_PRICING = {
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}


def estimate_cost(model: str, in_tokens: int, cache_read: int,
                  cache_write: int, out_tokens: int) -> float:
    """Rough USD cost for one call. Cache reads ~0.1x, writes ~1.25x input."""
    in_price, out_price = _PRICING.get(model, (0.0, 0.0))
    billed_input = in_tokens + cache_write * 1.25 + cache_read * 0.1
    return (billed_input * in_price + out_tokens * out_price) / 1_000_000


def log_usage(label: str, model: str, usage) -> None:
    """Emit a `[usage]` line for one completed LLM call."""
    in_tokens = getattr(usage, "input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    out_tokens = getattr(usage, "output_tokens", 0) or 0
    cost = estimate_cost(model, in_tokens, cache_read, cache_write, out_tokens)
    logger.info(
        "[usage] %-16s model=%s in=%d cache_read=%d cache_write=%d out=%d ~$%.4f",
        label, model, in_tokens, cache_read, cache_write, out_tokens, cost,
    )
