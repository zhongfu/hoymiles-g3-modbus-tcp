"""Build a block-read plan from inclusive register ranges."""
from __future__ import annotations

DEFAULT_RANGES = ((0, 369), (1800, 1924), (2000, 2246), (30000, 30030))
DEFAULT_HOLDING_RANGES = (
    (258, 260),    # GCF enable / export limit
    (303, 312),    # gen port mode, battery power limits, SOC range
    (323, 325),    # EPS mode, PV island mode
    (3001, 3002),  # system operation
    (3016, 3017),  # parallel networking command
    (4100, 4103),  # battery type / BMS type / capacity
    (4300, 4307),  # EMS block
    (6048, 6050),  # topology: machines type / count
)
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
