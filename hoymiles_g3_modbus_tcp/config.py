"""Connection config and device detection."""
from __future__ import annotations

from dataclasses import dataclass

from .client import HoymilesClient
from .decode import decode_ascii_string
from .readplan import DEFAULT_HOLDING_RANGES, DEFAULT_RANGES


@dataclass
class InverterConfig:
    host: str
    port: int = 502
    unit: int = 1
    timeout: float = 3.0
    max_block: int = 123
    poll_ranges: tuple = DEFAULT_RANGES
    holding_ranges: tuple = DEFAULT_HOLDING_RANGES
    read_retries: int = 3



@dataclass
class InverterInfo:
    inverter_model: str
    has_battery: bool
    has_grid_meter: bool
    pv_mppt_count: int
    battery_capacity_kwh: float | None

async def detect_config(client: HoymilesClient) -> InverterInfo:
    """Detect device from the new battery (1900) and meter (1800) blocks.

    ``block_a[i]`` is register ``i`` in ``[0, 123)``; ``block_b[i]`` is register
    ``1000 + i`` in ``[1000, 1123)``; ``batt[i]`` is register ``1900 + i`` in
    ``[1900, 1924)``; ``meter[i]`` is register ``1800 + i`` in ``[1800, 1807)``.
    """
    block_a = await client.read_input(0, 123)
    block_b = await client.read_input(1000, 123)
    batt = await client.read_input(1900, 24)
    meter = await client.read_input(1800, 7)

    inverter_model = decode_ascii_string(block_b[0:5]) or "unknown"

    link = batt[1]                                   # 1901
    cap = (batt[7] << 16) | batt[8]                  # 1907-1908 (U_DWORD)
    soc = batt[9]                                    # 1909
    v = batt[11] * 0.1                               # 1911
    has_battery = bool(link > 0 or (cap * 0.1 > 1 and 0 <= soc <= 100 and v > 10))

    mlink = meter[0]                                 # 1800
    currents = meter[4:7]                            # 1804-1806
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
