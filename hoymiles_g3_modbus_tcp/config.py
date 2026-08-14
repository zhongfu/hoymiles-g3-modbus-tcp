"""Connection config and device detection."""
from __future__ import annotations

from dataclasses import dataclass

from .client import HoymilesClient
from .decode import decode_ascii_string
from .readplan import DEFAULT_RANGES


@dataclass
class InverterConfig:
    host: str
    port: int = 502
    unit: int = 1
    timeout: float = 3.0
    max_block: int = 123
    poll_ranges: tuple = DEFAULT_RANGES


@dataclass
class InverterInfo:
    inverter_model: str
    has_battery: bool
    has_grid_meter: bool
    pv_mppt_count: int
    battery_capacity_kwh: float | None


async def detect_config(client: HoymilesClient) -> InverterInfo:
    """Two block reads robust to the device's single-read drop quirk.

    ``block_a[i]`` is register ``i`` in ``[0, 123)``; ``block_b[i]`` is register
    ``1000 + i`` in ``[1000, 1123)``.
    """
    block_a = await client.read_input(0, 123)
    block_b = await client.read_input(1000, 123)

    inverter_model = decode_ascii_string(block_b[0:5]) or "unknown"

    link = block_b[22]
    soc = block_b[25]
    v = block_b[32]
    cap = block_b[24]
    has_battery = bool(link > 0 or (cap * 0.1 > 1 and 0 <= soc <= 100 and v > 10))

    mlink = block_b[46]
    currents = block_b[50:53]
    has_grid_meter = bool(
        mlink > 0 or any(x > 0 or x >= 0x8000 for x in currents)
    )

    pv_voltages = (block_a[27], block_a[30], block_a[33], block_a[36])
    pv_mppt_count = sum(1 for pv in pv_voltages if pv > 10)

    battery_capacity_kwh = cap * 0.1 if has_battery else None

    return InverterInfo(
        inverter_model=inverter_model,
        has_battery=has_battery,
        has_grid_meter=has_grid_meter,
        pv_mppt_count=pv_mppt_count,
        battery_capacity_kwh=battery_capacity_kwh,
    )
