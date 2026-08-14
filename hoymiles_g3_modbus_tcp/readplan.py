"""Build a block-read plan from inclusive register ranges."""
from __future__ import annotations

DEFAULT_RANGES = ((0, 369), (1000, 1123), (2000, 2246))


def build_read_plan(poll_ranges, max_block=123) -> list:
    """Return ``[(addr, count), ...]`` covering each ``(lo, hi)`` range.

    ``hi`` is exclusive.
    """
    plan = []
    for lo, hi in poll_ranges:
        a = lo
        while a < hi:
            n = min(max_block, hi - a)
            plan.append((a, n))
            a += n
    return plan
