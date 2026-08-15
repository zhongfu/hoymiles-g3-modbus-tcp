"""Plausibility checks for freshly-read Modbus blocks.

A desynced/garbage block read (e.g. from two readers on one device) can return a
physically absurd value like ``battery_soc = 2005`` or ``grid_voltage_a = 1000 V``.
:func:`block_is_plausible` flags such blocks so the reader can retry them. Bounds are
generous physical limits (2-5x nominal), so genuinely out-of-spec but plausible
readings (e.g. 15200 W on a 15 kW unit) are never flagged.
"""
from __future__ import annotations

from .decode import decode_words
from .registers import REGISTERS_BY_ADDR, WSIZE

# Decoded-value inclusive bounds, keyed by register key. Only physically-bounded
# sensor magnitudes: SoC / SOH / battery voltage / AC voltage / frequency / temperature.
# Power, current, and energy flows are intentionally absent so real out-of-spec loads
# are never flagged.
REGISTER_BOUNDS: dict[str, tuple[float, float]] = {
    "battery_soc": (0.0, 100.0),       # hard physical ceiling; catches 2005
    "battery_soh": (0.0, 150.0),
    "batt_voltage_bms": (0.0, 150.0),  # 16S LFP ~40-60 V; 60 V passes
    "bat1_voltage": (0.0, 150.0),
    "grid_voltage_a": (0.0, 600.0),    # L-N nominal ~240 V; catches 1000 V
    "grid_voltage_b": (0.0, 600.0),
    "grid_voltage_c": (0.0, 600.0),
    "inv_voltage_a": (0.0, 600.0),
    "inv_voltage_b": (0.0, 600.0),
    "inv_voltage_c": (0.0, 600.0),
    "backup_voltage_a": (0.0, 600.0),
    "backup_voltage_b": (0.0, 600.0),
    "backup_voltage_c": (0.0, 600.0),
    "meter_grid_voltage_a": (0.0, 600.0),
    "meter_grid_voltage_b": (0.0, 600.0),
    "meter_grid_voltage_c": (0.0, 600.0),
    "pv_meter_voltage_a": (0.0, 600.0),
    "pv_meter_voltage_b": (0.0, 600.0),
    "pv_meter_voltage_c": (0.0, 600.0),
    "grid_frequency": (40.0, 70.0),    # 50 Hz +/- wide margin
    "meter_grid_freq": (40.0, 70.0),
    "inv_ths_temp": (-40.0, 150.0),
    "bat_ths_temp": (-40.0, 150.0),
    "cav_temp": (-40.0, 150.0),
    "batt_max_cell_temp": (-40.0, 150.0),
    "batt_min_cell_temp": (-40.0, 150.0),
}


def block_is_plausible(addr, count, words, bounds=REGISTER_BOUNDS) -> bool:
    """Return ``True`` when ``words`` (a single block read of ``count`` words
    starting at ``addr``) decodes to physically plausible values."""
    if not bounds:
        return True
    for i, w in enumerate(words):
        if w is None:
            continue
        reg = REGISTERS_BY_ADDR.get(addr + i)
        if reg is None:
            continue
        key = reg.key
        if key not in bounds:
            continue
        n = WSIZE[reg.dtype]
        ws = words[i : i + n]
        if len(ws) < n or any(x is None for x in ws):
            # Block-edge partial / missing data -- not "bad data", leave it.
            continue
        v = decode_words(ws, reg.dtype, reg.scale)
        if not (bounds[key][0] <= v <= bounds[key][1]):
            return False
    return True


__all__ = ["REGISTER_BOUNDS", "block_is_plausible"]
