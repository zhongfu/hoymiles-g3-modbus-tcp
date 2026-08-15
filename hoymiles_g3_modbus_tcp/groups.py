"""Named register poll groups for tiered polling cadence.

A group is a pair ``(input_ranges, holding_ranges)`` of the same shape as
``readplan.DEFAULT_RANGES`` / ``DEFAULT_HOLDING_RANGES``.  Ranges are inclusive
``(lo, hi)`` start/end with ``hi`` exclusive.

The idea is that a consumer (e.g. a Home Assistant integration) can poll the
rapidly-changing statistics very often and the slow-moving ones rarely:

- ``fast``      — instantaneous power/current/voltage/frequency, meter and
                  battery blocks, energy flows, overview power totals.
- ``energy``    — lifetime and per-day energy counters (rarely change).
- ``status``    — device/battery work status codes and decoded fault bitmaps.
- ``battery``   — slow battery parameters (SOH, capacity, cutoffs, limits).
- ``diagnostics`` — thermals, auxiliary rails, fan speeds, isolation.
- ``settings``  — read-only holding registers (GCF, EMS, SOC limits).
- ``all``       — every register (input + holding).

Groups may overlap; a register read by two groups is simply read twice.
"""
from __future__ import annotations

from .readplan import DEFAULT_HOLDING_RANGES, DEFAULT_RANGES

FAST = (
    (0, 123),        # status, PV, battery-DC, bus, grid/AC/EPS
    (1800, 1924),    # grid meter + PV meter + battery BMS
    (2000, 2246),    # energy counters + power/energy flows
    (30000, 30021),  # overview power totals + battery SOC
)
ENERGY = ((2000, 2150),)          # lifetime + per-day energy counters
STATUS = (
    (0, 246),        # work status, SW/HW faults, firmware (via both 0-123 + 123-245)
    (1900, 1924),    # battery type / link / work status / fault
    (30000, 30030),  # system status, battery status/SOC, fault bitmaps
)
BATTERY = ((1900, 1924),)
DIAGNOSTICS = ((0, 246),)         # thermals, aux, fans, bus balance, PE/iso/residual
GROUPS = {
    "fast": (FAST, ()),
    "energy": (ENERGY, ()),
    "status": (STATUS, ()),
    "battery": (BATTERY, ()),
    "diagnostics": (DIAGNOSTICS, ()),
    "settings": ((), DEFAULT_HOLDING_RANGES),
    "all": (DEFAULT_RANGES, DEFAULT_HOLDING_RANGES),
}


def group_names() -> list[str]:
    """Return the pollable group names (excluding the ``all`` aggregator)."""
    return [name for name in GROUPS if name != "all"]
